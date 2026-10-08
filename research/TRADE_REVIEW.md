# Trade Review: "Prove it or don't take it"

*CRO review of the v2 intraday strategy, 8 Oct 2026.*
- **Data:** 5-minute candles for 158 liquid NSE stocks and Nifty, 16 Jul – 7 Oct 2026, plus 6 years of daily candles.
- **Trades reviewed:** 58 v2 trades, 46 v1 trades and a pool of 468 trades (all opening-volume ≥ 1.5× entries with the v2 exit).
- **₹ figures:** ₹25,000 per trade, no margin, full charges plus 0.03% slippage per side.
- **Code:** `research/scripts/trade_review.py` (evidence builder) and `research/scripts/intraday_backtest.py --v3`.
- **Data:** `research/intraday_backtest/trade_review.xlsx`.

> **Verdict in one paragraph.**
> Every one of the 25 v2 losing trades had a visible objection at entry. **One objection is backed by the data in all three trade sets and both time halves:** don't trade against the higher-timeframe trend. That is O3: the previous day's 20/50/200 EMA stack is net against the trade, or price is on the wrong side of its 20-week EMA. Adding it as a veto gives **v3**:
>
> | | v2 | **v3** |
> |---|---|---|
> | Trades | 58 | 34 |
> | Win rate | 57% | **68%** |
> | Net at ₹25,000 per trade | +₹3,659 | **+₹4,077** |
> | Profit factor | 1.45 | **2.02** |
> | Drawdown | −₹2,632 | **−₹1,440** |
> | ₹5 lakh with risk sizing | +8.75% | **+9.18%** (max drawdown −2.8% → **−1.8%**) |
>
> **What the data doesn't support:**
> - The CRO's blanket scepticism. "Reject" verdicts also hit 12 winners, and the conviction score does not rank trades reliably.
> - Most other objections, such as "sector against", "rejection wick" or "no room". They sound right but cut as many winners as losers.
>
> **v3 is still a hypothesis.** It rests on 34 trades, v3 earned less than v2 in the first half of the period, and its shorts are weak. It needs longer data before real money.

---

## 1. Method (and why you can trust it)

- **No look-ahead.** The evidence uses only data available at the close of the signal candle:
  - **weekly and daily** values from completed days before the trade day;
  - **1-hour** candles that had completed by then;
  - **15-minute** CPR from yesterday;
  - **5-minute** values up to the signal candle;
  - **Nifty and sector peers** at the same timestamp.

  Outcome measures (MFE/MAE, after-exit move, wick vs close stop) are kept in a separate **hindsight** block, prefixed `H_`. They are never used for verdicts or rules.
- **Objections were fixed before looking at results.** The 11 objections (O1–O11) and 7 supports (S1–S7) below use thresholds from market practice and were not tuned. 18 rules plus 4 combinations were tested, and that count is reported so the result can be discounted for multiple testing.
- **Rules need evidence across sets, not one lucky set.** A rule counts only if it improves the **average ₹ per trade** in the v2, v1 and pool sets, and in both halves of the pool:
  - first 60% = 16 Jul – 1 Sep;
  - last 40% = 2 Sep – 7 Oct.

  Average-per-trade "lift" is used because the pool loses money overall, so simply skipping trades would look like a saving.

### The CRO's objections (fixed in advance)

| Code | Objection | Exact test |
|---|---|---|
| O1 | No room | Less than 1R to the nearest of: yesterday's high/low, the 20/60-day high/low, CPR R1/R2 (S1/S2), or the last 3 completed 1h swing points |
| O2 | Chasing | More than 3 ATR from VWAP, or more than 2 ATR from the 9 EMA, or 4+ candles in a row in the trade's direction |
| **O3** | **Higher timeframe against** | **Previous-day EMA score (close vs 20 EMA, 20 vs 50, 50 vs 200) net against the trade, or the last close on the wrong side of the 20-week EMA** |
| O4 | 1h against | The last completed 1h candle is on the wrong side of the 1h 20 EMA, or 1h RSI is above 75 (long) / below 25 (short) |
| O5 | Index against | Nifty on the wrong side of its 5m 21 EMA, or Nifty's day move more than 0.3% against the trade |
| O6 | Sector against | Median same-sector peer return since the open is against the trade |
| O7 | Rejection candle | Wick against the trade more than 35% of the candle's range, or the close in the weaker 40% of the range |
| O8 | Divergence | New 5m extreme with RSI more than 5 points weaker than the recent RSI extreme |
| O9 | Thin participation | Cumulative volume less than 1.2× normal for the time of day |
| O10 | Stop inside structure | The 2 × ATR stop doesn't clear the last 12-candle swing |
| O11 | Daily stretched | Daily RSI above 75 (long) / below 25 (short) |

