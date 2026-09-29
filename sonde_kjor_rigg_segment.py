# ---------------------------------------------------------------------------
# sonde_kjor_rigg_segment: B for rigger med segmenttall fra de blandede
# selskapene
#
# Frodes bestilling 29.09.2026, etter sonde_kjor_rigg_b. Der ble de blandede
# riggselskapene holdt utenfor for aa faa rene signaler, og da sto dypt vann
# igjen med Transocean alene og grunt vann med Borr alene etter 2019. De
# blandede rapporterer likevel investeringer og avskrivninger per segment
# (flytere, jackups) i noten om segmenter. Tallene ligger ikke i SECs samlede
# data (companyfacts), men i XBRL-fila til hver aarsrapport, merket med
# segmentaksen (us-gaap:StatementBusinessSegmentsAxis).
#
# Sonden
#   1  henter alle 10-K og 20-F for de blandede selskapene, leser XBRL-fila og
#      plukker ut tolvmaaneders tall per segment for investeringer og
#      avskrivninger;
#   2  klassifiserer segmentene etter navnet paa medlemmet, satt foer kjoering:
#        dyp    floater, deepwater, drillship, semisub, midwater, ultra
#        grunt  jackup, jack-up, shallow
#        ellers (tender, managed, ARO, other, reconciling) teller ikke;
#   3  legger segmenttallene sammen med de rene selskapene fra
#      sonde_kjor_rigg_b og viser forholdet og B2 per segment og aar, med
#      antall selskaper.
# Nyeste aarsrapport vinner for et aar (omarbeidede tall).
#
# KONTROLL, som i sonde_kjor_rigg_b og skrevet foer kjoering: dypt vann boer
# ha forhold over 1,2 i 2011 til 2014 og under 1,0 i 2016 til 2021. Grunt
# vann hadde ogsaa en nybyggboelge (jackups bestilt 2012 til 2014), saa samme
# krav brukes der.
# ---------------------------------------------------------------------------

import contextlib, io, json, re, runpy, time
import numpy as np
import pandas as pd
import requests

UA = {"User-Agent": "Syklusbordet frode@h-k.no"}
SKJEMA = {"10-K", "20-F"}
BLANDET = {
    "0000314808": "Valaris (Ensco)",
    "0001458891": "Noble Corp",
    "0001895262": "Noble Corp plc",
    "0001169055": "Noble Finance",
    "0001351413": "Seadrill (gammel)",
    "0001737706": "Seadrill",
    "0000833081": "Pride International",
    "0000008411": "Atwood Oceanics",
    "0000085408": "Rowan Companies plc",
    "0001419428": "Vantage Drilling",
    "0001451505": "Transocean Ltd",
}
KLASSE = [("dyp", r"floater|deepwater|drillship|semisub|midwater|ultra"),
          ("grunt", r"jack.?up|shallow")]
CAPEX = r"^(us-gaap:SegmentExpenditureAdditionToLongLivedAssets|us-gaap:PaymentsToAcquirePropertyPlantAndEquipment|us-gaap:PaymentsToAcquireProductiveAssets|[a-z]+:CapitalExpenditures?\w*|[a-z]+:\w*CapitalExpenditure\w*)$"
DEP = r"^(us-gaap:DepreciationDepletionAndAmortization|us-gaap:DepreciationAndAmortization|us-gaap:Depreciation|us-gaap:DepreciationNonproduction|us-gaap:CostDepreciationAmortizationAndDepletion|[a-z]+:Depreciation\w*)$"


def get(url, **kw):
    for i in range(4):
        try:
            r = requests.get(url, headers=UA, timeout=120, **kw)
            if r.status_code == 429:
                time.sleep(5); continue
            return r
        except requests.RequestException:
            time.sleep(3)
    return None


def aarsrapporter(cik):
    s = get(f"https://data.sec.gov/submissions/CIK{cik}.json").json()
    blokker = [s["filings"]["recent"]]
    for f in s["filings"].get("files", []):
        r = get(f"https://data.sec.gov/submissions/{f['name']}")
        if r is not None and r.status_code == 200:
            blokker.append(r.json())
    ut = []
    for b in blokker:
        for i in range(len(b["form"])):
            if b["form"][i] in SKJEMA and b["filingDate"][i] >= "2009":
                ut.append((b["filingDate"][i], b["accessionNumber"][i]))
    return sorted(set(ut))


