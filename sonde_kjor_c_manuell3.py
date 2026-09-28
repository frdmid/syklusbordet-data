# ---------------------------------------------------------------------------
# sonde_kjor_c_manuell3: tredje runde for C, DNO og Whitecap
#
# Brent holdes etter det parallelle signalet til desember 2027, og WTI likeså.
# Porten for Brent kommer fra 28.09.2026 fra Aker BP (c_manuell.json). DNO og
# Whitecap mangler fortsatt. Denne sonden skriver ut tallene som trengs, slik
# at de kan leses av for haand til c_manuell.json. Sonden endrer ingenting.
#
# DNO: runde 2 fant alle aarsrapportene som vedlegg paa NewsWeb, men lenken
# ga en HTML-side paa 3,7 kB. Her proeves flere adresser paa det foerste
# vedlegget, og den som gir en PDF eller ZIP brukes for resten. Fra 2021
# ligger ESEF-filen (iXBRL i ZIP) ved siden av PDF-en; den leses maskinelt.
# Eldre aar leses fra PDF-oppstillingene.
#
# Whitecap: kanadisk, ikke hos SEC. Aarsregnskapene hentes fra selskapets
# egne sider.
#
# Det som trengs per selskap: kontantstroem fra driften for hvert aar (hele
# historikken), og for siste aar kontanter, langsiktig rentebaerende gjeld,
# egenkapital og betalte renter.
# ---------------------------------------------------------------------------

import io, re, subprocess, sys, time, zipfile
import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
API = "https://api3.oslo.oslobors.no/v1/newsreader"

try:
    import pymupdf as fitz
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "pymupdf"], check=False)
    try:
        import pymupdf as fitz
    except ImportError:
        fitz = None
if fitz is None:
    import pdfplumber


def sider(b):
    if fitz is not None:
        with fitz.open(stream=b, filetype="pdf") as d:
            for i, p in enumerate(d):
                yield i + 1, p.get_text()
    else:
        with pdfplumber.open(io.BytesIO(b)) as d:
            for i, p in enumerate(d.pages):
                yield i + 1, p.extract_text() or ""


def skriv_oppstillinger(b, maks_linjer=75):
    """Skriver konsernets kontantstroemoppstilling og balanse (begge sider)."""
    ks, bs = [], []
    for s, t in sider(b):
        if re.search(r"operating\s+activities", t, re.I) and re.search(r"investing\s+activities", t, re.I) \
           and re.search(r"cash\s+and\s+cash\s+equivalents", t, re.I):
            ks.append((s, t))
        if re.search(r"total\s+equity", t, re.I) and \
           re.search(r"cash\s+and\s+cash\s+equivalents|interest.bearing|bond|borrowings|long.term\s+debt", t, re.I):
            bs.append((s, t))
    print(f"   {s} sider, kontantstroem-kandidater {[x[0] for x in ks[:6]]}, balanse-kandidater {[x[0] for x in bs[:6]]}")
    # Oppstillingene staar foran notene; ta de to foerste treffene av hver.
    for navn, liste in (("KONTANTSTROEM", ks[:2]), ("BALANSE", bs[:2])):
        for s, t in liste:
            print(f"\n   ---- {navn}, side {s}")
            for l in [x for x in t.split("\n") if x.strip()][:maks_linjer]:
                print(f"      {l[:150]}")


# ------------------------------------------------------------------ ESEF-lesing
BEGREP = re.compile(r"CashFlowsFromUsedInOperatingActivities|^CashAndCashEquivalents$|InterestPaid|^Equity$"
                    r"|Borrowings|BondsIssued|Bond|InterestBearing|LoansReceived|Debt", re.I)