**Supports:**
- S1: full daily trend.
- S2: weekly trend (above the 20-week EMA, and 10 EMA above 20 EMA).
- S3: 1h with the trend.
- S4: Nifty and sector with the trade.
- S5: stock leads its sector by ≥ 1%.
- S6: ≥ 2R of room.
- S7: strong candle (close in the top 25%, wick ≤ 20%).

**Verdict score:** 60 − 10 × objections + 7 × supports. 65 or more = APPROVE; 45–64 = APPROVE WITH CONDITIONS; below 45 = REJECT.

---

## 2. The CRO's scorecard on all 58 v2 trades

| Verdict | Trades | Losers | Winners | Avg net ₹ | Net ₹ |
|---|---|---|---|---|---|
| APPROVE | 10 | 4 | 6 | +4 | +44 |
| APPROVE WITH CONDITIONS | 21 | 6 | 15 | **+208** | +4,360 |
| REJECT | 27 | 15 | 12 | −28 | −745 |

- The CRO was right on **62%** of trades. Rejecting would have avoided 15 losers but also thrown away 12 winners.
- **The conviction score is not reliable.** Its rank correlation with ₹ result was 0.19 (v2), 0.23 (v1) and 0.04 (pool). "APPROVE" did *worse* than "APPROVE WITH CONDITIONS", and in the pool all three verdicts lose money.
- **Conclusion:** don't size trades by this score. A pile of reasonable-sounding objections is not an edge. Only objections proven one by one (Section 4) earn a place in the rules.

The full Defense Sheet for each trade (about 60 evidence fields, objections, supports, score, verdict and hindsight) is on the `v2 defense sheets` tab of `trade_review.xlsx`.

---

## 3. Why the 25 v2 losers lost

| Category (first matching objection) | Losers | ₹ lost | Blocked by v3? |
|---|---|---|---|
| **Higher-timeframe conflict (O3)** | **14** | **−4,127** | **Yes, all 14** |
| Exhaustion / chasing / rejection candle (O2, O7, O8) | 9 | −3,350 | No. These rules failed the cross-set test |
| Level collision, less than 1R of room (O1) | 2 | −640 | No |
| Pure variance (no objection at all) | 0 | 0 | n/a |

**The thesis that broke:**
- All 25 losers were ORB trades whose idea was "the opening-range breakout continues".
- In the 14 higher-timeframe losers, the breakout went **against the daily/weekly trend**. Examples: buying a stock in a daily downtrend (score −3/3) after a one-day bounce, or shorting a stock in a strong uptrend (STLTECH, daily RSI 81).
- Those intraday moves were counter-trend bounces that ran into higher-timeframe supply or demand. 11 of the 14 never reached +0.7R.

**Mirror test:** O3 also blocks **10 winners (+₹3,709)**. 6 of them were shorts in up-trending stocks, 4 of those between 14 and 19 August. On v2 alone that nets only +₹418. The case for O3 rests on all three sets together, not on v2.

### Every v2 losing trade

