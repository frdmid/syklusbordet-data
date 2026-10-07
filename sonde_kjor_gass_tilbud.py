# ---------------------------------------------------------------------------
# sonde_kjor_gass_tilbud: maaler B for gass tilbudet, og er produksjonsveksten
# et brukbart tilbudsmaal for Henry Hub?
#
# Frodes bestilling 07.10.2026, etter sonde_kjor_b_gass (K1 til K3 holdt, men
# B1 har ligget hoeyt siden 2015 fordi boomaarene dominerer historikken).
# Samme oppsett som biomassesonden for laks: MEKANISMEN testes, ikke
# papirene og ikke prisen framover. Ingenting paa dashbordet endres.
#
# DATA
#   B      forholdet investeringer/avskrivninger for gassprodusentene per aar,
#          hentet ved aa kjoere sonde_kjor_b_gass.py (samme selskaper, samme
#          vinduer, samme rettelser).
#   prod   EIA, U.S. Dry Natural Gas Production (N9070US2), maanedlig fra 1973,
#          historikksiden paa eia.gov (ingen konto eller noekkel).
#   pris   Henry Hub spot, maanedssnitt (datasets/natural-gas, som priser.py).
#
# TEST 1, B varsler tilbudet. Kjent mekanisme: mer boring gir mer produksjon
# 6 til 24 mnd senere. Korrelasjon mellom forholdet i aar t og
# produksjonsveksten i aar t+1 og t+2 (aarstall, ingen overlapp).
#   K1  hoeyeste av de to minst 0,30 (positiv). n er lite (rundt 15); tallet er
#       beskrivende og vises med n.
# TEST 2, produksjonen svarer paa prisen. Lav pris skal gi lavere vekst med
# etterslep. Korrelasjon mellom prisendringen over 12 mnd (log) ved maaned t
# og produksjonsveksten over 12 mnd ved t+L, L = 12, 18 og 24 mnd, fra 1997.
#   K2  hoeyeste minst 0,30. Kontroll uten overlapp: desember mot desember,
#       pris aar t mot produksjon aar t+1.
# BESLUTNING, satt foer kjoering:
#   K1 holder           B for gass maaler tilbudet og kan bli Challenger.
#   K1 holder ikke      B for gass bygges ikke.
#   K2 holder           produksjonsveksten kan brukes som tilbudsmaal (som
#                       biomassen for laks), og et flagg kan defineres og
#                       registreres som Challenger.
# Begge kan holde; da avgjoer Frode hvilken som brukes.
# NB: tilbudet i USA kommer ogsaa fra assosiert gass fra oljeboring (Permian),
# som gassprodusentenes investeringer ikke styrer. Det kan svekke K1.
# ---------------------------------------------------------------------------

import contextlib, io, re, runpy, time
import numpy as np
import pandas as pd
import requests

UA = {"User-Agent": "Syklusbordet frode@h-k.no"}
L_MND = [12, 18, 24]


def get(url):
    for i in range(4):
        try:
            r = requests.get(url, headers=UA, timeout=90)
            if r.status_code == 200:
                return r
        except requests.RequestException:
            pass
        time.sleep(2 ** (i + 1))
    raise RuntimeError(url)


print("1. DATA\n")
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    g = runpy.run_path("sonde_kjor_b_gass.py")
B = g["df"]
print(f"   B for gass fra sonde_kjor_b_gass: {B.index.min()} til {B.index.max()}, "
      f"siste forhold {B['forhold'].iloc[-1]:.2f}")

t = get("https://www.eia.gov/dnav/ng/hist/n9070us2m.htm").text
rader = re.findall(r"<td class='B4'>&nbsp;&nbsp;(\d{4})</td>(.*?)</tr>", t, re.S)
prod = {}
for aar, rest in rader:
    verdier = re.findall(r"<td class='B3'>([\d,]*)</td>", rest)
    for m, v in enumerate(verdier, 1):
        if v:
            prod[pd.Period(f"{aar}-{m:02d}", "M")] = float(v.replace(",", ""))
P = pd.Series(prod).sort_index()
print(f"   EIA toerrgass: {P.index[0]} til {P.index[-1]}, siste {P.iloc[-1] / 1e6:.2f} Tcf i maaneden")

