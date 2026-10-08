"""Backtest of research/INTRADAY_PLAYBOOK.md (Setup A: 15m ORB, Setup B: VWAP pullback) on 5-minute bars.

Python port of pine/nse_vwap_orb_pullback.pine. Two stages:
  1. per stock, bar by bar: signals and trade outcomes (one position at a time per stock, like the
     Pine strategy on one chart);
  2. portfolio: trades taken in time order under the desk limits (max 3 open, max 5 per day,
     max 2 per sector... sector skipped here, daily stop -2R, halt after 2 consecutive losses).

Usage: python intraday_backtest.py <data_dir> <universe.txt> <out_dir> [--rvol 1.5] [--no-rs] ...
data_dir must contain 5m/<SYM>.csv, 5m/^NSEI.csv and 1d/<SYM>.csv (IST timestamps).
"""

import argparse
import os

import numpy as np
import pandas as pd

TICK = 0.05


def load(path):
    d = pd.read_csv(path, index_col=0)
    d.index = pd.to_datetime(d.index, format="mixed")
    if getattr(d.index, "tz", None) is not None:
        d.index = d.index.tz_convert("Asia/Kolkata").tz_localize(None)
    return d[~d.index.duplicated()].sort_index().dropna(subset=["Open", "High", "Low", "Close"])


def ema(x, n):
    return x.ewm(span=n, adjust=False).mean()


def rsi(c, n=14):
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def atr(h, l, c, n=14):
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean()          # Wilder, as ta.atr


def daily_refs(path):
    d = load(path)
    c = d.Close
    tr = pd.concat([d.High - d.Low, (d.High - c.shift()).abs(), (d.Low - c.shift()).abs()], axis=1).max(axis=1)
    r = pd.DataFrame({"pdc": c, "pdh": d.High, "pdl": d.Low, "e20": ema(c, 20), "e50": ema(c, 50),
                      "e200": ema(c, 200), "datr": tr.ewm(alpha=1 / 14, adjust=False).mean()}).shift(1)   # yesterday's values
    r.index = r.index.normalize()
    # weekly trend known before the open: last close vs the 20-week EMA, built from days before today
    wdiff = pd.Series(np.nan, index=r.index)
    for k in range(max(len(d) - 150, 30), len(d)):
        w = c.iloc[:k].resample("W-FRI").last().dropna()
        if len(w) >= 22:
            wdiff.iat[k] = w.iloc[-1] - ema(w, 20).iloc[-1]
    r["wdiff"] = wdiff.values
    return r


def prepare(sym, a, idx):
    d = load(os.path.join(a.data, "5m", f"{sym}.csv"))
    d = d[(d.index.time >= pd.Timestamp("09:15").time()) & (d.index.time <= pd.Timestamp("15:25").time())]
    if getattr(a, "start", ""):
        d = d[d.index >= pd.Timestamp(a.start)]
    if getattr(a, "end", ""):
        d = d[d.index < pd.Timestamp(a.end) + pd.Timedelta(days=1)]
    d["day"] = d.index.normalize()
    d["t"] = d.index.hour * 100 + d.index.minute
    d["ema9"], d["ema21"] = ema(d.Close, 9), ema(d.Close, 21)
    d["rsi"], d["atr"] = rsi(d.Close), atr(d.High, d.Low, d.Close)
    d["volavg"] = d.Volume.rolling(20).mean()
    d["vol_hi10"] = d.Volume.rolling(10).max()
    tp = (d.High + d.Low + d.Close) / 3
    g = d.groupby("day")
    sv, spv, spv2 = g.Volume.cumsum(), (tp * d.Volume).groupby(d.day).cumsum(), (tp * tp * d.Volume).groupby(d.day).cumsum()
    d["vwap"] = (spv / sv.replace(0, np.nan)).fillna(tp)
    sd = np.sqrt(np.maximum(spv2 / sv.replace(0, np.nan) - d.vwap ** 2, 0)).fillna(0)
    d["up1"], d["dn1"], d["up2"], d["dn2"] = d.vwap + sd, d.vwap - sd, d.vwap + 2 * sd, d.vwap - 2 * sd
    d["rsi_lo4"], d["rsi_hi4"] = d.rsi.rolling(4).min(), d.rsi.rolling(4).max()
    d["bar_n"] = g.cumcount() + 1
    d["above"] = (d.Close > d.vwap).groupby(d.day).cumsum() / d.bar_n
    d["tag_up1"] = (d.High > d.up1).groupby(d.day).cummax()
    d["tag_dn1"] = (d.Low < d.dn1).groupby(d.day).cummax()
    d["day_open"] = g.Open.transform("first")
    # opening range 09:15-09:30 and opening RVol vs previous 20 days
    orb = d[d.t < 930].groupby("day").agg(orh=("High", "max"), orl=("Low", "min"), orv=("Volume", "sum"))
    orb["rvol"] = orb.orv / orb.orv.rolling(20, min_periods=a.rvol_days).mean().shift(1)
    d = d.join(orb, on="day")
    d["ormid"] = (d.orh + d.orl) / 2
    # daily references
    ref = daily_refs(os.path.join(a.data, "1d", f"{sym}.csv"))
    d = d.join(ref, on="day")
    piv = (d.pdh + d.pdl + d.pdc) / 3
    bc = (d.pdh + d.pdl) / 2
    tc = 2 * piv - bc
    d["cprw"], d["r1"], d["s1"] = (tc - bc).abs() / piv * 100, 2 * piv - d.pdl, 2 * piv - d.pdh
    # benchmark
    d = d.join(idx, how="left")
    d[["ic", "ie21", "iopen"]] = d[["ic", "ie21", "iopen"]].ffill()
    return d


