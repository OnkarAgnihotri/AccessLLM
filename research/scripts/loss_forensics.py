"""Loss forensics for the intraday playbook (research/LOSS_ANALYSIS.md).

Builds a candidate pool of every setup-A/B signal (core pattern only, optional filters recorded as
features), re-simulates exits under different rules at Rs 25,000 per trade (no margin), and
reports features, loss causes and what-if results with a 60/40 time split.

Usage: python loss_forensics.py <data_dir> <universe.txt> <out_dir>
"""

import argparse
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
import intraday_backtest as ib                                      # noqa: E402

CAP = 25000.0
TICK = 0.05


def charges(buy_v, sell_v, orders, slip=0.03):
    brok = sum(min(20, 0.0003 * v) for v in (buy_v, sell_v)) + (min(20, 0.0003 * sell_v / 2) if orders == 3 else 0)
    exch, sebi = (buy_v + sell_v) * 0.0000297, (buy_v + sell_v) * 0.000001
    return brok + 0.18 * (brok + exch + sebi) + exch + sebi + sell_v * 0.00025 + buy_v * 0.00003 \
        + (buy_v + sell_v) * slip / 100


# ----------------------------------------------------------------------------- candidate pool
def pool_args():
    return argparse.Namespace(rvol=0.0, rvol_days=10, rs=False, idx_bias=False, daily=False, cpr_max=99.0,
                              use_a=True, use_b=True)


def strict_masks(d):
    """the playbook's optional filters, evaluated separately so they can be switched on/off later"""
    c = d.Close
    stk, ix = c / d.day_open - 1, d.ic / d.iopen - 1
    return pd.DataFrame({
        "f_rvol": d.rvol >= 1.5,
        "f_rs_long": (stk > 0) & (stk > ix), "f_rs_short": (stk < 0) & (stk < ix),
        "f_idx_long": d.ic > d.ie21, "f_idx_short": d.ic < d.ie21,
        "f_daily_long": (d.pdc > d.e20) & (d.e20 > d.e50), "f_daily_short": (d.pdc < d.e20) & (d.e20 < d.e50),
        "f_cpr": d.cprw <= 0.6,
    }, index=d.index)


def build_pool(data, universe):
    nf = ib.load(os.path.join(data, "5m", "^NSEI.csv"))
    idx = pd.DataFrame({"ic": nf.Close, "ie21": ib.ema(nf.Close, 21)})
    idx["iopen"] = nf.Open.groupby(nf.index.normalize()).transform("first")
    a = pool_args()
    a.data = data
    bars, cands = {}, []
    for s in [x.strip() for x in open(universe) if x.strip()]:
        p = os.path.join(data, "5m", f"{s}.csv")
        if not os.path.exists(p):
            continue
        try:
            d = ib.signals(ib.prepare(s, a, idx), a)
        except Exception as e:                           # noqa: BLE001
            print("skip", s, e)
            continue
        d["ic_ret6"] = d.ic / d.ic.shift(6) - 1
        d = d.join(strict_masks(d))
        bars[s] = d
        for col, side, setup in (("aL", 1, "A"), ("aS", -1, "A"), ("bL", 1, "B"), ("bS", -1, "B")):
            for i in np.flatnonzero(d[col].to_numpy()):
                cands.append((s, i, side, setup))
    return bars, cands


def plan_fill(d, i, side, setup):
    """playbook entry: A = next open, B = stop order beyond the signal candle for 2 bars (cancel on VWAP loss)"""
    O, H, L, C, DAY, VW = (d[k].to_numpy() for k in ("Open", "High", "Low", "Close", "day", "vwap"))
    n = len(d)
    if i + 1 >= n or DAY[i + 1] != DAY[i]:
        return None, None
    if setup == "A":
        return i + 1, O[i + 1]
    e = H[i] + TICK if side == 1 else L[i] - TICK
    for j in range(i + 1, min(i + 3, n)):
        if DAY[j] != DAY[i]:
            return None, None
        if (side == 1 and H[j] >= e) or (side == -1 and L[j] <= e):
            return j, (max(O[j], e) if side == 1 else min(O[j], e))
        if (side == 1 and C[j] < VW[j]) or (side == -1 and C[j] > VW[j]):
            return None, None
    return None, None