def instans(cik, accn):
    base = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accn.replace('-', '')}"
    r = get(base + "/index.json")
    if r is None or r.status_code != 200:
        return None
    navn = [x["name"] for x in r.json()["directory"]["item"]]
    kand = [n for n in navn if n.endswith("_htm.xml")] or \
           [n for n in navn if n.endswith(".xml") and not re.search(r"_(cal|def|lab|pre)\.xml$|FilingSummary|MetaLinks", n)]
    if not kand:
        return None
    r = get(base + "/" + kand[0])
    return None if r is None or r.status_code != 200 else r.text


def segmentfakta(t):
    ctx = {}
    for m in re.finditer(r"<(?:xbrli:)?context id=\"([^\"]+)\">(.*?)</(?:xbrli:)?context>", t, re.S):
        body = m.group(2)
        st = re.search(r"<(?:xbrli:)?startDate>([^<]+)<", body)
        en = re.search(r"<(?:xbrli:)?endDate>([^<]+)<", body)
        dims = dict(re.findall(r"<xbrldi:explicitMember dimension=\"([^\"]+)\">([^<]+)<", body))
        if not st or not en:
            continue
        dager = (pd.Timestamp(en.group(1)) - pd.Timestamp(st.group(1))).days
        seg = dims.get("us-gaap:StatementBusinessSegmentsAxis")
        andre = [d for d in dims if d not in ("us-gaap:StatementBusinessSegmentsAxis", "srt:ConsolidationItemsAxis")]
        if 330 <= dager <= 400 and seg and not andre:
            ctx[m.group(1)] = (int(en.group(1)[:4]), seg)
    ut = []
    for m in re.finditer(r"<([A-Za-z0-9\-]+:[A-Za-z0-9_]+)\b[^>]*?contextRef=\"([^\"]+)\"[^>]*>([^<]*)</\1>", t):
        if m.group(2) not in ctx:
            continue
        try:
            v = float(m.group(3).strip())
        except ValueError:
            continue
        aar, seg = ctx[m.group(2)]
        ut.append((m.group(1), aar, seg, v))
    return ut


def klasse(medlem):
    for k, mønster in KLASSE:
        if re.search(mønster, medlem, re.I):
            return k
    return None


print("1. SEGMENTTALL FRA DE BLANDEDE SELSKAPENE\n")
SEG = {}   # (klasse, cik, aar) -> {"capex":, "dda":, "arkiv":}
for cik, navn in BLANDET.items():
    rap = aarsrapporter(cik)
    print(f"   {navn}: {len(rap)} aarsrapporter fra 2009")
    for dato, accn in rap:
        t = instans(cik, accn)
        time.sleep(0.15)
        if not t:
            print(f"      {dato} ingen XBRL-fil"); continue
        fakta = segmentfakta(t)
        funn = {}
        for navn_b, aar, medlem, v in fakta:
            k = klasse(medlem)
            if not k:
                continue
            felt = "capex" if re.match(CAPEX, navn_b) else "dda" if re.match(DEP, navn_b) else None
            if not felt:
                continue
            nk = (k, aar)
            funn.setdefault(nk, {}).setdefault(felt, {})[medlem] = abs(v)
        for (k, aar), d in funn.items():
            if "capex" in d and "dda" in d:
                SEG[(k, cik, aar)] = {"capex": sum(d["capex"].values()), "dda": sum(d["dda"].values()),
                                      "medlemmer": sorted(set(d["capex"]) | set(d["dda"])), "rapport": dato}
        vis = sorted({(k, a) for (k, a), d in funn.items() if "capex" in d and "dda" in d})
        print(f"      {dato} {len(fakta):5d} segmentfakta, brukbare: " + (", ".join(f"{k} {a}" for k, a in vis) or "ingen"))

print("\n   Brukte segmentmedlemmer per selskap og klasse:")
for cik, navn in BLANDET.items():
    for k in ("dyp", "grunt"):
        m = sorted({x for (kk, c, a), d in SEG.items() if c == cik and kk == k for x in d["medlemmer"]})
        aar = sorted({a for (kk, c, a) in SEG if c == cik and kk == k})
        if m:
            print(f"      {navn:22s} {k:5s} {aar[0]}-{aar[-1]}  {', '.join(x.split(':')[-1] for x in m)[:110]}")

