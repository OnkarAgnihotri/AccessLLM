"""Long-only swing strategies (1-4 week holds) on daily bars, portfolio-level, with Indian delivery costs.

Four strategies with parameters FIXED in advance (no tuning):
  S1 momentum breakout   - uptrend, top-20% 6m relative strength, near 52w high, 20-day breakout on 1.5x volume
  S2 trend pullback      - uptrend leader dips to the 20 EMA, RSI 40-60, reversal day (close > prior high)
  S3 weekly rotation     - every Friday buy the top-10 3m/6m momentum stocks above their 200 SMA
  S4 squeeze breakout    - uptrend, Bollinger width in the lowest 20% of 120 days, close above upper band on volume
Common rules: Nifty above its 200 SMA for new entries; median turnover >= Rs 1 cr (point in time);
enter next open; initial stop (2-3 ATR); 3-ATR chandelier trail; forced exit after 20 trading days;
10 equal-weight slots; max 3 per industry. Gaps through stops fill at the open.

Usage: python swing_backtest.py <data_dir> <symbols.txt> <industry_map.csv|-> <out_dir> --start --end [--slippage]
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

STRATS = ("S1", "S2", "S3", "S4")
NAMES = {"S1": "Momentum breakout", "S2": "Trend pullback", "S3": "Weekly momentum rotation", "S4": "Squeeze breakout"}


def build(panels, nifty, min_turn_cr=1.0):
    o, h, l, c, v = (panels[k] for k in ("Open", "High", "Low", "Close", "Volume"))
    f = {"sma50": ind.sma(c, 50), "sma200": ind.sma(c, 200), "ema20": c.ewm(span=20, adjust=False).mean(),
         "atr": ind.atr(h, l, c, 14), "rsi": ind.rsi(c, 14), "hi20": h.rolling(20).max().shift(1),
         "hi252": h.rolling(252, min_periods=200).max(), "low5": l.rolling(5).min(),
         "rs": ind.rs_percentile(c, 126), "volavg": v.rolling(20).mean().shift(1),
         "turn": ind.median_turnover(c, v, 20) / 1e7}
    sma20, sd20 = ind.sma(c, 20), c.rolling(20).std()
    f["bb_up"] = sma20 + 2 * sd20
    bbw = 4 * sd20 / sma20
    f["bbw_rank"] = bbw.rolling(120, min_periods=100).rank(pct=True)
    mom = 0.5 * (c / c.shift(63) - 1) + 0.5 * (c / c.shift(126) - 1)
    f["mom_rank"] = mom.where(c > f["sma200"]).rank(axis=1, ascending=False)
    n = nifty.reindex(c.index).ffill()
    regime = (n > ind.sma(n, 200)).values[:, None]
    liq = f["turn"] >= min_turn_cr
    up = (c > f["sma50"]) & (f["sma50"] > f["sma200"])
    base = liq & regime
    f["S1"] = base & up & (c > f["hi20"]) & (c >= 0.9 * f["hi252"]) & (v >= 1.5 * f["volavg"]) & (f["rs"] >= 80)
    f["S2"] = base & up & (f["rs"] >= 70) & (l.rolling(3).min() <= f["ema20"] * 1.01) & (f["rsi"] >= 40) & (f["rsi"] <= 60) \
        & (c > h.shift(1)) & (c > f["ema20"])
    wk = pd.Series(c.index.strftime("%G-%V"), index=c.index)
    last_of_week = wk != wk.shift(-1)                  # last trading day of each ISO week
    f["week_end"] = last_of_week
    f["S3"] = base & (c > f["sma200"]) & (f["mom_rank"] <= 10) & last_of_week.values[:, None]
    f["S4"] = base & up & (f["bbw_rank"].shift(1) <= 0.2) & (c > f["bb_up"]) & (c > f["hi20"]) & (v >= 1.5 * f["volavg"])
    f["score"] = f["rs"]
    return f


def run(panels, f, strat, groups, cfg, start, end, capital=500000.0, slots=10, per_ind=3, max_hold=20):
    dates = panels["Close"].index
    days = dates[(dates >= pd.Timestamp(start)) & (dates <= pd.Timestamp(end))]
    cols = {s: j for j, s in enumerate(panels["Close"].columns)}
    O, H, L, C = (panels[k].to_numpy(float) for k in ("Open", "High", "Low", "Close"))
    ATR, SIG, SC = f["atr"].to_numpy(float), f[strat].fillna(False).to_numpy(bool), f["score"].to_numpy(float)
    SMA50, LOW5, MR = f["sma50"].to_numpy(float), f["low5"].to_numpy(float), f["mom_rank"].to_numpy(float)
    WE = f["week_end"].to_numpy(bool)
    cash, pos, trades, curve, pending = capital, {}, [], [], []
    colnames = panels["Close"].columns

    def sell(p, px, day, reason, market=True):
        nonlocal cash
        fill = costs.sell_fill(px, cfg) if market else px
        val = fill * p["qty"]
        ch = costs.sell_cost(val, cfg)
        cash += val - ch
        pnl = val - ch - p["cost"]
        trades.append(dict(strategy=strat, symbol=p["sym"], industry=p["ind"], signal_date=p["sig"].date(), entry_date=p["d0"].date(),
                           exit_date=day.date(), days_held=p["held"], entry=round(p["px"], 2), exit=round(fill, 2), qty=p["qty"],
                           invested=round(p["cost"], 2), pnl=round(pnl, 2), return_pct=round(100 * pnl / p["cost"], 2), exit_reason=reason))

    for day in days:
        i = dates.get_loc(day)
        # open: stops gapped through
        for s in list(pos):
            p, j = pos[s], cols[s]
            if not np.isnan(O[i, j]) and O[i, j] <= p["stop"]:
                sell(p, O[i, j], day, "stop (gap)")
                del pos[s]
        # open: entries from yesterday's signals
        if pending:
            eq_prev = curve[-1]["equity"] if curve else capital
            per = {}
            for p in pos.values():
                per[p["ind"]] = per.get(p["ind"], 0) + 1
            for s, j, stop_dist in pending:
                if len(pos) >= slots:
                    break
                if s in pos or per.get(groups.get(s, "Other"), 0) >= per_ind or np.isnan(O[i, j]):
                    continue
                px = costs.buy_fill(O[i, j], cfg)
                qty = math.floor(min(eq_prev / slots, cash) / (px * 1.003))
                if qty < 1:
                    continue
                cost = px * qty + costs.buy_cost(px * qty, cfg)
                cash -= cost
                pos[s] = dict(sym=s, ind=groups.get(s, "Other"), px=px, qty=qty, cost=cost, stop=px - stop_dist,
                              hc=px, held=0, d0=day, sig=dates[i - 1])
                per[pos[s]["ind"]] = per.get(pos[s]["ind"], 0) + 1
        # intraday stop
        for s in list(pos):
            p, j = pos[s], cols[s]
            if not np.isnan(L[i, j]) and L[i, j] <= p["stop"]:
                sell(p, p["stop"], day, "stop")
                del pos[s]
        # close: time exit, strategy exits, trail update
        for s in list(pos):
            p, j = pos[s], cols[s]
            c = C[i, j]
            if np.isnan(c):
                continue
            p["held"] += 1
            p["last"] = c
            reason = None
            if p["held"] >= max_hold:
                reason = "time (20 days)"
            elif strat == "S2" and c < SMA50[i, j]:
                reason = "close below 50 SMA"
            elif strat == "S3" and WE[i] and not (MR[i, j] <= 30):
                reason = "dropped out of top 30"
            if reason:
                sell(p, c, day, reason)
                del pos[s]
                continue
            p["hc"] = max(p["hc"], c)
            p["stop"] = max(p["stop"], p["hc"] - 3 * ATR[i, j])          # chandelier, active next day
        inv = sum(p["qty"] * p.get("last", p["px"]) for p in pos.values())
        curve.append(dict(date=day, equity=cash + inv, cash=cash, positions=len(pos)))
        # queue tomorrow's entries
        pending = []
        js = np.flatnonzero(SIG[i])
        js = sorted(js, key=lambda j: -np.nan_to_num(SC[i, j]))
        for j in js:
            a = ATR[i, j]
            if np.isnan(a) or a <= 0:
                continue
            if strat == "S2":
                dist = min(max(C[i, j] - LOW5[i, j] + 0.5 * a, a), 3 * a)
            elif strat == "S3":
                dist = 3 * a
            else:
                dist = 2 * a
            pending.append((colnames[j], j, dist))
    last = days[-1]
    for s in list(pos):
        sell(pos[s], pos[s].get("last", pos[s]["px"]), last, "end of test")
    eq = pd.DataFrame(curve).set_index("date")
    eq.iloc[-1, eq.columns.get_loc("equity")] = cash
    return pd.DataFrame(trades), eq


def stats(tr, eq, nifty, ew):
    e = eq.equity
    yrs = (e.index[-1] - e.index[0]).days / 365.25
    dd = (e / e.cummax() - 1).min() * 100
    r = e.pct_change().dropna()
    nb = nifty.reindex(e.index).ffill()
    eb = ew.reindex(e.index).ffill()
    out = dict(start=str(e.index[0].date()), end=str(e.index[-1].date()), final=round(e.iloc[-1]),
               total_ret=round(100 * (e.iloc[-1] / e.iloc[0] - 1), 1), cagr=round(100 * ((e.iloc[-1] / e.iloc[0]) ** (1 / yrs) - 1), 1),
               max_dd=round(dd, 1), sharpe=round(np.sqrt(252) * r.mean() / r.std(), 2) if r.std() > 0 else np.nan,
               nifty_ret=round(100 * (nb.iloc[-1] / nb.iloc[0] - 1), 1), ew_universe_ret=round(100 * (eb.iloc[-1] / eb.iloc[0] - 1), 1),
               exposure=round(100 * (1 - (eq.cash / eq.equity)).mean(), 1))
    if len(tr):
        w = tr.pnl > 0
        out.update(trades=len(tr), win=round(100 * w.mean(), 1), avg_win=round(tr.return_pct[w].mean(), 2),
                   avg_loss=round(tr.return_pct[~w].mean(), 2), avg_trade=round(tr.return_pct.mean(), 2),
                   pf=round(tr.pnl[w].sum() / -tr.pnl[~w].sum(), 2) if (~w).any() else np.inf,
                   avg_days=round(tr.days_held.mean(), 1), charges_note="included")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data"); ap.add_argument("symbols"); ap.add_argument("industry"); ap.add_argument("out")
    ap.add_argument("--start", required=True); ap.add_argument("--end", required=True)
    ap.add_argument("--slippage", type=float, default=0.10)
    ap.add_argument("--brokerage", type=float, default=20.0)
    ap.add_argument("--capital", type=float, default=500000)
    ap.add_argument("--strategies", default=",".join(STRATS))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    syms = [s.strip() for s in open(a.symbols) if s.strip()]
    groups = {}
    if a.industry != "-":
        m = pd.read_csv(a.industry)
        groups = dict(zip(m.symbol, m.industry))
    panels, nifty = load_panels(syms, a.data, "^NSEI", min_bars=260, log=lambda *x: None)
    f = build(panels, nifty)
    c = panels["Close"]
    ew = (1 + c.pct_change(fill_method=None).clip(-0.5, 1).mean(axis=1).fillna(0)).cumprod()
    cfg = load_config(slippage_pct=a.slippage, brokerage_per_order=a.brokerage)
    rows = []
    for s in a.strategies.split(","):
        tr, eq = run(panels, f, s, groups, cfg, a.start, a.end, capital=a.capital)
        tr.to_csv(os.path.join(a.out, f"{s}_trades.csv"), index=False)
        eq.to_csv(os.path.join(a.out, f"{s}_equity.csv"))
        st = stats(tr, eq, nifty, ew)
        rows.append(dict(strategy=s, name=NAMES[s], **st))
        print(rows[-1], flush=True)
    pd.DataFrame(rows).to_csv(os.path.join(a.out, "summary.csv"), index=False)


if __name__ == "__main__":
    main()
