# ---------------------------------------------------------------------------
# sonde_kjor_c_manuell2: andre runde for engangslesingen av C
#
# Foerste runde (25.09.2026) fant alle Aker BP sine aarsrapporter fra 2006 og
# leste kontantstroemmen fra driften for de fleste aar. Tre hull: 2019 (2020-
# rapporten ga ingen oppstilling), 2014 (teksten kom ut omrokert) og siste
# kontanter og betalte renter (2024 og 2025). DNO sine sider svarte 403.
#
# Her skrives HELE sidene med kontantstroemoppstilling og balanse ut for de
# rapportene som mangler, slik at tallene kan leses av for haand. DNO proeves
# via Oslo Boers NewsWeb, der aarsrapportene ligger som vedlegg til
# boersmeldingene. Sonden endrer ingenting.
# ---------------------------------------------------------------------------

import io, json, re, time, logging
import requests, pdfplumber

logging.getLogger("pdfminer").setLevel(logging.ERROR)
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}


def sider_med(pdf, krav):
    ut = []
    for i, s in enumerate(pdf.pages):
        t = s.extract_text() or ""
        if all(re.search(k, t, re.I) for k in krav):
            ut.append((i, t))
    return ut


def skriv_oppstillinger(b, maks_linjer=90):
    with pdfplumber.open(io.BytesIO(b)) as pdf:
        print(f"   {len(pdf.pages)} sider")
        ks = sider_med(pdf, [r"operating\s+activities", r"investing\s+activities",
                             r"cash\s+and\s+cash\s+equivalents"])
        bs = sider_med(pdf, [r"total\s+equity", r"total\s+(non-current\s+)?liabilities|interest-bearing"])
        for navn, liste in (("KONTANTSTROEM", ks[:2]), ("BALANSE", bs[:2])):
            for i, t in liste:
                print(f"\n   ---- {navn}, side {i + 1}")
                for l in [x for x in t.split("\n") if x.strip()][:maks_linjer]:
                    print(f"      {l[:150]}")


print("1. Aker BP, rapportene med hull")
for u in ["https://akerbp.com/wp-content/uploads/2021/03/akerbp-annual-report-2020.pdf",
          "https://akerbp.com/wp-content/uploads/2021/02/detnor-annual-report-2014.pdf",
          "https://akerbp.com/wp-content/uploads/2025/04/annual-report-2024.pdf",
          "https://akerbp.com/wp-content/uploads/2026/03/akerbp-annual-report-2025.pdf",
          "https://akerbp.com/wp-content/uploads/2021/02/detnor-annual-report-2010.pdf"]:
    print(f"\n=== {u}")
    try:
        r = requests.get(u, headers=UA, timeout=180)
        print(f"   HTTP {r.status_code}, {len(r.content)} byte")
        if r.status_code == 200:
            skriv_oppstillinger(r.content)
    except Exception as e:
        print(f"   {type(e).__name__}: {str(e)[:100]}")
    time.sleep(1)

print("\n\n2. DNO via NewsWeb")
API = "https://api3.oslo.oslobors.no/v1/newsreader"
funnet = []
for fra, til in [("2008-01-01", "2013-12-31"), ("2014-01-01", "2019-12-31"), ("2020-01-01", "2026-09-30")]:
    for metode in ("post", "get"):
        try:
            par = {"category": "", "issuer": "DNO", "fromDate": fra, "toDate": til, "market": "",
                   "messageTitle": "annual report"}
            r = (requests.post if metode == "post" else requests.get)(f"{API}/list", params=par,
                                                                     headers={**UA, "Accept": "application/json"}, timeout=60)
            print(f"   {fra}..{til} {metode.upper()}: HTTP {r.status_code}, {len(r.content)} byte")
            if r.status_code != 200:
                continue
            d = r.json()
            msgs = (d.get("data") or {}).get("messages") or d.get("messages") or []
            print(f"      {len(msgs)} meldinger")
            for m in msgs[:40]:
                print(f"      {m.get('messageId')} {str(m.get('publishedTime'))[:10]} {str(m.get('title'))[:90]}")
                if re.search(r"annual\s+report", str(m.get("title")), re.I):
                    funnet.append(m)
            break
        except Exception as e:
            print(f"   {fra}..{til} {metode}: {type(e).__name__}: {str(e)[:80]}")
    time.sleep(1)

sett = set()
for m in funnet:
    mid = m.get("messageId")
    if mid in sett:
        continue
    sett.add(mid)
    try:
        r = requests.get(f"{API}/message", params={"messageId": mid}, headers={**UA, "Accept": "application/json"}, timeout=60)
        d = r.json()
        msg = (d.get("data") or {}).get("message") or d.get("message") or d
        vedl = msg.get("attachments") or []
        print(f"\n=== DNO melding {mid} {str(msg.get('publishedTime'))[:10]} {str(msg.get('title'))[:80]}: {len(vedl)} vedlegg")
        for a in vedl:
            navn, aid = a.get("name") or a.get("fileName") or "", a.get("id") or a.get("attachmentId")
            print(f"      vedlegg {aid} {navn[:80]}")
            if not re.search(r"\.pdf$", navn, re.I) or re.search(r"esg|sustainab|climate|remuneration|payments", navn, re.I):
                continue
            url = f"https://newsweb.oslobors.no/obsvc/attachment.obsvc?messageId={mid}&attachmentId={aid}&obsvc.item=1"
            b = requests.get(url, headers=UA, timeout=180)
            print(f"      henter: HTTP {b.status_code}, {len(b.content)} byte")
            if b.status_code == 200 and b.content[:4] == b"%PDF":
                skriv_oppstillinger(b.content, maks_linjer=70)
            time.sleep(1)
    except Exception as e:
        print(f"   melding {mid}: {type(e).__name__}: {str(e)[:100]}")
