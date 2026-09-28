# ---------------------------------------------------------------------------
# sonde_kjor_b_jernmalm: capex og avskrivninger fra rene jernmalmprodusenter
#
# Frodes beslutning 26.09.2026: tilbudsskaaren B for jernmalm skal bygges fra
# aarsrapportene til de rene produsentene, fordi SEC-tallene for Vale var gale
# og BHP og Rio er for diversifiserte (se tilbud_b.py). Denne sonden finner
# rapportene og skriver ut linjene med investeringer og avskrivninger, med
# side, slik at tallene kan leses av for haand og legges i b_manuell.json.
# Sonden endrer ingenting.
#
#   Fortescue (FMG)   ren jernmalm, USD, regnskapsaar til 30. juni
#   Kumba (KIO)       ren jernmalm, rand, kalenderaar
#   Champion (CIA)    rent hoeygradig konsentrat, CAD, regnskapsaar til 31. mars
#   Vale              jernmalmsegmentet (Ferrous minerals, fra 2020 Iron Ore
#                     Solutions), USD, fra 20-F hos SEC
#
# Det som skal leses: "Payments for property, plant and equipment" (eller
# tilsvarende) og "Depreciation and amortisation" for konsernet, begge aar i
# hver rapport, slik at hvert aar kan kontrolleres mot to rapporter.
# ---------------------------------------------------------------------------

import io, json, re, subprocess, sys, time
import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
SEC_UA = {"User-Agent": "Syklusbordet frode@h-k.no"}

try:
    import pymupdf as fitz  # PyMuPDF, mye raskere enn pdfplumber paa store rapporter
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "pymupdf"], check=False)
    try:
        import pymupdf as fitz
    except ImportError:
        fitz = None
if fitz is None:
    import pdfplumber

NOKKEL = re.compile(r"(payments? for|purchases? of|acquisition of|additions to|investment in)\s+(property|mine|mining|capital)"
                    r"|capital expenditure|sustaining capital|expansion capital"
                    r"|depreciation|amortisation|amortization|depletion", re.I)
AAR = re.compile(r"\b(20[0-2]\d)\b")
TALL = re.compile(r"\(?\d[\d ,.]*\)?")


def sider(b):
    if fitz is not None:
        with fitz.open(stream=b, filetype="pdf") as d:
            for i, p in enumerate(d):
                yield i + 1, p.get_text()
    else:
        with pdfplumber.open(io.BytesIO(b)) as d:
            for i, p in enumerate(d.pages):
                yield i + 1, p.extract_text() or ""


def les_rapport(navn, url, maks=45):
    try:
        r = requests.get(url, headers=UA, timeout=180)
    except Exception as e:
        print(f"   {navn}: {type(e).__name__}"); return
    if r.status_code != 200 or r.content[:4] != b"%PDF":
        print(f"   {navn}: HTTP {r.status_code}, ikke PDF"); return
    print(f"\n   === {navn}  ({len(r.content) // 1000} kB)  {url}")
    n = 0
    for s, tekst in sider(r.content):
        linjer = [l.strip() for l in tekst.split("\n") if l.strip()]
        # bare sider som ser ut som oppstillinger: kontantstroem eller resultat
        oppst = re.search(r"cash flows? (from|used in) investing|statement of cash flows|"
                          r"income statement|statement of (profit|comprehensive)|segment", tekst, re.I)
        if not oppst:
            continue
        hode = next((l for l in linjer if len(AAR.findall(l)) >= 2), "")
        treff = []
        for i, l in enumerate(linjer):
            if NOKKEL.search(l):
                # tallene staar ofte paa egne linjer rett etter teksten
                tall = []
                for x in linjer[i + 1:i + 6]:
                    if not TALL.fullmatch(x.replace("US$", "").strip()):
                        break
                    tall.append(x)
                tall = " | ".join(tall)
                treff.append(f"{l[:110]}{'   -> ' + tall if tall else ''}")
        if treff:
            print(f"      s. {s}   [{hode[:80]}]")
            for t in treff[:8]:
                print(f"         {t}")
                n += 1
        if n >= maks:
            print("      (stopper, nok linjer)"); break


def pdf_lenker(side_url, moenster):
    try:
        html = requests.get(side_url, headers=UA, timeout=60).text
    except Exception as e:
        print(f"   {side_url}: {type(e).__name__}"); return []
    ut = []
    for u in re.findall(r'href="([^"]+\.pdf[^"]*)"', html, re.I):
        if re.search(moenster, u, re.I):
            if u.startswith("/"):
                base = re.match(r"https?://[^/]+", side_url).group(0)
                u = base + u
            ut.append(u)
    return list(dict.fromkeys(ut))


