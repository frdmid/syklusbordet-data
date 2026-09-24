# ---------------------------------------------------------------------------
# Syklusbordet: overlevelsesporten C
#
# Dokumentet: "Taaler selskapet ventetiden." Under aatte kvartaler med kontanter
# er aksjen i praksis en opsjon, ikke en investering, og da virker ikke
# taalmodighet som strategi: du blir utvannet foer du faar rett.
#
# C gjelder SELSKAPET, ikke raavaren. Den porter instrumentet.
#
# Sonden viste at 35 av 60 aksjer finnes hos SEC og 34 har minst fire av seks
# ledd. De ovrige 25 er Oslo, Stockholm, Kobenhavn, London og kontinentet, og
# maa dekkes av andre kilder senere. De staar som "ukjent", ikke som "stengt":
# en manglende maaling er ikke det samme som en feilet test.
#
# Ingen begreper gjettes. Skriptet scanner hva hvert selskap faktisk bruker, i
# baade us-gaap og ifrs-full, og logger hvilket begrep som ble valgt.
# ---------------------------------------------------------------------------

REPO, BRANCH = "frdmid/syklusbordet-data", "main"

import base64, json, os, re, sys, time
import numpy as np, pandas as pd, requests

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
SEC_UA = {"User-Agent": "Syklusbordet frode@h-k.no"}
FORMER = {"10-K", "20-F", "40-F"}
MIN_AAR = 4
# Stresstilfellet er det verste aaret i HELE den tilgjengelige historikken, ikke
# de siste fem. Femaarsvinduet inneholder ingen syklisk bunn for de fleste av
# disse selskapene: 2021 til 2025 var gode aar for raavarer, saa "verste aar"
# ble et godt aar og porten slapp gjennom 30 av 32. Det relevante spoergsmaalet
# for en bunnkjoepstrategi er om selskapet overlevde forrige bunn.
PORT_KVARTALER = 8      # dokumentets egen terskel

from instrumenter import INSTR

# Rangert per ledd. Foerste begrep med nok aarstall vinner, saa de mest
# spesifikke staar foerst. Balansepostene er oyeblikksverdier, stromspostene
# aarlige.
LEDD = {
 "kontanter": ([
    "CashAndCashEquivalentsAtCarryingValue",
    "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
    "CashAndCashEquivalents",
    "CashAndBankBalancesAtCentralBanks",
    "Cash"], "balanse"),
 "gjeld": ([
    "LongTermDebtAndCapitalLeaseObligations",
    "LongTermDebtNoncurrent",
    "LongTermDebt",
    "LongtermBorrowings",
    "Borrowings",
    "DebtLongtermAndShorttermCombinedAmount"], "balanse"),
 "drift": ([
    "NetCashProvidedByUsedInOperatingActivities",
    "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
    "CashFlowsFromUsedInOperatingActivities"], "strom"),
 "egenkapital": ([
    "StockholdersEquity",
    "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
    "EquityAttributableToOwnersOfParent",
    "Equity"], "balanse"),
 "rente": ([
    "InterestExpense",
    "InterestExpenseDebt",
    "InterestPaidNet",
    "FinanceCosts"], "strom"),
}


def hent(url, headers=None, timeout=90):
    r = requests.get(url, headers=headers or SEC_UA, timeout=timeout)
    r.raise_for_status()
    return r


def aarsserie(fakta, kandidater, slag):
    """Velger foerste begrep med nok aarstall. Deduper paa aar: samme
    regnskapsaar rapporteres i flere innleveringer, og uten deduplisering
    telles ett aar flere ganger. Siste innlevering vinner."""
    for begrep in kandidater:
        d = fakta.get(begrep)
        if not d:
            continue
        for enh, pkt in d.get("units", {}).items():
            if not enh.startswith("USD"):
                continue
            if slag == "strom":
                aar = [p for p in pkt if p.get("form") in FORMER and p.get("fp") == "FY"
                       and p.get("start") and p.get("end")
                       and 330 <= (pd.Timestamp(p["end"]) - pd.Timestamp(p["start"])).days <= 400]
            else:
                aar = [p for p in pkt if p.get("form") in FORMER]
            if len(aar) < MIN_AAR:
                continue
            best = {}
            for p in aar:
                k = p["end"][:4]
                if k not in best or p.get("accn", "") > best[k].get("accn", ""):
                    best[k] = p
            s = pd.Series({int(k): float(v["val"]) for k, v in best.items()}).sort_index()
            if len(s) >= MIN_AAR:
                return begrep, s
    return None, None