h = pd.read_csv(io.StringIO(get("https://raw.githubusercontent.com/datasets/natural-gas/main/data/monthly.csv").text))
h.columns = [c.lower() for c in h.columns]
PRIS = pd.Series(h["price"].values, index=pd.PeriodIndex(pd.to_datetime(h["month"]), freq="M")).dropna()
PRIS = PRIS[~PRIS.index.duplicated(keep="last")].sort_index()
print(f"   Henry Hub: {PRIS.index[0]} til {PRIS.index[-1]}")

P12 = P.rolling(12).sum()
vekst_m = 100 * (P12 / P12.shift(12) - 1)                    # maanedlig, overlappende
aar_p = P.groupby(lambda p: p.year).agg(["sum", "count"])
aar_p = aar_p[aar_p["count"] == 12]["sum"]
vekst_a = 100 * (aar_p / aar_p.shift(1) - 1)                 # aarlig

print("\n   Aar: forhold (B), produksjonsvekst samme aar, aaret etter, to aar etter")
for a in B.index:
    f = lambda x: "" if not np.isfinite(x) else f"{x:+5.1f} %"
    print(f"   {a}: {B.loc[a, 'forhold']:5.2f}   {f(vekst_a.get(a, np.nan)):>8s} {f(vekst_a.get(a + 1, np.nan)):>8s} "
          f"{f(vekst_a.get(a + 2, np.nan)):>8s}")

print("\n\n2. TEST 1: B VARSLER TILBUDET (aarstall, ingen overlapp)\n")
res1 = {}
for k in (1, 2):
    d = pd.DataFrame({"b": B["forhold"], "v": [vekst_a.get(a + k, np.nan) for a in B.index]}, index=B.index).dropna()
    res1[k] = (float(d["b"].corr(d["v"])), len(d))
    print(f"   forhold aar t mot vekst aar t+{k}: korrelasjon {res1[k][0]:+.2f} (n {res1[k][1]})")
    if "B1" in B:
        d1 = pd.DataFrame({"b1": B["B1"], "v": [vekst_a.get(a + k, np.nan) for a in B.index]}, index=B.index).dropna()
        if len(d1) > 3:
            print(f"      (B1 mot vekst t+{k}: {d1['b1'].corr(d1['v']):+.2f}, n {len(d1)}; forventet negativ)")
best1 = max(res1, key=lambda k: res1[k][0])
k1 = res1[best1][0] >= 0.30
print(f"   K1 hoeyeste {res1[best1][0]:+.2f} ved t+{best1} (krav 0,30) -> {'HOLDER' if k1 else 'HOLDER IKKE'}")

print("\n\n3. TEST 2: PRODUKSJONEN SVARER PAA PRISEN\n")
dp = 100 * np.log(PRIS / PRIS.shift(12))
res2 = {}
for L in L_MND:
    d = pd.concat([dp, vekst_m.shift(-L)], axis=1).dropna()
    d = d[d.index >= pd.Period("1997-01", "M")]
    res2[L] = (float(d.iloc[:, 0].corr(d.iloc[:, 1])), len(d))
    print(f"   prisendring 12 mnd ved t mot produksjonsvekst ved t+{L}: korrelasjon {res2[L][0]:+.2f} (n {res2[L][1]}, overlappende)")
bestL = max(res2, key=lambda L: res2[L][0])
k2 = res2[bestL][0] >= 0.30
print(f"   K2 hoeyeste {res2[bestL][0]:+.2f} ved L = {bestL} (krav 0,30) -> {'HOLDER' if k2 else 'HOLDER IKKE'}")
des = PRIS[[p for p in PRIS.index if p.month == 12]]
des.index = [p.year for p in des.index]
dd = pd.DataFrame({"pris": 100 * np.log(des / des.shift(1)), "v": [vekst_a.get(a + 1, np.nan) for a in des.index]},
                  index=des.index).dropna()
dd = dd[dd.index >= 1997]
print(f"   kontroll uten overlapp (desember, pris aar t mot produksjon aar t+1): {dd['pris'].corr(dd['v']):+.2f}, "
      f"n {len(dd)}, samme fortegn {100 * (np.sign(dd['pris']) == np.sign(dd['v'])).mean():.0f} %")

print("\n\n4. I DAG\n")
s = P.index[-1]
print(f"   produksjon siste 12 mnd til {s}: {vekst_m[s]:+.1f} % fra aaret foer; Henry Hub {PRIS.index[-1]} "
      f"{PRIS.iloc[-1]:.2f} USD, {dp.iloc[-1]:+.0f} log-% over 12 mnd")
print(f"\n   Oppsummering: K1 {k1} (B varsler tilbudet), K2 {k2} (produksjonen svarer paa prisen)")
