"""Day-by-day portfolio simulation of the Leaders' Pullback strategy.

Order of events on each trading day:
  1. Open:  positions that gap below their stop exit at the open; a gap above the first target
            fills that target at the open. New trades from yesterday's setups are bought at the open.
  2. Day:   the high/low decide stops and the first target. If both are touched on the same day the
            stop is assumed to come first (conservative). A stop moved to entry after the first
            target is only active from the next day, because the order of moves inside a day is unknown.
  3. Close: the rest of a position is sold if the close is above the fast SMA, or on the time stop.
            Equity is marked to market and today's setups are queued for tomorrow's open.
Market orders (entry, stops, close exits) pay slippage; the first-target limit order does not.
"""

from dataclasses import dataclass, field
import math

import numpy as np
import pandas as pd

from .config import Config
from . import costs
from .signals import setups_on, size_multiplier


@dataclass
class Position:
    sym: str
    sector: str
    signal_date: pd.Timestamp
    entry_date: pd.Timestamp
    entry_px: float
    qty: int
    stop: float
    t1_px: float
    risk_rs: float
    size_mult: float
    qty_open: int = 0
    t1_done: bool = False
    t1_date: pd.Timestamp = None
    bars_held: int = 0
    cash_flow: float = 0.0          # net rupees: proceeds minus purchase and all charges
    last_close: float = float("nan")
    fills: list = field(default_factory=list)


@dataclass
class Result:
    trades: pd.DataFrame
    equity: pd.DataFrame
    cfg: Config


