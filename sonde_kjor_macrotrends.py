# ---------------------------------------------------------------------------
# sonde_kjor_macrotrends: gir MacroTrends femten aar for borsene SEC ikke naar
#
# Tre kilder er avklart og forkastet:
#   ESEF            4 til 6 aar, 2020 eller 2021 og framover
#   stockanalysis   6 aar, 2020 til 2026. range=10Y endrer ingenting
#   Yahoo           4 aar, 2022 til 2025, ogsaa for Alcoa der SEC gir tolv
#   Bronnoysund     ett aar, uten kontantstromoppstilling
#
# Alle gir det samme femaarsvinduet, og det er nettopp vinduet som ga feilen i
# september: 2021 til 2025 var gode aar for alle, og 30 av 32 selskaper leste
# "aapen" fordi ingen syklusbunn laa inne.
#
# MacroTrends oppgir "Cash Flow Statement 2011-2026". Tabellen bygges av
# JavaScript, saa den er usynlig for en vanlig teksthenting, men tallene ligger
# i sidekilden som "var originalData = [...]". Det kan leses herfra.
#
# Sonden gjetter ikke tickere. MacroTrends publiserer hele dekningslisten sin,
# og den matches mot selskapsnavnene vaare.
#
# Det avgjorende er aarstallene. Naar den er ferdig vet vi om ruten gir
# selskapets verste driftskontantstrom noensinne, som er det ene tallet C
# trenger og som aldri endrer seg.
# ---------------------------------------------------------------------------

import json, re, time
import requests

TIMEOUT = 40
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept-Language": "en-US,en;q=0.9"}

# De nitten uten C. De aatte forste er dem som faktisk mangler for at et
# segment skal faa port; resten er med fordi de koster ingenting naar ruten
# forst virker.
SELSKAP = [
    ("DNO.OL",    "DNO",                  "brent"),
    ("AKRBP.OL",  "Aker BP",              "brent"),
    ("CS.TO",     "Capstone Copper",      "kobber"),
    ("ATYM.L",    "Atalaya Mining",       "kobber"),
    ("ERA.PA",    "Eramet",               "nikkel"),
    ("GLEN.L",    "Glencore",             "nikkel og tinn"),
    ("MPE.L",     "M.P. Evans",           "palmeolje"),
    ("RE.L",      "REA Holdings",         "palmeolje"),
    ("NHY.OL",    "Norsk Hydro",          "aluminium, har alt port"),
    ("BOL.ST",    "Boliden",              "sink og bly"),
    ("NESN.SW",   "Nestle",               "kakao"),
    ("BARN.SW",   "Barry Callebaut",      "kakao"),
    ("HAFNI.OL",  "Hafnia",               "shipping"),
    ("OET.OL",    "Okeanis Eco Tankers",  "shipping"),
    ("2020.OL",   "2020 Bulkers",         "shipping"),
    ("TMIP.L",    "Taylor Maritime",      "shipping"),
    ("TOU.TO",    "Tourmaline Oil",       "henryhub"),
    ("WCP.TO",    "Whitecap Resources",   "wti"),
    ("BIR.TO",    "Birchcliff Energy",    "henryhub"),
]


def get(url, **kw):
    for i in range(3):
        try:
            r = requests.get(url, headers=UA, timeout=TIMEOUT, **kw)
            if r.status_code in (429, 502, 503):
                time.sleep(4 * (i + 1)); continue
            return r
        except requests.RequestException:
            if i == 2:
                raise
            time.sleep(2 * (i + 1))
    raise RuntimeError("ga opp")


norm = lambda s: re.sub(r"[^a-z0-9]", "", str(s).lower())
HALER = ("asa", "plc", "ab", "sa", "ag", "inc", "corp", "ltd", "limited",
         "group", "publ", "nv", "oyj", "co", "holdings", "energy")
def kjerne(s):
    s, endret = norm(s), True
    while endret:
        endret = False
        for h in HALER:
            if s.endswith(h) and len(s) - len(h) >= 3:
                s, endret = s[:-len(h)], True
    return s


# ============================================== 1. MacroTrends sin dekningsliste
print("1. Henter MacroTrends sin tickerliste\n")
LISTE = []
for u in ("https://www.macrotrends.net/assets/php/ticker_search_list.php",
          "https://www.macrotrends.net/stocks/stock-screener"):
    try:
        r = get(u)
        print(f"   {u.split('/')[-1]:30} HTTP {r.status_code}  {len(r.content)//1024} kB")
        if r.status_code != 200:
            continue
        # listen er normalt JSON med n (navn) og s (ticker/slug)
        try:
            LISTE = r.json()
        except Exception:
            m = re.search(r"(\[\s*\{.*?\}\s*\])", r.text, re.S)
            LISTE = json.loads(m.group(1)) if m else []
        if LISTE:
            print(f"   {len(LISTE)} oppforinger. Feltene: {sorted(LISTE[0])}")
            print(f"   Eksempel: {LISTE[0]}")
            break
    except Exception as e:
        print(f"   {u[-40:]:40} {type(e).__name__} {str(e)[:50]}")

