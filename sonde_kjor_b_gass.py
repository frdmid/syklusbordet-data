# ---------------------------------------------------------------------------
# sonde_kjor_b_gass: finnes en tilbudsskaar B for Henry Hub?
#
# Frodes bestilling 07.10.2026. Samme maal som B for metallene og riggene:
# investeringer (capex) delt paa avskrivninger (DD&A), fra SEC, per selskap
# og aar. Sonden bygger ingenting. tilbud_b.py er frosset i Champion v1.0, saa
# en B for gass kan bare komme inn som Challenger.
#
# RENE SIGNALER: bare aar der selskapet i hovedsak produserte toerrgass i USA
# teller. Vinduene er satt foer kjoering ut fra kjent selskapshistorie:
#   EQT          2009-     (Equitrans konsolidert til 2018, midstream i capex)
#   Range        2009-
#   Antero       2010-     (Antero Midstream konsolidert til 2019)
#   CNX          2018-     (kullet skilt ut i november 2017)
#   Southwestern 2009-2023 (kjoept av Chesapeake i oktober 2024)
#   Cabot        2009-2020 (Coterra fra 2021 er olje og gass)
#   Gulfport     2014-2020 (Utica fra 2014; ny startbalanse mai 2021)
#   Comstock     2016-     (solgte Eagle Ford-oljen 2015, Haynesville siden)
# Blandet, vises men teller ikke: Chesapeake/Expand Energy (oljevridd
# 2013-2019, ny startbalanse februar 2021) og Coterra fra 2021.
# Regel A fra riggene gjelder: aar etter ny startbalanse holdes utenfor,
# fordi avskrivningene da er kunstig lave.
#
# NEDSKRIVNINGER holdes utenfor nevneren og vises for seg (samme retting som
# i tilbud_b.py 29.09.2026). Gasselskapene skriver ned tungt i bunnaarene,
# og med nedskrivningene i nevneren ville B se ut som et tilbudskutt som ikke
# har skjedd.
#
# UTSKRIFT per aar: antall selskaper, sum capex, sum avskrivninger, forholdet
# av summene, median av selskapenes forhold, nedskrivninger i prosent av
# avskrivningene, B1 (persentil, slik tilbud_b.py regner den, bare med aar
# som var kjent da) og B2 (nivaa mot 1,0, slik tilbud_b.py regner den).
#
# FORVENTNING foer kjoering: skifergass har bratt fall per broenn, saa
# forholdet ligger trolig over 1 ogsaa i normale aar. B2 (nivaa mot 1,0) er
# derfor trolig lite meningsfylt for gass, og B1 (relativt) er kandidaten.
#
# KONTROLL, skrevet foer kjoering. Kjent historie: skifergassboomen ga
# kraftige investeringer 2010-2014, kutt i 2015-2016 og igjen i 2020, og
# store nedskrivninger i 2015-2016 og 2020.
#   K1  forholdet 2010-2014 i snitt over 1,3
#   K2  forholdet 2016 hoyst 0,7 ganger snittet 2012-2014
#   K3  forholdet 2020 lavere enn 2019
#   K4  nedskrivninger 2015-2016 og 2020 i snitt minst dobbelt av 2017-2019
# BESLUTNING: K1 til K3 maa holde for at B1 for gass kan foreslaas som
# Challenger. K4 viser bare om nedskrivningene er skilt ut riktig. Holder
# ikke K1 til K3, maaler tallene ikke tilbudet, og ingen B for gass bygges.
# ---------------------------------------------------------------------------

import time
import numpy as np
import pandas as pd
import requests

UA = {"User-Agent": "Syklusbordet frode@h-k.no"}
FORMER = {"10-K", "20-F", "40-F", "10-K/A", "20-F/A"}
MIN_AAR = 6

# cik: (navn, ord som maa staa i navnet hos SEC, foerste aar, siste aar, teller)
SELSKAP = {
    "0000033213": ("EQT", "EQT", 2009, None, True),
    "0000315852": ("Range Resources", "RANGE", 2009, None, True),
    "0001433270": ("Antero Resources", "ANTERO", 2010, None, True),
    "0001070412": ("CNX Resources", "CNX", 2018, None, True),
    "0000007332": ("Southwestern Energy", "SOUTHWESTERN", 2009, 2023, True),
    # Navnet hos SEC er naa Coterra (samme CIK); rettet etter foerste kjoering
    "0000858470": ("Cabot Oil & Gas", "COTERRA", 2009, 2020, True),
    "0000874499": ("Gulfport Energy", "GULFPORT", 2014, 2020, True),
    "0000023194": ("Comstock Resources", "COMSTOCK", 2016, None, True),
    # blandet, teller ikke
    "0000895126": ("Chesapeake / Expand Energy", "", 2009, None, False),
    "0000858470_c": ("Coterra (fra 2021)", "", 2021, None, False),
}

