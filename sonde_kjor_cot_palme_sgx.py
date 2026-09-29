# ---------------------------------------------------------------------------
# sonde_kjor_cot_palme_sgx: to ting foer COT bygges ut (Frodes valg 29.09.2026)
#
#   A  Palmeolje hos CFTC: hvilken kontraktkode er den aktive, og gir
#      signaler.cot_fra_rader et fornuftig felt paa den?
#   B  SGX, COT for jernmalm: siden er en JavaScript-app. Finn hvilke
#      adresser appen henter tallene fra, ved aa lese skriptene den laster.
# ---------------------------------------------------------------------------

import json, re, time
import requests
from signaler import hent_kontrakt, cot_fra_rader

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}

print("A. Palmeolje hos CFTC\n")
r = requests.get("https://publicreporting.cftc.gov/resource/72hh-3qpy.json",
                 params={"$select": "cftc_contract_market_code, market_and_exchange_names, "
                                    "min(report_date_as_yyyy_mm_dd) as fra, max(report_date_as_yyyy_mm_dd) as til, count(*) as uker",
                         "$where": "upper(market_and_exchange_names) like '%PALM%'",
                         "$group": "cftc_contract_market_code, market_and_exchange_names", "$limit": "20"},
                 headers={"User-Agent": "Syklusbordet frode@h-k.no"}, timeout=60)
koder = sorted(r.json(), key=lambda x: x.get("til", ""), reverse=True)
for x in koder:
    print(f"   {x['cftc_contract_market_code']:8s} {x['market_and_exchange_names'][:60]:60s} "
          f"{str(x['fra'])[:10]} til {str(x['til'])[:10]}  {x['uker']} uker")
if koder:
    kode = koder[0]["cftc_contract_market_code"]
    try:
        c = cot_fra_rader(hent_kontrakt(kode), kode)
        print(f"\n   Aktiv kode {kode}: {json.dumps(c, ensure_ascii=False)}")
    except Exception as e:
        print(f"\n   cot_fra_rader feilet for {kode}: {type(e).__name__}: {e}")

print("\n\nB. SGX, hvor henter COT-siden tallene?\n")
side = requests.get("https://www.sgx.com/derivatives/commitment-of-traders", headers=UA, timeout=40).text
skript = sorted(set(re.findall(r'<script[^>]+src="([^"]+)"', side)))
print(f"   {len(skript)} skript paa siden")
funn = set()
for s in skript[:40]:
    u = s if s.startswith("http") else "https://www.sgx.com" + (s if s.startswith("/") else "/" + s)
    try:
        t = requests.get(u, headers=UA, timeout=40).text
    except Exception:
        continue
    for m in re.finditer(r'(commitment[^"\'`]{0,80}|cot[-_ ]?report[^"\'`]{0,60}|queryId[^,;]{0,80}|'
                         r'https?://[a-z0-9.-]*sgx\.com/[^"\'`\s]{0,100})', t, re.I):
        funn.add(m.group(0)[:140])
    time.sleep(0.3)
for f in sorted(funn)[:120]:
    print(f"   {f}")
kandidater = [f for f in funn if re.search(r"commit|cot", f, re.I)]
print(f"\n   {len(funn)} treff, {len(kandidater)} som nevner commitment eller COT")
for u in sorted({m for f in kandidater for m in re.findall(r"https?://[^\s\"'`]+", f)})[:10]:
    try:
        rr = requests.get(u, headers=UA, timeout=30)
        print(f"   {rr.status_code} {len(rr.content):>8} byte  {u[:120]}")
        print("      " + rr.text[:300].replace("\n", " "))
    except Exception as e:
        print(f"   {type(e).__name__} {u[:120]}")
