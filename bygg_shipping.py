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
            "scores": {"A": None, "Ad": None, "Ar": None, "flagg": False,
                       "flagg_styrke": 0,
                       "A2": None if not sis else round(sis["nom"] / sis["anchor"], 3),
                       "B": None, "D": None, "S": None,
                       "gate": "ukjent", "months_in_zone": 0}})
        rr = INSTR_KILDE.get(sid)
        if rr:
            d["instrumenter"] = [
                {"ticker": tk, "bors": b, "navn": nv, "type": ty,
                 "kommentar": km.lstrip("-").strip(),
                 "omvendt": km.strip().startswith("-"),
                 "handlbar": b in HANDLBAR}
                for tk, b, nv, ty, km in rr]
        if GITHUB_TOKEN:
            push(f"segments/{sid}.json", json.dumps(d, ensure_ascii=False))
        a, bx = serie[0], serie[-1]
        print(f"   {sid:16s} {len(serie):>3} mnd  {a['t']} nom {a['nom']:>7} "
              f"real {a['real']:>9}   {bx['t']} nom {bx['nom']:>7} real {bx['real']:>9}   "
              f"A2={d['scores']['A2']}")
        ut += 1
    except Exception as e:
        feil += 1
        print(f"   {sid:16s} FEIL {type(e).__name__}: {str(e)[:70]}")

print(f"\n{ut} segment skrevet, {feil} feilet")
if feil and not ut:
    sys.exit("Ingen shipping-segment kunne bygges.")
