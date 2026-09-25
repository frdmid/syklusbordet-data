# ---------------------------------------------------------------------------
# sonde_kjor_indikator: sammensatt timingindikator 0 til 100
#
# Reglene er satt 24.09.2026, foer timing- og kurvesonden var lest, og staar i
# statusnotatet (claude/syklusbordet-status.md, "Sammensatt timingindikator").
# Sonden endrer ingenting paa bordet.
#
# HVA INDIKATOREN ER
#   Regnes bare i maaneder der segmentet staar i bunnsone eller under oppsikt
#   (raa A >= 80). Svarer paa "er det tid naa", ikke "er det billig".
#   Komponenter, hver 0 til 100, punkt i tid:
#     nivaa  = snittet av A og detrendet A
#     trend  = 0, 50, 100 for Nei, Begynnende, Bekreftet (samme regel som feltet)
#     COT    = 100 minus forvalternes persentil mot tre aar (mest korte gir 100)
#     kurve  = 100 minus kurvepersentilen (mest backwardert gir 100)
#   Indikatoren er snittet av komponentene som er med. Faste like vekter.
#   Tallet er en rangering, ikke en sannsynlighet.
#
# TRE LAG
#   Lag 1, raavarene fra 1965: nivaa og trend. Rangkorrelasjon innen sonen
#     mellom indikatoren og realprisendringen 24 maaneder fram (mot segmentets
#     eget snitt; 12 maaneder rapporteres ved siden av). Null: felles
#     blokkbootstrap av alle segmentene, som i terskelsonden, med A, detrendet
#     A, trend, sone og utfall regnet paa nytt fra hver bane. 500 trekk.
#     Trend er med bare hvis den bedrer korrelasjonen mot nivaa alene med
#     p <= 0,05 (strammet fra 0,10 etter kalibrering, se under).
#   Lag 2, COT fra 2006 (6 segmenter, persentil fra 2009): bedrer COT lag 1 paa
#     maanedene der COT finnes? Null: COT-serien forskjoevet sirkulaert (minst
#     24 maaneder, samme forskyvning for alle segmenter). 1000 trekk.
#     Kalibreringen viste at denne testen er for villig (se under), saa lag 2
#     er bare beskrivende, og COT blir staaende som kontekstfelt uansett tall.
#   Lag 3, kurve: skulle vaere med hvis kurvesonden ga minst 36 maaneder
#     historikk for minst fire segmenter. Den gjorde det i antall (WTI, Henry
#     Hub, gull, kobber, aluminium), men historikken er gal: WTI leses +4,8 % i
#     april 2020, da kurven sto i ekstrem contango, og -1,5 til -3,0 % i
#     februar 2022, da den sto i dyp backwardation. Dagens tall stemmer med
#     markedet, de gamle gjoer ikke. Lag 3 kjoeres derfor ikke, og kurven blir
#     staaende som kontekstfelt. Avgjort 25.09.2026 ut fra datakvalitet, foer
#     noe utfall var regnet mot kurven.
#   Papirene 2011 til 2024: beskrivende. Oevre mot nedre halvdel av
#     indikatoren innen sonen, meravkastning mot universet over 24 maaneder.
#
# BESLUTNING, SATT FOER KJOERING (grensene justert etter kalibrering, foer
# sonden er kjoert paa ekte data)
#   Trend er med bare hvis den bedrer lag 1 med p <= 0,05. Indikatoren kommer
#   paa dashbordet bare hvis lag 1 gir p <= 0,03 og indikatoren har mer enn
#   nivaa (med bare nivaa er den det samme som A-skaarene bordet viser).
#
# KALIBRERING (kal_indikator.py, simulerte data uten sammenheng)
#   Lag 1, 58 paneler med 200 trekk hver. Andel p under grensen:
#     trendens bidrag   3,4 % ved 0,05, 13,8 % ved 0,10
#     indikatoren       1,7 % ved 0,03,  8,6 % ved 0,05
#     nivaa alene       1,7 % ved 0,05 (streng)
#   Opprinnelige grenser var 0,10 for trend og 0,05 for indikatoren. De ga
#   14 og 9 % falske funn, og er derfor strammet til 0,05 og 0,03.
#   Lag 2, 185 paneler med 400 trekk: 5,9 % under 0,01 og 11,4 % under 0,05.
#   Nullen er for smal: med COT fra 2009 og faa maaneder i sonen gir
#   forskyvningen for faa uavhengige utfall. Ingen grense gjoer testen
#   gyldig i halen, saa lag 2 er beskrivende.
# ---------------------------------------------------------------------------

import json, os, time, warnings
import numpy as np
import pandas as pd

import terskel_motor as M
import indikator_motor as I

warnings.filterwarnings("ignore")
rng = np.random.default_rng(20260925)
KALIBRERT = {"lag1_paneler": 58, "p_trend": {"0.05": 0.034, "0.10": 0.138},
             "p_indikator": {"0.03": 0.017, "0.05": 0.086}, "p_niva_0.05": 0.017,
             "lag2_paneler": 185, "p_cot": {"0.01": 0.059, "0.05": 0.114, "0.10": 0.135},
             "grenser": {"trend": 0.05, "indikator": 0.03, "cot": "beskrivende"}}
