"""Indicators. Every function works on a Series or on a wide DataFrame (dates x symbols)."""

import numpy as np
import pandas as pd


def sma(close, n):
    return close.rolling(n, min_periods=n).mean()


def rsi(close, n=2):
    """Wilder's RSI (Connors uses n=2)."""
    delta = close.diff()
    up = delta.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    down = (-delta.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    rs = up / down.replace(0, np.nan)
    out = 100 - 100 / (1 + rs)
    out = out.where(down != 0, 100.0)          # no down moves at all -> RSI 100
    return out.where(close.notna())


def true_range(high, low, close):
    prev = close.shift(1)
    a, b, c = high - low, (high - prev).abs(), (low - prev).abs()
    if isinstance(high, pd.DataFrame):
        return np.maximum(np.maximum(a, b.fillna(a)), c.fillna(a))
    return pd.concat([a, b, c], axis=1).max(axis=1)


def atr(high, low, close, n=14):
    """Simple-average ATR, as used in the research."""
    return true_range(high, low, close).rolling(n, min_periods=n).mean()


def median_turnover(close, volume, n=20):
    return (close * volume).rolling(n, min_periods=n).median()


def rs_percentile(close, lookback=126):
    """Cross-sectional percentile (0-100) of each stock's `lookback`-day return on each date."""
    ret = close / close.shift(lookback)
    return ret.rank(axis=1, pct=True) * 100


def vwap(high, low, close, volume):
    """Cumulative VWAP of the bars passed in (pass one session at a time)."""
    tp = (high + low + close) / 3
    return (tp * volume).cumsum() / volume.cumsum().replace(0, np.nan)
