# ---------------------------------------------------------------------------
# sonde_kjor_gass_rigger: kan boreaktiviteten (EIA) brukes som tilbudsmaal B
# for Henry Hub?
#
# Frodes bestilling 07.10.2026. Bakgrunn: sonde_kjor_gass_tilbud viste at
# verken gassprodusentenes investeringer (regnskap) eller prisen varsler
# gassproduksjonen i USA. Forklaringen var trolig assosiert gass fra
# oljeboring. Denne sonden maaler aktiviteten direkte. MEKANISMEN testes,
# ikke papirene og ikke prisen framover. Ingenting paa dashbordet endres.
# Tallene i kildene er ikke sett foer kjoering (bare strukturen).
#
# DATA (alt uten konto eller noekkel)
#   Rigger og DUC per basseng: EIA Drilling Productivity Report, arkiv
#   (dpr-data.xlsx 2007 til 2024, duc-data.xlsx 2014 til 2024), skjoetet med
#   STEO tabell 10a (STEO_m.xlsx, 2022 og senere). Overlappen 2022 til 2024
#   vises som kontroll. Fra 2022 brukes STEO. STEO har prognose: rigger brukes
#   til og med maaneden to foer prognosedatoen, broenner og DUC til og med
#   sju maaneder foer (EIA: siste seks maaneder broenndata er ufullstendige).
#   Produksjon: EIA toerrgass for hele USA (N9070US2), som forrige sonde.
#   Pris: Henry Hub maanedssnitt (datasets/natural-gas), bare beskrivende.
#
# MAAL x (ved maaned t) mot y = produksjonsvekst over 12 mnd ved t+L:
#   T1  rigger i gassbassengene (Appalachia + Haynesville), snitt 3 mnd,
#       endring fra aaret foer i log-%. L = 6, 12, 18. Forventet positiv.
#   T2  som T1, pluss Permian (assosiert gass). L = 6, 12, 18. Positiv.
#   T3  tapping av broennbanken i gassbassengene: komplettert minus boret
#       siste 12 mnd, i prosent av DUC aaret foer. L = 12, 18, 24. Forventet
#       negativ (tapping holder produksjonen oppe naa, men ikke senere).
#   Kontroll uten overlapp: desember mot desember, x aar t mot vekst aar t+1.
# KRITERIER, satt foer kjoering:
#   T1, T2  holder hvis hoeyeste korrelasjon er minst 0,30 OG kontrollen uten
#           overlapp har samme fortegn.
#   T3      holder hvis laveste korrelasjon er -0,30 eller lavere OG kontrollen
#           har samme fortegn.
# BESLUTNING: holder T1 eller T2, kan riggmaalet defineres som B for gass og
# registreres som Challenger (Frode avgjoer). Holder ingen, avsluttes B for
# gass. Beskrivende i tillegg: svarer riggene paa prisen (L = 3, 6, 9, 12)?
# ---------------------------------------------------------------------------

import io, re, time
import numpy as np
import pandas as pd
import requests

UA = {"User-Agent": "Syklusbordet frode@h-k.no"}
GASS = ["Appalachia", "Haynesville"]


def get(url):
    for i in range(4):
        try:
            r = requests.get(url, headers=UA, timeout=120)
            if r.status_code == 200:
                return r
        except requests.RequestException:
            pass
        time.sleep(2 ** (i + 1))
    raise RuntimeError(url)


def mnd(s):
    s = s.dropna()
    return s[~s.index.duplicated(keep="last")].sort_index()


print("1. DATA\n")
dpr = pd.read_excel(io.BytesIO(get("https://www.eia.gov/petroleum/drilling/xls/dpr-data.xlsx").content),
                    sheet_name=None, header=None)
RIG_DPR, PROD_DPR = {}, {}
for b in GASS + ["Permian"]:
    d = dpr[f"{b} Region"].iloc[2:]
    idx = pd.PeriodIndex(pd.to_datetime(d[0]), freq="M")
    RIG_DPR[b] = mnd(pd.Series(pd.to_numeric(d[1], errors="coerce").values, index=idx))
    PROD_DPR[b] = mnd(pd.Series(pd.to_numeric(d[7], errors="coerce").values, index=idx))
    print(f"   DPR {b:11s} rigger {RIG_DPR[b].index[0]} til {RIG_DPR[b].index[-1]}")

duc = pd.read_excel(io.BytesIO(get("https://www.eia.gov/petroleum/drilling/xls/duc-data.xlsx").content),
                    sheet_name="Data", header=None)