def signals(d, a):
    c, o, h, l = d.Close, d.Open, d.High, d.Low
    am = (d.t >= 930) & (d.t < 1130)
    pm = (d.t >= 1330) & (d.t < 1445)
    rvol_ok = (d.rvol >= a.rvol) if a.rvol > 0 else True
    stk, ix = c / d.day_open - 1, d.ic / d.iopen - 1
    rs_l = ((stk > 0) & (stk > ix)) if a.rs else True
    rs_s = ((stk < 0) & (stk < ix)) if a.rs else True
    ib = (d.ic > d.ie21) if a.idx_bias else True
    ibr = (d.ic < d.ie21) if a.idx_bias else True
    du = ((d.pdc > d.e20) & (d.e20 > d.e50)) if a.daily else True
    dd = ((d.pdc < d.e20) & (d.e20 < d.e50)) if a.daily else True
    cpr_ok = (d.cprw <= a.cpr_max) & (d.atr / d.Close * 100 >= a.min_atr_pct)   # v2: only stocks that move
    b_ok = cpr_ok if a.cpr_on_b else True                                       # v1 has no CPR rule for setup B
    vsurge = d.Volume >= 1.5 * d.volavg
    body, rng = (c - o).abs(), (h - l).clip(lower=TICK)
    hammer = ((np.minimum(o, c) - l) >= 2 * body) & (c >= l + rng * 2 / 3)
    star = ((h - np.maximum(o, c)) >= 2 * body) & (c <= h - rng * 2 / 3)
    beng = (c > o) & (c.shift() < o.shift()) & (c >= o.shift()) & (o <= c.shift()) & (d.Volume > d.volavg)
    seng = (c < o) & (c.shift() > o.shift()) & (c <= o.shift()) & (o >= c.shift()) & (d.Volume > d.volavg)
    vw_up, vw_dn = d.vwap > d.vwap.shift(3), d.vwap < d.vwap.shift(3)
    # v3 veto O3: no trade against the higher-timeframe trend (daily EMA stack net against, or wrong side of 20w EMA)
    dscore = np.sign(d.pdc - d.e20) + np.sign(d.e20 - d.e50) + np.sign(d.e50 - d.e200)
    htf_l = ~((dscore <= -1) | (d.wdiff < 0)) if a.veto_htf else True
    htf_s = ~((-dscore <= -1) | (d.wdiff > 0)) if a.veto_htf else True
    d["aL"] = a.use_a & am & htf_l & (c > d.orh + 0.1 * d.atr) & (c > d.vwap) & vw_up & (d.ema9 > d.ema21) & d.rsi.between(60, 80) \
        & vsurge & (c < d.up2) & rvol_ok & rs_l & ib & du & cpr_ok
    d["aS"] = a.use_a & am & htf_s & (c < d.orl - 0.1 * d.atr) & (c < d.vwap) & vw_dn & (d.ema9 < d.ema21) & d.rsi.between(20, 40) \
        & vsurge & (c > d.dn2) & rvol_ok & rs_s & ibr & dd & cpr_ok
    bwin = (am & (d.bar_n >= 7)) | pm
    d["bL"] = a.use_b & bwin & b_ok & htf_l & (d.above >= 0.7) & d.tag_up1 & (d.ema9 > d.ema21) & (l <= d.vwap + 0.1 * d.atr) & (c > d.vwap) \
        & (hammer | beng) & (d.rsi_lo4 >= 45) & (d.rsi > d.rsi.shift()) & (d.Volume < d.vol_hi10) & (c < d.up2) & rvol_ok & rs_l & ib
    d["bS"] = a.use_b & bwin & b_ok & htf_s & (d.above <= 0.3) & d.tag_dn1 & (d.ema9 < d.ema21) & (h >= d.vwap - 0.1 * d.atr) & (c < d.vwap) \
        & (star | seng) & (d.rsi_hi4 <= 55) & (d.rsi < d.rsi.shift()) & (d.Volume < d.vol_hi10) & (c > d.dn2) & rvol_ok & rs_s & ibr
    for k in ("aL", "aS", "bL", "bS"):
        d[k] = d[k].fillna(False).astype(bool)
    return d


