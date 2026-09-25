"""Bygger ship_*-segmentene fra shipping.json og legger dem i segments/.

Kjores rett etter shipping.py i den ukentlige arbeidsflyten. Henter
shipping.json gjennom GitHubs API og ikke gjennom raw-CDN-en, slik at den
garantert ser det steget foer nettopp skrev.

Deflaterer baade annenhaandsverdien og ankeret (nybyggpris) med amerikansk
KPI, slik som resten av bordet. A2 er et forhold mellom to priser fra samme
dato og er derfor upaavirket, men grafen ville ellers sammenliknet en
realpris med en nominell pris i samme rute.
"""

REPO, BRANCH = "frdmid/syklusbordet-data", "main"
MIRROR = "https://raw.githubusercontent.com/datasets/"

import base64, io, json, os, sys
import numpy as np, pandas as pd, requests

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
UA = {"User-Agent": "Mozilla/5.0 (compatible; Syklusbordet)"}
H = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}

META = {
 "ship_aframax": {
  "name": "Aframax/LR2 (5 år)",
  "group": "Shipping",
  "unit": "mill. USD",
  "status": "live",
  "value_label": "Verdi 5 år",
  "note": "Femårig annenhåndsverdi i millioner dollar, deflatert med amerikansk KPI til dagens nivå slik som resten av bordet. A2 er upåvirket, siden den er et forhold mellom to priser fra samme dato. Historikken rekker bare til 2023, så A1 er ikke beregnet. A2 er paritet mot nybyggpris: over 1,0 betyr at et fem år gammelt skip koster mer enn et nytt, noe som bare skjer når verftskøen er lang. Det er et topp-signal, ikke et bunn-signal.",
  "source": "Fearnleys ukerapport via Hellenic Shipping News",
  "source_url": "https://www.hellenicshippingnews.com/category/weekly-shipbrokers-reports/",
  "anchor_label": "Nybyggpris"
 },
 "ship_capesize": {
  "name": "Capesize (5 år)",
  "group": "Shipping",
  "unit": "mill. USD",
  "status": "live",
  "value_label": "Verdi 5 år",
  "note": "Femårig annenhåndsverdi i millioner dollar, deflatert med amerikansk KPI til dagens nivå slik som resten av bordet. A2 er upåvirket, siden den er et forhold mellom to priser fra samme dato. Historikken rekker bare til 2023, så A1 er ikke beregnet. A2 er paritet mot nybyggpris: over 1,0 betyr at et fem år gammelt skip koster mer enn et nytt, noe som bare skjer når verftskøen er lang. Det er et topp-signal, ikke et bunn-signal.",
  "source": "Fearnleys ukerapport via Hellenic Shipping News",
  "source_url": "https://www.hellenicshippingnews.com/category/weekly-shipbrokers-reports/",
  "anchor_label": "Nybyggpris"
 },
 "ship_handysize": {
  "name": "Handysize (5 år)",
  "group": "Shipping",
  "unit": "mill. USD",
  "status": "live",
  "value_label": "Verdi 5 år",
  "note": "Femårig annenhåndsverdi i millioner dollar, deflatert med amerikansk KPI til dagens nivå slik som resten av bordet. A2 er upåvirket, siden den er et forhold mellom to priser fra samme dato. Historikken rekker bare til 2023, så A1 er ikke beregnet. A2 er paritet mot nybyggpris: over 1,0 betyr at et fem år gammelt skip koster mer enn et nytt, noe som bare skjer når verftskøen er lang. Det er et topp-signal, ikke et bunn-signal.",
  "source": "Fearnleys ukerapport via Hellenic Shipping News",
  "source_url": "https://www.hellenicshippingnews.com/category/weekly-shipbrokers-reports/",
  "anchor_label": "Nybyggpris"
 },
 "ship_kamsarmax": {
  "name": "Kamsarmax (5 år)",
  "group": "Shipping",
  "unit": "mill. USD",
  "status": "live",
  "value_label": "Verdi 5 år",
  "note": "Femårig annenhåndsverdi i millioner dollar, deflatert med amerikansk KPI til dagens nivå slik som resten av bordet. A2 er upåvirket, siden den er et forhold mellom to priser fra samme dato. Historikken rekker bare til 2023, så A1 er ikke beregnet. A2 er paritet mot nybyggpris: over 1,0 betyr at et fem år gammelt skip koster mer enn et nytt, noe som bare skjer når verftskøen er lang. Det er et topp-signal, ikke et bunn-signal.",
  "source": "Fearnleys ukerapport via Hellenic Shipping News",
  "source_url": "https://www.hellenicshippingnews.com/category/weekly-shipbrokers-reports/",
  "anchor_label": "Nybyggpris"
 },
 "ship_suezmax": {
  "name": "Suezmax (5 år)",
  "group": "Shipping",
  "unit": "mill. USD",
  "status": "live",
  "value_label": "Verdi 5 år",
  "note": "Femårig annenhåndsverdi i millioner dollar, deflatert med amerikansk KPI til dagens nivå slik som resten av bordet. A2 er upåvirket, siden den er et forhold mellom to priser fra samme dato. Historikken rekker bare til 2023, så A1 er ikke beregnet. A2 er paritet mot nybyggpris: over 1,0 betyr at et fem år gammelt skip koster mer enn et nytt, noe som bare skjer når verftskøen er lang. Det er et topp-signal, ikke et bunn-signal.",
  "source": "Fearnleys ukerapport via Hellenic Shipping News",
  "source_url": "https://www.hellenicshippingnews.com/category/weekly-shipbrokers-reports/",
  "anchor_label": "Nybyggpris"
 },
 "ship_ultramax": {
  "name": "Ultramax (5 år)",
  "group": "Shipping",
  "unit": "mill. USD",
  "status": "live",
  "value_label": "Verdi 5 år",
  "note": "Femårig annenhåndsverdi i millioner dollar, deflatert med amerikansk KPI til dagens nivå slik som resten av bordet. A2 er upåvirket, siden den er et forhold mellom to priser fra samme dato. Historikken rekker bare til 2023, så A1 er ikke beregnet. A2 er paritet mot nybyggpris: over 1,0 betyr at et fem år gammelt skip koster mer enn et nytt, noe som bare skjer når verftskøen er lang. Det er et topp-signal, ikke et bunn-signal.",
  "source": "Fearnleys ukerapport via Hellenic Shipping News",
  "source_url": "https://www.hellenicshippingnews.com/category/weekly-shipbrokers-reports/",
  "anchor_label": "Nybyggpris"
 },
 "ship_vlcc": {
  "name": "VLCC (5 år)",
  "group": "Shipping",
  "unit": "mill. USD",
  "status": "live",
  "value_label": "Verdi 5 år",
  "note": "Femårig annenhåndsverdi i millioner dollar, deflatert med amerikansk KPI til dagens nivå slik som resten av bordet. A2 er upåvirket, siden den er et forhold mellom to priser fra samme dato. Historikken rekker bare til 2023, så A1 er ikke beregnet. A2 er paritet mot nybyggpris: over 1,0 betyr at et fem år gammelt skip koster mer enn et nytt, noe som bare skjer når verftskøen er lang. Det er et topp-signal, ikke et bunn-signal.",
  "source": "Fearnleys ukerapport via Hellenic Shipping News",
  "source_url": "https://www.hellenicshippingnews.com/category/weekly-shipbrokers-reports/",
  "anchor_label": "Nybyggpris"
 }
}

