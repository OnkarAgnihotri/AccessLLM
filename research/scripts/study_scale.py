import pandas as pd, numpy as np
exec(open('study_swing2.py').read().split('def sim')[0])
COST=0.0025
cs,os_,hs,ls,s5v,at=C.values,O.values,Hh.values,L.values,s5.values,atr.values
def run(sig,t1,stop_atr,be=True,maxh=10):
    ii,jj=np.where(sig.fillna(False).values); out=[]
    for i,j in zip(ii,jj):
        if i+maxh+1>=len(C): continue
        e=os_[i+1,j]; stp=e-stop_atr*at[i,j]; tg=e*(1+t1); half=None; rest=None
        for k in range(i+1,i+1+maxh):
            if half is None:
                if ls[k,j]<=stp: half=rest=stp/e-1; break
                if hs[k,j]>=tg:
                    half=t1
                    if be: stp=e
                    if cs[k,j]>s5v[k,j]: rest=cs[k,j]/e-1; break
                    continue
            else:
                if ls[k,j]<=stp: rest=stp/e-1; break
            if cs[k,j]>s5v[k,j]: 
                rest=cs[k,j]/e-1
                if half is None: half=rest
                break
        if rest is None: rest=cs[k,j]/e-1; half=half if half is not None else rest
        r=0.5*half+0.5*rest-COST
        out.append(dict(date=C.index[i],sym=C.columns[j],t1hit=half==t1,ret=r,risk=stop_atr*at[i,j]/e))
    return pd.DataFrame(out)
sig=liq&(C>s200)&(C>s50)&(C<s5)&(rsi2<5)&(rs>=0.7)
sigreg=sig&(nreg>0).values[:,None]
pd.set_option('display.width',200)
res=[]
for nm,sg in (('no regime',sig),('Nifty>200',sigreg)):
  for t1 in (0.01,0.015,0.02):
    for st in (2.0,3.0):
        R=run(sg,t1,st); R['per']=np.where(R.date<'2024-07-01','IS','OOS')
        for p,x in R.groupby('per'):
            w=x.ret>0
            res.append(dict(filter=nm,T1=t1*100,stopATR=st,per=p,n=len(x),T1_hit=round(100*x.t1hit.mean(),1),net_win=round(100*w.mean(),1),
                avg=round(100*x.ret.mean(),2),pf=round(x.ret[w].sum()/-x.ret[~w].sum(),2),avg_loss=round(100*x.ret[~w].mean(),2),worst=round(100*x.ret.min(),1)))
print(pd.DataFrame(res).to_string(index=False))
# how many signals today / recent
last=sig.iloc[-15:].sum(axis=1); print('signals last 15 days (no regime):',last.to_dict())
print('nifty regime last:',nreg.iloc[-1])
