"""Indian delivery-equity transaction costs (NSE)."""

from .config import Config


def buy_cost(value: float, cfg: Config) -> float:
    """Rupee charges on a buy order of `value` (slippage is applied to the fill price, not here)."""
    if value <= 0:
        return 0.0
    exch = value * cfg.exchange_pct / 100
    sebi = value * cfg.sebi_pct / 100
    gst = (cfg.brokerage_per_order + exch + sebi) * cfg.gst_pct / 100
    return (cfg.brokerage_per_order + value * cfg.stt_pct / 100 + exch + sebi + gst
            + value * cfg.stamp_pct / 100)


def sell_cost(value: float, cfg: Config) -> float:
    """Rupee charges on a sell order, including the per-day demat (DP) charge."""
    if value <= 0:
        return 0.0
    exch = value * cfg.exchange_pct / 100
    sebi = value * cfg.sebi_pct / 100
    gst = (cfg.brokerage_per_order + exch + sebi) * cfg.gst_pct / 100
    return cfg.brokerage_per_order + value * cfg.stt_pct / 100 + exch + sebi + gst + cfg.dp_charge


def buy_fill(price: float, cfg: Config) -> float:
    return price * (1 + cfg.slippage_pct / 100)


def sell_fill(price: float, cfg: Config) -> float:
    return price * (1 - cfg.slippage_pct / 100)