HANDLBAR = {"Oslo", "Stockholm", "K\u00f8benhavn", "London", "NYSE",
            "Nasdaq", "Toronto", "TSX Venture"}

SKIP = {"ship_vlcc": "VLCC", "ship_suezmax": "Suezmax", "ship_aframax": "Aframax",
        "ship_kamsarmax": "Kamsarmax", "ship_ultramax": "Ultramax",
        "ship_capesize": "Capesize", "ship_handysize": "Handysize"}

INSTR_KILDE = {}
try:
    from instrumenter import INSTR
    INSTR_KILDE = INSTR
except Exception as e:
    print(f"  instrumenter.py ikke lest: {type(e).__name__}")


def api_les(sti):
    r = requests.get(f"https://api.github.com/repos/{REPO}/contents/{sti}",
                     headers=H, params={"ref": BRANCH}, timeout=60)
    r.raise_for_status()
    return json.loads(base64.b64decode(r.json()["content"]))


def push(sti, tekst):
    api = f"https://api.github.com/repos/{REPO}/contents/{sti}"
    sha = None
    g = requests.get(api, headers=H, params={"ref": BRANCH}, timeout=30)
    if g.status_code == 200:
        sha = g.json().get("sha")
    body = {"message": f"oppdatert {sti}", "branch": BRANCH,
            "content": base64.b64encode(tekst.encode()).decode()}
    if sha:
        body["sha"] = sha
    requests.put(api, headers=H, json=body, timeout=60).raise_for_status()


