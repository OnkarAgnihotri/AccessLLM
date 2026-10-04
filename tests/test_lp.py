import numpy as np
import pandas as pd
import pytest

from lp import indicators as ind
from lp import costs
from lp.backtest import run_backtest
from lp.config import load_config


# ---------------------------------------------------------------- indicators

def test_rsi_extremes():
    up = pd.Series(np.arange(1, 30, dtype=float))
    assert ind.rsi(up, 2).iloc[-1] == pytest.approx(100)
    down = pd.Series(np.arange(30, 1, -1, dtype=float))
    assert ind.rsi(down, 2).iloc[-1] == pytest.approx(0)


def test_rsi_two_period_values():
    c = pd.Series([10, 11, 10, 9.0])
    # Wilder alpha=1/2 seeded with the first change: up = [1, .5, .25], down = [0, .5, .75]
    assert ind.rsi(c, 2).iloc[-1] == pytest.approx(100 - 100 / (1 + 0.25 / 0.75))


def test_atr_simple_average():
    h = pd.Series([11, 12, 13.0]); l = pd.Series([9, 10, 11.0]); c = pd.Series([10, 11, 12.0])
    assert ind.atr(h, l, c, 2).iloc[-1] == pytest.approx(2.0)


def test_atr_on_frames_uses_gaps():
    h = pd.DataFrame({"A": [10, 15.0]}); l = pd.DataFrame({"A": [9, 14.0]}); c = pd.DataFrame({"A": [9.5, 14.5]})
    assert ind.true_range(h, l, c).iloc[1, 0] == pytest.approx(5.5)   # high - previous close


def test_rs_percentile_orders_stocks():
    c = pd.DataFrame({"A": [100, 110.0], "B": [100, 90.0], "C": [100, 100.0]})
    p = ind.rs_percentile(c, 1).iloc[-1]
    assert p["A"] > p["C"] > p["B"]


# ---------------------------------------------------------------- costs

def test_buy_and_sell_costs():
    cfg = load_config()
    v = 100_000
    exch, sebi = v * 0.00297 / 100, v * 0.0001 / 100
    gst = (20 + exch + sebi) * 0.18
    assert costs.buy_cost(v, cfg) == pytest.approx(20 + 100 + exch + sebi + gst + 15)
    assert costs.sell_cost(v, cfg) == pytest.approx(20 + 100 + exch + sebi + gst + 15.93)


# ---------------------------------------------------------------- backtest engine

def _world(bars: dict, setup_days: dict, n=8, atr=2.0, sma_fast=1e9):
    """Tiny market: bars = {sym: [(o,h,l,c), ...]}; setup_days = {sym: [day indices]}."""
    dates = pd.bdate_range("2024-01-01", periods=n)
    syms = list(bars)
    def panel(k):
        return pd.DataFrame({s: [b[k] for b in bars[s]] for s in syms}, index=dates)
    panels = {"Open": panel(0), "High": panel(1), "Low": panel(2), "Close": panel(3),
              "Volume": pd.DataFrame(1e6, index=dates, columns=syms)}
    setup = pd.DataFrame(False, index=dates, columns=syms)
    for s, ds in setup_days.items():
        for d in ds:
            setup.iloc[d, setup.columns.get_loc(s)] = True
    full = lambda v: pd.DataFrame(v, index=dates, columns=syms)
    f = {"setup": setup, "score": full(90.0), "rs_pct": full(90.0), "rsi": full(3.0), "atr": full(atr),
         "turnover_cr": full(100.0), "sma_fast": full(sma_fast),
         "regime_up": pd.Series(True, index=dates), "index_sma": pd.Series(1.0, index=dates)}
    return panels, f


def _cfg(**kw):
    base = dict(capital=1_000_000, slippage_pct=0, brokerage_per_order=0, stt_pct=0, exchange_pct=0,
                sebi_pct=0, stamp_pct=0, dp_charge=0, monthly_dd_stop_pct=100)
    base.update(kw)
    return load_config(**base)