def simulate(sym, d, a):
    """bar-by-bar, one position at a time; returns trades in R (gross) plus prices for costs"""
    O, H, L, C = (d[k].to_numpy(float) for k in ("Open", "High", "Low", "Close"))
    T, DAY = d.t.to_numpy(), d.day.to_numpy()
    E9, UP2, DN2, VW, ATR = (d[k].to_numpy(float) for k in ("ema9", "up2", "dn2", "vwap", "atr"))
    sig = {k: d[k].to_numpy() for k in ("aL", "aS", "bL", "bS")}
    PDH, PDL, R1, S1, DATR, ORM = (d[k].to_numpy(float) for k in ("pdh", "pdl", "r1", "s1", "datr", "ormid"))
    idx = d.index
    n, out, i = len(d), [], 0

    def room(side, e, R, j):
        if side == 1:
            lvl = PDH[j] if PDH[j] > e else (R1[j] if R1[j] > e else UP2[j])
            return lvl <= e or lvl - e >= a.room * R
        lvl = PDL[j] if PDL[j] < e else (S1[j] if S1[j] < e else DN2[j])
        return lvl >= e or e - lvl >= a.room * R

    while i < n - 1:
        side = setup = None
        if T[i] < 1510:
            for k, s, st in (("aL", 1, "A"), ("aS", -1, "A"), ("bL", 1, "B"), ("bS", -1, "B")):
                if sig[k][i]:
                    side, setup = s, st
                    break
        if side is None:
            i += 1
            continue
        # plan
        if setup == "A":
            if a.a_stop == "or_far":
                stop = d.orl.iat[i] if side == 1 else d.orh.iat[i]
            else:
                stop = max(L[i] - 0.1 * ATR[i], ORM[i]) if side == 1 else min(H[i] + 0.1 * ATR[i], ORM[i])
            plan_e = C[i]
            R = (plan_e - stop) * side
            ok = R > 0 and R <= 1.2 * DATR[i] / 4
        else:
            plan_e = H[i] + TICK if side == 1 else L[i] - TICK
            stop = L[i] - 0.1 * ATR[i] if side == 1 else H[i] + 0.1 * ATR[i]
            R = (plan_e - stop) * side
            ok = R > 0 and R <= 3 * ATR[i]
        if a.stop_atr > 0:                         # v2: fixed ATR stop replaces the structural stop
            stop, R = plan_e - side * a.stop_atr * ATR[i], a.stop_atr * ATR[i]
            ok = True
        floor = max(a.min_stop_atr * ATR[i], a.min_stop_pct / 100 * plan_e)
        if ok and R < floor:                       # noise floor: widen the stop, never tighten
            stop, R = plan_e - side * floor, floor
            ok = setup == "B" or R <= 1.2 * DATR[i] / 4 or a.a_stop == "or_far"
        if not ok or not room(side, plan_e, R, i):
            i += 1
            continue
        # fill
        j, fill = i + 1, None
        if setup == "A":
            if DAY[j] == DAY[i]:
                fill = O[j]
        else:
            for j in range(i + 1, min(i + 3, n)):
                if DAY[j] != DAY[i]:
                    break
                if (side == 1 and H[j] >= plan_e) or (side == -1 and L[j] <= plan_e):
                    fill = max(O[j], plan_e) if side == 1 else min(O[j], plan_e)
                    break
                if (side == 1 and C[j] < VW[j]) or (side == -1 and C[j] > VW[j]):
                    break                                  # lost VWAP: order cancelled
        if fill is None:
            i += 1
            continue
        # manage (R stays the planned risk; stop and target are absolute prices)
        t1 = fill + side * a.t1 * R
        cur_stop, t1_done, t1_bar, half_px, exit_px, reason = stop, False, None, None, None, None
        k = j
        while k < n and DAY[k] == DAY[i]:
            hit_stop = (L[k] <= cur_stop) if side == 1 else (H[k] >= cur_stop)
            gap_stop = (O[k] <= cur_stop) if side == 1 else (O[k] >= cur_stop)
            if not t1_done:
                if hit_stop:
                    exit_px = O[k] if (gap_stop and k > j) else cur_stop
                    reason = "stop"
                    break
                if (H[k] >= t1) if side == 1 else (L[k] <= t1):
                    t1_done, t1_bar, half_px = True, k, t1
                    cur_stop = max(stop, fill * 1.001) if side == 1 else min(stop, fill * 0.999)
            else:
                if k > t1_bar and hit_stop:
                    exit_px = O[k] if gap_stop else cur_stop
                    reason = "breakeven"
                    break
                if k > t1_bar and ((side == 1 and (C[k] < E9[k] or H[k] >= UP2[k])) or
                                   (side == -1 and (C[k] > E9[k] or L[k] <= DN2[k]))):
                    exit_px, reason = C[k], "trail"
                    break
            if T[k] >= 1510:
                exit_px, reason = C[k], "15:10 flat"
                break
            k += 1
        if exit_px is None:                     # day ended without a 15:10 bar
            k -= 1
            exit_px, reason = C[k], "eod"
        if half_px is None:
            half_px = exit_px
        gross_R = (0.5 * (half_px - fill) + 0.5 * (exit_px - fill)) * side / R
        out.append(dict(symbol=sym, setup=setup, side="LONG" if side == 1 else "SHORT", day=pd.Timestamp(DAY[i]).date(),
                        signal=idx[i], entry_time=idx[j], exit_time=idx[k], entry=fill, stop=stop, t1=t1, R=R,
                        half_px=half_px, exit=exit_px, t1_hit=t1_done, reason=reason, gross_R=gross_R))
        i = k + 1
    return out


