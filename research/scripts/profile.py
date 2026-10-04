import pandas as pd, numpy as np, json, glob, os
m=json.load(open('/home/user/AccessLLM/all_profile_metadata.json'))
sec={k.replace('.NS',''):v['sector'] for k,v in m.items()}
nifty=pd.read_csv('data/1d/^NSEI.csv',index_col=0,parse_dates=True)['Close']
rows=[]
for f in glob.glob('data/1d/*.csv'):
    s=os.path.basename(f)[:-4]
    if s.startswith('^'): continue
    d=pd.read_csv(f,index_col=0,parse_dates=True).dropna()
    if len(d)<260: continue
    c=d.Close; h=d.High; l=d.Low
    tr=pd.concat([h-l,(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1)
    atr=tr.rolling(14).mean()
    turn=(c*d.Volume).rolling(20).median()
    n=nifty.reindex(c.index).ffill()
    r=lambda k: c.iloc[-1]/c.iloc[-1-k]-1
    rn=lambda k: n.iloc[-1]/n.iloc[-1-k]-1
    rows.append(dict(sym=s,sector=sec.get(s,''),close=c.iloc[-1],turnover_cr=turn.iloc[-1]/1e7,
        atr_pct=100*atr.iloc[-1]/c.iloc[-1], adr_pct=100*((h-l)/c).rolling(20).mean().iloc[-1],
        ret1w=100*r(5),ret1m=100*r(21),ret3m=100*r(63),ret6m=100*r(126),
        rs1m=100*(r(21)-rn(21)),rs3m=100*(r(63)-rn(63)),
        above50=c.iloc[-1]>c.rolling(50).mean().iloc[-1], above200=c.iloc[-1]>c.rolling(200).mean().iloc[-1],
        dist52h=100*(c.iloc[-1]/h.rolling(252).max().iloc[-1]-1),
        rvol5=d.Volume.iloc[-5:].mean()/d.Volume.iloc[-55:-5].mean()))
p=pd.DataFrame(rows); p.to_csv('profile.csv',index=False)
print(len(p), 'stocks; last date', nifty.index[-1].date())
print(p[['turnover_cr','atr_pct','adr_pct']].describe(percentiles=[.1,.25,.5,.75,.9]).round(2))
# simplify sectors
def grp(s):
    s=s.lower()
    for k,v in [('bank','Banks'),('financ','Financials'),('nbfc','Financials'),('insur','Financials'),('pharma','Pharma/Health'),('health','Pharma/Health'),('hospital','Pharma/Health'),('software','IT'),('it ','IT'),('information','IT'),('auto','Auto'),('steel','Metals'),('metal','Metals'),('mining','Metals'),('alumin','Metals'),('cement','Cement/Infra'),('construct','Cement/Infra'),('infra','Cement/Infra'),('realty','Realty'),('real estate','Realty'),('power','Power/Energy'),('oil','Power/Energy'),('gas','Power/Energy'),('energy','Power/Energy'),('chemical','Chemicals'),('fertil','Chemicals'),('fmcg','FMCG/Consumer'),('consumer','FMCG/Consumer'),('food','FMCG/Consumer'),('textile','Textiles'),('defen','Capital Goods/Defence'),('capital goods','Capital Goods/Defence'),('engineer','Capital Goods/Defence'),('electric','Capital Goods/Defence'),('telecom','Telecom/Media'),('media','Telecom/Media')]:
        if k in s: return v
    return 'Other'
p['grp']=p.sector.map(grp)
print(p.grp.value_counts())
g=p.groupby('grp').agg(n=('sym','size'),ret1m=('ret1m','median'),ret3m=('ret3m','median'),rs3m=('rs3m','median'),pct_above50=('above50','mean'),atr=('atr_pct','median')).sort_values('rs3m',ascending=False)
print(g.round(2))
p.to_csv('profile.csv',index=False)
