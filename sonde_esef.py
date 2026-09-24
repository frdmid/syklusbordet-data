# ---------------------------------------------------------------------------
# Sonde 2: kan ESEF gi nok AAR til overlevelsesporten C
#
# Runde 1 (24. september) svarte "12 av 20 treff i ESEF". Det tallet var feil,
# og feilen var min egen. Navnematchen strippet alt som ikke var a-z0-9, og et
# koreansk selskapsnavn ble da den tomme strengen. "glencore".startswith("")
# er sant, saa alle fem London-papirene matchet samme koreanske reisebyraa.
# Aker BP matchet "AKER ASA", som er morselskapet og et annet regnskap.
# Ekte treff i runde 1 var seks: DNO, Norsk Hydro, Hafnia, Okeanis, Boliden
# og Eramet.
#
# Runde 1 avklarte likevel to ting for godt:
#   Bronnoysund er en blindvei. Tre av seks norske ga treff, men bare ETT aar
#   (2025) og ingen kontantstromoppstilling i dataene. C trenger driftskontant-
#   strom aar for aar. Ruten er lukket, ikke delvis aapen.
#   Yahoo quoteSummary svarer 401 paa alt. Endepunktet krever nu cookie og
#   crumb. Merk at chart-endepunktet som priser.py bruker fortsatt virker; det
#   er bare regnskapsmodulene som er stengt.
#
# Denne runden svarer paa det som faktisk avgjoer: hvor mange AAR med
# driftskontantstrom ligger i ESEF. Mandatet gjelder regnskapsaar fra 2020, og
# hver aarsrapport har med fjoraaret som sammenligning, saa taket er trolig
# 2019 og framover. Er det taket, dekker ESEF 2020-krakket men ikke bunnen i
# 2015 og 2016, og da er porten aapen for oljeselskapene og blind for gruve.
# Det maa maales, ikke antas.
#
# Kjores manuelt fra Actions-fanen, valget "esef". Skriver ingenting.
# ---------------------------------------------------------------------------

import json, re, time
import requests

TIMEOUT = 40
UA = {"User-Agent": "Syklusbordet frode@h-k.no"}
API = "https://filings.xbrl.org/api"

MANGLER = [
    ("AKRBP.OL",  "Aker BP",           "Oslo",      "NO"),
    ("DNO.OL",    "DNO",               "Oslo",      "NO"),
    ("NHY.OL",    "Norsk Hydro",       "Oslo",      "NO"),
    ("HAFNI.OL",  "Hafnia",            "Oslo",      "NO"),
    ("OET.OL",    "Okeanis Eco Tankers","Oslo",     "NO"),
    ("2020.OL",   "2020 Bulkers",      "Oslo",      "NO"),
    ("GLEN.L",    "Glencore",          "London",    "GB"),
    ("ATYM.L",    "Atalaya Mining",    "London",    "GB"),
    ("MPE.L",     "M.P. Evans",        "London",    "GB"),   # reg.navn kan vaere "MP Evans"
    ("RE.L",      "REA Holdings",      "London",    "GB"),
    ("TMIP.L",    "Taylor Maritime Investments", "London", "GB"),
    ("BOL.ST",    "Boliden",           "Stockholm", "SE"),
    ("ERA.PA",    "Eramet",            "Paris",     "FR"),
]
# Kanadierne og sveitserne staar utenfor ESEF. For dem testes en annen ide:
# noen av dem er notert i USA under en annen ticker og filer 20-F eller 40-F.
SEC_ALT = {"CVE.TO": ["CVE"], "WCP.TO": ["WCPRF"], "TOU.TO": ["TRMLF"],
           "BIR.TO": ["BIREF"], "CS.TO": ["CSCCF"],
           "BARN.SW": ["BYCBF"], "NESN.SW": ["NSRGY", "NSRGF"]}


def get(url, **kw):
    h = kw.pop("headers", UA)
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


def norm(s):
    """Beholder bokstaver fra alle alfabeter, ikke bare a-z."""
    return re.sub(r"[^\w]", "", str(s).lower(), flags=re.UNICODE)

HALER = ("asa", "plc", "ab", "sa", "ag", "inc", "corp", "ltd", "limited",
         "group", "publ", "nv", "se", "oyj")
def kjerne(s):
    """Strippet navn: selskapsledd fjernet, gjentatt til ingenting mer gaar."""
    s = norm(s)
    endret = True
    while endret:
        endret = False
        for h in HALER:
            if s.endswith(h) and len(s) - len(h) >= 2:
                s, endret = s[:-len(h)], True
    return s

def likner(kandidat, sokt):
    """Likhet, ikke prefiks. Prefiks var det som gikk galt i runde 1.

    "aker" er et prefiks av "akerbp", men Aker ASA er morselskapet og et helt
    annet regnskap. "boliden" er et prefiks av "bolidenmineral", som er
    datterselskapet. Begge ville sluppet gjennom en prefiksregel, og begge
    ville gitt C feil tall uten aa si fra. Derfor kreves likhet etter at
    selskapsleddene er strippet. Bommer den, skriver sonden ut de naermeste
    kandidatene, og da retter jeg navnet i listen i stedet for aa lose opp
    regelen.
    """
    a, b = kjerne(kandidat), kjerne(sokt)
    return len(b) >= 3 and a == b