print("1. Henter deflator og raadata")
c = pd.read_csv(io.StringIO(requests.get(
    MIRROR + "cpi-us/main/data/cpiai.csv", headers=UA, timeout=30).text))
c = c.iloc[:, :2]; c.columns = ["Date", "Index"]
c["Date"] = pd.to_datetime(c["Date"])
c = c.dropna().set_index("Date")["Index"]; c.index = c.index.to_period("M")
# Serien har hull. Oktober 2025 mangler helt, fordi KPI ikke ble publisert den
# maaneden. Uten utfylling ville et oppslag paa en manglende maaned falle
# tilbake paa dagens KPI og gi en maaned som ser udeflatert ut.
full = pd.period_range(c.index.min(), c.index.max(), freq="M")
hull = len(full) - len(c)
c = c.reindex(full).ffill()
BASE = float(c.iloc[-1])
print(f"   KPI til {c.index[-1]}, base {BASE:.3f}, {hull} hull fylt ut")

# Baltic Dry Index. Fearnleys publiserer bare tankrater, saa de fire
# torrlastsegmentene sto uten ratevariabel og maatte maales mot
# annenhaandsverdien alene. Den er en meglertaksasjon som beveger seg tregt,
# og maalt mot den korrelerer redere med sitt eget segment paa -0,06 (Star
# Bulk mot Capesize), -0,16 (mot Ultramax) og -0,14 (CMB.TECH mot Capesize).
# Maalt mot BDI over samme 41 maaneder: +0,42, +0,42 og +0,22. Fem av seks par
# ble bedre, og forbedringen er den samme som tank fikk av TC-ratene
# (DHT -0,18 mot verdien, +0,48 mot raten).
#
# BDI faar ingen egen A-skaar og staar ikke som eget segment. Testet som det:
# flagget ville staatt 27 % av alle maaneder og 60 % av 2010-tallet, altsaa en
# tilstand og ikke et signal, og 17 klynger ga median +22,9 % over tolv maaneder
# med p = 0,087. Det er bedre enn en tilfeldig kjopsdato (+0,5 %), men naar ikke
# terskelen raavareflagget satte (p = 0,014, sju av sju klynger positive).
TORRLAST = {"ship_capesize", "ship_kamsarmax", "ship_ultramax", "ship_handysize"}
BDI = {}
try:
    b = api_les("bdi.json")
    BDI = dict(zip(b["t"], b["nom"]))
    print(f"   BDI: {len(BDI)} maaneder, {b['hist_start']} til {b['siste_obs']}")
except Exception as e:
    print(f"   BDI utilgjengelig: {type(e).__name__} {str(e)[:60]}")

rader = api_les("shipping.json")["rader"]
rader = [dict(x, skip="Aframax" if x["skip"] == "Aframax / LR2" else x["skip"])
         for x in rader]
print(f"   {len(rader)} rader fra shipping.json")


def defl(v, p):
    """KPI framskrives flatt for maaneder etter siste KPI-punkt."""
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return None
    k = float(c.get(p)) if p in c.index else BASE
    return round(float(v) * BASE / k, 4)


def pctl(verdier, x):
    v = [a for a in verdier if a is not None]
    return None if not v else round(100.0 * sum(1 for a in v if a <= x) / len(v), 1)