class Backtester:
    def __init__(self, panels: dict, f: dict, groups: dict, cfg: Config, log=print):
        self.cfg, self.f, self.groups, self.log = cfg, f, groups, log
        self.dates = panels["Close"].index
        self.cols = {s: j for j, s in enumerate(panels["Close"].columns)}
        self.O = panels["Open"].to_numpy(float)
        self.H = panels["High"].to_numpy(float)
        self.L = panels["Low"].to_numpy(float)
        self.C = panels["Close"].to_numpy(float)
        self.SF = f["sma_fast"].to_numpy(float)

    # ------------------------------------------------------------------ helpers
    def _sell(self, p: Position, qty: int, price: float, day, reason: str, market: bool = True):
        qty = min(qty, p.qty_open)
        if qty <= 0:
            return
        px = costs.sell_fill(price, self.cfg) if market else price
        value = px * qty
        charge = costs.sell_cost(value, self.cfg)
        p.cash_flow += value - charge
        p.qty_open -= qty
        p.fills.append((day, "SELL", qty, px, charge, reason))
        self.cash += value - charge
        self.costs_paid += charge
        if p.qty_open == 0:
            self._close_trade(p, day, reason)

    def _close_trade(self, p: Position, day, reason: str):
        invested = p.entry_px * p.qty
        self.trades.append(dict(
            symbol=p.sym, sector=p.sector, signal_date=p.signal_date.date(), entry_date=p.entry_date.date(),
            exit_date=day.date(), days_held=p.bars_held, entry_price=round(p.entry_px, 2), qty=p.qty,
            invested=round(invested, 2), first_target_hit=p.t1_done, exit_reason=reason,
            pnl=round(p.cash_flow, 2), return_pct=round(100 * p.cash_flow / invested, 3),
            r_multiple=round(p.cash_flow / p.risk_rs, 3) if p.risk_rs else np.nan,
            size_mult=p.size_mult,
            exits="; ".join(f"{d.date()} {q}@{x:.2f} {r}" for d, side, q, x, _, r in p.fills if side == "SELL"),
        ))
        del self.positions[p.sym]

    # ------------------------------------------------------------------ main loop
    def run(self) -> Result:
        cfg, f = self.cfg, self.f
        dates = self.dates
        ready = f["index_sma"].notna() & f["rs_pct"].notna().any(axis=1)
        first = ready.idxmax() if ready.any() else dates[0]
        start = max(first, pd.Timestamp(cfg.start)) if cfg.start else first
        end = pd.Timestamp(cfg.end) if cfg.end else dates[-1]
        days = dates[(dates >= start) & (dates <= end)]
        if len(days) < 2:
            raise ValueError("Backtest window has fewer than 2 trading days")

        self.cash = float(cfg.capital)
        self.positions: dict[str, Position] = {}
        self.trades, curve = [], []
        self.costs_paid = 0.0
        prev_equity = float(cfg.capital)
        month, month_start_eq, halted = None, prev_equity, False
        pending, pending_mult, pending_day = None, 1.0, None

        for day in days:
            i = dates.get_loc(day)
            if day.month != month:
                month, month_start_eq, halted = day.month, prev_equity, False

            # 1a. open: gaps on existing positions
            for p in list(self.positions.values()):
                j = self.cols[p.sym]
                o = self.O[i, j]
                if np.isnan(o):
                    continue
                if o <= p.stop:
                    self._sell(p, p.qty_open, o, day, "gap_stop" if not p.t1_done else "gap_breakeven")
                elif not p.t1_done and o >= p.t1_px:
                    self._take_t1(p, o, day)

            # 1b. open: new entries from yesterday's setups
            if pending is not None and not halted and pending_mult > 0:
                self._enter(pending, pending_mult, pending_day, day, i, prev_equity)

            # 2. intraday stops and first target
            for p in list(self.positions.values()):
                j = self.cols[p.sym]
                hi, lo = self.H[i, j], self.L[i, j]
                if np.isnan(hi) or np.isnan(lo):
                    continue
                if not p.t1_done:
                    if lo <= p.stop:
                        self._sell(p, p.qty_open, p.stop, day, "stop")
                    elif hi >= p.t1_px:
                        self._take_t1(p, p.t1_px, day)
                elif p.t1_date != day and lo <= p.stop:
                    self._sell(p, p.qty_open, p.stop, day, "breakeven" if p.stop >= p.entry_px else "stop")

            # 3. close: fast-SMA exit and time stop
            for p in list(self.positions.values()):
                j = self.cols[p.sym]
                c = self.C[i, j]
                if np.isnan(c):
                    continue
                p.last_close = c
                p.bars_held += 1
                if c > self.SF[i, j]:
                    self._sell(p, p.qty_open, c, day, "sma_exit")
                elif p.bars_held >= cfg.max_hold_days:
                    self._sell(p, p.qty_open, c, day, "time_stop")

            # mark to market
            invested = sum(p.qty_open * p.last_close for p in self.positions.values()
                           if not np.isnan(p.last_close))
            equity = self.cash + invested
            regime_up = bool(f["regime_up"].loc[day])
            curve.append(dict(date=day, equity=equity, cash=self.cash, invested=invested,
                              positions=len(self.positions), regime_up=regime_up, halted=halted))
            if equity <= month_start_eq * (1 - cfg.monthly_dd_stop_pct / 100):
                halted = True
            prev_equity = equity

            # queue today's setups for tomorrow's open
            pending_mult = size_multiplier(regime_up, cfg)
            pending = setups_on(day, f) if pending_mult > 0 else None
            pending_day = day

        # close anything still open at the last close
        last = days[-1]
        for p in list(self.positions.values()):
            self._sell(p, p.qty_open, p.last_close, last, "end_of_test")
        if curve:
            curve[-1]["equity"] = self.cash
            curve[-1]["cash"], curve[-1]["invested"], curve[-1]["positions"] = self.cash, 0.0, 0

        eq = pd.DataFrame(curve).set_index("date")
        tr = pd.DataFrame(self.trades)
        eq.attrs["costs_paid"] = self.costs_paid
        return Result(trades=tr, equity=eq, cfg=cfg)

    def _take_t1(self, p: Position, price: float, day):
        cfg = self.cfg
        qty = max(1, int(round(p.qty * cfg.t1_fraction)))
        p.t1_done, p.t1_date = True, day
        if cfg.move_stop_to_entry:
            p.stop = max(p.stop, p.entry_px)
        self._sell(p, qty, price, day, "first_target", market=False)

    def _enter(self, pending: pd.DataFrame, mult: float, signal_day, day, i: int, equity_ref: float):
        cfg = self.cfg
        sector_count = {}
        for p in self.positions.values():
            sector_count[p.sector] = sector_count.get(p.sector, 0) + 1
        for sym, row in pending.iterrows():
            if len(self.positions) >= cfg.max_positions:
                break
            if sym in self.positions:
                continue
            sector = self.groups.get(sym, "Other")
            if sector_count.get(sector, 0) >= cfg.max_per_sector:
                continue
            o = self.O[i, self.cols[sym]]
            if np.isnan(o) or np.isnan(row.atr) or row.atr <= 0:
                continue
            px = costs.buy_fill(o, cfg)
            stop = px - cfg.stop_atr * row.atr
            if stop <= 0:
                continue
            risk_rs = equity_ref * cfg.risk_pct / 100 * mult
            qty = math.floor(risk_rs / (px - stop))
            qty = min(qty, math.floor(equity_ref * cfg.max_position_pct / 100 / px))
            while qty > 0 and px * qty + costs.buy_cost(px * qty, cfg) > self.cash:
                qty = math.floor(qty * 0.95) if qty > 20 else qty - 1
            if qty < 1:
                continue
            charge = costs.buy_cost(px * qty, cfg)
            self.cash -= px * qty + charge
            self.costs_paid += charge
            p = Position(sym=sym, sector=sector, signal_date=signal_day, entry_date=day, entry_px=px,
                         qty=qty, qty_open=qty, stop=stop, t1_px=px * (1 + cfg.t1_pct / 100),
                         risk_rs=qty * (px - stop), size_mult=mult, cash_flow=-(px * qty + charge))
            p.fills.append((day, "BUY", qty, px, charge, "entry"))
            self.positions[sym] = p
            sector_count[sector] = sector_count.get(sector, 0) + 1


def run_backtest(panels, f, groups, cfg: Config, log=print) -> Result:
    return Backtester(panels, f, groups, cfg, log).run()