# =================================================== 1. finn enhetene i ESEF
print("1. ESEF: finner enhetene paa nytt, med rettet navnematch\n")
ENH = {}
for land in sorted({l for *_, l in MANGLER}):
    enh, url, side = {}, (f"{API}/filings?include=entity&filter[country]={land}"
                          f"&page[size]=500"), 0
    try:
        while url and side < 12:
            r = get(url)
            if r.status_code != 200:
                print(f"   {land}: HTTP {r.status_code}"); break
            j = r.json()
            for e in j.get("included", []):
                if e.get("type") == "entity":
                    enh[e.get("id")] = (e.get("attributes") or {}).get("name", "")
            url = (j.get("links") or {}).get("next"); side += 1
            time.sleep(0.4)
        print(f"   {land}: {len(enh)} enheter")
        ENH[land] = enh
    except Exception as e:
        print(f"   {land}: {type(e).__name__} {str(e)[:60]}")
        ENH[land] = {}

print()
FUNNET = {}
for tk, navn, bors, land in MANGLER:
    traff = [(i, n) for i, n in ENH.get(land, {}).items() if likner(n, navn)]
    if len(traff) == 1:
        FUNNET[tk] = traff[0]
        print(f"   ok    {tk:10} -> {traff[0][1]}")
    elif traff:
        FUNNET[tk] = traff[0]
        print(f"   FLERE {tk:10} -> {', '.join(n for _, n in traff[:4])}  (valgte forste)")
    else:
        nær = sorted(ENH.get(land, {}).values(),
                     key=lambda n: 0 if kjerne(navn)[:4] in kjerne(n) else 1)[:3]
        print(f"   nei   {tk:10} ingen match i {land}. Naermeste: {', '.join(nær)}")


# ================================== 2. hvor mange aar, og finnes kontantstrom
print("\n2. Aar per enhet, og om driftskontantstrom finnes i rapporten")
print("   Dette er spoersmaalet som avgjor alt. C maaler mot verste aar i")
print("   HELE historikken, og et femaarsvindu uten syklusbunn var nettopp")
print("   feilen som ble rettet i september.\n")

KONTANT = ("CashFlowsFromUsedInOperatingActivities",
           "NetCashFlowsFromUsedInOperatingActivities",
           "CashFlowsFromUsedInOperatingActivitiesContinuingOperations")

for tk, (eid, navn) in FUNNET.items():
    try:
        r = get(f"{API}/filings?filter[entity.id]={requests.utils.quote(str(eid))}&page[size]=100")
        if r.status_code != 200:
            print(f"   {tk:10} filings HTTP {r.status_code}"); continue
        data = r.json().get("data", [])
        if not data:
            print(f"   {tk:10} ingen filings"); continue
        attr = [d.get("attributes", {}) for d in data]
        if tk == list(FUNNET)[0]:
            print(f"   (feltene en filing har: {sorted(attr[0])})\n")
        aar = sorted({str(a.get("period_end", ""))[:4] for a in attr} - {"", "None"})
        jsonurl = next((a.get("json_url") for a in attr if a.get("json_url")), None)
        print(f"   {tk:10} {len(data):2} rapporter, aar {aar[0] if aar else '-'}..{aar[-1] if aar else '-'}"
              f"  ({', '.join(aar)})")
        # prov aa hente fakta fra den nyeste og se om kontantstrommen ligger der
        if jsonurl:
            u = jsonurl if jsonurl.startswith("http") else f"https://filings.xbrl.org{jsonurl}"
            rr = get(u, timeout=90)
            if rr.status_code == 200:
                t = rr.text
                traff = [k for k in KONTANT if k in t]
                per = len(set(re.findall(r'"(\d{4}-\d{2}-\d{2})"', t)))
                print(f"              rapportfil {len(rr.content)//1024} kB, "
                      f"kontantstromtag: {traff[0] if traff else 'IKKE FUNNET'}, "
                      f"{per} ulike datoer i filen")
            else:
                print(f"              rapportfil HTTP {rr.status_code}")
        else:
            print(f"              ingen json_url i metadataene")
    except Exception as e:
        print(f"   {tk:10} {type(e).__name__} {str(e)[:60]}")
    time.sleep(0.6)


# ============================ 3. finnes kanadierne og sveitserne hos SEC likevel
print("\n3. SEC under amerikansk ticker (Toronto og Zurich)")
try:
    kart = get("https://www.sec.gov/files/company_tickers.json").json()
    tick = {str(v["ticker"]).upper(): str(v["cik_str"]).zfill(10) for v in kart.values()}
    print(f"   SEC-kartet har {len(tick)} tickere")
    for tk, alts in SEC_ALT.items():
        funn = [(a, tick[a]) for a in alts if a in tick]
        if not funn:
            print(f"   nei   {tk:10} ingen av {alts} i SEC-kartet"); continue
        a, cik = funn[0]
        rr = get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json", timeout=90)
        if rr.status_code != 200:
            print(f"   nei   {tk:10} {a} -> CIK {cik}, companyfacts HTTP {rr.status_code}"); continue
        f = rr.json().get("facts", {})
        n = sum(len(v) for tak in ("us-gaap", "ifrs-full") for v in f.get(tak, {}).values())
        har = [k for tak in ("us-gaap", "ifrs-full") for k in f.get(tak, {})
               if "OperatingActivities" in k]
        print(f"   ok    {tk:10} {a} -> CIK {cik}, {n} fakta, "
              f"kontantstromtag: {har[0] if har else 'IKKE FUNNET'}")
        time.sleep(0.4)
except Exception as e:
    print(f"   SEC-kartet feilet: {type(e).__name__} {str(e)[:70]}")

print("\nSend hele utskriften tilbake.")
