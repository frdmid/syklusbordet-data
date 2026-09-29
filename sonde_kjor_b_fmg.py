# ---------------------------------------------------------------------------
# sonde_kjor_b_fmg: Fortescue sine tall til tilbudsskaaren B for jernmalm
#
# B for jernmalm bygges fra 28.09.2026 av Kumba, Vales jernmalmsegment og
# Champion (b_manuell.json). Fortescue mangler fordi linjen "Payments for
# property, plant and equipment" ikke kunne leses fra nettverktoeyene her.
# Denne sonden henter aarsrapportene og skriver ut:
#   1. konsernets kontantstroemoppstilling (hele siden)
#   2. linjene med avskrivninger (Depreciation and amortisation)
#   3. segmentnoten (Hematite, Magnetite/Iron Bridge, Energy/Metals), slik at
#      investeringene i Fortescue Energy kan trekkes fra og tallet blir rent
#      jernmalm
# Sonden endrer ingenting. Tallene leses av for haand til b_manuell.json.
# ---------------------------------------------------------------------------

import io, re, subprocess, sys, time
import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
try:
    import pymupdf as fitz
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "pymupdf"], check=False)
    import pymupdf as fitz

C = "https://content.fortescue.com/fortescue17114-fortescueeb60-productionbbdb-8be5/media/project/fortescueportal/shared"
A = "https://announcements.asx.com.au/asxpdf"
H = "https://www.annualreports.com/HostedData/AnnualReportArchive/F"
RAPPORTER = {
    2026: [f"{C}/documents/regulatory/asx-announcements/fy26-annual-report_-app4e_updated.pdf"],
    2025: [f"{C}/documents/regulatory/asx-announcements/2935109-fy25-annual-report-and-appendix-4e.pdf"],
    2024: [f"{C}/docs/default-source/announcements-and-reports/fy24-annual-report.pdf"],
    2023: [f"{A}/20230828/pdf/05t4vq395zntr7.pdf", f"{C}/docs/default-source/announcements-and-reports/fy23-annual-report.pdf"],
    2022: [f"{A}/20220829/pdf/45ddl54gvmcnkk.pdf"],
    2021: [f"{A}/20210830/pdf/44zww94mcxk24f.pdf",
           f"{C}/docs/default-source/announcements-and-reports/fy21-annual-report-and-appendix-4eaa5cc29666e84da49761411885c73c37.pdf"],
    2020: [f"{C}/docs/default-source/uncategorised/fy20-annual-report-and-4e.pdf", f"{A}/20200824/pdf/44lsxhjtpkslkg.pdf"],
    2019: [f"{A}/20190826/pdf/447tyyqlrwgq17.pdf"],
    2018: [f"{A}/20180820/pdf/43xgg2jwrzbys0.pdf"],
    2017: [f"{A}/20170821/pdf/43lk8yq7n6mrvq.pdf"],
    2016: [f"{A}/20160822/pdf/439hbg830g3669.pdf", f"{H}/ASX_FMG_2016.pdf"],
    2015: [f"{A}/20150824/pdf/430qp1hq3gks21.pdf", f"{H}/ASX_FMG_2015.pdf"],
    2014: [f"{H}/ASX_FMG_2014.pdf"],
    2013: [f"{H}/ASX_FMG_2013.pdf"],
    2012: [f"{H}/ASX_FMG_2012.pdf"],
    2011: [f"{H}/ASX_FMG_2011.pdf"],
    2010: [f"{H}/ASX_FMG_2010.pdf"],
    2009: [f"{H}/ASX_FMG_2009.pdf"],
    2008: [f"{H}/ASX_FMG_2008.pdf"],
}
NOKKEL = re.compile(r"payments?\s+for\s+(property|exploration|development|deposits|mine|capital)"
                    r"|depreciation\s+and\s+amorti[sz]ation|capital\s+expenditure", re.I)


def hent(url):
    try:
        r = requests.get(url, headers=UA, timeout=240)
    except Exception as e:
        print(f"   {type(e).__name__}  {url}")
        return None
    ok = r.status_code == 200 and r.content[:4] == b"%PDF"
    print(f"   {r.status_code}  {len(r.content) // 1000:>6} kB  {'PDF' if ok else 'ikke PDF'}  {url}")
    return r.content if ok else None


def les(b, fy):
    with fitz.open(stream=b, filetype="pdf") as d:
        sider = [(i + 1, p.get_text()) for i, p in enumerate(d)]
    print(f"   {len(sider)} sider")
    # 1. Konsernets kontantstroemoppstilling: foerste side med overskriften og
    #    baade drift og investering.
    ks = [(s, t) for s, t in sider
          if re.search(r"statement\s+of\s+cash\s+flows|cash\s+flow\s+statement", t, re.I)
          and re.search(r"operating\s+activities", t, re.I) and re.search(r"investing\s+activities", t, re.I)
          and re.search(r"payments?\s+for\s+property", t, re.I)]
    for s, t in ks[:1]:
        print(f"\n   ---- KONTANTSTROEM FY{fy}, side {s}")
        for l in [x for x in t.split("\n") if x.strip()][:95]:
            print(f"      {l[:140]}")
    # 2. Noekkellinjer i hele rapporten, med tallene som foelger
    print(f"\n   ---- NOEKKELLINJER FY{fy}")
    n = 0
    for s, t in sider:
        ll = [x.strip() for x in t.split("\n") if x.strip()]
        for i, l in enumerate(ll):
            if NOKKEL.search(l) and len(l) < 120:
                tall = [x for x in ll[i + 1:i + 5] if re.fullmatch(r"[\(\-]?[\d,\.]+\)?|\d+(,\s*\d+)*", x)]
                print(f"      s.{s:<4} {l[:100]}   -> {' | '.join(tall)}")
                n += 1
        if n > 60:
            break
    # 3. Segmentnoten
    seg = [(s, t) for s, t in sider if re.search(r"operating\s+segments|segment\s+information", t, re.I)
           and re.search(r"hematite|energy|metals|iron\s+bridge|magnetite", t, re.I)
           and re.search(r"capital\s+expenditure|depreciation", t, re.I)]
    for s, t in seg[:2]:
        print(f"\n   ---- SEGMENT FY{fy}, side {s}")
        for l in [x for x in t.split("\n") if x.strip()][:90]:
            print(f"      {l[:140]}")


for fy in sorted(RAPPORTER, reverse=True):
    print(f"\n\n==================== FY{fy}")
    for u in RAPPORTER[fy]:
        b = hent(u)
        if b:
            try:
                les(b, fy)
            except Exception as e:
                print(f"   lesefeil {type(e).__name__}: {str(e)[:100]}")
            break
        time.sleep(1)

print("\nSend utskriften til Claude. Tallene leses av for haand til b_manuell.json.")