# Rettet etter foerste kjoering 07.10.2026 (kriteriet er uendret): foerste
# versjon hadde PaymentsToAcquireOilAndGasProperty i listen. Det er kjoep av
# arealer og felt, ikke boring, og ga Antero forhold 0,05 til 0,3 og
# Southwestern 0,12 i 2013. Det er tatt ut. Boring (ExploreAndDevelop) staar
# naa foerst, deretter samlede investeringer (ProductiveAssets) foran PPE,
# fordi PPE hos Southwestern 2014 tar med kjoepet av Chesapeakes eiendeler
# (5,3 mrd.) og hos EQT 2013 bare er 114 mill.
CAPEX = ["PaymentsToExploreAndDevelopOilAndGasProperties", "PaymentsToAcquireProductiveAssets",
         "PaymentsToAcquireOilAndGasPropertyAndEquipment", "PaymentsToAcquirePropertyPlantAndEquipment"]
DDA = ["DepreciationDepletionAndAmortization", "DepreciationDepletionAndAmortizationExcludingAmortizationOfDeferredSalesCommissions",
       "DepreciationAndAmortization", "OilAndGasDepletionExpense"]
NEDSKR = ["ImpairmentOfOilAndGasProperties", "AssetImpairmentCharges", "ImpairmentOfLongLivedAssetsHeldForUse",
          "ResultsOfOperationsImpairmentOfOilAndGasProperties", "CapitalizedCostsOilAndGasProducingActivitiesImpairment"]


def aarsserie(fakta, begreper, sum_alle=False):
    """Skjoetet serie: foerste begrep vinner et aar, de neste fyller hull (for
    nedskrivninger det stoerste per aar). Tolvmaaneders perioder, siste
    innlevering vinner."""
    samlet, enh_valgt, brukt = {}, None, []
    for b in begreper:
        d = fakta.get("us-gaap", {}).get(b)
        if not d:
            continue
        for enh, pkt in d.get("units", {}).items():
            if len(enh) != 3 or (enh_valgt and enh != enh_valgt):
                continue
            best = {}
            for p in pkt:
                if p.get("form") not in FORMER or not p.get("start"):
                    continue
                dager = (pd.Timestamp(p["end"]) - pd.Timestamp(p["start"])).days
                if not 330 <= dager <= 400:
                    continue
                k = int(p["end"][:4])
                if k not in best or p.get("accn", "") > best[k].get("accn", ""):
                    best[k] = p
            if not best:
                continue
            s = {k: float(v["val"]) for k, v in best.items()}
            nye = {k: v for k, v in s.items() if sum_alle or k not in samlet}
            if not nye:
                continue
            for k, v in nye.items():
                samlet[k] = max(samlet.get(k, 0.0), abs(v)) if sum_alle else abs(v)
            enh_valgt = enh
            brukt.append(b)
    if samlet:
        return "+".join(brukt), enh_valgt, pd.Series(samlet).sort_index()
    return None, None, pd.Series(dtype=float)


print("1. SELSKAPENE\n")
DATA, FAKTA = {}, {}
for noekkel, (navn, ord_, fra, til, teller) in SELSKAP.items():
    cik = noekkel.split("_")[0]
    try:
        if cik not in FAKTA:
            r = requests.get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json", headers=UA, timeout=120)
            if r.status_code != 200:
                print(f"   {navn:28s} ingen XBRL-data ({r.status_code})"); continue
            FAKTA[cik] = r.json()
            time.sleep(0.25)
        j = FAKTA[cik]
    except Exception as e:
        print(f"   {navn:28s} {type(e).__name__}"); continue
    sec_navn = j.get("entityName", "")
    if ord_ and ord_ not in sec_navn.upper():
        print(f"   {navn:28s} FEIL SELSKAP: SEC sier '{sec_navn}', hoppet over"); continue
    f = j.get("facts", {})
    bc, ec, cx = aarsserie(f, CAPEX)
    bd, ed, dd = aarsserie(f, DDA)
    bn, en, nd = aarsserie(f, NEDSKR, sum_alle=True)
    if cx.empty or dd.empty or ec != ed:
        print(f"   {navn:28s} mangler {'capex' if cx.empty else 'avskrivninger' if dd.empty else 'samme valuta'}")
        continue
    aar = cx.index.intersection(dd.index)
    aar = aar[(aar >= fra) & ((aar <= til) if til else True)]
    if len(aar) < 2:
        print(f"   {navn:28s} for faa aar i vinduet {fra}-{til or ''}"); continue
    DATA[noekkel] = {"navn": navn, "teller": teller, "capex": cx[aar], "dda": dd[aar],
                     "ned": nd.reindex(aar).fillna(0.0) if en == ec else pd.Series(0.0, index=aar)}
    fh = cx[aar] / dd[aar]
    print(f"   {navn:28s} {'teller' if teller else 'vises '} SEC: {sec_navn[:30]:30s} {aar.min()}-{aar.max()}"
          f"  forhold median {fh.median():.2f} siste {fh.iloc[-1]:.2f}  [{bc[:34]} / {bd[:34]}]")

