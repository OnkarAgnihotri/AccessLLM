r"""
A-C-B-D reversal pattern scanner - daily (1d) and intraday (1h, 2h, 4h, 30m, 15m) timeframes
Calibrated on SOLARA and SKYGOLD (daily). Intraday thresholds are scaled from the daily ones.
Supports scanning all stocks in one go via local CSVs or live Yahoo Finance batch download.

Usage (Windows):
    # 1. Hourly live scan across ALL 597 stocks in one go (default timeframe: 1h):
    python abcd_scanner.py --live

    # 2. Hourly scan on existing local CSVs in C:\Users\onkar\Desktop\Stock_data\1_H_TF:
    python abcd_scanner.py

    # 3. Daily live scan across ALL 597 stocks:
    python abcd_scanner.py --tf 1d --live

    # 3b. Stock names come from all_profile_metadata.json (auto-detected next to this script for --live;
    #     pass --metadata PATH to use another file, or to restrict a local-CSV scan to those stocks):
    python abcd_scanner.py --live --metadata all_profile_metadata.json

    # 4. Filter for specific symbols or recent candles:
    python abcd_scanner.py --symbols SKYGOLD,SOLARA --live
    python abcd_scanner.py --recent 60

    # 5. 15-minute scan (data in C:\Users\onkar\Desktop\Stock_data\15M_TF). Yahoo only serves the last
    #    60 days of 15m candles, so each --live run ADDS the new candles to the saved CSVs: run it daily and
    #    the history keeps growing. Longer 15m history (e.g. from a broker API) can be dropped into the folder.
    python abcd_scanner.py --tf 15m --live

    # 6. Backtest money settings (used for the profit/loss summary):
    python abcd_scanner.py --tf 1d --capital 500000 --risk-pct 1 --cost-pct 0.35

CSV format expected: Date,Open,High,Low,Close,Volume
    intraday: Date (or Datetime) holds date + time, e.g. 2026-09-29 09:15:00 or 2026-09-29 09:15:00+05:30
Output: abcd_results_1h.csv / abcd_results.csv in the data folder + backtest summary
        (gross and after-cost returns, and a rupee profit/loss simulation with risk-based position sizing).
"""

import argparse
import glob
import json
import os
import sys

import pandas as pd

# ----------------------------------------------------------------------------
# PARAMETERS  (tune these as you add more examples)
# ----------------------------------------------------------------------------
P = dict(
    # swing detection
    a_pivot_window=20,          # A must be the highest high within +/- this many bars
    b_pivot_window=10,          # B must be the highest high within +/- this many bars
    max_cross_bars=15,          # 9 SMA must cross below 20 SMA within this many bars after A and after B

    # distances (candles, both points included)
    ab_min=150, ab_max=600,     # A -> B
    bd_max=60,                  # B -> D
    ac_share_min=0.0,           # (A->C) / (A->B) - reported only, not filtered
    ac_share_max=1.0,           # (SOLARA 87%, SKYGOLD 55%, so the 70/30 rule is off)

    # fibonacci zones  (level = low + ratio * (high - low))
    # A, B = highest high;  C, D = lowest low
    fib_b_min=0.382, fib_b_max=0.618,   # B on fib(A high, C low): SOLARA 0.430, SKYGOLD 0.583
    fib_d_min=0.236, fib_d_max=0.500,   # D low on fib(B high, C low): SOLARA 0.250, SKYGOLD 0.458
    target_ratio=1.618,                 # target on fib(B high, C low)
    c_anchor="low",                     # "low" -> 742.93 for SOLARA, "close" -> 740.74 (closer to your 740.25)

    # 200 SMA at D: must not fall faster than this (% per bar, measured over slope_bars)
    sma200_min_slope_pct=-0.10,
    slope_bars=10,

    # resistance phase between B and D
    # (starts at the 9/20 bear cross after B, ends at the first close below 200 SMA)
    res_min_bars=5,             # phase length
    res_min_touches=3,          # days whose high touches/crosses the 20 SMA
    res_max_close_above20=3.0,  # % - no close more than this above the 20 SMA
    d_max_after_break=10,       # D must form within this many bars after the first close below 200 SMA

    # consolidation after D and entry
    consol_min_bars=4,          # candles in the base INCLUDING D (SKYGOLD: 24,25,27,30 Mar -> entry 1 Apr)
    consol_max_range_pct=10.0,  # close-to-close range of the consolidation
    entry_max_bars=40,          # breakout must happen within this many bars after D
    entry_min_move_pct=6.0,     # breakout candle % change: SOLARA 7.85%, SKYGOLD 6.13%
    # exit: first DAILY CLOSE above the 1.618 target (SOLARA 11 Sep, SKYGOLD 6 May)
    # stop: daily close below D low
)

