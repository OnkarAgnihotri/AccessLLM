"""Backtest statistics, monthly table, equity chart and a Markdown summary."""

import os

import numpy as np
import pandas as pd

from .config import as_dict


def _max_drawdown(series: pd.Series):
    peak = series.cummax()
    dd = series / peak - 1
    trough = dd.idxmin()
    peak_day = series.loc[:trough].idxmax()
    return 100 * dd.min(), peak_day, trough


def _cagr(series: pd.Series) -> float:
    years = (series.index[-1] - series.index[0]).days / 365.25
    return 100 * ((series.iloc[-1] / series.iloc[0]) ** (1 / years) - 1) if years > 0 else np.nan


def _longest_run(flags) -> int:
    best = cur = 0
    for x in flags:
        cur = cur + 1 if x else 0
        best = max(best, cur)
    return best


def stats(res, index_close: pd.Series) -> dict:
    eq, tr, cfg = res.equity.equity, res.trades, res.cfg
    daily = eq.pct_change().dropna()
    dd, dd_peak, dd_trough = _max_drawdown(eq)
    bench = index_close.reindex(eq.index).ffill()
    bdd, _, _ = _max_drawdown(bench)
    s = {
        "period": f"{eq.index[0].date()} to {eq.index[-1].date()}",
        "start_capital": cfg.capital,
        "final_equity": round(eq.iloc[-1], 0),
        "total_return_pct": round(100 * (eq.iloc[-1] / cfg.capital - 1), 2),
        "cagr_pct": round(_cagr(eq), 2),
        "max_drawdown_pct": round(dd, 2),
        "max_drawdown_window": f"{dd_peak.date()} to {dd_trough.date()}",
        "sharpe": round(np.sqrt(252) * daily.mean() / daily.std(), 2) if daily.std() > 0 else np.nan,
        "avg_capital_in_use_pct": round(100 * (res.equity.invested / res.equity.equity).mean(), 1),
        "nifty_return_pct": round(100 * (bench.iloc[-1] / bench.iloc[0] - 1), 2),
        "nifty_cagr_pct": round(_cagr(bench), 2),
        "nifty_max_drawdown_pct": round(bdd, 2),
        "total_charges_rs": round(res.equity.attrs.get("costs_paid", 0.0), 0),
    }
    if tr.empty:
        s["trades"] = 0
        return s
    win = tr.pnl > 0
    s.update({
        "trades": len(tr),
        "trades_per_month": round(len(tr) / max(1, len(eq) / 21), 1),
        "win_rate_pct": round(100 * win.mean(), 1),
        "first_target_hit_pct": round(100 * tr.first_target_hit.mean(), 1),
        "avg_win_pct": round(tr.return_pct[win].mean(), 2),
        "avg_loss_pct": round(tr.return_pct[~win].mean(), 2) if (~win).any() else 0.0,
        "avg_trade_pct": round(tr.return_pct.mean(), 3),
        "avg_trade_rs": round(tr.pnl.mean(), 0),
        "expectancy_r": round(tr.r_multiple.mean(), 3),
        "profit_factor": round(tr.pnl[win].sum() / -tr.pnl[~win].sum(), 2) if (~win).any() else np.inf,
        "best_trade_pct": round(tr.return_pct.max(), 2),
        "worst_trade_pct": round(tr.return_pct.min(), 2),
        "avg_days_held": round(tr.days_held.mean(), 1),
        "longest_losing_streak": _longest_run(~win),
        "exit_reasons": tr.exit_reason.value_counts().to_dict(),
    })
    return s


def monthly_table(eq: pd.Series) -> pd.DataFrame:
    m = eq.resample("ME").last()
    first = pd.Series([eq.iloc[0]], index=[m.index[0] - pd.offsets.MonthEnd(1)])
    r = pd.concat([first, m]).pct_change().dropna() * 100
    t = pd.DataFrame({"year": r.index.year, "month": r.index.strftime("%b"), "ret": r.values})
    order = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    p = t.pivot(index="year", columns="month", values="ret").reindex(columns=order)
    y = eq.resample("YE").last()
    y = pd.concat([pd.Series([eq.iloc[0]], index=[y.index[0] - pd.offsets.YearEnd(1)]), y]).pct_change().dropna() * 100
    p["Year"] = y.values
    return p.round(2)


