# Fund-house universe outside our list, and v3 tested on it

*8 Oct 2026. Code: `research/scripts/universe_screen.py` (screen) and `research/scripts/intraday_backtest.py --v3` (backtest, unchanged rules). Data: `research/universe500/`.*

> **Bottom line**
> 1. **There aren't 500 such stocks.** Only **424** stocks outside your 597 pass every quality check and have at least ₹1 Cr of daily turnover. Your list already holds almost every large, mid-sized and liquid stock. The rest are small (423 of 424 are below ₹30,000 Cr market cap).
> 2. **BSE-only stocks can't be used.** Only 25 of 1,668 averaged ₹2 Cr or more in daily turnover over two days, several of those are ETFs or recent listings, and there is no intraday price data for any of them.
> 3. **v3 does not carry over to these stocks.** Same rules, same dates (17 Jul – 7 Oct 2026):
>
>    | Universe | Trades | Wins | Net at ₹25,000 per trade | ₹5 lakh, risk sizing |
>    |---|---|---|---|---|
>    | Your list | 34 | 68% | **+₹4,077** | +9.18% |
>    | New 424 stocks | 120 | 38% | **−₹3,637** | −2.20% |
>    | New 424, double slippage | 120 | 38% | worse | −5.25% |
>
>    The rules still make money before costs (+₹1,453), but charges (₹5,090) wipe it out. The higher-timeframe veto, the only rule added in v3, didn't help here: v2 without it lost −0.1%.
> 4. **Fundamental and policy quality do not help intraday.**
>    - The 100 *lowest*-scored stocks made +₹3,381 and the top 100 lost −₹1,883.
>    - What mattered is **liquidity**: stocks trading ≥ ₹10 Cr a day made +₹2,990, while the ₹1–5 Cr tiers lost −₹5,562.
>    - Fund-house quality picks stocks to *own*. It doesn't make a stock better to *day-trade*.

---

## 1. Data coverage (Step 0)

| Item | Result |
|---|---|
| NSE equity list (`EQUITY_L.csv`, series EQ) | 2,333 EQ stocks; 1,751 after removing your list (by ISIN) |
| BSE list | The BSE API returned **403 Access Denied**. The BSE daily bhavcopy (6–7 Oct 2026) worked and was used: 1,668 active BSE-only stocks (groups A, B, T, X, XT; SME and Z groups excluded), matched to NSE by ISIN |
| Candidates after removing your 597 | **3,419** (1,751 NSE-listed, 1,668 BSE-only) |
| Daily prices on Yahoo | 1,727 of 1,751 NSE; **0 of 1,668 BSE-only** (numeric and symbol tickers both tried) |
| Yahoo fundamentals (sample of 50, then all 780 liquid candidates) | 94% returned data; 90% have ≥ 3 years of income statement, balance sheet and cash flow |
| ROE field | Mostly missing in Yahoo's summary (6%), so **computed from the statements** (net income ÷ equity, 3-year average) |
| Debt | From the statements; Yahoo's reported debt/equity as fallback; 12 stocks unknown (never assumed zero) |
| Fields not available, so those checks were dropped | Promoter **pledge**, bank/NBFC **capital adequacy and NPA**, **auditor changes** and SEBI/ED actions, **ASM/GSM surveillance** lists, promoter-holding **trend** (only the current level). Banks and NBFCs are scored on ROA instead of balance-sheet ratios |

## 2. How stocks were scored (Steps 1–4)

- **Eligibility:**
  - NSE EQ series;
  - listed on NSE for at least 3 years;
  - at least 3 years of financials;
  - market cap ≥ ₹1,000 Cr;
  - price ₹50 – ₹15,000;
  - liquidity tier (see the funnel).
- **Quality score, 0–100.** Each metric is a percentile *within its sector*; missing values count as a neutral 50.
  - Profitability 25%: ROE, ROCE (ROA for financials), operating margin and its trend.
  - Growth 25%: revenue and profit CAGR, last year's revenue growth.
  - Balance sheet 20%: debt/equity, interest cover, current ratio.
  - Cash quality 15%: operating cash flow ÷ profit, years of positive free cash flow.
  - Valuation sanity 15%: penalised only above 3× the sector median P/E or P/B.
