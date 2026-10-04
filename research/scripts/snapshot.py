import pandas as pd, numpy as np
exec(open('study_swing2.py').read().split('def sim')[0])
p=pd.read_csv('profile.csv').set_index('sym')
def grp(s):
    s=str(s).lower()
    M=[('bank','Banks'),('financ','Financials/NBFC'),('insur','Financials/NBFC'),('exchange','Financials/NBFC'),('invest','Financials/NBFC'),('holding','Financials/NBFC'),
       ('pharma','Pharma/Healthcare'),('health','Pharma/Healthcare'),('hospital','Pharma/Healthcare'),('medical','Pharma/Healthcare'),
       ('software','IT'),('information','IT'),('it -','IT'),('computer','IT'),('auto','Auto'),('bearing','Auto'),('forging','Auto'),('tyre','Auto'),
       ('steel','Metals/Mining'),('metal','Metals/Mining'),('mining','Metals/Mining'),('alumin','Metals/Mining'),
       ('cement','Cement/Construction'),('construct','Cement/Construction'),('infra','Cement/Construction'),('realty','Realty'),('real estate','Realty'),
       ('utilit','Power/Utilities'),('power','Power/Utilities'),('oil','Oil & Gas'),('gas','Oil & Gas'),('energy','Oil & Gas'),('refin','Oil & Gas'),
       ('chemical','Chemicals/Materials'),('fertil','Chemicals/Materials'),('material','Chemicals/Materials'),('carbon','Chemicals/Materials'),('plastic','Chemicals/Materials'),('plywood','Chemicals/Materials'),
       ('fmcg','FMCG/Consumer'),('consumer','FMCG/Consumer'),('food','FMCG/Consumer'),('beverage','FMCG/Consumer'),('personal care','FMCG/Consumer'),('agro','FMCG/Consumer'),
       ('communication','Telecom/Media'),('retail','Retail/Hotels/Services'),('hotel','Retail/Hotels/Services'),('e-commerce','Retail/Hotels/Services'),('tour','Retail/Hotels/Services'),('services','Retail/Hotels/Services'),('watch','Retail/Hotels/Services'),('textile','Retail/Hotels/Services'),
       ('industrial','Capital Goods/Industrials'),('electric','Capital Goods/Industrials'),('engineer','Capital Goods/Industrials'),('defen','Capital Goods/Industrials'),('capital goods','Capital Goods/Industrials'),('pump','Capital Goods/Industrials'),('ship','Capital Goods/Industrials'),('port','Capital Goods/Industrials'),('logistic','Capital Goods/Industrials'),
       ('telecom','Telecom/Media'),('communication','Telecom/Media'),('media','Telecom/Media'),('print','Telecom/Media')]
    for k,v in M:
        if k in s: return v
    return 'Other'
p['grp']=p.sector.map(grp); print(p.grp.value_counts().to_string())
last=C.index[-1]
p['rs6m_pct']=(rs.iloc[-1]*100).round(0); p['rs3m_pct']=(rs3.iloc[-1]*100).round(0); p['rsi2']=rsi2.iloc[-1].round(1)
p['above50']=(C.iloc[-1]>s50.iloc[-1]); p['above200']=(C.iloc[-1]>s200.iloc[-1])
sec=p.groupby('grp').agg(stocks=('sector','size'),med_1m=('ret1m','median'),med_3m=('ret3m','median'),med_6m=('ret6m','median'),pct_above_50dma=('above50','mean'),pct_above_200dma=('above200','mean'),median_rs6m_pct=('rs6m_pct','median')).sort_values('median_rs6m_pct',ascending=False)
sec['pct_above_50dma']=(100*sec.pct_above_50dma).round(0); sec['pct_above_200dma']=(100*sec.pct_above_200dma).round(0)
print(sec.round(1).to_string()); sec.round(1).to_csv('sector_rank.csv')
lead=p[(p.turnover_cr>20)&(p.rs6m_pct>=70)&p.above200].sort_values('rs6m_pct',ascending=False)
cols=['grp','close','turnover_cr','atr_pct','ret1m','ret3m','ret6m','rs6m_pct','above50','dist52h','rsi2']
print('\nleaders:',len(lead)); print(lead[cols].round(1).head(40).to_string())
lead[cols].round(2).to_csv('leaders.csv')
cand=lead[(lead.above50)&(lead.rsi2<5)&(C.iloc[-1][lead.index]<s5.iloc[-1][lead.index])]
print('\nsetup today (RSI2<5 pullback in leaders):'); print(cand[cols].round(1).to_string())
cand[cols].round(2).to_csv('candidates.csv')
