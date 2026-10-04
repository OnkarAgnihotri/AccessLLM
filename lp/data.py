"""Stock list, Yahoo Finance download with a local CSV cache, and loading price panels."""

import json
import os

import numpy as np
import pandas as pd

COLS = ["Open", "High", "Low", "Close", "Volume"]


def load_universe(metadata_path: str) -> dict:
    """{SYMBOL: sector label} from all_profile_metadata.json (keys like 'ICICIBANK.NS')."""
    with open(metadata_path, encoding="utf-8") as fh:
        meta = json.load(fh)
    out = {}
    items = meta.items() if isinstance(meta, dict) else ((m.get("symbol", ""), m) for m in meta)
    for key, info in items:
        sym = str(info.get("symbol", key) if isinstance(info, dict) else key).upper()
        sym = sym.removesuffix(".NS").removesuffix(".BO")
        if sym:
            out[sym] = (info.get("sector", "") if isinstance(info, dict) else "") or ""
    return out


def _csv_path(data_dir: str, interval: str, sym: str) -> str:
    return os.path.join(data_dir, interval, f"{sym}.csv")


def read_csv(path: str) -> pd.DataFrame:
    d = pd.read_csv(path, index_col=0)
    d.index = pd.to_datetime(d.index, utc=False, format="mixed")
    if getattr(d.index, "tz", None) is not None:
        d.index = d.index.tz_localize(None)
    d.index.name = "Date"
    return clean(d)


def clean(d: pd.DataFrame) -> pd.DataFrame:
    """Drop empty, duplicate and impossible bars, and isolated one-day price spikes (bad ticks)."""
    d = d[[c for c in COLS if c in d.columns]].copy()
    d = d[~d.index.duplicated(keep="last")].sort_index()
    d = d.dropna(subset=["Open", "High", "Low", "Close"])
    d = d[(d[["Open", "High", "Low", "Close"]] > 0).all(axis=1) & (d.High >= d.Low)]
    if len(d) > 3:
        r = d.Close.pct_change()
        spike = (r.abs() > 0.4) & (r.shift(-1).abs() > 0.3) & (np.sign(r) != np.sign(r.shift(-1)))
        d = d[~spike]
    return d


def fetch(symbols, data_dir: str, interval: str = "1d", period: str = "6y",
          batch_size: int = 50, log=print) -> int:
    """Download or update cached CSVs. Symbols without '^' get the '.NS' suffix.

    Existing files are topped up with only the recent bars, so daily refreshes are quick.
    Prices are split/dividend adjusted, so if the overlapping days of a cached file no longer
    match the fresh download (a new corporate action), that stock's full history is re-downloaded.
    Returns the number of files written.
    """
    import yfinance as yf

    os.makedirs(os.path.join(data_dir, interval), exist_ok=True)
    new, old = [], []
    for s in symbols:
        (old if os.path.exists(_csv_path(data_dir, interval, s)) else new).append(s)
    written = 0
    stale = []
    for group, per in ((old, "1mo"), (new, period), (stale, period)):
        for i in range(0, len(group), batch_size):
            batch = group[i:i + batch_size]
            tickers = {(s if s.startswith("^") else f"{s}.NS"): s for s in batch}
            log(f"  {interval}: downloading {i + 1}-{i + len(batch)} of {len(group)} "
                f"({'full history' if per == period else 'update'})")
            try:
                raw = yf.download(list(tickers), period=per, interval=interval, auto_adjust=True,
                                  progress=False, group_by="ticker", threads=True)
            except Exception as e:                       # network hiccup: keep going with the next batch
                log(f"  ! batch failed: {e}")
                continue
            for t, s in tickers.items():
                try:
                    part = raw[t] if isinstance(raw.columns, pd.MultiIndex) else raw
                except KeyError:
                    continue
                part = part.dropna(how="all")
                if part.empty:
                    continue
                part.index = pd.to_datetime(part.index)
                if getattr(part.index, "tz", None) is not None:
                    part.index = part.index.tz_localize(None)
                part.index.name = "Date"
                path = _csv_path(data_dir, interval, s)
                if per != period and os.path.exists(path):
                    cached = read_csv(path)
                    both = cached.Close.index.intersection(part.index)
                    if len(both) and (cached.Close[both] / part.Close[both] - 1).abs().max() > 0.005:
                        stale.append(s)          # adjusted history changed: refetch everything
                        continue
                    part = pd.concat([cached, part[COLS]])
                clean(part).to_csv(path)
                written += 1
    if stale:
        log(f"  re-downloaded full history for {len(stale)} stock(s) with new splits/dividends")
    return written


def load_panels(symbols, data_dir: str, index_symbol: str = "^NSEI", interval: str = "1d",
                min_bars: int = 250, log=print):
    """Wide DataFrames (dates x symbols) for Open/High/Low/Close/Volume plus the index close.

    The index's trading days define the calendar. Stocks with fewer than `min_bars` bars are skipped.
    """
    idx_path = _csv_path(data_dir, interval, index_symbol)
    if not os.path.exists(idx_path):
        raise FileNotFoundError(f"{idx_path} not found - run the fetch command first")
    index = read_csv(idx_path)
    frames, missing, short = {}, 0, 0
    for s in symbols:
        p = _csv_path(data_dir, interval, s)
        if not os.path.exists(p):
            missing += 1
            continue
        d = read_csv(p)
        if len(d) < min_bars:
            short += 1
            continue
        frames[s] = d
    if not frames:
        raise RuntimeError(f"No price files found in {os.path.join(data_dir, interval)}")
    cal = index.index
    panels = {c: pd.DataFrame({s: d[c] for s, d in frames.items()}).reindex(cal) for c in COLS}
    log(f"Loaded {len(frames)} stocks, {len(cal)} days ({cal[0].date()} to {cal[-1].date()}); "
        f"{missing} without data, {short} with under {min_bars} bars")
    return panels, index.Close