- **Red flags (excluded outright):**
  - negative net worth;
  - losses in 2 of the last 3 years;
  - debt/equity above 2 (non-financials);
  - negative operating cash flow in 2 of 3 years.

  **91 stocks** were removed this way.
- **Governance (−15 to +10), from the data available:**
  - promoter/insider holding of 40–75%: +4; under 20%: −5; over 85% (very low free float): −5;
  - institutional holding ≥ 15%: +4; under 3%: −3;
  - pays a dividend: +2.
- **Policy (0 to +15):**
  - **+15 only with a company-specific source** (named scheme beneficiary or disclosed order book);
  - **+5** if the stock's industry maps to a sourced theme;
  - policy risks (fertiliser price controls, sugar export curbs, windfall taxes) are flagged.
- **Final score** = quality + governance + policy.
- **Diversification:** at most 12% of names from one industry. Yahoo's 11 broad sectors are too coarse for a 12% cap plus "at least 15 sectors", so industries were used. The result has 87 industries; the largest is 8.5%.

### Screening funnel

| Step | Stocks left |
|---|---|
| candidates (597 removed) | 3419 |
| NSE with price data | 1727 |
| + listed >= 3 years | 1189 |
| + 3y fundamentals available | 577 |
| + market cap >= Rs 1,000 cr | 525 |
| + price Rs 50-15,000 | 525 |
| + no red flags | 434 |
| + liquidity >= Rs 20 cr & 200,000 shares | 62 |
| + liquidity >= Rs 10 cr & 100,000 shares | 124 |
| + liquidity >= Rs 5 cr & 50,000 shares | 217 |
| + liquidity >= Rs 3 cr & 50,000 shares | 275 |
| + liquidity >= Rs 2 cr & 25,000 shares | 350 |
| + liquidity >= Rs 1 cr & 10,000 shares | 424 |

### Policy map (sources)

