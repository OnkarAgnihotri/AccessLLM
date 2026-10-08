# NSE Intraday Playbook: VWAP-Anchored ORB and Pullback (cash and F&O stocks)

*Desk playbook v1, 8 Oct 2026. These are rule-based, testable specifications. Nothing here is proven yet; see Section 0.*

---

> **⚠️ BACKTEST RESULT (8 Oct 2026): not profitable.**
> These rules were ported to Python (`research/scripts/intraday_backtest.py`) and run on 5-minute data:
> 158 liquid stocks, 16 Jul – 7 Oct 2026 (58 days, of which about 48 had enough history for RVol), ₹5 lakh, 0.5% risk, full MIS costs plus 0.03% slippage per side.
>
> | Variant | Trades | Win % | Gross R/trade | Net R/trade | Result |
> |---|---|---|---|---|---|
> | Playbook as written | 46 | 37% | −0.01 | −0.52 | **−11.9%** |
> | + minimum stop (1 × ATR5m and 0.4%) | 27 | 48% | +0.09 | −0.12 | −1.6% |
> | + minimum stop, ₹0 brokerage, 0.02% slippage | 27 | 48% | +0.09 | −0.06 | −0.7% |
> | ORB stop at the far side of the opening range | 11 | 36% | −0.07 | −0.27 | −1.5% |
> | Minimum stop, no RS/index filters | 52 | 40% | −0.11 | −0.32 | −8.2% |
> | Minimum stop, no RVol filter | 135 | 36% | −0.09 | −0.32 | −21.9% |
> | Minimum stop, no filters at all | 233 | 36% | −0.06 | −0.29 | −33.5% |
>
> Three findings:
> 1. **The playbook stop rule is too tight.** The median stop was 0.25% of price, which forces positions of ₹10–15 lakh and costs of about 0.4R per trade. A minimum stop distance is required.
> 2. **The filters help but are not enough.** Every filter removed made results worse. With all filters the gross edge is only about +0.09R, against 0.14–0.20R of costs.
> 3. **Even the best variant lost money.** It also had only 27 trades, too few to trust either way.
>
> **Do not trade this live.** A real verdict needs years of 5-minute data (Dhan/Kite export).

## 0. Read this first: what our own data already says

Before any capital goes on this, three facts from earlier tests on this repo's 597-stock universe have to shape the rules:

| Test | Result | Implication |
|---|---|---|
| 1h first-hour breakout, 3 years, about 187,000 trades (`research/STRATEGY_REPORT.md` §3.2) | **−0.03 to −0.07R per trade after costs**, with trend, Nifty and RVol filters | A plain breakout is not an edge on NSE. It needs VWAP, RVol, RS and time filters, and a selective trigger |
| 15m "stocks in play" ORB, top-20 RVol per day, 48 days | **−0.02R** (break-even) with the stop at the far side of the opening range | The 15m ORB is close to fair. The edge has to come from **selection and management**, not from the breakout itself |
| Did the first-hour direction persist into the rest of the day? | 50.0% (a coin flip) | Never assume the morning trend holds. Use VWAP to tell you whether it still does |

**The friction is not 0.05%.**

For a ₹1,00,000 MIS position at ₹20 per order:

| Charge | Amount |
|---|---|
| Brokerage, 2 × ₹20 | ₹40 |
| STT, 0.025% on the sell side | ₹25 |
| NSE transaction charge, 0.00297% × 2 | ₹6 |
| Stamp duty, 0.003% on the buy side | ₹3 |
| GST, 18% on brokerage + exchange | ₹8 |
| **Statutory and brokerage total** | **≈ ₹82, or 0.08%** |

Add **0.02–0.05% slippage per side** and a realistic round trip is **0.12–0.18%**.

With a typical intraday stop of 0.6–0.9% of price, that is **0.15–0.25R per trade**. The system therefore needs a **gross expectancy above +0.25R** just to break even. That single number decides which setups survive.

**Deployment gate.** No real money until:
1. a 5-minute backtest of at least 300 trades (Section 8) shows net expectancy ≥ +0.15R and a profit factor ≥ 1.3; **and**
2. 4 weeks of paper or minimum-size trading confirms live fills within 0.05% of the backtest.

