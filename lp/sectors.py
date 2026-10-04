"""Map the mixed sector labels in all_profile_metadata.json to ~15 groups, and rank the groups."""

import pandas as pd

# first matching keyword wins, so more specific words come first
_RULES = [
    ("bank", "Banks"),
    ("communication", "Telecom/Media"), ("telecom", "Telecom/Media"), ("media", "Telecom/Media"),
    ("print", "Telecom/Media"),
    ("financ", "Financials/NBFC"), ("insur", "Financials/NBFC"), ("exchange", "Financials/NBFC"),
    ("invest", "Financials/NBFC"), ("holding", "Financials/NBFC"),
    ("pharma", "Pharma/Healthcare"), ("health", "Pharma/Healthcare"), ("hospital", "Pharma/Healthcare"),
    ("medical", "Pharma/Healthcare"),
    ("software", "IT"), ("information", "IT"), ("it -", "IT"), ("computer", "IT"),
    ("auto", "Auto"), ("bearing", "Auto"), ("forging", "Auto"), ("tyre", "Auto"),
    ("steel", "Metals/Mining"), ("metal", "Metals/Mining"), ("mining", "Metals/Mining"), ("alumin", "Metals/Mining"),
    ("cement", "Cement/Construction"), ("construct", "Cement/Construction"), ("infra", "Cement/Construction"),
    ("realty", "Realty"), ("real estate", "Realty"),
    ("utilit", "Power/Utilities"), ("power", "Power/Utilities"),
    ("oil", "Oil & Gas"), ("gas", "Oil & Gas"), ("energy", "Oil & Gas"), ("refin", "Oil & Gas"),
    ("chemical", "Chemicals/Materials"), ("fertil", "Chemicals/Materials"), ("material", "Chemicals/Materials"),
    ("carbon", "Chemicals/Materials"), ("plastic", "Chemicals/Materials"), ("plywood", "Chemicals/Materials"),
    ("fmcg", "FMCG/Consumer"), ("consumer", "FMCG/Consumer"), ("food", "FMCG/Consumer"),
    ("beverage", "FMCG/Consumer"), ("personal care", "FMCG/Consumer"), ("agro", "FMCG/Consumer"),
    ("retail", "Retail/Services"), ("hotel", "Retail/Services"), ("e-commerce", "Retail/Services"),
    ("tour", "Retail/Services"), ("services", "Retail/Services"), ("watch", "Retail/Services"),
    ("textile", "Retail/Services"),
    ("industrial", "Capital Goods"), ("electric", "Capital Goods"), ("engineer", "Capital Goods"),
    ("defen", "Capital Goods"), ("capital goods", "Capital Goods"), ("pump", "Capital Goods"),
    ("ship", "Capital Goods"), ("port", "Capital Goods"), ("logistic", "Capital Goods"),
]


def sector_group(label: str) -> str:
    s = (label or "").lower()
    for key, grp in _RULES:
        if key in s:
            return grp
    return "Other"


def rank_sectors(groups: dict, close: pd.DataFrame, rs_pct: pd.Series, sma_mid: pd.DataFrame) -> pd.DataFrame:
    """Sector table for the latest date: median returns, breadth and median RS percentile."""
    last = close.iloc[-1]
    rows = []
    for sym in close.columns:
        c = close[sym].dropna()
        if len(c) < 130:
            continue
        rows.append(dict(sector=groups.get(sym, "Other"),
                         ret_1m=100 * (c.iloc[-1] / c.iloc[-22] - 1),
                         ret_3m=100 * (c.iloc[-1] / c.iloc[-64] - 1),
                         ret_6m=100 * (c.iloc[-1] / c.iloc[-127] - 1),
                         above_50dma=bool(last[sym] > sma_mid[sym].iloc[-1]),
                         rs_pct=rs_pct.get(sym)))
    df = pd.DataFrame(rows)
    t = df.groupby("sector").agg(stocks=("rs_pct", "size"), median_rs_pct=("rs_pct", "median"),
                                 ret_1m=("ret_1m", "median"), ret_3m=("ret_3m", "median"),
                                 ret_6m=("ret_6m", "median"), pct_above_50dma=("above_50dma", "mean"))
    t["pct_above_50dma"] *= 100
    return t.sort_values("median_rs_pct", ascending=False).round(1)
