# ---------------------------------------------------------------------------
# sonde_kjor_b_kilder: finnes aarlige tilbudstall med lang historikk til B for
# metaller, palmeolje og kakao
#
# B mangler for jernmalm, nikkel, sink, bly, tinn, palmeolje og kakao. Planen
# (godkjent av Frode 25.09.2026) er EN akse per segment, lik for alle:
#   metaller    vekst i verdens gruveproduksjon (USGS)
#   palmeolje   produksjon og lager mot forbruk (USDA PSD)
#   kakao       areal og produksjon (FAOSTAT), kakaobonner, verden
# B er ikke testet som regel. Denne sonden maaler bare om dataene finnes og
# kan hentes fra Actions. Testen av B settes opp etterpaa, med kravene skrevet
# ned foer den kjoeres.
#
# Krav satt foer kjoering, per serie: aarlig, starter senest 1990, siste aar
# er hoeyst to aar gammelt (i 2026: 2024 eller nyere).
# ---------------------------------------------------------------------------

import io, re, time, zipfile
import pandas as pd
import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
AAR_NAA = pd.Timestamp.now().year
RES = []


def vurder(navn, s, kilde):
    s = s.dropna().sort_index()
    if s.empty:
        print(f"   {navn}: tom"); return
    ok = int(s.index[0]) <= 1990 and int(s.index[-1]) >= AAR_NAA - 2
    RES.append((navn, int(s.index[0]), int(s.index[-1]), len(s), ok, kilde))
    print(f"   {navn}: {s.index[0]} til {s.index[-1]}, {len(s)} aar -> {'KANDIDAT' if ok else 'nei'}")
    print(f"      siste fem: {', '.join(f'{a}:{v:,.0f}' for a, v in s.tail(5).items())}")


# ================================================================ USGS
print("1. USGS, historisk global statistikk")
METALLER = {"jernmalm": r"iron[\s_-]*ore", "nikkel": r"nickel", "sink": r"zinc", "bly": r"lead",
            "tinn": r"\btin\b|[-_/]tin[-_.]", "kobber": r"copper", "aluminium": r"bauxite|alumin"}
SIDER = ["https://www.usgs.gov/centers/national-minerals-information-center/historical-global-statistics-mineral-and-material",
         "https://www.usgs.gov/centers/national-minerals-information-center/historical-statistics-mineral-commodities-united"]
lenker = {}
for side in SIDER:
    try:
        r = requests.get(side, headers=UA, timeout=60)
        print(f"   {side[-70:]}: HTTP {r.status_code}")
        for m in re.finditer(r'href="([^"]+)"[^>]*>(.*?)</a>', r.text, re.I | re.S):
            u, t = m.group(1), re.sub(r"<[^>]+>|\s+", " ", m.group(2)).strip()
            if not u.startswith("http"):
                u = "https://www.usgs.gov" + u
            if re.search(r"\.xlsx?|/media/files/|data-series|global", u, re.I):
                lenker[u] = t
    except Exception as e:
        print(f"   {side[-70:]}: {type(e).__name__}: {str(e)[:80]}")
    time.sleep(1)
print(f"   {len(lenker)} lenker til filer eller filsider")


def les_xlsx(url):
    """Henter en fil; er det en side, foelg foerste .xlsx-lenke paa den."""
    r = requests.get(url, headers=UA, timeout=90)
    if r.content[:2] == b"PK":
        return r.content, url
    m = re.search(r'href="([^"]+\.xlsx[^"]*)"', r.text, re.I)
    if not m:
        return None, url
    u = m.group(1)
    u = u if u.startswith("http") else "https://www.usgs.gov" + u
    r2 = requests.get(u, headers=UA, timeout=90)
    return (r2.content if r2.content[:2] == b"PK" else None), u


for seg, moenster in METALLER.items():
    kand = [(u, t) for u, t in lenker.items() if re.search(moenster, u + " " + t, re.I)]
    kand.sort(key=lambda x: (0 if re.search(r"global|world", x[0] + x[1], re.I) else 1, x[0]))
    print(f"\n   --- {seg}: {len(kand)} lenker")
    for u, t in kand[:6]:
        print(f"      {t[:60]:60s} {u[:120]}")
    for u, t in kand[:3]:
        try:
            b, fil = les_xlsx(u)
            if not b:
                print(f"      ingen xlsx bak {u[:90]}"); continue
            ark = pd.read_excel(io.BytesIO(b), sheet_name=None, header=None)
            print(f"      fil {fil[:110]}")
            funnet = False
            for navn, df in ark.items():
                df = df.astype(object)
                # rad med kolonneoverskrifter: den foerste med "year"
                hode = next((i for i in range(min(15, len(df)))
                             if any(re.fullmatch(r"\s*year\s*", str(x), re.I) for x in df.iloc[i].tolist())), None)
                if hode is None:
                    continue
                kol = [str(x).strip() for x in df.iloc[hode].tolist()]
                print(f"      ark '{navn}' {df.shape}, kolonner: {' | '.join(k[:28] for k in kol[:14])}")
                aarkol = next(j for j, k in enumerate(kol) if re.fullmatch(r"year", k, re.I))
                for j, k in enumerate(kol):
                    if re.search(r"world.*(mine|production)|(mine|production).*world|world\s*production", k, re.I):
                        v = {}
                        for i in range(hode + 1, len(df)):
                            a = pd.to_numeric(df.iat[i, aarkol], errors="coerce")
                            x = pd.to_numeric(str(df.iat[i, j]).replace(",", ""), errors="coerce")
                            if pd.notna(a) and pd.notna(x) and 1800 <= a <= 2100:
                                v[int(a)] = float(x)
                        vurder(f"{seg} ({k[:40]})", pd.Series(v), fil.split("/")[-1][:60])
                        funnet = True
            if funnet:
                break
        except Exception as e:
            print(f"      {type(e).__name__}: {str(e)[:90]}")
        time.sleep(1)


