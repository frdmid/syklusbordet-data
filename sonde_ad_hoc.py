# ---------------------------------------------------------------------------
# Sonde 3: finnes en kilde som gir FLERE AAR enn ESEF
#
# Sonde 2 svarte paa hovedspoersmaalet, og svaret var nedslaaende. ESEF fant
# ti av tretten selskaper, men ga bare fire til seks aarsrapporter, fra 2020
# eller 2021 og fram til i dag. Eramet hadde flest med 2020-2025, Atalaya
# faerrest med 2024-2025.
#
# Det er for kort. Overlevelsesporten C maaler mot selskapets verste
# driftskontantstrom i HELE historikken, og det var nettopp et femaarsvindu
# uten syklusbunn som ga feilen i september: 30 av 32 selskaper leste "aapen"
# fordi 2021 til 2025 var gode aar. ESEF-vinduet er det samme vinduet.
#
# For olje og tank ligger 2020 saa vidt inne, og 2020 var et ekte bunnaar for
# dem. For gruve er bunnen 2015 og 2016, og den er utenfor uansett.
#
# Denne sonden stiller ett spoersmaal: finnes det en gratis kilde som gir ti
# aar eller mer med aarlig driftskontantstrom, for borser utenfor USA. Svaret
# avgjor om ESEF er verdt aa bygge i det hele tatt.
#
# Fire representative tickere, en fra hver problembors:
#   NHY.OL   Oslo,   gruve og metall, bunn 2015-2016
#   GLEN.L   London, gruve, bunn 2015-2016
#   TOU.TO   Toronto, gass, bunn 2016 og 2020
#   NESN.SW  Zurich, utenfor baade ESEF og SEC
# Pluss AA (NYSE) som fasit: den vet vi C allerede klarer, med 12 aar.
#
# Kjores via valget "ad hoc" i Sonder. Skriver ingenting.
# ---------------------------------------------------------------------------

import json, re, time
import requests

TIMEOUT = 30
UAB = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                     "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
       "Accept": "application/json,text/plain,*/*"}

PROVER = [("NHY.OL",  "osl", "Norsk Hydro",  "gruve, bunn 2015-2016"),
          ("GLEN.L",  "lon", "Glencore",     "gruve, bunn 2015-2016"),
          ("TOU.TO",  "tsx", "Tourmaline",   "gass, bunn 2016 og 2020"),
          ("NESN.SW", "swx", "Nestle",       "utenfor ESEF og SEC"),
          ("AA",      "",    "Alcoa",        "fasit: SEC gir 12 aar")]


def get(url, **kw):
    h = kw.pop("headers", UAB)
    for i in range(3):
        try:
            r = requests.get(url, headers=h, timeout=kw.pop("timeout", TIMEOUT), **kw)
            if r.status_code in (429, 502, 503):
                time.sleep(3 * (i + 1)); continue
            return r
        except requests.RequestException:
            if i == 2:
                raise
            time.sleep(2 * (i + 1))
    raise RuntimeError("ga opp")


def aar_av(verdier):
    a = sorted({str(x)[:4] for x in verdier if re.match(r"^\d{4}", str(x))})
    return a


# =============================================== 1. Yahoo fundamentals-timeseries
# Et annet endepunkt enn quoteSummary, som svarte 401 i sonde 1. Dette har
# historisk ikke krevd cookie. Verdt aa prove for det er den eneste verten vi
# allerede vet er naabar fra denne maskinen.
print("1. Yahoo fundamentals-timeseries")
for tk, _, navn, hvorfor in PROVER:
    try:
        u = ("https://query2.finance.yahoo.com/ws/fundamentals-timeseries/v1/finance/"
             f"timeseries/{tk}?symbol={tk}&type=annualOperatingCashFlow"
             "&period1=536457600&period2=2000000000&merge=false")
        r = get(u)
        if r.status_code != 200:
            print(f"   nei   {tk:9} HTTP {r.status_code}"); continue
        res = (r.json().get("timeseries") or {}).get("result") or []
        rader = []
        for blokk in res:
            for k, v in blokk.items():
                if k.startswith("annual") and isinstance(v, list):
                    rader += [x.get("asOfDate") for x in v if isinstance(x, dict)]
        a = aar_av(rader)
        print(f"   {'ok  ' if a else 'nei '}  {tk:9} {len(a):2} aar"
              f"  {a[0] if a else '-'}..{a[-1] if a else '-'}   ({navn}, {hvorfor})")
    except Exception as e:
        print(f"   nei   {tk:9} {type(e).__name__} {str(e)[:50]}")
    time.sleep(0.6)