print("\n\n2. RENE SELSKAPER (fra sonde_kjor_rigg_b)\n")
with contextlib.redirect_stdout(io.StringIO()):
    RB = runpy.run_path("sonde_kjor_rigg_b.py")
REN = RB["DATA"]
for d in REN.values():
    print(f"   {d['navn']:32s} {d['seg']:7s} {d['capex'].index.min()}-{d['capex'].index.max()}")

print("\n\n3. SAMLET PER SEGMENT OG AAR (rene selskaper + segmenttall fra blandede)\n")
RES = {}
for k in ("dyp", "grunt"):
    rader = {}
    for d in REN.values():
        if d["seg"] != k or d["enh"] != "USD":
            continue
        for a in d["capex"].index:
            r = rader.setdefault(int(a), {"capex": 0.0, "dda": 0.0, "n_ren": 0, "n_seg": 0, "forhold": []})
            r["capex"] += d["capex"][a]; r["dda"] += d["dda"][a]; r["n_ren"] += 1
            r["forhold"].append(d["capex"][a] / d["dda"][a])
    for (kk, cik, a), d in SEG.items():
        if kk != k or not d["dda"]:
            continue
        # Transocean og Rowan staar ogsaa som rene; ta ikke med segmenttall for dem to ganger
        if any(v["navn"].split()[0] == BLANDET[cik].split()[0] and v["seg"] == k and a in v["capex"].index for v in REN.values()):
            continue
        r = rader.setdefault(int(a), {"capex": 0.0, "dda": 0.0, "n_ren": 0, "n_seg": 0, "forhold": []})
        r["capex"] += d["capex"]; r["dda"] += d["dda"]; r["n_seg"] += 1
        r["forhold"].append(d["capex"] / d["dda"])
    df = pd.DataFrame({a: {"n_ren": r["n_ren"], "n_seg": r["n_seg"], "capex": r["capex"], "dda": r["dda"],
                           "forhold": r["capex"] / r["dda"] if r["dda"] else np.nan,
                           "median": float(np.median(r["forhold"])) if r["forhold"] else np.nan}
                       for a, r in rader.items()}).T.sort_index()
    df["snitt5"] = df["forhold"].rolling(5, min_periods=3).mean()
    df["B2"] = ((1.4 - df["snitt5"]) / 0.8 * 100).clip(0, 100)
    RES[k] = df
    print(f"   {k.upper()}")
    print(f"   {'aar':>5s} {'rene':>5s} {'segm':>5s} {'capex mUSD':>11s} {'avskr mUSD':>11s} {'forhold':>8s} {'median':>7s} {'B2':>5s}")
    for a, r in df.iterrows():
        print(f"   {int(a):5d} {int(r['n_ren']):5d} {int(r['n_seg']):5d} {r['capex'] / 1e6:11,.0f} {r['dda'] / 1e6:11,.0f} "
              f"{r['forhold']:8.2f} {r['median']:7.2f} {'' if np.isnan(r['B2']) else format(r['B2'], '.0f'):>5s}")
    print()

print("\n4. KONTROLL (satt foer kjoering)\n")
for k, df in RES.items():
    f1 = df.loc[2011:2014, "forhold"].mean(); f2 = df.loc[2016:2021, "forhold"].mean()
    n = df.loc[2019:, ["n_ren", "n_seg"]].sum(axis=1)
    print(f"   {k:5s} forhold 2011-2014 {f1:.2f} (krav over 1,2) {'ok' if f1 > 1.2 else 'IKKE'}; "
          f"2016-2021 {f2:.2f} (krav under 1,0) {'ok' if f2 < 1.0 else 'IKKE'}; "
          f"selskaper per aar fra 2019: {n.min():.0f} til {n.max():.0f}; siste B2 {df['B2'].dropna().iloc[-1]:.0f}")

json.dump({k: {str(int(a)): {c: (None if pd.isna(v) else float(v)) for c, v in r.items()} for a, r in df.iterrows()}
           for k, df in RES.items()}, open("sonder/rigg_segment.json", "w"), indent=1)
print("\nlagret sonder/rigg_segment.json")