FLAT = (100, 100.5, 99.5, 100)


def test_first_target_then_breakeven():
    bars = {"A": [FLAT, (100, 101.5, 99.8, 100.5), (100.4, 100.6, 99.0, 99.5)] + [FLAT] * 5}
    panels, f = _world(bars, {"A": [0]})
    res = run_backtest(panels, f, {"A": "X"}, _cfg())
    t = res.trades.iloc[0]
    assert t.first_target_hit and t.exit_reason == "breakeven"
    assert str(t.entry_date) == "2024-01-02"
    # risk 1% of 10 lakh = 10,000 / stop distance 6 -> 1666 shares, capped at 25% of equity -> 2500 max
    assert t.qty == 1666
    assert t.pnl == pytest.approx(833 * 1.0)          # half sold +1 rupee, rest flat


def test_stop_first_when_both_hit_same_day():
    bars = {"A": [FLAT, (100, 102, 93, 95)] + [FLAT] * 6}
    panels, f = _world(bars, {"A": [0]})
    t = run_backtest(panels, f, {"A": "X"}, _cfg()).trades.iloc[0]
    assert t.exit_reason == "stop" and not t.first_target_hit
    assert t.pnl == pytest.approx(-6 * t.qty)


def test_gap_below_stop_fills_at_open():
    bars = {"A": [FLAT, FLAT, (90, 91, 89, 90)] + [FLAT] * 5}
    panels, f = _world(bars, {"A": [0]})
    t = run_backtest(panels, f, {"A": "X"}, _cfg()).trades.iloc[0]
    assert t.exit_reason == "gap_stop"
    assert t.pnl == pytest.approx(-10 * t.qty)


def test_sma_exit_and_time_stop():
    bars = {"A": [FLAT] * 8}
    panels, f = _world(bars, {"A": [0]}, sma_fast=99.0)        # close 100 > sma -> exit on entry day close
    assert run_backtest(panels, f, {"A": "X"}, _cfg()).trades.iloc[0].exit_reason == "sma_exit"
    panels, f = _world(bars, {"A": [0]})
    t = run_backtest(panels, f, {"A": "X"}, _cfg(max_hold_days=3)).trades.iloc[0]
    assert t.exit_reason == "time_stop" and t.days_held == 3


def test_position_and_sector_limits():
    bars = {s: [FLAT] * 8 for s in "ABCD"}
    panels, f = _world(bars, {s: [0] for s in "ABCD"})
    groups = {"A": "X", "B": "X", "C": "X", "D": "Y"}
    tr = run_backtest(panels, f, groups, _cfg(max_positions=5, max_per_sector=2)).trades
    assert sorted(tr.symbol) == ["A", "B", "D"]
    tr = run_backtest(panels, f, groups, _cfg(max_positions=1, max_per_sector=2)).trades
    assert len(tr) == 1


def test_amber_market_half_size_and_skip():
    bars = {"A": [FLAT] * 8}
    panels, f = _world(bars, {"A": [0]})
    f["regime_up"][:] = False
    t = run_backtest(panels, f, {"A": "X"}, _cfg(regime_mode="half")).trades.iloc[0]
    assert t.qty == 833 and t.size_mult == 0.5
    assert run_backtest(panels, f, {"A": "X"}, _cfg(regime_mode="skip")).trades.empty


def test_costs_reduce_pnl():
    bars = {"A": [FLAT] * 8}
    panels, f = _world(bars, {"A": [0]})
    t = run_backtest(panels, f, {"A": "X"}, _cfg(max_hold_days=2, stt_pct=0.1)).trades.iloc[0]
    assert t.pnl == pytest.approx(-0.2 * t.qty, rel=1e-6)       # 0.1% STT on each side of a flat trade


def test_config_rejects_unknown_keys():
    with pytest.raises(ValueError):
        load_config(not_a_setting=1)
