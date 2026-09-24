# ---------------------------------------------------------------------------
# Sonde: hvor finnes regnskapstall for de 20 aksjene SEC ikke dekker
#
# Overlevelsesporten C leser SEC XBRL. Etter instrumentbyttet 22. september er
# 23 av 43 aksjer dekket. De 20 andre ligger paa Oslo, London, Toronto, Zurich,
# Stockholm og Paris, og sju segmenter staar derfor helt uten port: brent, wti,
# gull, kobber, nikkel, tinn og palmeolje.
#
# Denne sonden bygger ingenting. Den svarer paa ett spoersmaal per rute: hvor
# mange av de 20 gir den treff, og hvor mange AAR med driftskontantstrom faar
# vi ut. Aarstallet er det som avgjoer. C maaler mot selskapets verste aar i
# HELE historikken, og det var nettopp den feilen som ble rettet i september:
# med et femaarsvindu laa ingen syklusbunn inne, og 30 av 32 selskaper leste
# "aapen". Fire aar er derfor ikke en halv losning, det er ingen losning.
#
# Ruter som testes:
#   1. filings.xbrl.org   ESEF-registeret. Borsnoterte i EOS har vaert paalagt
#                         aa rapportere i ESEF siden 2020, i samme ifrs-full-
#                         taksonomi som overlevelse_c.py allerede leser. Dekker
#                         i prinsippet Oslo, Stockholm og Paris. Zurich er ikke
#                         EOS og faller utenfor.
#   2. Bronnoysund        Regnskapsregisteret. Bare norske. Dokumentasjonen
#                         lover ti aar, repoets egne notater sier siste aar.
#                         Det maa avklares, ikke antas.
#   3. Yahoo              quoteSummary gir fire aar for alle borser. Tas med
#                         som gulv, slik at vi vet hva den daarligste ruten gir.
#
# Kjores manuelt fra Actions-fanen. Skriver ingenting, printer alt.
# ---------------------------------------------------------------------------

import json, re, time
import requests

TIMEOUT = 30
UA = {"User-Agent": "Syklusbordet frode@h-k.no"}
UAB = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                     "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}

# ticker, selskapsnavn slik det staar i regnskapene, bors, landkode
MANGLER = [
    ("AKRBP.OL",  "Aker BP ASA",                 "Oslo",      "NO"),
    ("DNO.OL",    "DNO ASA",                     "Oslo",      "NO"),
    ("NHY.OL",    "Norsk Hydro ASA",             "Oslo",      "NO"),
    ("HAFNI.OL",  "Hafnia Limited",              "Oslo",      "NO"),
    ("OET.OL",    "Okeanis Eco Tankers Corp",    "Oslo",      "NO"),
    ("2020.OL",   "2020 Bulkers Ltd",            "Oslo",      "NO"),
    ("GLEN.L",    "Glencore plc",                "London",    "GB"),
    ("ATYM.L",    "Atalaya Mining",              "London",    "GB"),
    ("MPE.L",     "M.P. Evans Group PLC",        "London",    "GB"),
    ("RE.L",      "REA Holdings plc",            "London",    "GB"),
    ("TMIP.L",    "Taylor Maritime Investments", "London",    "GB"),
    ("CVE.TO",    "Cenovus Energy Inc",          "Toronto",   "CA"),
    ("WCP.TO",    "Whitecap Resources Inc",      "Toronto",   "CA"),
    ("TOU.TO",    "Tourmaline Oil Corp",         "Toronto",   "CA"),
    ("BIR.TO",    "Birchcliff Energy Ltd",       "Toronto",   "CA"),
    ("CS.TO",     "Capstone Copper Corp",        "Toronto",   "CA"),
    ("BARN.SW",   "Barry Callebaut AG",          "Zurich",    "CH"),
    ("NESN.SW",   "Nestle SA",                   "Zurich",    "CH"),
    ("BOL.ST",    "Boliden AB",                  "Stockholm", "SE"),
    ("ERA.PA",    "Eramet",                      "Paris",     "FR"),
]

LOGG = []
def note(rute, tk, ok, d=""):
    LOGG.append({"rute": rute, "ticker": tk, "ok": ok, "detalj": d})
    print(f"   {'ok   ' if ok else 'nei  '} {rute:12} {tk:12} {d}")


def get(url, **kw):
    h = kw.pop("headers", UA)
    for i in range(3):
        try:
            r = requests.get(url, headers=h, timeout=kw.pop("timeout", TIMEOUT), **kw)
            if r.status_code in (429, 502, 503):
                time.sleep(3 * (i + 1)); continue
            return r
        except requests.RequestException as e:
            if i == 2:
                raise
            time.sleep(2 * (i + 1))
    raise RuntimeError("ga opp")


norm = lambda s: re.sub(r"[^a-z0-9]", "", str(s).lower())
def likner(a, b):
    """Navnematch som taaler ASA, plc, Inc og mellomrom."""
    a, b = norm(a), norm(b)
    for hale in ("asa", "plc", "ab", "sa", "ag", "inc", "corp", "ltd", "limited", "group"):
        a = a[:-len(hale)] if a.endswith(hale) else a
        b = b[:-len(hale)] if b.endswith(hale) else b
    return a.startswith(b[:8]) or b.startswith(a[:8])


