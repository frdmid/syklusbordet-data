# ---------------------------------------------------------------------------
# Syklusbordet: shipping-innhenting
#
# Går gjennom hele Fearnleys-arkivet og trekker ut nybyggpris, annenhåndspris
# og ettårs timecharter per skipstype og uke.
#
# To maler, begge testet mot faktiske linjer:
#   Fearnpulse (aug 2023 og nyere): hvert felt på egen linje
#   Eldre mal  (til og med 2023):   navn og tall på samme linje
#
# Kjøringen tar 25 til 40 minutter første gang, rundt 300 MB. Den er
# gjenopptakbar: allerede hentede uker hoppes over, så avbrutt kjøring
# kan startes på nytt uten å miste noe.
#
# Kjøres av GitHub Actions. Token kommer fra miljøet.
# ---------------------------------------------------------------------------


import base64, io, json, logging, re, time
from collections import Counter, defaultdict
import pandas as pd
import requests, pdfplumber

logging.getLogger("pdfminer").setLevel(logging.ERROR)
try:
    from google.colab import userdata
    GITHUB_TOKEN = userdata.get("GITHUB_TOKEN")
except Exception:
    import os
    GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")   # GitHub Actions setter denne

REPO, BRANCH = "frdmid/syklusbordet-data", "main"
RAW = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}"
HSN = "https://www.hellenicshippingnews.com"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
MAKS = 400          # tak på antall rapporter per kjøring

SKIP = (r"VLCC|Suezmax|Aframax(?:\s*/\s*LR2)?|Product|LR1|LR2|MR|"
        r"Newcastlemax|Capesize|Kamsarmax|Panamax|Ultramax|Supramax|Handysize")


# =============================================================== parsere

def p_ny_nybygg(L):
    ut = {}
    try:
        s = next(i for i, l in enumerate(L) if re.fullmatch(r"Newbuilding", l, re.I))
        p = next(i for i in range(s, min(s + 25, len(L)))
                 if re.fullmatch(r"Prices", L[i], re.I))
    except StopIteration:
        return ut
    i = p + 1
    while i + 2 < len(L) and len(ut) < 14:
        navn = L[i]
        if not re.fullmatch(SKIP, navn, re.I):
            if re.fullmatch(r"\d{2}|Sale & Purchase|Market Brief", navn, re.I):
                break
            i += 1
            continue
        # Ta forste beloep som er stort nok til aa vere ein skipspris.
        # Endringskolonnen staar ofte forst og er $0 eller nokre faa millionar.
        pl = next((v for v in (float(m.group(1).replace(",", ""))
                               for m in (re.fullmatch(r"\$([\d.,]+)", b2)
                                         for b2 in L[i + 1:i + 4]) if m)
                   if v > 5), None)
        if pl is not None:
            ut[navn] = pl
            i += 3
        else:
            i += 1
    return ut


def p_ny_tc(L):
    ut = {}
    for i in range(len(L) - 2):
        if not re.fullmatch(SKIP, L[i], re.I):
            continue
        if not re.fullmatch(r"Modern|ECO|Scrubber|Eco/Scrubber", L[i + 1], re.I):
            continue
        m = re.fullmatch(r"\$([\d.,]+)", L[i + 2])
        if m:
            v = float(m.group(1).replace(",", ""))
            if v > 3000:
                ut[L[i]] = v
    return ut


def p_ny_sh(L):
    ut, sek = {}, None
    for l in L:
        if re.match(r"^(Dry|Wet)\s+5\s*yr\s*old\s+10\s*yr\s*old$", l, re.I):
            sek = l.split()[0].lower(); continue
        m = re.match(r"^([A-Za-z][\w /\-]*?)\s+\$([\d.]+)\s+\$([\d.]+)$", l)
        if m and sek:
            ut[m.group(1).strip()] = (float(m.group(2)), float(m.group(3)))
    return ut


def p_gammel(L):
    ut = {"nybygg": {}, "sh5": {}, "sh10": {}, "tc": {}}
    mal = None
    for l in L:
        if re.fullmatch(r"Newbuilding", l, re.I):                       mal = "nybygg"; continue
        if re.match(r"^(Dry|Wet)\s*\(5\s*yr\)", l, re.I):               mal = "sh5";   continue
        if re.match(r"^(Dry|Wet)\s*\(10\s*yr\)", l, re.I):              mal = "sh10";  continue
        if re.match(r"^1\s*Year\s*T/C\s*\(USD/Day\)", l, re.I):         mal = "tc";    continue
        if re.fullmatch(r"Sale & Purchase|Prices|Activity Levels", l, re.I): continue
        m = re.match(rf"^({SKIP})(?:\s*\(Modern\))?\s+\$([\d.,]+)\s+-?\$?[\d.,]+\s*$", l, re.I)
        if m and mal:
            ut[mal][m.group(1).strip()] = float(m.group(2).replace(",", ""))
    return ut


