"""Settings for the Leaders' Pullback system.

Defaults follow research/STRATEGY_REPORT.md. Override any of them in config.yaml
(same key names) or from the command line.
"""

from dataclasses import dataclass, fields, asdict
import os


@dataclass
class Config:
    # --- data ---
    data_dir: str = "lp_data"                         # cache folder: <data_dir>/1d/<SYMBOL>.csv
    metadata: str = "all_profile_metadata.json"      # stock list + sectors
    index_symbol: str = "^NSEI"                       # market regime benchmark (Nifty 50)
    history_period: str = "6y"                        # first download length for daily data

    # --- account ---
    capital: float = 500_000.0                        # starting capital in rupees
    risk_pct: float = 1.0                             # % of equity lost if the hard stop is hit
    max_positions: int = 5
    max_per_sector: int = 2
    max_position_pct: float = 25.0                    # cap on one position's value, % of equity
    monthly_dd_stop_pct: float = 6.0                  # no new trades for the rest of the month after this loss

    # --- leaders filter ---
    min_turnover_cr: float = 20.0                     # median daily turnover (20 days), rupees crore
    turnover_days: int = 20
    rs_lookback: int = 126                            # 6-month return used for relative strength
    rs_min_pct: float = 70.0                          # keep the top 30% of the universe
    sma_mid: int = 50
    sma_long: int = 200

    # --- pullback setup ---
    rsi_len: int = 2
    rsi_max: float = 5.0                              # RSI(2) below this
    sma_fast: int = 5                                 # close below this average

    # --- trade management ---
    atr_len: int = 14
    stop_atr: float = 3.0                             # hard stop = entry - stop_atr * ATR
    t1_pct: float = 1.0                               # first target, % above entry
    t1_fraction: float = 0.5                          # share of the position sold at the first target
    move_stop_to_entry: bool = True                   # after the first target, stop moves to the entry price
    max_hold_days: int = 10                           # time stop (trading days, entry day = day 1)
    rank_by: str = "rs"                               # "rs" (strongest first) or "rsi" (deepest dip first)

    # --- market regime ---
    regime_sma: int = 200
    regime_mode: str = "half"                         # half | skip | ignore  (when the index is below its SMA)

    # --- costs (Indian delivery equity) ---
    brokerage_per_order: float = 20.0                 # rupees per executed order (0 for zero-brokerage delivery)
    stt_pct: float = 0.1                              # on buy and sell value
    exchange_pct: float = 0.00297                     # NSE transaction charge
    sebi_pct: float = 0.0001                          # Rs 10 per crore
    stamp_pct: float = 0.015                          # on buy value
    gst_pct: float = 18.0                             # on brokerage + exchange + SEBI fees
    dp_charge: float = 15.93                          # per stock per day that shares are sold from demat
    slippage_pct: float = 0.05                        # per side, against you

    # --- backtest window ---
    start: str = ""                                   # YYYY-MM-DD, empty = first date with enough history
    end: str = ""


def load_config(path: str = "", **overrides) -> Config:
    """Build a Config from defaults, then an optional YAML file, then keyword overrides."""
    values = {}
    if path and os.path.exists(path):
        import yaml
        with open(path, encoding="utf-8") as fh:
            values.update(yaml.safe_load(fh) or {})
    values.update({k: v for k, v in overrides.items() if v is not None})
    known = {f.name: f.type for f in fields(Config)}
    unknown = set(values) - set(known)
    if unknown:
        raise ValueError(f"Unknown config keys: {', '.join(sorted(unknown))}")
    cfg = Config()
    for k, v in values.items():
        default = getattr(cfg, k)
        if isinstance(default, bool):
            v = v if isinstance(v, bool) else str(v).lower() in ("1", "true", "yes")
        elif isinstance(default, (int, float)) and not isinstance(default, bool):
            v = type(default)(v)
        setattr(cfg, k, v)
    if cfg.regime_mode not in ("half", "skip", "ignore"):
        raise ValueError("regime_mode must be half, skip or ignore")
    if cfg.rank_by not in ("rs", "rsi"):
        raise ValueError("rank_by must be rs or rsi")
    return cfg


def as_dict(cfg: Config) -> dict:
    return asdict(cfg)
