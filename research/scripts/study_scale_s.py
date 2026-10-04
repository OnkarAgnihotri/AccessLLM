import pandas as pd, numpy as np
exec(open('study_scale.py').read().split('sig=liq')[0])
# mirror for shorts: flip prices
def runs(sig,t1,stop_atr,maxh=10,cost=0.0012):  # futures cost lower (no delivery STT)
    ii,jj=np.where(sig.fillna(False).values); out=[]
    for i,j in zip(ii,jj):
        if i+maxh+1>=len(C): continue
        e=os_[i+1,j]; stp=e+stop_atr*at[i,j]; tg=e*(1-t1); half=None; rest=None
        for k in range(i+1,i+1+maxh):
            if half is None:
                if hs[k,j]>=stp: half=rest=1-stp/e; break
                if ls[k,j]<=tg:
                    half=t1; stp=e
                    if cs[k,j]<s5v[k,j]: rest=1-cs[k,j]/e; break
                    continue
            else:
                if hs[k,j]>=stp: rest=1-stp/e; break
            if cs[k,j]<s5v[k,j]:
                rest=1-cs[k,j]/e
                if half is None: half=rest
                break
        if rest is None: rest=1-cs[k,j]/e; half=half if half is not None else rest
        out.append(dict(date=C.index[i],t1hit=half==t1,ret=0.5*half+0.5*rest-cost))
    return pd.DataFrame(out)
res=[]
for nm,sg in (('short all',liq&(C<s200)&(C<s50)&(C>s5)&(rsi2>95)&(rs<=0.3)),('short +Nifty<200',liq&(C<s200)&(C<s50)&(C>s5)&(rsi2>95)&(rs<=0.3)&(nreg<0).values[:,None])):
  for t1 in (0.01,0.015):
    R=runs(sg,t1,3.0); R['per']=np.where(R.date<'2024-07-01','IS','OOS')
    for p,x in R.groupby('per'):
        w=x.ret>0; res.append(dict(f=nm,T1=t1,per=p,n=len(x),T1_hit=round(100*x.t1hit.mean(),1),net_win=round(100*w.mean(),1),avg=round(100*x.ret.mean(),2),pf=round(x.ret[w].sum()/-x.ret[~w].sum(),2)))
print(pd.DataFrame(res).to_string(index=False))
