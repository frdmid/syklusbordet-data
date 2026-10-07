# ---------------------------------------------------------------------------
# sonde_kjor_biomasse: varsler staaende biomasse slakten for norsk laks?
#
# Frodes bestilling 07.10.2026, etter at sonde_kjor_smolt viste at utsett av
# smolt varsler slakt for svakt (K2 +0,22). Biomassen i sjoeen er fisken som
# faktisk skal slaktes, saa ledetiden er kortere. DATASONDE: ser IKKE paa
# papirene eller prisen framover. Ingenting paa dashbordet endres.
#
# NB: aarstallene for biomasse og slakt er alt sett i utskriften fra
# sonde_kjor_smolt. Testen er derfor ikke blind. Kravet er det samme som for
# smolt, og forsinkelsene er satt foer denne kjoeringen.
#
# KILDE: som sonde_kjor_smolt (Fiskeridirektoratets biomassestatistikk, laks,
# summert til Norge, maanedlig fra 2005).
#
# KRITERIER, satt foer kjoering:
#   K2  korrelasjon mellom endringen i biomasse fra aaret foer (maanedsslutt,
#       snitt siste 3 mnd for aa dempe sesongen) og endringen i slakt (sum 12
#       mnd) L maaneder senere, L = 6, 9 og 12. Holder hvis den hoeyeste er
#       minst 0,30.
#   K2b strengere kontroll uten overlapp: bare ett punkt per aar (biomassen i
#       desember mot slakten kalenderaaret etter). Rapporteres med n.
# Hvis K2 holder, er biomasse et brukbart tilbudsmaal, og et flagg kan
# defineres og registreres som Challenger. Det testes ikke her.
# ---------------------------------------------------------------------------

import io, time
import numpy as np
import pandas as pd
import requests

URL = "https://register.fiskeridir.no/biomassestatistikk/BIOSTAT-LAKS-FLK/biostat-total-flk.csv"
FORSINKELSER = [6, 9, 12]

for i in range(3):
    try:
        r = requests.get(URL, headers={"User-Agent": "Syklusbordet"}, timeout=120)
        break
    except requests.RequestException:
        time.sleep(4 * (i + 1))
d = pd.read_csv(io.StringIO(r.content.decode("utf-8-sig", errors="replace")), sep=";")
d = d[d["ARTSID"].str.upper() == "LAKS"]
d["mnd"] = pd.PeriodIndex(pd.to_datetime(dict(year=d["ÅR"], month=d["MÅNED_KODE"], day=1)), freq="M")
for c in ("BIOMASSE_KG", "UTTAK_KG"):
    d[c] = pd.to_numeric(d[c].astype(str).str.replace(",", "."), errors="coerce")
N = d.groupby("mnd")[["BIOMASSE_KG", "UTTAK_KG"]].sum().sort_index()
N = N.reindex(pd.period_range(N.index[0], N.index[-1], freq="M"))
print(f"1. DATA\n\n   laks, Norge: {N.index[0]} til {N.index[-1]}\n")

B3 = N["BIOMASSE_KG"].rolling(3).mean()
dB = 100 * (B3 / B3.shift(12) - 1)
H12 = N["UTTAK_KG"].rolling(12).sum()
dH = 100 * (H12 / H12.shift(12) - 1)

print("2. K2: BIOMASSE VARSLER SLAKT (maanedlig, overlappende)\n")
korr = {}
for L in FORSINKELSER:
    x = pd.concat([dB, dH.shift(-L)], axis=1).dropna()
    korr[L] = (float(x.iloc[:, 0].corr(x.iloc[:, 1])), len(x))
    print(f"   L = {L:2d} mnd: korrelasjon {korr[L][0]:+.2f} (n {korr[L][1]})")
beste = max(korr, key=lambda L: korr[L][0])
k2 = korr[beste][0] >= 0.30
print(f"   K2 hoeyeste {korr[beste][0]:+.2f} ved L = {beste} (krav 0,30) -> {'HOLDER' if k2 else 'HOLDER IKKE'}")

print("\n3. K2b: ETT PUNKT PER AAR (biomasse desember mot slakt aaret etter)\n")
des = N["BIOMASSE_KG"][[p for p in N.index if p.month == 12]]
des.index = [p.year for p in des.index]
aar_slakt = N["UTTAK_KG"].groupby(lambda p: p.year).agg(["sum", "count"])
aar_slakt = aar_slakt[aar_slakt["count"] == 12]["sum"]
rader = []
for a in des.index:
    if a - 1 in des.index and a + 1 in aar_slakt.index and a in aar_slakt.index:
        rader.append({"aar": a, "dB": 100 * (des[a] / des[a - 1] - 1), "dH_neste": 100 * (aar_slakt[a + 1] / aar_slakt[a] - 1)})
A = pd.DataFrame(rader).set_index("aar")
for a, rr in A.iterrows():
    print(f"   {a}: biomasse des {rr['dB']:+5.1f} %  ->  slakt {a + 1} {rr['dH_neste']:+5.1f} %")
kb = float(A["dB"].corr(A["dH_neste"]))
retning = float((np.sign(A["dB"]) == np.sign(A["dH_neste"])).mean())
print(f"   K2b korrelasjon {kb:+.2f}, n {len(A)}, samme fortegn i {100 * retning:.0f} % av aarene")

print("\n4. I DAG\n")
t = N.index[-1]
print(f"   {t}: biomasse (snitt 3 mnd) {B3[t] / 1e6:.0f} tusen tonn, {dB[t]:+.1f} % fra aaret foer; "
      f"slakt siste 12 mnd {dH[t]:+.1f} %")
print(f"\n   Oppsummering: K2 {k2} (beste L {beste}), K2b {kb:+.2f} (n {len(A)})")