# ---------------------------------------------------------------- Fortescue
print("1. Fortescue\n")
fmg = []
for s in ["https://investors.fortescue.com/en/results-and-operational-performance",
          "https://investors.fortescue.com/en/announcements-and-reports",
          "https://www.fortescue.com/en/investors/reports"]:
    l = pdf_lenker(s, r"annual[-_ ]?report|full[-_ ]?year|financial[-_ ]?report")
    print(f"   {s}: {len(l)} lenker")
    fmg += l
fmg = [u for u in dict.fromkeys(fmg) if not re.search(r"sustainab|climate|modern[-_ ]slavery|tax", u, re.I)]
for u in fmg[:20]:
    print(f"      {u}")
for u in fmg[:16]:
    les_rapport("FMG", u)
    time.sleep(1)

# -------------------------------------------------------------------- Kumba
print("\n\n2. Kumba\n")
kio = []
for aar in range(2025, 2008, -1):
    l = pdf_lenker(f"https://www.angloamericankumba.com/investors/annual-reporting/reports-archive/{aar}",
                   r"financial[-_ ]?statement|afs")
    if l:
        print(f"   arkiv {aar}: {len(l)} lenker")
    kio += l
    time.sleep(0.5)
kio += pdf_lenker("https://www.angloamericankumba.com/investors/annual-reporting", r"financial[-_ ]?statement|afs")
kio = list(dict.fromkeys(kio))
for u in kio[:20]:
    print(f"      {u}")
for u in kio[:16]:
    les_rapport("KIO", u)
    time.sleep(1)

# ----------------------------------------------------------------- Champion
print("\n\n3. Champion Iron\n")
cia = pdf_lenker("https://www.championiron.com/investors/financial-regulatory-reports/",
                 r"fs|financial[-_ ]?statement|annual[-_ ]?report")
cia = [u for u in cia if re.search(r"fy20\d\d|annual|20\d\d-0[5-6]", u, re.I)
       and not re.search(r"q[1-3]|half|interim|aif|mda|md-a", u, re.I)]
for u in cia[:15]:
    print(f"      {u}")
for u in cia[:10]:
    les_rapport("CIA", u)
    time.sleep(1)

# --------------------------------------------------------------------- Vale
print("\n\n4. Vale, jernmalmsegmentet i 20-F\n")
try:
    sub = requests.get("https://data.sec.gov/submissions/CIK0000917851.json", headers=SEC_UA, timeout=60).json()
    rec = sub["filings"]["recent"]
    filer = [(rec["filingDate"][i], rec["accessionNumber"][i], rec["primaryDocument"][i])
             for i in range(len(rec["form"])) if rec["form"][i] == "20-F"]
    print(f"   {len(filer)} 20-F i den nyere listen")
    for dato, acc, dok in filer[:12]:
        url = f"https://www.sec.gov/Archives/edgar/data/917851/{acc.replace('-', '')}/{dok}"
        try:
            html = requests.get(url, headers=SEC_UA, timeout=120).text
        except Exception as e:
            print(f"   {dato}: {type(e).__name__}"); continue
        tekst = re.sub(r"&nbsp;|&#160;", " ", html)
        tekst = re.sub(r"</t[dh]>", " | ", tekst, flags=re.I)
        tekst = re.sub(r"</tr>", "\n", tekst, flags=re.I)
        tekst = re.sub(r"<[^>]+>", "", tekst)
        rader = [re.sub(r"[ |]{2,}", " | ", r).strip(" |") for r in tekst.split("\n")]
        print(f"\n   === Vale 20-F levert {dato}")
        n = 0
        for i, r in enumerate(rader):
            if re.search(r"(iron ore solutions|ferrous minerals|iron ore)\b", r, re.I) and \
               re.search(r"capital expenditure|investments|depreciation|amortization|depletion", " ".join(rader[max(0, i - 3):i + 1]), re.I) \
               and len(re.findall(r"\d", r)) >= 4:
                print(f"      {' / '.join(x[:90] for x in rader[max(0, i - 2):i + 1])[:300]}")
                n += 1
                if n >= 14:
                    break
        time.sleep(0.5)
except Exception as e:
    print(f"   FEIL {type(e).__name__}: {str(e)[:100]}")

print("\nSend utskriften til Claude. Tallene leses av for haand til b_manuell.json.")
