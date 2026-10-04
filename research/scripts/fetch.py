import json, sys, yfinance as yf, pandas as pd, os
interval, period, out = sys.argv[1], sys.argv[2], sys.argv[3]
m=json.load(open('/home/user/AccessLLM/all_profile_metadata.json'))
tk=sorted(m)+['^NSEI','^NSEBANK','^CNXIT','^CNXAUTO','^CNXPHARMA','^CNXFMCG','^CNXMETAL','^CNXREALTY','^CNXENERGY','^INDIAVIX']
for i in range(0,len(tk),60):
    b=tk[i:i+60]
    d=yf.download(b,period=period,interval=interval,auto_adjust=True,progress=False,group_by='ticker',threads=True)
    for t in b:
        try:
            x=d[t].dropna(how='all')
            if len(x)<5: continue
            x.index.name='Date'
            x[['Open','High','Low','Close','Volume']].to_csv(f"{out}/{t.replace('.NS','')}.csv")
        except Exception as e: pass
    print(i, flush=True)
