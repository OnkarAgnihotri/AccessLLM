import pandas as pd, numpy as np, glob, os
COST=0.0012
def ld(f):
    d=pd.read_csv(f); d['Date']=pd.to_datetime(d.Date,utc=True).dt.tz_convert('Asia/Kolkata')
    d=d.dropna(subset=['Close']).set_index('Date'); d['day']=d.index.date; return d
n=ld('data/15m/^NSEI.csv'); nd=n.groupby('day').apply(lambda x: x.Close.iloc[0]/x.Open.iloc[0]-1)
rows=[]
for f in glob.glob('data/15m/*.csv'):
    s=os.path.basename(f)[:-4]
    if s.startswith('^') or not os.path.exists(f'data/1d/{s}.csv'): continue
    d1=pd.read_csv(f'data/1d/{s}.csv',index_col=0,parse_dates=True).dropna(); c=d1.Close
    tr=pd.concat([d1.High-d1.Low,(d1.High-c.shift()).abs(),(d1.Low-c.shift()).abs()],axis=1).max(axis=1)
    dd=pd.DataFrame({'atr':tr.rolling(14).mean(),'pc':c,'e20':c.ewm(span=20).mean(),'e50':c.ewm(span=50).mean(),'turn':(c*d1.Volume).rolling(20).median()}).shift(1); dd.index=dd.index.date
    x=ld(f); g=[(k,v) for k,v in x.groupby('day') if len(v)>=20]
    v1=pd.Series({k:v.Volume.iloc[0] for k,v in g}); rv=v1/v1.rolling(10).mean().shift(1)
    for day,v in g:
        if day not in dd.index or np.isnan(rv.get(day,np.nan)): continue
        r=dd.loc[day]
        if np.isnan(r.atr) or r.turn<2e8: continue
        O,Hh,L,C=v.Open.values,v.High.values,v.Low.values,v.Close.values
        tp=(Hh+L+C)/3; vw=np.cumsum(tp*v.Volume.values)/np.maximum(np.cumsum(v.Volume.values),1)
        fb=C[0]-O[0]
        if fb==0: continue
        dirn=1 if fb>0 else -1   # Zarattini: trade in direction of first candle
        e=O[1]; stop=e-dirn*0.10*r.atr*1.0
        # variants: stop at 10% ATR (paper), stop at OR other side
        out={}
        for nm,stp in (('atr10',e-dirn*0.10*r.atr),('orside',L[0] if dirn==1 else Hh[0])):
            R=abs(e-stp)
            if R<=0: continue
            res=None
            for i in range(1,len(C)):
                if (dirn==1 and L[i]<=stp) or (dirn==-1 and Hh[i]>=stp): res=-1.0; break
            if res is None: res=(C[-1]-e)*dirn/R
            out[nm]=res-COST*e/R; out['R_'+nm]=R/e
        rows.append(dict(sym=s,day=day,dir=dirn,rv=rv[day],trend=1 if r.pc>r.e20>r.e50 else (-1 if r.pc<r.e20<r.e50 else 0),nfh=nd.get(day,0),**out))
T=pd.DataFrame(rows); T.to_pickle('orb15.pkl'); print('stock-days',len(T),'days',T.day.nunique())
def sm(x,c): return dict(n=len(x),win=round(100*(x[c]>0).mean(),1),avgR=round(x[c].mean(),3),medRpct=round(100*x['R_'+c].median(),2))
for c in ('atr10','orside'):
    print('\nstop',c)
    print(' all            ',sm(T,c))
    top=T.sort_values('rv',ascending=False).groupby('day').head(20)
    print(' top20 RVOL/day ',sm(top,c))
    print(' top20 + trend  ',sm(top[top.trend==top.dir],c))
    print(' top20 + trend + nifty',sm(top[(top.trend==top.dir)&(np.sign(top.nfh)==top.dir)],c))
    for d in (1,-1): print('  top20 side',d,sm(top[top.dir==d],c))
