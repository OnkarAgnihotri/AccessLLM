# Strategy Research Report: NSE momentum and pullback trading

*Research desk report, prepared 4 Oct 2026. Data runs to the close of 1 Oct 2026. This is research, not investment advice.*

---

## 0. The short answer

| Question | Answer from the data |
|---|---|
| Can a strategy win 75–85% of trades? | **Yes, on the BUY side, as a 2–10 day swing.** The rule is to book half the position at +1% and move the stop to cost. That gave **82–86% winning trades**, both on the data it was designed on and on newer data it had never seen. |
| Does that make good money? | **Only modestly.** Wins are small (about +1%) and the occasional loss is big (about −4%). One loss wipes out 3–4 wins. The net result was **about +0.2% to +0.4% per trade after costs**. That is a real edge, but a thin one. |
| Pure intraday momentum (first-hour breakout, ORB)? | **No proven edge on these stocks.** On 3 years of 1-hour data the first-hour breakout **lost 0.03–0.07R per trade after costs**, including with trend, Nifty and volume filters. On 48 days of 15-minute data the US-style ORB was roughly break-even. |
| SELL side (shorting)? | **Not proven.** Mirror-image short setups also won 77–86% of the time, but **lost money** in the older test period. Short trades held overnight also need F&O. |
| Trade from tomorrow with real money? | **Not recommended.** Do the formal backtest (your step 2), then **paper-trade for 4–6 weeks** (forward test). The market is also in a downtrend right now (Nifty below its 200-day average), which is the weaker regime for this setup. |

The rest of this report explains why, in simple words.

---

## 1. What the outside research says

### 1.1 Most intraday traders lose money, so the edge has to be real

