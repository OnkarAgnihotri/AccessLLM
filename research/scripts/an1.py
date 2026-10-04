import pandas as pd, numpy as np
D=pd.read_pickle('days.pkl'); T=pd.read_pickle('orb_trades.pkl')
COST=0.0012
print('=== Intraday momentum: does first-hour direction continue for rest of day? ===')
D=D[D.fh!=0]
same=(np.sign(D.fh)==np.sign(D.rest))
print('all stock-days: P(rest same sign as first hour) = %.1f%%  n=%d'%(100*same.mean(),len(D)))
for lo,hi in [(0,1),(1,1.5),(1.5,2.5),(2.5,99)]:
    m=(D.rv>=lo)&(D.rv<hi); print(f' rvol {lo}-{hi}: {100*same[m].mean():.1f}%  n={m.sum()}  mean rest*sign(fh) = {1e4*(np.sign(D.fh)*D.rest)[m].mean():.1f} bps')
al=(np.sign(D.fh)==np.sign(D.nfh)); print(' stock FH same dir as Nifty FH: %.1f%%; not: %.1f%%'%(100*same[al].mean(),100*same[~al].mean()))
tr=(np.sign(D.fh)==D.trend); print(' FH in daily-trend dir: %.1f%%; against: %.1f%%'%(100*same[tr].mean(),100*same[(D.trend!=0)&~tr].mean()))

def stats(x,stop,tg,label):
    r=x[f'{stop}_{tg}']-COST/x['R_'+stop]
    w=(x[f'{stop}_{tg}']>0).mean()
    return dict(setup=label,stop=stop,tgt=tg,n=len(x),win=round(100*w,1),avgR_net=round(r.mean(),3),medR=round(x['R_'+stop].median()*100,2))
T['ok_trend']=T.dir==T.trend; T['ok_nifty']=np.sign(T.nfh)==T.dir; T['ok_gap']=np.sign(T.gap)==T.dir
T['liq']=T.turn>2e8
rows=[]
filt={'ALL':T.index==T.index,'trend':T.ok_trend,'trend+nifty':T.ok_trend&T.ok_nifty,
      'trend+nifty+rv1.5':T.ok_trend&T.ok_nifty&(T.rv>1.5),'trend+nifty+rv1.5+liq':T.ok_trend&T.ok_nifty&(T.rv>1.5)&T.liq,
      'trend+nifty+gap+rv1.5':T.ok_trend&T.ok_nifty&T.ok_gap&(T.rv>1.5),'counter-trend':(T.trend==-T.dir)}
for name,m in filt.items():
    for d in (1,-1):
        x=T[m&(T.dir==d)]
        for stop in ('or','mid','bar'):
            for tg in (0.5,1.0,2.0,99):
                rows.append(dict(stats(x,stop,tg,name),side='LONG' if d==1 else 'SHORT'))
R=pd.DataFrame(rows)
pd.set_option('display.width',200)
print(R[R.stop=='or'].to_string(index=False))
print(R[(R.stop!='or')&(R.setup.isin(['ALL','trend+nifty+rv1.5']))].to_string(index=False))