def costs_rs(t, qty, a):
    """Indian intraday (MIS) charges for one trade: buy + sell legs, 3 orders if T1 was hit."""
    buy_px, sell_px = (t.entry, (t.half_px + t.exit) / 2) if t.side == "LONG" else ((t.half_px + t.exit) / 2, t.entry)
    buy_v, sell_v = buy_px * qty, sell_px * qty
    orders = 3 if t.t1_hit else 2
    brok = sum(min(a.brokerage, 0.0003 * v) for v in [buy_v, sell_v]) + (a.brokerage if orders == 3 else 0)
    exch = (buy_v + sell_v) * 0.0000297
    sebi = (buy_v + sell_v) * 0.000001
    gst = 0.18 * (brok + exch + sebi)
    stt = sell_v * 0.00025
    stamp = buy_v * 0.00003
    slip = (buy_v + sell_v) * a.slippage / 100
    return brok + exch + sebi + gst + stt + stamp + slip


def portfolio(tr, a):
    """apply desk limits in time order; returns taken trades with rupee P&L"""
    risk_rs = a.capital * a.risk / 100
    tr = tr.sort_values(["entry_time", "symbol"]).reset_index(drop=True)
    taken, open_until = [], []
    day, day_pnl, day_n, consec, halted = None, 0.0, 0, 0, False
    closed_q = []                                     # (exit_time, pnl) of taken trades not yet booked
    for _, t in tr.iterrows():
        if t.day != day:
            day, day_pnl, day_n, consec, halted, open_until, closed_q = t.day, 0.0, 0, 0, False, [], []
        # book trades that closed before this entry
        for x in sorted([q for q in closed_q if q[0] <= t.entry_time]):
            day_pnl += x[1]
            consec = consec + 1 if x[1] < 0 else 0
        closed_q = [q for q in closed_q if q[0] > t.entry_time]
        if day_pnl <= -a.day_stop_r * risk_rs or consec >= 2:
            halted = True
        open_until = [e for e in open_until if e > t.entry_time]
        if halted or day_n >= a.max_trades or len(open_until) >= a.max_open:
            continue
        qty = int(min(risk_rs / t.R, 3 * a.capital / t.entry))
        if qty < 1:
            continue
        gross = t.gross_R * t.R * qty
        cost = costs_rs(t, qty, a)
        pnl = gross - cost
        taken.append(dict(t.to_dict(), qty=qty, gross_rs=round(gross, 2), costs_rs=round(cost, 2), pnl_rs=round(pnl, 2),
                          net_R=round(pnl / risk_rs, 3)))
        day_n += 1
        open_until.append(t.exit_time)
        closed_q.append((t.exit_time, pnl))
    return pd.DataFrame(taken)