print("\n   Per selskap og aar (capex/avskrivninger, nedskrivninger i % av avskrivningene i parentes):")
alle_aar = sorted({a for d in DATA.values() for a in d["capex"].index})
print("   " + f"{'':28s}" + "".join(f"{a:>12d}" for a in alle_aar))
for d in DATA.values():
    celler = []
    for a in alle_aar:
        if a in d["capex"].index and d["dda"][a]:
            celler.append(f"{d['capex'][a] / d['dda'][a]:5.2f} ({100 * d['ned'][a] / d['dda'][a]:3.0f})")
        else:
            celler.append("")
    print("   " + f"{d['navn'][:28]:28s}" + "".join(f"{c:>12s}" for c in celler))

print("\n\n2. GASS SAMLET (bare selskaper som teller)\n")
egne = [d for d in DATA.values() if d["teller"]]
rader = []
for a in sorted({a for d in egne for a in d["capex"].index}):
    m = [d for d in egne if a in d["capex"].index]
    cx = sum(d["capex"][a] for d in m); dd = sum(d["dda"][a] for d in m); nd = sum(d["ned"][a] for d in m)
    fh = [d["capex"][a] / d["dda"][a] for d in m if d["dda"][a]]
    rader.append({"aar": a, "n": len(m), "capex": cx, "dda": dd, "forhold": cx / dd if dd else np.nan,
                  "median": float(np.median(fh)) if fh else np.nan, "ned_pst": 100 * nd / dd if dd else np.nan})
df = pd.DataFrame(rader).set_index("aar")
df = df[df["n"] >= 2]
v = df["forhold"].values
pct = np.array([np.nan if i + 1 < MIN_AAR else (v[:i + 1] <= v[i]).sum() / (i + 1) for i in range(len(v))])
df["B1"] = (1 - pct) * 100
df["snitt5"] = df["forhold"].rolling(5, min_periods=3).mean()
df["B2"] = ((1.4 - df["snitt5"]) / 0.8 * 100).clip(0, 100)
print(f"   {'aar':>5s} {'n':>3s} {'capex mUSD':>11s} {'avskr mUSD':>11s} {'forhold':>8s} {'median':>7s} {'nedskr %':>9s} {'B1':>5s} {'B2':>5s}")
for a, r in df.iterrows():
    f = lambda x: "" if np.isnan(x) else format(x, ".0f")
    print(f"   {a:5d} {r['n']:3.0f} {r['capex'] / 1e6:11,.0f} {r['dda'] / 1e6:11,.0f} {r['forhold']:8.2f} "
          f"{r['median']:7.2f} {r['ned_pst']:9.0f} {f(r['B1']):>5s} {f(r['B2']):>5s}")

print("\n\n3. KONTROLL MOT KJENT HISTORIE (satt foer kjoering)\n")
g = lambda a, b, k="forhold": df.loc[a:b, k].mean()
k1 = g(2010, 2014); k2a = df["forhold"].get(2016, np.nan); k2b = g(2012, 2014)
k3a = df["forhold"].get(2020, np.nan); k3b = df["forhold"].get(2019, np.nan)
k4a = np.nanmean([df["ned_pst"].get(a, np.nan) for a in (2015, 2016, 2020)]); k4b = g(2017, 2019, "ned_pst")
ok = [k1 > 1.3, k2a <= 0.7 * k2b, k3a < k3b, k4a >= 2 * max(k4b, 1)]
print(f"   K1 forhold 2010-2014: {k1:.2f} (krav over 1,3) -> {'ok' if ok[0] else 'IKKE'}")
print(f"   K2 forhold 2016: {k2a:.2f} mot 2012-2014 {k2b:.2f} (krav hoyst {0.7 * k2b:.2f}) -> {'ok' if ok[1] else 'IKKE'}")
print(f"   K3 forhold 2020: {k3a:.2f} mot 2019 {k3b:.2f} (krav lavere) -> {'ok' if ok[2] else 'IKKE'}")
print(f"   K4 nedskrivninger 2015-16 og 2020: {k4a:.0f} % mot {k4b:.0f} % 2017-2019 (krav minst dobbelt) -> {'ok' if ok[3] else 'IKKE'}")
print("\n   " + ("K1 til K3 holder. B1 for gass kan foreslaas som Challenger."
                 if all(ok[:3]) else "K1 til K3 holder IKKE alle. Ingen B for gass bygges paa disse tallene."))
s = df.dropna(subset=["B1"])
if not s.empty:
    print(f"   Siste aar {s.index[-1]}: forhold {s['forhold'].iloc[-1]:.2f}, B1 {s['B1'].iloc[-1]:.0f}, "
          f"B2 {s['B2'].iloc[-1]:.0f}, {int(s['n'].iloc[-1])} selskaper")