RES = {"kjort": time.strftime("%Y-%m-%d %H:%M:%S"), "kalibrering": KALIBRERT}
COT_SEG = ["brent", "wti", "henryhub", "gold", "kobber", "kakao"]
f3 = lambda v: "-" if v is None or not np.isfinite(v) else f"{v:+.3f}"
fp = lambda v: "-" if v is None or not np.isfinite(v) else f"{v:.3f}"

# ================================================================ 1. data
print("1. Data\n")
from raavare_hist import hent
REAL, _NOM, _CPI = hent()
SEGS = []
for sid, lr in sorted(REAL.items()):
    lr = lr.dropna()
    full = pd.period_range(lr.index[0], lr.index[-1], freq="M")
    if len(full) != len(lr):
        lr = lr.reindex(full).interpolate()
    SEGS.append(M.Segment(sid, lr.values, np.array([p.ordinal for p in lr.index])))
print(f"   {len(SEGS)} raavaresegmenter")

# COT-historikk, punkt i tid: for hver maanedsslutt regnes feltet med
# signaler.cot_fra_rader paa ukene som var publisert da, altsaa noyaktig
# samme regel som dashbordet.
from signaler import KONTRAKTER, hent_kontrakt, cot_fra_rader
COT = {}
for sid in COT_SEG:
    try:
        rader = sorted(hent_kontrakt(KONTRAKTER[sid]), key=lambda r: str(r.get("report_date_as_yyyy_mm_dd")))
        datoer = [str(r.get("report_date_as_yyyy_mm_dd"))[:10] for r in rader]
        seg = next(s for s in SEGS if s.sid == sid)
        c = np.full(len(seg.o), np.nan)
        for i, o in enumerate(seg.o):
            slutt = str(pd.Period(ordinal=int(o), freq="M").end_time.date())
            n = sum(1 for d in datoer if d <= slutt)
            if n < 156:          # tre aar med uker foer persentilen gir mening
                continue
            try:
                c[i] = 100 - cot_fra_rader(rader[:n], KONTRAKTER[sid])["mm_pctl_3aar"]
            except Exception:
                pass
        COT[sid] = c
        ok = np.isfinite(c)
        print(f"   COT {sid:9} {ok.sum()} maaneder fra {pd.Period(ordinal=int(seg.o[ok][0]), freq='M') if ok.any() else '-'}")
        time.sleep(1.5)
    except Exception as e:
        print(f"   COT {sid}: {type(e).__name__} {str(e)[:60]}")

# ================================================================ 2. lag 1
print("\n2. Lag 1: nivaa og trend, raavarene fra 1965\n")
t0 = time.time()
L1 = I.lag1_test(SEGS, rng, 500)
L1_12 = I.lag1(SEGS, 12)
print(f"   {L1['maaneder']} maaneder i sonen, {L1['segmenter']} segmenter ({time.time() - t0:.0f} s)")
print(f"   rangkorrelasjon mot 24 mnd fram:  nivaa alene {f3(L1['rho_niva'])} (p {fp(L1['p_niva'])}),"
      f"  nivaa og trend {f3(L1['rho_indikator'])} (p {fp(L1['p_indikator'])})")
print(f"   trendens bidrag {f3(L1['delta_trend'])}, p {fp(L1['p_trend'])}")
print(f"   12 mnd fram (beskrivende): nivaa {f3(L1_12['rho_niva'])}, nivaa og trend {f3(L1_12['rho_indikator'])}")
MED_TREND = np.isfinite(L1["p_trend"]) and L1["delta_trend"] > 0 and L1["p_trend"] <= 0.05
print(f"   trend {'er med' if MED_TREND else 'er ikke med'} (krav: bedrer med p <= 0,05)")
P_LAG1 = L1["p_indikator"] if MED_TREND else L1["p_niva"]
RES["lag1"] = {**L1, "12mnd": L1_12, "med_trend": bool(MED_TREND), "p_lag1": P_LAG1}

# ================================================================ 3. lag 2
print("\n3. Lag 2: COT fra 2009 (seks segmenter)\n")
L2 = I.lag2_test(SEGS, COT, MED_TREND, rng, 1000)
print(f"   {L2['maaneder']} maaneder i sonen med COT")
if np.isfinite(L2.get("delta_cot", np.nan)):
    print(f"   rangkorrelasjon uten COT {f3(L2['rho_uten'])}, med COT {f3(L2['rho_med'])}, "
          f"bidrag {f3(L2['delta_cot'])}, p {fp(L2['p_cot'])}")
MED_COT = False
print("   Beskrivende. Testen var for villig i kalibreringen, saa COT er ikke med og blir")
print("   staaende som kontekstfelt, uansett tallene over.")
RES["lag2"] = {**L2, "med_cot": bool(MED_COT)}

