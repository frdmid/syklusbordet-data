# ---------------------------------------------------------------------------
# Syklusbordet: diagnose 2.5
#
# Tre ting, ingen av dem endrer modellen. De avgjor hva som SKAL endres.
#
#   1. Aldersvekting i detrendingen. Skal 1960 telle like mye som 1990 naar
#      trenden estimeres i 2026. Testes paa alle 24 segmenter med full
#      historikk, med terskelen satt slik at hver variant flagger like ofte.
#      Uten den kontrollen ser fa flagg automatisk bedre ut.
#
#   2. BDI 2013-2026. Serien 1985-2013 ligger paa GitHub og er allerede lastet.
#      Hullet 2013-2019 er det som hindrer at den skjotes mot Fearnleys.
#      Ni kandidatkilder testes. Ingen antas aa virke.
#
#   3. Baltic per segment: BCI, BPI, BSI, BHSI, BDTI, BCTI. Samme sonde.
#
# Skriver bare bdi_hist.json og etterspørsel.json. Resten er utskrift.
# Colab-hemmelighet: GITHUB_TOKEN (scope repo)
# ---------------------------------------------------------------------------

REPO, BRANCH, TIMEOUT = "frdmid/syklusbordet-data", "main", 25

import base64, io, json, re, time, warnings
import numpy as np, pandas as pd, requests
warnings.filterwarnings("ignore")
try:
    from google.colab import userdata
    GITHUB_TOKEN = userdata.get("GITHUB_TOKEN")
except Exception:
    import os; GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
MIRROR = "https://raw.githubusercontent.com/datasets/"