# Raten over grafen. For torrlast er det BDI, som er felles for alle fire
# storrelsene, med persentil av realverdien mot hele historikken fra 1985.
# BDI ble 24. september 2026 testet som eget A-segment og forkastet (27 % av
# maanedene flagget, p=0,087), men som ratevariabel for torrlastaksjene holdt
# den (SBLK fra -0,06 til +0,42 i korrelasjon). Derfor staar den her som
# kontekst og ikke som skaar. Tank har bare TC 1 aar fra Fearnleys, med
# historikk fra 2023, som er for kort til en persentil.
BDI_FELT = None
if BDI:
    try:
        tt = sorted(BDI)
        rl = [defl(BDI[t], pd.Period(t, freq="M")) for t in tt]
        sis = tt[-1]
        i12 = tt.index(sis) - 12
        BDI_FELT = {
            "navn": "Baltic Dry Index", "t": sis, "verdi": round(BDI[sis], 0),
            "enhet": "indekspoeng",
            "endr12_pst": None if i12 < 0 else round(100 * (rl[-1] / rl[i12] - 1), 1),
            "pctl_alle": pctl(rl, rl[-1]), "pctl_10aar": pctl(rl[-120:], rl[-1]),
            "fra": tt[0], "basis": "realverdi, maanedssnitt",
            "kilde": "Baltic Exchange, skjoetet serie i bdi.json"}
        print(f"   BDI {sis}: {BDI[sis]:.0f}, persentil {BDI_FELT['pctl_alle']} "
              f"(fra {tt[0]}) / {BDI_FELT['pctl_10aar']} (10 aar)")
        alder = (pd.Period(pd.Timestamp.now(), freq="M") - pd.Period(sis, freq="M")).n
        if alder > 2:
            print(f"   ADVARSEL: BDI er {alder} maaneder gammel. bdi.json maa forlenges.")
    except Exception as e:
        print(f"   BDI-feltet feilet: {type(e).__name__} {str(e)[:60]}")

try:
    from signaler import trend
except Exception as e:
    trend = lambda s: None
    print(f"   signaler.py ikke lest: {type(e).__name__}")


# Kapitulasjon D og overlevelsesport C. Begge regnes allerede for
# skipssegmentene (d_kapitulasjon.json og c_overlevelse.json), men fram til
# 25.09.2026 ble de ikke lest her, saa skipssegmentene sto uten D og med
# porten "ukjent". Samme regler som i priser.py.
KAP, COV = {}, {}
try:
    KAP = api_les("d_kapitulasjon.json")
except Exception as e:
    print(f"   d_kapitulasjon.json ikke lest: {type(e).__name__}")
try:
    COV = api_les("c_overlevelse.json")
except Exception as e:
    print(f"   c_overlevelse.json ikke lest: {type(e).__name__}")


def berik_c_d(sid, d):
    g = (KAP.get("segmenter") or {}).get(sid)
    if g and g.get("D") is not None:
        d["scores"]["D"] = g["D"]
        d["d_detalj"] = {k: g.get(k) for k in ("D_aksjer", "tema", "tema_D", "spredning", "n")}
        for i in d.get("instrumenter", []):
            pp = (KAP.get("papirer") or {}).get(i["ticker"])
            if pp:
                i["D"], i["fall_pst"] = pp.get("D"), pp.get("fall_pst")
    cg = (COV.get("segmenter") or {}).get(sid) or {}
    selskap = COV.get("selskaper") or {}
    maalt = {i["ticker"]: i for i in cg.get("instrumenter", [])}
    egne = [maalt[i["ticker"]] for i in d.get("instrumenter", []) if i["ticker"] in maalt]
    if egne:
        if any(x["port"] == "aapen" for x in egne):   gate = "aapen"
        elif any(x["port"] == "trang" for x in egne): gate = "trang"
        else:                                         gate = "stengt"
        d["scores"]["gate"] = gate
        d["gate_detalj"] = {"aapne": sum(1 for x in egne if x["port"] == "aapen"), "malte": len(egne)}
        for i in d.get("instrumenter", []):
            x = maalt.get(i["ticker"])
            if x:
                i["port"], i["kvartaler"] = x["port"], x.get("kvartaler")
                sk = selskap.get(i["ticker"], {})
                i["bunnaar"], i["aar_historikk"] = sk.get("bunnaar"), sk.get("aar_historikk")