def les_esef(zb):
    z = zipfile.ZipFile(io.BytesIO(zb))
    navn = [n for n in z.namelist() if re.search(r"\.x?html?$", n, re.I) and "/reports/" in n.replace("\\", "/")]
    if not navn:
        navn = [n for n in z.namelist() if re.search(r"\.x?html?$", n, re.I)]
    print(f"   ESEF: {len(z.namelist())} filer, rapport {navn[:2]}")
    if not navn:
        return
    x = z.read(navn[0]).decode("utf-8", "ignore")
    # kontekster: id -> (periode, har dimensjon)
    ktx = {}
    for m in re.finditer(r"<xbrli:context\b[^>]*\bid=\"([^\"]+)\"[^>]*>(.*?)</xbrli:context>", x, re.S):
        body = m.group(2)
        dim = bool(re.search(r"explicitMember|typedMember", body))
        inst = re.search(r"<xbrli:instant>([^<]+)<", body)
        slutt = re.search(r"<xbrli:endDate>([^<]+)<", body)
        start = re.search(r"<xbrli:startDate>([^<]+)<", body)
        per = inst.group(1) if inst else (f"{start.group(1)}..{slutt.group(1)}" if slutt else "?")
        ktx[m.group(1)] = (per, dim)
    funn = {}
    for m in re.finditer(r"<ix:nonFraction\b([^>]*)>(.*?)</ix:nonFraction>", x, re.S):
        a = m.group(1)
        nm = re.search(r"\bname=\"([^\"]+)\"", a)
        cr = re.search(r"\bcontextRef=\"([^\"]+)\"", a)
        if not nm or not cr:
            continue
        begrep = nm.group(1).split(":")[-1]
        if not BEGREP.search(begrep):
            continue
        per, dim = ktx.get(cr.group(1), ("?", True))
        if dim:
            continue
        sc = re.search(r"\bscale=\"(-?\d+)\"", a)
        tekst = re.sub(r"<[^>]+>", "", m.group(2)).strip()
        fmt = re.search(r"\bformat=\"([^\"]+)\"", a)
        fmt = fmt.group(1) if fmt else ""
        if "numcommadecimal" in fmt:
            tall = tekst.replace(".", "").replace(" ", "").replace(",", ".")
        else:
            tall = tekst.replace(",", "").replace(" ", "")
        try:
            v = float(tall) if tall not in ("", "-") else 0.0
        except ValueError:
            continue
        if re.search(r"\bsign=\"-\"", a):
            v = -v
        v = v * 10 ** int(sc.group(1)) if sc else v
        funn[(nm.group(1), per)] = v
    for (b, per), v in sorted(funn.items()):
        print(f"      {b:75s} {per:25s} {v / 1e6:14,.1f} mill")


# ------------------------------------------------------------------------- DNO
print("1. DNO via NewsWeb\n")
# (melding, vedlegg, navn) fra runde 2
DNO = [
    (668073, 321006, "2025 Annual Report.pdf"), (668073, 321010, "ESEF 2025.zip"),
    (642876, 301342, "2024 Annual Report.pdf"), (642876, 301345, "ESEF 2024.zip"),
    (613370, 278246, "2023 Annual Report.pdf"), (613370, 278250, "ESEF 2023.zip"),
    (585329, 256661, "2022 Annual Report.pdf"), (585329, 256659, "ESEF 2022.zip"),
    (556782, 234728, "2021 Annual Report.pdf"), (556782, 234734, "ESEF 2021.zip"),
    (528016, 213606, "2020 Annual Report.pdf"),
    (498689, 194987, "Annual Report and Accounts 2019.pdf"),
    (473009, 180952, "Annual Report 2018.pdf"),
    (446557, 8743, "Annual Report 2017.pdf"),
    (422692, 22276, "Annual Report 2016.pdf"),
    (397676, 35168, "Annual Report 2015.pdf"),
    (373874, 47309, "Annual Report 2014.pdf"),
    (351649, 57813, "Annual Report 2013.pdf"),
    (326922, 69133, "Annual Report 2012.pdf"),
    (304052, 79719, "Annual Report 2011.pdf"),
    (281358, 90648, "Annual Report 2010.pdf"),
    (236288, 111879, "Annual Report 2008.pdf"),
    (212230, 121320, "Annual Report 2007.pdf"),
]
VARIANTER = [
    "{api}/attachment?messageId={m}&attachmentId={a}",
    "{api}/message/attachment?messageId={m}&attachmentId={a}",
    "{api}/attachment/{m}/{a}",
    "https://newsweb.oslobors.no/obsvc/attachment.obsvc?messageId={m}&attachmentId={a}",
    "https://newsweb.oslobors.no/message/attachment?messageId={m}&attachmentId={a}",
]


def ok_fil(b):
    return b[:4] == b"%PDF" or b[:2] == b"PK"


