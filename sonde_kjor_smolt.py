# ---------------------------------------------------------------------------
# sonde_kjor_smolt: datagrunnlag for et tilbudsflagg for norsk laks.
#
# Frodes bestilling 07.10.2026. DATASONDE: den ser IKKE paa papirene eller
# lakseprisen framover. Formaalet er aa vite om dataene finnes, hvor langt de
# gaar, og om utsett faktisk varsler slakt, foer et flagg defineres og
# registreres som Challenger. Ingenting paa dashbordet endres.
#
# KILDE: Fiskeridirektoratets biomassestatistikk per fylke, maanedlig fra
# 2005, oppdateres den 20. i hver maaned
# (register.fiskeridir.no/biomassestatistikk/BIOSTAT-LAKS-FLK/biostat-total-flk.csv).
# Bare arten LAKS, summert over fylker og utsettsaar til Norge.
#
# SERIENE:
#   utsett    smolt satt ut (stk), sum siste 12 mnd, endring fra aaret foer
#   slakt     uttak (kg), sum siste 12 mnd, endring fra aaret foer
#   biomasse  staaende biomasse ved maanedsslutt, endring fra aaret foer
#   doed      doedfisk i prosent av beholdningen, siste 12 mnd
#
# KRITERIER, satt foer kjoering:
#   K1  minst 15 aar sammenhengende maanedsdata for utsett og slakt.
#   K2  mekanismen: utsett varsler slakt. Korrelasjon mellom endringen i
#       utsett (12 mnd) og endringen i slakt (12 mnd) L maaneder senere, for
#       L = 12, 18 og 24 (tre forsinkelser, satt foer kjoering). Holder hvis
#       den hoeyeste av de tre er minst 0,30. Ellers varsler utsett ikke
#       tilbudet godt nok til aa bygge et flagg paa.
#   K3  ferskhet: siste maaned i filen hoeyst to maaneder gammel.
# Sonden viser ogsaa hvor ofte et kandidatflagg ville ha slaatt til (bare
# datoer, ingen utfall): utsett 12 mnd lavere enn aaret foer, alene og
# sammen med margin-A minst 80 fra laksesonden (sonder/laks.csv).
# ---------------------------------------------------------------------------

import io, time
import numpy as np
import pandas as pd
import requests

URL = "https://register.fiskeridir.no/biomassestatistikk/BIOSTAT-LAKS-FLK/biostat-total-flk.csv"
FORSINKELSER = [12, 18, 24]
PAUSE = 12

print("1. DATA\n")
for i in range(3):
    try:
        r = requests.get(URL, headers={"User-Agent": "Syklusbordet"}, timeout=120)
        break
    except requests.RequestException:
        time.sleep(4 * (i + 1))
tekst = r.content.decode("utf-8-sig", errors="replace")
d = pd.read_csv(io.StringIO(tekst), sep=";")
d.columns = [c.strip() for c in d.columns]
print(f"   HTTP {r.status_code}, {len(r.content) / 1e6:.1f} MB, {len(d):,} rader, kolonner: {', '.join(d.columns[:12])} ...")
d = d[d["ARTSID"].str.upper() == "LAKS"]
d["mnd"] = pd.PeriodIndex(pd.to_datetime(dict(year=d["ÅR"], month=d["MÅNED_KODE"], day=1)), freq="M")
num = ["BEHFISK_STK", "BIOMASSE_KG", "UTSETT_SMOLT_STK", "UTTAK_KG", "DØDFISK_STK"]
for c in num:
    d[c] = pd.to_numeric(d[c].astype(str).str.replace(",", "."), errors="coerce")
N = d.groupby("mnd")[num].sum().sort_index()
N = N.reindex(pd.period_range(N.index[0], N.index[-1], freq="M"))
print(f"   laks, Norge: {N.index[0]} til {N.index[-1]}, {N.notna().all(axis=1).sum()} hele maaneder, "
      f"fylker: {d['FYLKE'].nunique()}")

U12 = N["UTSETT_SMOLT_STK"].rolling(12).sum()
H12 = N["UTTAK_KG"].rolling(12).sum()
dU = 100 * (U12 / U12.shift(12) - 1)
dH = 100 * (H12 / H12.shift(12) - 1)
dB = 100 * (N["BIOMASSE_KG"] / N["BIOMASSE_KG"].shift(12) - 1)
doed = 100 * N["DØDFISK_STK"].rolling(12).sum() / N["BEHFISK_STK"].rolling(12).mean()