---

## 1. Session map and what we do in each window (IST)

| Time | Phase | Allowed actions |
|---|---|---|
| 08:45–09:08 | Global cues | GIFT Nifty vs Nifty close, US close (S&P/Nasdaq), Brent, DXY/USDINR, India VIX. Classify the day bias: **Risk-on / Risk-off / Neutral** |
| 09:00–09:08 | Pre-open (equilibrium price) | Build the **gap list**: \|gap\| > 0.7% vs PDC. Mark news-driven names (results, block deals, orders) |
| 09:15–09:30 | Opening drive | **No entries.** Record the 15-minute opening range (ORH/ORL), first-15m RVol, Open=High / Open=Low flags, and stock vs sector vs Nifty performance |
| 09:30–11:30 | **Primary window** | ORB and VWAP-pullback entries. Max 3 new trades |
| 11:30–13:30 | Midday | **No new entries.** Manage open trades and move stops to the 9 EMA or VWAP |
| 13:30–14:45 | Secondary window | **VWAP pullback only**, continuation in the established direction of the day. Max 2 new trades. No ORB |
| 14:45–15:10 | Wind-down | No new entries. Trail tightly |
| **15:10** | Hard flat | Square off everything (broker MIS auto-square-off is about 15:20; never let it fire) |

---

## 2. Universe and pre-trade screener

| Filter | Rule | Why |
|---|---|---|
| Universe | Nifty 200 ∩ F&O list (about 180 names) | Liquidity, OI data, no circuit-limit traps |
| Price | ₹100 – ₹10,000 | Tick-size efficiency, no penny stocks |
| Liquidity | 20-day average volume ≥ 10 lakh shares **and** median turnover ≥ ₹50 Cr | Spread ≤ 0.03% |
| Volatility | Daily ATR(14) ≥ 1.5% of price | Room to make 2R after 0.15–0.25R of friction |
| Event filter | No results, AGM or ex-date today; no stock in the F&O ban list | Avoid gap and halt risk |
| **RVol (09:30)** | Cumulative volume 09:15–09:30 ≥ **1.5×** the 20-day average of the same slice (log 2.0× separately for the review) | The "stocks in play" filter from Zarattini & Aziz |
| **Relative strength** | Long: stock % from open > sector index % > 0 and > Nifty %. Short: the mirror | Trade the leader in a strong sector, or the laggard in a weak one |
| Day bias | Long only if Nifty > its VWAP at 09:30 or the bias is Risk-on; short only if Nifty < VWAP or Risk-off | Don't fight the index |

**Output at 09:31:** a ranked list of the top 10 longs and top 10 shorts, sorted by RVol × \|RS\|. Trade only from this list.

---

## 3. Multi-timeframe reference map (prepare before 09:15)

| Tier | Tool | Use |
|---|---|---|
| **Daily (bias)** | Close vs 20/50/200 EMA; HH/HL structure; **PDH, PDL, PDC** | Longs only if close > 20 EMA > 50 EMA, or the stock is reclaiming PDH. Shorts are the mirror |
| **15-minute (structure)** | **CPR** from yesterday: P = (H+L+C)/3, BC = (H+L)/2, TC = 2P − BC. Width = \|TC−BC\| / P | **Narrow CPR (< 0.25%) means a trending day is likely**, so favour ORB. **Wide (> 0.6%) means range**, so allow only VWAP fades or skip. Mark virgin CPRs and the last 3 days' supply/demand zones |
| **5-minute (execution)** | Session VWAP ± 1σ / 2σ, 9/21 EMA ribbon, RSI(14), ATR(14) | Triggers, stops, trailing |
| **Derivatives** (F&O names) | OI change vs price change at 09:30 and 11:00 | Long build-up (price ↑, OI ↑) or short covering confirms longs. Short build-up (price ↓, OI ↑) or long unwinding confirms shorts. **Disagreement means half size or skip.** Stock-option PCR is informational only, since single-stock option liquidity is thin |

