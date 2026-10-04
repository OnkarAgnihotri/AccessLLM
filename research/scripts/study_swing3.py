import pandas as pd, numpy as np, glob, os
exec(open('study_swing2.py').read().split('def sim')[0])   # reuse panel construction
COST=0.0025
body=(C-O); rng=(Hh-L).replace(0,np.nan)
hammer=((np.minimum(O,C)-L)>=2*body.abs())&((Hh-np.maximum(O,C))<=0.3*rng)
engulf=(C>O)&(C.shift()<O.shift())&(C>=O.shift())&(O<=C.shift())
sig=liq&(C>s200)&(C>s50)&(C<s5)&(rsi2<5)&(rs>=0.7)
ii,jj=np.where(sig.fillna(False).values)
cs,os_,hs,ls,s5v,at=C.values,O.values,Hh.values,L.values,s5.values,atr.values
rows=[]
for i,j in zip(ii,jj):
    if i+11>=len(C): continue
    e=os_[i+1,j]
    # exit close>sma5 max10 no stop
    for k in range(i+1,i+11):
        if cs[k,j]>s5v[k,j]: break
    ret=cs[k,j]/e-1-COST
    mfe=[(hs[i+1:i+1+h,j].max()/e-1) for h in (1,3,5)]
    # touch +x% before close<entry-2ATR within 5 days
    def touch(x,stop_atr=2.0):
        stp=e-stop_atr*at[i,j]; tg=e*(1+x)
        for k2 in range(i+1,i+6):
            if ls[k2,j]<=stp: return 0
            if hs[k2,j]>=tg: return 1
        return 0
    rows.append(dict(date=C.index[i],sym=C.columns[j],ret=ret,hold=k-i,hammer=hammer.iat[i,j],engulf=engulf.iat[i,j],
        nreg=nreg.iat[i],gapdn=os_[i+1,j]<ls[i,j],t05=touch(.005),t1=touch(.01),t15=touch(.015),t2=touch(.02),t3=touch(.03),mfe1=mfe[0],mfe3=mfe[1],mfe5=mfe[2]))
R=pd.DataFrame(rows); R['per']=np.where(R.date<'2024-07-01','IS','OOS'); R.to_pickle('leaders.pkl')
print('signals',len(R))
print('P(touch +x% within 5 days before -2ATR stop):'); print((R.groupby('per')[['t05','t1','t15','t2','t3']].mean()*100).round(1))
g=lambda x: pd.Series(dict(n=len(x),win=100*(x.ret>0).mean(),avg=100*x.ret.mean()))
print('candles on signal day:'); 
for c in ('hammer','engulf','gapdn'): print(c); print(R.groupby([c,'per']).apply(g).round(2).unstack())