# ----------------------------------------------------------------------------
# TIMEFRAMES
# Candle-count rules (pivots, distances, base length) stay the same on every timeframe:
# the pattern is measured in candles. Percentage thresholds shrink with the square root of
# candle duration, because typical price moves grow with the square root of time.
#   1h vs 1d: sqrt(60 / 375) = 0.40  ->  breakout 6% -> 2.4%, base range 10% -> 4% ...
# ----------------------------------------------------------------------------
TF_MINUTES = {"15m": 15, "30m": 30, "1h": 60, "2h": 120, "4h": 240, "1d": 375, "1w": 1875}
PCT_KEYS = ["sma200_min_slope_pct", "res_max_close_above20", "consol_max_range_pct", "entry_min_move_pct"]
P_DAILY = dict(P)
TF = "1h"
DATE_FMT = "%d-%b-%Y %H:%M"

TF_YF_MAP = {
    "15m": ("15m", "60d"),
    "30m": ("30m", "60d"),
    "1h":  ("1h",  "730d"),
    "2h":  ("1h",  "730d"),
    "4h":  ("1h",  "730d"),
    "1d":  ("1d",  "5y"),
    "1w":  ("1wk", "10y"),
}

# optional hand-tuned overrides per timeframe (applied after scaling); fill in as you calibrate
P_OVERRIDES = {
    "1h": {},
}


def set_timeframe(tf):
    """scale percentage thresholds from the daily calibration to timeframe tf"""
    global TF, DATE_FMT
    TF = tf
    factor = (TF_MINUTES[tf] / TF_MINUTES["1d"]) ** 0.5
    P.clear()
    P.update(P_DAILY)
    for k in PCT_KEYS:
        P[k] = round(P_DAILY[k] * factor, 3)
    P.update(P_OVERRIDES.get(tf, {}))
    DATE_FMT = "%d-%b-%Y" if tf in ("1d", "1w") else "%d-%b-%Y %H:%M"
    return factor


# ----------------------------------------------------------------------------
def parse_dates(col):
    """dates with or without time / timezone -> naive local (IST) timestamps"""
    raw = col.astype(str).str.strip()
    has_tz = raw.str.contains(r"(?:[+-]\d\d:?\d\d|Z)$", regex=True).any()
    if has_tz:
        d = pd.to_datetime(raw, errors="coerce", utc=True).dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
    else:
        d = pd.to_datetime(raw, errors="coerce", format="mixed")
    return d


def load(src):
    if isinstance(src, str):
        df = pd.read_csv(src)
    else:
        df = src.copy()
    df.columns = [c.strip().capitalize() for c in df.columns]
    for alt in ("Datetime", "Timestamp", "Time"):
        if "Date" not in df.columns and alt in df.columns:
            df = df.rename(columns={alt: "Date"})
    if "Date" not in df.columns and df.index.name in ("Date", "Datetime"):
        df = df.reset_index()
        if df.columns[0] != "Date":
            df = df.rename(columns={df.columns[0]: "Date"})
    df["Date"] = parse_dates(df["Date"])
    df = df.dropna(subset=["Date", "Open", "High", "Low", "Close"]).sort_values("Date")
    df = df.drop_duplicates("Date")
    # drop holiday filler rows: O=H=L=C and unchanged from the previous close
    flat = (df.Open == df.High) & (df.High == df.Low) & (df.Low == df.Close)
    filler = flat & (df.Close == df.Close.shift())
    if TF not in ("1d", "1w") and "Volume" in df.columns:
        filler &= df.Volume.fillna(0) == 0
    df = df[~filler].reset_index(drop=True)
    for n in (9, 20, 200):
        df[f"s{n}"] = df.Close.rolling(n).mean()
    return df


def bear_cross_after(df, i, max_bars):
    """first bar in (i, i+max_bars] where 9 SMA crosses below 20 SMA"""
    s9, s20 = df.s9.values, df.s20.values
    for j in range(i + 1, min(i + max_bars, len(df) - 1) + 1):
        if s9[j] < s20[j] and s9[j - 1] >= s20[j - 1]:
            return j
    return None


def is_pivot_high(h, i, w):
    lo, hi = max(0, i - w), min(len(h), i + w + 1)
    return h[i] == h[lo:hi].max()


def bull_stack(df, i):
    r = df.iloc[i]
    return r.Close > r.s9 > r.s20 > r.s200


