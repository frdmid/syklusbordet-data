# ---------------------------------------------------------------------------
# sonde_kjor_c_produksjon: hvilke SEC-selskaper i C har verste driftsaar foer
# produksjonsstart?
#
# Frodes beslutning 29.09.2026: aar foer produksjonsstart teller ikke i C.
# Cowork har innfoert det i c_manuell. Denne sonden finner kandidatene i
# SEC-delen og leter etter kilder, uten aa bestemme noe.
#
#   1  Kjoerer overlevelse_c.py med PRODFIX=0 (dagens tall, ingenting
#      publiseres) og henter driftsserien og bunnaaret per selskap.
#   2  Henter omsetningen per aar fra SEC i samme valuta som driften.
#      Kandidat: omsetningen i bunnaaret er under ti prosent av siste aars
#      omsetning, eller mangler.
#   3  For kandidatene: leser selskapets foerste og siste aarsrapport hos SEC
#      (10-K, 20-F, 40-F) og skriver ut setninger om start av produksjon eller
#      drift, med adresse, som kilde.
# ---------------------------------------------------------------------------

import json, os, re, subprocess, sys, tempfile, time
import requests

SEC_UA = {"User-Agent": "Syklusbordet frode@h-k.no"}
FORMER = {"10-K", "20-F", "40-F"}
OMS = ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet",
       "SalesRevenueGoodsNet", "RevenueFromContractWithCustomerIncludingAssessedTax",
       "Revenue", "RevenueFromContractsWithCustomers", "RevenueFromSaleOfGoods"]
FRASER = re.compile(r"[^.]{0,200}(commenc\w+ (commercial )?(production|operations|mining)|"
                    r"commercial production|first production|start(ed)? of (commercial )?production|"
                    r"production (began|commenced|started)|began (commercial )?(production|operations)|"
                    r"took delivery of (its|our) first|first vessel|delivery of the first|"
                    r"development stage|exploration stage|pre-production|no revenues?)[^.]{0,200}\.", re.I)

fil = os.path.join(tempfile.gettempdir(), "c_prod.json")
p = subprocess.run([sys.executable, "overlevelse_c.py"], capture_output=True, text=True, timeout=3000,
                   env={**os.environ, "GITHUB_TOKEN": "", "PRODFIX": "0", "C_UT": fil})
if p.returncode != 0 or not os.path.exists(fil):
    sys.exit(f"overlevelse_c.py feilet:\n{p.stdout[-2000:]}\n{p.stderr[-2000:]}")
C = json.load(open(fil, encoding="utf-8"))
tick = requests.get("https://www.sec.gov/files/company_tickers.json", headers=SEC_UA, timeout=60).json()
KART = {v["ticker"].upper(): str(v["cik_str"]).zfill(10) for v in tick.values()}


def secnr(tk):
    for k in (tk, re.sub(r"\.[A-Z]+$", "", tk), re.sub(r"-[A-Z]$", "", re.sub(r"\.[A-Z]+$", "", tk))):
        if k.upper() in KART:
            return KART[k.upper()]


def omsetning(fakta, valuta):
    for b in OMS:
        for tak in ("us-gaap", "ifrs-full"):
            d = fakta.get(tak, {}).get(b)
            if not d or valuta not in d.get("units", {}):
                continue
            best = {}
            for x in d["units"][valuta]:
                if x.get("form") in FORMER and x.get("fp") == "FY" and x.get("start") and x.get("end"):
                    import datetime as dt
                    dager = (dt.date.fromisoformat(x["end"]) - dt.date.fromisoformat(x["start"])).days
                    if 330 <= dager <= 400:
                        k = int(x["end"][:4])
                        if k not in best or x.get("accn", "") > best[k].get("accn", ""):
                            best[k] = x
            if len(best) >= 3:
                return f"{tak}:{b}", {k: float(v["val"]) for k, v in sorted(best.items())}
    return None, {}


def aarsrapporter(cik):
    s = requests.get(f"https://data.sec.gov/submissions/CIK{cik}.json", headers=SEC_UA, timeout=60).json()
    r = s["filings"]["recent"]
    ut = [(r["filingDate"][i], r["form"][i], r["accessionNumber"][i], r["primaryDocument"][i])
          for i in range(len(r["form"])) if r["form"][i] in FORMER]
    return sorted(ut)


def tekst(cik, accn, dok):
    url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accn.replace('-', '')}/{dok}"
    h = requests.get(url, headers=SEC_UA, timeout=120).text
    h = re.sub(r"(?is)<(script|style).*?</\1>", " ", h)
    h = re.sub(r"<[^>]+>", " ", h)
    h = re.sub(r"&#160;|&nbsp;", " ", h)
    return url, re.sub(r"\s+", " ", h)


print("1 og 2. Bunnaar og omsetning, alle SEC-selskaper (manuelt leste er utelatt)\n")
print(f"{'papir':10s} {'port':7s} {'bunnaar':>7s} {'oms bunnaar':>14s} {'oms siste':>14s} {'andel':>7s}  kandidat")
kand = []
for tk, v in sorted(C["selskaper"].items()):
    if str(v.get("kilde", "")).startswith("manuelt") or tk not in C["drift"]:
        continue
    cik = secnr(tk)
    val = C["drift"][tk]["valuta"]
    try:
        fakta = requests.get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json",
                             headers=SEC_UA, timeout=120).json().get("facts", {})
    except Exception as e:
        print(f"{tk:10s} FEIL {type(e).__name__}"); continue
    begrep, oms = omsetning(fakta, val)
    b = v["bunnaar"]
    siste = oms[max(oms)] if oms else None
    ob = oms.get(b)
    andel = None if not siste or ob is None else ob / siste
    er = ob is None or (andel is not None and andel < 0.10)
    fm = lambda x: "-" if x is None else f"{x / 1e6:,.0f} m"
    print(f"{tk:10s} {v['port']:7s} {b:>7d} {fm(ob):>14s} {fm(siste):>14s} "
          f"{'-' if andel is None else format(100 * andel, '.0f') + ' %':>7s}  {'JA' if er else ''}")
    print(f"           drift ({val}): " + "  ".join(f"{a}:{x / 1e6:,.0f}" for a, x in C["drift"][tk]["drift"].items()))
    print(f"           omsetning ({begrep}, siste aar {max(oms) if oms else '-'}): "
          + "  ".join(f"{a}:{x / 1e6:,.0f}" for a, x in oms.items()))
    if er:
        kand.append((tk, cik))
    time.sleep(0.3)

print(f"\n   Kandidater: {', '.join(t for t, _ in kand) or 'ingen'}")

print("\n\n3. Kilder: setninger om start av produksjon eller drift i aarsrapportene\n")
for tk, cik in kand:
    print(f"   {tk}")
    try:
        rap = aarsrapporter(cik)
    except Exception as e:
        print(f"      innleveringer feilet: {type(e).__name__}"); continue
    print(f"      {len(rap)} aarsrapporter i siste liste: " + ", ".join(f"{d[:4]} {f}" for d, f, _, _ in rap))
    for d, f, accn, dok in ([rap[0], rap[-1]] if len(rap) > 1 else rap):
        try:
            url, t = tekst(cik, accn, dok)
        except Exception as e:
            print(f"      {d} {f}: {type(e).__name__}"); continue
        treff = []
        for m in FRASER.finditer(t):
            s = m.group(0).strip()
            if s not in treff:
                treff.append(s)
        print(f"      {f} innlevert {d}: {url}")
        for s in treff[:8]:
            print(f"         \"{s[:400]}\"")
        if not treff:
            print("         ingen treff")
        time.sleep(0.5)
