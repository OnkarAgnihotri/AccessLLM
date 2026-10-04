import pandas as pd, numpy as np, glob, os
COST=0.0025
P={}
for f in glob.glob('data/1d/*.csv'):
    s=os.path.basename(f)[:-4]
    if s.startswith('^'): continue
    d=pd.read_csv(f,index_col=0,parse_dates=True).dropna()
    if len(d)>=400: P[s]=d
C=pd.DataFrame({s:d.Close for s,d in P.items()}); Hh=pd.DataFrame({s:d.High for s,d in P.items()}); L=pd.DataFrame({s:d.Low for s,d in P.items()})
O=pd.DataFrame({s:d.Open for s,d in P.items()}); V=pd.DataFrame({s:d.Volume for s,d in P.items()})
nifty=pd.read_csv('data/1d/^NSEI.csv',index_col=0,parse_dates=True).Close.reindex(C.index).ffill()
nreg=np.sign(nifty-nifty.rolling(200).mean())
turn=(C*V).rolling(20).median()
s5=C.rolling(5).mean(); s50=C.rolling(50).mean(); s200=C.rolling(200).mean()
dl=C.diff(); up=dl.clip(lower=0).ewm(alpha=.5).mean(); dn=(-dl.clip(upper=0)).ewm(alpha=.5).mean(); rsi2=100-100/(1+up/dn)
tr=pd.concat([Hh-L,(Hh-C.shift()).abs(),(L-C.shift()).abs()]).groupby(level=0).max(); atr=tr.rolling(14).mean()
rs=(C/C.shift(126)).rank(axis=1,pct=True)    # 6m relative strength percentile
rs3=(C/C.shift(63)).rank(axis=1,pct=True)
liq=turn>2e8
def sim(sig,dirn,exit_kind,stop_atr,maxh=10,name=''):
    out=[]
    cs=C.values;os_=O.values;hs=Hh.values;ls=L.values;s5v=s5.values;at=atr.values;idx=C.index
    ii,jj=np.where(sig.fillna(False).values)
    for i,j in zip(ii,jj):
        if i+1>=len(idx): continue
        e=os_[i+1,j]
        if np.isnan(e): continue
        stp=e-dirn*stop_atr*at[i,j] if stop_atr else None
        x=None
        for k in range(i+1,min(i+1+maxh,len(idx))):
            if stp is not None and ((dirn==1 and ls[k,j]<=stp) or (dirn==-1 and hs[k,j]>=stp)): x=stp;break
            if exit_kind=='sma5' and dirn*(cs[k,j]-s5v[k,j])>0: x=cs[k,j];break
            if exit_kind=='upclose' and dirn*(cs[k,j]-cs[k-1,j])>0: x=cs[k,j];break
        if x is None: k=min(i+maxh,len(idx)-1); x=cs[k,j]
        out.append((idx[i],C.columns[j],dirn*(x/e-1)-COST,k-i))
    R=pd.DataFrame(out,columns=['date','sym','ret','hold']); R['name']=name; return R
def sm(R):
    w=R.ret>0
    return pd.Series(dict(n=len(R),win=100*w.mean(),avg=100*R.ret.mean(),avgwin=100*R.ret[w].mean(),avgloss=100*R.ret[~w].mean(),pf=R.ret[w].sum()/-R.ret[~w].sum(),hold=R.hold.mean(),worst=100*R.ret.min()))
base_long=liq&(C>s200)&(C>s50)&(C<s5)
base_short=liq&(C<s200)&(C<s50)&(C>s5)
tests=[]
for thr in (10,5):
  for rsq in (0,0.7,0.85):
    for reg in (False,True):
        sl=base_long&(rsi2<thr)&(rs>=rsq)
        if reg: sl=sl&(nreg>0).values[:,None]
        ss=base_short&(rsi2>100-thr)&(rs<=1-rsq if rsq else True)
        if reg: ss=ss&(nreg<0).values[:,None]
        for ex,st in (('sma5',2.5),('upclose',None),('sma5',None)):
            tests.append(sim(sl,1,ex,st,name=f'L rsi<{thr} rs>={rsq} reg={reg} {ex} stop={st}'))
            tests.append(sim(ss,-1,ex,st,name=f'S rsi>{100-thr} rs<={1-rsq if rsq else 1} reg={reg} {ex} stop={st}'))
A=pd.concat(tests); A['per']=np.where(A.date<'2024-07-01','IS','OOS'); A.to_pickle('swing2.pkl')
t=A.groupby(['name','per']).apply(sm).round(2).unstack()
cols=[('n','IS'),('n','OOS'),('win','IS'),('win','OOS'),('avg','IS'),('avg','OOS'),('pf','IS'),('pf','OOS'),('avgwin','OOS'),('avgloss','OOS'),('worst','OOS'),('hold','OOS')]
pd.set_option('display.width',250); print(t[cols].to_string())
