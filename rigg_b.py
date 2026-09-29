# ---------------------------------------------------------------------------
# rigg_b: tilbudsskaaren B for rigger, delt i land, grunt vann og dypt vann
#
# Innfoert 29.09.2026 (Frodes beslutning) etter sonde_kjor_rigg_b og
# sonde_kjor_rigg_segment. Maalet er det samme som B for metallene i
# tilbud_b.py: investeringer (capex) delt paa avskrivninger. Under 1 over
# flere aar betyr at flaaten krymper. B2 = klipp((1,4 - femaarssnitt) / 0,8 *
# 100, 0, 100), som for metallene. Vises som informasjon i oljeservicepanelet,
# inngaar ikke i noe flagg.
#
# RENE SIGNALER
#   Rene selskaper (nesten hele flaaten i ett segment) fra SECs samlede data.
#   Blandede selskaper bidrar bare med segmenttall fra noten om segmenter i
#   XBRL-fila til hver aarsrapport (Valaris/Ensco, Seadrill, Rowan fra 2014).
#   Har et rent selskap segmenttall for et aar, brukes de i stedet for hele
#   selskapet (Rowan hadde boreskip 2014 til 2018).
#   Konkursrammede selskaper er med, ellers blir B skjev mot dem som overlevde.
#   Aar foer riggene er i drift (avskrivninger under en firedel av selskapets
#   median) utelates.
#
# UTENFOR, med grunn
#   Patterson-UTI: foerer avskrivninger og nedskrivninger samlet
#     (pten:DepreciationDepletionAmortizationAndImpairment). Nedskrivninger i
#     nevneren gir falsk krymping, samme feil som ble rettet i tilbud_b.py.
#   Noble, Transocean foer 2009, Atwood, Pride, Vantage: blandede med ett
#     segment. Transocean er i praksis flytere fra 2009 og staar som ren.
#
# SVAKHETER (staar ogsaa i JSON-fila)
#   Aar etter ny startbalanse holdes utenfor (UTELAT_FRA), fordi
#   avskrivningene da faller og forholdet ser hoeyere ut enn investeringene
#   tilsier. Offshore hviler derfor paa ett selskap per segment etter 2021,
#   og reaktiveringer hos de restrukturerte selskapene kommer ikke med.
# ---------------------------------------------------------------------------

import base64, json, os, re, time
import numpy as np
import pandas as pd
import requests

REPO, BRANCH = "frdmid/syklusbordet-data", "main"
UA = {"User-Agent": "Syklusbordet frode@h-k.no"}
FORMER = {"10-K", "20-F", "40-F", "10-K/A", "20-F/A"}

REN = {
    "0000046765": ("Helmerich & Payne", "land"),
    "0001163739": ("Nabors", "land"),
    "0001013605": ("Precision Drilling", "land"),
    "0001537028": ("Independence Contract Drilling", "land"),
    "0001133260": ("Union Drilling", "land"),
    "0001330849": ("Hercules Offshore", "grunt"),
    "0001594590": ("Paragon Offshore", "grunt"),
    "0001715497": ("Borr Drilling", "grunt"),
    "0000085408": ("Rowan", "grunt"),
    "0001451505": ("Transocean", "dyp"),
    "0000949039": ("Diamond Offshore", "dyp"),
    "0001517342": ("Pacific Drilling", "dyp"),
    "0001447382": ("Ocean Rig", "dyp"),
}
BLANDET = {
    "0000314808": "Valaris",
    "0001351413": "Seadrill",
    "0001737706": "Seadrill",
    "0000085408": "Rowan",
}
CAPEX = ["PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets",
         "PaymentsToAcquireOilAndGasPropertyAndEquipment", "PaymentsForCapitalImprovements",
         "PaymentsToAcquireMachineryAndEquipment", "PaymentsToAcquireOilAndGasEquipment",
         "PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities",
         "PurchaseOfPropertyPlantAndEquipment", "PaymentsForProceedsFromProductiveAssets"]