def find_d(df, B, b_high, c_low):
    """resistance phase -> first close below 200 -> D. returns (D, info) or (None, reason)"""
    n = len(df)
    C_, s9, s20, s200 = df.Close.values, df.s9.values, df.s20.values, df.s200.values
    H, L = df.High.values, df.Low.values

    cross = bear_cross_after(df, B, P["max_cross_bars"])
    if cross is None:
        return None, "no 9/20 cross after B"
    brk = next((k for k in range(cross, min(B + P["bd_max"], n)) if C_[k] < s200[k]), None)
    if brk is None:
        return None, "no close below 200 after B"
    ph = range(cross, brk)
    if len(ph) < P["res_min_bars"]:
        return None, "resistance phase too short"
    touches = sum(H[k] >= s20[k] for k in ph)
    max_above = max((C_[k] / s20[k] - 1) * 100 for k in ph)
    if touches < P["res_min_touches"] or max_above > P["res_max_close_above20"]:
        return None, "no clean 20 SMA resistance"
    if max(H[k] for k in ph) >= b_high:
        return None, "resistance phase exceeded B"

    for k in range(brk, min(brk + P["d_max_after_break"] + 1, n)):
        if L[k] != L[B:k + 1].min():
            continue
        if not (C_[k] < s9[k] and C_[k] < s20[k] and C_[k] < s200[k] and s9[k] < s20[k]):
            continue
        fib_d = (L[k] - c_low) / (b_high - c_low)
        if not (P["fib_d_min"] <= fib_d <= P["fib_d_max"]):
            continue
        sb = P["slope_bars"]
        slope = (s200[k] / s200[k - sb] - 1) * 100 / sb
        if slope < P["sma200_min_slope_pct"]:
            continue
        nxt = L[k + 1:k + 1 + P["consol_min_bars"]]
        if len(nxt) and nxt.min() <= L[k]:
            continue  # a lower low follows, so not D yet
        return k, dict(cross=cross, brk=brk, touches=touches, max_above20=max_above,
                       fib_d=fib_d, slope200=slope)
    return None, "no valid D"


def find_entry(df, D, d_low):
    n = len(df)
    C_, L, s9, s200 = df.Close.values, df.Low.values, df.s9.values, df.s200.values
    start = D + P["consol_min_bars"]          # base = D + (consol_min_bars-1) candles
    for k in range(D + 1, min(D + P["entry_max_bars"] + 1, n)):
        if L[k] < d_low:
            return None, "D broken", k
        if k < start:
            continue
        move = (C_[k] / C_[k - 1] - 1) * 100
        if move >= P["entry_min_move_pct"] and C_[k] > s200[k] and C_[k] > s9[k]:
            closes = C_[D + 1:k]
            rng = (closes.max() / closes.min() - 1) * 100
            if rng > P["consol_max_range_pct"]:
                return None, "consolidation too wide", k
            early = next((j for j in range(k - 1, D, -1)
                          if C_[j] > s9[j] and C_[j - 1] <= s9[j - 1]), None)
            return k, dict(move=move, early=early, consol_range=rng), k
    if n - 1 - D < P["consol_min_bars"]:
        return None, "FORMING", n - 1
    if n - 1 - D <= P["entry_max_bars"]:
        return None, "WATCH", n - 1
    return None, "no breakout", n - 1


def outcome(df, E, target, stop):
    """tracks the trade until stop / target or the end of data (close-based)"""
    C_ = df.Close.values
    for k in range(E + 1, len(df)):
        if C_[k] < stop:
            ret = (C_[k] / C_[E] - 1) * 100
            return "STOPPED", k, ret, k - E
        if C_[k] >= target:
            ret = (C_[k] / C_[E] - 1) * 100
            return "TARGET HIT", k, ret, k - E
    ret = (C_[-1] / C_[E] - 1) * 100
    return "OPEN", len(df) - 1, ret, len(df) - 1 - E


