# ---------------------------------------------------------------------------
# sonde_kjor_usdnok_samtidig: beveger USD/NOK seg SAMTIDIG med aksjefall, og
# hva gjorde kronen i flaggepisodene? (beskrivende tillegg til
# sonde_kjor_usdnok_regime, 03.11.2026, kjørt etter at den var lest)
# Leser Norges Banks USD/NOK fra usdnok.csv (lastes ned først) og handel.json.
# Ingen kriterier, ingen avgjørelse.
# ---------------------------------------------------------------------------
import io, json, time, sys
import numpy as np, pandas as pd, requests
open("usdnok.csv", "wb").write(requests.get("https://data.norges-bank.no/api/data/EXR/B.USD.NOK.SP?format=csv&startPeriod=1980&locale=en",
                                            headers={"User-Agent": "Syklusbordet"}, timeout=120).content)
UA={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
d=pd.read_csv("usdnok.csv",sep=";"); u=pd.Series(d.OBS_VALUE.values,index=pd.to_datetime(d.TIME_PERIOD))
um=u.resample("ME").last(); um.index=um.index.to_period("M"); lu=np.log(um)
r=requests.get("https://query1.finance.yahoo.com/v8/finance/chart/^GSPC",params={"period1":0,"period2":int(time.time()),"interval":"1d"},headers=UA,timeout=60).json()["chart"]["result"][0]
s=pd.Series(r["indicators"]["quote"][0]["close"],index=pd.to_datetime(r["timestamp"],unit="s")).dropna().resample("ME").last(); s.index=s.index.to_period("M"); ls=np.log(s)
du, ds = lu.diff(), ls.diff()
m=(du.index>=pd.Period("1993-01","M"))
x=pd.concat([du,ds],axis=1).dropna(); x=x[x.index>=pd.Period("1993-01","M")]; x.columns=["u","s"]
print("korrelasjon maanedlig USD/NOK mot S&P 500, 1993-2026:", round(x.u.corr(x.s),2))
for lo,hi in ((-1,-0.07),(-0.07,-0.03),(-0.03,0.03),(0.03,1)):
    g=x[(x.s>lo)&(x.s<=hi)]; print(f"  S&P {lo:+.2f} til {hi:+.2f}: n {len(g):3}  USD/NOK samme mnd snitt {100*g.u.mean():+5.1f} %")
print("10 verste S&P-maaneder og USD/NOK samme maaned:")
for t,v in x.s.nsmallest(10).items(): print(f"  {t}  S&P {100*v:+6.1f} %  USD/NOK {100*x.u[t]:+5.1f} %")
h=json.load(open("handel.json",encoding="utf-8"))
print("USD/NOK over flaggepisodene (inngang til +24 mnd):")
for p in h["portefolje"]["posisjoner"]:
    if p["variant"]!="alle": continue
    t=pd.Period(p["inngang"],"M")
    a=um.get(t); b=um.get(t+24); c=um.get(t+6)
    print(f"  {p['segment']:10} {p['inngang']}  USD/NOK {a:.2f}  +6 mnd {100*(c/a-1):+5.1f} %  +24 mnd {100*(b/a-1) if b else float('nan'):+5.1f} %  pct mot 10 aar {100*((um[t-119:t+1]<=a).mean()):3.0f}")
