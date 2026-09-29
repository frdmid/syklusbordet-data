# ---------------------------------------------------------------------------
# sonde_kjor_cotr: finnes posisjonstall (COT) for segmentene som mangler det?
#
# Frodes bestilling 29.09.2026. COT-feltet dekker i dag seks segmenter fra
# CFTC (brent, WTI, Henry Hub, gull, kobber, kakao). Denne sonden bygger
# ingenting. Den sjekker hva som lar seg hente fra GitHub Actions:
#   1  CFTC selv: finnes kontrakter for aluminium, nikkel, sink, bly, tinn,
#      jernmalm, kull, TTF, uran eller palmeolje i de to datasettene?
#   2  LME Commitments of Traders (COTR), xlsx per metall.
#   3  ICE Futures Europe, ukentlig COT som CSV per aar (COTHist).
#   4  SGX, COT for jernmalm (fra oktober 2024).
# For hver kilde: svarer den, hvor langt tilbake gaar den, og hvilke
# kategorier har den.
# ---------------------------------------------------------------------------

import io, re, time
import pandas as pd
import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept-Language": "en-GB,en;q=0.9"}
SEC_UA = {"User-Agent": "Syklusbordet frode@h-k.no"}


def get(url, **kw):
    try:
        r = requests.get(url, headers=kw.pop("headers", UA), timeout=kw.pop("timeout", 40), **kw)
        return r
    except Exception as e:
        print(f"      {type(e).__name__}: {str(e)[:80]}")
        return None


def vis(r, navn):
    if r is None:
        print(f"   {navn}: ingen svar"); return False
    print(f"   {navn}: {r.status_code}, {len(r.content):,} byte, {r.headers.get('content-type', '')[:40]}")
    return r.status_code == 200


# ============================================================ 1 CFTC
print("1. CFTC (Socrata), markedsnavn som matcher\n")
SOK = ["ALUMIN", "NICKEL", "ZINC", "LEAD", "TIN ", "IRON ORE", "COAL", "TTF", "URANIUM", "PALM"]
for ds, navn in (("72hh-3qpy", "Disaggregated futures"), ("6dca-aqww", "Legacy futures")):
    for s in SOK:
        r = get(f"https://publicreporting.cftc.gov/resource/{ds}.json",
                params={"$select": "market_and_exchange_names, min(report_date_as_yyyy_mm_dd) as fra, "
                                   "max(report_date_as_yyyy_mm_dd) as til, count(*) as uker",
                        "$where": f"upper(market_and_exchange_names) like '%{s}%'",
                        "$group": "market_and_exchange_names", "$limit": "50"},
                headers=SEC_UA, timeout=60)
        if r is None or r.status_code != 200:
            print(f"   {navn} {s.strip()}: {'ingen svar' if r is None else r.status_code}"); continue
        rader = r.json()
        for x in rader:
            print(f"   {navn:22s} {x['market_and_exchange_names'][:60]:60s} "
                  f"{str(x.get('fra'))[:10]} til {str(x.get('til'))[:10]}  {x.get('uker')} uker")
        if not rader:
            print(f"   {navn:22s} {s.strip()}: ingen")
        time.sleep(1.2)

# ============================================================ 2 LME
print("\n\n2. LME COTR\n")
base = "https://www.lme.com"
r = get(base + "/Market-data/Reports-and-data/Commitments-of-traders")
if vis(r, "oversiktssiden"):
    lenker = sorted(set(re.findall(r'href="([^"]*commitments-of-traders/[^"#?]+)"', r.text, re.I)))
    xl = sorted(set(re.findall(r'href="([^"]+\.xlsx[^"]*)"', r.text, re.I)))
    print(f"   {len(lenker)} undersider, {len(xl)} xlsx-lenker")
    for l in lenker[:30]:
        print(f"      {l}")
    for l in xl[:10]:
        print(f"      {l}")
else:
    print("   (siden svarte ikke med 200; ofte beskyttelse mot automatisk nedlasting)")
    if r is not None:
        print("   utdrag: " + re.sub(r"\s+", " ", r.text[:300]))
for metall in ("aluminium", "copper", "nickel", "zinc", "lead", "tin"):
    for sti in (f"/en/market-data/reports-and-data/commitments-of-traders/{metall}",
                f"/Market-data/Reports-and-data/Commitments-of-traders/{metall}"):
        r = get(base + sti)
        if vis(r, f"{metall} {sti[:4]}"):
            xl = sorted(set(re.findall(r'href="([^"]+\.xlsx[^"]*)"', r.text, re.I)))
            print(f"      {len(xl)} xlsx-lenker, foerste: {xl[:3]}")
            if xl:
                u = xl[0] if xl[0].startswith("http") else base + xl[0]
                f = get(u)
                if vis(f, "   foerste xlsx"):
                    try:
                        xls = pd.ExcelFile(io.BytesIO(f.content))
                        print(f"      ark: {xls.sheet_names[:6]}")
                        d = pd.read_excel(xls, xls.sheet_names[0], header=None)
                        print("      topp:\n" + d.head(18).to_string(max_colwidth=28)[:2500])
                    except Exception as e:
                        print(f"      kunne ikke lese: {type(e).__name__}: {str(e)[:80]}")
            break
        time.sleep(1)

# ============================================================ 3 ICE
print("\n\n3. ICE Futures Europe, COTHist per aar\n")
for aar in (2018, 2021, 2024, 2025, 2026):
    for u in (f"https://www.ice.com/publicdocs/futures/COTHist{aar}.csv",):
        r = get(u, timeout=90)
        if vis(r, f"COTHist{aar}.csv") and len(r.content) > 1000:
            try:
                d = pd.read_csv(io.StringIO(r.text), low_memory=False)
                kol = next((c for c in d.columns if "market" in c.lower() and "name" in c.lower()), d.columns[0])
                navn = sorted(d[kol].astype(str).str.strip().unique())
                print(f"      {len(d)} rader, {len(navn)} markeder, kolonner: {list(d.columns)[:8]}")
                treff = [n for n in navn if re.search(r"coal|newcastle|ttf|dutch|gas|alumin|iron", n, re.I)]
                print(f"      relevante: {treff[:20] or 'ingen'}")
                if aar == 2018:
                    print(f"      alle markeder: {navn[:40]}")
            except Exception as e:
                print(f"      kunne ikke lese: {type(e).__name__}: {str(e)[:80]}")
    time.sleep(1)
r = get("https://www.ice.com/report/122")
if vis(r, "ICE rapportside 122"):
    print("      lenker: " + ", ".join(sorted(set(re.findall(r'href="([^"]*(?:cot|COT|commit)[^"]*)"', r.text)))[:15]))

# ============================================================ 4 SGX
print("\n\n4. SGX, COT for jernmalm\n")
for u in ("https://www.sgx.com/derivatives/commitment-of-traders",
          "https://www.sgx.com/derivatives/products/commitment-of-traders",
          "https://www.sgx.com/research-education/derivatives/commitment-of-traders",
          "https://api2.sgx.com/content-api?queryId=commitment-of-traders"):
    r = get(u)
    if vis(r, u):
        treff = re.findall(r'href="([^"]+\.(?:xlsx|csv|pdf)[^"]*)"', r.text, re.I)
        print(f"      filer: {treff[:10]}")
        print("      utdrag: " + re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", r.text))[:300])
    time.sleep(1)

print("\nFerdig. Sonden bygger ingenting; den viser bare hva som kan hentes.")
