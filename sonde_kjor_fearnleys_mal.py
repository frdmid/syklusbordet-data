# ---------------------------------------------------------------------------
# sonde_kjor_fearnleys_mal: hvorfor gir 158 Fearnleys-rapporter fra 2020 til
# 2022 ingen tall
#
# shipping.py leser to maler: Fearnpulse (fra august 2023) og den eldre med
# navn og tall paa samme linje. Rapportene fra april 2020 til 2022 gir
# "ingen tabeller". Shipping-historikken har derfor et hull midt i, og A for
# shipping venter paa lengre historikk. Fylles hullet, gaar historikken
# sammenhengende fra mars 2019.
#
# Sonden henter et utvalg av de tomme rapportene og viser hva som faktisk
# staar i dem: tegn og bilder per side, de foerste linjene, og linjene rundt
# stikkordene parserne ser etter. Er teksten tom, er PDF-en et bilde og maa
# leses med tekstgjenkjenning. Den endrer ingenting.
# ---------------------------------------------------------------------------

import io, re, time, logging
import requests, pdfplumber

logging.getLogger("pdfminer").setLevel(logging.ERROR)
HSN = "https://www.hellenicshippingnews.com"
RAW = "https://raw.githubusercontent.com/frdmid/syklusbordet-data/main"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
STIKK = re.compile(r"Newbuild|5\s*yr|10\s*yr|T/C|Time\s*charter|VLCC|Suezmax|Aframax|Capesize|"
                   r"Kamsarmax|Panamax|Ultramax|Supramax|Handysize|Second\s*hand|Baltic", re.I)


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


print("1. Hvilke rapporter er tomme")
kat = katalog()
sj = requests.get(f"{RAW}/shipping.json", params={"cb": int(time.time())}, timeout=60).json()
har = {r["dato"] for r in sj["rader"]}
tomme = sorted(d for d in kat if d not in har)
print(f"   {len(kat)} i arkivet, {len(har)} datoer med tall, {len(tomme)} uten")
aar = {}
for d in tomme:
    aar[d[:4]] = aar.get(d[:4], 0) + 1
print(f"   uten tall per aar: {aar}")
if tomme:
    print(f"   foerste uten {tomme[0]}, siste uten {tomme[-1]}")
    # siste rapport MED tall foer hullet og foerste etter, for aa se overgangen
    foer = max((d for d in har if d < tomme[0]), default=None)
    etter = min((d for d in har if d > tomme[-1]), default=None)
    print(f"   siste med tall foer hullet {foer}, foerste etter {etter}")

utvalg = [tomme[int(i * (len(tomme) - 1) / 5)] for i in range(6)] if len(tomme) >= 6 else tomme
print(f"\n2. Utvalg: {', '.join(utvalg)}")
for dato in utvalg:
    url = kat[dato]
    print(f"\n=== {dato}  {url}")
    try:
        b = requests.get(url, headers=UA, timeout=120).content
        with pdfplumber.open(io.BytesIO(b)) as pdf:
            print(f"   {len(pdf.pages)} sider, {len(b)} byte")
            alle = []
            for i, s in enumerate(pdf.pages):
                t = s.extract_text() or ""
                print(f"   side {i + 1}: {len(t)} tegn, {len(s.images)} bilder, {len(s.chars)} tegnobjekter")
                alle += [(i + 1, x.strip()) for x in t.split("\n") if x.strip()]
            print("   foerste 25 linjer:")
            for sd, l in alle[:25]:
                print(f"      [{sd}] {l[:120]}")
            treff = [k for k, (sd, l) in enumerate(alle) if STIKK.search(l)]
            print(f"   {len(treff)} linjer med stikkord. De foerste 40, med linjen foer og etter:")
            vist = set()
            for k in treff[:40]:
                for j in (k - 1, k, k + 1):
                    if 0 <= j < len(alle) and j not in vist:
                        vist.add(j)
                        sd, l = alle[j]
                        print(f"      {'>' if j == k else ' '}[{sd}] {l[:120]}")
            # tabeller, i tilfelle tallene bare kommer ut som tabellceller
            for i, s in enumerate(pdf.pages[:4]):
                tab = s.extract_tables()
                if tab:
                    print(f"   side {i + 1}: {len(tab)} tabeller, foerste har {len(tab[0])} rader")
                    for rad in tab[0][:6]:
                        print("      " + " | ".join(str(c)[:16] for c in rad))
    except Exception as e:
        print(f"   {type(e).__name__}: {str(e)[:100]}")
    time.sleep(1)
