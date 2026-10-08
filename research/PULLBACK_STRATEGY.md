# Daily chart pattern + pullback-only strategy: honest test

*8 Oct 2026. Code: `research/scripts/pullback_backtest.py`. Outputs: `research/pullback/` (summaries, every trade, equity curves, `pullback_results.xlsx`).*

> **Result: not profitable.** Reading the trend and pattern on the daily chart and buying only pullbacks lost money in the out-of-sample test (Jul 2024 – Oct 2026), on both stock lists and with both the daily and the 1-hour entry trigger. It also failed to beat Nifty in training. **Do not trade it.**

---

## 1. The rules (fixed before testing; no tuning afterwards)

**Daily chart pattern** (only data available at the signal close):
- **Swing points:** a high or low that is the extreme of the 5 candles on each side, known 5 candles later.
- **Uptrend structure:**
  - the last two swing highs are rising, and the last two swing lows are rising (higher highs, higher lows);
  - price is above the 50 SMA, which is above the 200 SMA;
  - 6-month relative strength is in the top 40%.
- **Pattern P1, trend pullback:**
  - the current up-leg (last swing low L0 to the highest high since) is at least 2 × ATR tall;
  - the high was made 3–15 days ago;
  - today's low retraces 38.2–61.8% of the leg, or touches the 20 EMA;
  - and stays above L0, so the structure is intact.
- **Pattern P2, breakout retest:**
  - a close above the prior 60-day high (level R) happened 3–20 days ago;
  - price has come back within 0.5 ATR of R and is holding it.

**Entry: pullbacks only, on two timeframes.**
- **(A) Daily trigger:** the pattern was active today or yesterday, and today closes green above yesterday's high. Buy at the next open.
- **(B) 1-hour trigger:** the pattern was active at yesterday's close. Buy at the close of the first 1-hour candle (from 10:15) that closes above the previous 1-hour high and above the 1-hour 20 EMA, provided the day's low is still above L0.

**Risk and exits:**
- **Stop:** the lowest low of the last 3 days − 0.25 ATR.
- **First target:** the prior swing high. The target must be at least 1.5 × the risk away, or the trade is skipped.
- **At the first target:** sell 50% and move the stop to cost.
- **The rest:** a 3 × ATR trailing stop.
- **Forced exit** after 20 trading days (4 weeks).

**Portfolio:**
- ₹5,00,000; 1% of equity at risk per trade; a position at most 20% of equity and at least ₹10,000.
- At most 10 positions, 3 per industry.
- New entries only when Nifty is above its 200-day average; median turnover ≥ ₹1 Cr.
- Full delivery charges plus slippage (0.10% per side on the 424 list, 0.05% on the 597 list).

**Testing:**
- **Training:** Aug 2021 – Jun 2024.
- **Test:** Jul 2024 – 7 Oct 2026, run once.
- 1-hour data exists only from Nov 2023, so the 1-hour version also shows a Nov 2023 – Jun 2024 training slice.

## 2. Results (after all charges)

| Run | Daily trigger (A) | 1-hour trigger (B) | Nifty |
|---|---|---|---|
| **Training, 424 list** (Aug 21 – Jun 24) | **−25.6%** (277 trades, 37% wins, profit factor 0.81) | n/a | +51.2% |
| **Training, 597 list** | **+2.1%** (298 trades, 41% wins, profit factor 1.02) | n/a | +51.2% |
| Training slice, 424 list (Nov 23 – Jun 24) | −14.9% (profit factor 0.68) | +4.4% (profit factor 1.09) | +22.0% |
| Training slice, 597 list | +20.2% (profit factor 1.67) | +7.4% (profit factor 1.17) | +22.0% |
| **Test, 424 list** (Jul 24 – Oct 26) | **−41.0%** (144 trades, 27% wins, profit factor 0.43) | **−35.8%** (213 trades, 27% wins, profit factor 0.65) | −6.4% |
| **Test, 597 list** | **−31.4%** (188 trades, 31% wins, profit factor 0.61) | **−25.6%** (214 trades, 31% wins, profit factor 0.73) | −6.4% |

By pattern in the test period, the trend pullback (P1) made up almost all trades and losses. The breakout retest (P2) was rare (3–17 trades per run) and also lost money.

## 3. Why it fails

1. **Pullbacks in small and mid caps from mid-2024 kept falling.** In a falling market for these stocks, a "38–62% retracement in an uptrend" is often the first leg of a trend change. Stops were hit on 60–65% of trades, and the first target was reached only 21–24% of the time.
2. **The daily uptrend filter reacts too late.** Higher highs and higher lows plus the 50/200 SMA stack stay "up" for weeks after a top. Nifty was above its 200-day average on 58% of test days while these stocks were falling.
3. **The 1-hour trigger helps a little but doesn't fix it.** Entering on a 1-hour reversal gave a tighter stop and lost 5–6 points less than the daily trigger. But it can't turn a falling market into a rising one.
4. **Even in training it didn't beat buy and hold.** The 597 list broke even (+2.1%) while Nifty made +51%, so there was no edge to carry forward.

## 4. The honest picture after all the tests in this project

| Strategy family | Out-of-sample result |
|---|---|
| Intraday opening-range breakout / VWAP (v1–v3) | v3 positive on the original list, **negative on 424 new stocks** |
| Leaders' pullback (2–10 days) | Negative after delivery charges |
| Four standard swing strategies (1–4 weeks) | All negative in 2024–26 |
| Daily pattern + pullback (this test) | **Negative, −26% to −41%** |
| ABCD daily pattern (loose preset) | Positive over 6 years, but few trades and a losing 2026 |

**Common thread:** every long-only setup tested here made its money in the 2021–24 bull market (mostly 2023) and lost from mid-2024 onwards. The problem is not the entry pattern or the timeframe. **Buying any kind of dip or breakout stops working when the broad small/mid-cap market turns down.**

## 5. What could work, stated honestly

- **The most important missing piece is a market filter that sees the small/mid-cap downturn.** Examples: the Nifty Smallcap/Midcap index above its 200-day average, or market breadth (% of stocks above their 50-day average) above 50%. That idea comes from *looking at this test period*, so the test period can no longer judge it fairly. It would need:
  - a **new period of data**: older history before 2021, or the next 6–12 months, traded on paper;
  - **or** a different market tested blind.
- **Long-only means some periods should simply be spent in cash.** A strategy that sits out falling markets would have done far better here than any entry rule.
- **More data beats more rules.** Ten-plus years of daily data from a broker or data vendor (including delisted stocks) would allow a proper multi-cycle test. Six years with one bull phase cannot.
