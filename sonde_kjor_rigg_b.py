# ---------------------------------------------------------------------------
# sonde_kjor_rigg_b: finnes en tilbudsskaar B for riggmarkedet, delt i land,
# grunt vann og dypt vann?
#
# Frodes bestilling 29.09.2026. Tilbudet av rigger bestemmes av nybygg,
# reaktivering, opplag og skraping. Flaatedata per rigg koster penger, saa
# sonden bruker det samme maalet som B for metallene: investeringer (capex)
# delt paa avskrivninger, fra SEC, per selskap og aar. Under 1 over flere aar
# betyr at flaaten krymper. Nedskrivninger regnes for seg, som et tegn paa
# skraping, og holdes utenfor nevneren (samme retting som i tilbud_b.py i dag).
#
# RENE SIGNALER: bare selskaper med nesten hele flaaten i ett segment teller.
# Blandede selskaper vises, men teller ikke. Konkursrammede selskaper er med,
# ellers blir B skjev mot dem som overlevde. Inndelingen er satt foer kjoering
# ut fra flaatesammensetningen selskapene selv beskriver i 10-K:
#   land   Helmerich & Payne, Patterson-UTI, Nabors (hovedsakelig land),
#          Precision (Canada og USA, 40-F i CAD), Independence Contract
#          Drilling, Grey Wolf, Union Drilling, Bronco Drilling
#   grunt  Hercules Offshore, Paragon Offshore, Borr Drilling, Rowan
#          (jackups; fire boreskip fra 2014)
#   dyp    Transocean, Diamond Offshore, Pacific Drilling, Ocean Rig
#   blandet (teller ikke) Seadrill, Atwood, Noble, Ensco/Valaris, Vantage, Pride
# CIK er slaatt opp i SECs liste over bransjekode 1381 (boring av olje- og
# gassbroenner) 29.09.2026.
#
# UTSKRIFT per segment og aar: antall selskaper, sum capex, sum avskrivninger,
# forholdet av summene (bare USD), median av selskapenes forhold (alle),
# nedskrivninger i prosent av avskrivningene, og B2 slik tilbud_b.py regner
# den: klipp((1,4 - femaarssnitt av forholdet) / 0,8 * 100, 0, 100).
#
# KONTROLL, skrevet foer kjoering: kjent historie er at flytere ble bestilt
# i stort antall 2011 til 2014 og skrapet i stort antall 2015 til 2020, uten
# nye bestillinger etter. Dypt vann boer derfor ha forhold godt over 1 i
# 2011 til 2014, under 1 fra 2016, og store nedskrivninger 2015 til 2020.
# Viser tallene ikke det, maaler de ikke flaaten, og B for rigger boer ikke
# bygges paa dem.
# ---------------------------------------------------------------------------

import time
import numpy as np
import pandas as pd
import requests

UA = {"User-Agent": "Syklusbordet frode@h-k.no"}
FORMER = {"10-K", "20-F", "40-F", "10-K/A", "20-F/A"}

SELSKAP = {
    # land
    "0000046765": ("Helmerich & Payne", "land"),
    "0000889900": ("Patterson-UTI", "land"),
    "0001163739": ("Nabors Industries Ltd", "land"),
    "0001013605": ("Precision Drilling", "land"),
    "0001537028": ("Independence Contract Drilling", "land"),
    "0000320186": ("Grey Wolf", "land"),
    "0001133260": ("Union Drilling", "land"),
    "0001328650": ("Bronco Drilling", "land"),
    # grunt vann
    "0001330849": ("Hercules Offshore", "grunt"),
    "0001594590": ("Paragon Offshore", "grunt"),
    "0001715497": ("Borr Drilling", "grunt"),
    "0000085408": ("Rowan Companies plc", "grunt"),
    # dypt vann
    "0001451505": ("Transocean Ltd", "dyp"),
    "0000949039": ("Diamond Offshore", "dyp"),
    "0001517342": ("Pacific Drilling", "dyp"),
    "0001447382": ("Ocean Rig UDW", "dyp"),
    # blandet, teller ikke
    "0001737706": ("Seadrill Ltd", "blandet"),
    "0001351413": ("Seadrill Ltd (gammel)", "blandet"),
    "0000008411": ("Atwood Oceanics", "blandet"),
    "0001458891": ("Noble Corp", "blandet"),
    "0001895262": ("Noble Corp plc", "blandet"),
    "0000314808": ("Valaris (tidligere Ensco)", "blandet"),
    "0001419428": ("Vantage Drilling", "blandet"),
    "0000833081": ("Pride International", "blandet"),
}

