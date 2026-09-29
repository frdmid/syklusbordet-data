# ---------------------------------------------------------------------------
# sonde_kjor_sgx_cot: andre forsoek paa SGX sin COT for jernmalm (29.09.2026).
# Foerste forsoek (sonde_kjor_cot_palme_sgx) fant at SGX-sidene henter filer
# via api2.sgx.com/content-api med queryId=<CMS-versjon>:fsp_files og en
# fspFileType. Her finnes CMS-versjonen i skriptene, og noen sannsynlige
# filtyper for COT proeves. Bygger ingenting.
# ---------------------------------------------------------------------------
import json, re, time
import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36", "Origin": "https://www.sgx.com",
      "Referer": "https://www.sgx.com/"}
side = requests.get("https://www.sgx.com/derivatives/commitment-of-traders", headers=UA, timeout=40).text
skript = sorted(set(re.findall(r'<script[^>]+src="([^"]+)"', side)))
versjoner, alle = set(), ""
for s in skript:
    u = s if s.startswith("http") else "https://www.sgx.com" + (s if s.startswith("/") else "/" + s)
    t = requests.get(u, headers=UA, timeout=40).text
    alle += t
    versjoner |= set(re.findall(r'CMS_VERSION["\']?\s*[:=]\s*["\']([^"\']+)["\']', t))
print("CMS-versjoner:", versjoner or "ingen funnet")
print("fspFileType-verdier i skriptene:", sorted(set(re.findall(r'fspFileType["\\]*:["\\]*([a-z_]+)', alle)))[:40])
print("Andre queryId-navn:", sorted(set(re.findall(r'queryId=\$\{[^}]+\}:([a-z_]+)', alle)))[:40])
kandidater = ["commitment_of_traders", "commitments_of_traders", "cot", "cot_report", "cot_reports",
              "derivatives_cot", "commitment_of_trader"]
for v in sorted(versjoner) or ["latest"]:
    for k in kandidater:
        url = ("https://api2.sgx.com/content-api?queryId=" + v + ":fsp_files&variables="
               + json.dumps({"fspFileType": k, "lang": "EN"}))
        try:
            r = requests.get(url, headers=UA, timeout=30)
            print(f"{r.status_code} {len(r.content):>7} {k:26s} {r.text[:200]}")
        except Exception as e:
            print(f"{type(e).__name__} {k}")
        time.sleep(0.5)
