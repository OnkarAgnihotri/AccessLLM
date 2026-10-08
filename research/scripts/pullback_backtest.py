"""Daily chart pattern + pullback-only swing strategy (1-4 week holds), long only.

Rules (fixed before testing, see research/PULLBACK_STRATEGY.md):

Daily chart pattern (only data up to the signal close):
  * swing points: a high/low that is the extreme of the 5 bars on each side, known 5 bars later
  * UPTREND: last two confirmed swing highs rising AND last two swing lows rising,
             close > 50 SMA > 200 SMA, 6-month relative strength in the top 40%
  * Pattern P1 "trend pullback": current up-leg (last swing low L0 -> highest high since, Hmax) is at least
             2 ATR tall, Hmax set 3-15 bars ago, today's low retraces 38.2-61.8% of the leg or tags the 20 EMA,
             and stays above L0 (structure intact)
  * Pattern P2 "breakout retest": a close above the prior 60-day high (level R) 3-20 bars ago, today's low
             back within 0.5 ATR of R and close not more than 0.5 ATR below R
Entry - pullbacks only:
  * daily trigger (A): pattern active today or yesterday, today closes green and above yesterday's high
             -> buy next open
  * 1h trigger (B): pattern active at yesterday's close; today the first 1h candle (from 10:15) that closes
             above the previous 1h high and above the 1h 20 EMA, with the day's low still above L0 -> buy at that close
Risk: stop = lowest low of the last 3 days - 0.25 ATR; first target T1 = Hmax; require T1 >= entry + 1.5R
Exits: 50% at T1 then stop to entry; rest trails 3 ATR below the highest close; forced exit after 20 days
Portfolio: 1% of equity at risk per trade, position <= 20% of equity, max 10 positions, max 3 per industry,
           new entries only when Nifty > 200 SMA, median turnover >= Rs 1 cr. Delivery costs + slippage.
"""

import argparse
import math
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from lp.config import load_config                                       # noqa: E402
from lp.data import load_panels                                          # noqa: E402
from lp import indicators as ind, costs                                  # noqa: E402

W = 5


def pattern_state(O, H, L, C, A, E20, S50, S200, RS, LIQ, REG):
    """per-stock arrays: pattern flag (1 = P1, 2 = P2, 0 none), leg low L0 and Hmax known at each close"""
    n = len(C)
    pat = np.zeros(n, dtype=np.int8)
    l0_at = np.full(n, np.nan)
    hmax_at = np.full(n, np.nan)
    sh, sl = [], []                     # confirmed swing highs / lows: (index, value)
    bo_level, bo_idx = np.nan, -999
    for t in range(n):
        c = t - W                       # the bar that becomes confirmable today
        if c >= W and np.isfinite(H[c]):
            win_h, win_l = H[c - W:t + 1], L[c - W:t + 1]
            if H[c] == np.nanmax(win_h):
                sh.append((c, H[c]))
            if L[c] == np.nanmin(win_l):
                sl.append((c, L[c]))
        if t < 260 or not np.isfinite(C[t]) or not np.isfinite(A[t]):
            continue
        prior60 = np.nanmax(H[t - 60:t])
        if C[t] > prior60 and (t - bo_idx) > 20:
            bo_level, bo_idx = prior60, t
        if len(sh) < 2 or len(sl) < 2:
            continue
        up = sh[-1][1] > sh[-2][1] and sl[-1][1] > sl[-2][1] and C[t] > S50[t] > S200[t] and RS[t] >= 60
        if not (up and LIQ[t] and REG[t]):
            continue
        i0, v0 = sl[-1]
        seg = H[i0:t + 1]
        hm_rel = int(np.nanargmax(seg))
        hmax, hidx = seg[hm_rel], i0 + hm_rel
        l0_at[t], hmax_at[t] = v0, hmax
        leg = hmax - v0
        if leg >= 2 * A[t] and 3 <= t - hidx <= 15 and L[t] > v0:
            retr = (hmax - L[t]) / leg
            if 0.382 <= retr <= 0.618 or L[t] <= E20[t]:
                pat[t] = 1
                continue
        if np.isfinite(bo_level) and 3 <= t - bo_idx <= 20 and L[t] <= bo_level + 0.5 * A[t] \
                and C[t] >= bo_level - 0.5 * A[t] and L[t] > v0:
            pat[t] = 2
    return pat, l0_at, hmax_at