# Begrepene er de riggselskapene faktisk bruker (sjekket 29.09.2026). Flere
# har byttet begrep underveis, saa seriene skjoetes: foerste begrep i listen
# vinner et aar, de neste fyller aar som mangler.
CAPEX = ["PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets",
         "PaymentsToAcquireOilAndGasPropertyAndEquipment", "PaymentsForCapitalImprovements",
         "PaymentsToAcquireMachineryAndEquipment", "PaymentsToAcquireOilAndGasEquipment",
         "PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities",
         "PurchaseOfPropertyPlantAndEquipment"]
DDA = ["DepreciationDepletionAndAmortization", "DepreciationAndAmortization",
       "DepreciationAndAmortisationExpense", "Depreciation", "DepreciationNonproduction",
       "DepreciationPropertyPlantAndEquipment"]
# Nedskrivninger av rigger, ikke goodwill (rettet etter foerste kjoering:
# Transoceans goodwill-nedskrivning 2010-2011 er ikke skraping). Begrepene kan
# overlappe, saa det stoerste per aar brukes, ikke summen.
NEDSKR = ["AssetImpairmentCharges", "ImpairmentOfLongLivedAssetsHeldForUse",
          "ImpairmentOfLongLivedAssetsToBeDisposedOf", "ImpairmentLossRecognisedInProfitOrLossPropertyPlantAndEquipment",
          "ImpairmentOfOilAndGasProperties"]


def aarsserie(fakta, begreper, sum_alle=False):
    """Skjoetet serie: foerste begrep vinner et aar, de neste fyller hull (eller
    summen av alle for nedskrivninger). Tolvmaaneders perioder, siste
    innlevering vinner."""
    samlet, enh_valgt, brukt = {}, None, []
    for b in begreper:
        for tak in ("us-gaap", "ifrs-full"):
            d = fakta.get(tak, {}).get(b)
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
DATA = {}
for cik, (navn, seg) in SELSKAP.items():
    try:
        r = requests.get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json", headers=UA, timeout=120)
        if r.status_code != 200:
            print(f"   {navn:32s} {seg:7s} ingen XBRL-data ({r.status_code})"); continue
        f = r.json().get("facts", {})
    except Exception as e:
        print(f"   {navn:32s} {seg:7s} {type(e).__name__}"); continue
    bc, ec, cx = aarsserie(f, CAPEX)
    bd, ed, dd = aarsserie(f, DDA)
    bn, en, nd = aarsserie(f, NEDSKR, sum_alle=True)
    if cx.empty or dd.empty or ec != ed:
        print(f"   {navn:32s} {seg:7s} mangler {'capex' if cx.empty else 'avskrivninger' if dd.empty else 'samme valuta'}")
        continue
    aar = cx.index.intersection(dd.index)
    if len(aar) < 2:
        print(f"   {navn:32s} {seg:7s} capex {cx.index.min()}-{cx.index.max()}, avskrivninger "
              f"{dd.index.min()}-{dd.index.max()}: for faa felles aar"); continue
    # Aar foer riggene er i drift (rettet etter foerste kjoering): et selskap
    # som bygger flaaten har nesten ingen avskrivninger, og forholdet blir
    # meningsloest (Pacific Drilling over 500 i 2009-2010). Aar med
    # avskrivninger under en firedel av selskapets median utelates.
    tidlig = [int(a) for a in aar if dd[a] < 0.25 * dd[aar].median()]
    aar = aar[[a not in tidlig for a in aar]]
    if tidlig:
        print(f"   {navn:32s} {seg:7s} utelatt aar foer drift: {tidlig}")
    DATA[cik] = {"navn": navn, "seg": seg, "enh": ec, "capex": cx[aar], "dda": dd[aar],
                 "ned": nd.reindex(aar).fillna(0.0) if en == ec else pd.Series(0.0, index=aar)}
    fh = (cx[aar] / dd[aar])
    print(f"   {navn:32s} {seg:7s} {ec} {aar.min()}-{aar.max()} ({len(aar)} aar)  capex/avskr median {fh.median():.2f}"
          f"  siste {fh.iloc[-1]:.2f}  [{bc[:30]} / {bd[:30]}]")
    time.sleep(0.25)

