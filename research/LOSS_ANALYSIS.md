# Loss forensics and v2: NSE intraday ORB / VWAP strategy

*8 Oct 2026. The data is 5-minute candles for 158 liquid stocks plus Nifty, 16 Jul – 7 Oct 2026 (58 trading days). The ₹ figures use ₹25,000 per trade with no margin, and full MIS charges plus 0.03% slippage on each side.*

> **Bottom line.**
> - The v1 playbook lost mainly because **its stops were far too tight**: 16 of 46 trades were stopped out inside the candle they were entered on.
> - A simpler v2 made money in both halves of the test period: **trade only on narrow-CPR days, only stocks that actually move, with a 2 × ATR stop.**
>   - At ₹25,000 per trade, v2 went from −₹2,297 (v1) to **+₹3,659 over 58 trades** (57% winners).
>   - With R-based sizing on ₹5 lakh, it made **+8.75% with a −2.8% maximum drawdown** (v1: −11.9%).
> - **It is still a hypothesis.**
>   - The sample is 58 trades over 32 days, and 3 trades make about 65% of the profit.
>   - About 140 variants were tried to find v2.
>   - It needs years of 5-minute data and paper trading before real money.

---

## 1. Why v1 lost: the 33 losing trades (v1, 46 trades)

### Top reasons, in ₹ at ₹25,000 per trade