print("\n4. Lag 3: kurve")
print("   Kjoeres ikke. Den rekonstruerte kurvehistorikken er gal foer 2023 (se toppen).")
print("   Kurven blir staaende som kontekstfelt.")
RES["lag3"] = {"kjort": False, "grunn": "rekonstruert historikk gal foer 2023"}

# ================================================================ 5. papirene
print("\n5. Papirene 2011 til 2024 (beskrivende)\n")
try:
    uv = json.load(open("sonder/instrument_univers.json", encoding="utf-8"))["univers"]
    K = pd.read_csv("sonder/instrument_kurser.csv", index_col=0)
    K.index = pd.PeriodIndex(K.index, freq="M")
    lk = np.log(K)
    fwd = lk.shift(-24) - lk
    uni = fwd.mean(axis=1)
    mer = fwd.sub(uni, axis=0)
    per_seg = {}
    for s in SEGS:
        tr = I.trendskaar(s.lr)
        with np.errstate(invalid="ignore"):
            sone = np.isfinite(s.A) & (s.A >= I.SONE) & np.isfinite(tr)
        niva = (s.A + s.Ad) / 2
        ind = (niva + tr) / 2 if MED_TREND else niva
        if MED_COT and s.sid in COT:
            ind = np.where(np.isfinite(COT[s.sid]), ((niva + tr + COT[s.sid]) / 3) if MED_TREND
                           else ((niva + COT[s.sid]) / 2), ind)
        per_seg[s.sid] = pd.Series(np.where(sone, ind, np.nan),
                                   index=pd.PeriodIndex([pd.Period(ordinal=int(o), freq="M") for o in s.o]))
    rader = []
    for tk, u in uv.items():
        if tk not in mer.columns:
            continue
        for sid in u["segs"]:
            if sid not in per_seg:
                continue
            x = per_seg[sid].reindex(mer.index)
            m = mer[tk]
            for t in x.index[(x.notna()) & (m.notna()) & (x.index >= pd.Period("2011-09", "M"))]:
                rader.append((str(t), tk, float(x[t]), float(m[t])))
    df = pd.DataFrame(rader, columns=["t", "tk", "ind", "mer"])
    if len(df):
        med = df["ind"].median()
        hoy, lav = df[df["ind"] > med], df[df["ind"] <= med]
        f = lambda v: f"{100 * (np.exp(v) - 1):+.1f} %"
        print(f"   {len(df)} papirmaaneder i sonen, {df['t'].nunique()} kalendermaaneder, median indikator {med:.0f}")
        print(f"   oevre halvdel: meravkastning 24 mnd mot universet, median {f(hoy['mer'].median())}, snitt {f(hoy['mer'].mean())}")
        print(f"   nedre halvdel: median {f(lav['mer'].median())}, snitt {f(lav['mer'].mean())}")
        print(f"   rangkorrelasjon {I.spearman(df['ind'].values, df['mer'].values):+.3f} (beskrivende, maanedene overlapper)")
        RES["papirer"] = {"n": len(df), "median_ind": float(med), "hoy_median": float(hoy["mer"].median()),
                          "lav_median": float(lav["mer"].median())}
except Exception as e:
    print(f"   ikke tilgjengelig: {type(e).__name__} {str(e)[:60]}")

# ================================================================ 6. beslutning
print("\n6. Beslutning etter regelen satt foer kjoering\n")
komp = ["nivaa"] + (["trend"] if MED_TREND else []) + (["COT"] if MED_COT else [])
paa = np.isfinite(P_LAG1) and P_LAG1 <= 0.03
print(f"   komponenter: {', '.join(komp)}")
print(f"   lag 1 p = {fp(P_LAG1)}: " + ("indikatoren kommer paa dashbordet." if paa else
      "indikatoren kommer ikke paa dashbordet. Feltene blir staaende som kontekst."))
if komp == ["nivaa"]:
    print("   Med bare nivaa er indikatoren det samme som A-skaarene bordet allerede viser.")
RES["beslutning"] = {"komponenter": komp, "paa_dashbordet": bool(paa and komp != ["nivaa"])}

# dagens verdi for segmentene i sonen
print("\n   Dagens verdi der segmentet staar i sonen:")
for s in SEGS:
    if not (np.isfinite(s.A[-1]) and s.A[-1] >= I.SONE):
        continue
    tr = I.trendskaar(s.lr)[-1]
    niva = (s.A[-1] + s.Ad[-1]) / 2
    print(f"      {s.sid:10} nivaa {niva:5.1f}  trend {tr:5.0f}"
          + (f"  COT {COT[s.sid][-1]:5.1f}" if s.sid in COT and np.isfinite(COT[s.sid][-1]) else ""))

os.makedirs("sonder", exist_ok=True)
json.dump(RES, open("sonder/indikator.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
print("\n   lagret sonder/indikator.json")
print("\nSend hele utskriften tilbake.")