def prepare(panels, nifty, min_turn_cr=1.0):
    o, h, l, c, v = (panels[k] for k in ("Open", "High", "Low", "Close", "Volume"))
    atr = ind.atr(h, l, c, 14)
    e20 = c.ewm(span=20, adjust=False).mean()
    s50, s200 = ind.sma(c, 50), ind.sma(c, 200)
    rs = ind.rs_percentile(c, 126)
    liq = ind.median_turnover(c, v, 20) / 1e7 >= min_turn_cr
    n = nifty.reindex(c.index).ffill()
    reg = (n > ind.sma(n, 200)).to_numpy()
    P = {k: np.zeros(c.shape, dtype=np.int8) for k in ("pat",)}
    L0 = np.full(c.shape, np.nan)
    HM = np.full(c.shape, np.nan)
    for j, s in enumerate(c.columns):
        p, a, b = pattern_state(o[s].to_numpy(float), h[s].to_numpy(float), l[s].to_numpy(float), c[s].to_numpy(float),
                                atr[s].to_numpy(float), e20[s].to_numpy(float), s50[s].to_numpy(float), s200[s].to_numpy(float),
                                rs[s].to_numpy(float), liq[s].to_numpy(bool), reg)
        P["pat"][:, j], L0[:, j], HM[:, j] = p, a, b
    return dict(pat=P["pat"], l0=L0, hmax=HM, atr=atr.to_numpy(float), e20=e20.to_numpy(float))


def daily_signals(panels, st):
    O, H, L, C = (panels[k].to_numpy(float) for k in ("Open", "High", "Low", "Close"))
    pat = st["pat"]
    active = (pat > 0) | np.vstack([np.zeros((1, pat.shape[1]), bool), pat[:-1] > 0])
    prevH = np.vstack([np.full((1, H.shape[1]), np.nan), H[:-1]])
    trig = active & (C > prevH) & (C > O)
    low3 = pd.DataFrame(L).rolling(3).min().to_numpy()
    stop = low3 - 0.25 * st["atr"]
    hm = np.where(np.isfinite(st["hmax"]), st["hmax"],
                  np.vstack([np.full((1, H.shape[1]), np.nan), st["hmax"][:-1]]))
    ok = trig & np.isfinite(stop) & np.isfinite(hm) & (hm - C >= 1.5 * (C - stop)) & (C > stop)
    pat_used = np.where(pat > 0, pat, np.vstack([np.zeros((1, pat.shape[1]), np.int8), pat[:-1]]))
    return ok, stop, hm, pat_used