# Maanedssnitt av daglige BDI-noteringer 1985-01 til 2013-06.
# Lastet ned fra GitHub og verifisert. Ligger her for aa ikke vaere
# avhengig av at en URL fortsatt svarer.
BDI_MND = {"1985-01":980, "1985-02":974, "1985-03":994, "1985-04":1044, "1985-05":1005, "1985-06":914, "1985-07":781, "1985-08":726, "1985-09":782, "1985-10":893, "1985-11":903, "1985-12":905, "1986-01":894, "1986-02":774, "1986-03":740, "1986-04":693, "1986-05":661, "1986-06":643, "1986-07":572, "1986-08":589, "1986-09":748, "1986-10":790, "1986-11":772, "1986-12":705, "1987-01":803, "1987-02":854, "1987-03":915, "1987-04":1012, "1987-05":1072, "1987-06":962, "1987-07":935, "1987-08":1089, "1987-09":1052, "1987-10":1106, "1987-11":1166, "1987-12":1254, "1988-01":1356, "1988-02":1522, "1988-03":1603, "1988-04":1505, "1988-05":1397, "1988-06":1267, "1988-07":1192, "1988-08":1222, "1988-09":1280, "1988-10":1320, "1988-11":1458, "1988-12":1514, "1989-01":1613, "1989-02":1532, "1989-03":1622, "1989-04":1621, "1989-05":1697, "1989-06":1418, "1989-07":1391, "1989-08":1409, "1989-09":1430, "1989-10":1534, "1989-11":1658, "1989-12":1600, "1990-01":1644, "1990-02":1594, "1990-03":1590, "1990-04":1443, "1990-05":1319, "1990-06":1213, "1990-07":1101, "1990-08":1213, "1990-09":1188, "1990-10":1243, "1990-11":1307, "1990-12":1440, "1991-01":1449, "1991-02":1596, "1991-03":1720, "1991-04":1602, "1991-05":1667, "1991-06":1707, "1991-07":1568, "1991-08":1492, "1991-09":1540, "1991-10":1608, "1991-11":1622, "1991-12":1532, "1992-01":1493, "1992-02":1307, "1992-03":1217, "1992-04":1172, "1992-05":1265, "1992-06":1170, "1992-07":1066, "1992-08":1067, "1992-09":1053, "1992-10":1062, "1992-11":1208, "1992-12":1360, "1993-01":1304, "1993-02":1328, "1993-03":1441, "1993-04":1501, "1993-05":1598, "1993-06":1545, "1993-07":1377, "1993-08":1390, "1993-09":1417, "1993-10":1371, "1993-11":1298, "1993-12":1232, "1994-01":1224, "1994-02":1154, "1994-03":1148, "1994-04":1287, "1994-05":1472, "1994-06":1345, "1994-07":1402, "1994-08":1480, "1994-09":1537, "1994-10":1808, "1994-11":1862, "1994-12":1992, "1995-01":2015, "1995-02":1990, "1995-03":2196, "1995-04":2257, "1995-05":2248, "1995-06":2006, "1995-07":1970, "1995-08":2091, "1995-09":2010, "1995-10":1716, "1995-11":1654, "1995-12":1622, "1996-01":1552, "1996-02":1435, "1996-03":1384, "1996-04":1454, "1996-05":1415, "1996-06":1272, "1996-07":1118, "1996-08":1089, "1996-09":1030, "1996-10":1132, "1996-11":1448, "1996-12":1491, "1997-01":1463, "1997-02":1439, "1997-03":1475, "1997-04":1380, "1997-05":1279, "1997-06":1273, "1997-07":1340, "1997-08":1294, "1997-09":1297, "1997-10":1324, "1997-11":1237, "1997-12":1235, "1998-01":1163, "1998-02":985, "1998-03":1055, "1998-04":982, "1998-05":982, "1998-06":897, "1998-07":840, "1998-08":800, "1998-09":872, "1998-10":984, "1998-11":959, "1998-12":844, "1999-01":803, "1999-02":836, "1999-03":967, "1999-04":921, "1999-05":1060, "1999-06":989, "1999-07":977, "1999-08":1046, "1999-09":1146, "1999-10":1339, "1999-11":1334, "1999-12":1337, "2000-01":1368, "2000-02":1393, "2000-03":1621, "2000-04":1666, "2000-05":1602, "2000-06":1589, "2000-07":1618, "2000-08":1639, "2000-09":1712, "2000-10":1734, "2000-11":1722, "2000-12":1608, "2001-01":1567, "2001-02":1479, "2001-03":1502, "2001-04":1439, "2001-05":1447, "2001-06":1377, "2001-07":1222, "2001-08":979, "2001-09":945, "2001-10":898, "2001-11":855, "2001-12":870, "2002-01":929, "2002-02":960, "2002-03":1066, "2002-04":1078, "2002-05":1032, "2002-06":1000, "2002-07":989, "2002-08":1003, "2002-09":1182, "2002-10":1365, "2002-11":1460, "2002-12":1682, "2003-01":1696, "2003-02":1674, "2003-03":1850, "2003-04":2066, "2003-05":2229, "2003-06":2136, "2003-07":2192, "2003-08":2287, "2003-09":2463, "2003-10":4163, "2003-11":4250, "2003-12":4643, "2004-01":5208, "2004-02":5450, "2004-03":5131, "2004-04":4496, "2004-05":3598, "2004-06":2902, "2004-07":3778, "2004-08":4172, "2004-09":4141, "2004-10":4539, "2004-11":5309, "2004-12":5319, "2005-01":4506, "2005-02":4532, "2005-03":4679, "2005-04":4532, "2005-05":3658, "2005-06":2749, "2005-07":2220, "2005-08":2225, "2005-09":2804, "2005-10":3161, "2005-11":2916, "2005-12":2556, "2006-01":2268, "2006-02":2444, "2006-03":2599, "2006-04":2469, "2006-05":2438, "2006-06":2718, "2006-07":3050, "2006-08":3687, "2006-09":4039, "2006-10":4028, "2006-11":4190, "2006-12":4350, "2007-01":4459, "2007-02":4398, "2007-03":5123, "2007-04":5733, "2007-05":6390, "2007-06":5772, "2007-07":6572, "2007-08":7199, "2007-09":8574, "2007-10":10425, "2007-11":10543, "2007-12":9685, "2008-01":7256, "2008-02":6874, "2008-03":8027, "2008-04":8287, "2008-05":10814, "2008-06":10245, "2008-07":8936, "2008-08":7390, "2008-09":4975, "2008-10":1808, "2008-11":819, "2008-12":750, "2009-01":899, "2009-02":1816, "2009-03":1958, "2009-04":1643, "2009-05":2517, "2009-06":3823, "2009-07":3362, "2009-08":2672, "2009-09":2351, "2009-10":2746, "2009-11":3941, "2009-12":3449, "2010-01":3161, "2010-02":2678, "2010-03":3207, "2010-04":3038, "2010-05":3838, "2010-06":3088, "2010-07":1910, "2010-08":2432, "2010-09":2712, "2010-10":2693, "2010-11":2329, "2010-12":2018, "2011-01":1399, "2011-02":1175, "2011-03":1489, "2011-04":1343, "2011-05":1352, "2011-06":1433, "2011-07":1366, "2011-08":1386, "2011-09":1843, "2011-10":2071, "2011-11":1835, "2011-12":1869, "2012-01":1091, "2012-02":706, "2012-03":866, "2012-04":1024, "2012-05":1106, "2012-06":934, "2012-07":1056, "2012-08":761, "2012-09":712, "2012-10":952, "2012-11":1017, "2012-12":872, "2013-01":774, "2013-02":745, "2013-03":873, "2013-04":875, "2013-05":851, "2013-06":806}