# ============================================================ 1. filings.xbrl.org
print("1. ESEF-registeret (filings.xbrl.org)")
print("   Henter indeksen per land og ser hvem vi finner igjen.\n")

ESEF = {}
for land in sorted({l for *_, l in MANGLER if l in ("NO", "SE", "FR", "GB")}):
    treff, side, nav = [], 0, None
    try:
        url = (f"https://filings.xbrl.org/api/filings?include=entity"
               f"&filter[country]={land}&page[size]=500")
        while url and side < 12:
            r = get(url)
            if r.status_code != 200:
                note("esef", land, False, f"HTTP {r.status_code}")
                break
            j = r.json()
            for e in j.get("included", []):
                if e.get("type") == "entity":
                    treff.append(e.get("attributes", {}).get("name", ""))
            for d in j.get("data", []):
                a = d.get("attributes", {})
                nav = nav or a.get("period_end")
            url = (j.get("links") or {}).get("next")
            side += 1
            time.sleep(0.4)
        navn = sorted(set(x for x in treff if x))
        print(f"   {land}: {len(navn)} enheter i registeret")
        ESEF[land] = navn
    except Exception as e:
        note("esef", land, False, f"{type(e).__name__}: {str(e)[:60]}")
        ESEF[land] = []

print()
for tk, navn, bors, land in MANGLER:
    kand = [n for n in ESEF.get(land, []) if likner(n, navn)]
    note("esef", tk, bool(kand), (kand[0] if kand else f"ingen match i {land}")[:60])


# ============================================================ 2. Bronnoysund
print("\n2. Bronnoysund regnskapsregisteret (bare norske)")
for tk, navn, bors, land in MANGLER:
    if land != "NO":
        continue
    try:
        r = get("https://data.brreg.no/enhetsregisteret/api/enheter"
                f"?navn={requests.utils.quote(navn)}&size=5")
        enh = (r.json().get("_embedded") or {}).get("enheter", [])
        if not enh:
            note("brreg", tk, False, "ikke i enhetsregisteret"); continue
        org = enh[0]["organisasjonsnummer"]
        rr = get(f"https://data.brreg.no/regnskapsregisteret/regnskap/{org}",
                 headers={**UA, "Accept": "application/json"})
        if rr.status_code != 200:
            note("brreg", tk, False, f"orgnr {org}, regnskap HTTP {rr.status_code}"); continue
        d = rr.json()
        d = d if isinstance(d, list) else [d]
        aar = sorted({str(x.get("regnskapsperiode", {}).get("tilDato", ""))[:4] for x in d} - {""})
        # finnes driftskontantstrom i det hele tatt
        tekst = json.dumps(d).lower()
        kontant = any(k in tekst for k in ("kontantstrom", "kontantstrøm", "likvide"))
        note("brreg", tk, bool(aar),
             f"orgnr {org}, {len(aar)} aar ({aar[0] if aar else '-'}..{aar[-1] if aar else '-'})"
             f", kontantstrom i data: {'ja' if kontant else 'NEI'}")
    except Exception as e:
        note("brreg", tk, False, f"{type(e).__name__}: {str(e)[:60]}")
    time.sleep(0.4)


# ============================================================ 3. Yahoo som gulv
print("\n3. Yahoo quoteSummary (alle borser, men faa aar)")
for tk, navn, bors, land in MANGLER:
    try:
        r = get(f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{tk}"
                "?modules=cashflowStatementHistory,balanceSheetHistory", headers=UAB)
        if r.status_code != 200:
            note("yahoo", tk, False, f"HTTP {r.status_code}"); continue
        res = (r.json().get("quoteSummary") or {}).get("result") or []
        if not res:
            note("yahoo", tk, False, "tomt svar"); continue
        cf = (res[0].get("cashflowStatementHistory") or {}).get("cashflowStatements") or []
        ocf = [x for x in cf if (x.get("totalCashFromOperatingActivities") or {}).get("raw") is not None]
        aar = sorted(str(x.get("endDate", {}).get("fmt", ""))[:4] for x in ocf)
        note("yahoo", tk, bool(ocf),
             f"{len(ocf)} aar med driftskontantstrom ({aar[0] if aar else '-'}..{aar[-1] if aar else '-'})")
    except Exception as e:
        note("yahoo", tk, False, f"{type(e).__name__}: {str(e)[:60]}")
    time.sleep(0.5)


# ================================================================ oppsummering
print("\n\n" + "=" * 62)
print("OPPSUMMERING: hvor mange av de 20 gir hver rute treff paa")
for rute in ("esef", "brreg", "yahoo"):
    r = [l for l in LOGG if l["rute"] == rute and l["ticker"] not in ("NO","SE","FR","GB")]
    print(f"   {rute:8} {sum(1 for x in r if x['ok']):2} av {len(r):2}")
print("\nPer aksje:")
for tk, navn, bors, land in MANGLER:
    s = {l["rute"]: l["ok"] for l in LOGG if l["ticker"] == tk}
    print(f"   {tk:12} {bors:10} esef={'ja ' if s.get('esef') else 'nei'}  "
          f"brreg={'ja ' if s.get('brreg') else ('nei' if land=='NO' else '  -')}  "
          f"yahoo={'ja' if s.get('yahoo') else 'nei'}")
print("\nSend hele utskriften tilbake.")
