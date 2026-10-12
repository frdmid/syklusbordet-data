# ---------------------------------------------------------------------------
# sonde_kjor_aluminium_tilbud: er primaerproduksjonen av aluminium utenfor
# Kina et brukbart tilbudsmaal (B) for aluminium? (Frodes bestilling 12.10.2026)
#
# Bakgrunn: sonde_kjor_b_mekanisme viste at dagens B for aluminium
# (capex/avskrivninger hos AA, CENX, KALU) ikke varsler produksjonen. Tilbudet
# bestemmes av smelteverkene. Kina (rundt 60 %) er politisk tak-styrt (rundt
# 45 mill. tonn), saa det er smelteverkene utenfor Kina som svarer paa pris,
# ved aa stenge og starte opp igjen. MEKANISMEN testes, ikke papirene eller
# prisen framover. Ingenting paa dashbordet endres.
#
# DATA
#   IAI primaerproduksjon per region og maaned 1999-01 til 2026-08, lastet ned
#   som CSV fra international-aluminium.org 12.10.2026 (Frodes godkjenning),
#   lagret i data_manuelt/iai_primaeraluminium_2026-10-12.csv.
#   Utenfor Kina = sum av de rapporterte regionene unntatt China (Estimated) og
#   Estimated Unreported to IAI. Europa er delt i to fram til 2024 og samlet
#   fra 2025; summen haandterer begge. GCC ligger i Asia (ex China) foer 2010.
#   Pris: aluminium real fra serier/priser_mnd.csv (samme som bordet).
#
# TEST 1 (avgjoer): svarer produksjonen utenfor Kina paa prisen?
#   Korrelasjon mellom prisendringen over 12 mnd (log) ved t og vekst i
#   produksjonen utenfor Kina over 12 mnd ved t+L, L = 6, 12, 18 (forventet
#   positiv: lav pris, stenging, lavere vekst). Holder hvis hoeyeste er minst
#   0,30 OG kontrollen uten overlapp (desember, pris aar t mot produksjon aar
#   t+1) har samme fortegn. Samme krav som for gass og olje.
# BESKRIVENDE (ingen krav): samme test for Kina (forventet svakere), og
#   Kinas produksjon siste 12 mnd mot taket paa 45 mill. tonn.
# BESLUTNING: holder Test 1, er fallet i produksjonen utenfor Kina et
# tilbudsmaal som kan defineres som B for aluminium og registreres som
# Challenger (Frode avgjoer). Holder den ikke, svarer ikke tilbudet utenfor
# Kina paa prisen godt nok til aa bygge et flagg paa.
# ---------------------------------------------------------------------------

import numpy as np
import pandas as pd

# Flyttet 12.10.2026: IAIs vilkaar tillater bare personlig bruk, ikke
# videreformidling, og repoet er offentlig. Fila ligger lokalt hos Frode i
# data_privat/ (ignorert av git) og skal aldri inn i repoet.
FIL = "data_privat/iai_primaeraluminium_2026-10-12.csv"
L_MND = [6, 12, 18]
TAK = 45_000            # tusen tonn per aar

d = pd.read_csv(FIL, sep=";")
d["mnd"] = pd.PeriodIndex(pd.to_datetime(d["Period from"]), freq="M")
d = d.set_index("mnd").sort_index()
num = lambda c: pd.to_numeric(d[c].astype(str).str.replace("*", "", regex=False).str.strip(), errors="coerce")
reg = ["Africa", "North America", "South America", "Asia (ex China)", "Western & Central Europe",
       "Russia & Eastern Europe", "Europe (inc Russia)", "Oceania", "Gulf Cooperation Council"]
UTE = sum(num(c).fillna(0) for c in reg)
KINA = num("China (Estimated)")
print("1. DATA\n")
print(f"   IAI {d.index[0]} til {d.index[-1]}, {len(d)} maaneder")
print(f"   utenfor Kina siste 12 mnd: {UTE.iloc[-12:].sum() / 1000:.1f} mill. tonn; Kina {KINA.iloc[-12:].sum() / 1000:.1f}; "
      f"Kinas andel {100 * KINA.iloc[-12:].sum() / (KINA.iloc[-12:].sum() + UTE.iloc[-12:].sum()):.0f} %")

pm = pd.read_csv("serier/priser_mnd.csv")
pm = pm[pm.segment == "aluminium"]
PRIS = pd.Series(pm.real.astype(float).values, index=pd.PeriodIndex(pm.t, freq="M"))
dp = 100 * np.log(PRIS / PRIS.shift(12))


def vekst(s):
    s12 = s.rolling(12).sum()
    return 100 * np.log(s12 / s12.shift(12))


def aarlig(s):
    a = s.groupby(lambda p: p.year).agg(["sum", "count"])
    a = a[a["count"] == 12]["sum"]
    return 100 * np.log(a / a.shift(1))


def test(navn, s, avgjoer):
    v = vekst(s)
    res = {}
    for L in L_MND:
        x = pd.concat([dp, v.shift(-L)], axis=1).dropna()
        res[L] = (float(x.iloc[:, 0].corr(x.iloc[:, 1])), len(x))
        print(f"   {navn}: prisendring t mot produksjonsvekst t+{L}: {res[L][0]:+.2f} (n {res[L][1]}, overlappende)")
    pd_ = PRIS[[p for p in PRIS.index if p.month == 12]]; pd_.index = [p.year for p in pd_.index]
    pa = 100 * np.log(pd_ / pd_.shift(1))
    va = aarlig(s)
    dd = pd.DataFrame({"p": pa, "v": [va.get(a + 1, np.nan) for a in pa.index]}, index=pa.index).dropna()
    kd = float(dd.p.corr(dd.v))
    best = max(res, key=lambda L: res[L][0])
    ok = res[best][0] >= 0.30 and kd > 0
    print(f"   {navn}: uten overlapp (des aar t mot produksjon aar t+1): {kd:+.2f}, n {len(dd)}, "
          f"samme fortegn {100 * (np.sign(dd.p) == np.sign(dd.v)).mean():.0f} %")
    if avgjoer:
        print(f"   TEST 1: {res[best][0]:+.2f} ved L = {best} -> {'HOLDER' if ok else 'HOLDER IKKE'}")
    return ok

print("\n2. TEST 1: SVARER PRODUKSJONEN UTENFOR KINA PAA PRISEN?\n")
ok = test("utenfor Kina", UTE, True)
print("\n3. BESKRIVENDE\n")
test("Kina", KINA, False)
k12 = KINA.rolling(12).sum()
print(f"   Kina siste 12 mnd: {k12.iloc[-1] / 1000:.1f} mill. tonn, {100 * k12.iloc[-1] / TAK:.0f} % av taket paa 45")
v = vekst(UTE)
print(f"   utenfor Kina, vekst siste 12 mnd ({UTE.index[-1]}): {v.iloc[-1]:+.1f} log-%")
print("   aar med fall utenfor Kina (des mot des): " + ", ".join(
    f"{a} {x:+.1f} %" for a, x in aarlig(UTE).items() if x < 0))
print(f"\n   Oppsummering: Test 1 {ok}")