def get(url, **kw):
    r = requests.get(url, headers=kw.pop("headers", UA),
                     timeout=kw.pop("timeout", TIMEOUT), **kw)
    r.raise_for_status(); return r


def csv_series(url, monthly=False):
    d = pd.read_csv(io.StringIO(get(url).text)).iloc[:, :2]
    d.columns = ["Date", "Value"]
    d["Value"] = pd.to_numeric(d["Value"], errors="coerce"); d = d.dropna()
    if monthly:
        d["Date"] = pd.PeriodIndex(d["Date"].astype(str), freq="M")
        return d.set_index("Date")["Value"].sort_index()
    d["Date"] = pd.to_datetime(d["Date"])
    s = d.set_index("Date")["Value"].resample("ME").last().dropna()
    s.index = s.index.to_period("M"); return s


def pink_sheet():
    kand = []
    try:
        html = get("https://www.worldbank.org/en/research/commodity-markets", timeout=30).text
        kand += re.findall(r'https?://[^"\']*?CMO[^"\']*?Monthly[^"\']*?\.xlsx', html)
    except Exception as e:
        print(f"   CMO-lenkesok feilet: {str(e)[:60]}")
    kand.append("https://thedocs.worldbank.org/en/doc/18675f1d1639c7a34d463f59263ba0a2-"
                "0050012025/related/CMO-Historical-Data-Monthly.xlsx")
    for u in dict.fromkeys(kand):
        try:
            raw = get(u, timeout=90).content
            for skip in (4, 5, 6):
                try:
                    df = pd.read_excel(io.BytesIO(raw), sheet_name="Monthly Prices", skiprows=skip)
                    df = df.rename(columns={df.columns[0]: "t"})
                    m = df[df["t"].astype(str).str.match(r"^\d{4}M\d{1,2}$", na=False)]
                    if len(m) > 100:
                        m = m.copy()
                        m["t"] = pd.PeriodIndex(m["t"].astype(str).str.replace("M", "-", regex=False), freq="M")
                        return m.set_index("t").apply(pd.to_numeric, errors="coerce")
                except Exception:
                    pass
        except Exception:
            pass
    raise RuntimeError("Pink Sheet utilgjengelig")


# =========================================================== 1. aldersvekting