| Stock | Side | Entry | Net ₹ | Category | What was wrong at entry (no hindsight) | Avoidable by v3? | Best move reached (R) |
|---|---|---|---|---|---|---|---|
| WIPRO | LONG | 07-30 10:20 | -258 | HTF conflict | daily trend score -1/3; Nifty against; 1h trend/RSI against; RSI divergence | YES (O3) | 0.79 |
| MANAPPURAM | SHORT | 08-04 09:55 | -17 | HTF conflict | daily trend score -3/3; only 0.0R room to next level; extended: 2.1 ATR from 9 EMA, 6 candles in a row; sector peers -0.19% against; Nifty against | YES (O3) | 1.30 |
| TMPV | SHORT | 08-12 11:15 | -262 | Exhaustion | extended: 2.3 ATR from 9 EMA; rejection candle (wick 6%, close at 22% of range) | NO | 1.19 |
| ADANIENSOL | SHORT | 08-13 10:15 | -290 | HTF conflict | daily trend score -1/3; only 0.1R room to next level; extended: 3.5 ATR from VWAP; Nifty against | YES (O3) | 0.23 |
| SAMMAANCAP | SHORT | 08-14 09:50 | -368 | HTF conflict | daily trend score +1/3; extended: 2.2 ATR from 9 EMA, 4 candles in a row; rejection candle (wick 54%, close at 46% of range); 1h trend/RSI against | YES (O3) | 0.12 |
| AEQUS | LONG | 08-20 09:45 | -304 | Exhaustion | extended: 2.3 ATR from 9 EMA; rejection candle (wick 36%, close at 64% of range) | NO | 0.22 |
| PINELABS | LONG | 08-27 09:55 | -330 | Exhaustion | extended: 2.3 ATR from 9 EMA; Nifty against | NO | 0.02 |
| KPITTECH | LONG | 08-28 09:40 | -285 | HTF conflict | daily trend score -3/3; extended: 3.0 ATR from 9 EMA; rejection candle (wick 8%, close at 36% of range); 1h trend/RSI against; RSI divergence | YES (O3) | 0.66 |
| REDINGTON | LONG | 08-28 10:05 | -450 | Exhaustion | rejection candle (wick 23%, close at 58% of range); 1h trend/RSI against | NO | 0.26 |
| MRPL | LONG | 09-01 10:30 | -312 | Level collision | only 0.1R room to next level; extended: 2.1 ATR from 9 EMA, 7 candles in a row | NO | 0.74 |
| TATAPOWER | LONG | 09-02 10:25 | -236 | HTF conflict | daily trend score -3/3; Nifty against; RSI divergence | YES (O3) | 0.64 |
| KARURVYSYA | LONG | 09-03 09:50 | -262 | Exhaustion | rejection candle (wick 57%, close at 29% of range); 1h trend/RSI against | NO | 1.05 |
| HBLENGINE | LONG | 09-04 10:20 | -399 | HTF conflict | daily trend score -3/3; rejection candle (wick 12%, close at 41% of range); sector peers -0.06% against; 1h trend/RSI against | YES (O3) | 0.08 |
| SUNTV | LONG | 09-11 10:20 | -23 | HTF conflict | daily trend score -3/3; extended: 2.5 ATR from 9 EMA; rejection candle (wick 54%, close at 46% of range); Nifty against; 1h trend/RSI against | YES (O3) | 1.24 |
| STLTECH | SHORT | 09-15 09:55 | -442 | HTF conflict | daily trend score -3/3; only 0.2R room to next level; extended: 2.3 ATR from 9 EMA; 1h trend/RSI against | YES (O3) | 0.33 |
| KPITTECH | LONG | 09-15 10:30 | -317 | HTF conflict | daily trend score -3/3; extended: 5 candles in a row; rejection candle (wick 53%, close at 47% of range); sector peers -0.04% against; Nifty against; RSI divergence | YES (O3) | 0.33 |
| TATACHEM | LONG | 09-16 11:00 | -732 | HTF conflict | daily trend score -1/3; extended: 4.1 ATR from VWAP, 3.4 ATR from 9 EMA, 5 candles in a row | YES (O3) | 0.19 |
| HBLENGINE | LONG | 09-17 09:50 | -352 | HTF conflict | daily trend score -1/3; rejection candle (wick 51%, close at 0% of range); 1h trend/RSI against; RSI divergence | YES (O3) | 0.04 |
| PINELABS | LONG | 09-22 09:50 | -426 | Exhaustion | extended: 2.3 ATR from 9 EMA; rejection candle (wick 19%, close at 25% of range); sector peers -0.46% against | NO | 0.02 |
| AEQUS | LONG | 09-22 11:15 | -321 | Exhaustion | rejection candle (wick 84%, close at 2% of range); sector peers -0.46% against; Nifty against; 1h trend/RSI against | NO | 0.00 |
| SBILIFE | LONG | 09-24 09:40 | -303 | HTF conflict | daily trend score -1/3; only 0.2R room to next level; extended: 2.1 ATR from 9 EMA, 5 candles in a row; rejection candle (wick 50%, close at 50% of range); sector peers -0.01% against; Nifty against | YES (O3) | 0.59 |
| SHADOWFAX | LONG | 09-24 10:45 | -328 | Level collision | only 0.1R room to next level; sector peers -0.06% against; Nifty against; 1h trend/RSI against | NO | 0.22 |
| ADANIPOWER | LONG | 09-30 10:15 | -105 | HTF conflict | daily trend score -1/3; only 0.0R room to next level; extended: 6 candles in a row | YES (O3) | 0.36 |
| TDPOWERSYS | LONG | 10-05 10:05 | -645 | Exhaustion | rejection candle (wick 55%, close at 45% of range) | NO | 0.38 |
| EMMVEE | SHORT | 10-05 10:45 | -351 | Exhaustion | extended: 2.1 ATR from 9 EMA; 1h trend/RSI against | NO | 0.05 |