# ============================================================ 2. stockanalysis.com
# Dekker Oslo, London, Toronto og SIX, og viser normalt ti aar eller mer i
# nettleseren. Spoersmaalet er om tallene ligger i et endepunkt vi kan lese.
print("\n2. stockanalysis.com")
for tk, bors, navn, hvorfor in PROVER:
    base = tk.split(".")[0]
    sti = f"quote/{bors}/{base}" if bors else f"stocks/{base}"
    funnet = False
    for u in (f"https://stockanalysis.com/{sti}/financials/cash-flow-statement/__data.json",
              f"https://stockanalysis.com/api/symbol/{'s' if not bors else bors}/{base}/financials/cash-flow-statement"):
        try:
            r = get(u)
            if r.status_code != 200:
                print(f"   nei   {tk:9} {u.split('/')[-1][:34]:36} HTTP {r.status_code}")
                continue
            t = r.text
            a = aar_av(re.findall(r'"(\d{4})-\d{2}-\d{2}"', t) + re.findall(r'\b(19\d\d|20\d\d)\b', t))
            a = [x for x in a if 1995 <= int(x) <= 2026]
            har = "operatingCashFlow" in t or "ocf" in t.lower()
            print(f"   {'ok  ' if a and har else 'nei '}  {tk:9} {len(r.content)//1024:4} kB, "
                  f"{len(a):2} aarstall {a[0] if a else '-'}..{a[-1] if a else '-'}, "
                  f"kontantstromfelt: {'ja' if har else 'nei'}")
            funnet = funnet or (bool(a) and har)
            if funnet:
                break
        except Exception as e:
            print(f"   nei   {tk:9} {type(e).__name__} {str(e)[:50]}")
        time.sleep(0.6)


# ================================================== 3. SEC for alt som er notert i USA
# Sonde 2 viste at Cenovus ligger hos SEC under CVE. Her sjekkes hvor mange
# AAR den faktisk gir, og om resten av universet har samme mulighet.
print("\n3. SEC: hvor mange aar gir en 40-F-filer egentlig")
try:
    kart = get("https://www.sec.gov/files/company_tickers.json",
               headers={"User-Agent": "Syklusbordet frode@h-k.no"}).json()
    tick = {str(v["ticker"]).upper(): str(v["cik_str"]).zfill(10) for v in kart.values()}
    for t in ("CVE", "AA"):
        if t not in tick:
            print(f"   nei   {t} ikke i kartet"); continue
        r = get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{tick[t]}.json",
                headers={"User-Agent": "Syklusbordet frode@h-k.no"}, timeout=90)
        f = r.json().get("facts", {})
        aar = set()
        for tak in ("us-gaap", "ifrs-full"):
            for navn, d in f.get(tak, {}).items():
                if "OperatingActivities" not in navn:
                    continue
                for enhet in d.get("units", {}).values():
                    for x in enhet:
                        if x.get("form") in ("10-K", "20-F", "40-F") and x.get("fy"):
                            aar.add(int(x["fy"]))
        a = sorted(aar)
        print(f"   ok    {t:9} {len(a):2} aar  {a[0] if a else '-'}..{a[-1] if a else '-'}")
        time.sleep(0.4)
except Exception as e:
    print(f"   SEC feilet: {type(e).__name__} {str(e)[:60]}")

print("\n\nKONKLUSJON aa lete etter: gir noen rute ti aar eller mer utenfor USA.")
print("Gjor den ikke det, er ESEF det beste som finnes, og da maa C endres")
print("til aa si fra naar porten er maalt paa et for kort vindu.")
print("\nSend hele utskriften tilbake.")