def pit_detrend(y, H=None, minn=60):
    """Punkt-i-tid detrending. H = halveringstid i aar for vekten i regresjonen.
    H=None er dagens modell: alle observasjoner teller likt."""
    v = np.asarray(y, float); n = len(v); out = np.full(n, np.nan)
    for i in range(minn - 1, n):
        t = np.arange(i + 1, dtype=float); yy = v[:i + 1]
        w = np.ones(i + 1) if H is None else 0.5 ** ((i - t) / (12.0 * H))
        Sw = w.sum(); Swt = (w * t).sum(); Swy = (w * yy).sum()
        Swtt = (w * t * t).sum(); Swty = (w * t * yy).sum()
        den = Sw * Swtt - Swt * Swt
        if den <= 0: continue
        b = (Sw * Swty - Swt * Swy) / den; a = (Swy - b * Swt) / Sw
        r = yy - (a + b * t)
        out[i] = (1 - (r <= r[i]).sum() / (i + 1)) * 100
    return out


VARIANTER = [("likevekt", None), ("HL 30 aar", 30), ("HL 20 aar", 20),
             ("HL 15 aar", 15), ("HL 10 aar", 10), ("HL 5 aar", 5)]

print("0. Henter deflator og priser")
cpi = csv_series(MIRROR + "cpi-us/main/data/cpiai.csv")
print(f"   CPI til {cpi.index[-1]}")

SER = {}
for sid, sti, mnd in [("brent", "oil-prices/main/data/brent-daily.csv", False),
                      ("wti", "oil-prices/main/data/wti-daily.csv", False),
                      ("henryhub", "natural-gas/main/data/daily.csv", False),
                      ("gold", "gold-prices/main/data/monthly.csv", True)]:
    try:
        SER[sid] = csv_series(MIRROR + sti, monthly=mnd)
    except Exception as e:
        print(f"   speil {sid} feilet: {str(e)[:50]}")

PINK = [("kobber","Copper"),("nikkel","Nickel"),("aluminium","Aluminum"),("sink","Zinc"),
        ("bly","Lead"),("tinn","Tin"),("jernmalm","Iron ore"),("kull","Coal, Australian"),
        ("ttf","Natural gas, Europe"),("urea","Urea"),("kalium","Potassium chloride"),
        ("fiskemel","Fish meal"),("kakao","Cocoa"),("kaffe_arabica","Coffee, Arabica"),
        ("kaffe_robusta","Coffee, Robusta"),("palmeolje","Palm oil"),
        ("gummi_rss3","Rubber, RSS3"),("gummi_tsr20","Rubber, TSR20"),
        ("kokosolje","Coconut oil"),("te","Tea, avg 3 auctions")]
try:
    ps = pink_sheet()
    norm = lambda x: re.sub(r"[^a-z0-9]", "", str(x).lower())
    kol = {norm(c): c for c in ps.columns}
    for sid, nokkel in PINK:
        eksakt = [v for k, v in kol.items() if k == norm(nokkel)]
        delvis = [v for k, v in kol.items() if norm(nokkel) in k]
        treff = eksakt or delvis
        if treff:
            SER[sid] = ps[treff[0]].dropna()
    print(f"   Pink Sheet: {len([s for s,_ in PINK if s in SER])} av {len(PINK)} funnet")
except Exception as e:
    print(f"   Pink Sheet feilet: {str(e)[:60]}")

REAL = {}
for sid, s in SER.items():
    s = s.dropna().sort_index()
    r = (s * (cpi.dropna().iloc[-1] / cpi.reindex(s.index).ffill())).dropna()
    if len(r) >= 120:
        REAL[sid] = r
print(f"   {len(REAL)} segmenter med minst 10 aars historikk\n")