def scan(df, symbol):
    out, H, L, C_ = [], df.High.values, df.Low.values, df.Close.values
    n = len(df)
    d_ = lambda i: df.Date.iloc[i].strftime(DATE_FMT) if i is not None else ""
    used_d = set()

    b_cands = [i for i in range(200, n) if is_pivot_high(H, i, P["b_pivot_window"]) and bull_stack(df, i)
               and bear_cross_after(df, i, P["max_cross_bars"]) is not None]
    for B in b_cands:
        best = None
        for A in range(max(200, B - P["ab_max"] + 1), B - P["ab_min"] + 2):
            if H[A] != H[A:B + 1].max() or not is_pivot_high(H, A, P["a_pivot_window"]):
                continue
            if not bull_stack(df, A) or bear_cross_after(df, A, P["max_cross_bars"]) is None:
                continue
            C = A + int(L[A:B + 1].argmin())
            r = df.iloc[C]
            if not (r.Close < r.s9 < r.s20 < r.s200):
                continue
            share = (C - A + 1) / (B - A + 1)
            if not (P["ac_share_min"] <= share <= P["ac_share_max"]):
                continue
            fib_b = (H[B] - L[C]) / (H[A] - L[C])
            if not (P["fib_b_min"] <= fib_b <= P["fib_b_max"]):
                continue
            best = (A, C, share, fib_b)
            break  # earliest valid A = highest top
        if best is None:
            continue
        A, C, share, fib_b = best
        D, info = find_d(df, B, H[B], L[C])
        if D is None or D in used_d or H[B] != H[C:D + 1].max():
            continue
        used_d.add(D)

        c_ref = L[C] if P["c_anchor"] == "low" else C_[C]
        target = c_ref + P["target_ratio"] * (H[B] - c_ref)
        E, einfo, _ = find_entry(df, D, L[D])
        row = dict(
            symbol=symbol,
            A=d_(A), A_high=H[A], C=d_(C), C_low=L[C], B=d_(B), B_high=H[B], D=d_(D), D_low=L[D],
            AB_bars=B - A + 1, AC_bars=C - A + 1, CB_bars=B - C + 1, BD_bars=D - B + 1,
            AC_share=round(share, 3), fib_B=round(fib_b, 3), fib_D=round(info["fib_d"], 3),
            sma200_slope_pct=round(info["slope200"], 3), res_touches=info["touches"],
            target=round(target, 2), stop=L[D],
        )
        if E is not None:
            res, xk, ret, hold = outcome(df, E, target, L[D])
            row.update(status=res, early_9sma=d_(einfo["early"]), entry=d_(E), entry_close=C_[E],
                       entry_move_pct=round(einfo["move"], 2), exit_date=d_(xk),
                       return_pct=round(ret, 2), hold_candles=hold,
                       reward_risk=round((target - C_[E]) / (C_[E] - L[D]), 2))
        else:
            row.update(status=einfo)
        out.append(row)
    return out


def collect_files(folder, recursive):
    pattern = "**/*" if recursive else "*"
    found = glob.glob(os.path.join(folder, pattern + ".csv"), recursive=recursive) + \
        glob.glob(os.path.join(folder, pattern + ".CSV"), recursive=recursive)
    uniq = {}
    for f in found:
        if os.path.basename(f).lower().startswith("abcd_results"):
            continue                      # never scan our own output file
        uniq.setdefault(os.path.normcase(os.path.abspath(f)), f)
    return sorted(uniq.values(), key=lambda p: os.path.basename(p).upper())


def add_costs(res, cost_pct, intraday_cost_pct):
    """net return after charges. Delivery (overnight) trades pay cost_pct round trip; on intraday
    timeframes a trade that exits on its entry day pays the lower intraday rate."""
    t = res.copy()
    if "entry" not in t.columns:
        return t
    entered = t.status.isin(["TARGET HIT", "STOPPED", "OPEN"])
    e = pd.to_datetime(t.entry, format=DATE_FMT, errors="coerce")
    x = pd.to_datetime(t.exit_date, format=DATE_FMT, errors="coerce")
    same_day = (e.dt.date == x.dt.date) & (TF not in ("1d", "1w"))
    t["cost_pct"] = (same_day.map({True: intraday_cost_pct, False: cost_pct})).where(entered)
    t["net_return_pct"] = (t.return_pct - t.cost_pct).round(2)
    t["risk_pct"] = (100 * (t.entry_close - t.stop) / t.entry_close).round(2).where(entered)
    t["r_multiple"] = (t.net_return_pct / t.risk_pct).round(2)
    return t


def summarize(res):
    """backtest statistics for setups that were entered (gross and after costs)"""
    t = res[res.status.isin(["TARGET HIT", "STOPPED", "OPEN"])].copy()
    if t.empty:
        return None
    t["year"] = pd.to_datetime(t.entry, format=DATE_FMT).dt.year

    def stats(g, label):
        closed = g[g.status != "OPEN"]
        wins, losses = closed[closed.net_return_pct > 0], closed[closed.net_return_pct <= 0]
        gross_win, gross_loss = wins.net_return_pct.sum(), -losses.net_return_pct.sum()
        return dict(period=label, setups_entered=len(g), target_hit=int((closed.status == "TARGET HIT").sum()),
                    stopped=int((closed.status == "STOPPED").sum()), open=int((g.status == "OPEN").sum()),
                    win_rate_pct=round(100 * len(wins) / len(closed), 1) if len(closed) else None,
                    avg_gross_pct=round(closed.return_pct.mean(), 2) if len(closed) else None,
                    avg_net_pct=round(closed.net_return_pct.mean(), 2) if len(closed) else None,
                    avg_win_pct=round(wins.net_return_pct.mean(), 2) if len(wins) else None,
                    avg_loss_pct=round(losses.net_return_pct.mean(), 2) if len(losses) else None,
                    avg_r=round(closed.r_multiple.mean(), 2) if len(closed) else None,
                    profit_factor=round(gross_win / gross_loss, 2) if gross_loss > 0 else None,
                    avg_hold_candles=round(closed.hold_candles.mean(), 1) if len(closed) else None)

    rows = [stats(g, str(y)) for y, g in t.groupby("year")] + [stats(t, "ALL")]
    return pd.DataFrame(rows)