print("\n2. Bygger segmentene")
ut, feil = 0, 0
for sid, nokkel in SKIP.items():
    try:
        r = [x for x in rader if x["skip"] == nokkel]
        df = pd.DataFrame(r)
        if df.empty or "sh5_musd" not in df:
            raise ValueError(f"ingen annenhaandsverdi for {nokkel}")
        df["t"] = pd.PeriodIndex(pd.to_datetime(df["dato"]), freq="M")
        kol = [k for k in ("sh5_musd", "nybygg_musd", "tc1y_usd_dag") if k in df]
        g = df.groupby("t")[kol].mean()
        g = g[g["sh5_musd"].notna()]
        if len(g) < 6:
            raise ValueError(f"bare {len(g)} maaneder")
        serie = []
        for p, row in g.iterrows():
            nom = float(row["sh5_musd"])
            ank = row.get("nybygg_musd")
            ank = None if ank is None or (isinstance(ank, float) and np.isnan(ank)) else float(ank)
            tc = row.get("tc1y_usd_dag")
            tc = None if tc is None or (isinstance(tc, float) and np.isnan(tc)) else round(float(tc), 0)
            serie.append({"t": str(p), "tc1y": tc,
                          "bdi": BDI.get(str(p)) if sid in TORRLAST else None,
                          "nom": round(nom, 4), "real": defl(nom, p),
                          "p10": None, "p25": None, "p50": None, "p75": None,
                          "p90": None, "A": None,
                          "anchor": None if ank is None else round(ank, 4),
                          "anchor_real": defl(ank, p)})
        sis = next((x for x in reversed(serie) if x["anchor"]), None)
        tc = g["tc1y_usd_dag"].dropna() if "tc1y_usd_dag" in g else pd.Series(dtype=float)
        # Ratene er den variabelen aksjene faktisk folger. Annenhaandsverdien er
        # en treg meglertaksasjon og henger etter ratene med maaneder: maalt mot
        # verdien korrelerer redere negativt med sitt eget segment (DHT -0,13,
        # INSW -0,00), maalt mot raten blir de positive (0,24 og 0,20).
        d = dict(META[sid])
        d.update({
            "id": sid, "series": serie,
            "hist_start": serie[0]["t"], "last_obs": serie[-1]["t"],
            "last_nom": serie[-1]["nom"], "last_real": serie[-1]["real"],
            "tc1y_siste": None if tc.empty else round(float(tc.iloc[-1]), 1),
            "rate_navn": "Baltic Dry Index" if sid in TORRLAST else "TC 1 år",
            "bdi_siste": next((x["bdi"] for x in reversed(serie) if x["bdi"]), None),
            "rate": BDI_FELT if sid in TORRLAST else (None if tc.empty else {
                "navn": "TC 1 år", "t": str(tc.index[-1]), "verdi": round(float(tc.iloc[-1]), 0),
                "enhet": "USD/dag",
                "endr12_pst": None if (tc.index[-1] - 12) not in tc.index else round(100 * (tc.iloc[-1] / tc[tc.index[-1] - 12] - 1), 1),
                "pctl_alle": None, "pctl_10aar": None, "fra": str(tc.index[0]),
                "basis": "nominell, maanedssnitt",
                "kilde": "Fearnleys ukerapport"}),
            "scores": {"A": None, "Ad": None, "Ar": None, "flagg": False,
                       "flagg_styrke": 0,
                       "A2": None if not sis else round(sis["nom"] / sis["anchor"], 3),
                       "B": None, "D": None, "S": None,
                       "gate": "ukjent", "months_in_zone": 0}})
        t = trend(serie)
        if t:
            d["trend"] = t
        rr = INSTR_KILDE.get(sid)
        if rr:
            d["instrumenter"] = [
                {"ticker": tk, "bors": b, "navn": nv, "type": ty,
                 "kommentar": km.lstrip("-").strip(),
                 "omvendt": km.strip().startswith("-"),
                 "handlbar": b in HANDLBAR}
                for tk, b, nv, ty, km in rr]
        berik_c_d(sid, d)
        if GITHUB_TOKEN:
            push(f"segments/{sid}.json", json.dumps(d, ensure_ascii=False))
        a, bx = serie[0], serie[-1]
        print(f"   {sid:16s} {len(serie):>3} mnd  {a['t']} nom {a['nom']:>7} "
              f"real {a['real']:>9}   {bx['t']} nom {bx['nom']:>7} real {bx['real']:>9}   "
              f"A2={d['scores']['A2']} D={d['scores']['D']} C={d['scores']['gate']}")
        ut += 1
    except Exception as e:
        feil += 1
        print(f"   {sid:16s} FEIL {type(e).__name__}: {str(e)[:70]}")

print(f"\n{ut} segment skrevet, {feil} feilet")
if feil and not ut:
    sys.exit("Ingen shipping-segment kunne bygges.")