---

## 4. Indicator stack (one job each, no redundancy)

| Job | Indicator | Rule |
|---|---|---|
| Fair value / control | Session VWAP + 1σ/2σ bands | Longs only above VWAP; shorts only below. **2σ = stretched: no fresh entries beyond it** |
| Short-term trend | 9 EMA / 21 EMA (5m) | Long: 9 > 21 and both rising. Short: the mirror |
| Momentum | RSI(14), 5m | ORB long needs **60–80**; a pullback long needs RSI to **hold 45–55 and turn up**. Shorts mirror at 20–40 and 45–55 |
| Risk unit | ATR(14), 5m | Stop buffer, maximum stop width, trail distance |

---

## 5. The two setups

### Setup A: 15-minute ORB with VWAP confirmation (09:30–11:30 only)

**Long trigger:** all must be true on a **closed** 5-minute candle.
1. The candle **closes above ORH**. The close must be more than 0.1 × ATR(5m) above ORH, so a touch doesn't count.
2. Close > VWAP, and VWAP is rising (VWAP now > VWAP 3 bars ago).
3. 9 EMA > 21 EMA.
4. RSI(14) between 60 and 80.
5. Breakout candle volume ≥ 1.5 × the 20-bar average volume.
6. Screener conditions pass: RVol ≥ 1.5, RS > 0, daily bias up, CPR not wide.
7. Price below VWAP +2σ.

**Entry:** buy at the open of the next candle, or a limit at the breakout close + 0.05%.

**Stop:**
- **Structural stop** = the higher of (signal-candle low − 0.1 ATR) and (the OR midpoint).
- If the stop distance is more than 1.2 × daily ATR / 4, the trade is too wide: **skip it**. That limit is roughly one quarter of a day's range.

**Targets:**
- Target 1 = entry + 1.5R. Sell 50% there and move the stop to entry + friction (about 0.1%).
- On the remaining 50%, exit on the **first 5-minute close below the 9 EMA**, or at 2σ VWAP-band exhaustion, or at 15:10.

**Invalidation (before entry):**
- the breakout candle closes back inside the range, or
- the next candle opens below ORH, or
- the Nifty 5-minute candle closes below Nifty VWAP.

**Short:** the exact mirror. Close below ORL, below a falling VWAP, 9 < 21, RSI 20–40.

### Setup B: VWAP pullback with a rejection candle (09:45–11:30 and 13:30–14:45)

**Long trigger:**
1. **The trend is established:** at least 70% of today's 5-minute closes are above VWAP, 9 > 21, and price has printed at least one high above VWAP +1σ today.
2. The pullback candle's **low touches VWAP (± 0.1 ATR) or the 21 EMA**, and the candle **closes above VWAP**.
3. The candle is bullish, with one of:
   - a **Hammer / pin bar**: lower wick ≥ 2 × body, close in the top third;
   - a **Bullish engulfing**: body engulfs the prior body, volume > the 20-bar average.
4. RSI held 45–55 during the pullback and is turning up (RSI > RSI[1]).
5. Pullback volume is lower than the impulse volume (a drying-up pullback).

**Entry:**
- a buy-stop at the signal-candle high + 1 tick, valid for the next 2 candles; **or**
- on the close of the next candle if it closes above the signal high.

**Stop:** the signal-candle low − 0.1 ATR. Skip the trade if the stop is more than 1.0 × ATR(5m) × 3 away.

**Targets:**
- Target 1 = 1.5R, or the day's high if that is closer and at least 1.2R away.
- Then trail the runner on a 5-minute close below the 9 EMA.

**Invalidation:** a 5-minute close below VWAP before entry triggers, or a Nifty VWAP flip against the trade.

**Short:** the mirror, with a shooting star or bearish engulfing at VWAP from below.

### Setup C (optional, log-only for the first month): liquidity sweep

Price sweeps PDH or ORH by less than 0.3 ATR, then closes back inside within 2 candles with volume above average. Fade it toward VWAP, with the stop beyond the sweep extreme.

**Track it but don't trade it** until it has 50 or more logged instances.