print("=" * 78)
print("0b. ER DET EN MARKEDSPRIS? ANDEL MAANEDER UTEN ENDRING")
print("=" * 78)
print("    En forhandlet kontraktspris eller en forsvart kurs staar stille mellom")
print("    revisjonene. Ligger en slik periode i fordelingen, opptar den de")
print("    billigste persentilene permanent. Det var feilen i gull: 206 av 206")
print("    flaggmaaneder laa foer 1971, og bunnen i 1999 leste A=53.")
print("    Maalt paa NOMINELL pris: en fast kurs beveger seg i realserien fordi")
print("    deflatoren beveger seg, saa realserien underoppdager problemet.")
print("    Over ca. 40 % i et tiaar betyr at perioden boer vurderes avkortet.")
print()
print(f"    {'segment':16s} " + "".join(f"{str(t)[2:]+'-tallet':>11}" for t in range(1960, 2030, 10)))
for sid in sorted(REAL):
    r = SER[sid].dropna().sort_index(); rad = []   # nominell, ikke real
    for t in range(1960, 2030, 10):
        w = r.loc[str(t):str(t+9)]
        if len(w) < 24: rad.append(f"{'':>11}"); continue
        d = w.diff().abs().dropna()
        pst = 100 * (d < 1e-9).mean()
        rad.append(f"{pst:>9.0f} %" + ("!" if pst >= 40 else " "))
    print(f"    {sid:16s} " + "".join(rad))
print()

print("=" * 78)
print("1. ALDERSVEKTING I DETRENDINGEN")
print("=" * 78)
print("\n1a. Hvor mye veier hvert tiaar allerede i dagens likevektede regresjon")
n = max(len(v) for v in REAL.values()); t = np.arange(n); d = np.abs(t - t.mean())
w = d / d.sum()
print("    (innflytelsen paa stigningstallet er proporsjonal med avstanden fra midten,")
print("     saa endepunktene dominerer allerede. Midten teller nesten ingenting.)")
lengste = max(REAL, key=lambda k: len(REAL[k]))
aar0 = REAL[lengste].index[0].year
for y in range(aar0 - aar0 % 10, 2030, 10):
    a = max(0, (y - aar0) * 12); b = min((y + 10 - aar0) * 12, n)
    if a < b: print(f"      {y}-{min(y+9, 2026)}   {100*w[a:b].sum():5.1f} % av vekten")

AD = {}
print(f"\n1b. Dagens Ad mot vektede varianter, per segment")
print(f"    {'segment':16s} {'n':>5} {'fra':>8}  " + "".join(f"{v:>11s}" for v, _ in VARIANTER))
for sid in sorted(REAL, key=lambda k: -len(REAL[k])):
    y = np.log(REAL[sid].values); rad = []
    for vn, H in VARIANTER:
        AD[(sid, vn)] = pit_detrend(y, H); rad.append(AD[(sid, vn)][-1])
    print(f"    {sid:16s} {len(y):>5} {str(REAL[sid].index[0]):>8}  " +
          "".join(f"{x:>11.1f}" for x in rad))

def fram(s, k):
    y = np.log(s.values); f = np.full(len(y), np.nan)
    if len(y) > k: f[:-k] = (np.exp(y[k:] - y[:-k]) - 1) * 100
    return f

print("\n1c. Betinget realavkastning. Terskelen er satt per variant slik at alle")
print("    flagger like ofte (topp 20 % av egne verdier). Uten det maaler man")
print("    bare at faerre flagg gir hoyere snitt.")
for K in (12, 24, 36):
    print(f"\n    {K} maaneder fram")
    print(f"    {'variant':12s} {'terskel':>8} {'n':>6} {'snitt':>9} {'median':>9} {'traff>0':>9} {'5% verst':>9}")
    for vn, H in VARIANTER:
        alle = np.concatenate([AD[(s, vn)][~np.isnan(AD[(s, vn)])] for s in REAL])
        t80 = np.percentile(alle, 80); r = []
        for s in REAL:
            a = AD[(s, vn)]; f = fram(REAL[s], K)
            m = (a >= t80) & ~np.isnan(a) & ~np.isnan(f); r += list(f[m])
        r = np.array(r)
        print(f"    {vn:12s} {t80:8.1f} {len(r):>6} {r.mean():8.1f}% {np.median(r):8.1f}% "
              f"{100*(r>0).mean():8.0f}% {np.percentile(r,5):8.1f}%")
    ub = np.concatenate([fram(s, K)[~np.isnan(fram(s, K))] for s in REAL.values()])
    print(f"    {'ubetinget':12s} {'':>8} {len(ub):>6} {ub.mean():8.1f}% {np.median(ub):8.1f}% "
          f"{100*(ub>0).mean():8.0f}% {np.percentile(ub,5):8.1f}%")