*Best move reached is hindsight, shown only to judge the trade, not used in any rule. All 25 losers are opening-range-breakout trades: the VWAP-pullback setup had no losers in v2.*

---

## 4. Evidence statistics: which objections actually predict losses?

Lift = average ₹ net per trade of the trades kept minus the trades vetoed (₹25,000 sizing). The 90% bootstrap confidence interval is in brackets; n = trades flagged.

| Rule | v2 (58) | v1 (46) | Pool (468) | Pool first 60% / last 40% | Sets improved |
|---|---|---|---|---|---|
| O1 no room | -66 [-222..90] n=19 | +98 [35..155] n=8 | +17 [-23..58] n=231 | +66 / -48 | 2/3 |
| O2 extended | +175 [12..329] n=29 | +49 [7..92] n=15 | +14 [-27..53] n=188 | +41 / -22 | 3/3 |
| O3 HTF against | +137 [-33..296] n=24 | +65 [11..117] n=9 | +35 [-4..75] n=216 | +36 / +33 | 3/3 |
| O4 1h against | +125 [-42..288] n=23 | -13 [-53..33] n=14 | +37 [-2..80] n=188 | +9 / +76 | 2/3 |
| O5 index against | -47 [-212..130] n=22 | n=0: too few | +5 [-34..46] n=219 | +42 / -41 | 1/3 |
| O6 sector against | -75 [-279..115] n=17 | +27 [-15..73] n=12 | -50 [-91..-8] n=181 | -44 / -61 | 1/3 |
| O7 rejection candle | +18 [-151..186] n=32 | -41 [-84..4] n=24 | +10 [-33..52] n=197 | +9 / +12 | 2/3 |
| O8 divergence | -32 [-207..142] n=13 | -6 [-47..36] n=8 | +42 [-9..91] n=112 | +13 / +80 | 1/3 |
| O9 thin participation | n=2: too few | n=4: too few | -37 [-81..8] n=56 | -56 / -9 | 0/3 |
| O10 stop inside structure | n=57 of 58: flags almost every trade | n=42 of 46: flags almost every trade | +29 [-26..84] n=412 | +33 / +23 | 1/3 |
| O11 daily stretched | n=0: too few | n=1: too few | -19 [-177..135] n=12 | -2 / -34 | 0/3 |
| S1 full daily trend | +130 [-38..299] n=39 | +57 [14..101] n=18 | +19 [-24..62] n=315 | +41 / -11 | 3/3 |
| S2 weekly trend | +166 [3..328] n=29 | +55 [10..102] n=15 | +16 [-24..57] n=234 | +30 / -2 | 3/3 |
| S3 1h with trend | +125 [-34..284] n=23 | -13 [-57..33] n=14 | +37 [-2..79] n=188 | +9 / +76 | 2/3 |
| S4 index + sector with trade | -99 [-262..61] n=28 | +29 [-14..72] n=13 | -24 [-67..18] n=294 | +8 / -68 | 1/3 |
| S5 leader in its sector | -189 [-372..15] n=7 | +12 [-30..52] n=14 | -0 [-37..38] n=146 | -1 / +3 | 1/3 |
| S6 room >= 2R | -57 [-223..120] n=30 | +69 [4..122] n=14 | -9 [-55..36] n=310 | +34 / -67 | 1/3 |
| S7 strong candle | +159 [-10..322] n=40 | -39 [-91..21] n=30 | -5 [-47..34] n=287 | +1 / -12 | 1/3 |

**Rules that passed:**

| Rule | Passes? | Evidence |
|---|---|---|
| **O3 higher timeframe against** | **Yes. The only rule positive in all 3 sets and both halves of the pool** | Lift +₹137 (v2), +₹65 (v1, confidence interval above 0), +₹35 (pool); halves +36 / +33 |
| S2 weekly trend (similar to O3) | Mostly | Positive in 3/3 sets; last-40% pool −2. Overlaps O3, so not added separately |
| O2 chasing | No | Positive in 3/3 sets but negative in the pool's last 40% (−22). Watch list |
| O4 1h against | No | v1 −13. Watch list |
| O6 sector against, S4, S5, S6, O7, O1 | **No, they hurt** | Vetoing "sector against" trades *removed winners*: lift −₹50 in the pool, interval below 0 |