DDA = ["DepreciationDepletionAndAmortization", "DepreciationAndAmortization",
       "CostOfGoodsAndServicesSoldDepreciation", "CostOfServicesDepreciation",
       "DepreciationAndAmortisationExpense", "Depreciation", "DepreciationNonproduction",
       "DepreciationPropertyPlantAndEquipment"]
# Ny startbalanse etter konkurs (fresh start): alle aar fra og med
# restruktureringsaaret holdes utenfor, rene selskaper og segmenttall likt
# (Frodes beslutning 29.09.2026, regel A). Riggene skrives ned ved
# restruktureringen, saa avskrivningene etterpaa er kunstig lave og forholdet
# ser ut som vekst. Eksempel: Valaris' 15 flytere hadde 1,2 mrd. i bokfoert
# verdi og 60 mill. i avskrivninger i 2025, mot rundt 660 hos Transocean.
# Kilde for aarene: SECs fulltekstsoek etter "fresh start accounting" i
# aarsrapportene og XBRL-begrepene FreshStart* (29.09.2026). Transocean, Borr,
# Rowan, Ocean Rig og landselskapene hadde ingen treff.
UTELAT_FRA = {"Valaris": 2021, "Diamond Offshore": 2021, "Pacific Drilling": 2018,
              "Hercules Offshore": 2015, "Paragon Offshore": 2017}
SEG_KLASSE = [("dyp", r"floater|deepwater|drillship|semisub|midwater|ultra"),
              ("grunt", r"jack.?up|shallow")]
SEG_CAPEX = r":(SegmentExpenditureAdditionToLongLivedAssets|PaymentsToAcquirePropertyPlantAndEquipment|PaymentsToAcquireProductiveAssets|\w*CapitalExpenditure\w*)$"
SEG_DEP = r":(?!\w*(Accumulated|Deferred|Tax|Accelerated|Impairment))\w*Depreciation\w*$"


def _get(url):
    for _ in range(4):
        try:
            r = requests.get(url, headers=UA, timeout=120)
            if r.status_code == 429:
                time.sleep(5); continue
            return r
        except requests.RequestException:
            time.sleep(3)
    return None


def _serie(fakta, begreper):
    """Skjoetet serie: foerste begrep vinner et aar, de neste fyller hull."""
    ut, enh_valgt = {}, None
    for b in begreper:
        for tak in ("us-gaap", "ifrs-full"):
            for enh, pkt in ((fakta.get(tak, {}).get(b) or {}).get("units") or {}).items():
                if len(enh) != 3 or (enh_valgt and enh != enh_valgt):
                    continue
                best = {}
                for p in pkt:
                    if p.get("form") not in FORMER or not p.get("start"):
                        continue
                    if not 330 <= (pd.Timestamp(p["end"]) - pd.Timestamp(p["start"])).days <= 400:
                        continue
                    k = int(p["end"][:4])
                    if k not in best or p.get("accn", "") > best[k].get("accn", ""):
                        best[k] = p
                nye = {k: abs(float(v["val"])) for k, v in best.items() if k not in ut}
                if nye:
                    ut.update(nye); enh_valgt = enh
    return enh_valgt, pd.Series(ut, dtype=float).sort_index()


def rene(note=print):
    data = {}
    for cik, (navn, seg) in REN.items():
        r = _get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json")
        if r is None or r.status_code != 200:
            note(f"   {navn}: ingen XBRL-data"); continue
        f = r.json().get("facts", {})
        ec, cx = _serie(f, CAPEX)
        ed, dd = _serie(f, DDA)
        aar = cx.index.intersection(dd.index) if ec == ed else pd.Index([])
        if len(aar):
            aar = aar[[dd[a] >= 0.25 * dd[aar].median() and a < UTELAT_FRA.get(navn, 9999) for a in aar]]
        if len(aar) < 2:
            note(f"   {navn}: for faa aar"); continue
        data[cik] = {"navn": navn, "seg": seg, "enh": ec, "capex": cx[aar], "dda": dd[aar]}
        time.sleep(0.2)
    return data


