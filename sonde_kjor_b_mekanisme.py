# ---------------------------------------------------------------------------
# sonde_kjor_b_mekanisme: maaler B tilbudet? (Frodes bestilling 12.10.2026)
#
# Laerdom fra gass og laks: fysiske maal for aktivitet (rigger, biomasse)
# varslet tilbudet, regnskapstall (capex delt paa avskrivninger) og smolt
# gjorde det ikke. Denne sonden tester to ting. Den ser IKKE paa papirene
# eller prisen framover. Ingenting paa dashbordet endres.
#
# TEST 1, B for olje fra oljerigger. Rigger i Permian, Eagle Ford og Bakken
# (EIA DPR-arkiv 2007 til 2021, STEO tabell 10a fra 2022, prognosen kuttet
# bort som i sonde_kjor_gass_rigger), snitt 3 mnd, endring 12 mnd i log-%, mot
# vekst i amerikansk raaoljeproduksjon over 12 mnd (EIA MCRFPUS2) L mnd senere,
# L = 6, 12, 18.
#   K1  hoeyeste korrelasjon minst 0,30 OG kontrollen uten overlapp (desember,
#       aar t mot vekst aar t+1) har samme fortegn. Samme krav som for gass.
#   Beskrivende: svarer riggene paa WTI (L = 3, 6, 9, 12)?
#
# TEST 2, varsler dagens B for metallene gruveproduksjonen? Forholdet
# investeringer/avskrivninger per aar fra b_capex.json (tilbud_b.py) mot
# verdens gruveproduksjon fra OWID (USGS og BGS): kobber (Copper), gull
# (Gold), jernmalm (Iron ore, jerninnhold), kull (Coal), aluminium (Bauxite,
# som tilnaerming: B-selskapene er smelteverk, ikke gruver). Uran har ingen
# serie hos OWID og bare 10 aar B; testes ikke.
#   M1  forholdet i aar t mot produksjonsvekst aar t+1, t+2 og t+3 (hver for
#       seg). Forventet positiv: mer investering, mer produksjon senere.
#   M2  femaarssnittet av forholdet (grunnlaget for B2) i aar t mot samlet
#       produksjonsvekst fra t til t+3 (gruver tar aar aa bygge).
#   Et metall bestaar hvis hoeyeste av M1 og M2 er minst 0,30. Med 10 til 19
#   aar er dette svakt bevis; n vises, og et metall som ikke bestaar, har en
#   B som ikke er vist aa maale tilbudet.
# BESLUTNING: K1 holder -> B for olje kan registreres som Challenger.
# Et metall som ikke bestaar M -> B-tallet paa bordet merkes som ikke
# bekreftet som tilbudsmaal, og Frode avgjoer om det skal staa.
# ---------------------------------------------------------------------------

import io, json, re, time
import numpy as np
import pandas as pd
import requests

UA = {"User-Agent": "Syklusbordet frode@h-k.no"}
L_MND = [6, 12, 18]


def get(url, **kw):
    for i in range(4):
        try:
            r = requests.get(url, headers=UA, timeout=120, **kw)
            if r.status_code == 200:
                return r
        except requests.RequestException:
            pass
        time.sleep(2 ** (i + 1))
    raise RuntimeError(url)


def mnd(s):
    s = s.dropna()
    return s[~s.index.duplicated(keep="last")].sort_index()


def eia_hist(url):
    t = get(url).text
    ut = {}
    for aar, rest in re.findall(r"<td class='B4'>&nbsp;&nbsp;(\d{4})</td>(.*?)</tr>", t, re.S):
        for m, v in enumerate(re.findall(r"<td class='B3'>([\d,.]*)</td>", rest), 1):
            if v:
                ut[pd.Period(f"{aar}-{m:02d}", "M")] = float(v.replace(",", ""))
    return pd.Series(ut).sort_index()


print("TEST 1. B FOR OLJE FRA OLJERIGGER\n")
dpr = pd.read_excel(io.BytesIO(get("https://www.eia.gov/petroleum/drilling/xls/dpr-data.xlsx").content),
                    sheet_name=None, header=None)
steo = pd.read_excel(io.BytesIO(get("https://www.eia.gov/outlooks/steo/xls/STEO_m.xlsx").content),
                     sheet_name="10atab", header=None)
m = re.search(r"(\w+) (\d+), (\d{4})", str(steo.iloc[3, 0]))
siste = pd.Period(pd.Timestamp(f"{m.group(1)} {m.group(2)} {m.group(3)}"), "M") - 2
kol = list(range(2, steo.shape[1]))
sidx = pd.period_range(f"{int(steo.iloc[2, 2])}-01", periods=len(kol), freq="M")
kode = {str(steo.iloc[i, 0]).strip(): i for i in range(len(steo))}
RIG = {}
for b, k in {"Permian": "PM", "Eagle Ford": "EF", "Bakken": "BK"}.items():
    d = dpr[f"{b} Region"].iloc[2:]
    a = mnd(pd.Series(pd.to_numeric(d[1], errors="coerce").values, index=pd.PeriodIndex(pd.to_datetime(d[0]), freq="M")))
    s = pd.Series(pd.to_numeric(steo.iloc[kode[f"RIGS{k}"], kol], errors="coerce").values, index=sidx)
    s = s[s.index <= siste].dropna()
    f = a.index.intersection(s.index)
    print(f"   {b:10s} DPR {a.index[0]}-{a.index[-1]}, STEO til {s.index[-1]}; overlapp n {len(f)}, "
          f"snitt {a[f].mean():.1f} mot {s[f].mean():.1f}")
    RIG[b] = mnd(pd.concat([a[a.index < pd.Period("2022-01", "M")], s]))