hode = duc.iloc[2].ffill()
DUC_A = {}
rad0 = next(i for i in range(len(duc)) if isinstance(duc.iloc[i, 0], (pd.Timestamp,)) or
            str(duc.iloc[i, 0])[:2] in ("20",))
didx = pd.PeriodIndex(pd.to_datetime(duc.iloc[rad0:, 0], errors="coerce"), freq="M")
for b in GASS:
    kol = [j for j in range(duc.shape[1]) if str(hode.iloc[j]).strip() == b]
    sub = {str(duc.iloc[3, j]).strip(): j for j in kol}
    DUC_A[b] = pd.DataFrame({k: pd.to_numeric(duc.iloc[rad0:, sub[k]], errors="coerce").values
                             for k in ("Drilled", "Completed", "DUC")}, index=didx).dropna(how="all")
    DUC_A[b] = DUC_A[b][~DUC_A[b].index.isna()]
    print(f"   DUC-arkiv {b:11s} {DUC_A[b].index[0]} til {DUC_A[b].index[-1]}")

steo = pd.read_excel(io.BytesIO(get("https://www.eia.gov/outlooks/steo/xls/STEO_m.xlsx").content),
                     sheet_name="10atab", header=None)
dato_tekst = str(steo.iloc[3, 0])
m = re.search(r"(\w+) (\d+), (\d{4})", dato_tekst)
prognose = pd.Period(pd.Timestamp(f"{m.group(1)} {m.group(2)} {m.group(3)}"), "M")
start = int(steo.iloc[2, 2])
kolonner = list(range(2, steo.shape[1]))
sidx = pd.period_range(f"{start}-01", periods=len(kolonner), freq="M")
KODE = {str(steo.iloc[i, 0]).strip(): i for i in range(len(steo))}
def steo_serie(kode, siste):
    v = pd.to_numeric(steo.iloc[KODE[kode], kolonner], errors="coerce").values
    s = pd.Series(v, index=sidx)
    return s[s.index <= siste].dropna()
RIG_SISTE, BRN_SISTE = prognose - 2, prognose - 7
print(f"   STEO {dato_tekst}: rigger til {RIG_SISTE}, broenner og DUC til {BRN_SISTE}")
SK = {"Appalachia": "AP", "Haynesville": "HA", "Permian": "PM"}
RIG_S = {b: steo_serie(f"RIGS{SK[b]}", RIG_SISTE) for b in SK}
DUC_S = {b: pd.DataFrame({"Drilled": steo_serie(f"NWD{SK[b]}", BRN_SISTE),
                          "Completed": steo_serie(f"NWC{SK[b]}", BRN_SISTE),
                          "DUC": steo_serie(f"DUCS{SK[b]}", BRN_SISTE)}) for b in GASS}

print("\n   Kontroll av skjoeten, overlapp 2022 til 2024 (snitt, DPR mot STEO):")
RIG = {}
for b in SK:
    f = RIG_DPR[b].index.intersection(RIG_S[b].index)
    if len(f):
        print(f"   rigger {b:11s} {RIG_DPR[b][f].mean():6.1f} mot {RIG_S[b][f].mean():6.1f}, n {len(f)}, "
              f"korrelasjon {RIG_DPR[b][f].corr(RIG_S[b][f]):.2f}")
    RIG[b] = mnd(pd.concat([RIG_DPR[b][RIG_DPR[b].index < pd.Period("2022-01", "M")], RIG_S[b]]))
DUCD = {}
for b in GASS:
    a, s = DUC_A[b], DUC_S[b]
    f = a.index.intersection(s.index)
    if len(f):
        print(f"   DUC    {b:11s} {a.loc[f, 'DUC'].mean():6.0f} mot {s.loc[f, 'DUC'].mean():6.0f}, n {len(f)}; "
              f"komplettert {a.loc[f, 'Completed'].mean():5.0f} mot {s.loc[f, 'Completed'].mean():5.0f}")
    DUCD[b] = pd.concat([a[a.index < pd.Period("2022-01", "M")], s]).sort_index()

t = get("https://www.eia.gov/dnav/ng/hist/n9070us2m.htm").text
prod = {}
for aar, rest in re.findall(r"<td class='B4'>&nbsp;&nbsp;(\d{4})</td>(.*?)</tr>", t, re.S):
    for mm, v in enumerate(re.findall(r"<td class='B3'>([\d,]*)</td>", rest), 1):
        if v:
            prod[pd.Period(f"{aar}-{mm:02d}", "M")] = float(v.replace(",", ""))
