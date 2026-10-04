# A-C-B-D scanner: why so few setups, and what loosening does

## Where setups were lost (strict rules, 1h, 3 years, 567 stocks)

Counts are per candidate B. The final scan merges duplicates, so it reports fewer.

| Stage | Candidates left |
|---|---|
| B is a pivot high | 82,338 |
| B has the bull stack (close > 9 > 20 > 200 SMA) | 29,844 |
| 9/20 bear cross within 15 bars of B | 23,664 |
| A found 150–600 bars earlier | 10,008 |
| A has the bull stack and its own cross | 7,304 |
| C has the bear stack | 5,938 |
| B in the 0.382–0.618 fib zone | 2,346 |
| **D found** | **146** |
| **Entered** | **16** |

Why D was not found:
- no close below the 200 SMA within 60 bars: 769
- resistance phase too short: 612
- no clean 20 SMA resistance: 577
- no valid D: 196

Of the 146 D's, **86 were "D broken"**: price undercut D before the breakout. That is the single biggest loss at the end. The 15m data shows the same pattern: 20 D's found, 16 of them broken.

## Presets (`--preset`)

| Preset | What changes |
|---|---|
| strict | the original SOLARA/SKYGOLD calibration |
| moderate | redraw D when it is undercut (up to 3 times), resistance at least 3 bars with 2 touches and 4.5% above the 20 SMA (scaled per timeframe), D within 100 bars of B and within 20 bars of the 200 break, 9/20 cross within 25 bars, breakout candle 3.6% (scaled), base range 15%, entry within 60 bars |
| loose | moderate, plus B fib up to 0.786, D fib up to 0.618, A–B at least 100 bars |

Also fixed: a breakout candle that already closes above the target no longer counts as a trade.

## Results

Settings: ₹25,000 capital, 1% risk per trade, 0.35% / 0.15% costs plus ₹15 / ₹47 per trade.

| TF | Preset | Setups | Trades | Win % | Avg net/trade | Profit factor | ₹25k at 1% risk |
|---|---|---|---|---|---|---|---|
| 1d (6y) | strict | 14 | 2 | 100 | +38.8% | n/a | +₹1,825 |
| 1d | moderate | 33 | 12 | 58 | +13.8% | 3.33 | +₹2,858 |
| 1d | loose | 90 | 36 | 39 | +6.0% | 1.74 | +₹4,374 |
| 1h (3y) | strict | 79 | 10 | 20 | −3.4% | 0.42 | −₹657 |
| 1h | moderate | 169 | 70 | 31 | +0.5% | 1.13 | −₹286 |
| 1h | loose | 386 | 168 | 30 | +0.6% | 1.13 | −₹939 |
| 15m (55d) | strict | 13 | 1 | 0 | −4.1% | 0 | −₹242 |
| 15m | moderate | 33 | 10 | 0 | −2.9% | 0 | −₹1,768 |
| 15m | loose | 66 | 17 | 6 | −2.7% | 0.08 | −₹2,763 |

**Daily is the only timeframe where the pattern makes money.**
- Without SKYGOLD and SOLARA (the calibration charts), the loose daily preset still gives 35 trades, a 34% win rate, +3.9% per trade and a profit factor of 1.46. That comes from big winners (+16% to +91%) against stops of about 10%.
- 2026 was a losing year (4 trades, −40% in total).
- Daily trades last about 3–4 months, so they overlap. The "full capital in every trade" numbers in the per-run reports overstate the result.

**1h** is about break-even after costs (a profit factor of 1.13 is less than the 1% risk sizing needs), and 2026 lost money.

**15m** lost money with every preset.

Each run has its own report: `<tf>_<preset>_REPORT.md`.