virker = None
m0, a0, _ = DNO[0]
for v in VARIANTER:
    url = v.format(api=API, m=m0, a=a0)
    try:
        r = requests.get(url, headers=UA, timeout=120)
        print(f"   {r.status_code}  {len(r.content):>10} byte  {r.content[:8]!r}  {url}")
        if r.status_code == 200 and ok_fil(r.content):
            virker = v
            break
        if r.status_code == 200 and len(r.content) < 20000:
            # kan vaere JSON med innholdet base64-kodet eller en lenke
            print(f"      innhold: {r.text[:300]!r}")
    except Exception as e:
        print(f"   {type(e).__name__}: {str(e)[:80]}  {url}")
    time.sleep(1)

if virker is None:
    print("\n   Ingen NewsWeb-adresse ga fil. Proever dno.no direkte for 2025.")
    for url in ["https://www.dno.no/media/kfgni4kw/2025-annual-report.pdf"]:
        try:
            r = requests.get(url, headers=UA, timeout=180)
            print(f"   {r.status_code}  {len(r.content)} byte  {url}")
            if r.status_code == 200 and ok_fil(r.content):
                skriv_oppstillinger(r.content)
        except Exception as e:
            print(f"   {type(e).__name__}: {str(e)[:80]}")
else:
    print(f"\n   Bruker {virker}\n")
    for m, a, navn in DNO:
        url = virker.format(api=API, m=m, a=a)
        try:
            r = requests.get(url, headers=UA, timeout=240)
        except Exception as e:
            print(f"\n=== DNO {navn}: {type(e).__name__}")
            continue
        print(f"\n=== DNO {navn}  ({len(r.content) // 1000} kB)")
        if r.status_code != 200 or not ok_fil(r.content):
            print(f"   HTTP {r.status_code}, ikke fil")
            continue
        try:
            if r.content[:2] == b"PK":
                les_esef(r.content)
            else:
                skriv_oppstillinger(r.content)
        except Exception as e:
            print(f"   lesefeil {type(e).__name__}: {str(e)[:100]}")
        time.sleep(1)

# -------------------------------------------------------------------- Whitecap
print("\n\n2. Whitecap Resources\n")
lenker = []
for side in ["https://www.wcap.ca/investors/financial-reporting",
             "https://www.wcap.ca/investors/financial-reports",
             "https://www.wcap.ca/investors/reports-and-filings",
             "https://www.wcap.ca/investors",
             "https://www.wcap.ca/investors/annual-reports"]:
    try:
        r = requests.get(side, headers=UA, timeout=60)
        l = re.findall(r'href="([^"]+\.pdf[^"]*)"', r.text, re.I)
        l = [u if u.startswith("http") else "https://www.wcap.ca" + ("" if u.startswith("/") else "/") + u for u in l]
        print(f"   {r.status_code}  {len(l):3d} pdf-lenker  {side}")
        lenker += l
    except Exception as e:
        print(f"   {type(e).__name__}  {side}")
    time.sleep(1)
lenker = list(dict.fromkeys(lenker))
for u in lenker[:80]:
    print(f"      {u}")
aars = [u for u in lenker if re.search(r"annual|year.?end|ye.?fs|q4|fs.?20\d\d|20\d\d.?fs|financial.?statements", u, re.I)
        and not re.search(r"q[1-3]\b|q[1-3][-_ ]|interim|aif|sustainab|esg|proxy|circular|presentation|guidance", u, re.I)]
print(f"\n   {len(aars)} kandidater til aarsregnskap")
for u in aars[:14]:
    try:
        r = requests.get(u, headers=UA, timeout=180)
    except Exception as e:
        print(f"\n=== WCP {u}: {type(e).__name__}")
        continue
    print(f"\n=== WCP {u}  ({len(r.content) // 1000} kB)")
    if r.status_code == 200 and r.content[:4] == b"%PDF":
        try:
            skriv_oppstillinger(r.content, maks_linjer=65)
        except Exception as e:
            print(f"   lesefeil {type(e).__name__}: {str(e)[:100]}")
    else:
        print(f"   HTTP {r.status_code}, ikke PDF")
    time.sleep(1)

print("\nSend utskriften til Claude. Tallene leses av for haand til c_manuell.json.")