P = pd.Series(prod).sort_index()
P12 = P.rolling(12).sum()
VEKST = 100 * np.log(P12 / P12.shift(12))
aar_p = P.groupby(lambda p: p.year).agg(["sum", "count"])
aar_p = aar_p[aar_p["count"] == 12]["sum"]
VEKST_A = 100 * np.log(aar_p / aar_p.shift(1))
print(f"   EIA toerrgass {P.index[0]} til {P.index[-1]}")
h = pd.read_csv(io.StringIO(get("https://raw.githubusercontent.com/datasets/natural-gas/main/data/monthly.csv").text))
h.columns = [c.lower() for c in h.columns]
PRIS = mnd(pd.Series(h["price"].values, index=pd.PeriodIndex(pd.to_datetime(h["month"]), freq="M")))


def endring(rig):
    r3 = rig.rolling(3).mean()
    return 100 * np.log(r3 / r3.shift(12))

GR = sum(RIG[b] for b in GASS).dropna()
GPR = (GR + RIG["Permian"]).dropna()
X = {"T1": endring(GR), "T2": endring(GPR)}
c12 = sum(DUCD[b]["Completed"] for b in GASS).rolling(12).sum()
d12 = sum(DUCD[b]["Drilled"] for b in GASS).rolling(12).sum()
ducs = sum(DUCD[b]["DUC"] for b in GASS)
X["T3"] = (100 * (c12 - d12) / ducs.shift(12)).dropna()
LAG = {"T1": [6, 12, 18], "T2": [6, 12, 18], "T3": [12, 18, 24]}
NAVN = {"T1": "rigger i gassbassengene", "T2": "gassbassengene + Permian", "T3": "tapping av broennbanken"}

print("\n\n2. TESTENE (x ved t mot produksjonsvekst 12 mnd ved t+L)\n")
RES = {}
for k in ("T1", "T2", "T3"):
    x = X[k]
    print(f"   {k} {NAVN[k]} (x fra {x.index[0]} til {x.index[-1]})")
    r = {}
    for L in LAG[k]:
        d = pd.concat([x, VEKST.shift(-L)], axis=1).dropna()
        r[L] = float(d.iloc[:, 0].corr(d.iloc[:, 1]))
        print(f"      L = {L:2d}: {r[L]:+.2f} (n {len(d)}, overlappende)")
    xd = x[[p for p in x.index if p.month == 12]]
    xd.index = [p.year for p in xd.index]
    dd = pd.DataFrame({"x": xd, "v": [VEKST_A.get(a + 1, np.nan) for a in xd.index]}, index=xd.index).dropna()
    kd = float(dd["x"].corr(dd["v"])) if len(dd) > 3 else np.nan
    print(f"      uten overlapp (des aar t mot vekst aar t+1): {kd:+.2f}, n {len(dd)}")
    if k == "T3":
        best = min(r, key=r.get); ok = r[best] <= -0.30 and kd < 0
    else:
        best = max(r, key=r.get); ok = r[best] >= 0.30 and kd > 0
    RES[k] = ok
    print(f"      {k}: {r[best]:+.2f} ved L = {best} -> {'HOLDER' if ok else 'HOLDER IKKE'}\n")

print("3. BESKRIVENDE: SVARER RIGGENE PAA PRISEN?\n")
dp = 100 * np.log(PRIS / PRIS.shift(12))
for navn, x in (("gassbassengene", X["T1"]), ("gass + Permian", X["T2"])):
    print(f"   {navn}: " + ", ".join(
        f"L {L}: {pd.concat([dp, x.shift(-L)], axis=1).dropna().corr().iloc[0, 1]:+.2f}" for L in (3, 6, 9, 12)))

print("\n\n4. I DAG\n")
for k in X:
    print(f"   {NAVN[k]:26s} {X[k].index[-1]}: {X[k].iloc[-1]:+.1f}")
print(f"   rigger nå: Appalachia {RIG['Appalachia'].iloc[-1]:.0f}, Haynesville {RIG['Haynesville'].iloc[-1]:.0f}, "
      f"Permian {RIG['Permian'].iloc[-1]:.0f} ({RIG['Permian'].index[-1]})")
print(f"   produksjon siste 12 mnd ({P.index[-1]}): {VEKST.iloc[-1]:+.1f} log-%")
print(f"\n   Oppsummering: T1 {RES['T1']}, T2 {RES['T2']}, T3 {RES['T3']}")
