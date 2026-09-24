# ---------------------------------------------------------------------------
# Sonde 4: knekk stockanalysis.com, eller slaa fast at den ikke lar seg knekke
#
# Utgangspunktet er en innsikt som endrer problemet. C trenger ikke femten aar
# med tall. Den trenger selskapets VERSTE driftskontantstrom noensinne, og det
# er ett tall og ett aarstall per selskap som aldri endrer seg. Cenovus sitt er
# 273 millioner fra 2020, og det staar fast uansett hva som skjer framover.
# Resten av skaaren, kontanter og renter, er ferske tall som ESEF og Yahoos
# fireaarsvindu gir uten problemer.
#
# Saa oppgaven er ikke en loepende innhenting. Den er aa banke ett tall per
# selskap, en gang, med kilde. Samme monster som bdi_hist.json og
# uran_reserve.csv, som begge loste like fastlaaste problemer.
#
# Og listen er kortere enn jeg trodde. Bare fem segmenter mangler port, og de
# henger paa aatte selskaper:
#   brent      DNO.OL, AKRBP.OL
#   kobber     CS.TO, ATYM.L
#   nikkel     ERA.PA, GLEN.L
#   tinn       GLEN.L
#   palmeolje  MPE.L, RE.L
#
# Sonde 3 provde stockanalysis.com med gjettede URL-er og fikk 18 kB tilbake.
# Det var ikke et svar, det var en daarlig test. Nettstedet viser ti aar med
# kontantstrom for Oslo, London og Toronto i nettleseren, gratis. Finnes tallene
# i et endepunkt vi kan lese, loser det alle nitten selskapene og ikke bare de
# aatte.
#
# Denne sonden gjetter ikke. Den henter den vanlige HTML-siden, skriver ut hva
# den faktisk inneholder, og lar meg se strukturen. Deretter kan jeg skrive
# uttrekket mot noe som finnes.
#
# Kjores via valget "ad hoc" i Sonder. Skriver ingenting.
# ---------------------------------------------------------------------------

import json, re, time
import requests

TIMEOUT = 35
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
      "Accept-Language": "en-US,en;q=0.9"}

# ticker hos stockanalysis, borskode, hvorfor vi trenger den
MAAL = [("AKRBP", "osl", "brent"),
        ("GLEN",  "lon", "nikkel og tinn"),
        ("CS",    "tsx", "kobber"),
        ("ERA",   "epa", "nikkel")]


def get(url, **kw):
    for i in range(3):
        try:
            r = requests.get(url, headers=UA, timeout=TIMEOUT, **kw)
            if r.status_code in (429, 502, 503):
                time.sleep(4 * (i + 1)); continue
            return r
        except requests.RequestException as e:
            if i == 2:
                raise
            time.sleep(2 * (i + 1))
    raise RuntimeError("ga opp")


def kikk(navn, url):
    """Henter og skriver ut nok til at strukturen kan leses, ikke bare ok/nei."""
    try:
        r = get(url)
    except Exception as e:
        print(f"      {navn:26} {type(e).__name__} {str(e)[:50]}")
        return None
    t = r.text if r.status_code == 200 else ""
    aar = sorted({int(x) for x in re.findall(r"\b(20[01]\d|202\d)\b", t)} & set(range(2005, 2027)))
    print(f"      {navn:26} HTTP {r.status_code}  {len(r.content)//1024:5} kB  "
          f"type={r.headers.get('content-type','?')[:24]}")
    if not t:
        return None
    markorer = {
        "operatingCashFlow": "operatingCashFlow" in t,
        "ocf-felt":          bool(re.search(r'"(ocf|operating_cash_flow|cashFlowOps)"', t)),
        "__sveltekit":       "__sveltekit" in t or "sveltekit" in t.lower(),
        "json-script":       'type="application/json"' in t,
        "tabellrad <tr>":    t.count("<tr") ,
    }
    print(f"         markorer: " + ", ".join(
        f"{k}={v}" for k, v in markorer.items()))
    print(f"         aarstall i sida: {len(aar)}  {aar[:3]}..{aar[-3:] if len(aar)>3 else ''}")
    return t


print("1. stockanalysis.com: hva ligger faktisk paa sida\n")
for tk, bors, hvorfor in MAAL:
    print(f"   {tk}.{bors}   ({hvorfor})")
    base = f"https://stockanalysis.com/quote/{bors}/{tk}"
    html = kikk("HTML, kontantstrom", f"{base}/financials/cash-flow-statement/")
    kikk("__data.json", f"{base}/financials/cash-flow-statement/__data.json")
    kikk("HTML + range=10Y", f"{base}/financials/cash-flow-statement/?p=annual&range=10Y")

    # Er tallene i sida, saa finn dem. Vi leter etter aarsrader med tall.
    if html:
        # stockanalysis legger ofte dataene i et script-tag som JSON
        blokker = re.findall(r'<script[^>]*>(.{200,}?)</script>', html, re.S)
        med_tall = [b for b in blokker if "ash" in b and re.search(r"\d{4}-\d{2}-\d{2}|20\d\d", b)]
        print(f"         script-blokker: {len(blokker)}, av dem med kontantstromord: {len(med_tall)}")
        if med_tall:
            b = max(med_tall, key=len)
            print(f"         storste slik blokk: {len(b)} tegn. Utdrag:")
            print("         " + b[:300].replace("\n", " "))
        # og let etter selve begrepet i klartekst
        for nokkel in ("Operating Cash Flow", "Cash from Operations", "operatingCashFlow"):
            i = html.find(nokkel)
            if i >= 0:
                print(f"         '{nokkel}' funnet ved tegn {i}. Kontekst:")
                print("         " + html[i:i + 260].replace("\n", " "))
                break
    print()
    time.sleep(1.2)


# ------------------------------------------------------------------ reserveruter
print("\n2. To andre generelle kilder, kort test")
for navn, url in [
    ("stockanalysis API v2",
     "https://stockanalysis.com/api/screener/s/f?m=marketCap&s=desc&c=no,s,n&cn=10&f=exchange-is-osl"),
    ("wisesheets/simfin-stil",
     "https://backend.simfin.com/api/v3/companies/general/compact?ticker=AKRBP"),
]:
    print(f"   {navn}")
    kikk("", url)
    time.sleep(1)


print("""

HVA JEG SER ETTER
   Ligger aarstallene og kontantstrommen i sida eller i et endepunkt, kan jeg
   skrive uttrekket og lose alle nitten selskapene.
   Gjor de ikke det, er svaret at ingen gratis generell kilde dekker disse
   borsene, og da henter jeg de aatte tallene fra selskapenes egne
   noekkeltallsoversikter i staden. Aatte oppslag, en gang, med kilde per linje.

Send hele utskriften tilbake.""")