print("\n   Per aar (desember): utsett mill. stk, slakt 1000 tonn, endring i %, doedfisk % av beholdning")
print(f"   {'aar':>5s} {'utsett':>8s} {'endr':>6s} {'slakt':>8s} {'endr':>6s} {'biomasse':>9s} {'endr':>6s} {'doed':>6s}")
for t in [p for p in N.index if p.month == 12] + [N.index[-1]]:
    f = lambda x, fmt: "" if not np.isfinite(x) else format(x, fmt)
    print(f"   {str(t):>7s} {f(U12[t] / 1e6, '8.0f')} {f(dU[t], '+6.1f')} {f(H12[t] / 1e6, '8.0f')} {f(dH[t], '+6.1f')} "
          f"{f(N['BIOMASSE_KG'][t] / 1e6, '9.0f')} {f(dB[t], '+6.1f')} {f(doed[t], '6.1f')}")

print("\n\n2. KRITERIENE\n")
hele = N[["UTSETT_SMOLT_STK", "UTTAK_KG"]].dropna()
aar = (hele.index[-1] - hele.index[0]).n / 12
k1 = aar >= 15
print(f"   K1 sammenhengende data: {aar:.1f} aar (krav 15) -> {'HOLDER' if k1 else 'HOLDER IKKE'}")

print("   K2 utsett varsler slakt:")
korr = {}
for L in FORSINKELSER:
    x = pd.concat([dU, dH.shift(-L)], axis=1).dropna()
    korr[L] = (float(x.iloc[:, 0].corr(x.iloc[:, 1])), len(x))
    print(f"      L = {L:2d} mnd: korrelasjon {korr[L][0]:+.2f} (n {korr[L][1]}, overlappende maaneder)")
beste = max(korr, key=lambda L: korr[L][0])
k2 = korr[beste][0] >= 0.30
print(f"   K2 hoeyeste {korr[beste][0]:+.2f} ved L = {beste} (krav 0,30) -> {'HOLDER' if k2 else 'HOLDER IKKE'}")
print("      (med overlappende 12-maanedersendringer er antall uavhengige observasjoner rundt "
      f"{korr[beste][1] // 12}; korrelasjonen er beskrivende)")

alder = (pd.Period(pd.Timestamp.today(), "M") - N.index[-1]).n
k3 = alder <= 2
print(f"   K3 ferskhet: siste maaned {N.index[-1]}, {alder} mnd gammel (krav hoeyst 2) -> {'HOLDER' if k3 else 'HOLDER IKKE'}")

print("\n\n3. HVOR OFTE ET KANDIDATFLAGG VILLE SLAATT TIL (bare datoer, ingen utfall)\n")
def innslag(sig):
    ut, siste = [], None
    for t, v in sig.dropna().items():
        if v and (siste is None or (t - siste).n > PAUSE):
            ut.append(t)
        if v:
            siste = t
    return ut
s1 = dU < 0
print(f"   utsett lavere enn aaret foer: {100 * s1[dU.notna()].mean():.0f} % av maanedene, "
      f"nye episoder: {', '.join(str(t) for t in innslag(s1))}")
try:
    L_ = pd.read_csv("sonder/laks.csv", index_col=0)
    L_.index = pd.PeriodIndex(L_.index, freq="M")
    am = L_["A_margin"].reindex(dU.index)
    s2 = (dU < 0) & (am >= 80)
    gyldig = dU.notna() & am.notna()
    print(f"   og margin-A minst 80:         {100 * s2[gyldig].mean():.0f} % av maanedene, "
          f"nye episoder: {', '.join(str(t) for t in innslag(s2.where(gyldig))) or 'ingen'}")
except Exception as e:
    print(f"   margin-A ikke lest: {type(e).__name__}")

print("\n\n4. I DAG\n")
t = N.index[-1]
print(f"   {t}: utsett siste 12 mnd {U12[t] / 1e6:.0f} mill. stk ({dU[t]:+.1f} %), slakt {H12[t] / 1e6:.0f} tusen tonn "
      f"({dH[t]:+.1f} %), biomasse {N['BIOMASSE_KG'][t] / 1e6:.0f} tusen tonn ({dB[t]:+.1f} %), doedfisk {doed[t]:.1f} %")
print(f"\n   Oppsummering: K1 {k1}, K2 {k2}, K3 {k3}")
