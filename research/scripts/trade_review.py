"""Adversarial trade review ("prove it or don't take it") for the intraday strategy.

Builds a multi-timeframe evidence sheet for any trade using only data available at the close of
the signal candle (weekly / daily / 1h / 15m CPR / 5m / Nifty / sector peers), plus a separate
hindsight block (MFE/MAE, after-exit move, wick-or-close stop). See research/TRADE_REVIEW.md.
"""

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
import intraday_backtest as ib                                       # noqa: E402
import loss_forensics as lf                                          # noqa: E402


def wilder_rsi(c, n=14):
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


class Context:
    """everything the evidence builder needs, computed once"""

    def __init__(self, data, bars, metadata):
        from lp.data import load_universe
        from lp.sectors import sector_group
        self.data, self.bars = data, bars
        self.sector = {s: sector_group(l) for s, l in load_universe(metadata).items()}
        self.daily, self.hourly = {}, {}
        n = ib.load(os.path.join(data, "1d", "^NSEI.csv"))
        self.nifty_d = pd.DataFrame({"c": n.Close, "e20": ib.ema(n.Close, 20)})
        # peer panel: each stock's return since today's open, on the 5m grid
        self.ret_open = pd.DataFrame({s: d.Close / d.day_open - 1 for s, d in bars.items()})

    def day_frame(self, s):
        if s not in self.daily:
            d = ib.load(os.path.join(self.data, "1d", f"{s}.csv"))
            c = d.Close
            tr = pd.concat([d.High - d.Low, (d.High - c.shift()).abs(), (d.Low - c.shift()).abs()], axis=1).max(axis=1)
            d["e20"], d["e50"], d["e200"] = ib.ema(c, 20), ib.ema(c, 50), ib.ema(c, 200)
            d["rsi"], d["atr"] = wilder_rsi(c), tr.ewm(alpha=1 / 14, adjust=False).mean()
            d.index = d.index.normalize()
            self.daily[s] = d
        return self.daily[s]

    def hour_frame(self, s):
        """60-minute candles from 09:15 built from the 5m bars, with the time each candle completes"""
        if s not in self.hourly:
            d = self.bars[s]
            mins = (d.index.hour * 60 + d.index.minute) - (9 * 60 + 15)
            key = d.day + pd.to_timedelta((mins // 60) * 60 + 9 * 60 + 15, unit="m")
            h = d.groupby(key).agg(Open=("Open", "first"), High=("High", "max"), Low=("Low", "min"),
                                   Close=("Close", "last"), last=("Close", lambda x: x.index[-1]))
            h["done_at"] = h["last"] + pd.Timedelta(minutes=5)
            h["e20"], h["rsi"] = ib.ema(h.Close, 20), wilder_rsi(h.Close)
            self.hourly[s] = h
        return self.hourly[s]


def _room(levels, fill, side, R):
    """distance in R to the nearest level in the trade's way (cap 10R)"""
    lv = [x for x in levels if np.isfinite(x) and side * (x - fill) > 0]
    if not lv:
        return 10.0
    near = min(lv) if side == 1 else max(lv)
    return min(10.0, side * (near - fill) / R)


def evidence(ctx, s, i, side, setup, fill, stop, j=None, exit_bar=None):
    d = ctx.bars[s]
    r = d.iloc[i]
    ts = d.index[i]
    sig_close = ts + pd.Timedelta(minutes=5)
    R = abs(fill - stop)
    A = r.atr
    day = pd.Timestamp(r.day)
    f = {"symbol": s, "setup": setup, "side": side, "signal": ts, "sector": ctx.sector.get(s, "Other")}

    # ---------------- weekly (completed days before today)
    dd = ctx.day_frame(s)
    past = dd[dd.index < day]
    w = past.Close.resample("W-FRI").last().dropna()
    wh, wl = past.High.resample("W-FRI").max().dropna(), past.Low.resample("W-FRI").min().dropna()
    if len(w) >= 22:
        e20w, e10w = ib.ema(w, 20).iloc[-1], ib.ema(w, 10).iloc[-1]
        f["w_above_20w"] = side * (w.iloc[-1] - e20w) > 0
        f["w_10_vs_20"] = side * (e10w - e20w) > 0
        f["w_hh_hl"] = (wh.iloc[-1] > wh.iloc[-2] and wl.iloc[-1] > wl.iloc[-2]) if side == 1 else \
                       (wh.iloc[-1] < wh.iloc[-2] and wl.iloc[-1] < wl.iloc[-2])
        f["w_room_R"] = _room([wh.iloc[-1]] if side == 1 else [wl.iloc[-1]], fill, side, R)
    hi52, lo52 = past.High.iloc[-252:].max(), past.Low.iloc[-252:].min()
    f["dist_52w_pct"] = 100 * ((fill / hi52 - 1) if side == 1 else (fill / lo52 - 1))

    # ---------------- daily (previous completed day)
    p = past.iloc[-1]
    f["d_trend_score"] = side * (np.sign(p.Close - p.e20) + np.sign(p.e20 - p.e50) + np.sign(p.e50 - p.e200))
    f["d_e20_slope"] = side * 100 * (past.e20.iloc[-1] / past.e20.iloc[-6] - 1)
    f["d_rsi"] = p.rsi
    f["d_rsi_side"] = p.rsi if side == 1 else 100 - p.rsi
    rng = (past.High - past.Low).iloc[-7:]
    f["d_nr7"] = rng.iloc[-1] == rng.min()
    f["d_inside"] = past.High.iloc[-1] <= past.High.iloc[-2] and past.Low.iloc[-1] >= past.Low.iloc[-2]
    f["gap_pct"] = side * 100 * (r.day_open / p.Close - 1)
    f["beyond_pd_extreme"] = (fill > p.High) if side == 1 else (fill < p.Low)
    f["against_pd_extreme"] = (fill < p.Low) if side == 1 else (fill > p.High)
    levels_d = [p.High, past.High.iloc[-20:].max(), past.High.iloc[-60:].max()] if side == 1 else \
               [p.Low, past.Low.iloc[-20:].min(), past.Low.iloc[-60:].min()]
    f["d_room_R"] = _room(levels_d, fill, side, R)
    f["d_atr_pct"] = 100 * p.atr / p.Close

    # ---------------- 1 hour (completed candles only)
    h = ctx.hour_frame(s)
    hd = h[h.done_at <= sig_close]
    if len(hd) >= 25:
        lh = hd.iloc[-1]
        f["h_above_20"] = side * (lh.Close - lh.e20) > 0
        f["h_rsi_side"] = lh.rsi if side == 1 else 100 - lh.rsi
        hh = hd.iloc[-40:]
        piv_hi = hh.High[(hh.High.shift(1) < hh.High) & (hh.High.shift(-1) < hh.High)]
        piv_lo = hh.Low[(hh.Low.shift(1) > hh.Low) & (hh.Low.shift(-1) > hh.Low)]
        f["h_room_R"] = _room(list(piv_hi.iloc[-3:]) if side == 1 else list(piv_lo.iloc[-3:]), fill, side, R)

    # ---------------- 15m structure: CPR and opening range
    piv = (r.pdh + r.pdl + r.pdc) / 3
    bc = (r.pdh + r.pdl) / 2
    tc = 2 * piv - bc
    f["cpr_width"] = r.cprw
    f["vs_cpr"] = side * (fill - (max(tc, bc) if side == 1 else min(tc, bc))) / A
    r2 = piv + (r.pdh - r.pdl)
    s2 = piv - (r.pdh - r.pdl)
    f["cpr_room_R"] = _room([r.r1, r2] if side == 1 else [r.s1, s2], fill, side, R)
    f["or_width_atr"] = (r.orh - r.orl) / A

    # ---------------- index and sector
    f["nifty_aligned"] = side * (r.ic - r.ie21) > 0
    f["nifty_day_ret"] = side * 100 * (r.ic / r.iopen - 1)
    nd = ctx.nifty_d[ctx.nifty_d.index < day]
    f["nifty_daily_aligned"] = side * (nd.c.iloc[-1] - nd.e20.iloc[-1]) > 0
    row = ctx.ret_open.loc[ts] if ts in ctx.ret_open.index else None
    if row is not None:
        peers = [x for x, g in ctx.sector.items() if g == f["sector"] and x != s and x in row.index]
        pm = row[peers].median() if peers else np.nan
        f["sector_peer_ret"] = side * 100 * pm if np.isfinite(pm) else np.nan
        f["breadth_ret"] = side * 100 * row.drop(s, errors="ignore").median()
        f["rs_vs_sector"] = side * 100 * (row[s] - pm) if np.isfinite(pm) else np.nan

    # ---------------- 5m execution
    c, o, hi, lo = r.Close, r.Open, r.High, r.Low
    rg = max(hi - lo, 1e-9)
    f["dist_vwap_atr"] = side * (c - r.vwap) / A
    f["vwap_slope_atr"] = side * (r.vwap - d.vwap.iat[max(i - 6, 0)]) / A
    f["ema_gap_atr"] = side * (r.ema9 - r.ema21) / A
    f["rsi5"] = r.rsi if side == 1 else 100 - r.rsi
    f["rsi5_slope"] = side * (r.rsi - d.rsi.iat[i - 3])
    win = d.iloc[max(i - 12, 0):i]
    win = win[win.day == r.day]
    if len(win) >= 4:
        if side == 1:
            f["rsi_divergence"] = hi >= win.High.max() and r.rsi < win.rsi.max() - 5
        else:
            f["rsi_divergence"] = lo <= win.Low.min() and r.rsi > win.rsi.min() + 5
    f["vol_ratio"] = r.Volume / r.volavg
    same = d[(d.bar_n == r.bar_n) & (d.day < r.day)].groupby("day").size()
    cumv = d[(d.day == r.day) & (d.index <= ts)].Volume.sum()
    prior = d[(d.day < r.day) & (d.bar_n <= r.bar_n)].groupby("day").Volume.sum().iloc[-20:]
    f["cum_rvol"] = cumv / prior.mean() if len(prior) >= 5 else np.nan
    f["body_pct"] = abs(c - o) / rg
    f["wick_against_pct"] = ((hi - max(o, c)) if side == 1 else (min(o, c) - lo)) / rg
    f["close_pos"] = ((c - lo) if side == 1 else (hi - c)) / rg
    f["sig_marubozu"] = f["body_pct"] >= 0.8
    f["sig_doji"] = f["body_pct"] <= 0.15
    f["sig_inside"] = hi <= d.High.iat[i - 1] and lo >= d.Low.iat[i - 1]
    run = 0
    for k in range(i, max(i - 10, 0), -1):
        if d.day.iat[k] != r.day or side * (d.Close.iat[k] - d.Open.iat[k]) <= 0:
            break
        run += 1
    f["consec_candles"] = run
    f["dist_ema9_atr"] = side * (c - r.ema9) / A
    f["move_since_or_atr"] = side * (c - (r.orh if side == 1 else r.orl)) / A
    f["move_since_open_atr"] = side * (c - r.day_open) / A
    sw = d.iloc[max(i - 12, 0):i + 1]
    sw = sw[sw.day == r.day]
    swing = sw.Low.min() if side == 1 else sw.High.max()
    f["stop_beyond_swing"] = side * (swing - stop) > 0
    f["time"] = r.t
    f["atr5_pct"] = 100 * A / c
    f["stop_pct"] = 100 * R / fill

    # ---------------- hindsight (never used for verdicts or rules)
    if j is not None and exit_bar is not None:
        path = d.iloc[j:exit_bar + 1]
        fav = ((path.High - fill) if side == 1 else (fill - path.Low)) / R
        adv = ((fill - path.Low) if side == 1 else (path.High - fill)) / R
        f["H_mfe_R"], f["H_mae_R"] = fav.max(), adv.max()
        f["H_min_to_mfe"] = (fav.idxmax() - d.index[j]).total_seconds() / 60
        post = d.iloc[exit_bar + 1:exit_bar + 13]
        post = post[post.day == r.day]
        f["H_after_exit_fav_R"] = (((post.High.max() - fill) if side == 1 else (fill - post.Low.min())) / R) if len(post) else np.nan
        xb = d.iloc[exit_bar]
        f["H_stop_by_close"] = side * (xb.Close - stop) <= 0
    return f


# ----------------------------------------------------------------------------- the CRO's objections
# Thresholds fixed from market logic before looking at outcomes (see TRADE_REVIEW.md section 2).
OBJECTIONS = {
    "O1 no room": ("Less than 1R to the next daily / CPR / 1h level in the trade's way",
                   lambda f: min(f.get("d_room_R", 10), f.get("cpr_room_R", 10), f.get("h_room_R", 10)) < 1.0),
    "O2 extended": ("Chasing: >3 ATR from VWAP, >2 ATR from the 9 EMA, or 4+ candles in a row",
                    lambda f: f["dist_vwap_atr"] > 3 or f["dist_ema9_atr"] > 2 or f["consec_candles"] >= 4),
    "O3 HTF against": ("Daily EMA stack against the trade, or price on the wrong side of the 20-week EMA",
                       lambda f: f["d_trend_score"] <= -1 or f.get("w_above_20w") is False),
    "O4 1h against": ("Last completed 1h candle on the wrong side of the 1h 20 EMA, or 1h RSI stretched (>75 / <25)",
                      lambda f: f.get("h_above_20") is False or f.get("h_rsi_side", 50) > 75),
    "O5 index against": ("Nifty on the wrong side of its 21 EMA, or Nifty down >0.3% on the day against the trade",
                         lambda f: (not f["nifty_aligned"]) or f["nifty_day_ret"] < -0.3),
    "O6 sector against": ("Sector peers moving the other way since the open",
                          lambda f: f.get("sector_peer_ret", 0) < 0),
    "O7 rejection candle": ("Signal candle shows rejection: wick against >35% of range or close in the weak 40%",
                            lambda f: f["wick_against_pct"] > 0.35 or f["close_pos"] < 0.6),
    "O8 divergence": ("New 5m extreme with RSI weaker than the recent RSI extreme",
                      lambda f: bool(f.get("rsi_divergence", False))),
    "O9 thin participation": ("Day's cumulative volume < 1.2x normal for the time of day",
                              lambda f: f.get("cum_rvol", 9) < 1.2),
    "O10 stop inside structure": ("2xATR stop does not clear the last 12-candle swing",
                                  lambda f: not f["stop_beyond_swing"]),
    "O11 daily stretched": ("Daily RSI already >75 (long) / <25 (short)",
                            lambda f: f["d_rsi_side"] > 75),
}
SUPPORTS = {
    "S1 full daily trend": lambda f: f["d_trend_score"] == 3,
    "S2 weekly trend": lambda f: f.get("w_above_20w") is True and f.get("w_10_vs_20") is True,
    "S3 1h with trend": lambda f: f.get("h_above_20") is True and f.get("h_rsi_side", 50) <= 75,
    "S4 index + sector with trade": lambda f: f["nifty_aligned"] and f.get("sector_peer_ret", 0) > 0,
    "S5 leader in its sector": lambda f: f.get("rs_vs_sector", 0) >= 1.0,
    "S6 room >= 2R": lambda f: min(f.get("d_room_R", 10), f.get("cpr_room_R", 10), f.get("h_room_R", 10)) >= 2,
    "S7 strong candle": lambda f: f["close_pos"] >= 0.75 and f["wick_against_pct"] <= 0.2,
}


def verdict(f):
    obj = [k for k, (_, fn) in OBJECTIONS.items() if fn(f)]
    sup = [k for k, fn in SUPPORTS.items() if fn(f)]
    score = int(np.clip(60 - 10 * len(obj) + 7 * len(sup), 0, 100))
    v = "APPROVE" if score >= 65 else ("APPROVE WITH CONDITIONS" if score >= 45 else "REJECT")
    return obj, sup, score, v