| Theme | Official anchor | Source |
|---|---|---|
| Defence indigenisation | 75% of FY26 defence modernisation budget earmarked for domestic procurement; positive indigenisation lists (5th list: 346 items, Jul 2024); MoD budget FY27 Rs 7.85 lakh cr | [link](https://idsa.in/publisher/issuebrief/ministry-of-defence-2026-27-budget-estimates-an-analysis) / [link](https://www.drishtiias.com/daily-updates/daily-news-analysis/5th-positive-indigenisation-list-1) |
| Railways capex | Union Budget 2026-27: ~Rs 2.93 trillion for Indian Railways, rolling stock Rs 521 bn the largest head | [link](https://indianinfrastructure.com/2026/02/02/union-budget-2026-27-highlights-for-infrastructure-sectors/) |
| Infrastructure capex | Union Budget 2026-27 capex ~Rs 12.2 lakh cr (+11.5%), MoRTH Rs 3.10 trillion | [link](https://www.outlookbusiness.com/budget/budget-2026-fm-sitharaman-raises-capex-for-fy27-to-122-lakh-crore) / [link](https://prsindia.org/files/budget/budget_parliament/2026/Analysis_of_Expenditure_2026-27.pdf) |
| Power, T&D and RDSS | Revamped Distribution Sector Scheme smart-metering (about 15.6 cr meters tendered) and transmission capex | [link](https://www.tndindia.com/genus-power-outstanding-order-book-exceeds-rs-25000-crore/amp/) |
| Renewable energy / solar PLI | Solar PV module PLI: 39.6 GW allotted in tranche II (48.3 GW total), Rs 64,873 cr investment | [link](https://jmkresearch.com/39-6-gw-cumulative-solar-pv-module-manufacturing-capacity-allotted-under-pli-tranche-2/) / [link](https://www.businesstoday.in/amp/latest/economy/story/pli-scheme-attracts-rs-2-4-lakh-crore-in-investments-till-march-2026-536415-2026-06-11) |
| Electronics / semiconductors | Electronics Component Manufacturing Scheme (106 approvals, Rs 695 bn) and India Semiconductor Mission (10+ approved projects, Rs 1.6 lakh cr) | [link](https://indianinfrastructure.com/2026/08/18/government-approved-31-proposals-under-electronics-components-manufacturing-scheme/) / [link](https://static.pib.gov.in/WriteReadData/specificdocs/documents/2026/feb/doc202627782201.pdf) |
| Pharma / medical devices PLI | PLI for bulk drugs, pharmaceuticals and medical devices (Department of Pharmaceuticals approved lists) | [link](https://www.pharma-dept.gov.in/schemes/archive) |
| Auto & components PLI | PLI for automobiles and auto components (one of 14 PLI sectors) | [link](https://www.outlookbusiness.com/corporate/806-applications-approved-under-pli-schemes-across-14-sectors) |
| White goods / textiles / food PLI | PLI for white goods (ACs/LED), textiles and food processing (14 PLI sectors) | [link](https://www.india-briefing.com/news/indias-pli-scheme-for-white-goods-ac-and-led-status-updates-24506.html) |
| Specialty steel PLI | PLI for specialty steel (14 PLI sectors) | [link](https://www.outlookbusiness.com/corporate/806-applications-approved-under-pli-schemes-across-14-sectors) |
| Telecom PLI | PLI for telecom and networking products (14 PLI sectors) | [link](https://www.outlookbusiness.com/corporate/806-applications-approved-under-pli-schemes-across-14-sectors) |

### Company-specific policy evidence (+15)

| Stock | Theme | Evidence | In final list? |
|---|---|---|---|
| IDEAFORGE | Defence indigenisation | [Named beneficiary, PLI scheme for drones (MoCA provisional list)](https://www.tribuneindia.com/news/business/adani-joint-venture-ideaforge-among-14-firms-selected-as-beneficiaries-of-pli-scheme-for-drone-manufacturing-387998) | No: red flag (losses, cash) |
| PARAS | Defence indigenisation | [Paras Aerospace named in drone PLI beneficiary list](https://raksha-anirveda.com/?p=43364) | **Yes** |
| GENUSPOWER | Power, T&D and RDSS | [Smart-meter order book ~Rs 24,020 cr (Jun 2026), mostly RDSS AMISP projects](https://nsearchives.nseindia.com/corporate/GENUSPOWER_19052026093441_Press_Release_Signed.pdf) | No: red flag (cash) |
| HPL | Power, T&D and RDSS | [Order book > Rs 3,200 cr (Aug 2026), ~96% smart metering](https://www.tndindia.com/hpl-electric-power-ltd-order-book-surpasses-rs-3200-crore/amp/) | **Yes** |
| JUPITERWAG | Railways capex | [Order book Rs 4,675 cr (Mar 2026); Vande Bharat wheelsets and LHB axles from Ministry of Railways](https://compoundingai.in/market-news/jwl-q4-fy26-earnings-call) | No: already in your 597 list |
| ASTRAMICRO | Defence indigenisation | [Consolidated order book Rs 2,849 cr (Jun 2026) + Rs 2,205 cr HAL Uttam radar order (Jul 2026)](https://nsearchives.nseindia.com/corporate/ASTRAMICRO_10082026163251_PressRelease.pdf) | No: red flag (cash) |
| APOLLO | Defence indigenisation | [Rs 213 cr orders from DRDO and defence PSUs (Aug 2026)](https://www.angelone.in/news/stocks/apollo-micro-systems-secures-2133-91-million-orders-from-drdo-defence-psus-and-private-industries) | No: red flag (cash) |
| AVANTEL | Defence indigenisation | [Rs 117.9 cr DRDO ground-segment order (Aug 2026)](https://www.multibagg.ai/market-pulse/articles/avantel-drdo-ground-hub-order-cmtg2h74n000j2ts53akqk1kj) | No: listed on NSE < 3 years |
| AARTIPHARM | Pharma / medical devices PLI | [Approved products under pharmaceuticals PLI (DoP annexure, Oct 2024)](https://www.pharma-dept.gov.in/sites/default/files/PPO%20DOP17oct2024.pdf) | **Yes** |

### Mix of the final list

| Broad sector | Stocks |
|---|---|
| Basic Materials | 96 |
| Consumer Cyclical | 93 |
| Industrials | 90 |
| Consumer Defensive | 35 |
| Healthcare | 34 |
| Financial Services | 28 |
| Technology | 20 |
| Real Estate | 10 |
| Energy | 7 |
| Communication Services | 6 |
| Utilities | 5 |

87 industries; the largest is Specialty Chemicals with 36 stocks (8.5%).

| Market cap | Stocks |
|---|---|
| small (<30k cr) | 423 |
| mid (30k-1L cr) | 1 |

| Liquidity tier (20-day median turnover) | Stocks |
|---|---|
| T1 >=20cr | 67 |
| T2 10-20cr | 67 |
| T3 5-10cr | 101 |
| T4 2-5cr | 132 |
| T5 1-2cr | 57 |

| Policy tailwind | Stocks |
|---|---|
| none | 258 |
| White goods / textiles / food PLI | 37 |
| Infrastructure capex | 31 |
| Auto & components PLI | 29 |
| Pharma / medical devices PLI | 25 |
| Specialty steel PLI | 20 |
| Power, T&D and RDSS | 13 |
| Renewable energy / solar PLI | 3 |
| Electronics / semiconductors | 3 |
| Defence indigenisation | 2 |
| Telecom PLI | 2 |
| Railways capex | 1 |

### Top 50 by final score

| # | Stock | Industry | Score | Why selected |
|---|---|---|---|---|
| 1 | INDOTECH | Electrical Equipment & Parts | 88.0 | ROE 23%, revenue CAGR 28%, profit CAGR 53%, debt-free, OCF/profit 0.7, policy: Power, T&D and RDSS (sector) |
| 2 | KIRLPNU | Specialty Industrial Machinery | 87.4 | ROE 18%, revenue CAGR 13%, profit CAGR 33%, debt-free, OCF/profit 1.1 |
| 3 | AVANTIFEED | Packaged Foods | 87.0 | ROE 17%, revenue CAGR 6%, profit CAGR 30%, debt-free, OCF/profit 0.9, policy: White goods / textiles / food PLI (sector) |
| 4 | ARROWGREEN | Packaging & Containers | 86.8 | ROE 26%, revenue CAGR 23%, profit CAGR 57%, debt-free, OCF/profit 0.9 |
| 5 | SHARDACROP | Agricultural Inputs | 86.2 | ROE 12%, revenue CAGR 9%, profit CAGR 26%, debt-free, OCF/profit 1.6 |
| 6 | MAYURUNIQ | Textile Manufacturing | 86.0 | ROE 16%, revenue CAGR 8%, profit CAGR 23%, debt-free, OCF/profit 0.9, policy: White goods / textiles / food PLI (sector) |
| 7 | GPPL | Marine Shipping | 85.2 | ROE 18%, revenue CAGR 7%, profit CAGR 18%, debt-free, OCF/profit 1.2 |
| 8 | BANCOINDIA | Auto Parts | 84.8 | ROE 28%, revenue CAGR 19%, profit CAGR 27%, D/E 0.36, OCF/profit 0.9, policy: Auto & components PLI (sector) |
| 9 | SUPRIYA | Biotechnology | 84.5 | ROE 17%, revenue CAGR 21%, profit CAGR 33%, debt-free, OCF/profit 0.9 |
| 10 | NRBBEARING | Auto Parts | 83.8 | ROE 17%, revenue CAGR 8%, profit CAGR 15%, D/E 0.16, OCF/profit 1.0, policy: Auto & components PLI (sector) |
| 11 | SHARDAMOTR | Auto Parts | 83.7 | ROE 29%, revenue CAGR 8%, profit CAGR 18%, debt-free, OCF/profit 1.0, policy: Auto & components PLI (sector) |
| 12 | ADVENZYMES | Specialty Chemicals | 83.7 | ROE 10%, revenue CAGR 11%, profit CAGR 17%, debt-free, OCF/profit 1.0 |
| 13 | VOLTAMP | Electrical Equipment & Parts | 83.2 | ROE 20%, revenue CAGR 16%, profit CAGR 15%, debt-free, OCF/profit 0.6, policy: Power, T&D and RDSS (sector) |
| 14 | TIPSMUSIC | Entertainment | 83.1 | ROE 78%, revenue CAGR 26%, profit CAGR 41%, debt-free, OCF/profit 1.1 |
| 15 | MARKSANS | Drug Manufacturers - General | 83.0 | ROE 15%, revenue CAGR 17%, profit CAGR 16%, D/E 0.11, OCF/profit 0.8, policy: Pharma / medical devices PLI (sector) |
| 16 | ICRA | Financial Data & Stock Exchanges | 82.7 | ROE 16%, revenue CAGR 14%, profit CAGR 10%, debt-free, OCF/profit 0.8 |
| 17 | PARAS | Aerospace & Defense | 81.6 | ROE 10%, revenue CAGR 29%, profit CAGR 35%, debt-free, OCF/profit 0.1, policy: Defence indigenisation (company evidence) |
| 18 | ADFFOODS | Packaged Foods | 81.2 | ROE 16%, revenue CAGR 13%, profit CAGR 17%, debt-free, OCF/profit 0.7, policy: White goods / textiles / food PLI (sector) |
| 19 | VESUVIUS | Specialty Industrial Machinery | 80.7 | ROE 17%, revenue CAGR 16%, profit CAGR 31%, debt-free, OCF/profit 0.7 |
| 20 | INDIGOPNTS | Specialty Chemicals | 80.7 | ROE 14%, revenue CAGR 9%, profit CAGR 3%, debt-free, OCF/profit 1.3 |
| 21 | DHANUKA | Agricultural Inputs | 80.7 | ROE 19%, revenue CAGR 5%, profit CAGR 7%, debt-free, OCF/profit 0.7 |
| 22 | GOLDIAM | Luxury Goods | 80.6 | ROE 15%, revenue CAGR 22%, profit CAGR 26%, debt-free, OCF/profit 0.3 |
| 23 | INDNIPPON | Auto Parts | 80.5 | ROE 12%, revenue CAGR 18%, profit CAGR 32%, debt-free, OCF/profit 0.6, policy: Auto & components PLI (sector) |
| 24 | VIMTALABS | Diagnostics & Research | 80.5 | ROE 16%, revenue CAGR 9%, profit CAGR 17%, debt-free, OCF/profit 1.6 |
| 25 | PGHL | Drug Manufacturers - Specialty & Generic | 80.1 | ROE 43%, revenue CAGR 8%, profit CAGR 19%, debt-free, OCF/profit 1.1, policy: Pharma / medical devices PLI (sector) |
| 26 | CARERATING | Financial Data & Stock Exchanges | 80.1 | ROE 16%, revenue CAGR 19%, profit CAGR 27%, debt-free, OCF/profit 0.9 |
| 27 | ASHIANA | Real Estate - Development | 79.4 | ROE 9%, revenue CAGR 41%, profit CAGR 62%, D/E 0.38, OCF/profit 3.6 |
| 28 | SIRCA | Specialty Chemicals | 79.3 | ROE 15%, revenue CAGR 23%, profit CAGR 12%, debt-free, OCF/profit 0.8 |
| 29 | RATNAMANI | Steel | 79.3 | ROE 16%, revenue CAGR -0%, profit CAGR -2%, debt-free, OCF/profit 1.2, policy: Specialty steel PLI (sector) |
| 30 | JYOTHYLAB | Household & Personal Products | 79.2 | ROE 23%, revenue CAGR 6%, profit CAGR 12%, debt-free, OCF/profit 1.1 |
| 31 | AHLUCONT | Engineering & Construction | 79.2 | ROE 16%, revenue CAGR 17%, profit CAGR 11%, debt-free, OCF/profit 1.1, policy: Infrastructure capex (sector) |
| 32 | KPIGREEN | Utilities - Renewable | 78.9 | ROE 16%, revenue CAGR 61%, profit CAGR 63%, D/E 1.71, OCF/profit 0.7, policy: Renewable energy / solar PLI (sector) |
| 33 | ASHOKA | Engineering & Construction | 78.9 | ROE 35%, revenue CAGR -2%, profit CAGR 106%, D/E 0.28, OCF/profit 0.6, policy: Infrastructure capex (sector) |
| 34 | NIITMTS | Education & Training Services | 78.9 | ROE 19%, revenue CAGR 13%, profit CAGR 9%, D/E 0.21, OCF/profit 1.2 |
| 35 | SUNTECK | Real Estate - Development | 78.7 | ROE 4%, revenue CAGR 47%, profit CAGR 425%, D/E 0.21, OCF/profit -0.3 |
| 36 | GUJENERGY | Utilities - Regulated Gas | 78.7 | ROE 14%, revenue CAGR 12%, profit CAGR 10%, D/E 0.18, OCF/profit 1.1, policy: Power, T&D and RDSS (sector) |
| 37 | AEROENTER | Steel | 78.6 | ROE 18%, revenue CAGR 14%, profit CAGR 14%, debt-free, OCF/profit -0.5, policy: Specialty steel PLI (sector) |
| 38 | ANUP | Specialty Industrial Machinery | 78.4 | ROE 18%, revenue CAGR 27%, profit CAGR 29%, D/E 0.16, OCF/profit 0.5 |
| 39 | ANTELOPUS | Oil & Gas E&P | 78.2 | ROE 12%, revenue CAGR 33%, profit CAGR 43%, debt-free, OCF/profit 1.6 |
| 40 | VADILALIND | Packaged Foods | 78.2 | ROE 22%, revenue CAGR 12%, profit CAGR 17%, D/E 0.27, OCF/profit 1.0, policy: White goods / textiles / food PLI (sector) |
| 41 | SANDUMA | Steel | 78.2 | ROE 16%, revenue CAGR 34%, profit CAGR 34%, D/E 0.31, OCF/profit 1.6, policy: Specialty steel PLI (sector) |
| 42 | VENUSPIPES | Steel | 78.1 | ROE 18%, revenue CAGR 27%, profit CAGR 32%, D/E 0.43, OCF/profit 0.8, policy: Specialty steel PLI (sector) |
| 43 | JAMNAAUTO | Auto Parts | 77.9 | ROE 20%, revenue CAGR 4%, profit CAGR 11%, debt-free, OCF/profit 1.4, policy: Auto & components PLI (sector) |
| 44 | WEBELSOLAR | Solar | 77.8 | ROE -3%, revenue CAGR 293%, D/E 0.21, OCF/profit 1.4, policy: Renewable energy / solar PLI (sector) |
| 45 | PREMIERPOL | Specialty Chemicals | 77.8 | ROE 22%, revenue CAGR 6%, profit CAGR 40%, D/E 0.13, OCF/profit 0.8 |
| 46 | MENONBE | Auto Parts | 77.8 | ROE 18%, revenue CAGR 11%, profit CAGR 5%, D/E 0.25, OCF/profit 0.9, policy: Auto & components PLI (sector) |
| 47 | FINPIPE | Building Products & Equipment | 77.7 | ROE 10%, revenue CAGR -2%, profit CAGR 34%, debt-free, OCF/profit 0.5, policy: Infrastructure capex (sector) |
| 48 | DODLA | Food Distribution | 77.7 | ROE 16%, revenue CAGR 14%, profit CAGR 30%, debt-free, OCF/profit 1.2 |
| 49 | DYCL | Electrical Equipment & Parts | 77.4 | ROE 18%, revenue CAGR 21%, profit CAGR 40%, debt-free, OCF/profit 0.6, policy: Power, T&D and RDSS (sector) |
| 50 | KSCL | Agricultural Inputs | 77.2 | ROE 20%, revenue CAGR 9%, profit CAGR 3%, debt-free, OCF/profit 0.7 |


### What was relaxed, and why

- **Liquidity was relaxed step by step, never the red flags.** At the intraday standard of ₹20 Cr a day, only **62** stocks qualify. Even at ₹1 Cr (a practical floor, since below it a ₹25,000 order is a real share of 5-minute volume) the total is **424**.
- **A ₹0.5–1 Cr band would add about 40 more**, but those can't be traded intraday sensibly, so they were not included.
- **The 500 target was not met on purpose** rather than lowering quality.
- **The planned market-cap mix (15–25% large, 30–40% mid) was impossible:** your list already contains the large and mid-cap stocks. The result is 423 small and 1 mid.

---

## 3. Backtest: v3 unchanged on the new universe (Step 6)

**Setup:**
- 5-minute candles, 17 Jul – 7 Oct 2026 (44 trading days with signals);
- ₹5 lakh risk-sized desk portfolio, and every trade restated at ₹25,000 (no margin);
- full charges plus 0.03% slippage per side; stress test at 0.06%.

| Run | Trades | Win % | Net R per trade | Profit factor | ₹5 lakh result | Max drawdown |
|---|---|---|---|---|---|---|
| **New 424, v3** | 120 | 37.5% | −0.04R | 0.94 | **−2.20%** | −6.2% |
| New 424, v3, slippage 0.06% | 120 | 37.5% | −0.09R | 0.86 | −5.25% | −7.0% |
| New 424, v2 (no trend veto) | 145 | 42.8% | 0.00R | 1.00 | −0.10% | −6.3% |
| **Your list, v3, same dates** | 34 | 67.6% | +0.54R | 2.50 | **+9.18%** | −1.8% |

**At ₹25,000 per trade:**

| | Trades | Win % | Gross ₹ | Charges ₹ | **Net ₹** | First 60% / last 40% |
|---|---|---|---|---|---|---|
| New 424, desk portfolio | 120 | 37.5% | +1,453 | 5,090 | **−3,637** | −2,398 / −1,239 |
| New 424, every signal (no desk limits) | 153 | 39.2% | +3,055 | 6,456 | **−3,402** | −2,950 / −452 |
| Your list, same dates | 34 | 67.6% | +5,559 | 1,482 | **+4,077** | +1,365 / +2,712 |

The breakdowns below use the 153 "every signal" trades, so each group has more trades.
#### Longs vs shorts

| Group | Trades | Win % | Gross ₹ | Charges ₹ | Net ₹ | First 60% / last 40% |
|---|---|---|---|---|---|---|
| SHORT | 28 | 35.7 | +314 | 1,186 | **-872** | -24 / -848 |
| LONG | 125 | 40.0 | +2,741 | 5,270 | **-2,529** | -2,926 / +397 |

#### By liquidity tier

| Group | Trades | Win % | Gross ₹ | Charges ₹ | Net ₹ | First 60% / last 40% |
|---|---|---|---|---|---|---|
| T2 10-20cr | 27 | 44.4 | +3,146 | 1,144 | **+2,002** | +3,087 / -1,085 |
| T1 >=20cr | 36 | 41.7 | +2,509 | 1,521 | **+988** | +716 / +272 |
| T3 5-10cr | 32 | 43.8 | +527 | 1,356 | **-830** | -2,636 / +1,807 |
| T5 1-2cr | 18 | 33.3 | -299 | 756 | **-1,055** | -506 / -550 |
| T4 2-5cr | 40 | 32.5 | -2,828 | 1,679 | **-4,507** | -3,611 / -895 |

#### By fundamental score (does quality help intraday?)

| Group | Trades | Win % | Gross ₹ | Charges ₹ | Net ₹ | First 60% / last 40% |
|---|---|---|---|---|---|---|
| bottom 100 score | 42 | 50.0 | +5,193 | 1,812 | **+3,381** | +1,923 / +1,458 |
| middle | 73 | 35.6 | -1,850 | 3,049 | **-4,899** | -4,591 / -309 |
| top 100 score | 38 | 34.2 | -289 | 1,595 | **-1,883** | -282 / -1,601 |

#### By policy theme

| Group | Trades | Win % | Gross ₹ | Charges ₹ | Net ₹ | First 60% / last 40% |
|---|---|---|---|---|---|---|
| Auto & components PLI | 17 | 52.9 | +2,583 | 713 | **+1,870** | +790 / +1,080 |
| White goods / textiles / food PLI | 10 | 50.0 | +1,195 | 426 | **+769** | -1,389 / +2,158 |
| Power, T&D and RDSS | 4 | 25.0 | +554 | 166 | **+388** | +901 / -513 |
| Telecom PLI | 2 | 50.0 | +139 | 85 | **+54** | +359 / -305 |
| Electronics / semiconductors | 1 | 0.0 | -294 | 38 | **-331** | -331 / +0 |
| Pharma / medical devices PLI | 5 | 40.0 | -312 | 212 | **-524** | -342 / -183 |
| Specialty steel PLI | 8 | 37.5 | -331 | 343 | **-674** | -689 / +15 |
| Infrastructure capex | 11 | 36.4 | -1,214 | 467 | **-1,681** | -1,058 / -623 |
| none | 95 | 36.8 | +735 | 4,006 | **-3,271** | -1,191 / -2,080 |

#### By sector

| Group | Trades | Win % | Gross ₹ | Charges ₹ | Net ₹ | First 60% / last 40% |
|---|---|---|---|---|---|---|
| Consumer Cyclical | 38 | 50.0 | +4,870 | 1,622 | **+3,248** | +510 / +2,738 |
| Energy | 4 | 50.0 | +946 | 173 | **+773** | +402 / +371 |
| Consumer Defensive | 15 | 46.7 | +1,244 | 640 | **+603** | +359 / +244 |
| Technology | 6 | 33.3 | -119 | 249 | **-368** | -62 / -305 |
| Financial Services | 15 | 33.3 | +226 | 638 | **-412** | -297 / -115 |
| Real Estate | 5 | 20.0 | -250 | 206 | **-457** | -394 / -63 |
| Industrials | 29 | 37.9 | +23 | 1,217 | **-1,193** | +316 / -1,510 |
| Healthcare | 11 | 27.3 | -1,705 | 458 | **-2,164** | -614 / -1,549 |
| Basic Materials | 30 | 33.3 | -2,180 | 1,252 | **-3,432** | -3,170 / -262 |

#### Best and worst 10 stocks (₹ net, every signal)

| Worst | ₹ | Best | ₹ |
|---|---|---|---|
| SKIPPER | -890 | WHEELS | +1918 |
| SOMANYCERA | -886 | GMMPFAUDLR | +1697 |
| RAYMOND | -823 | DYCL | +1416 |
| TMB | -762 | MVGJL | +1300 |
| GULPOLY | -754 | SMCGLOBAL | +904 |
| PITTIENG | -659 | JINDRILL | +904 |
| BHAGERIA | -631 | ORIENTHOT | +849 |
| MIDHANI | -629 | RANEHOLDIN | +700 |
| ARIHANTCAP | -620 | BOROLTD | +671 |
| IRISDOREME | -616 | PARAGMILK | +637 |

---

## 4. Bias warnings

- **Look-ahead in the selection.** The list was built from *today's* fundamentals and policy knowledge, then tested on the past 3 months. If anything, that should flatter the result, and it still lost.
- **Survivorship.** Delisted and suspended stocks are missing.
- **Small sample.** 44 days of 5-minute data. The comparison with your list (34 trades) is also small.
- **Liquidity and costs.** Small caps in the ₹1–5 Cr tiers have wider bid-ask spreads than the 0.03% slippage assumed. The 0.06% stress test shows the loss grows quickly.
- **Data gaps.** No pledge, NPA, auditor or surveillance data, so a few stocks a fund would reject on governance may remain.

## 5. Plain-language summary

- **Is v3 portable to new stocks? No.**
  - On 424 fresh, fundamentally sound stocks over the same 3 months, v3 lost money: −₹3,637 at ₹25,000 per trade, a 38% win rate.
  - Your list made +₹4,077 with 68% winners.
  - The v3 result on your list now looks partly **specific to those stocks and that period**, which is exactly what this test was meant to check.
- **Do fundamentals or government policy make intraday trading better? No evidence.**
  - Low-scored stocks did better than high-scored ones.
  - Policy-theme stocks were mixed: auto components and white goods did well, while infrastructure and pharma lost.
  - Long-term quality and 5-minute price behaviour are different things.
- **What did matter: liquidity.** The strategy is only plausible in stocks trading ≥ ₹10 Cr a day. In the ₹1–5 Cr tiers, charges and slippage eat every gain.
- **Recommendations:**
  1. Use this 424-stock list for **long-term or swing investing research**, which is what fund-style screens are for, not for intraday trading.
  2. Keep v3 restricted to highly liquid stocks (≥ ₹10–20 Cr a day).
  3. Before trusting v3 at all, test it on 1–3 years of 5-minute data (Dhan/Kite). The out-of-sample failure here is a serious warning.