def simulate_money(res, capital, risk_pct, max_position_pct=25.0):
    """rupee profit/loss: each trade risks risk_pct of current equity between entry and the D-low stop
    (position capped at max_position_pct of equity); trades are booked in exit order, compounding."""
    t = res[res.status.isin(["TARGET HIT", "STOPPED"])].copy()
    if t.empty:
        return None, None
    t["_x"] = pd.to_datetime(t.exit_date, format=DATE_FMT)
    t = t.sort_values("_x")
    equity, rows = float(capital), []
    for _, r in t.iterrows():
        stop_dist = max(r.risk_pct, 0.01) / 100
        position = min(equity * risk_pct / 100 / stop_dist, equity * max_position_pct / 100)
        pnl = position * r.net_return_pct / 100
        equity += pnl
        rows.append(dict(symbol=r.symbol, entry=r.entry, exit_date=r.exit_date, status=r.status,
                         position_rs=round(position), net_return_pct=r.net_return_pct,
                         pnl_rs=round(pnl), equity_rs=round(equity)))
    ledger = pd.DataFrame(rows)
    peak = ledger.equity_rs.cummax().clip(lower=capital)
    summary = dict(start_capital=round(capital), final_equity=round(equity), profit_rs=round(equity - capital),
                   return_pct=round(100 * (equity / capital - 1), 2),
                   max_drawdown_pct=round(100 * (ledger.equity_rs / peak - 1).min(), 2),
                   trades=len(ledger))
    return summary, ledger


def merge_saved(path, fresh):
    """saved candles + freshly downloaded ones (fresh wins on overlap). If the overlapping prices
    disagree by more than 0.5% (a split/dividend re-adjusted Yahoo's history) the old file is dropped."""
    if not os.path.exists(path):
        return fresh
    try:
        old = pd.read_csv(path)
        old.columns = [c.strip().capitalize() for c in old.columns]
        old = old.rename(columns={"Datetime": "Date"})[list(fresh.columns)]
    except Exception:
        return fresh
    o = old.assign(_k=parse_dates(old.Date)).dropna(subset=["_k"]).drop_duplicates("_k").set_index("_k")
    f = fresh.assign(_k=parse_dates(fresh.Date)).dropna(subset=["_k"]).drop_duplicates("_k").set_index("_k")
    both = o.index.intersection(f.index)
    if len(both) and (o.Close[both].astype(float) / f.Close[both].astype(float) - 1).abs().max() > 0.005:
        return fresh
    merged = pd.concat([o[~o.index.isin(f.index)], f]).sort_index()
    merged["Date"] = merged.index.strftime("%Y-%m-%d %H:%M:%S")
    return merged.reset_index(drop=True)[list(fresh.columns)]


