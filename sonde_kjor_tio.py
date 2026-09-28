# ---------------------------------------------------------------------------
# sonde_kjor_tio: holder jernmalmterminen hos Yahoo maal?
#
# Fra 26.09.2026 henter kurve_innhent.py jernmalmkurven fra Yahoo (CME Iron
# Ore 62% Fe, CFR China, TSI, som TIO<kode><aar>.NYM). Denne sonden sjekker tre
# ting foer tallet leses som annet enn kontekst:
#   1. Hvilke maanedskontrakter som svarer, med siste handelsdag og volum.
#      En kontrakt uten handel siste ti dager tas ikke med i kurven.
#   2. Kontinuerlig front (TIO=F): hvor langt tilbake den gaar.
#   3. Samme vare? Maanedssnittet av TIO=F mot Verdensbankens "Iron ore, cfr
#      spot" for de maanedene begge finnes. Avviket boer vaere lite og uten
#      trend. Er det stort, maaler de to ikke det samme.
# Sonden endrer ingenting.
# ---------------------------------------------------------------------------

import datetime as dt
import io, re, time
import numpy as np
import pandas as pd
import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
KODE = "FGHJKMNQUVXZ"


def chart(sym, **par):
    r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}", params=par,
                     headers=UA, timeout=30)
    if r.status_code != 200:
        return None
    try:
        return r.json()["chart"]["result"][0]
    except Exception:
        return None


print("1. Maanedskontrakter, siste 10 dager\n")
idag = dt.date.today()
y, m = idag.year, idag.month
print(f"   {'kontrakt':14} {'siste':>8} {'dato':>11} {'volum 10d':>10}  med i kurven")
for i in range(16):
    sym = f"TIO{KODE[m - 1]}{y % 100:02d}.NYM"
    res = chart(sym, range="10d", interval="1d")
    if res and res.get("timestamp"):
        q = res["indicators"]["quote"][0]
        par = [(t, c, v) for t, c, v in zip(res["timestamp"], q["close"], q.get("volume") or [None] * len(q["close"]))
               if c is not None]
        if par:
            t, c, _ = par[-1]
            vol = sum(v or 0 for _, _, v in par)
            print(f"   {sym:14} {c:8.2f} {dt.datetime.utcfromtimestamp(t):%Y-%m-%d} {vol:10.0f}  {'ja' if i > 0 else 'nei, loepende maaned'}")
        else:
            print(f"   {sym:14} ingen handel siste 10 dager")
    else:
        print(f"   {sym:14} svarer ikke")
    m += 1
    if m > 12:
        m, y = 1, y + 1
    time.sleep(0.2)

print("\n2. Kontinuerlig front TIO=F\n")
res = chart("TIO=F", range="max", interval="1d")
front = None
if res and res.get("timestamp"):
    front = pd.Series(res["indicators"]["quote"][0]["close"],
                      index=pd.to_datetime(res["timestamp"], unit="s")).dropna()
    print(f"   {front.index[0]:%Y-%m-%d} til {front.index[-1]:%Y-%m-%d}, {len(front)} dager, siste {front.iloc[-1]:.2f}")
else:
    print("   svarer ikke")

print("\n3. Maanedssnitt TIO=F mot Verdensbanken (Iron ore, cfr spot)\n")
try:
    html = requests.get("https://www.worldbank.org/en/research/commodity-markets", headers=UA, timeout=40).text
    kand = [u if u.startswith("http") else "https://www.worldbank.org" + u
            for u in re.findall(r'https?://[^"\']*?CMO[^"\']*?Monthly[^"\']*?\.xlsx', html)]
except Exception:
    kand = []
kand.append("https://thedocs.worldbank.org/en/doc/18675f1d1639c7a34d463f59263ba0a2-0050012025/"
            "related/CMO-Historical-Data-Monthly.xlsx")
ps = None
for u in dict.fromkeys(kand):
    try:
        raw = requests.get(u, headers=UA, timeout=120).content
        for skip in (4, 5, 6):
            df = pd.read_excel(io.BytesIO(raw), sheet_name="Monthly Prices", skiprows=skip)
            df = df.rename(columns={df.columns[0]: "t"})
            mm = df[df["t"].astype(str).str.match(r"^\d{4}M\d{1,2}$", na=False)].copy()
            if len(mm) > 100:
                mm["t"] = pd.PeriodIndex(mm["t"].astype(str).str.replace("M", "-", regex=False), freq="M")
                ps = mm.set_index("t").apply(pd.to_numeric, errors="coerce")
                break
        if ps is not None:
            break
    except Exception:
        pass
if ps is None or front is None:
    print("   mangler en av seriene")
else:
    kol = next(c for c in ps.columns if str(c).lower().startswith("iron ore"))
    wb = ps[kol].dropna()
    fm = front.groupby(front.index.to_period("M")).mean()
    i = wb.index.intersection(fm.index)
    avv = (fm.reindex(i) / wb.reindex(i) - 1) * 100
    print(f"   {len(i)} felles maaneder. Avvik TIO=F mot Verdensbanken: median {avv.median():+.1f} %, "
          f"snitt absolutt {avv.abs().mean():.1f} %, stoerste {avv.abs().max():.1f} % ({avv.abs().idxmax()})")
    print(f"   korrelasjon i maanedsendringer: "
          f"{np.corrcoef(np.log(fm.reindex(i)).diff().dropna(), np.log(wb.reindex(i)).diff().dropna())[0, 1]:.3f}")
    for aar in sorted(set(p.year for p in i)):
        a = avv[[p for p in i if p.year == aar]]
        print(f"      {aar}: median {a.median():+5.1f} %  ({len(a)} mnd)")
    print("\n   siste seks maaneder:")
    for p in i[-6:]:
        print(f"      {p}  TIO=F {fm[p]:7.2f}   Verdensbanken {wb[p]:7.2f}   {avv[p]:+5.1f} %")