def rule_stop(d, i, side, setup, kind, fill):
    H, L, ATR, ORM = d.High.iat[i], d.Low.iat[i], d.atr.iat[i], d.ormid.iat[i]
    if kind in ("rule", "floor"):
        if setup == "A":
            st = max(L - 0.1 * ATR, ORM) if side == 1 else min(H + 0.1 * ATR, ORM)
        else:
            st = L - 0.1 * ATR if side == 1 else H + 0.1 * ATR
        if kind == "floor":
            dist = max(abs(fill - st), ATR, 0.004 * fill)
            st = fill - side * dist
        return st
    if kind == "or_far":
        return (d.orl.iat[i] if side == 1 else d.orh.iat[i]) if setup == "A" else rule_stop(d, i, side, setup, "floor", fill)
    if kind.startswith("atr"):
        return fill - side * float(kind[3:]) * ATR
    if kind == "vwap":                                      # catastrophic stop; the real exit is a close beyond VWAP
        return fill - side * 2.0 * ATR
    raise ValueError(kind)


def sim_exit(d, j, fill, side, stop, cfg):
    """cfg keys: t1 (R or None), final (R target for the rest or None), trail ('ema9'|None),
    be (move stop to cost after t1), time_bars/time_r (time stop), vwap_exit (bool)"""
    O, H, L, C, T, DAY = (d[k].to_numpy() for k in ("Open", "High", "Low", "Close", "t", "day"))
    E9, UP2, DN2, VW = (d[k].to_numpy() for k in ("ema9", "up2", "dn2", "vwap"))
    R = abs(fill - stop)
    t1 = fill + side * cfg["t1"] * R if cfg.get("t1") else None
    fin = fill + side * cfg["final"] * R if cfg.get("final") else None
    cur, t1_done, t1_bar, half_px, mfe, mae = stop, False, None, None, 0.0, 0.0
    k, n, day = j, len(d), DAY[j]
    exit_px = reason = None
    while k < n and DAY[k] == day:
        fav = (H[k] - fill) if side == 1 else (fill - L[k])
        adv = (fill - L[k]) if side == 1 else (H[k] - fill)
        hit_stop = (L[k] <= cur) if side == 1 else (H[k] >= cur)
        gap = ((O[k] <= cur) if side == 1 else (O[k] >= cur)) and k > j
        if hit_stop and not (t1_done and k == t1_bar):
            exit_px, reason = (O[k] if gap else cur), ("breakeven" if t1_done else "stop")
            mae = max(mae, adv / R)
            break
        mfe, mae = max(mfe, fav / R), max(mae, adv / R)
        if t1 is not None and not t1_done and ((H[k] >= t1) if side == 1 else (L[k] <= t1)):
            t1_done, t1_bar, half_px = True, k, t1
            if cfg.get("be", True):
                cur = max(cur, fill * 1.001) if side == 1 else min(cur, fill * 0.999)
        if fin is not None and ((H[k] >= fin) if side == 1 else (L[k] <= fin)):
            exit_px, reason = fin, "target"
            break
        if cfg.get("vwap_exit") and ((side == 1 and C[k] < VW[k]) or (side == -1 and C[k] > VW[k])):
            exit_px, reason = C[k], "vwap close"
            break
        if cfg.get("trail") == "ema9" and t1_done and k > t1_bar and \
                ((side == 1 and (C[k] < E9[k] or H[k] >= UP2[k])) or (side == -1 and (C[k] > E9[k] or L[k] <= DN2[k]))):
            exit_px, reason = C[k], "trail"
            break
        if cfg.get("time_bars") and k - j + 1 >= cfg["time_bars"] and not t1_done and mfe < cfg.get("time_r", 0.5):
            exit_px, reason = C[k], "time stop"
            break
        if T[k] >= 1510:
            exit_px, reason = C[k], "15:10 flat"
            break
        k += 1
    if exit_px is None:
        k -= 1
        exit_px, reason = C[k], "eod"
    return dict(exit_bar=k, exit_px=exit_px, reason=reason, t1_hit=t1_done,
                half_px=half_px if half_px is not None else exit_px, R=R, mfe_R=mfe, mae_R=mae)