def run(panels, st, groups, cfg, start, end, mode="daily", hourly=None, capital=500000.0, risk=0.01,
        slots=10, per_ind=3, max_hold=20):
    dates = panels["Close"].index
    days = dates[(dates >= pd.Timestamp(start)) & (dates <= pd.Timestamp(end))]
    names = list(panels["Close"].columns)
    O, H, L, C = (panels[k].to_numpy(float) for k in ("Open", "High", "Low", "Close"))
    A = st["atr"]
    sig, stop_arr, tgt_arr, pat_used = daily_signals(panels, st)
    cash, pos, trades, curve, pending = capital, {}, [], [], []

    def sell(p, qty, px, day, reason, market=True):
        nonlocal cash
        qty = min(qty, p["qty_open"])
        fill = costs.sell_fill(px, cfg) if market else px
        val = fill * qty
        ch = costs.sell_cost(val, cfg)
        cash += val - ch
        p["proceeds"] += val - ch
        p["qty_open"] -= qty
        if p["qty_open"] == 0:
            pnl = p["proceeds"] - p["cost"]
            trades.append(dict(mode=mode, symbol=p["sym"], industry=p["ind"], pattern="P1 trend pullback" if p["pat"] == 1 else "P2 breakout retest",
                               signal_date=p["sig"].date(), entry_date=p["d0"].date(), entry_time=p.get("t0", ""), exit_date=day.date(),
                               days_held=p["held"], entry=round(p["px"], 2), stop0=round(p["stop0"], 2), t1=round(p["t1"], 2),
                               t1_hit=p["t1_done"], exit=round(fill, 2), qty=p["qty"], invested=round(p["cost"], 2), pnl=round(pnl, 2),
                               return_pct=round(100 * pnl / p["cost"], 2), r_multiple=round(pnl / p["risk_rs"], 2), exit_reason=reason))

    def open_pos(s, j, px, stop, t1, pat, sigday, day, eq, t0=""):
        nonlocal cash
        fill = costs.buy_fill(px, cfg)
        if fill <= stop or fill >= t1:
            return
        per = sum(1 for p in pos.values() if p["ind"] == groups.get(s, "Other"))
        if len(pos) >= slots or s in pos or per >= per_ind:
            return
        qty = math.floor(min(eq * risk / (fill - stop), 0.2 * eq / fill, cash / (fill * 1.003)))
        if qty < 1 or qty * fill < 10000:                 # no token positions: fixed charges would dominate
            return
        cost = fill * qty + costs.buy_cost(fill * qty, cfg)
        cash -= cost
        pos[s] = dict(sym=s, ind=groups.get(s, "Other"), px=fill, qty=qty, qty_open=qty, cost=cost, proceeds=0.0, stop=stop,
                      stop0=stop, t1=t1, t1_done=False, hc=fill, held=0, d0=day, sig=sigday, pat=pat, t0=t0,
                      risk_rs=qty * (fill - stop))

    for day in days:
        i = dates.get_loc(day)
        eq_prev = curve[-1]["equity"] if curve else capital
        # gaps at the open
        for s in list(pos):
            p, j = pos[s], names.index(s)
            o = O[i, j]
            if np.isnan(o):
                continue
            if o <= p["stop"]:
                sell(p, p["qty_open"], o, day, "breakeven (gap)" if p["t1_done"] else "stop (gap)")
                del pos[s]
            elif not p["t1_done"] and o >= p["t1"]:
                sell(p, p["qty"] // 2, o, day, "T1", market=False)
                p["t1_done"], p["t1_day"] = True, day
                p["stop"] = max(p["stop"], p["px"])
                if p["qty_open"] == 0:
                    del pos[s]
        # entries
        if mode == "daily":
            for s, j, stop, t1, pat, sd in pending:
                open_pos(s, j, O[i, j], stop, t1, pat, sd, day, eq_prev)
        elif mode == "hourly" and hourly is not None:
            yi = i - 1
            cand = np.flatnonzero(st["pat"][yi] > 0) if yi >= 0 else []
            hits = []
            for j in cand:
                s = names[j]
                hb = hourly.get(s)
                if hb is None:
                    continue
                bars = hb.get(day.normalize())
                if bars is None or len(bars) < 3:
                    continue
                l0, hm = st["l0"][yi, j], st["hmax"][yi, j]
                low3 = np.nanmin(L[max(yi - 1, 0):yi + 1, j])
                day_low = np.inf
                for k in range(len(bars)):
                    b = bars.iloc[k]
                    day_low = min(day_low, b.Low)
                    if day_low <= l0:
                        break
                    if k == 0:
                        continue
                    if b.Close > bars.High.iloc[k - 1] and b.Close > b.e20:
                        stop = min(day_low, low3) - 0.25 * A[yi, j]
                        if hm - b.Close >= 1.5 * (b.Close - stop) and b.Close > stop:
                            hits.append((bars.index[k], s, j, b.Close, stop, hm, int(st["pat"][yi, j]), bars.Low.iloc[k + 1:].min()
                                         if k + 1 < len(bars) else np.inf))
                        break
            for t0, s, j, px, stop, hm, pat, later_low in sorted(hits):
                open_pos(s, j, px, stop, hm, pat, dates[i - 1], day, eq_prev, t0=str(t0)[11:16])
                if s in pos and later_low <= pos[s]["stop"]:
                    p = pos[s]
                    sell(p, p["qty_open"], p["stop"], day, "stop (entry day)")
                    del pos[s]
        # intraday stop / T1 on daily bar (entry-day bars for daily mode handled here too)
        for s in list(pos):
            p, j = pos[s], names.index(s)
            if p.get("t0") and p["d0"] == day:
                continue                                 # hourly entry: rest of the day already checked
            if np.isnan(L[i, j]):
                continue
            if not p["t1_done"]:
                if L[i, j] <= p["stop"]:
                    sell(p, p["qty_open"], p["stop"], day, "stop")
                    del pos[s]
                    continue
                if H[i, j] >= p["t1"]:
                    sell(p, p["qty"] // 2, p["t1"], day, "T1", market=False)
                    p["t1_done"], p["t1_day"] = True, day
                    p["stop"] = max(p["stop"], p["px"])
                    if p["qty_open"] == 0:
                        del pos[s]
                        continue
            elif p.get("t1_day") != day and L[i, j] <= p["stop"]:
                sell(p, p["qty_open"], p["stop"], day, "breakeven" if p["stop"] <= p["px"] * 1.0001 else "trail stop")
                del pos[s]
        # close
        for s in list(pos):
            p, j = pos[s], names.index(s)
            c = C[i, j]
            if np.isnan(c):
                continue
            p["held"] += 1
            p["last"] = c
            if p["held"] >= max_hold:
                sell(p, p["qty_open"], c, day, "time (20 days)")
                del pos[s]
                continue
            p["hc"] = max(p["hc"], c)
            if p["t1_done"]:
                p["stop"] = max(p["stop"], p["hc"] - 3 * A[i, j])
        inv = sum(p["qty_open"] * p.get("last", p["px"]) for p in pos.values())
        curve.append(dict(date=day, equity=cash + inv, cash=cash, positions=len(pos)))
        pending = []
        if mode == "daily":
            js = np.flatnonzero(sig[i])
            for j in sorted(js, key=lambda j: -(tgt_arr[i, j] - C[i, j]) / max(C[i, j] - stop_arr[i, j], 1e-9)):
                pending.append((names[j], j, stop_arr[i, j], tgt_arr[i, j], int(pat_used[i, j]), day))
    last = days[-1]
    for s in list(pos):
        sell(pos[s], pos[s]["qty_open"], pos[s].get("last", pos[s]["px"]), last, "end of test")
    eq = pd.DataFrame(curve).set_index("date")
    eq.iloc[-1, eq.columns.get_loc("equity")] = cash
    return pd.DataFrame(trades), eq


def load_hourly(folder, names):
    out = {}
    for s in names:
        p = os.path.join(folder, f"{s}.csv")
        if not os.path.exists(p):
            continue
        d = pd.read_csv(p)
        d["Date"] = pd.to_datetime(d.Date, utc=True, format="mixed").dt.tz_convert("Asia/Kolkata").dt.tz_localize(None) \
            if d.Date.astype(str).str.contains(r"\+").any() else pd.to_datetime(d.Date, format="mixed")
        d = d.dropna(subset=["Close"]).set_index("Date").sort_index()
        d = d[~d.index.duplicated()]
        d["e20"] = d.Close.ewm(span=20, adjust=False).mean()
        out[s] = {k: g for k, g in d.groupby(d.index.normalize())}
    return out


def stats(tr, eq, nifty):
    e = eq.equity
    yrs = (e.index[-1] - e.index[0]).days / 365.25
    r = e.pct_change().dropna()
    nb = nifty.reindex(e.index).ffill()
    o = dict(start=str(e.index[0].date()), end=str(e.index[-1].date()), final=round(e.iloc[-1]),
             total_ret=round(100 * (e.iloc[-1] / e.iloc[0] - 1), 1), cagr=round(100 * ((e.iloc[-1] / e.iloc[0]) ** (1 / yrs) - 1), 1),
             max_dd=round(100 * (e / e.cummax() - 1).min(), 1), sharpe=round(np.sqrt(252) * r.mean() / r.std(), 2) if r.std() > 0 else np.nan,
             nifty_ret=round(100 * (nb.iloc[-1] / nb.iloc[0] - 1), 1))
    if len(tr):
        w = tr.pnl > 0
        o.update(trades=len(tr), win=round(100 * w.mean(), 1), avg_r=round(tr.r_multiple.mean(), 2), avg_ret=round(tr.return_pct.mean(), 2),
                 pf=round(tr.pnl[w].sum() / -tr.pnl[~w].sum(), 2) if (~w).any() else np.inf, t1_hit=round(100 * tr.t1_hit.mean(), 1),
                 avg_days=round(tr.days_held.mean(), 1))
    return o


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data"); ap.add_argument("symbols"); ap.add_argument("industry"); ap.add_argument("out")
    ap.add_argument("--start", required=True); ap.add_argument("--end", required=True)
    ap.add_argument("--slippage", type=float, default=0.10)
    ap.add_argument("--mode", default="daily", choices=["daily", "hourly"])
    ap.add_argument("--hourly-dir", default="")
    ap.add_argument("--no-regime", action="store_true")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    syms = [s.strip() for s in open(a.symbols) if s.strip()]
    m = pd.read_csv(a.industry)
    groups = dict(zip(m.symbol, m.industry))
    panels, nifty = load_panels(syms, a.data, "^NSEI", min_bars=260, log=lambda *x: None)
    if a.no_regime:
        nifty = nifty * 0 + 1e9
        nifty.iloc[:200] = np.nan
    st = prepare(panels, nifty)
    cfg = load_config(slippage_pct=a.slippage, brokerage_per_order=20.0)
    hourly = load_hourly(a.hourly_dir, list(panels["Close"].columns)) if a.mode == "hourly" else None
    tr, eq = run(panels, st, groups, cfg, a.start, a.end, mode=a.mode, hourly=hourly)
    tag = f"{a.mode}"
    tr.to_csv(os.path.join(a.out, f"{tag}_trades.csv"), index=False)
    eq.to_csv(os.path.join(a.out, f"{tag}_equity.csv"))
    s = stats(tr, eq, nifty if not a.no_regime else load_panels(syms[:1], a.data, "^NSEI", min_bars=1, log=lambda *x: None)[1])
    pd.DataFrame([s]).to_csv(os.path.join(a.out, f"{tag}_summary.csv"), index=False)
    print(s)
    if len(tr):
        print(tr.groupby("pattern").agg(n=("pnl", "size"), win=("pnl", lambda x: round(100 * (x > 0).mean())), pnl=("pnl", "sum")).round(0).to_string())
        tr["y"] = pd.to_datetime(tr.exit_date).dt.year
        print(tr.groupby("y").pnl.sum().round(0).to_dict(), tr.exit_reason.value_counts().to_dict())


if __name__ == "__main__":
    main()
