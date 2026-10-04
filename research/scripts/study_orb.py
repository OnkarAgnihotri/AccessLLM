import pandas as pd, numpy as np, glob, os, sys
H="/home/user/AccessLLM/C:\\Users\\onkar\\Desktop\\Stock_data/1_H_TF"
TG=[0.5,0.75,1.0,1.5,2.0]
def load1h(f):
    d=pd.read_csv(f); d['Date']=pd.to_datetime(d.Date,utc=True).dt.tz_convert('Asia/Kolkata')
    d=d.dropna(subset=['Open','High','Low','Close']).set_index('Date'); d['day']=d.index.date; return d
nf=load1h('data/idx1h/^NSEI.csv')
nday=nf.groupby('day').agg(o=('Open','first'),c1=('Close','first'),c=('Close','last'))
nday['fh']=nday.c1/nday.o-1; nday['rest']=nday.c/nday.c1-1
trades=[]; days=[]
files=sorted(glob.glob(H+'/*.csv'))
for k,f in enumerate(files):
    s=os.path.basename(f)[:-4]
    fd=f'data/1d/{s}.csv'
    if not os.path.exists(fd): continue
    d1=pd.read_csv(fd,index_col=0,parse_dates=True).dropna()
    c=d1.Close; tr=pd.concat([d1.High-d1.Low,(d1.High-c.shift()).abs(),(d1.Low-c.shift()).abs()],axis=1).max(axis=1)
    dd=pd.DataFrame({'pc':c,'e20':c.ewm(span=20).mean(),'e50':c.ewm(span=50).mean(),'atr':tr.rolling(14).mean(),
                     'hi20':d1.High.rolling(20).max(),'lo20':d1.Low.rolling(20).min(),'turn':(c*d1.Volume).rolling(20).median()}).shift(1)  # known before today
    dd.index=dd.index.date
    h=load1h(f)
    if len(h)<500: continue
    g=[(day,x) for day,x in h.groupby('day') if len(x)>=6]
    v1=pd.Series({day:x.Volume.iloc[0] for day,x in g}); rv=v1/v1.rolling(20).mean().shift(1)
    for day,x in g:
        if day not in dd.index: continue
        r=dd.loc[day]
        if np.isnan(r.atr) or np.isnan(rv.get(day,np.nan)): continue
        O=x.Open.values;Hh=x.High.values;L=x.Low.values;C=x.Close.values
        orh,orl=Hh[0],L[0]
        base=dict(sym=s,day=day,gap=O[0]/r.pc-1,fh=C[0]/O[0]-1,rest=C[-1]/C[0]-1,rv=rv[day],
                  trend=1 if (r.pc>r.e20>r.e50) else (-1 if r.pc<r.e20<r.e50 else 0),
                  or_atr=(orh-orl)/r.atr,atr_pct=r.atr/r.pc,turn=r.turn,
                  nfh=nday.fh.get(day,np.nan),nrest=nday.rest.get(day,np.nan),
                  near20h=r.pc/r.hi20, near20l=r.pc/r.lo20)
        days.append(base)
        done=False
        for j in range(1,5):
            for dirn in (1,-1):
                if dirn==1 and C[j]>orh: 
                    stp_or=orl; stp_bar=L[j]
                elif dirn==-1 and C[j]<orl:
                    stp_or=orh; stp_bar=Hh[j]
                else: continue
                e=C[j]; t=dict(base,dir=dirn,j=j,entry=e)
                for sname,stp in (('or',stp_or),('bar',stp_bar),('mid',(orh+orl)/2)):
                    R=(e-stp)*dirn
                    if R<=0 or R/e<0.002: R=max(R,0.002*e)
                    t['R_'+sname]=R/e
                    stop=e-dirn*R
                    for tg in TG+[99]:
                        tgt=e+dirn*tg*R; out=None
                        for i in range(j+1,len(C)):
                            hit_s = (L[i]<=stop) if dirn==1 else (Hh[i]>=stop)
                            hit_t = (Hh[i]>=tgt) if dirn==1 else (L[i]<=tgt)
                            if hit_s: out=-1.0; break
                            if hit_t: out=tg; break
                        if out is None: out=(C[-1]-e)*dirn/R
                        t[f'{sname}_{tg}']=out
                trades.append(t); done=True; break
            if done: break
    if k%100==0: print(k,len(trades),flush=True)
pd.DataFrame(trades).to_pickle('orb_trades.pkl'); pd.DataFrame(days).to_pickle('days.pkl')
print('trades',len(trades),'days',len(days))
