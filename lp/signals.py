"""Leaders' Pullback rules. The backtester and the live scanner both use this module,
so a setup means exactly the same thing in both.

Everything is computed from data known at the close of day t; trades are entered at the
open of day t+1.
"""

import pandas as pd

from . import indicators as ind
from .config import Config


def compute(panels: dict, index_close: pd.Series, cfg: Config) -> dict:
    """Indicator panels, the leader mask, the setup mask, the ranking score and the market light."""
    o, h, l, c, v = (panels[k] for k in ("Open", "High", "Low", "Close", "Volume"))
    f = {
        "sma_fast": ind.sma(c, cfg.sma_fast),
        "sma_mid": ind.sma(c, cfg.sma_mid),
        "sma_long": ind.sma(c, cfg.sma_long),
        "rsi": ind.rsi(c, cfg.rsi_len),
        "atr": ind.atr(h, l, c, cfg.atr_len),
        "turnover_cr": ind.median_turnover(c, v, cfg.turnover_days) / 1e7,
        "rs_pct": ind.rs_percentile(c, cfg.rs_lookback),
    }
    leader = ((f["turnover_cr"] >= cfg.min_turnover_cr)
              & (c > f["sma_mid"]) & (c > f["sma_long"])
              & (f["rs_pct"] >= cfg.rs_min_pct))
    setup = leader & (f["rsi"] < cfg.rsi_max) & (c < f["sma_fast"]) & f["atr"].notna()
    f["leader"] = leader
    f["setup"] = setup
    # higher score = taken first when there are more setups than free slots
    f["score"] = f["rs_pct"] if cfg.rank_by == "rs" else -f["rsi"]
    idx = index_close.reindex(c.index).ffill()
    f["index_sma"] = ind.sma(idx, cfg.regime_sma)
    f["regime_up"] = idx > f["index_sma"]           # True = green light, False = amber
    f["index_close"] = idx
    return f


def size_multiplier(regime_up: bool, cfg: Config) -> float:
    if regime_up or cfg.regime_mode == "ignore":
        return 1.0
    return 0.5 if cfg.regime_mode == "half" else 0.0


def setups_on(day, f: dict) -> pd.DataFrame:
    """Setups at the close of `day`, best score first."""
    m = f["setup"].loc[day]
    syms = m[m.fillna(False)].index
    out = pd.DataFrame({
        "score": f["score"].loc[day, syms],
        "rs_pct": f["rs_pct"].loc[day, syms],
        "rsi": f["rsi"].loc[day, syms],
        "atr": f["atr"].loc[day, syms],
        "turnover_cr": f["turnover_cr"].loc[day, syms],
    })
    return out.sort_values("score", ascending=False)