print("\n1d. Hvor mye flytter vektingen Ad i dag, per segment")
print(f"    {'segment':16s} {'likevekt':>10} {'HL 15':>10} {'diff':>8}")
flytt = []
for sid in sorted(REAL):
    a, b = AD[(sid, "likevekt")][-1], AD[(sid, "HL 15 aar")][-1]
    flytt.append(abs(a - b))
    print(f"    {sid:16s} {a:10.1f} {b:10.1f} {b-a:+8.1f}")
print(f"    median absolutt endring: {np.median(flytt):.1f} poeng")


# ============================================================ 2 og 3. BDI-sonde

print("\n" + "=" * 78)
print("2. BDI OG BALTIC PER SEGMENT: HVA SVARER")
print("=" * 78)

def sonde(navn, fn):
    try:
        r = fn()
        print(f"   OK    {navn}: {r}")
        return r
    except Exception as e:
        print(f"   feil  {navn}: {type(e).__name__} {str(e)[:70]}")
        return None

def f_stooq(sym):
    def g():
        t = get(f"https://stooq.com/q/d/l/?s={sym}&i=d").text
        if not t.startswith("Date"): return f"svarte, men ikke CSV: {t[:60]!r}"
        d = pd.read_csv(io.StringIO(t))
        return f"{len(d)} rader, {d.iloc[0,0]} til {d.iloc[-1,0]}"
    return g

def f_yahoo(sym):
    def g():
        j = get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}"
                f"?range=max&interval=1mo").json()["chart"]["result"][0]
        ts = j["timestamp"]
        return (f"{len(ts)} mnd, {pd.to_datetime(ts[0],unit='s').date()} til "
                f"{pd.to_datetime(ts[-1],unit='s').date()}")
    return g

def f_te(sti):
    def g():
        h = get(f"https://tradingeconomics.com/commodity/{sti}").text
        par = re.findall(r'\[\s*(?:new Date\()?["\']?\d{4}[-/]\d{2}[-/]\d{2}', h)
        tall = re.findall(r'"(?:value|close|y)"\s*:\s*-?[\d.]+', h)
        return (f"{len(h):,} tegn, {len(par)} datopunkter, {len(tall)} verditagger "
                f"{'SERIE FINNES' if len(par) > 50 else 'ingen serie i siden'}")
    return g

def f_investing():
    def g():
        h = get("https://www.investing.com/indices/baltic-dry-historical-data").text
        pid = re.findall(r'(?:pairId|pair_id)["\':\s]+(\d{3,8})', h)
        return f"{len(h):,} tegn, pairId-kandidater {sorted(set(pid))[:5]}"
    return g

def f_macromicro(nr):
    def g():
        r = get(f"https://en.macromicro.me/charts/data/{nr}",
                headers={**UA, "Referer": f"https://en.macromicro.me/series/{nr}/x",
                         "X-Requested-With": "XMLHttpRequest"})
        return f"{len(r.content):,} b, starter {r.text[:70]!r}"
    return g

print("\n2a. Headline BDI, hullet 2013-2026")
print(f"   OK    innebygd historikk: {len(BDI_MND)} maaneder, "
      f"{min(BDI_MND)} til {max(BDI_MND)} (lastet ned og verifisert paa forhaand)")
for s in ["^bdi", "bdi", "^badi"]:
    sonde(f"stooq {s}", f_stooq(s))
for s in ["^BDIY", "BDRY", "BDI"]:
    sonde(f"yahoo {s}", f_yahoo(s))
sonde("tradingeconomics /commodity/baltic", f_te("baltic"))
sonde("investing.com BADI", f_investing())
sonde("macromicro serie 760", f_macromicro(760))

print("\n2b. Baltic per skipssegment")
for navn, sym in [("Capesize BCI", "^bci"), ("Panamax BPI", "^bpi"),
                  ("Supramax BSI", "^bsi"), ("Handysize BHSI", "^bhsi")]:
    sonde(f"stooq {navn}", f_stooq(sym))
