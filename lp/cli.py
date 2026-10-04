"""Command line: python -m lp <command> [options]

  fetch      download / update daily data for every stock in the metadata file, plus Nifty
  backtest   run the portfolio backtest and write a report folder

Examples (Windows):
  python -m lp fetch --data-dir C:\\Users\\onkar\\Desktop\\Stock_data\\lp_data
  python -m lp backtest --data-dir C:\\Users\\onkar\\Desktop\\Stock_data\\lp_data --capital 500000
  python -m lp backtest --set t1_pct=1.5 --set stop_atr=2 --out bt_t15_s2
"""

import argparse
import os
import sys

from .config import load_config


def _common(ap):
    ap.add_argument("--config", default="config.yaml", help="YAML settings file (optional)")
    ap.add_argument("--data-dir", help="data cache folder")
    ap.add_argument("--metadata", help="stock list JSON (default: all_profile_metadata.json)")
    ap.add_argument("--set", action="append", default=[], metavar="KEY=VALUE",
                    help="override any setting, e.g. --set t1_pct=1.5 (repeatable)")


def _cfg(args, **extra):
    over = dict(data_dir=args.data_dir, metadata=args.metadata, **extra)
    for kv in args.set:
        if "=" not in kv:
            sys.exit(f"--set needs KEY=VALUE, got {kv!r}")
        k, v = kv.split("=", 1)
        over[k.strip()] = v.strip()
    try:
        return load_config(args.config, **over)
    except ValueError as e:
        sys.exit(str(e))


def cmd_fetch(args):
    from .data import load_universe, fetch
    cfg = _cfg(args)
    syms = list(load_universe(cfg.metadata))
    print(f"Updating daily data for {len(syms)} stocks + {cfg.index_symbol} in {cfg.data_dir}")
    n = fetch([cfg.index_symbol] + syms, cfg.data_dir, "1d", cfg.history_period)
    print(f"Done: {n} files written")


def cmd_backtest(args):
    from .data import load_universe, load_panels
    from .sectors import sector_group
    from . import signals, backtest, report

    cfg = _cfg(args, capital=args.capital, start=args.start, end=args.end)
    universe = load_universe(cfg.metadata)
    groups = {s: sector_group(lbl) for s, lbl in universe.items()}
    panels, index_close = load_panels(list(universe), cfg.data_dir, cfg.index_symbol,
                                      min_bars=cfg.sma_long + 20)
    print("Computing indicators and setups ...")
    f = signals.compute(panels, index_close, cfg)
    print("Simulating ...")
    res = backtest.run_backtest(panels, f, groups, cfg)
    s = report.write(res, index_close, args.out)
    width = max(len(k) for k in s)
    print()
    for k, v in s.items():
        print(f"  {k:<{width}}  {v}")
    print(f"\nReport written to {os.path.abspath(args.out)} "
          "(summary.md, trades.csv, equity.csv, monthly_returns.csv, equity_curve.png)")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m lp", description="Leaders' Pullback trading system")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("fetch", help="download / update daily price data")
    _common(p)
    p.set_defaults(func=cmd_fetch)

    p = sub.add_parser("backtest", help="run the portfolio backtest")
    _common(p)
    p.add_argument("--capital", type=float, help="starting capital in rupees")
    p.add_argument("--start", help="first trading day, YYYY-MM-DD")
    p.add_argument("--end", help="last trading day, YYYY-MM-DD")
    p.add_argument("--out", default="backtest_results", help="output folder")
    p.set_defaults(func=cmd_backtest)

    args = ap.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