def les(txt):
    """Returnerer rader for en rapport. Prover begge malene."""
    L = [x.strip() for x in txt.split("\n") if x.strip()]
    sh, nb, tc = p_ny_sh(L), p_ny_nybygg(L), p_ny_tc(L)
    mal = "fearnpulse"
    if not (sh or nb or tc):
        g = p_gammel(L)
        sh = {k: (v, g["sh10"].get(k)) for k, v in g["sh5"].items()}
        nb, tc, mal = g["nybygg"], g["tc"], "eldre"
    felt = defaultdict(dict)
    for k, (a, b) in sh.items():
        felt[k]["sh5_musd"], felt[k]["sh10_musd"] = a, b
    for k, v in nb.items():
        felt[k]["nybygg_musd"] = v
    for k, v in tc.items():
        felt[k]["tc1y_usd_dag"] = v
    return mal, felt


# =========================================================== arkivet

def katalog():
    ut = {}
    for side in range(1, 40):
        r = requests.get(f"{HSN}/wp-json/wp/v2/media?search=Fearnleys&per_page=100"
                         f"&page={side}&_fields=date,source_url", headers=UA, timeout=60)
        if r.status_code != 200:
            break
        d = r.json()
        if not d:
            break
        for m in d:
            u = m.get("source_url", "")
            if u.lower().endswith(".pdf"):
                ut[m.get("date", "")[:10]] = u
        if len(d) < 100:
            break
        time.sleep(0.3)
    return ut


def eksisterende():
    try:
        r = requests.get(f"{RAW}/shipping.json", timeout=30)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return {"rader": [], "logg": {}}


def push(sti, tekst):
    api = f"https://api.github.com/repos/{REPO}/contents/{sti}"
    h = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}
    sha = None
    g = requests.get(api, headers=h, params={"ref": BRANCH}, timeout=30)
    if g.status_code == 200:
        sha = g.json().get("sha")
    body = {"message": f"oppdatert {sti}",
            "content": base64.b64encode(tekst.encode()).decode(), "branch": BRANCH}
    if sha:
        body["sha"] = sha
    requests.put(api, headers=h, json=body, timeout=90).raise_for_status()


# =========================================================== kjoring

print("1. Katalog og tidligere arbeid")
kat = katalog()
gammelt = eksisterende()
hatt = {r["dato"] for r in gammelt["rader"]}
nye = {d: u for d, u in kat.items() if d not in hatt}
print(f"   {len(kat)} rapporter i arkivet")
print(f"   {len(hatt)} datoer allerede hentet")
print(f"   {len(nye)} gjenstår\n")

print("2. Henter og parser")
rader, maler, feil = list(gammelt["rader"]), Counter(), []
for n, (dato, url) in enumerate(sorted(nye.items())[:MAKS], 1):
    try:
        b = requests.get(url, headers=UA, timeout=120).content
        with pdfplumber.open(io.BytesIO(b)) as pdf:
            t = "\n".join((s.extract_text() or "") for s in pdf.pages)
        mal, felt = les(t)
        if not felt:
            feil.append((dato, "ingen tabeller"))
            maler["tom"] += 1
        else:
            maler[mal] += 1
            for skip, v in felt.items():
                rader.append({"dato": dato, "skip": skip, "mal": mal, **v})
        if n % 20 == 0:
            print(f"   {n}/{min(len(nye), MAKS)}   {dato}   {len(rader)} rader totalt")
    except Exception as e:
        feil.append((dato, f"{type(e).__name__}: {str(e)[:40]}"))
    time.sleep(0.8)

print(f"\n   maler: {dict(maler)}")
print(f"   feilet: {len(feil)}")

print("\n3. Dekning")
df = pd.DataFrame(rader)
if len(df):
    df["aar"] = df["dato"].str[:4]
    for felt in ["nybygg_musd", "sh5_musd", "tc1y_usd_dag"]:
        if felt in df:
            per = df[df[felt].notna()].groupby("aar")["dato"].nunique()
            print(f"\n   {felt}, uker med data per år:")
            print("      " + "  ".join(f"{a}:{n}" for a, n in per.items()))
    print(f"\n   {df['dato'].nunique()} uker, {df['skip'].nunique()} skipstyper, {len(df)} rader")
    print(f"   spenn: {df['dato'].min()} til {df['dato'].max()}")

    siste = df[df["dato"] == df["dato"].max()]
    print(f"\n   Siste uke ({df['dato'].max()}):")
    for _, r in siste.iterrows():
        nb = r.get("nybygg_musd"); s5 = r.get("sh5_musd")
        par = f"{s5/nb:.2f}" if (pd.notna(nb) and pd.notna(s5) and nb) else "-"
        print(f"      {r['skip']:14s} nybygg {nb if pd.notna(nb) else '-':>7} "
              f"5år {s5 if pd.notna(s5) else '-':>7}  paritet {par}")

if GITHUB_TOKEN and rader:
    push("shipping.json", json.dumps(
        {"oppdatert": str(pd.Timestamp.utcnow())[:19], "rader": rader,
         "logg": {"maler": dict(maler), "feil": feil[:40]}}, ensure_ascii=False))
    print(f"\n   publisert: {len(rader)} rader til {REPO}/shipping.json")
elif not GITHUB_TOKEN:
    print("\n   GITHUB_TOKEN mangler, ingenting publisert")

print("\n" + "=" * 72)
print("Paritet over 1,0 betyr at et fem år gammelt skip koster mer enn et nytt.")