def _aarsrapporter(cik):
    s = _get(f"https://data.sec.gov/submissions/CIK{cik}.json").json()
    blokker = [s["filings"]["recent"]]
    for f in s["filings"].get("files", []):
        r = _get(f"https://data.sec.gov/submissions/{f['name']}")
        if r is not None and r.status_code == 200:
            blokker.append(r.json())
    return sorted({(b["filingDate"][i], b["accessionNumber"][i]) for b in blokker
                   for i in range(len(b["form"])) if b["form"][i] in ("10-K", "20-F") and b["filingDate"][i] >= "2009"})


def _instans(cik, accn):
    base = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accn.replace('-', '')}"
    r = _get(base + "/index.json")
    if r is None or r.status_code != 200:
        return None
    navn = [x["name"] for x in r.json()["directory"]["item"]]
    kand = [n for n in navn if n.endswith("_htm.xml")] or \
           [n for n in navn if n.endswith(".xml") and not re.search(
               r"_(cal|def|lab|pre)\.xml$|FilingSummary|MetaLinks|defnref|^R\d+\.xml$", n)]
    if not kand:
        return None
    r = _get(base + "/" + kand[0])
    return None if r is None or r.status_code != 200 else r.text


def segmenter(note=print):
    """(klasse, cik, aar) -> {capex, dda}. Nyeste aarsrapport vinner."""
    ut = {}
    for cik, navn in BLANDET.items():
        for dato, accn in _aarsrapporter(cik):
            t = _instans(cik, accn)
            time.sleep(0.15)
            if not t:
                continue
            ctx = {}
            for m in re.finditer(r"<(?:xbrli:)?context id=\"([^\"]+)\">(.*?)</(?:xbrli:)?context>", t, re.S):
                b = m.group(2)
                st = re.search(r"startDate>([^<]+)<", b); en = re.search(r"endDate>([^<]+)<", b)
                dims = dict(re.findall(r"<xbrldi:explicitMember dimension=\"([^\"]+)\">([^<]+)<", b))
                seg = dims.get("us-gaap:StatementBusinessSegmentsAxis")
                andre = [d for d in dims if d not in ("us-gaap:StatementBusinessSegmentsAxis", "srt:ConsolidationItemsAxis")]
                if st and en and seg and not andre and \
                        330 <= (pd.Timestamp(en.group(1)) - pd.Timestamp(st.group(1))).days <= 400:
                    k = next((kl for kl, mo in SEG_KLASSE if re.search(mo, seg, re.I)), None)
                    if k:
                        ctx[m.group(1)] = (k, int(en.group(1)[:4]), seg)
            funn = {}
            for m in re.finditer(r"<([A-Za-z0-9\-]+:[A-Za-z0-9_]+)\b[^>]*?contextRef=\"([^\"]+)\"[^>]*>([^<]*)</\1>", t):
                if m.group(2) not in ctx:
                    continue
                felt = "capex" if re.search(SEG_CAPEX, m.group(1)) else "dda" if re.search(SEG_DEP, m.group(1)) else None
                if not felt:
                    continue
                try:
                    v = abs(float(m.group(3).strip()))
                except ValueError:
                    continue
                k, aar, seg = ctx[m.group(2)]
                funn.setdefault((k, aar), {}).setdefault(felt, {})[seg] = v
            for (k, aar), d in funn.items():
                if aar >= UTELAT_FRA.get(navn, 9999):
                    continue
                if "capex" in d and "dda" in d:
                    ut[(k, cik, aar)] = {"navn": navn, "capex": sum(d["capex"].values()), "dda": sum(d["dda"].values())}
        note(f"   {navn}: segmenttall for {len({a for (_, c, a) in ut if c == cik})} aar")
    return ut