def load_metadata_symbols(path=""):
    """stock symbols (keys of all_profile_metadata.json, e.g. ICICIBANK.NS); [] if the file is missing"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [path] if path else [
        os.path.join(base_dir, "all_profile_metadata.json"),
        os.path.join(base_dir, "watchlists", "all_profile_metadata.json"),
        os.path.join(os.path.dirname(base_dir), "watchlists", "all_profile_metadata.json"),
    ]
    for p in candidates:
        if p and os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return [v.get("symbol", k) if isinstance(v, dict) else k for k, v in data.items()]
            return [str(x.get("symbol", "")) if isinstance(x, dict) else str(x) for x in data]
    if path:
        sys.exit(f"Metadata file not found: {path}")
    return []


def get_all_tickers():
    """Retrieve full master stock universe (597 tickers) across project watchlists"""
    meta = load_metadata_symbols()
    if meta:
        return meta
    base_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(base_dir, "watchlists", "all_profiles_tickers.txt"),
        os.path.join(os.path.dirname(base_dir), "watchlists", "all_profiles_tickers.txt"),
        r"C:\Users\onkar\Desktop\DhanSetu\watchlists\all_profiles_tickers.txt",
    ]
    for p in candidates:
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                return [line.strip() for line in f if line.strip()]
    return []


def main():
    ap = argparse.ArgumentParser(description="A-C-B-D pattern scanner - Hourly & Daily Timeframes (Scans All Stocks in One Go)")
    ap.add_argument("folder", nargs="?", default="",
                    help="folder that holds the CSV files (default: ...\\Stock_data\\1_H_TF for 1h, 1_D_TF for 1d)")
    ap.add_argument("--tf", default="1h", choices=list(TF_MINUTES), help="candle timeframe (default: 1h)")
    ap.add_argument("--recent", type=int, default=0, help="keep only setups whose D is within the last N candles")
    ap.add_argument("--from", dest="date_from", default="", help="keep setups whose D is on/after this date (YYYY-MM-DD)")
    ap.add_argument("--to", dest="date_to", default="", help="keep setups whose D is on/before this date (YYYY-MM-DD)")
    ap.add_argument("--asof", default="", help="scan as if today were this date (YYYY-MM-DD): later candles are ignored")
    ap.add_argument("--symbols", default="", help="comma-separated stock names, e.g. SOLARA,SKYGOLD")
    ap.add_argument("--symbols-file", default="", help="text file with one stock name per line (or comma-separated)")
    ap.add_argument("--metadata", default="",
                    help="all_profile_metadata.json to take stock names from (default for --live: the one next to this script)")
    ap.add_argument("--limit", type=int, default=0, help="scan only the first N stocks (alphabetical)")
    ap.add_argument("--recursive", action="store_true", help="also scan CSVs in sub-folders")
    ap.add_argument("--status", default="", help="keep only these statuses, e.g. WATCH,FORMING")
    ap.add_argument("--out", default="", help="output CSV path (default: abcd_results_1h.csv in folder)")
    ap.add_argument("--live", "--yfin", dest="live", action="store_true",
                    help="fetch fresh OHLCV live from Yahoo Finance for all stocks before scanning")
    ap.add_argument("--batch-size", type=int, default=50,
                    help="batch size for concurrent Yahoo Finance downloads (default: 50)")
    ap.add_argument("--no-save", action="store_true",
                    help="do not save fetched Yahoo Finance data to local CSV files")
    ap.add_argument("--capital", type=float, default=500000, help="starting capital for the profit/loss simulation")
    ap.add_argument("--risk-pct", type=float, default=1.0,
                    help="%% of equity lost if a trade hits its D-low stop (sets position size)")
    ap.add_argument("--cost-pct", type=float, default=0.35,
                    help="round-trip charges + slippage for overnight (delivery) trades, %% (default 0.35)")
    ap.add_argument("--intraday-cost-pct", type=float, default=0.15,
                    help="round-trip charges + slippage for trades closed on their entry day, %% (default 0.15)")
    args = ap.parse_args()

    factor = set_timeframe(args.tf)
    if not args.folder:
        sub = {"1d": "1_D_TF", "1h": "1_H_TF"}.get(args.tf, f"{args.tf.upper()}_TF")
        args.folder = os.path.join(r"C:\Users\onkar\Desktop\Stock_data", sub)

    if args.tf != "1d":
        print(f"Timeframe {args.tf}: % thresholds scaled x{factor:.2f} from daily -> " +
              ", ".join(f"{k}={P[k]}" for k in PCT_KEYS))

    try:
        end_of_day = lambda t: (pd.Timestamp(t) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
                                if len(t.strip()) <= 10 else pd.Timestamp(t))   # a bare date covers the whole day
        asof = end_of_day(args.asof) if args.asof else None
        d_from = pd.Timestamp(args.date_from) if args.date_from else None
        d_to = end_of_day(args.date_to) if args.date_to else None
    except ValueError as e:
        sys.exit(f"Bad date ({e}); use YYYY-MM-DD")

    rows, skipped = [], 0

    if args.live:
        import yfinance as yf
        raw_syms = []
        if args.symbols:
            raw_syms = [s for s in args.symbols.replace(";", ",").split(",") if s.strip()]
        elif args.symbols_file and os.path.exists(args.symbols_file):
            with open(args.symbols_file, encoding="utf-8") as fh:
                raw_syms = [s for s in fh.read().replace(";", ",").replace("\n", ",").split(",") if s.strip()]
        elif args.metadata:
            raw_syms = load_metadata_symbols(args.metadata)
        else:
            raw_syms = get_all_tickers()
            if not raw_syms and os.path.isdir(args.folder):
                raw_syms = [os.path.splitext(os.path.basename(f))[0] for f in collect_files(args.folder, args.recursive)]

        ticker_map = {}
        for s in raw_syms:
            s_clean = s.strip().upper().removesuffix(".CSV")
            if s_clean.endswith(".BO") or s_clean.endswith(".BSE"):
                base = s_clean.removesuffix(".BO").removesuffix(".BSE")
                ticker_map[f"{base}.BO"] = base
            elif s_clean.endswith(".NS") or s_clean.endswith(".NSE"):
                base = s_clean.removesuffix(".NS").removesuffix(".NSE")
                ticker_map[f"{base}.NS"] = base
            else:
                ticker_map[f"{s_clean}.NS"] = s_clean

        tickers = sorted(ticker_map.keys())
        if args.limit:
            tickers = tickers[:args.limit]

        os.makedirs(args.folder, exist_ok=True)
        yf_interval, yf_period = TF_YF_MAP.get(args.tf, ("1h", "730d"))
        print(f"Fetching live Yahoo Finance data for {len(tickers)} stock(s) ({args.tf} timeframe, period={yf_period}, batch size {args.batch_size}) ...")

        total = len(tickers)
        for i in range(0, total, args.batch_size):
            batch = tickers[i:i + args.batch_size]
            b_label = f"{i+1}-{min(i+len(batch), total)}"
            print(f"  Downloading batch {b_label}/{total} ...", flush=True)
            try:
                data = yf.download(
                    tickers=batch,
                    period=yf_period,
                    interval=yf_interval,
                    auto_adjust=True,
                    progress=False,
                    group_by="ticker",
                    threads=True
                )
            except Exception as e:
                print(f"  ! Batch download error: {e}")
                continue

            for yf_sym in batch:
                clean_sym = ticker_map[yf_sym]
                try:
                    if len(batch) == 1:
                        df_sym = data.copy()
                    elif isinstance(data.columns, pd.MultiIndex):
                        if yf_sym in data.columns.levels[0]:
                            df_sym = data[yf_sym].dropna(how="all")
                        elif yf_sym in data.columns.levels[1]:
                            df_sym = data.xs(yf_sym, level=1, axis=1).dropna(how="all")
                        else:
                            continue
                    else:
                        df_sym = data.copy()

                    if df_sym.empty or len(df_sym) < 10:
                        continue

                    df_sym = df_sym.reset_index()
                    df_sym.columns = [c.capitalize() for c in df_sym.columns]
                    for alt in ("Datetime", "Timestamp", "Time"):
                        if "Date" not in df_sym.columns and alt in df_sym.columns:
                            df_sym = df_sym.rename(columns={alt: "Date"})
                    req_cols = ["Date", "Open", "High", "Low", "Close", "Volume"]
                    if not all(col in df_sym.columns for col in req_cols):
                        continue

                    df_sym = df_sym[req_cols]
                    if args.tf not in ("1d", "1w"):
                        # Yahoo keeps only 60-730 days of intraday candles: add the fresh candles
                        # to what is already saved so the local history keeps growing
                        df_sym = merge_saved(os.path.join(args.folder, f"{clean_sym}.csv"), df_sym)

                    # Save fresh data to local CSV
                    if not args.no_save:
                        csv_file = os.path.join(args.folder, f"{clean_sym}.csv")
                        try:
                            df_sym.to_csv(csv_file, index=False)
                        except Exception:
                            pass

                    df_loaded = load(df_sym)
                    if asof is not None:
                        df_loaded = df_loaded[df_loaded.Date <= asof].reset_index(drop=True)
                    if len(df_loaded) < 400:
                        skipped += 1
                        continue

                    res = scan(df_loaded, clean_sym)
                    if args.recent:
                        cutoff = df_loaded.Date.iloc[-min(args.recent, len(df_loaded))]
                        res = [r for r in res if pd.to_datetime(r["D"], format=DATE_FMT) >= cutoff]
                    rows += res
                except Exception as e:
                    pass
            print(f"  ... {min(i+len(batch), total)}/{total} scanned, {len(rows)} setup(s) found so far", flush=True)

        scanned_count = len(tickers)
    else:
        if not os.path.isdir(args.folder):
            sys.exit(f"Folder not found: {args.folder} (Run with --live to fetch live data for all stocks)")
        files = collect_files(args.folder, args.recursive)
        if not files:
            sys.exit(f"No CSV files found in {args.folder} (Run with --live to fetch live data for all stocks)")

        wanted = [s for s in args.symbols.replace(";", ",").split(",") if s.strip()]
        if args.symbols_file:
            with open(args.symbols_file, encoding="utf-8") as fh:
                wanted += fh.read().replace(";", ",").replace("\n", ",").split(",")
        if args.metadata:
            wanted += load_metadata_symbols(args.metadata)
        wanted = {s.strip().upper().removesuffix(".CSV").removesuffix(".NS").removesuffix(".BO") for s in wanted if s.strip()}
        if wanted:
            have = {os.path.splitext(os.path.basename(f))[0].upper(): f for f in files}
            missing = sorted(wanted - have.keys())
            if missing:
                print(f"  ! not found in folder: {', '.join(missing)}")
            files = [have[s] for s in sorted(wanted & have.keys())]
        if args.limit:
            files = files[:args.limit]
        if not files:
            sys.exit("No matching stocks to scan.")

        mode = f"{args.tf}, " + (f"as of {asof}" if asof is not None else "full history")
        print(f"Scanning {len(files)} stock(s) in {args.folder} ({mode}) ...")
        for n, f in enumerate(files, 1):
            sym = os.path.splitext(os.path.basename(f))[0].upper()
            try:
                df = load(f)
                if asof is not None:
                    df = df[df.Date <= asof].reset_index(drop=True)
                if len(df) < 400:
                    skipped += 1
                    continue
                res = scan(df, sym)
                if args.recent:
                    cutoff = df.Date.iloc[-min(args.recent, len(df))]
                    res = [r for r in res if pd.to_datetime(r["D"], format=DATE_FMT) >= cutoff]
                rows += res
            except Exception as e:
                print(f"  ! {sym}: {e}")
            if n % 100 == 0:
                print(f"  ... {n}/{len(files)} done, {len(rows)} setup(s) so far")
        scanned_count = len(files)

    if d_from is not None or d_to is not None:
        dd = lambda r: pd.to_datetime(r["D"], format=DATE_FMT)
        rows = [r for r in rows if (d_from is None or dd(r) >= d_from) and (d_to is None or dd(r) <= d_to)]
    if args.status:
        keep = {s.strip().upper() for s in args.status.split(",") if s.strip()}
        rows = [r for r in rows if str(r.get("status", "")).upper() in keep]

    note = f" ({skipped} skipped: fewer than 400 candles)" if skipped else ""
    if not rows:
        print(f"No setups found in {scanned_count} stock(s){note}.")
        return

    res = add_costs(pd.DataFrame(rows), args.cost_pct, args.intraday_cost_pct)
    res["_d"] = pd.to_datetime(res.D, format=DATE_FMT)
    res = res.sort_values(["_d", "symbol"]).drop(columns="_d").reset_index(drop=True)
    default_name = f"abcd_results_{args.tf}.csv"
    if args.live:
        default_name = f"abcd_results_{args.tf}_live.csv"
    out = args.out or os.path.join(args.folder, default_name)
    try:
        res.to_csv(out, index=False)
    except PermissionError:
        import time
        out = os.path.join(args.folder, f"{os.path.splitext(default_name)[0]}_{int(time.time())}.csv")
        try:
            res.to_csv(out, index=False)
        except Exception as e:
            print(f"Could not save CSV: {e}")

    pd.set_option("display.width", 250, "display.max_columns", 40)
    cols = ["symbol", "A", "C", "B", "D", "fib_B", "fib_D", "status", "entry", "entry_close",
            "target", "exit_date", "return_pct", "hold_candles"]
    print(res[[c for c in cols if c in res.columns]].to_string(index=False))
    print(f"\n{len(res)} setup(s) from {scanned_count} stock(s){note} -> {out}")

    summ = summarize(res)
    if summ is not None:
        sout = os.path.splitext(out)[0] + "_summary.csv"
        try:
            summ.to_csv(sout, index=False)
        except Exception:
            pass
        print(f"\nBacktest summary (closed trades, after {args.cost_pct}% delivery / "
              f"{args.intraday_cost_pct}% same-day costs; OPEN trades not counted in win rate):")
        print(summ.to_string(index=False))
        print(f"-> {sout}")

    money, ledger = simulate_money(res, args.capital, args.risk_pct)
    if money is not None:
        lout = os.path.splitext(out)[0] + "_pnl.csv"
        try:
            ledger.to_csv(lout, index=False)
        except Exception:
            pass
        verdict = "PROFIT" if money["profit_rs"] > 0 else "LOSS"
        print(f"\nMoney simulation ({args.risk_pct}% risk per trade, closed trades in exit order):")
        print(ledger.to_string(index=False))
        print(f"\n  Rs {money['start_capital']:,} -> Rs {money['final_equity']:,}  =  {verdict} of "
              f"Rs {abs(money['profit_rs']):,} ({money['return_pct']:+.2f}%), max drawdown "
              f"{money['max_drawdown_pct']}% over {money['trades']} trade(s)")
        print(f"-> {lout}")


if __name__ == "__main__":
    main()
