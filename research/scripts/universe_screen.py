"""Fund-house style screen for a 500-stock universe outside the existing 597-stock list.

Inputs (built in research/UNIVERSE_500.md, step 0): candidates_liq.csv (NSE/BSE candidates with
20-day liquidity) and one Yahoo fundamentals JSON per candidate. Steps:
  1 eligibility (listing age, market cap, price, liquidity tier)
  2 financial quality score 0-100 (sector-relative percentiles), red-flag exclusions
  3 governance adjustment (-15..+10) from holdings / dividends available in the data
  4 policy tailwind (0..+15): sector theme (max +5) or sourced company evidence (+15)
  5 selection of 500 with sector / count limits, relaxing liquidity first
Usage: python universe_screen.py <work_dir> <out_dir>
"""

import json
import os
import sys

import numpy as np
import pandas as pd

TODAY = pd.Timestamp("2026-10-08")

# ----------------------------------------------------------------------------- policy map
# theme -> (official anchor, source)
THEMES = {
    "Defence indigenisation": ("75% of FY26 defence modernisation budget earmarked for domestic procurement; positive indigenisation lists (5th list: 346 items, Jul 2024); MoD budget FY27 Rs 7.85 lakh cr",
                               "https://idsa.in/publisher/issuebrief/ministry-of-defence-2026-27-budget-estimates-an-analysis ; https://www.drishtiias.com/daily-updates/daily-news-analysis/5th-positive-indigenisation-list-1"),
    "Railways capex": ("Union Budget 2026-27: ~Rs 2.93 trillion for Indian Railways, rolling stock Rs 521 bn the largest head",
                       "https://indianinfrastructure.com/2026/02/02/union-budget-2026-27-highlights-for-infrastructure-sectors/"),
    "Infrastructure capex": ("Union Budget 2026-27 capex ~Rs 12.2 lakh cr (+11.5%), MoRTH Rs 3.10 trillion",
                             "https://www.outlookbusiness.com/budget/budget-2026-fm-sitharaman-raises-capex-for-fy27-to-122-lakh-crore ; https://prsindia.org/files/budget/budget_parliament/2026/Analysis_of_Expenditure_2026-27.pdf"),
    "Power, T&D and RDSS": ("Revamped Distribution Sector Scheme smart-metering (about 15.6 cr meters tendered) and transmission capex",
                            "https://www.tndindia.com/genus-power-outstanding-order-book-exceeds-rs-25000-crore/amp/"),
    "Renewable energy / solar PLI": ("Solar PV module PLI: 39.6 GW allotted in tranche II (48.3 GW total), Rs 64,873 cr investment",
                                     "https://jmkresearch.com/39-6-gw-cumulative-solar-pv-module-manufacturing-capacity-allotted-under-pli-tranche-2/ ; https://www.businesstoday.in/amp/latest/economy/story/pli-scheme-attracts-rs-2-4-lakh-crore-in-investments-till-march-2026-536415-2026-06-11"),
    "Electronics / semiconductors": ("Electronics Component Manufacturing Scheme (106 approvals, Rs 695 bn) and India Semiconductor Mission (10+ approved projects, Rs 1.6 lakh cr)",
                                     "https://indianinfrastructure.com/2026/08/18/government-approved-31-proposals-under-electronics-components-manufacturing-scheme/ ; https://static.pib.gov.in/WriteReadData/specificdocs/documents/2026/feb/doc202627782201.pdf"),
    "Pharma / medical devices PLI": ("PLI for bulk drugs, pharmaceuticals and medical devices (Department of Pharmaceuticals approved lists)",
                                     "https://www.pharma-dept.gov.in/schemes/archive"),
    "Auto & components PLI": ("PLI for automobiles and auto components (one of 14 PLI sectors)",
                              "https://www.outlookbusiness.com/corporate/806-applications-approved-under-pli-schemes-across-14-sectors"),
    "White goods / textiles / food PLI": ("PLI for white goods (ACs/LED), textiles and food processing (14 PLI sectors)",
                                          "https://www.india-briefing.com/news/indias-pli-scheme-for-white-goods-ac-and-led-status-updates-24506.html"),
    "Specialty steel PLI": ("PLI for specialty steel (14 PLI sectors)",
                            "https://www.outlookbusiness.com/corporate/806-applications-approved-under-pli-schemes-across-14-sectors"),
    "Telecom PLI": ("PLI for telecom and networking products (14 PLI sectors)",
                    "https://www.outlookbusiness.com/corporate/806-applications-approved-under-pli-schemes-across-14-sectors"),
}