def beregn(ren, seg):
    res = {}
    med_seg = {(v["navn"], a) for (_, c, a), v in seg.items()}
    for k in ("land", "grunt", "dyp"):
        rader = {}
        for d in ren.values():
            if d["seg"] != k:
                continue
            for a in d["capex"].index:
                if (d["navn"], int(a)) in med_seg:
                    continue
                r = rader.setdefault(int(a), {"capex": 0.0, "dda": 0.0, "selskaper": []})
                if d["enh"] == "USD":
                    r["capex"] += d["capex"][a]; r["dda"] += d["dda"][a]
                    r["selskaper"].append(d["navn"])
        for (kk, cik, a), d in seg.items():
            if kk != k or not d["dda"]:
                continue
            r = rader.setdefault(int(a), {"capex": 0.0, "dda": 0.0, "selskaper": []})
            r["capex"] += d["capex"]; r["dda"] += d["dda"]
            r["selskaper"].append(d["navn"] + " (segment)")
        df = pd.DataFrame({a: {"capex": r["capex"], "dda": r["dda"], "n": len(r["selskaper"]),
                               "selskaper": ", ".join(sorted(set(r["selskaper"])))}
                           for a, r in rader.items() if r["dda"]}).T.sort_index()
        df["forhold"] = df["capex"].astype(float) / df["dda"].astype(float)
        df["snitt5"] = df["forhold"].rolling(5, min_periods=3).mean()
        df["B2"] = ((1.4 - df["snitt5"]) / 0.8 * 100).clip(0, 100)
        res[k] = df
    return res


def til_json(res):
    ut = {"oppdatert": str(pd.Timestamp.now("UTC"))[:19],
          "metode": "Investeringer delt paa avskrivninger fra SEC. B2 = klipp((1,4 - femaarssnitt) / 0,8 * 100, 0, 100). "
                    "Rene selskaper pluss segmenttall fra blandede. Informasjon, ikke flagg.",
          "svakhet": "Aar etter ny startbalanse (Valaris og Diamond fra 2021, Pacific Drilling fra 2018) er holdt "
                     "utenfor: avskrivningene er ikke sammenlignbare. Etter 2021 hviler offshore paa ett selskap per "
                     "segment, og reaktiveringer hos de restrukturerte kommer ikke med.",
          "segmenter": {}}
    navn = {"land": "Land", "grunt": "Grunt vann (jackups)", "dyp": "Dypt vann (flytere)"}
    for k, df in res.items():
        b = df["B2"].dropna()
        sis = b.index[-1] if len(b) else df.index[-1]
        ut["segmenter"][k] = {
            "navn": navn[k], "aar_siste": int(sis),
            "B2_siste": None if not len(b) else round(float(b.iloc[-1]), 1),
            "forhold_siste": round(float(df.loc[sis, "forhold"]), 3),
            "snitt5_siste": None if pd.isna(df.loc[sis, "snitt5"]) else round(float(df.loc[sis, "snitt5"]), 3),
            "n_siste": int(df.loc[sis, "n"]), "selskaper_siste": df.loc[sis, "selskaper"],
            "aar": [int(a) for a in df.index], "forhold": [round(float(x), 3) for x in df["forhold"]],
            "B2": [None if pd.isna(x) else round(float(x), 1) for x in df["B2"]],
            "n": [int(x) for x in df["n"]]}
    return ut


def kjor(note=print):
    note("Rigg B: rene selskaper")
    ren = rene(note)
    note("Rigg B: segmenttall fra blandede selskaper")
    seg = segmenter(note)
    res = beregn(ren, seg)
    ut = til_json(res)
    for k, v in ut["segmenter"].items():
        note(f"   {k:5s} {v['aar_siste']}: forhold {v['forhold_siste']}, B2 {v['B2_siste']}, "
             f"{v['n_siste']} selskaper ({v['selskaper_siste']})")
    tok = os.environ.get("GITHUB_TOKEN")
    if os.environ.get("RIGG_UT"):
        json.dump(ut, open(os.environ["RIGG_UT"], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if tok:
        api = f"https://api.github.com/repos/{REPO}/contents/b_rigg.json"
        h = {"Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json"}
        g = requests.get(api, headers=h, params={"ref": BRANCH}, timeout=30)
        body = {"message": "b_rigg", "branch": BRANCH,
                "content": base64.b64encode(json.dumps(ut, ensure_ascii=False).encode()).decode()}
        if g.status_code == 200:
            body["sha"] = g.json().get("sha")
        requests.put(api, headers=h, json=body, timeout=60).raise_for_status()
        note("   publisert b_rigg.json")
    return ut


if __name__ == "__main__":
    kjor()
