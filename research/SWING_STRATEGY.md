# Swing strategies (1–4 week holds): honest out-of-sample test

*8 Oct 2026. Code: `research/scripts/swing_backtest.py`. Trades and equity curves: `research/swing/`. Spreadsheet: `research/swing/swing_results.xlsx`.*

> **Result: none of the four strategies is profitable out of sample.**
>
> The strategy chosen on 2021–24 data (trend pullback) **lost 44.5% on the fund-screened 424-stock list in Jul 2024 – Oct 2026**, after full delivery charges. On your original 597-stock list, three strategies made about **+18% a year in 2021–24, then all four lost money in 2024–26**.
>
> Almost every rupee of profit came from **2023**, an exceptional small/mid-cap bull year. These long-only swing rules make money in strong bull markets and give it back otherwise. No rule was loosened or re-tuned after seeing the test results.

---

## 1. Protocol (fixed before any results were seen)

**Stock lists:**
- **Primary:** the 424 fund-screened stocks (`research/universe500/universe_500.csv`).
- **Robustness:** the original 597-stock list.

**Data:** daily candles, Oct 2020 – 7 Oct 2026.

**Periods:**
- **Training:** 1 Aug 2021 – 30 Jun 2024. The best strategy is chosen here only.
- **Test:** 1 Jul 2024 – 7 Oct 2026. Reported once, for all strategies.

**Portfolio:**
- ₹5,00,000, 10 equal slots of about ₹50,000, long only.
- At most 3 positions per industry.
- New entries only when Nifty is above its 200-day average.
- Point-in-time liquidity: median turnover of at least ₹1 Cr.

**Execution:**
- Signal at the close, entry at the next open.
- A gap through the stop fills at the open.

**Exits:**
- Initial stop: 2 × ATR (3 × ATR for S3; for S2, below the 5-day low).
- Trailing stop: 3 × ATR below the highest close since entry.
- **Forced exit after 20 trading days (4 weeks).**

**Costs, on every trade:**
- STT 0.1% on buy and sell, exchange and SEBI fees, stamp duty 0.015%, GST, ₹20 brokerage per order, demat charge ₹15.93 per sell.
- Slippage of **0.10% per side** for the small-cap 424 list and 0.05% for the 597 list.

**The four strategies (parameters from standard practice, never tuned):**

| | Strategy | Entry rule |
|---|---|---|
| S1 | Momentum breakout | Price above 50 SMA above 200 SMA; top 20% 6-month relative strength; within 10% of the 52-week high; close above the prior 20-day high on ≥ 1.5× average volume |
| S2 | Trend pullback | Same uptrend; RS top 30%; low touched the 20 EMA in the last 3 days; RSI(14) 40–60; reversal day (close above the previous day's high and the 20 EMA). Extra exit: close below the 50 SMA |
| S3 | Weekly momentum rotation | Every Friday, buy the top 10 by 3-month/6-month return among stocks above their 200 SMA. Extra exit: drops out of the top 30 |
| S4 | Squeeze breakout | Uptrend; Bollinger width in the lowest 20% of 120 days; close above the upper band and the 20-day high on ≥ 1.5× volume |

## 2. Results (all after charges)

### 424 fund-screened stocks (primary)

| Strategy | Training 2021–24 | **Test 2024–26** | Test trades | Test win rate | Test avg win / avg loss | Test profit factor |
|---|---|---|---|---|---|---|
| S1 Momentum breakout | −16.7% | **−14.2%** | 235 | 36% | +14.6% / −8.8% | 0.89 |
| **S2 Trend pullback (chosen on training)** | **+30.8%** (9.7% a year) | **−44.5%** | 353 | 20% | +14.5% / −5.6% | 0.64 |
| S3 Weekly rotation | −7.7% | **−5.5%** | 200 | 40% | +14.0% / −9.7% | 0.95 |
| S4 Squeeze breakout | −31.4% | **+10.5%** | 201 | 30% | +17.2% / −6.7% | 1.11 |
| *Nifty 50 buy and hold* | *+51.2%* | *−6.4%* | | | | |
| *Equal-weight all 424 stocks* | *+131.8%\** | *+18.3%\** | | | | |

### Your 597-stock list (robustness)

| Strategy | Training 2021–24 | **Test 2024–26** | Test profit factor |
|---|---|---|---|
| S1 Momentum breakout | +63.5% (18.4% a year) | **−12.9%** | 0.85 |
| S2 Trend pullback | +60.7% (17.7% a year) | **−8.4%** | 0.93 |
| S3 Weekly rotation | +61.8% (18.0% a year) | **−5.2%** | 0.94 |
| S4 Squeeze breakout | −12.3% | **−20.3%** | 0.74 |

\* The equal-weight figures are **heavily inflated by look-ahead**. Both lists were built *today* from stocks that survived and look healthy now, which flatters buy-and-hold over past years. The strategy results carry the same bias, which makes the losses even more telling.

**S4's +10.5% on the 424 list is not an edge.** It lost 31% in training on the same stocks and lost 20% on the 597 list in the same test period. It was not chosen in advance, and picking it now would be exactly the "bypass the rules" the brief forbids.

## 3. Why they failed: one good year, then losses

| Profit and loss by exit year | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|
| S2 on the 424 list | −₹42,647 | −₹19,034 | **+₹2,11,637** | −₹24,598 | −₹1,62,017 | −₹31,843 |
| S1 on the 597 list | +₹15,858 | +₹9,348 | **+₹2,05,757** | −₹9,475 | −₹7,415 | +₹38,825 |

- **2023 was a strong small/mid-cap rally.** Breakouts and pullbacks kept working, and 20-day holds captured +12% to +14% moves.
- **From mid-2024 small caps peaked and fell,** while Nifty stayed above its 200-day average on 58% of test days. The market filter kept the strategies trading into a falling small-cap market.
- **The win rate collapsed** to 20–37%, and stops (−5% to −9% each after gaps and costs) outweighed the winners.
- **Costs are not the main problem here.** On a ₹50,000 position a round trip costs about 0.45–0.55%, small next to ±8–15% moves. The problem is direction: long-only swing strategies need a rising market.

## 4. What this does *not* mean, and what to do next

- These are four standard, untuned strategies. The finding is that **none of them has a stable edge** across 2021–26 on these stocks. That doesn't prove no swing strategy can work.
- Any further idea (for example a small-cap regime filter or a market-breadth filter) must be **designed on 2021–24 only and judged on 2024–26**, and reported even if it fails. Trying many ideas until one passes the test period would quietly turn the test period into training data.
- **Recommendation:**
  - Do not trade any of these four live.
  - The realistic options are:
    1. one pre-registered regime-filter variant, tested under exactly the same protocol;
    2. a longer-horizon approach (monthly momentum with 1–3 month holds), which the academic evidence supports better than 1–4 week swings;
    3. accept index investing as the benchmark to beat. Nifty lost 6.4% in the test period. Only S3 (about −5%) and S4 on the 424 list did better, and neither is a reliable edge.