# Yahoo industry keyword -> theme (sector-level tailwind, max +5)
INDUSTRY_THEME = [
    ("aerospace", "Defence indigenisation"), ("defense", "Defence indigenisation"),
    ("railroad", "Railways capex"),
    ("engineering & construction", "Infrastructure capex"), ("infrastructure", "Infrastructure capex"),
    ("building materials", "Infrastructure capex"), ("building products", "Infrastructure capex"),
    ("electrical equipment", "Power, T&D and RDSS"), ("utilities—regulated", "Power, T&D and RDSS"),
    ("utilities - regulated", "Power, T&D and RDSS"),
    ("renewable", "Renewable energy / solar PLI"), ("solar", "Renewable energy / solar PLI"),
    ("semiconductor", "Electronics / semiconductors"), ("electronic components", "Electronics / semiconductors"),
    ("scientific & technical", "Electronics / semiconductors"), ("consumer electronics", "Electronics / semiconductors"),
    ("drug manufacturers", "Pharma / medical devices PLI"), ("medical devices", "Pharma / medical devices PLI"),
    ("medical instruments", "Pharma / medical devices PLI"),
    ("auto parts", "Auto & components PLI"), ("auto manufacturers", "Auto & components PLI"),
    ("furnishings", "White goods / textiles / food PLI"), ("textile", "White goods / textiles / food PLI"),
    ("packaged foods", "White goods / textiles / food PLI"),
    ("steel", "Specialty steel PLI"),
    ("communication equipment", "Telecom PLI"),
]
POLICY_RISK = [("agricultural inputs", "fertiliser subsidy / price controls"),
               ("confectioners", "sugar export curbs"), ("farm products", "export curbs / stock limits"),
               ("oil & gas refining", "windfall tax / fuel price controls"), ("tobacco", "excise / GST changes")]

# companies with sourced, company-specific evidence of benefiting (+15)
DIRECT = {
    "IDEAFORGE": ("Defence indigenisation", "Named beneficiary, PLI scheme for drones (MoCA provisional list)",
                  "https://www.tribuneindia.com/news/business/adani-joint-venture-ideaforge-among-14-firms-selected-as-beneficiaries-of-pli-scheme-for-drone-manufacturing-387998"),
    "PARAS": ("Defence indigenisation", "Paras Aerospace named in drone PLI beneficiary list",
              "https://raksha-anirveda.com/?p=43364"),
    "GENUSPOWER": ("Power, T&D and RDSS", "Smart-meter order book ~Rs 24,020 cr (Jun 2026), mostly RDSS AMISP projects",
                   "https://nsearchives.nseindia.com/corporate/GENUSPOWER_19052026093441_Press_Release_Signed.pdf"),
    "HPL": ("Power, T&D and RDSS", "Order book > Rs 3,200 cr (Aug 2026), ~96% smart metering",
            "https://www.tndindia.com/hpl-electric-power-ltd-order-book-surpasses-rs-3200-crore/amp/"),
    "JUPITERWAG": ("Railways capex", "Order book Rs 4,675 cr (Mar 2026); Vande Bharat wheelsets and LHB axles from Ministry of Railways",
                   "https://compoundingai.in/market-news/jwl-q4-fy26-earnings-call"),
    "ASTRAMICRO": ("Defence indigenisation", "Consolidated order book Rs 2,849 cr (Jun 2026) + Rs 2,205 cr HAL Uttam radar order (Jul 2026)",
                   "https://nsearchives.nseindia.com/corporate/ASTRAMICRO_10082026163251_PressRelease.pdf"),
    "APOLLO": ("Defence indigenisation", "Rs 213 cr orders from DRDO and defence PSUs (Aug 2026)",
               "https://www.angelone.in/news/stocks/apollo-micro-systems-secures-2133-91-million-orders-from-drdo-defence-psus-and-private-industries"),
    "AVANTEL": ("Defence indigenisation", "Rs 117.9 cr DRDO ground-segment order (Aug 2026)",
                "https://www.multibagg.ai/market-pulse/articles/avantel-drdo-ground-hub-order-cmtg2h74n000j2ts53akqk1kj"),
    "AARTIPHARM": ("Pharma / medical devices PLI", "Approved products under pharmaceuticals PLI (DoP annexure, Oct 2024)",
                   "https://www.pharma-dept.gov.in/sites/default/files/PPO%20DOP17oct2024.pdf"),
}