for navn, sti in [("Capesize", "baltic-capesize"), ("Panamax", "baltic-panamax"),
                  ("Supramax", "baltic-supramax"), ("Handysize", "baltic-handysize"),
                  ("Dirty tanker BDTI", "baltic-dirty-tanker"),
                  ("Clean tanker BCTI", "baltic-clean-tanker")]:
    sonde(f"tradingeconomics {navn}", f_te(sti))

print("\n2c. Staar BDI i Fearnleys-rapportene vi allerede henter")
print("    (fyller i saa fall 2019-2026 fra en kilde som er bevist)")
try:
    import pdfplumber
except ImportError:
    import subprocess, sys
    subprocess.run([sys.executable, "-m", "pip", "-q", "install", "pdfplumber"], check=False)
    import pdfplumber

try:
    med = []
    for side in (1, 2):
        j = get("https://www.hellenicshippingnews.com/wp-json/wp/v2/media",
                params={"search": "Fearnleys", "per_page": 100, "page": side,
                        "_fields": "date,source_url"}, timeout=40).json()
        med += [m for m in j if str(m.get("source_url", "")).lower().endswith(".pdf")]
    med.sort(key=lambda m: m["date"], reverse=True)
    print(f"    {len(med)} PDF-er funnet, sjekker de 6 nyeste")
    MONSTER = re.compile(r"\b(BDI|BCI|BPI|BSI|BHSI|BDTI|BCTI|Baltic[^\n]{0,30}Index)\b", re.I)
    for m in med[:6]:
        try:
            raw = get(m["source_url"], timeout=60).content
            with pdfplumber.open(io.BytesIO(raw)) as pdf:
                tx = "\n".join((s.extract_text() or "") for s in pdf.pages)
            traff = []
            for lin in tx.splitlines():
                if MONSTER.search(lin):
                    traff.append(lin.strip()[:100])
            print(f"      {m['date'][:10]}  {len(traff)} treff" +
                  ("" if traff else "   (ingen Baltic-indeks i rapporten)"))
            for lin in traff[:6]:
                print(f"         {lin}")
        except Exception as e:
            print(f"      {m['date'][:10]}  FEIL {type(e).__name__} {str(e)[:50]}")
except Exception as e:
    print(f"    mediesok feilet: {type(e).__name__} {str(e)[:60]}")


# ================================================= 4. bank det vi allerede har

print("\n" + "=" * 78)
print("3. BANKER DET SOM ER SIKKERT")
print("=" * 78)

def push(path, text):
    api = f"https://api.github.com/repos/{REPO}/contents/{path}"
    h = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}
    sha = None
    try:
        g = requests.get(api, headers=h, params={"ref": BRANCH}, timeout=30)
        if g.status_code == 200: sha = g.json().get("sha")
    except Exception: pass
    body = {"message": f"oppdatert {path}", "branch": BRANCH,
            "content": base64.b64encode(text.encode()).decode()}
    if sha: body["sha"] = sha
    requests.put(api, headers=h, json=body, timeout=60).raise_for_status()

ut = {}
try:
    s_bdi = pd.Series({pd.Period(k, "M"): float(v) for k, v in BDI_MND.items()}).sort_index()
    r = (s_bdi * (cpi.dropna().iloc[-1] / cpi.reindex(s_bdi.index).ffill())).dropna()
    ut["bdi_hist"] = {"id": "bdi_hist", "name": "Baltic Dry Index (historisk)",
        "group": "Shipping", "unit": "indeks", "status": "historikk",
        "hist_start": str(r.index[0]), "siste_obs": str(r.index[-1]),
        "note": ("Torrlastrater 1985-2013, maanedssnitt av daglige noteringer. "
                 "Serien stopper i juni 2013. Uten overlapp kan den ikke skjotes mot "
                 "Fearnleys 2019-2026, saa den gir ingen A i dag. Den bankes som "
                 "fordelingsgrunnlag for den dagen hullet 2013-2019 er fylt."),
        "kilde": "GitHub ajoposor/Baltic-Dry-Index, maanedsaggregert",
        "aar": [str(p) for p in r.index],
        "nom": [round(float(x), 1) for x in s_bdi[r.index]],
        "real": [round(float(x), 1) for x in r]}
    print(f"   bdi_hist: {len(r)} maaneder, {r.index[0]} til {r.index[-1]}, "
          f"realt snitt {r.mean():,.0f}, realt siste {r.iloc[-1]:,.0f}")
    lav = r.nsmallest(3); hoy = r.nlargest(3)
    print(f"      lavest realt: " + ", ".join(f"{p} {v:,.0f}" for p, v in lav.items()))
    print(f"      hoyest realt: " + ", ".join(f"{p} {v:,.0f}" for p, v in hoy.items()))
