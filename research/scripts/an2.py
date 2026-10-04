import pandas as pd, numpy as np
D=pd.read_pickle('days.pkl'); D=D[D.turn>2e8].copy()   # liquid only (>20cr/day)
D['day']=pd.to_datetime(D.day); D['half']=np.where(D.day<'2025-04-01','IS','OOS')
D['rel']=D.fh-D.nfh; D['fh_atr']=D.fh/D.atr_pct; D['gap_atr']=D.gap/D.atr_pct
D['tot']=D.gap+D.fh  # move from prev close to 10:15
D['tot_atr']=D.tot/D.atr_pct
print('liquid stock-days',len(D))
def tab(col,q=10):
    D['b']=pd.qcut(D[col],q,duplicates='drop')
    t=D.groupby(['b','half'],observed=True).rest.agg(['mean','count',lambda r:(r>0).mean()]).unstack()
    t.columns=[f'{a}_{b}' for a,b in t.columns]
    t=t.rename(columns=lambda c:c.replace('<lambda_0>','up%'))
    for c in t.columns:
        if c.startswith('mean'): t[c]=(t[c]*1e4).round(1)
        if c.startswith('up%'): t[c]=(t[c]*100).round(1)
    print(f'\n== rest-of-day return (10:15 close -> 15:30 close, bps) by decile of {col}'); print(t.to_string())
for c in ['tot_atr','rel','gap_atr','fh_atr','near20h']: tab(c)