| # | Main cause (exact rule in `research/intraday_backtest/v1_loss_causes.csv`) | Losers | ₹ lost |
|---|---|---|---|
| 1 | **Noise stop**: stop under 1.2 ATR away, and price then moved ≥ 1R in our direction within 60 minutes | 9 | −895 |
| 2 | **False breakout**: never got 0.3R in our favour, stopped within 15 minutes | 5 | −482 |
| 3 | **Late / extended entry**: entry more than 1.5 ATR beyond VWAP, or a breakout candle more than 2 ATR long | 5 | −465 |
| 4 | Gave back profit: reached ≥ 1R, then finished at a loss | 3 | −458 |
| 5 | Normal loss (setup valid, market didn't follow) | 4 | −435 |
| 6 | Nifty moved against the trade in the 30 minutes after entry | 2 | −326 |
| 7 | Costs turned a small gross profit into a loss | 5 | −77 |
| | **Total** | **33** | **−3,138** (winners +945 → net −2,193 in this rebuild) |

**The root cause sits underneath causes 1, 2, 3 and 7: the playbook's stop rule.** It put the stop just under the breakout candle or at the opening-range midpoint, and the median losing stop was **0.20% of price**.

- **16 of 46 trades** were stopped inside their own entry candle, costing −₹1,284.
- Stops ≤ 0.15% of price won **1 of 16 times (6%)**. Stops above 0.30% won 47% of the time.
- **9 losers moved at least 1R our way within an hour after being stopped out.** The direction was right; the stop was inside normal noise.

### Winners vs losers (v1 medians; small samples, so read these as hypotheses)

| Feature | Winners (13) | Losers (33) |
|---|---|---|
| Stop distance, % of price | **0.38** | **0.20** |
| 5-minute ATR, % of price (how much the stock moves) | **0.64** | **0.33** |
| RS vs Nifty since the open, % | **3.7** | **1.3** |
| Opening RVol | 2.9× | 2.1× |
| Breakout distance beyond the opening range (ATR) | 2.5 | 0.8 |

- Entries before 10:00 won 17% of the time, against about 32% later in the day.
- The VWAP-pullback setup won 19% of the time.
- Shorts won 20%, against 32% for longs.

### Every losing trade

| Stock | Setup | Side | Entry | Held (min) | Stop % of price | Best move reached (R) | Distance from VWAP (ATR) | Move our way within 60 min after exit (R) | Net ₹ | Main cause |
|---|---|---|---|---|---|---|---|---|---|---|
| CAMS | ORB | LONG | 07-31 09:40 | 20 | 0.10 | 6.18 | 0.4 | 2.5 | -15 | costs flipped it |
| HBLENGINE | VWAP | LONG | 07-31 10:50 | 160 | 0.41 | 0.35 | 0.4 | -0.1 | -143 | other (normal loss) |
| GAIL | ORB | LONG | 07-31 11:20 | 0 | 0.15 | 0.00 | 3.1 | 2.1 | -78 | noise stop (tight stop, then went our way) |
| NTPC | VWAP | LONG | 08-05 10:55 | 0 | 0.12 | 0.00 | 0.1 | 0.0 | -70 | false breakout (failed immediately) |
| ZYDUSLIFE | ORB | LONG | 08-05 11:15 | 0 | 0.26 | 0.00 | 3.4 | -1.9 | -104 | late / extended entry |
| CASTROLIND | VWAP | LONG | 08-06 10:05 | 10 | 0.39 | 0.01 | 1.0 | -0.6 | -138 | false breakout (failed immediately) |
| ASTERDM | ORB | LONG | 08-06 10:10 | 25 | 0.61 | 1.11 | 3.4 | -0.7 | -187 | gave back profit |
| WELCORP | ORB | LONG | 08-07 09:55 | 5 | 0.20 | 1.10 | 1.0 | 4.1 | -87 | gave back profit |
| VAML | VWAP | SHORT | 08-07 10:25 | 10 | 0.24 | 0.22 | 0.4 | 3.1 | -101 | noise stop (tight stop, then went our way) |
| PFC | VWAP | SHORT | 08-13 10:30 | 15 | 0.10 | 1.53 | 0.3 | 1.4 | -19 | costs flipped it |
| BSE | VWAP | SHORT | 08-17 11:10 | 0 | 0.19 | 0.00 | 0.2 | 1.2 | -83 | noise stop (tight stop, then went our way) |
| MFSL | VWAP | LONG | 08-25 11:15 | 0 | 0.13 | 0.00 | 0.5 | 1.0 | -70 | false breakout (failed immediately) |
| CGCL | ORB | LONG | 08-26 09:50 | 0 | 0.25 | 0.00 | 0.7 | 7.1 | -104 | noise stop (tight stop, then went our way) |
| SBICARD | ORB | LONG | 08-26 09:55 | 5 | 0.08 | 3.16 | 0.2 | 9.9 | -21 | costs flipped it |
| PFC | ORB | SHORT | 08-27 11:15 | 10 | 0.13 | 0.32 | 0.6 | -0.2 | -74 | other (normal loss) |
| BALRAMCHIN | VWAP | SHORT | 09-02 09:55 | 85 | 0.93 | 0.61 | 0.8 | -0.4 | -271 | Nifty moved against |
| SWIGGY | VWAP | LONG | 09-04 09:55 | 315 | 1.35 | 1.43 | 1.7 | 0.4 | -183 | gave back profit |
| MEESHO | VWAP | LONG | 09-04 10:05 | 0 | 0.26 | 0.00 | 0.4 | 5.5 | -107 | noise stop (tight stop, then went our way) |
| GRANULES | ORB | LONG | 09-04 10:45 | 10 | 0.34 | 0.00 | 3.3 | 1.0 | -127 | late / extended entry |
| GRANULES | ORB | LONG | 09-04 11:20 | 0 | 0.07 | 0.00 | 3.6 | 0.0 | -56 | late / extended entry |
| CAMS | VWAP | SHORT | 09-09 11:00 | 15 | 0.08 | 3.21 | 0.3 | 2.0 | -17 | costs flipped it |
| CAMS | ORB | SHORT | 09-09 11:30 | 0 | 0.15 | 0.00 | 0.5 | 0.1 | -4 | costs flipped it |
| LT | VWAP | SHORT | 09-10 10:50 | 105 | 0.27 | 0.48 | 1.4 | -1.1 | -102 | other (normal loss) |
| INDUSTOWER | ORB | SHORT | 09-10 11:10 | 0 | 0.10 | 0.00 | 2.9 | 2.0 | -66 | noise stop (tight stop, then went our way) |
| BPCL | ORB | SHORT | 09-11 11:00 | 5 | 0.05 | 0.94 | 1.4 | -0.3 | -55 | Nifty moved against |
| BEL | ORB | SHORT | 09-15 11:30 | 0 | 0.13 | 0.00 | 3.1 | 0.7 | -73 | late / extended entry |
| KISSHT | ORB | LONG | 09-16 11:20 | 10 | 0.59 | 0.02 | 3.1 | 1.9 | -196 | noise stop (tight stop, then went our way) |
| PINELABS | ORB | LONG | 09-17 09:35 | 0 | 0.47 | 0.00 | 1.2 | -1.8 | -158 | false breakout (failed immediately) |
| PFOCUS | ORB | LONG | 09-17 10:10 | 0 | 0.09 | 0.00 | 2.6 | 32.8 | -64 | noise stop (tight stop, then went our way) |
| PINELABS | ORB | LONG | 09-22 09:50 | 0 | 0.25 | 0.00 | 1.5 | -5.8 | -104 | late / extended entry |
| TRENT | ORB | SHORT | 09-29 10:30 | 0 | 0.03 | 0.00 | 0.7 | -4.5 | -46 | false breakout (failed immediately) |
| BHEL | ORB | LONG | 10-06 10:10 | 0 | 0.22 | 0.00 | 1.1 | 1.2 | -97 | noise stop (tight stop, then went our way) |
| JSWENERGY | VWAP | LONG | 10-06 11:05 | 35 | 0.30 | 0.96 | 0.3 | -0.8 | -115 | other (normal loss) |

*Held 0 minutes means the stop was hit in the entry candle itself. The time of the half-exit at Target 1 isn't logged separately.*

---

## 2. What-if tests on the same entries (Step 4)

Two sets of entries were tested:
- **PLAYBOOK:** the v1 filters (about 50 trades).
- **RVOL ≥ 1.5:** only the core pattern plus the opening-volume filter (about 500 trades, much more statistical power).

The first 60% of days runs 16 Jul – 1 Sep and the last 40% runs 2 Sep – 7 Oct. All figures are ₹ net at ₹25,000 per trade.

| Exit rule | PLAYBOOK net (first 60% / last 40%) | RVOL≥1.5 net (first 60% / last 40%) |
|---|---|---|
| v1: structural stop, Target 1 at 1.5R, 9-EMA trail | −2,927 (−1,045 / −1,882) | −25,234 |
| Stop with a minimum distance (1 ATR / 0.4%) | −1,993 | −21,399 |
| Stop 1.5 × ATR | −1,592 | −20,038 |
| **Stop 2 × ATR** | **−144 (+447 / −592)** | −22,509 |
| Stop at the opening range's far side | −1,598 | −15,028 |
| Exit on a candle close beyond VWAP | −850 | −21,722 |
| Target 1 at 1R or 2R instead of 1.5R | −2,393 / −2,501 | −23,079 / −21,613 |
| No partial exit, full exit at 1.5R | −754 | −22,639 |
| Time stop: exit if not +0.5R within 30 minutes | −1,322 | −21,875 |

**Wider stops are the biggest single fix.** But on the broad entry set, every exit rule still loses, which means the core breakout and pullback patterns have no edge before costs on their own. The improvement has to come from **which days and which stocks** get traded.

## 3. Entry-filter tests (Step 5) and combinations (Step 6)

Tested with a 2 × ATR stop. The full tables are in `step5_filters.csv` and `step6_combos.csv`.

| Filter (added on its own) | PLAYBOOK net | RVOL≥1.5 net | Consistent? |
|---|---|---|---|
| None | −144 | −22,509 | |
| **5-minute ATR ≥ 0.4% of price** | **+1,939** (+1,086 / +853) | −7,337 (best single filter) | ✓ both sets improve |
| **Narrow CPR (< 0.25%)** | **+789** (+539 / +250) | −2,772 | ✓ |
| RVol ≥ 3 | +495 | −3,680 | ✓ |
| RS vs Nifty ≥ 2% | +2,043 | −10,678 | ✗ helps only on the playbook set |
| Longs only | +1,638 | −14,212 | ✗ |
| Setup B (VWAP pullback) only | −824 | −6,178 | ✗ B loses on its own |
| No entry before 10:00 / after 11:00 | +80 / −105 | −16,003 / −17,995 | weak |
| Within 1 ATR of VWAP | −858 | −10,413 | ✗ |
| Two closes beyond the level | +978 | −20,456 | ✗ |

**The only combination that is positive in both entry sets, both halves of the data and with every stop type tested:**

| 5-minute ATR ≥ 0.4% + narrow CPR, RVOL≥1.5 entries | Trades | Win % | Net ₹ | Profit factor | First 60% / last 40% |
|---|---|---|---|---|---|
| Stop 2 × ATR | 59 | 56% | **+3,383** | 1.40 | +2,124 / +1,259 |
| Stop 1.5 × ATR | 62 | 52% | +1,167 | 1.14 | +945 / +223 |
| Stop at the opening range's far side | 55 | 60% | +3,246 | 1.30 | +1,645 / +1,601 |

**Why this makes sense, not just luck:**
- A **narrow CPR** marks days where yesterday's range was compressed, which classic pivot theory treats as likely trend days.
- A **5-minute ATR ≥ 0.4%** keeps only stocks that move enough for a 1.5R target to clear about 0.17% of costs.
- A **2 × ATR stop** sits outside normal 5-minute noise, which removes cause 1.

**Overfitting check:**
- About **140 variants** were run (28 exit tests, 68 filter tests, 42 combinations).
- v2 was chosen because it was positive in every split, not because it had the highest number.
- Even so, with 58 trades, chance can't be ruled out.

## 4. v2 rules (changes from v1)

| Rule | v1 | **v2** |
|---|---|---|
| Day filter | CPR ≤ 0.6% (ORB only) | **CPR width ≤ 0.25%, for both setups** |
| Stock filter | ATR(daily) ≥ 1.5% | plus **5-minute ATR ≥ 0.4% of price** on the signal candle |
| Stop | Structural: signal candle / opening-range midpoint, often 0.1–0.2% | **2 × ATR(5m) from entry** (about 0.8–1.2% of price) |
| RS vs Nifty, Nifty 21-EMA bias, daily EMA trend, 2R room check | Required | **Removed** (they cut trades without a consistent benefit) |
| Unchanged | | 15-minute opening range, VWAP side, 9/21 EMA, RSI 60–80 / 20–40, volume surge, RVol ≥ 1.5, time windows, 50% at 1.5R, stop to cost, 9-EMA trail, 15:10 flat, desk limits |

**Code changes:**
- **Backtest:** `research/scripts/intraday_backtest.py --v2`. New options: `--stop-atr`, `--min-atr-pct`, `--cpr-on-b`; v1 is still the default and reproduces exactly.
- **Pine Script:** `pine/nse_vwap_orb_pullback.pine` now defaults to v2. The new inputs are "stop = N × ATR", "min ATR %" and a CPR limit that now applies to both setups, and RS / index / daily / room are off by default. The header explains how to switch back to v1.

## 5. v1 vs v2, same period, same costs

**At ₹25,000 per trade, no margin** (`trades_25k_v1_vs_v2.xlsx`):

These figures come from the main backtest engine, which applies the desk limits. The forensics engine has no desk limits, so in §3 it shows 59 trades and +₹3,383.

| | v1 playbook | **v2** |
|---|---|---|
| Trades | 46 | 58 |
| Winners | 12 (26%) | **33 (57%)** |
| Gross ₹ | −342 | +6,159 |
| Charges ₹ | 1,955 | 2,500 |
| **Net ₹** | **−2,297** | **+3,659** |
| Average net per trade | −₹50 | **+₹63** |
| 16 Jul – 1 Sep / 2 Sep – 7 Oct | −987 / −1,310 | **+2,409 / +1,249** |
| Best 3 trades | +581 | +2,394 (65% of the profit) |

**With R-based sizing** (₹5 lakh, 0.5% risk, desk limits; `intraday_backtest.py`): v1 **−11.86%** (max drawdown −12.4%) vs v2 **+8.75%** (max drawdown −2.8%). v2 averaged +0.30R per trade net and had a profit factor of 1.71.

**v2 by setup:**
- ORB longs: 42 trades, +0.28R each.
- ORB shorts: 10 trades, **−0.20R each**.
- VWAP pullback: 6 trades, all winners. Too few to judge.

## 6. Plain-language summary

- **What went wrong.** v1's stops were set so close that ordinary 5-minute wiggles knocked trades out. Often the move then went our way without us. Tight stops also meant big positions relative to the risk, so charges ate a large share of each trade. And the core breakout pattern by itself has no edge on these stocks.
- **What to change.**
  1. Give trades room: a 2 × ATR stop.
  2. Only trade stocks that are actually moving: 5-minute ATR ≥ 0.4%.
  3. Only trade on narrow-CPR (trend-likely) days.
  4. Drop the extra filters that only cut trades.
- **Is v2 worth testing further? Yes, but not trading yet.** It was profitable in both halves of the period and in both test engines. But it rests on 58 trades, a few big winners, weak ORB shorts and a small pullback sample.
- **Next steps:**
  1. Load 1–3 years of 5-minute data (Dhan or Kite) and rerun `--v2` unchanged.
  2. If it stays positive, paper-trade it for 4 weeks.
  3. Consider running it as long-only if the longer test confirms that ORB shorts are weak.
