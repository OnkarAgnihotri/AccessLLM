import pandas as pd, numpy as np, glob, os
COST=0.0025  # delivery round trip incl STT 0.1% each side + slippage
nifty=pd.read_csv('data/1d/^NSEI.csv',index_col=0,parse_dates=True).Close
n200=nifty>nifty.rolling(200).mean(); n50=nifty>nifty.rolling(50).mean()
rows=[]
for f in glob.glob('data/1d/*.csv'):
    s=os.path.basename(f)[:-4]
    if s.startswith('^'): continue
    d=pd.read_csv(f,index_col=0,parse_dates=True).dropna()
    if len(d)<400: continue
    c,h,l,o,v=d.Close,d.High,d.Low,d.Open,d.Volume
    turn=(c*v).rolling(20).median()
    dl=c.diff(); up=dl.clip(lower=0).ewm(alpha=1/2).mean(); dn=(-dl.clip(upper=0)).ewm(alpha=1/2).mean()
    rsi2=100-100/(1+up/dn)
    s5=c.rolling(5).mean(); s200=c.rolling(200).mean(); s50=c.rolling(50).mean()
    tr=pd.concat([h-l,(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1); atr=tr.rolling(14).mean()
    hi20=h.rolling(20).max().shift(1); lo20=l.rolling(20).min().shift(1)
    rs=(c/c.shift(63))/(nifty.reindex(c.index).ffill()/nifty.reindex(c.index).ffill().shift(63))
    C=c.values;O=o.values;Hh=h.values;L=l.values;idx=c.index
    def run(i,dirn,kind,maxh=10,exit_rule='sma5'):
        e=O[i+1] if i+1<len(C) else None  # enter next open
        if e is None: return
        stop=e-dirn*2.0*atr.iloc[i]
        for k in range(i+1,min(i+1+maxh,len(C))):
            if (dirn==1 and L[k]<=stop) or (dirn==-1 and Hh[k]>=stop): x=stop; break
            if exit_rule=='sma5' and ((dirn==1 and C[k]>s5.iloc[k]) or (dirn==-1 and C[k]<s5.iloc[k])): x=C[k]; break
            if exit_rule=='trail' and k>i+1:
                pass
        else: x=C[min(i+maxh,len(C)-1)]; k=min(i+maxh,len(C)-1)
        rows.append(dict(sym=s,date=idx[i],kind=kind,dir=dirn,ret=dirn*(x/e-1)-COST,hold=k-i,
                         n200=n200.get(idx[i],np.nan),n50=n50.get(idx[i],np.nan),liq=turn.iloc[i]>2e8,rs=rs.iloc[i],rsi=rsi2.iloc[i]))
    for i in range(220,len(C)-1):
        if np.isnan(atr.iloc[i]): continue
        # Connors RSI2 mean reversion
        if C[i]>s200.iloc[i] and C[i]<s5.iloc[i] and rsi2.iloc[i]<10: run(i,1,'RSI2_pullback_long')
        if C[i]<s200.iloc[i] and C[i]>s5.iloc[i] and rsi2.iloc[i]>90: run(i,-1,'RSI2_bounce_short')
        # 20-day breakout momentum with volume, hold 10 days
        if C[i]>hi20.iloc[i] and v.iloc[i]>1.5*v.iloc[i-20:i].mean() and C[i]>s50.iloc[i]>s200.iloc[i]: run(i,1,'Breakout20_long',maxh=10,exit_rule='none')
        if C[i]<lo20.iloc[i] and v.iloc[i]>1.5*v.iloc[i-20:i].mean() and C[i]<s50.iloc[i]<s200.iloc[i]: run(i,-1,'Breakdown20_short',maxh=10,exit_rule='none')
R=pd.DataFrame(rows); R.to_pickle('swing.pkl')
def summ(x):
    w=x.ret>0; return pd.Series(dict(n=len(x),win=100*w.mean(),avg=100*x.ret.mean(),avgwin=100*x.ret[w].mean(),avgloss=100*x.ret[~w].mean(),
        pf=x.ret[w].sum()/-x.ret[~w].sum(),hold=x.hold.mean()))
pd.set_option('display.width',200)
print(R.groupby('kind').apply(summ).round(2))
print('-- with market regime filter (long only when Nifty>200SMA, short only when Nifty<200SMA) + liquid')
m=((R.dir==1)&(R.n200==True))|((R.dir==-1)&(R.n200==False))
print(R[m&R.liq].groupby('kind').apply(summ).round(2))
print('-- RSI2 long, by RSI threshold, liquid, nifty>200')
x=R[(R.kind=='RSI2_pullback_long')&R.liq&(R.n200==True)]
for t in (10,5,2): print(t, summ(x[x.rsi<t]).round(2).to_dict())
print('-- by year'); R['yr']=R.date.dt.year
print(R[R.liq].groupby(['kind','yr']).apply(summ)[['n','win','avg','pf']].round(2).unstack(0).to_string())