- **SEBI study (July 2024):** 7 out of 10 individual intraday traders in the equity cash segment lost money in FY23. The share rises to **80% for very frequent traders** (more than 500 trades a year). [Business Standard](https://www.business-standard.com/amp/markets/news/7-in-10-intraday-traders-in-equity-cash-suffered-losses-in-fy23-sebi-study-124072400975_1.html), [Moneylife](https://moneylife.in/article/7-out-of-10-individual-intraday-traders-in-equity-cash-segment-make-losses-sebi-study/74733.html)
- **Barber, Lee, Liu & Odean, "The Cross-Section of Speculator Skill" (Journal of Financial Markets, 2014)** studied 15 years of Taiwan day traders. **Less than 1%** could predictably earn positive returns after fees. [eScholarship](https://www.escholarship.org/uc/item/7k75v0qx)
- Lesson: anyone selling an "85% accurate intraday system" should be asked for the **average win, the average loss, and costs**, not just the win rate.

### 1.2 Momentum is real, but mostly over weeks and months, and mostly in sectors

- **Jegadeesh & Titman (1993):** stocks that went up most over the past 3–12 months tend to keep outperforming for the next few months. This is the foundation of momentum investing.
- **Moskowitz & Grinblatt, "Do Industries Explain Momentum?" (Journal of Finance, 1999):** much of stock momentum is really **sector momentum**. Buying stocks from the strongest sectors works better than picking individual winners blindly. [IDEAS/RePEc](https://ideas.repec.org/a/bla/jfinan/v54y1999i4p1249-1290.html)
- **Gao, Han, Li & Zhou, "Market Intraday Momentum" (JFE, 2018):** for the S&P 500 ETF, the first half-hour return predicts the last half-hour return. This works for the **index** on volatile and news days, not for every stock. [WUSTL](https://profiles.wustl.edu/en/publications/market-intraday-momentum/)
- **Zarattini & Aziz, "Can Day Trading Really Be Profitable?" (2023)** and **Zarattini, Barbon & Aziz, "A Profitable Day Trading Strategy for the U.S. Equity Market" (2024):** a 5-minute Opening Range Breakout on "stocks in play" (unusually high volume) was profitable in the US for 2016–2023. The win rate was **low**, with a few large winners carrying the result. [SSRN](https://papers.ssrn.com/abstract=4416622), [Concretum](https://concretumgroup.com/a-profitable-day-trading-strategy-for-the-u-s-equity-market/)
- **Zarattini, Barbon & Aziz, "Beat the Market" (2024):** intraday momentum on SPY using a volatility "noise band", VWAP and trailing stops. It made 19.6% a year with a Sharpe ratio of 1.33 for 2007–2024, on the **index ETF**, not single stocks. [SFI](https://www.sfi.ch/de/publications/n-24-97-beat-the-market-an-effective-intraday-momentum-strategy-for-s-p500-etf-spy)

### 1.3 High win rates come from mean reversion inside a trend, not from breakouts

- **Larry Connors & Cesar Alvarez, *Short Term Trading Strategies That Work* (2008):** buy a stock that is **above its 200-day average** when the **2-period RSI drops below 10**, and sell when it closes back above its 5-day average. This is the best-known high-win-rate stock setup. Removing the 200-day trend filter made results much worse. [Backtest Substack](https://backtest.substack.com/p/the-2-period-rsi-a-simple-system)
- **Thomas Bulkowski, *Encyclopedia of Candlestick Charts*:** he tested 103 patterns on millions of bars. The best ones reverse direction 78–86% of the time (for example the bearish three-line strike, three white soldiers and bearish engulfing), but most patterns are close to a coin flip. [ThePatternSite, top performers](https://www.thepatternsite.com/CandlePerformers.html)

### 1.4 Books worth reading, and what each one teaches

| Book | Main lesson for us |
|---|---|
| Ernest Chan, *Quantitative Trading* and *Algorithmic Trading* | How to backtest without fooling yourself (look-ahead bias, survivorship bias, costs), and when mean reversion or momentum works |
| Perry Kaufman, *Trading Systems and Methods* | An encyclopedia of indicators and systems, with tested results |
| Connors & Alvarez, *Short Term Trading Strategies That Work* | RSI(2) pullback in an uptrend, the core of our recommended setup |
| Van K. Tharp, *Trade Your Way to Financial Freedom* | **Expectancy**, R-multiples, position sizing. Win rate alone means nothing |
| Ralph Vince, *The Mathematics of Money Management* | Kelly criterion and optimal f: how much to risk per trade |
| Mark Minervini, *Trade Like a Stock Market Wizard* | Trade **leaders** (top relative strength), tight risk, market-regime awareness |
| William O'Neil, *How to Make Money in Stocks* (CAN SLIM) | Relative strength, sector leadership, institutional buying |
| Andrew Aziz, *How to Day Trade for a Living* | Stocks in play, ORB, VWAP: the intraday toolkit |
| Linda Raschke & Larry Connors, *Street Smarts* | Short-term price-action setups and pullback entries |
| Thomas Bulkowski, *Encyclopedia of Candlestick Charts* | Which candle patterns actually have statistics behind them |
| Marcos López de Prado, *Advances in Financial Machine Learning* | Backtest overfitting, walk-forward testing, why most backtests lie |

### 1.5 The maths every trader must know

1. **Expectancy per trade** = (Win% × Average win) − (Loss% × Average loss) − Costs.
   *Example:* an 85% win rate with an average win of 1% and an average loss of 6% gives 0.85×1 − 0.15×6 = **−0.05%**. That **loses** money despite the 85% win rate.
2. **Break-even win rate** = Average loss ÷ (Average win + Average loss). With a 1% win and a 4% loss you must win **more than 80%** just to break even. **High win rate and good strategy are not the same thing.**
3. **Position size** (the 1% rule): Quantity = (Capital × 1%) ÷ (Entry − Stop). You never lose more than 1% of capital on one trade when the stop works.
4. **Kelly fraction** = W − (1 − W) ÷ (Average win ÷ Average loss). This is the theoretical maximum to risk. Professionals use **¼ Kelly or less**. When the edge is thin, as ours is, Kelly says to keep the size small.
5. **Costs in India**, round trip, approximate:
   - Intraday: brokerage + STT 0.025% (sell side) + exchange charges + GST + stamp duty + slippage ≈ **0.10–0.15%**.
   - Delivery: STT 0.1% on each side ≈ **0.25%** including slippage.

   These are the figures used in every test below. On intraday trades costs eat most of the small edges.

---

## 2. How professional research firms find stocks

A research house with about 20 people usually splits the work like this. Every part except the analyst meetings can be automated in our scanner.

| Desk (people) | What they do | How we automate it |
|---|---|---|
| **Macro and strategy (2)** | Market regime: is Nifty in an up or down trend? What are VIX, FII/DII flows and interest rates doing? | Nifty vs its 50/200-day averages, India VIX, breadth (% of stocks above their 50-day average) |
| **Sector analysts (8: banks, NBFC, IT, pharma, auto, capital goods, metals, FMCG/consumer)** | Find which sectors are getting stronger (sector rotation), plus earnings trends and order books | Sector relative-strength ranking over 1, 3 and 6 months, and % of the sector's stocks above their 50-day average |
| **Quant screening (3)** | Factor screens: momentum, relative strength, quality, earnings-estimate revisions, 52-week-high proximity | 6-month RS percentile, distance from 52-week high, trend filters |
| **Technical and flow desk (3)** | Volume shockers, delivery %, bulk and block deals, F&O open-interest build-up (long or short build-up), breakouts | Relative volume, 20-day breakouts, RSI(2) pullbacks *(OI and delivery data need an NSE data feed, a future add-on)* |
| **Event desk (2)** | Results calendar, order wins, corporate actions, news | *Not automated yet*: check the results date before every trade |
| **Risk desk (2)** | Position sizing, sector exposure limits, stop discipline, drawdown control | 1% risk rule, max 5 positions, max 2 per sector, hard stops |

The typical funnel is **market regime → strongest sectors → strongest stocks in those sectors (leaders) → a low-risk entry point (pullback) → strict exit and size rules**. This is what Minervini and O'Neil describe, and what Moskowitz–Grinblatt and Jegadeesh–Titman measured.

---

## 3. What OUR data showed

**Data used:** the 597 stocks in `all_profile_metadata.json`, from Yahoo Finance:

- **1d** bars: 6 years (Oct 2020 – Oct 2026), 558 stocks with enough history
- **1h** bars: about 3 years (Oct 2023 – Oct 2026), about 569 stocks
- **15m** bars: 48 trading days

Only liquid stocks (median daily turnover above ₹20 crore) are used in the tests. Every test is split into an **in-sample** period, where ideas were formed, and an **out-of-sample** period, used as a check. For the daily tests the split is before and after Jul 2024. For the hourly tests it is before and after Apr 2025.

### 3.1 Universe profile

- Typical stock: ATR about **3.0%** of price, average daily range about **2.75%**, median turnover about **₹45 crore/day**.
- **Market right now is weak.** Nifty is at 22,422, below its 50-day average (23,870) and its 200-day average (24,356). It is −6.8% over 1 month, −7.6% over 3 months and −10.9% over 1 year. Only about 19% of stocks are above their 50-day average and 42% above their 200-day average.

### 3.2 Intraday tests on 1h data, about 300,000 stock-days

**Does the first hour's direction continue for the rest of the day?**

| Condition | % of days the rest of the day went the same way |
|---|---|
| All stock-days | **50.0%** (a coin flip) |
| First-hour volume 2.5× normal | 47.9% (slightly *reverses*) |
| Stock moves with Nifty in the first hour | 50.8% |
| First hour in the daily-trend direction | 48.3% |

**First-hour breakout:** entry on the first hourly close above or below the 9:15 candle's range, stop at the other side of that range, and exit at the target or at 3:30.

| Filter | Side | Trades | Win% (0.5R target) | Win% (1R target) | Net R per trade |
|---|---|---|---|---|---|
| None | Long | 79,702 | 52.3 | 48.2 | **−0.05** |
| None | Short | 107,564 | 57.0 | 53.4 | **−0.03** |
| Daily trend + Nifty agree | Long | 15,601 | 51.5 | 47.5 | **−0.06** |
| Daily trend + Nifty agree | Short | 19,759 | 57.7 | 54.3 | **−0.03** |
| + volume 1.5× (stocks in play) | Long | 2,444 | 51.4 | 47.7 | **−0.05** |
| + volume 1.5× (stocks in play) | Short | 1,825 | 53.4 | 50.5 | **−0.07** |

**15-minute ORB, Zarattini style** (top 20 stocks by first-15-minute volume each day, trade in the direction of the first candle, hold to the close, 48 days):

- With a tight 10%-of-ATR stop: win rate 11.5%, **−0.45R per trade**.
- With the stop at the other side of the opening range: win rate 38.9%, **−0.02R per trade** (break-even).

> **Conclusion:** the textbook intraday momentum setups had **no edge after costs** on these stocks with hourly data. Intraday edges are smaller than the ~0.12% round-trip cost. This matches the SEBI finding. Intraday should be used **only for timing entries**, until a proper tick-level or 5-minute study proves otherwise.

### 3.3 Swing tests on daily data, 2–10 day holds

| Setup | Trades | Win% | Average per trade (net) | Profit factor |
|---|---|---|---|---|
| 20-day breakout + volume 1.5× (long) | 14,028 | 43.2 | +0.11% | 1.04 |
| 20-day breakdown + volume (short) | 3,892 | 38.8 | −1.39% | 0.60 |
| RSI(2) < 10 pullback above 200-day average (long) | 37,807 | 60.9 | +0.02% | 1.02 |
| RSI(2) > 90 bounce below 200-day average (short) | 22,019 | 60.4 | −0.33% | 0.80 |

Plain breakouts and plain RSI(2) are roughly break-even after costs. **Two filters made the long pullback clearly better.**

**Filter A, only trade leaders:** the stock's 6-month return must be in the top 30% of all 597 stocks (relative strength), it must be above its 50-day and 200-day averages, and the dip must be sharp (RSI(2) < 5).

| Version | In-sample win% | Out-of-sample win% | In-sample average | Out-of-sample average | Out-of-sample profit factor |
|---|---|---|---|---|---|
| RSI(2)<5 in leaders, exit close > 5-day average | 66.3 | 63.9 | +0.90% | +0.34% | 1.27 |

**Filter B, scale out:** book **half at +1%**, move the stop to the entry price, and exit the rest when the price closes above its 5-day average. The hard stop is 3×ATR.

| Version | Period | Trades | Hit +1% first target | **Trades that ended in profit** | Average per trade (net) | Profit factor | Average losing trade |
|---|---|---|---|---|---|---|---|
| Leaders pullback + scale-out | In-sample (2021–Jun 2024) | 1,251 | 86.3% | **86.2%** | +0.38% | 1.53 | −5.2% |
| Leaders pullback + scale-out | **Out-of-sample (Jul 2024–Oct 2026)** | 1,288 | 83.2% | **83.9%** | **+0.19%** | 1.31 | −3.8% |
| Same, first target +1.5% | Out-of-sample | 1,288 | 73.4% | 78.1% | +0.20% | 1.24 | −3.8% |

Other checks:

- **Probability of touching +1% within 5 days before the stop:** 85–87%. For +1.5% it is 77–82%, and for +2% it is 70–76%.
- **Candlestick confirmation on the signal day** (hammer, bullish engulfing): it **added nothing**. Hammers were too rare, and an engulfing candle almost never happens on a deep-dip day.
- **Gap-down open the next day:** win rate improved to **68–71%** (base 64–66%). Buying weakness in leaders works better than chasing.
- **Short-side mirror** (RSI(2) > 95 in laggards below their averages, half at −1%, futures costs): it won 77–86% of trades but had a **negative average in-sample (−0.25%)** and a small positive one out of sample (+0.16%). **That is not reliable**, so it is not recommended.

---

## 4. The proposed strategy, in simple words

### "Leaders' Pullback" (LP): buy-side swing, 2–10 days

**The idea in one line:** find the strongest stocks in the market and buy them **only on the days they have a sharp, short fall**. Take a quick small profit on half the position and let the other half bounce back to normal.

**Why it should work:** big funds keep buying leaders (momentum, sector rotation), so a sharp 2–3 day dip in a leader is usually short-term panic or profit-booking, not a change in trend. Prices "snap back" toward their short-term average (mean reversion). The data above shows this in both test periods.

#### Every evening after 3:30 pm (scanner)

1. **Check the market light.**
   - Nifty above its 200-day average → **green**, normal size.
   - Nifty below its 200-day average → **amber**, **half size**. This is today's condition.
2. **Make the Leaders List.** Keep stocks that:
   - trade at least ₹20 crore per day (median of 20 days),
   - close above their 50-day **and** 200-day averages, and
   - have a 6-month return in the **top 30%** of all 597 stocks.
   - Prefer the top-ranked sectors (Section 5).
3. **Find the setup.** Within that list, flag stocks where:
   - **RSI(2) < 5**: two or three red days in a row, a sharp short dip, and
   - the close is **below the 5-day average**.
   - Skip the stock if quarterly results are due within the next 5 days.

#### Next morning (entry)

4. **Buy at the open** (9:15–9:20). If it **opens lower** (a gap down), still buy. Historically those did *better*.
   - *Intraday timing option:* instead of buying at the open, wait for the first 15-minute candle to close **above VWAP**. This is a timing refinement that has **not been tested yet**, and it is part of the backtest phase.

#### Exits (set as orders immediately)

5. **Target 1:** sell **half** at **+1%** above entry, using a limit order.
6. **After Target 1 fills:** move the stop on the other half to the **entry price** (a free trade).
7. **Target 2:** sell the rest at the close of the first day the price **closes above its 5-day average**.
8. **Hard stop:** **3 × ATR(14)** below entry, roughly 9% for a typical stock. It is wide on purpose, because pullbacks need room.
9. **Time stop:** exit whatever is left after **10 trading days**.

#### Position size and risk rules

- **Risk per trade = 1% of capital.** Quantity = (Capital × 1%) ÷ (3 × ATR in ₹). Halve it on amber days.
  *Example:* ₹5,00,000 capital, a stock at ₹1,000 with an ATR of ₹30. The stop distance is ₹90, so the quantity is 5,000 ÷ 90 = **55 shares** (about ₹55,000).
- **Max 5 open positions**, **max 2 from the same sector**.
- Stop trading for the month if the account falls **6%** in that month.

#### What to expect, from the out-of-sample data

| Item | Value |
|---|---|
| Trades that end in profit | **~82–86%** |
| Typical winning trade | about **+1.0% to +1.3%** of the position |
| Typical losing trade | about **−3.8% to −5%** of the position |
| Average net per trade | **about +0.2% to +0.4%** |
| Signals | anywhere from 0 to 20 a day. They cluster after market dips, and many days have none |
| Holding time | about 4 days on average |

> **Be clear on this:** the high win rate comes from taking a small, quick profit. **One bad trade can erase 3–4 good ones**, so the hard stop and the 1% risk rule are not optional.

### Intraday momentum: research only, not yet for real money

You asked for an intraday momentum strategy. The honest result is that **none of the standard intraday momentum setups showed an edge** on this data (Section 3.2). What to do instead:

- **Use intraday charts only to time** the Leaders' Pullback entries (15-minute VWAP reclaim, first-hour low hold).
- If you still want a pure intraday system, the best candidate from the research is the **"Stocks in Play" 5-minute ORB**:
  - trade only the 10–20 stocks with the highest opening relative volume,
  - stay with the daily trend,
  - stop on the other side of the opening range,
  - hold to the close.

  It needs **5-minute data for 1–2 years** (Yahoo only gives 60 days) and must be **paper traded** first.

### Sell side

Shorting overbought weak stocks showed the same high win rate but **no reliable profit**. In the cash segment shorts also have to be squared off the same day, and swing shorts need F&O stocks. **Recommendation:** no short strategy until one passes the formal backtest. When Nifty is below its 200-day average (amber), **reduce size and stay selective** instead of flipping to shorts.

---

## 5. Current market snapshot (data to 1 Oct 2026)

**Regime:** Nifty is **below its 200-day average → AMBER (half size)**. India VIX is 14.5, against a 1-year median of 12.5.

**Sector strength ranking**, by median 6-month relative-strength percentile (full table in `research/data/sector_rank.csv`):

| Rank | Sector | 1-month | 3-month | 6-month | % of stocks above 50-day average | Median RS percentile |
|---|---|---|---|---|---|---|
| 1 | Auto | −4.9% | +1.9% | +28.6% | 18% | 77 |
| 2 | Pharma/Healthcare | −3.5% | −0.3% | +25.3% | 30% | 72 |
| 3 | Realty | −5.5% | −5.4% | +18.7% | 8% | 64.5 |
| 4 | Banks | −6.3% | −7.9% | +11.7% | 15% | 58 |
| 5 | Capital Goods/Industrials | −4.5% | −7.7% | +11.7% | 25% | 57 |
| … | … | | | | | |
| Bottom | IT, Power/Utilities, Oil & Gas, Cement | | | | | 8–39 |

**Leaders List:** 100 stocks pass the leader filter (full list in `research/data/leaders.csv`). The top names by 6-month RS include **HFCL, STLTECH, SKYGOLD, WELCORP, AVALON, MTARTECH, NEOGEN, WELSPUNLIV, SYRMA, REDINGTON, LAURUSLABS, QPOWER, APARINDS, FINCABLES, TDPOWERSYS, BHEL, PAYTM, SONACOMS**.

**Setup as of the 1 Oct close:** 1 stock, **AVALON** (RSI(2) 4.8, 6-month RS percentile 99, ATR 6.4%). The rules give amber/half size. *This is an example of the scanner output, not a recommendation.*

> Note: the sector labels in `all_profile_metadata.json` are broad (for example "Materials", "Industrials"), so some stocks sit in a generic group. Better sector tags (NSE industry classification) would sharpen the sector ranking.

---

## 6. Caveats

1. **Survivorship bias.** The tests use *today's* 597 stocks. Stocks that crashed or were delisted in the past are missing, which makes long results look better than reality. The formal backtest should use point-in-time index membership if possible.
2. **Results got weaker over time.** The in-sample average was +0.38% and the out-of-sample average was +0.19% per trade. The edge is real but thin, and costs and slippage matter a lot.
3. **Data quality.** Yahoo Finance data has gaps and occasional bad ticks. The 15-minute data covers only 48 days.
4. **Daily-bar simplifications.** When the stop and the target are both touched on the same day, the test assumed the **stop came first**, which is conservative.
5. **No strategy works in every market.** Expect losing months, especially in falling markets.

---

## 7. Next steps (your plan)

1. **You review this strategy.** Tell me what to change: the first target (+1% or +1.5%), the stop (2 or 3 ATR), whether to use the regime filter, and which sectors to focus on.
2. **Formal backtest:**
   - a portfolio-level simulation with max 5 positions and the 1% risk rule,
   - an equity curve, max drawdown, monthly returns,
   - walk-forward testing and exact Indian cost modelling,
   - and a test of the 15-minute VWAP entry timing.
3. **Live scanner.** An end-of-day script that:
   - prints the market light, sector ranks and Leaders List,
   - lists the next day's buy candidates with entry, Target 1, stop and quantity for your capital,
   - and can optionally run intraday to watch the VWAP entry trigger.
4. **Paper trade for 4–6 weeks** before using real money, and compare live fills with the backtest.

---

### Files

- `research/data/sector_rank.csv`: sector strength table
- `research/data/leaders.csv`: current Leaders List with RS, ATR, returns and RSI(2)
- `research/data/candidates.csv`: setups as of the latest close
- `research/scripts/`: research scripts used for every number in this report (data fetch, intraday studies, swing studies, snapshot)