> **Triangles and flags** are not coded as separate setups. A flag that resolves at VWAP or the 9 EMA *is* Setup B; a flag that resolves at the opening range *is* Setup A. Keeping one rule for each avoids subjective pattern-drawing.

---

## 6. Risk engineering

| Rule | Value |
|---|---|
| Risk per trade | **0.5% of equity** for the first 100 live trades, then up to 1.0% if the live expectancy is ≥ +0.15R |
| Quantity | `qty = floor(equity × risk% / (entry − stop))`, rounded down to the lot size for futures |
| Max position value | 3 × equity (MIS leverage cap). Skip if the computed quantity needs more |
| Minimum structural RR | Target 1 at ≥ 1.5R **and** room to ≥ 2R before the next major level (PDH/PDL, CPR, 2σ). Otherwise no trade |
| **Daily circuit breaker** | Stop for the day at **−2R net**, **or after 2 consecutive full-stop losses**, whichever comes first |
| Weekly breaker | −5R for the week means half size for the next week |
| Max concurrent positions | 3, no more than 2 in the same sector, and no two longs on stocks with more than 0.8 correlation |
| Max trades per day | 5 |

**Why −2R and not −2% to −3%:** at 1% risk, a 3% daily stop allows three full losses plus friction. Two consecutive stops on a 50%-win-rate system happen on 25% of days. Measuring the breaker in R keeps it consistent when the risk % changes.

### Expectancy math the strategy must clear

Assumptions:
- Win rate W, with 50% of each position booked at 1.5R;
- the runner averages +1.0R after Target 1 (from the backtest) or 0R if stopped at cost;
- a loss is −1R − friction;
- friction f ≈ 0.2R.

Gross per winner ≈ 0.5 × 1.5 + 0.5 × 1.0 = **1.25R**, so:

> E = W × (1.25 − f) − (1 − W) × (1 + f)

| W | E (f = 0.2R) |
|---|---|
| 40% | −0.30R |
| 45% | −0.19R |
| **50%** | **−0.08R** |
| 55% | +0.04R |
| 60% | +0.15R |

**The system needs a win rate of 55% or more at Target 1, or bigger runners.** That is why the RVol, RS, CPR and VWAP filters exist: to push W from the raw ~48% (measured) to 55% or more. If the backtest cannot show that, **don't trade it**.

---

## 7. Exact step-by-step checklist

**Evening before (15 minutes)**
1. Update the daily data. Compute PDH, PDL and PDC, CPR and its width, daily EMA trend and daily ATR% for the universe.
2. Remove stocks with events tomorrow and stocks in the F&O ban list.
3. Note the macro calendar: RBI, CPI, Fed, expiry day. **On RBI policy days, no trades until 30 minutes after the announcement.**

**08:45–09:14**
4. Write down the day bias (Risk-on / off / neutral) from GIFT Nifty, US close, crude and USDINR.
5. Build the gap list (\|gap\| > 0.7%) with the news reason for each name.

**09:15–09:30 (hands off)**
6. Record ORH/ORL for each candidate, plus first-15m RVol, RS vs sector and Nifty, OI change, and Open=High / Open=Low flags.

**09:30**
7. Run the screener. Freeze the top-10 long and top-10 short lists, and mark CPR width.
8. Set alerts at ORH/ORL and VWAP for each listed stock.

**On each alert (before you click)**
9. Is the trigger **candle closed**? Yes / No.
10. Are all the setup conditions true? Read them off the chart; don't remember them.
11. Stop and Target 1 computed; RR ≥ 1.5 to Target 1 with room to 2R?
12. Quantity from the formula; breaker status OK; position and sector limits OK?
13. Place the entry **with SL-M and Target 1 orders in the same action** (a bracket or OCO if available).

**In the trade**
14. When Target 1 fills, move the stop to entry + 0.1%. Trail the runner on a 9-EMA close.
15. **Never widen a stop.** Reduce only.

**11:30 / 13:30 / 14:45 / 15:10**
16. Apply the window rules from Section 1. At **15:10**, flat.

