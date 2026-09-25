# ---------------------------------------------------------------------------
# sonde_kjor_c_manuell: grunnlag for engangslesing av C for DNO og Aker BP
#
# Brent har ingen overlevelsesport, fordi papirene (DNO, Aker BP) ikke filer
# hos SEC, og de frie kildene gir bare fem til sju aar. C trenger det verste
# aaret gjennom en hel syklus. Historikken endrer seg ikke, saa den kan leses
# av aarsrapportene EN gang og legges i repoet som c_manuell.json. Nye aar
# kan senere hentes automatisk.
#
# Denne sonden finner aarsrapportene paa selskapenes egne sider, laster dem
# ned og skriver ut linjene fra kontantstroemoppstillingen som C trenger:
#   drift     netto kontantstroem fra driften
#   renter    betalte renter
#   kontanter kontanter og kontantekvivalenter ved aarsslutt
#   gjeld     rentebaerende langsiktig gjeld
#   ek        sum egenkapital
# med side og enhet (USD million, NOK 1 000 og saa videre). Tallene skrives
# av for haand etterpaa og kontrolleres mot to aarsrapporter der aarene
# overlapper (hver rapport viser ogsaa aaret foer). Sonden endrer ingenting.
# ---------------------------------------------------------------------------

import io, re, time, logging
import requests, pdfplumber

logging.getLogger("pdfminer").setLevel(logging.ERROR)
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
SIDER = {
    "DNO": ["https://www.dno.no/en/investors/reports-and-presentations/annual-reports/",
            "https://www.dno.no/en/investors/reports-and-presentations/"],
    "Aker BP": ["https://akerbp.com/en/investor/reports/",
                "https://akerbp.com/en/investor-relations/reports-and-presentations/",
                "https://akerbp.com/en/investor/annual-reports/",
                "https://akerbp.com/en/investor-relations/"],
}
MOENSTER = {
    "drift": re.compile(r"(net\s+cash|cash\s+flows?).{0,40}(from|provided|generated).{0,30}operating\s+activities", re.I),
    "renter": re.compile(r"interest\s+(paid|expenses?\s+paid)", re.I),
    "kontanter": re.compile(r"cash\s+and\s+cash\s+equivalents\s+(at\s+(the\s+)?end|end\s+of|at\s+31)", re.I),
    "gjeld": re.compile(r"(interest[- ]bearing|long[- ]term)\s+(bank\s+)?(debt|loans|borrowings|bonds)", re.I),
    "ek": re.compile(r"^total\s+equity\b", re.I),
}
ENHET = re.compile(r"(USD|NOK)\s*(million|thousand|1\s*000|mill)|\(\s*(USD|NOK)\s*(million|thousand|1\s*000)\s*\)", re.I)


def lenker(side):
    r = requests.get(side, headers=UA, timeout=60)
    print(f"   {side}: HTTP {r.status_code}")
    if r.status_code != 200:
        return []
    ut = []
    for m in re.finditer(r'href="([^"]+?\.pdf[^"]*)"[^>]*>(.*?)</a>', r.text, re.I | re.S):
        u, tekst = m.group(1), re.sub(r"<[^>]+>|\s+", " ", m.group(2)).strip()
        if not u.startswith("http"):
            u = re.match(r"https?://[^/]+", side).group(0) + ("" if u.startswith("/") else "/") + u
        ut.append((u, tekst))
    return ut


for selskap, sider in SIDER.items():
    print(f"\n==================== {selskap}")
    alle = {}
    for s in sider:
        try:
            for u, t in lenker(s):
                alle[u] = t
        except Exception as e:
            print(f"   {s}: {type(e).__name__}: {str(e)[:80]}")
        time.sleep(1)
    aars = {u: t for u, t in alle.items() if re.search(r"annual|årsrapport|aarsrapport", u + " " + t, re.I)
            and not re.search(r"sustainab|climate|esg|payments|remuneration|governance", u + " " + t, re.I)}
    print(f"   {len(alle)} PDF-lenker, {len(aars)} ser ut som aarsrapporter")
    for u, t in sorted(aars.items()):
        print(f"      {t[:60]:60s} {u[:140]}")
    for u, t in sorted(aars.items()):
        print(f"\n   --- {t[:70]}  {u}")
        try:
            b = requests.get(u, headers=UA, timeout=180).content
            with pdfplumber.open(io.BytesIO(b)) as pdf:
                print(f"   {len(pdf.pages)} sider")
                vist = 0
                for i, sd in enumerate(pdf.pages):
                    txt = sd.extract_text() or ""
                    if not re.search(r"operating\s+activities", txt, re.I):
                        continue
                    if not re.search(r"statement\s+of\s+cash\s+flows?|cash\s+flow\s+statement", txt, re.I):
                        continue
                    enh = ENHET.search(txt)
                    print(f"   side {i + 1} (kontantstroem), enhet: {enh.group(0) if enh else 'ikke funnet'}")
                    for l in txt.split("\n"):
                        l = l.strip()
                        if re.search(r"^(amounts|figures|\(?usd|\(?nok|note\s|\d{4}\s+\d{4})", l, re.I) and vist < 400:
                            print(f"      hode: {l[:140]}")
                        for navn, m in MOENSTER.items():
                            if m.search(l):
                                print(f"      {navn:9s} {l[:140]}")
                    vist += 1
                    if vist >= 3:
                        break
                # balansen for egenkapital og gjeld
                for i, sd in enumerate(pdf.pages):
                    txt = sd.extract_text() or ""
                    if re.search(r"statement\s+of\s+financial\s+position|balance\s+sheet", txt, re.I) and \
                       re.search(r"total\s+equity", txt, re.I):
                        enh = ENHET.search(txt)
                        print(f"   side {i + 1} (balanse), enhet: {enh.group(0) if enh else 'ikke funnet'}")
                        for l in txt.split("\n"):
                            l = l.strip()
                            if MOENSTER["ek"].search(l) or MOENSTER["gjeld"].search(l) or MOENSTER["kontanter"].search(l) \
                               or re.search(r"^cash\s+and\s+cash\s+equivalents", l, re.I):
                                print(f"      balanse   {l[:140]}")
                        break
        except Exception as e:
            print(f"   {type(e).__name__}: {str(e)[:100]}")
        time.sleep(1)
