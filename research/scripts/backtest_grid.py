import itertools, sys, pandas as pd, numpy as np
sys.path.insert(0,'/home/user/AccessLLM')
from lp.config import load_config
from lp.data import load_universe, load_panels
from lp.sectors import sector_group
from lp import signals, backtest, report
S=sys.argv[1]
uni=load_universe('/home/user/AccessLLM/all_profile_metadata.json'); groups={s:sector_group(l) for s,l in uni.items()}
panels,idx=load_panels(list(uni),S+'/data','^NSEI',min_bars=220,log=lambda *a:None)
F={}
rows=[]
for rsi_max,t1,stop,reg,brok in itertools.product((5,2),(1,2,3,1000),(2,3),('half','skip'),(20,0)):
    for per,(a,b) in {'IS':('','2024-06-30'),'OOS':('2024-07-01','')}.items():
        cfg=load_config(data_dir=S+'/data',rsi_max=rsi_max,t1_pct=t1,stop_atr=stop,regime_mode=reg,brokerage_per_order=brok,start=a,end=b)
        if rsi_max not in F: F[rsi_max]=signals.compute(panels,idx,cfg)
        r=backtest.run_backtest(panels,F[rsi_max],groups,cfg,log=lambda *a:None)
        s=report.stats(r,idx)
        rows.append(dict(rsi=rsi_max,t1=('off' if t1==1000 else t1),stop=stop,regime=reg,brok=brok,per=per,cagr=s['cagr_pct'],dd=s['max_drawdown_pct'],
                         trades=s['trades'],win=s.get('win_rate_pct'),avg=s.get('avg_trade_pct'),pf=s.get('profit_factor')))
R=pd.DataFrame(rows); R.to_csv(S+'/grid.csv',index=False)
W=R.pivot_table(index=['brok','rsi','t1','stop','regime'],columns='per',values=['cagr','avg','win','pf','trades','dd']).round(2)
W.columns=[f'{a}_{b}' for a,b in W.columns]
pd.set_option('display.width',250); pd.set_option('display.max_rows',200)
print(W[['trades_IS','trades_OOS','win_IS','win_OOS','avg_IS','avg_OOS','pf_IS','pf_OOS','cagr_IS','cagr_OOS','dd_IS','dd_OOS']].sort_values('avg_OOS',ascending=False).to_string())