R = pd.concat(RIG, axis=1).dropna().sum(axis=1)
r3 = R.rolling(3).mean()
X = (100 * np.log(r3 / r3.shift(12))).dropna()
P = eia_hist("https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx?n=PET&s=MCRFPUS2&f=M")
print(f"   raaolje USA (EIA MCRFPUS2): {P.index[0]} til {P.index[-1]}")
P12 = P.rolling(12).mean()
V = 100 * np.log(P12 / P12.shift(12))
ap = P.groupby(lambda p: p.year).agg(["mean", "count"]); ap = ap[ap["count"] == 12]["mean"]
VA = 100 * np.log(ap / ap.shift(1))
res = {}
for L in L_MND:
    d = pd.concat([X, V.shift(-L)], axis=1).dropna()
    res[L] = (float(d.iloc[:, 0].corr(d.iloc[:, 1])), len(d))
    print(f"   rigger t mot produksjonsvekst t+{L}: {res[L][0]:+.2f} (n {res[L][1]}, overlappende)")
xd = X[[p for p in X.index if p.month == 12]]; xd.index = [p.year for p in xd.index]
dd = pd.DataFrame({"x": xd, "v": [VA.get(a + 1, np.nan) for a in xd.index]}, index=xd.index).dropna()
kd = float(dd["x"].corr(dd["v"]))
best = max(res, key=lambda L: res[L][0])
k1 = res[best][0] >= 0.30 and kd > 0
print(f"   uten overlapp (des aar t mot vekst aar t+1): {kd:+.2f}, n {len(dd)}")
print(f"   K1: {res[best][0]:+.2f} ved L = {best} -> {'HOLDER' if k1 else 'HOLDER IKKE'}")
w = pd.read_csv(io.StringIO(get("https://raw.githubusercontent.com/datasets/oil-prices/main/data/wti-monthly.csv").text))
W = mnd(pd.Series(w.iloc[:, 1].values, index=pd.PeriodIndex(pd.to_datetime(w.iloc[:, 0]), freq="M")).astype(float))
dw = 100 * np.log(W / W.shift(12))
print("   beskrivende, WTI-endring mot riggendring L mnd senere: " + ", ".join(
    f"L {L}: {pd.concat([dw, X.shift(-L)], axis=1).dropna().corr().iloc[0, 1]:+.2f}" for L in (3, 6, 9, 12)))
print(f"   i dag: rigger {R.iloc[-1]:.0f} ({R.index[-1]}), endring 12 mnd {X.iloc[-1]:+.1f} log-%; "
      f"produksjon {P.index[-1]} {V.iloc[-1]:+.1f} log-% over 12 mnd")

print("\n\nTEST 2. VARSLER B FOR METALLENE GRUVEPRODUKSJONEN?\n")
o = pd.read_csv(io.StringIO(get("https://ourworldindata.org/grapher/global-mine-production-minerals.csv"
                                "?v=1&csvType=full&useColumnShortNames=false").text))
o.columns = ["Entity", "Year", "prod"] + list(o.columns[3:])
# Rettet etter foerste kjoering 12.10.2026: jerninnhold finnes hos OWID bare
# fra 2020 (4 aar), saa jernmalm kunne ikke testes. Byttet til raamalm (fra
# 1904) paa grunn av datamangel, ikke resultat. Kriteriet er uendret.
KART = {"kobber": "Copper", "gull": "Gold", "jernmalm": "Iron ore (crude ore)", "kull": "Coal",
        "aluminium": "Bauxite"}
B = json.load(open("b_capex.json", encoding="utf-8"))["metaller"]
RES2 = {}
for met, ent in KART.items():
    if met not in B:
        print(f"   {met}: ingen B"); continue
    v = B[met]
    rat = pd.Series(v["ratio"], index=v["aar"], dtype=float)
    sn5 = rat.rolling(5, min_periods=3).mean()
    pr = o[o.Entity == ent].set_index("Year")["prod"].astype(float).sort_index()
    g = 100 * np.log(pr / pr.shift(1))
    print(f"   {met:10s} B {rat.index.min()}-{rat.index.max()}, produksjon ({ent}) {pr.index.min()}-{pr.index.max()}")
    m1 = {}
    for k in (1, 2, 3):
        d = pd.DataFrame({"x": rat, "y": [g.get(a + k, np.nan) for a in rat.index]}, index=rat.index).dropna()
        m1[k] = (float(d.x.corr(d.y)) if len(d) >= 6 else np.nan, len(d))
    g3 = 100 * np.log(pr.shift(-3) / pr)
    d2 = pd.DataFrame({"x": sn5, "y": [g3.get(a, np.nan) for a in sn5.index]}, index=sn5.index).dropna()
    m2 = (float(d2.x.corr(d2.y)) if len(d2) >= 6 else np.nan, len(d2))
    best = np.nanmax([m1[1][0], m1[2][0], m1[3][0], m2[0]])
    ok = bool(best >= 0.30)
    RES2[met] = ok
    print(f"      M1 t+1 {m1[1][0]:+.2f} (n {m1[1][1]}), t+2 {m1[2][0]:+.2f} (n {m1[2][1]}), t+3 {m1[3][0]:+.2f} (n {m1[3][1]});"
          f"  M2 {m2[0]:+.2f} (n {m2[1]})  -> {'BESTAAR' if ok else 'BESTAAR IKKE'}")
print("   uran: ingen produksjonsserie hos OWID, bare 10 aar B; ikke testet")
print(f"\n   Oppsummering: K1 olje {k1}; metaller {RES2}")