**After the close (20 minutes)**
17. Journal every trade (Section 9). Take screenshots of the entry and exit charts.
18. Update the running expectancy and the breaker counters.

---

## 8. Two blueprints

> **Illustrative numbers.** They show the arithmetic, not real trades. Equity ₹5,00,000, risk 0.5% = **₹2,500 per trade**, friction 0.15%.

### Blueprint 1: LONG, Setup A (ORB), stock "XYZ"

| Item | Value |
|---|---|
| Context | Nifty above VWAP at 09:30; Bank Nifty +0.6%; XYZ (a private bank) +1.1% from open. RS vs sector +0.5%, vs Nifty +0.8% |
| Daily | Close 1,512 > 20 EMA 1,488 > 50 EMA 1,455. PDH 1,520. CPR width 0.18% (**narrow**, a trend day is likely) |
| RVol at 09:30 | 2.3× |
| Opening range | ORH 1,524.0, ORL 1,509.0 (OR mid 1,516.5) |
| ATR(5m) | 3.2; daily ATR 34 (2.3%) |
| Signal | The 09:40 5-minute candle closes at **1,526.4**, above ORH + 0.1 ATR (1,524.3). VWAP 1,518 and rising. 9 EMA 1,521 > 21 EMA 1,517. RSI 66. Volume 1.9× the 20-bar average. Below +2σ (1,531) |
| Entry | Buy at the 09:45 open ≈ **1,526.5** |
| Stop | max(signal low 1,519.8 − 0.3 = 1,519.5, OR mid 1,516.5) = **1,519.5**. Risk = 7.0 (0.46%). Width check: 7.0 < 1.2 × 34 / 4 = 10.2 ✓ |
| Quantity | 2,500 / 7.0 = **357 shares** (position ₹5.45 L, leverage 1.09×) |
| Target 1 | 1,526.5 + 1.5 × 7 = **1,537.0**: sell 178, then stop to **1,528.0** (cost + 0.1%) |
| Runner | 179 shares, exit on the first 5-minute close < 9 EMA, or at 15:10 |
| Room check | The next resistance (R1 pivot) is 1,541, which is ≥ 2R (1,540.5) ✓ |
| Invalidation | Before the fill: the 09:45 candle opens < 1,524, or Nifty 5m closes below Nifty VWAP. After the fill: a 5-minute **close** < 1,519.5 means out |
| Outcome math | Target 1 hit, then runner stopped at cost: 178 × 10.5 + 179 × 1.5 = ₹2,138 gross − ₹818 friction ≈ **+₹1,320 (+0.53R)**. Target 1 hit plus a runner exit at 1,544 (+2.5R): 1,869 + 3,132 − 818 ≈ **+₹4,180 (+1.7R)**. Full stop: −₹2,500 − ₹818 ≈ **−₹3,318 (−1.33R)**. That last figure is why friction must be in every calculation |

### Blueprint 2: SHORT, Setup B (VWAP rejection), stock "ABC"

| Item | Value |
|---|---|
| Context | 13:45, secondary window. Nifty below VWAP since 10:30. Nifty IT −0.9%. ABC (IT) −1.6%, RS vs sector −0.7%. OI +6% with price down (**short build-up**) |
| Daily | Close 742 < 20 EMA 755 < 50 EMA 768; trading below PDL 744 |
| Trend check | 82% of 5-minute closes below VWAP today; a low printed below VWAP −1σ; 9 EMA 735.2 < 21 EMA 736.8 |
| Pullback | Price rallies to VWAP 737.6. The 13:45 candle's **high is 737.9** (touches VWAP), it **closes at 735.1**, and its upper wick is 2.4 × the body (**shooting star**). RSI peaked at 53 and turned down to 48. Pullback volume is 0.7× the impulse volume |
| ATR(5m) | 1.6 |
| Entry | Sell-stop at the signal low − 1 tick: **734.70**, valid for 2 candles. It fills at 13:50 |
| Stop | Signal high 737.9 + 0.1 × ATR (0.16) = **738.06**. Risk = 3.36 (0.46%). Width ✓ (< 3 × 1.6) |
| Quantity | 2,500 / 3.36 = **744 shares** (₹5.47 L) |
| Target 1 | 734.70 − 1.5 × 3.36 = **729.66**: cover 372, then stop to **733.97** (cost − 0.1%) |
| Room check | Day low 728.4, −2σ band 727.9; 2R = 727.98 just fits ✓ |
| Runner | 372 shares. Cover on a 5-minute close > 9 EMA, at −2σ exhaustion, or at 15:10 |
| Invalidation | Before the fill: a 5-minute close > VWAP (737.6), or the Nifty 5m closes above its VWAP. After the fill: a stop-loss market order (SL-M) at 738.06 |