def rupees(fill, side, res, slip=0.03):
    qty = int(CAP // fill)
    q1 = qty // 2 if res["t1_hit"] else 0
    q2 = qty - q1
    avg = (q1 * res["half_px"] + q2 * res["exit_px"]) / qty
    gross = side * qty * (avg - fill)
    bv, sv = (fill * qty, avg * qty) if side == 1 else (avg * qty, fill * qty)
    ch = charges(bv, sv, 3 if res["t1_hit"] else 2, slip)
    return qty, avg, gross, ch, gross - ch


V1 = dict(stop="rule", t1=1.5, trail="ema9", be=True)


def run_config(bars, cands, cfg, keep=None):
    """simulate every candidate under cfg; one position per stock at a time (time order)"""
    rows = []
    busy = {}
    for s, i, side, setup in sorted(cands, key=lambda c: (bars[c[0]].index[c[1]], c[0])):
        d = bars[s]
        if keep is not None and not keep(d, i, side, setup):
            continue
        if busy.get(s, -1) >= i:
            continue
        j, fill = plan_fill(d, i, side, setup)
        if j is None:
            continue
        stop = rule_stop(d, i, side, setup, cfg["stop"], fill)
        if (fill - stop) * side <= 0:
            continue
        r = sim_exit(d, j, fill, side, stop, cfg)
        qty, avg, gross, ch, net = rupees(fill, side, r)
        if qty < 1:
            continue
        busy[s] = r["exit_bar"]
        rows.append(dict(symbol=s, i=i, j=j, setup=setup, side=side, day=d.day.iat[i], signal=d.index[i],
                         entry_time=d.index[j], exit_time=d.index[r["exit_bar"]], entry=fill, stop=stop,
                         avg_exit=avg, qty=qty, gross=gross, charges=ch, net=net, **r))
    return pd.DataFrame(rows)


def summary(t, split_day=None):
    def one(x):
        if x.empty:
            return dict(trades=0)
        w = x.net > 0
        return dict(trades=len(x), win_pct=round(100 * w.mean(), 1), gross_rs=round(x.gross.sum()),
                    charges_rs=round(x.charges.sum()), net_rs=round(x.net.sum()), avg_net_rs=round(x.net.mean(), 1),
                    pf=round(x.net[w].sum() / -x.net[~w].sum(), 2) if (~w).any() and w.any() else None)
    out = {"ALL": one(t)}
    if split_day is not None and not t.empty:
        out["first60"] = one(t[t.day < split_day])
        out["last40"] = one(t[t.day >= split_day])
    return out


# ----------------------------------------------------------------------------- entry filters
def playbook_keep(d, i, side, setup):
    """the v1 playbook filters plus its stop-width and room checks"""
    r = d.iloc[i]
    L_ = side == 1
    ok = bool(r.f_rvol) and bool(r.f_rs_long if L_ else r.f_rs_short) and bool(r.f_idx_long if L_ else r.f_idx_short)
    if setup == "A":
        ok = ok and bool(r.f_daily_long if L_ else r.f_daily_short) and bool(r.f_cpr)
        st = max(r.Low - 0.1 * r.atr, r.ormid) if L_ else min(r.High + 0.1 * r.atr, r.ormid)
        e = r.Close
        R = (e - st) * side
        ok = ok and 0 < R <= 1.2 * r.datr / 4
    else:
        e = r.High + TICK if L_ else r.Low - TICK
        st = r.Low - 0.1 * r.atr if L_ else r.High + 0.1 * r.atr
        R = (e - st) * side
        ok = ok and 0 < R <= 3 * r.atr
    if not ok:
        return False
    if L_:
        lvl = r.pdh if r.pdh > e else (r.r1 if r.r1 > e else r.up2)
        return lvl <= e or lvl - e >= 2 * R
    lvl = r.pdl if r.pdl < e else (r.s1 if r.s1 < e else r.dn2)
    return lvl >= e or e - lvl >= 2 * R


def rvol_only_keep(d, i, side, setup):
    return bool(d.f_rvol.iat[i])


def both(*fs):
    return lambda d, i, side, setup: all(f(d, i, side, setup) for f in fs)


def feat(name, fn):
    f = lambda d, i, side, setup: bool(fn(d.iloc[i], side, setup))          # noqa: E731
    f.__name__ = name
    return f