# ----------------------------------------------------------------------------- financial metrics
def _series(block, key):
    """values newest first for one line item across the (up to 4) annual statements"""
    out = []
    for d in sorted(block, reverse=True):
        v = block[d].get(key)
        out.append(np.nan if v is None else v)
    return np.array(out, dtype=float)


def _first(block, keys):
    for k in keys:
        s = _series(block, k)
        if len(s) and np.isfinite(s).any():
            return s
    return np.array([])


def metrics(rec):
    i, IS, BS, CF = rec["info"], rec["is"], rec["bs"], rec["cf"]
    rev = _first(IS, ["Total Revenue", "Operating Revenue"])
    ni = _first(IS, ["Net Income", "Net Income Common Stockholders"])
    ebit = _first(IS, ["EBIT", "Operating Income"])
    opi = _first(IS, ["Operating Income", "EBIT"])
    intr = _first(IS, ["Interest Expense", "Interest Expense Non Operating"])
    eq = _first(BS, ["Stockholders Equity", "Common Stock Equity", "Total Equity Gross Minority Interest"])
    debt = _first(BS, ["Total Debt"])
    assets = _first(BS, ["Total Assets"])
    ca, cl = _first(BS, ["Current Assets"]), _first(BS, ["Current Liabilities"])
    ocf = _first(CF, ["Operating Cash Flow"])
    fcf = _first(CF, ["Free Cash Flow"])
    m = {"years": int(np.isfinite(rev).sum()) if len(rev) else 0}

    def g(a, k):
        return a[k] if 0 <= k < len(a) and np.isfinite(a[k]) else np.nan
    n3 = min(3, len(ni), len(eq))
    roe = [g(ni, k) / g(eq, k) for k in range(n3) if g(eq, k) and g(eq, k) > 0]
    m["roe3"] = np.nanmean(roe) * 100 if roe else np.nan
    cap = [g(ebit, k) / (g(eq, k) + (g(debt, k) if np.isfinite(g(debt, k)) else 0)) for k in range(min(3, len(ebit), len(eq)))
           if np.isfinite(g(eq, k)) and g(eq, k) > 0]
    m["roce3"] = np.nanmean(cap) * 100 if cap else np.nan
    roa = [g(ni, k) / g(assets, k) for k in range(min(3, len(ni), len(assets))) if g(assets, k)]
    m["roa3"] = np.nanmean(roa) * 100 if roa else np.nan
    m["op_margin"] = g(opi, 0) / g(rev, 0) * 100 if g(rev, 0) else np.nan
    kk = min(2, len(rev) - 1, len(opi) - 1)
    old = g(opi, kk) / g(rev, kk) * 100 if kk >= 1 and g(rev, kk) else np.nan
    m["op_margin_trend"] = m["op_margin"] - old
    k = min(3, m["years"] - 1)
    m["rev_cagr"] = ((g(rev, 0) / g(rev, k)) ** (1 / k) - 1) * 100 if k >= 1 and g(rev, k) and g(rev, k) > 0 and g(rev, 0) > 0 else np.nan
    m["np_cagr"] = ((g(ni, 0) / g(ni, k)) ** (1 / k) - 1) * 100 if k >= 1 and g(ni, k) and g(ni, k) > 0 and g(ni, 0) > 0 else np.nan
    m["rev_growth_1y"] = (g(rev, 0) / g(rev, 1) - 1) * 100 if g(rev, 1) and g(rev, 1) > 0 else np.nan
    m["de"] = g(debt, 0) / g(eq, 0) if g(eq, 0) and g(eq, 0) > 0 and np.isfinite(g(debt, 0)) else (np.nan if not len(eq) else np.inf if g(eq, 0) <= 0 else 0.0)
    m["int_cover"] = g(ebit, 0) / abs(g(intr, 0)) if g(intr, 0) else np.nan
    m["current_ratio"] = g(ca, 0) / g(cl, 0) if g(cl, 0) else np.nan
    s_ocf, s_ni = np.nansum(ocf[:3]) if len(ocf) else np.nan, np.nansum(ni[:3]) if len(ni) else np.nan
    m["ocf_to_np"] = s_ocf / s_ni if s_ni and s_ni > 0 else np.nan
    m["fcf_pos_years"] = int((fcf[:3] > 0).sum()) if len(fcf) else np.nan
    m["neg_equity"] = bool(len(eq) and g(eq, 0) <= 0)
    m["loss_years_3"] = int((ni[:3] < 0).sum()) if len(ni) else np.nan
    m["neg_ocf_years_3"] = int((ocf[:3] < 0).sum()) if len(ocf) else np.nan
    m["pe"], m["pb"] = i.get("trailingPE"), i.get("priceToBook")
    m["mcap_cr"] = (i.get("marketCap") or np.nan) / 1e7
    m["insiders_pct"] = (i.get("heldPercentInsiders") or np.nan) * 100
    m["institutions_pct"] = (i.get("heldPercentInstitutions") or np.nan) * 100
    m["div_yield"] = i.get("dividendYield")
    m["yahoo_sector"], m["yahoo_industry"] = i.get("sector") or "Unknown", i.get("industry") or ""
    return m