except Exception as e:
    print(f"   BDI-historikk feilet: {type(e).__name__} {str(e)[:60]}")

try:
    o = pd.read_csv("https://raw.githubusercontent.com/owid/energy-data/master/owid-energy-data.csv",
                    low_memory=False)
    w = o[o.country == "World"].set_index("year")
    def vekst(s, k):
        y = np.log(s.iloc[-k:].values)
        return None if len(y) < k else round(float(100*(np.exp(np.polyfit(np.arange(len(y)), y, 1)[0])-1)), 2)
    baerere = {}
    for kol, (navn, segs) in {"oil_consumption": ("Olje", ["brent", "wti"]),
                              "gas_consumption": ("Gass", ["henryhub", "ttf"]),
                              "coal_consumption": ("Kull", ["kull"]),
                              "nuclear_consumption": ("Kjernekraft", ["uran"])}.items():
        s = w[kol].dropna()
        baerere[navn] = {"baerer": navn, "segmenter": segs, "enhet": "TWh primaerenergi, verden",
            "aar": [int(a) for a in s.index], "verdi": [round(float(x), 1) for x in s.values],
            "siste_aar": int(s.index[-1]), "siste": round(float(s.iloc[-1]), 1),
            "vekst10": vekst(s, 10), "vekst20": vekst(s, 20), "vekst30": vekst(s, 30),
            "topp_aar": int(s.idxmax()),
            "under_topp_pst": round(float(100*(s.iloc[-1]/s.max()-1)), 1),
            "kilde": "Our World in Data, Energy dataset",
            "kilde_url": "https://github.com/owid/energy-data"}
    ut["etterspørsel"] = {"oppdatert": str(pd.Timestamp.utcnow())[:10], "baerere": baerere,
        "merknad": ("Verdensforbruk er lik verdensproduksjon per definisjon, saa dette er "
                    "IKKE etterspørsel minus tilbud. Det er etterspørselstrenden alene. "
                    "Tilbudsbenet maales med B, altsaa capex mot avskrivninger. "
                    "Femaarsvinduet er utelatt fordi 2020 gjor det til en maaling av "
                    "gjeninnhentingen og ikke av trenden.")}
    print(f"\n   etterspørsel: {len(baerere)} baerere, siste aar {baerere['Olje']['siste_aar']}")
    for n, v in baerere.items():
        print(f"      {n:13s} 10aar {v['vekst10']:+6.2f} %   30aar {v['vekst30']:+6.2f} %   "
              f"topp {v['topp_aar']}, naa {v['under_topp_pst']:+.1f} % mot topp")
except Exception as e:
    print(f"   OWID feilet: {type(e).__name__} {str(e)[:60]}")

if GITHUB_TOKEN and ut:
    for navn, obj in ut.items():
        try:
            push(f"{navn}.json", json.dumps(obj, ensure_ascii=False))
            print(f"   publisert {navn}.json")
        except Exception as e:
            print(f"   publisering av {navn} feilet: {type(e).__name__} {str(e)[:50]}")
elif not GITHUB_TOKEN:
    print("   GITHUB_TOKEN mangler, ingenting publisert")

print("\n" + "=" * 78)
print("Send hele utskriften tilbake. 1c avgjor vektingen, 2 avgjor BDI.")