def stats(x, risk_rs):
    if x.empty:
        return {"trades": 0}
    w = x.pnl_rs > 0
    return {"trades": len(x), "win_pct": round(100 * w.mean(), 1), "t1_hit_pct": round(100 * x.t1_hit.mean(), 1),
            "avg_gross_R": round(x.gross_R.mean(), 3), "avg_net_R": round(x.net_R.mean(), 3),
            "avg_cost_R": round((x.costs_rs / risk_rs).mean(), 3),
            "profit_factor": round(x.pnl_rs[w].sum() / -x.pnl_rs[~w].sum(), 2) if (~w).any() else None,
            "net_pnl_rs": round(x.pnl_rs.sum()), "costs_rs": round(x.costs_rs.sum())}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data"); ap.add_argument("universe"); ap.add_argument("out")
    ap.add_argument("--capital", type=float, default=500000)
    ap.add_argument("--risk", type=float, default=0.5)
    ap.add_argument("--rvol", type=float, default=1.5)
    ap.add_argument("--rvol-days", type=int, default=10, help="min prior days for the RVol average")
    ap.add_argument("--no-rs", dest="rs", action="store_false")
    ap.add_argument("--no-idx-bias", dest="idx_bias", action="store_false")
    ap.add_argument("--no-daily", dest="daily", action="store_false")
    ap.add_argument("--cpr-max", type=float, default=0.6)
    ap.add_argument("--t1", type=float, default=1.5)
    ap.add_argument("--room", type=float, default=2.0)
    ap.add_argument("--no-a", dest="use_a", action="store_false")
    ap.add_argument("--no-b", dest="use_b", action="store_false")
    ap.add_argument("--brokerage", type=float, default=20.0)
    ap.add_argument("--slippage", type=float, default=0.03, help="%% per side")
    ap.add_argument("--min-stop-atr", type=float, default=0.0, help="stop at least this many 5m ATRs away")
    ap.add_argument("--min-stop-pct", type=float, default=0.0, help="stop at least this %% of price away")
    ap.add_argument("--a-stop", default="rule", choices=["rule", "or_far"], help="ORB stop: playbook rule or far side of the range")
    ap.add_argument("--stop-atr", type=float, default=0.0, help="v2: stop = entry -/+ this many 5m ATRs")
    ap.add_argument("--min-atr-pct", type=float, default=0.0, help="v2: skip stocks whose 5m ATR is below this %% of price")
    ap.add_argument("--cpr-on-b", action="store_true", help="v2: apply the CPR/ATR filter to setup B too")
    ap.add_argument("--v2", action="store_true", help="v2 preset (research/LOSS_ANALYSIS.md)")
    ap.add_argument("--veto-htf", action="store_true", help="v3 veto O3: skip trades against the daily/weekly trend")
    ap.add_argument("--v3", action="store_true", help="v3 preset = v2 + veto O3 (research/TRADE_REVIEW.md)")
    ap.add_argument("--start", default="", help="first day of 5m data to use (YYYY-MM-DD)")
    ap.add_argument("--end", default="", help="last day of 5m data to use (YYYY-MM-DD)")
    ap.add_argument("--max-open", type=int, default=3)
    ap.add_argument("--max-trades", type=int, default=5)
    ap.add_argument("--day-stop-r", type=float, default=2.0)
    a = ap.parse_args()
    if a.v3:
        a.v2 = a.veto_htf = True
    if a.v2:
        a.rs = a.idx_bias = a.daily = False
        a.cpr_max, a.min_atr_pct, a.stop_atr, a.room, a.cpr_on_b = 0.25, 0.4, 2.0, 0.0, True
    os.makedirs(a.out, exist_ok=True)

    nf = load(os.path.join(a.data, "5m", "^NSEI.csv"))
    idx = pd.DataFrame({"ic": nf.Close, "ie21": ema(nf.Close, 21)})
    idx["iopen"] = nf.Open.groupby(nf.index.normalize()).transform("first")

    syms = [s.strip() for s in open(a.universe) if s.strip()]
    trades, nsig = [], 0
    for s in syms:
        p = os.path.join(a.data, "5m", f"{s}.csv")
        if not os.path.exists(p):
            continue
        try:
            d = signals(prepare(s, a, idx), a)
        except Exception as e:
            print("skip", s, e)
            continue
        nsig += int(d[["aL", "aS", "bL", "bS"]].to_numpy().sum())
        trades += simulate(s, d, a)
    tr = pd.DataFrame(trades)
    risk_rs = a.capital * a.risk / 100
    if tr.empty:
        print("no trades"); return
    tr.to_csv(os.path.join(a.out, "all_signals_trades.csv"), index=False)
    pf = portfolio(tr, a)
    pf.to_csv(os.path.join(a.out, "portfolio_trades.csv"), index=False)
    # per-stock (Pine-equivalent) stats with the same sizing and costs
    every = portfolio(tr, argparse.Namespace(**{**vars(a), "max_open": 10**6, "max_trades": 10**6, "day_stop_r": 10**6}))
    rows = [{"view": "every signal (Pine, one chart per stock)", **stats(every, risk_rs)},
            {"view": "desk portfolio (limits + breaker)", **stats(pf, risk_rs)}]
    for (st, sd), g in every.groupby(["setup", "side"]):
        rows.append({"view": f"every signal: setup {st} {sd}", **stats(g, risk_rs)})
    S = pd.DataFrame(rows)
    S.to_csv(os.path.join(a.out, "summary.csv"), index=False)
    days = pd.to_datetime(pf.day) if not pf.empty else pd.Series(dtype="datetime64[ns]")
    print(f"days {tr.day.nunique()} | raw signal bars {nsig} | simulated trades {len(tr)}")
    print(S.to_string(index=False))
    if not pf.empty:
        daily = pf.groupby("day").pnl_rs.sum()
        eq = a.capital + daily.cumsum()
        print(f"\nPortfolio: Rs {a.capital:,.0f} -> Rs {eq.iloc[-1]:,.0f} ({100 * (eq.iloc[-1] / a.capital - 1):+.2f}%), "
              f"max DD {100 * (eq / eq.cummax().clip(lower=a.capital) - 1).min():.2f}%, "
              f"trading days {len(daily)}, winning days {(daily > 0).sum()}")
        print("exit reasons:", pf.reason.value_counts().to_dict())
        daily.to_csv(os.path.join(a.out, "daily_pnl.csv"))


if __name__ == "__main__":
    main()