def pct_rank(s, higher_better=True):
    r = s.rank(pct=True)
    return (r if higher_better else 1 - r + 1 / max(len(s), 1)).fillna(0.5) * 100   # unknown -> neutral 50


def main():
    work, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    C = pd.read_csv(os.path.join(work, "candidates_liq.csv"))
    nse = pd.read_csv(os.path.join(work, "EQUITY_L.csv"))
    nse.columns = [c.strip() for c in nse.columns]
    listed = dict(zip(nse.SYMBOL, pd.to_datetime(nse["DATE OF LISTING"], format="%d-%b-%Y", errors="coerce")))
    rows = []
    for _, c in C.iterrows():
        p = os.path.join(work, "fund", f"{c.yf}.json")
        base = dict(symbol=c.symbol, exchange=c.exchange, company=c.company, yf=c.yf, price=c.price,
                    turn20_cr=c.turn20_cr, vol20=c.vol20, listed=listed.get(c.symbol))
        if not os.path.exists(p):
            rows.append(dict(base, has_fund=False))
            continue
        rows.append(dict(base, has_fund=True, **metrics(json.load(open(p)))))
    D = pd.DataFrame(rows)
    D["fin"] = D.yahoo_sector.eq("Financial Services")

    # ------------------------------------------------------------- step 1 eligibility
    D["f_exchange_data"] = D.exchange.eq("NSE") & D.price.notna()
    D["f_listing_3y"] = D.listed.notna() & (D.listed <= TODAY - pd.DateOffset(years=3))
    D["f_fundamentals"] = D.has_fund.fillna(False) & (D.years >= 3)
    D["f_mcap"] = D.mcap_cr >= 1000
    D["f_price"] = D.price.between(50, 15000)
    # ------------------------------------------------------------- red flags
    D["rf_neg_equity"] = D.neg_equity.fillna(False).astype(bool)
    D["rf_losses"] = D.loss_years_3.fillna(0) >= 2
    D["rf_debt"] = (~D.fin) & (D.de > 2)
    D["rf_cash"] = (~D.fin) & (D.neg_ocf_years_3.fillna(0) >= 2)
    D["red_flags"] = D[["rf_neg_equity", "rf_losses", "rf_debt", "rf_cash"]].apply(
        lambda r: ", ".join(k[3:] for k, v in r.items() if v), axis=1)

    # ------------------------------------------------------------- step 2 quality score (sector-relative)
    E = D[D.f_fundamentals].copy()
    parts = []
    for sec, g in E.groupby("yahoo_sector"):
        g = g.copy()
        ret = g.roa3 if sec == "Financial Services" else g.roce3
        g["s_profit"] = (pct_rank(g.roe3) + pct_rank(ret) + pct_rank(g.op_margin) + pct_rank(g.op_margin_trend)) / 4
        g["s_growth"] = (pct_rank(g.rev_cagr) + pct_rank(g.np_cagr) + pct_rank(g.rev_growth_1y)) / 3
        if sec == "Financial Services":
            g["s_balance"] = pct_rank(g.roa3)            # bank/NBFC capital & NPA data not available: use ROA
        else:
            g["s_balance"] = (pct_rank(g.de, False) + pct_rank(g.int_cover) + pct_rank(g.current_ratio)) / 3
        g["s_cash"] = 50.0 if sec == "Financial Services" else (pct_rank(g.ocf_to_np) + pct_rank(g.fcf_pos_years)) / 2
        med_pe = g.pe.where(g.pe > 0).median()
        med_pb = g.pb.where(g.pb > 0).median()
        val = pd.Series(100.0, index=g.index)
        val[(g.pe > 3 * med_pe) | (g.pb > 3 * med_pb)] = 40.0
        val[g.pe.isna() | (g.pe <= 0)] = 60.0
        g["s_value"] = val
        parts.append(g)
    E = pd.concat(parts)
    E["quality"] = (0.25 * E.s_profit + 0.25 * E.s_growth + 0.20 * E.s_balance + 0.15 * E.s_cash + 0.15 * E.s_value).round(1)

    # ------------------------------------------------------------- step 3 governance (data available: holdings, dividends)
    gov = pd.Series(0.0, index=E.index)
    gov += np.where(E.insiders_pct.between(40, 75), 4, np.where(E.insiders_pct < 20, -5, 0))
    gov += np.where(E.insiders_pct > 85, -5, 0)                    # very low free float
    gov += np.where(E.institutions_pct >= 15, 4, np.where(E.institutions_pct < 3, -3, 0))
    gov += np.where(E.div_yield.fillna(0) > 0, 2, 0)
    E["governance"] = gov.clip(-15, 10)

    # ------------------------------------------------------------- step 4 policy
    def theme_of(r):
        if r.symbol in DIRECT:
            t, ev, src = DIRECT[r.symbol]
            return t, 15, ev, src
        ind = str(r.yahoo_industry).lower()
        for k, t in INDUSTRY_THEME:
            if k in ind:
                return t, 5, f"sector-level only (Yahoo industry: {r.yahoo_industry})", THEMES[t][1]
        return "", 0, "", ""
    th = E.apply(theme_of, axis=1, result_type="expand")
    E["policy_theme"], E["policy"], E["policy_evidence"], E["policy_source"] = th[0], th[1], th[2], th[3]
    E["policy_risk"] = E.yahoo_industry.str.lower().apply(lambda s: next((v for k, v in POLICY_RISK if k in s), ""))
    E["final_score"] = (E.quality + E.governance + E.policy).round(1)
    D = D.join(E[[c for c in E.columns if c not in D.columns]])

    # ------------------------------------------------------------- step 5 selection, relaxing liquidity first
    base = D.f_exchange_data & D.f_listing_3y & D.f_fundamentals & D.f_mcap & D.f_price & D.red_flags.eq("")
    tiers = [(20, 2e5), (10, 1e5), (5, 5e4), (3, 5e4), (2, 2.5e4)]
    funnel = [("candidates (597 removed)", len(D)), ("NSE with price data", int(D.f_exchange_data.sum())),
              ("+ listed >= 3 years", int((D.f_exchange_data & D.f_listing_3y).sum())),
              ("+ 3y fundamentals available", int((D.f_exchange_data & D.f_listing_3y & D.f_fundamentals).sum())),
              ("+ market cap >= Rs 1,000 cr", int((D.f_exchange_data & D.f_listing_3y & D.f_fundamentals & D.f_mcap).sum())),
              ("+ price Rs 50-15,000", int((D.f_exchange_data & D.f_listing_3y & D.f_fundamentals & D.f_mcap & D.f_price).sum())),
              ("+ no red flags", int(base.sum()))]
    chosen_tier = None
    for t, v in tiers:
        ok = base & (D.turn20_cr >= t) & (D.vol20 >= v)
        funnel.append((f"+ liquidity >= Rs {t} cr & {int(v):,} shares", int(ok.sum())))
        if chosen_tier is None and ok.sum() >= 500:
            chosen_tier = (t, v)
    if chosen_tier is None:
        chosen_tier = tiers[-1]
    t, v = chosen_tier
    P = D[base & (D.turn20_cr >= t) & (D.vol20 >= v)].sort_values("final_score", ascending=False)
    cap = 60                                                     # 12% of 500 per sector
    picked, per = [], {}
    for idx, r in P.iterrows():
        if per.get(r.yahoo_sector, 0) >= cap:
            continue
        picked.append(idx)
        per[r.yahoo_sector] = per.get(r.yahoo_sector, 0) + 1
        if len(picked) == 500:
            break
    U = D.loc[picked].copy()
    U["mcap_bucket"] = pd.cut(U.mcap_cr, [0, 30000, 100000, np.inf], labels=["small (<30k cr)", "mid (30k-1L cr)", "large (>1L cr)"])
    U["liquidity_tier"] = np.select([U.turn20_cr >= 20, U.turn20_cr >= 10, U.turn20_cr >= 5], ["T1 >=20cr", "T2 10-20cr", "T3 5-10cr"], "T4 <5cr")
    U["rank"] = range(1, len(U) + 1)
    cols = ["rank", "symbol", "exchange", "company", "yahoo_sector", "yahoo_industry", "mcap_cr", "mcap_bucket", "price", "turn20_cr",
            "liquidity_tier", "final_score", "quality", "governance", "policy", "s_profit", "s_growth", "s_balance", "s_cash", "s_value",
            "roe3", "roce3", "roa3", "op_margin", "op_margin_trend", "rev_cagr", "np_cagr", "rev_growth_1y", "de", "int_cover",
            "current_ratio", "ocf_to_np", "fcf_pos_years", "pe", "pb", "insiders_pct", "institutions_pct", "div_yield",
            "policy_theme", "policy_evidence", "policy_source", "policy_risk", "years", "listed"]
    U[cols].to_csv(os.path.join(out, "universe_500.csv"), index=False)
    D.to_csv(os.path.join(out, "screening_all_candidates.csv"), index=False)
    pd.DataFrame(funnel, columns=["step", "stocks"]).to_csv(os.path.join(out, "funnel.csv"), index=False)
    print(pd.DataFrame(funnel, columns=["step", "stocks"]).to_string(index=False))
    print("liquidity tier used:", chosen_tier, "| selected", len(U))
    print(U.yahoo_sector.value_counts().to_string())
    print(U.mcap_bucket.value_counts().to_string())
    print(U.liquidity_tier.value_counts().to_string())
    print(U.policy_theme.replace("", "none").value_counts().to_string())


if __name__ == "__main__":
    main()