**Combinations, ₹ net at ₹25,000** (the full table is in the scripts' output; the split here is the pool's 60/40 date):

| Veto set | v2 trades / net | v1 trades / net | Pool trades / avg ₹ |
|---|---|---|---|
| None (v2) | 58 / +3,659 | 46 / −2,297 | 468 / −48 |
| **O3 (v3)** | **34 / +4,077** | 37 / −1,377 | 252 / −32 |
| O3 + O4 | 22 / +3,625 | 25 / −918 | 162 / −11 |
| O3 + O2 + O4 | 10 / +2,850 (90% wins) | 13 / +163 | 100 / −13 |

The three-rule version looks spectacular on v2 (9 of 10 winners), but **10 trades prove nothing**, so it was rejected as overfitting. v3 keeps one rule.

---

## 5. The v3 rules and the pre-trade CRO checklist

**v3 = v2 + one veto.** `python research/scripts/intraday_backtest.py <data> <universe> <out> --v3`

> **Veto O3 (mandatory):** skip the trade if either is true:
> 1. **Daily trend against:** using **yesterday's** daily close and EMAs, the score sign(close − EMA20) + sign(EMA20 − EMA50) + sign(EMA50 − EMA200) is ≤ −1 for a long or ≥ +1 for a short;
> 2. **Weekly trend against:** yesterday's close is below its 20-week EMA (long) or above it (short).
>
> *Market logic:* intraday breakouts that fight the daily and weekly trend are usually counter-trend bounces into higher-timeframe supply or demand. Institutions add to positions in the direction of the higher-timeframe trend.

**30-second checklist before clicking.** Answer all 6:

| # | Question | If NO |
|---|---|---|
| 1 | Is today a narrow-CPR day (width ≤ 0.25%) and does the stock's 5-minute ATR exceed 0.4% of price? *(v2)* | No trade |
| 2 | **Do the daily EMA stack and the 20-week EMA agree with my direction?** *(O3)* | **No trade** |
| 3 | Did the signal candle *close* beyond the opening range (+0.1 ATR) on the right side of a sloping VWAP, with the 9/21 EMAs aligned, RSI 60–80 (20–40) and volume ≥ 1.5× average? *(v2)* | No trade |
| 4 | Is the stop exactly 2 × ATR(5m) away, and is the quantity from the risk formula? | Fix before entering |
| 5 | *Watch list, log only:* am I chasing (more than 3 ATR from VWAP, more than 2 ATR from the 9 EMA, or 4+ candles in a row)? | Note it in the journal |
| 6 | *Watch list, log only:* is the last completed 1h candle against me, or 1h RSI stretched? | Note it in the journal |

Questions 5 and 6 are recorded on every trade so that, after 100+ more trades, the data can show whether they deserve to become vetoes.

**Conviction sizing: not adopted.** The score doesn't rank trades (Section 2), so every trade keeps the same risk.

---

## 6. v2 vs v3 on the same data and costs (₹25,000 per trade)

| | v2 | **v3** |
|---|---|---|
| Trades | 58 | **34** |
| Win % | 56.9% | **67.6%** |
| Gross ₹ | +6,159 | +5,559 |
| Charges ₹ | 2,500 | 1,482 |
| **Net ₹** | **+3,659** | **+4,077** |
| Average win / average loss ₹ | +357 / −325 | +351 / −363 |
| Profit factor | 1.45 | **2.02** |
| Worst drawdown along the trade sequence | −2,632 | **−1,440** |
| Net 16 Jul – 1 Sep / 2 Sep – 7 Oct | +2,409 / +1,249 | +1,365 / **+2,712** |
| Best 3 trades' share of profit | 65% | **53%** |
| **₹5 lakh, risk sizing, desk limits** | +8.75% (max drawdown −2.8%) | **+9.18% (max drawdown −1.8%)**, +0.54R per trade, profit factor 2.50 |

**The 24 trades v3 blocked** (`v3_blocked_trades.csv`):

| | Trades | ₹ |
|---|---|---|
| Losers avoided | 14 | +4,127 not lost |
| Winners lost | 10 | −3,709 not made |
| **Net effect** | | **+418**, plus fewer trades and lower charges (−₹1,018) |