def finn(navn):
    k = kjerne(navn)
    tr = []
    for rad in LISTE:
        n = rad.get("n") or rad.get("name") or ""
        s = rad.get("s") or rad.get("slug") or rad.get("ticker") or ""
        if not n or not s:
            continue
        if kjerne(n) == k or kjerne(n).startswith(k) and len(kjerne(n)) - len(k) <= 4:
            tr.append((s, n))
    return tr


# ======================================= 2. Kontantstrom per selskap, alle aar
print("\n\n2. Driftskontantstrom per aar\n")
TREFF, BOM = {}, []
for tk, navn, hvorfor in SELSKAP:
    kand = finn(navn) if LISTE else []
    if not kand:
        print(f"   nei   {tk:10} {navn:22} ikke i MacroTrends' liste")
        BOM.append(tk); continue
    slug, mtnavn = kand[0]
    url = f"https://www.macrotrends.net/stocks/charts/{slug}/cash-flow-statement"
    try:
        r = get(url)
        if r.status_code != 200:
            print(f"   nei   {tk:10} {navn:22} {slug} HTTP {r.status_code}")
            BOM.append(tk); continue
        m = re.search(r"var\s+originalData\s*=\s*(\[.*?\]);", r.text, re.S)
        if not m:
            print(f"   nei   {tk:10} {navn:22} {slug}: fant ikke originalData "
                  f"({len(r.content)//1024} kB)")
            BOM.append(tk); continue
        data = json.loads(m.group(1))
        rad = next((d for d in data
                    if "operating activities" in re.sub(r"<[^>]+>", "", str(d.get("field_name", ""))).lower()), None)
        if rad is None:
            felt = [re.sub(r"<[^>]+>", "", str(d.get("field_name", "")))[:34] for d in data[:8]]
            print(f"   nei   {tk:10} {navn:22} {slug}: ingen driftsrad. Feltene: {felt}")
            BOM.append(tk); continue
        aar = {}
        for k, v in rad.items():
            if re.match(r"^\d{4}-\d{2}-\d{2}$", str(k)) and str(v).strip() not in ("", "-"):
                try:
                    aar[int(str(k)[:4])] = float(str(v).replace(",", ""))
                except ValueError:
                    pass
        if not aar:
            print(f"   nei   {tk:10} {navn:22} {slug}: raden er tom. Nokler: {list(rad)[:6]}")
            BOM.append(tk); continue
        verst = min(aar, key=aar.get)
        TREFF[tk] = {"slug": slug, "mt_navn": mtnavn, "aar": sorted(aar),
                     "verste_aar": verst, "verste": aar[verst], "siste": aar[max(aar)]}
        print(f"   ok    {tk:10} {navn:22} {len(aar):2} aar {min(aar)}..{max(aar)}   "
              f"verst {verst}: {aar[verst]:>12,.0f}   ({hvorfor})")
    except Exception as e:
        print(f"   nei   {tk:10} {navn:22} {type(e).__name__} {str(e)[:50]}")
        BOM.append(tk)
    time.sleep(1.0)


# ============================================================== oppsummering
print(f"\n\n{'=' * 62}")
print(f"{len(TREFF)} av {len(SELSKAP)} selskaper fikk tall. {len(BOM)} bommet: {', '.join(BOM) or 'ingen'}")
nok = [t for t, d in TREFF.items() if len(d["aar"]) >= 10]
print(f"{len(nok)} har ti aar eller mer, altsaa nok til at det verste aaret kan stoles paa.")
print("\nEnheten maa sjekkes for hvert selskap. MacroTrends oppgir normalt")
print("millioner i selskapets rapporteringsvaluta, men det staar ikke i")
print("originalData, saa det maa leses av sida eller avstemmes mot SEC der")
print("begge finnes.")
if TREFF:
    print("\nDette er tallene C trenger, ett per selskap, og de endrer seg aldri:")
    for tk, d in TREFF.items():
        print(f"   {tk:10} verste aar {d['verste_aar']}: {d['verste']:>14,.0f}   "
              f"(siste aar {d['siste']:>12,.0f})   slug {d['slug']}")
print("\nSend hele utskriften tilbake.")
