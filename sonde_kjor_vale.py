# ---------------------------------------------------------------------------
# sonde_kjor_vale: hvorfor stopper Vales tall hos SEC i 2021?
# Viser aarsrapportene Vale har levert siden 2020, og for begrepene C bruker
# (drift og kontanter) alle enheter, skjema og siste aar.
# ---------------------------------------------------------------------------
import requests
UA = {"User-Agent": "Syklusbordet frode@h-k.no"}
t = requests.get("https://www.sec.gov/files/company_tickers.json", headers=UA, timeout=60).json()
cik = next(str(v["cik_str"]).zfill(10) for v in t.values() if v["ticker"] == "VALE")
s = requests.get(f"https://data.sec.gov/submissions/CIK{cik}.json", headers=UA, timeout=60).json()
r = s["filings"]["recent"]
print("Aarsrapporter og 6-K med XBRL siden 2020:")
for i in range(len(r["form"])):
    if r["filingDate"][i] >= "2020" and (r["form"][i] in ("20-F", "20-F/A") or r["isXBRL"][i]):
        print(f"   {r['filingDate'][i]} {r['form'][i]:7s} xbrl={r['isXBRL'][i]} {r['primaryDocument'][i]}")
f = requests.get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json", headers=UA, timeout=120).json()["facts"]
for tak, begreper in f.items():
    for b, d in begreper.items():
        if not any(k.lower() in b.lower() for k in ("Operat", "CashAndCashEquivalents", "InterestPaid",
                                                      "IncomeTaxesPaid", "Borrowings", "Equity")):
            continue
        if tak in ("us-gaap",):
            continue
        for enh, pkt in d["units"].items():
            siste = max(pkt, key=lambda p: p["end"])
            fy = [p for p in pkt if p.get("fp") == "FY"]
            if max(p["end"] for p in pkt) < "2022":
                continue
            print(f"{tak:9s} {b[:75]:75s} {enh:4s} n={len(pkt):3d} siste slutt {siste['end']} "
                  f"skjema {siste.get('form')} fp {siste.get('fp')}  FY-aar: {sorted({p['end'][:4] for p in fy})[-6:]}")