**Where v3 is weaker:**
- **First half:** v3 made ₹1,044 less than v2 in 16 Jul – 1 Sep. O3 blocked four big winning shorts (BELRISE, HSCL, PPLPHARMA, SAMMAANCAP) on stocks in uptrends.
- **Shorts:** v3 has only 4 opening-range shorts left, and they lost (−0.29R each). The edge is almost entirely **opening-range longs in up-trending stocks**: 29 trades, 69% winners, +0.62R each.

---

## 7. Three worked examples: the losers v3 now blocks

### TATACHEM, LONG, 16 Sep 11:00 (net −₹732, the biggest v2 loss)

| Timeframe | Evidence at entry |
|---|---|
| Weekly | Above the 20-week EMA, but the 10-week EMA is below the 20-week; 22% below the 52-week high |
| Daily | **Trend score −1/3** (20 EMA below 50), daily RSI 73.6 |
| Open | Gapped down 4.5% |
| 1h | Above the 1h 20 EMA, RSI 73 |
| 15m | CPR width 0.00%; opening range very wide (4.3 ATR) |
| 5m | **4.1 ATR above VWAP, 3.4 ATR above the 9 EMA, 5 green candles in a row**, RSI 78, volume 3× average |
| Context | Nifty and sector slightly positive; stock +11% vs sector (news-driven) |

- **CRO objections:** daily trend against (O3); a chase into a vertical move after a gap-down (O2); the stop sits inside the morning's swing structure (O10).
- **Defense:** a sector leader with Nifty, sector and 1h trend all supporting, and 10R of room.
- **Verdict:** APPROVE WITH CONDITIONS (58).
- **Hindsight:** reached +0.19R, then the stop was hit on a close.
- **Lesson:** a news spike against a falling daily trend usually fades. **Blocked by O3.**

### STLTECH, SHORT, 15 Sep 09:55 (net −₹442)

- **Weekly / daily:** a powerful uptrend. **Daily score +3 (−3 for a short)**, above the 20-week EMA, daily RSI 81.
- **1h:** the last completed 1h candle was above its 20 EMA, with 1h RSI 78. **Only 0.2R of room** to the last 1h swing low.
- **Context:** Nifty and the sector were both *up* (+0.7% and +1.3%).
- **Verdict:** REJECT (31). Objections O1, O2, O3, O4 and O10.
- **Hindsight:** reached +0.33R, then reversed −2R.
- **Lesson:** shorting a leader in a strong trend on its first red candle is fading the trend. **Blocked by O3.**

### HBLENGINE, LONG, 4 Sep 10:20 (net −₹399)

- **Weekly / daily:** **downtrend.** Score −3/3, below the 20-week EMA, 36% below the 52-week high.
- **1h:** RSI 83 (stretched).
- **Signal candle:** closed at only 41% of its range.
- **Context:** sector peers slightly negative, even though the stock was +6.4% vs its sector.
- **Verdict:** REJECT (24).
- **Hindsight:** best point +0.08R, stopped on a wick.
- **Lesson:** a one-day relief rally in a stock in a long downtrend. **Blocked by O3.** It took a second loss on 17 Sep (−₹352), also blocked.

---

## 8. Plain-language summary for the trader

1. **Most v2 losses weren't bad luck.** 14 of 25 were breakouts *against* the daily/weekly trend. From now on, **only trade in the direction of the daily EMA stack and the 20-week EMA.** That one rule cut losers from 25 to 11, lifted the win rate from 57% to 68% and nearly halved the drawdown.
2. **The other 11 losses** were mostly chasing extended moves or a rejection candle. The data doesn't yet prove that avoiding them helps (it also cuts winners), so **log them, don't ban them yet**.
3. **Being sceptical of everything isn't a strategy.** The CRO's general verdicts were right only 62% of the time and the score didn't rank trades. Only rules proven one at a time go into the system.
4. **What would prove v3 wrong:**
   - on 1–3 years of new 5-minute data, trades blocked by O3 do **as well as or better than** trades kept; or
   - v3's profit factor drops below 1.2.
5. **Next steps:**
   - run `--v3` unchanged on Dhan/Kite 5-minute history;
   - paper-trade 4 weeks with the 6-question checklist;
   - review the watch-list rules (chasing, 1h against) after 100 more logged trades;
   - consider dropping shorts if they stay negative.