---

## 9. Journal and the optimisation loop

**Log every trade with these columns:**
- date, time, symbol, setup (A/B/C), side
- RVol at 09:30, RS vs sector and vs Nifty, CPR width, day bias, OI state
- entry, stop, Target 1, quantity
- exit time and reason, gross R, friction R, net R
- whether Target 1 was hit, MAE, MFE
- **loss tag**, plus screenshots

**Loss tags:**

| Tag | Definition | Action |
|---|---|---|
| **1. System loss** | All rules followed, the market didn't cooperate | None. This is variance |
| **2. Execution error** | Early entry on an open candle, moved stop, size error, FOMO, slippage > 0.1% | Fix the behaviour. **Three execution errors in a week means trading at half size the next week** |
| **3. Regime shift** | A news shock, RBI/policy, a Nifty VWAP flip within 15 minutes of entry, a chop day (Nifty range < 0.5 × ATR by 11:30) | Find a pre-trade filter that would have flagged it |

**Weekly review (Saturday, 1 hour):**
1. Expectancy = W × avg win − (1 − W) × avg loss, in **R after friction**: by setup, by window (AM / PM), by CPR state and by RVol bucket (1.5–2.0 vs > 2.0).
2. **Rule-change protocol.** Change a filter only if:
   - the bucket comparison has **≥ 30 trades on each side**, **and**
   - the difference holds in the backtest on out-of-sample data.

   Change one rule per fortnight, and keep a changelog.
3. If 50 trades in a row run below 0 expectancy, stop live trading and return to paper.

---

## 10. Validation plan (before live)

1. **Data.** 5-minute OHLCV for the F&O universe.
   - Yahoo provides only 60 days.
   - **Dhan / Kite historical APIs provide years**, and are needed for at least 300 trades.
   - Nifty and sector indices on the same timeframe.
2. **Backtest** with the Pine script below (TradingView "Deep Backtesting") for spot checks, and a Python port on the full universe for statistics:
   - commission 0.03% per side plus 2 ticks of slippage;
   - walk-forward: tune on 2023–2024, test on 2025–2026.
3. **Pass criteria** (net):
   - expectancy ≥ +0.15R, profit factor ≥ 1.3, win rate at Target 1 ≥ 52%;
   - max drawdown ≤ 10R;
   - positive results in at least 2 of 3 test years and in both long and short books.
4. **Paper-trade 4 weeks** with the checklist, then go live at 0.25% risk.

---

## 11. Pine Script

Full code: `pine/nse_vwap_orb_pullback.pine` (TradingView Pine v5 strategy, 5-minute chart).

What it implements:
- the 15m opening range, session VWAP ± 1σ/2σ, the 9/21 EMA, RSI 60/40 logic, ATR stops;
- 15m-slice RVol vs a 20-day average, RS vs Nifty, the daily EMA trend, CPR width, PDH/PDL;
- Setups A and B (long and short) on closed candles only;
- risk-based quantity, 50% at 1.5R then break-even, a 9-EMA trail;
- time windows, a −2R / 2-consecutive-loss daily breaker, and a 15:10 square-off.

It has **not** been compiled or tested in TradingView yet. Treat it as a strong outline and expect small syntax fixes.

What it can't do: sector RS vs a specific sector index (set the sector index symbol by hand in the inputs), OI/PCR, and the pre-market gap scan. Those stay in the manual checklist or need a Python scanner.