print("\n\n2. PER SEGMENT OG AAR\n")
RES = {}
for seg in ("land", "grunt", "dyp", "blandet"):
    egne = [d for d in DATA.values() if d["seg"] == seg]
    if not egne:
        continue
    aar = sorted({a for d in egne for a in d["capex"].index})
    rader = []
    for a in aar:
        m = [d for d in egne if a in d["capex"].index]
        usd = [d for d in m if d["enh"] == "USD"]
        cx = sum(d["capex"][a] for d in usd); dd = sum(d["dda"][a] for d in usd); nd = sum(d["ned"][a] for d in usd)
        fh = [d["capex"][a] / d["dda"][a] for d in m if d["dda"][a]]
        rader.append({"aar": a, "n": len(m), "capex": cx, "dda": dd, "forhold": cx / dd if dd else np.nan,
                      "median": float(np.median(fh)) if fh else np.nan, "ned_pst": 100 * nd / dd if dd else np.nan})
    df = pd.DataFrame(rader).set_index("aar")
    df["snitt5"] = df["forhold"].rolling(5, min_periods=3).mean()
    df["B2"] = ((1.4 - df["snitt5"]) / 0.8 * 100).clip(0, 100)
    RES[seg] = df
    print(f"   {seg.upper()}{' (teller ikke, bare til sammenligning)' if seg == 'blandet' else ''}")
    print(f"   {'aar':>5s} {'n':>3s} {'capex mUSD':>11s} {'avskr mUSD':>11s} {'forhold':>8s} {'median':>7s} {'nedskr %':>9s} {'B2':>5s}")
    for a, r in df.iterrows():
        print(f"   {a:5d} {r['n']:3.0f} {r['capex'] / 1e6:11,.0f} {r['dda'] / 1e6:11,.0f} {r['forhold']:8.2f} "
              f"{r['median']:7.2f} {r['ned_pst']:9.0f} {'' if np.isnan(r['B2']) else format(r['B2'], '.0f'):>5s}")
    print()

print("\n3. KONTROLL MOT KJENT HISTORIE (dypt vann, satt foer kjoering)\n")
if "dyp" in RES:
    d = RES["dyp"]
    f1 = d.loc[2011:2014, "forhold"].mean(); f2 = d.loc[2016:2021, "forhold"].mean()
    n1 = d.loc[2015:2020, "ned_pst"].mean(); n0 = d.loc[2010:2014, "ned_pst"].mean()
    print("   (foerste kjoering 29.09.2026 feilet paa nedskrivningene fordi goodwill var med;"
          " kriteriet er uendret, definisjonen av nedskrivning er rettet)")
    ok = [f1 > 1.2, f2 < 1.0, n1 > 2 * max(n0, 1)]
    print(f"   forhold 2011-2014: {f1:.2f} (krav over 1,2) -> {'ok' if ok[0] else 'IKKE'}")
    print(f"   forhold 2016-2021: {f2:.2f} (krav under 1,0) -> {'ok' if ok[1] else 'IKKE'}")
    print(f"   nedskrivninger 2015-2020: {n1:.0f} % av avskrivningene mot {n0:.0f} % 2010-2014 (krav minst dobbelt) -> {'ok' if ok[2] else 'IKKE'}")
    print("   " + ("Tallene foelger kjent flaatehistorie. B for dypt vann kan bygges paa dem."
                   if all(ok) else "Tallene foelger IKKE kjent flaatehistorie paa alle punkter. Se over foer noe bygges."))
print("\n   Siste B2 per segment: " + ", ".join(f"{s} {RES[s]['B2'].dropna().iloc[-1]:.0f} ({RES[s]['B2'].dropna().index[-1]})"
                                               for s in RES if not RES[s]['B2'].dropna().empty))