print("1. SECs tickerliste")
try:
    tick = hent("https://www.sec.gov/files/company_tickers.json", timeout=45).json()
    KART = {v["ticker"].upper(): str(v["cik_str"]).zfill(10) for v in tick.values()}
    print(f"   {len(KART)} selskaper")
except Exception as e:
    sys.exit(f"   SEC svarte ikke: {type(e).__name__} {e}")


def secnavn(tk):
    for k in (tk, re.sub(r"\.[A-Z]+$", "", tk), re.sub(r"-[A-Z]$", "", re.sub(r"\.[A-Z]+$", "", tk))):
        if k.upper() in KART:
            return k.upper()
    return None


AKSJER = {}
for sid, rader in INSTR.items():
    for tk, bors, navn, typ, kom in rader:
        # Fond har ingen balanse aa maale. ETC-ene er ute av universet, men
        # UCITS-fondene er inne, og uten dette leter C etter Agnico-tall for
        # GDX.L.
        if typ.lower().startswith(("etc", "etf", "etn", "fond")):
            continue
        AKSJER.setdefault(tk, {"navn": navn, "bors": bors, "segmenter": []})["segmenter"].append(sid)

print(f"\n2. Regnskapstall for {len(AKSJER)} aksjer")
SELSKAP, utenfor = {}, []
for tk in sorted(AKSJER):
    nk = secnavn(tk)
    if not nk:
        utenfor.append(tk)
        continue
    try:
        cf = hent(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{KART[nk]}.json").json()
    except Exception as e:
        print(f"   {tk:12s} FEIL {type(e).__name__} {str(e)[:40]}")
        utenfor.append(tk)
        continue
    fakta = {}
    for tak in ("us-gaap", "ifrs-full"):
        fakta.update(cf.get("facts", {}).get(tak, {}))
    valgt, serier = {}, {}
    for ledd, (kand, slag) in LEDD.items():
        b, s = aarsserie(fakta, kand, slag)
        if b is not None:
            valgt[ledd], serier[ledd] = b, s
    if "kontanter" not in serier or "drift" not in serier:
        print(f"   {tk:12s} mangler {'kontanter' if 'kontanter' not in serier else 'driftskontantstrom'}")
        utenfor.append(tk)
        time.sleep(0.3)
        continue

    kont = float(serier["kontanter"].iloc[-1])
    drift = serier["drift"]
    stress = float(drift.min())
    naa = float(drift.iloc[-1])
    bunnaar = int(drift.idxmin())
    gjeld = float(serier["gjeld"].iloc[-1]) if "gjeld" in serier else None
    ek = float(serier["egenkapital"].iloc[-1]) if "egenkapital" in serier else None
    rente = abs(float(serier["rente"].iloc[-1])) if "rente" in serier else None

    # Fri kontantstrom etter renter. Er den positiv, finansierer selskapet seg
    # selv og kontantbeholdningen er irrelevant.
    #
    # Renten skal TREKKES FRA driften, ikke legges til brennraten. Foerste
    # versjon la den til, og da fikk Diamondback med 3,9 mrd i positiv drift
    # "1,7 kvartaler igjen". 14 av 34 selskaper var feilklassifisert.
    def kv(ocf):
        fri = ocf - (rente or 0.0)
        return None if fri >= 0 else round(kont / (-fri / 4), 1)
    kvartaler = kv(stress)          # ved forrige syklusbunn
    kvartaler_naa = kv(naa)         # ved dagens rate, dokumentets egen ordlyd
    # C2: netto gjeld mot egenkapital
    ngek = None if not ek or ek <= 0 or gjeld is None else round((gjeld - kont) / ek, 2)
    # C3: rentedekning i stresstilfellet
    dekning = None if not rente else round(stress / rente, 1)

    if kvartaler is None:
        port, hvorfor = "aapen", f"positiv drift etter renter selv i {bunnaar}"
    elif kvartaler >= 16 and (ngek is None or ngek < 1.5):
        port, hvorfor = "aapen", f"{kvartaler} kvartaler"
    elif kvartaler >= PORT_KVARTALER:
        port, hvorfor = "trang", f"{kvartaler} kvartaler"
    else:
        port, hvorfor = "stengt", f"bare {kvartaler} kvartaler"
    if ngek is not None and ngek > 3 and port == "aapen":
        port, hvorfor = "trang", hvorfor + f", men netto gjeld {ngek}x egenkapital"

    SELSKAP[tk] = {"ticker": tk, "navn": AKSJER[tk]["navn"], "bors": AKSJER[tk]["bors"],
                   "segmenter": AKSJER[tk]["segmenter"], "port": port, "hvorfor": hvorfor,
                   "kvartaler": kvartaler, "kvartaler_naa": kvartaler_naa,
                   "bunnaar": bunnaar, "aar_historikk": len(drift),
                   "netto_gjeld_ek": ngek, "rentedekning": dekning,
                   "kontanter_musd": round(kont / 1e6, 0),
                   "verste_drift_musd": round(stress / 1e6, 0),
                   "drift_naa_musd": round(naa / 1e6, 0),
                   "rente_musd": None if rente is None else round(rente / 1e6, 0),
                   "aar": [int(drift.index[0]), int(drift.index[-1])],
                   "begreper": valgt}
    print(f"   {tk:12s} {port:7s} {hvorfor[:38]:40s} bunnaar {bunnaar} av "
          f"{len(drift)} aar, netto gjeld/EK {str(ngek):>6}")
    time.sleep(0.3)

print(f"\n   {len(SELSKAP)} maalt, {len(utenfor)} uten SEC-tall: {', '.join(utenfor)}")

print("\n3. Port per segment")
SEG = {}
for sid in INSTR:
    egne = [v for v in SELSKAP.values() if sid in v["segmenter"]]
    if not egne:
        SEG[sid] = {"gate": "ukjent", "aapne": 0, "malte": 0, "instrumenter": []}
        continue
    aapne = [v for v in egne if v["port"] == "aapen"]
    SEG[sid] = {"gate": "aapen" if aapne else ("trang" if any(v["port"] == "trang" for v in egne) else "stengt"),
                "aapne": len(aapne), "malte": len(egne),
                "instrumenter": [{"ticker": v["ticker"], "port": v["port"],
                                  "kvartaler": v["kvartaler"]} for v in egne]}
for sid, v in sorted(SEG.items(), key=lambda x: (x[1]["gate"], x[0])):
    if v["malte"]:
        print(f"   {sid:16s} {v['gate']:7s} {v['aapne']}/{v['malte']} aapne  "
              + ", ".join(f"{i['ticker']}:{i['port'][:1]}" for i in v["instrumenter"]))
ukjent = [s for s, v in SEG.items() if not v["malte"]]
print(f"   uten maaling: {', '.join(ukjent) or 'ingen'}")

if GITHUB_TOKEN and SELSKAP:
    api = f"https://api.github.com/repos/{REPO}/contents/c_overlevelse.json"
    h = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}
    sha = None
    g = requests.get(api, headers=h, params={"ref": BRANCH}, timeout=30)
    if g.status_code == 200:
        sha = g.json().get("sha")
    body = {"message": "overlevelsesport C", "branch": BRANCH,
            "content": base64.b64encode(json.dumps(
                {"oppdatert": str(pd.Timestamp.utcnow())[:19],
                 "terskel_kvartaler": PORT_KVARTALER,
                 "selskaper": SELSKAP, "segmenter": SEG,
                 "utenfor_sec": utenfor,
                 "merknad": ("C1 er hvor mange kvartaler kontantbeholdningen holder hvis "
                             "driftskontantstrommen blir like daarlig som sitt verste aar "
                             "i hele historikken, etter renter. kvartaler_naa er det samme "
                             "ved siste aars drift. Under aatte kvartaler regnes "
                             "porten som stengt. Selskaper uten SEC-tall staar som ukjent, "
                             "ikke som stengt.")},
                ensure_ascii=False).encode()).decode()}
    if sha:
        body["sha"] = sha
    requests.put(api, headers=h, json=body, timeout=60).raise_for_status()
    print(f"\n   publisert c_overlevelse.json ({len(SELSKAP)} selskaper, {len(SEG)} segmenter)")
elif not GITHUB_TOKEN:
    print("\n   GITHUB_TOKEN mangler, ingenting publisert")