def yearly_trades(tr: pd.DataFrame) -> pd.DataFrame:
    if tr.empty:
        return pd.DataFrame()
    t = tr.assign(year=pd.to_datetime(tr.exit_date).dt.year)
    g = t.groupby("year")
    return pd.DataFrame({
        "trades": g.size(),
        "win_rate_pct": g.pnl.apply(lambda x: 100 * (x > 0).mean()),
        "avg_trade_pct": g.return_pct.mean(),
        "pnl_rs": g.pnl.sum(),
        "profit_factor": g.pnl.apply(lambda x: x[x > 0].sum() / -x[x <= 0].sum() if (x <= 0).any() else np.inf),
    }).round(2)


def regime_table(tr: pd.DataFrame) -> pd.DataFrame:
    if tr.empty:
        return pd.DataFrame()
    g = tr.assign(market=np.where(tr.size_mult < 1, "amber (index below SMA)", "green")).groupby("market")
    return pd.DataFrame({"trades": g.size(), "win_rate_pct": g.pnl.apply(lambda x: 100 * (x > 0).mean()),
                         "avg_trade_pct": g.return_pct.mean(), "pnl_rs": g.pnl.sum()}).round(2)


def plot(res, index_close: pd.Series, path: str):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    eq = res.equity.equity
    bench = index_close.reindex(eq.index).ffill()
    bench = bench / bench.iloc[0] * res.cfg.capital
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(11, 7), sharex=True, gridspec_kw={"height_ratios": [3, 1]})
    a1.plot(eq.index, eq / 1e5, label="Leaders' Pullback", color="#2563eb", lw=1.6)
    a1.plot(bench.index, bench / 1e5, label="Nifty 50 (buy & hold)", color="#9ca3af", lw=1.2)
    a1.set_ylabel("Equity (Rs lakh)")
    a1.legend(loc="upper left")
    a1.grid(alpha=0.3)
    a1.set_title("Leaders' Pullback backtest")
    dd = 100 * (eq / eq.cummax() - 1)
    a2.fill_between(dd.index, dd, 0, color="#dc2626", alpha=0.4)
    a2.set_ylabel("Drawdown %")
    a2.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def write(res, index_close: pd.Series, out_dir: str) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    s = stats(res, index_close)
    res.trades.to_csv(os.path.join(out_dir, "trades.csv"), index=False)
    res.equity.to_csv(os.path.join(out_dir, "equity.csv"))
    mt = monthly_table(res.equity.equity)
    mt.to_csv(os.path.join(out_dir, "monthly_returns.csv"))
    yt, rt = yearly_trades(res.trades), regime_table(res.trades)
    plot(res, index_close, os.path.join(out_dir, "equity_curve.png"))

    def md(df):
        if df.empty:
            return "_none_"
        head = "| " + " | ".join([str(df.index.name or "")] + [str(c) for c in df.columns]) + " |"
        rows = ["| " + " | ".join([str(i)] + ["" if pd.isna(v) else str(v) for v in r]) + " |"
                for i, r in zip(df.index, df.values)]
        return "\n".join([head, "|" + "---|" * (len(df.columns) + 1)] + rows)

    lines = ["# Leaders' Pullback - backtest summary", "", "## Results", "",
             "| Metric | Value |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in s.items()]
    lines += ["", "## Monthly returns (%)", "", md(mt), "", "## By year (closed trades)", "", md(yt),
              "", "## By market light", "", md(rt), "", "## Settings", "", "| Setting | Value |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in as_dict(res.cfg).items()]
    lines += ["", "![equity curve](equity_curve.png)", ""]
    with open(os.path.join(out_dir, "summary.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    return s