# ================================================================ USDA PSD
print("\n2. USDA PSD, palmeolje")
try:
    r = requests.get("https://apps.fas.usda.gov/psdonline/downloads/psd_oilseeds_csv.zip", headers=UA, timeout=120)
    print(f"   HTTP {r.status_code}, {len(r.content)} byte")
    z = zipfile.ZipFile(io.BytesIO(r.content))
    navn = z.namelist()[0]
    d = pd.read_csv(z.open(navn), low_memory=False)
    print(f"   {navn}: {d.shape}, kolonner {list(d.columns)[:12]}")
    p = d[d["Commodity_Description"].str.contains("Palm", case=False, na=False)]
    print(f"   varer: {sorted(p['Commodity_Description'].unique())[:6]}")
    p = p[p["Commodity_Description"].str.fullmatch(r"Oil, Palm", case=False, na=False)]
    print(f"   attributter: {sorted(p['Attribute_Description'].unique())}")
    for attr in ("Production", "Ending Stocks", "Domestic Consumption"):
        q = p[p["Attribute_Description"] == attr].groupby("Market_Year")["Value"].sum()
        vurder(f"palmeolje, verden, {attr}", q, "USDA PSD oilseeds")
    prod = p[p["Attribute_Description"] == "Production"].groupby("Market_Year")["Value"].sum()
    lag = p[p["Attribute_Description"] == "Ending Stocks"].groupby("Market_Year")["Value"].sum()
    forb = p[p["Attribute_Description"] == "Domestic Consumption"].groupby("Market_Year")["Value"].sum()
    su = (lag / forb * 100).dropna()
    vurder("palmeolje, lager mot forbruk (%)", su, "USDA PSD oilseeds")
except Exception as e:
    print(f"   {type(e).__name__}: {str(e)[:120]}")


# ================================================================ FAOSTAT
print("\n3. FAOSTAT, kakaobonner")
try:
    x = requests.get("https://bulks-faostat.fao.org/production/datasets_E.xml", headers=UA, timeout=60).text
    urls = re.findall(r"<FileLocation>(.*?)</FileLocation>", x)
    fil = next((u for u in urls if "Production_Crops_Livestock_E_All_Data_(Normalized)" in u), None)
    fil = fil or "https://bulks-faostat.fao.org/production/Production_Crops_Livestock_E_All_Data_(Normalized).zip"
    print(f"   {fil}")
    r = requests.get(fil, headers=UA, timeout=300)
    print(f"   HTTP {r.status_code}, {len(r.content) / 1e6:.1f} MB")
    z = zipfile.ZipFile(io.BytesIO(r.content))
    csvnavn = next(n for n in z.namelist() if n.endswith(".csv") and "All_Data" in n)
    biter = []
    for bit in pd.read_csv(z.open(csvnavn), encoding="latin-1", chunksize=500000, low_memory=False):
        biter.append(bit[bit["Item"].astype(str).str.contains("Cocoa", case=False, na=False)])
    k = pd.concat(biter)
    print(f"   varer: {sorted(k['Item'].unique())}, elementer: {sorted(k['Element'].unique())}")
    k = k[k["Item"].str.fullmatch(r"Cocoa beans", case=False, na=False)]
    # Omraadekoder i stedet for navn, saa tegnsettet i filen ikke spiller inn:
    # 5000 verden, 107 Elfenbenskysten, 81 Ghana.
    for kode, omr in ((5000, "verden"), (107, "Elfenbenskysten"), (81, "Ghana")):
        for el in ("Area harvested", "Production"):
            q = k[(pd.to_numeric(k["Area Code"], errors="coerce") == kode) & (k["Element"] == el)]
            q = q.groupby("Year")["Value"].sum()
            vurder(f"kakao, {omr}, {el}", q, "FAOSTAT QCL")
except Exception as e:
    print(f"   {type(e).__name__}: {str(e)[:120]}")


print("\n4. Oppsummering")
for navn, fra, til, n, ok, kilde in RES:
    print(f"   {navn:52s} {fra}-{til} ({n} aar)  {'KANDIDAT' if ok else 'nei'}  [{kilde}]")
