# ---------------------------------------------------------------------------
# sonde_kjor_oljeservice: grunnlag for et oljeservicesegment bygget som
# shippingsegmentene
#
# Frodes bestilling 29.09.2026. Et shippingsegment har en prisserie
# (annenhaandsverdi), en rate som indikator (BDI, timecharter), D paa
# papirene og C som port. Denne sonden bygger ingenting. Den sjekker hva et
# oljeservicesegment kan bygges av, og viser beskrivende tall. Ingen regel
# testes, og ingenting her skal leses som bevis: siden fondene fikk kurser er
# det bare to til tre bunner (2008/09, 2015/16, 2020).
#
#   1  PRISSERIE OG INDIKATOR (FRED, gratis, maanedlig)
#        PCU213111213111  produsentpris, boring av olje- og gassbroenner (1985)
#        PCU213112213112  produsentpris, stoettetjenester for olje og gass (1985)
#        IPN213111N       industriproduksjon, boring (aktivitet, 1972)
#      Baker Hughes rig count proeves ogsaa (svarte ikke fra Claude Codes miljoe).
#      Prisseriene deflateres med bordets egen KPI, og A og detrendet A regnes
#      med terskel_motor som for raavarene. Innslag i bunnsone listes ved siden
#      av Brent og WTI for aa se etterslepet.
#   2  PAPIRER: fond og aksjer paa Yahoo. Historikk, valuta, stoerste fall, og
#      hull i kursserien som tyder paa konkurs og ny notering.
#   3  C: for papirer hos SEC, antall aar med driftskontantstroem og verste aar.
#   4  BESKRIVENDE: avkastning mot SPY 3, 6, 12 og 24 mnd etter tre slags
#      hendelser, alle definert her foer kjoering:
#        a  innslag i bunnsone for Brent (bordets eget flagg)
#        b  innslag i bunnsone for produsentprisen for boring
#        c  aktivitetsbunn: foerste maaned der 3-maanedersendringen i
#           industriproduksjon for boring er positiv, etter at
#           12-maanedersendringen har vaert under -30 % en gang de siste seks
#           maanedene. Tolv maaneders pause mellom innslag.
#      Inngang ved slutten av hendelsesmaaneden.
# ---------------------------------------------------------------------------

import io, re, time, warnings
import numpy as np
import pandas as pd
import requests
import terskel_motor as M

warnings.filterwarnings("ignore")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
SEC_UA = {"User-Agent": "Syklusbordet frode@h-k.no"}
NAA = pd.Period(pd.Timestamp.utcnow().strftime("%Y-%m"), "M")
PAUSE = M.PAUSE
H = (3, 6, 12, 24)

PAPIRER = {
    # fond
    "OIH": "VanEck Oil Services ETF", "XES": "SPDR S&P Oil & Gas Equipment & Services",
    "IEZ": "iShares U.S. Oil Equipment & Services",
    # store, lange serier
    "SLB": "SLB", "HAL": "Halliburton", "BKR": "Baker Hughes", "NOV": "NOV", "TS": "Tenaris",
    "FTI": "TechnipFMC", "WFRD": "Weatherford", "OII": "Oceaneering", "HP": "Helmerich & Payne",
    "PTEN": "Patterson-UTI", "NBR": "Nabors", "TDW": "Tidewater",
    # offshore rigg
    "RIG": "Transocean", "VAL": "Valaris", "NE": "Noble", "SDRL": "Seadrill", "BORR": "Borr Drilling",
    # Oslo
    "SUBC.OL": "Subsea 7", "AKSO.OL": "Aker Solutions", "TGS.OL": "TGS", "DOFG.OL": "DOF",
    "ODL.OL": "Odfjell Drilling",
}


def get(url, headers=UA, timeout=60, **kw):
    for i in range(3):
        try:
            r = requests.get(url, headers=headers, timeout=timeout, **kw)
            if r.status_code in (429, 502, 503):
                time.sleep(3 * (i + 1)); continue
            return r
        except requests.RequestException:
            time.sleep(2 * (i + 1))
    return None


def fred(sid):
    # FRED henger paa nettleser-agent, svarer paa en vanlig
    r = get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}", headers=SEC_UA)
    d = pd.read_csv(io.StringIO(r.text))
    d.columns = ["t", "v"]
    d["v"] = pd.to_numeric(d["v"], errors="coerce")
    d = d.dropna()
    return pd.Series(d["v"].values, index=pd.PeriodIndex(d["t"].astype(str).str[:7], freq="M"))


_fx = {}
def yahoo(sym, valutakurs=False):
    """Maanedskurs i dollar, justert for utbytte. Returnerer (serie, valuta,
    dagserie uten justering for hullsjekk)."""
    r = get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?period1=0&period2={int(time.time())}"
            "&interval=1mo&events=div%7Csplit&includeAdjustedClose=true")
    res = r.json()["chart"]["result"][0]
    meta = res.get("meta") or {}
    idx = pd.to_datetime(res["timestamp"], unit="s").to_period("M")
    try:
        v = res["indicators"]["adjclose"][0]["adjclose"]
    except Exception:
        v = res["indicators"]["quote"][0]["close"]
    s = pd.Series(v, index=idx).dropna()
    s = s[(s > 0) & ~s.index.duplicated(keep="last")]
    if valutakurs:
        return s
    val = meta.get("currency") or "USD"
    if val != "USD":
        fs, inv = {"NOK": ("NOK=X", True), "EUR": ("EURUSD=X", False), "GBP": ("GBPUSD=X", False)}[val]
        if fs not in _fx:
            f = yahoo(fs, valutakurs=True)
            _fx[fs] = (1.0 / f) if inv else f
        s = (s * _fx[fs].reindex(s.index).ffill()).dropna()
    return s[s.index < NAA], val


def innslag(fl):
    ut, siste = [], None
    for t in fl.index[fl.values]:
        if siste is None or t.ordinal - siste.ordinal > PAUSE:
            ut.append(t)
        siste = t
    return ut


# ============================================================ 1 kilder
print("1. PRISSERIE OG INDIKATOR\n")
from raavare_hist import hent
REAL, _NOM, cpi = hent()
cpi_m = cpi.dropna()
KILDE = {}
for sid, navn in (("PCU213111213111", "PPI boring"), ("PCU213112213112", "PPI stoettetjenester"),
                  ("IPN213111N", "IP boring (aktivitet)")):
    try:
        s = fred(sid)
        KILDE[sid] = s
        print(f"   {navn:24s} {sid:17s} {s.index[0]} til {s.index[-1]}, siste {s.iloc[-1]:.1f}, "
              f"hoeyeste {s.max():.1f} ({s.idxmax()}), laveste etter 2000 {s.loc['2000':].min():.1f} "
              f"({s.loc['2000':].idxmin()})")
    except Exception as e:
        print(f"   {navn:24s} {sid}: {type(e).__name__} {str(e)[:60]}")

for u in ("https://rigcount.bakerhughes.com/intl-rig-count", "https://rigcount.bakerhughes.com/na-rig-count"):
    r = get(u, timeout=40)
    if r is None:
        print(f"   Baker Hughes {u.split('/')[-1]}: ingen svar")
        continue
    lenker = sorted(set(re.findall(r'href="([^"]+\.(?:xlsx|xlsb|xls)[^"]*)"', r.text)))
    print(f"   Baker Hughes {u.split('/')[-1]}: {r.status_code}, {len(lenker)} regnearklenker: {lenker[:4]}")

print("\n   A og detrendet A (bunnsone = begge >= 80), realpris deflatert med bordets KPI:")
FLAGG = {}
for sid in ("PCU213111213111", "PCU213112213112"):
    if sid not in KILDE:
        continue
    nom = KILDE[sid]
    real = (nom * (cpi_m.iloc[-1] / cpi_m.reindex(nom.index).ffill())).dropna()
    lr = np.log(real)
    seg = M.Segment(sid, lr.values, np.array([p.ordinal for p in lr.index]))
    ok = np.isfinite(seg.A) & np.isfinite(seg.Ad)
    b = pd.Series(ok & (seg.A >= 80) & (seg.Ad >= 80), index=lr.index)
    FLAGG[sid] = innslag(b)
    sone = int(b[::-1].cumprod().sum())
    print(f"      {sid}: A naa {seg.A[-1]:.1f}, detrendet {seg.Ad[-1]:.1f}, "
          f"{'i bunnsone naa, ' + str(sone) + ' mnd paa rad' if sone else 'ikke i bunnsone naa'}. "
          f"Realpris naa mot 1985: {100 * (real.iloc[-1] / real.iloc[0] - 1):+.0f} %. Innslag: "
          + " ".join(str(t) for t in FLAGG[sid]))
for sid in ("brent", "wti"):
    lr = REAL[sid].dropna()
    full = pd.period_range(lr.index[0], lr.index[-1], freq="M")
    lr = lr.reindex(full).interpolate()
    seg = M.Segment(sid, lr.values, np.array([p.ordinal for p in lr.index]))
    ok = np.isfinite(seg.A) & np.isfinite(seg.Ad)
    FLAGG[sid] = innslag(pd.Series(ok & (seg.A >= 80) & (seg.Ad >= 80), index=lr.index))
    print(f"      {sid}: innslag " + " ".join(str(t) for t in FLAGG[sid] if t.year >= 1985))

if "IPN213111N" in KILDE:
    ip = KILDE["IPN213111N"]
    e12, e3 = ip / ip.shift(12) - 1, ip / ip.shift(3) - 1
    krasj = (e12 < -0.30).rolling(6, min_periods=1).max().astype(bool)
    kand = (e3 > 0) & krasj
    FLAGG["aktivitet"] = innslag(kand.fillna(False))
    print(f"      aktivitetsbunn (IP boring): " + " ".join(str(t) for t in FLAGG["aktivitet"]))

# ============================================================ 2 papirer
print("\n\n2. PAPIRER (Yahoo, maanedlig, utbyttejustert, i dollar)\n")
KURS = {}
print(f"   {'papir':9s} {'navn':36s} {'val':4s} {'fra':8s} {'stoerste fall':>13s}  merknad")
for tk, navn in PAPIRER.items():
    try:
        s, val = yahoo(tk)
    except Exception as e:
        print(f"   {tk:9s} {navn:36s} ingen data ({type(e).__name__})"); continue
    KURS[tk] = s
    fall = float((s / s.cummax() - 1).min())
    hull = [f"{a}-{b}" for a, b in zip(s.index[:-1], s.index[1:]) if b.ordinal - a.ordinal > 2]
    merk = []
    if hull:
        merk.append("hull i serien " + ", ".join(hull[:3]))
    if s.index[0].year >= 2018:
        merk.append("kort historikk (ny notering?)")
    if fall < -0.95:
        merk.append("fall over 95 %")
    print(f"   {tk:9s} {navn:36s} {val:4s} {str(s.index[0]):8s} {100 * fall:12.0f} %  {'; '.join(merk)}")
    time.sleep(0.3)
try:
    SPY, _ = yahoo("SPY")
except Exception:
    SPY = None

# ============================================================ 3 C
print("\n\n3. C: DRIFTSKONTANTSTROEM HOS SEC\n")
tick = get("https://www.sec.gov/files/company_tickers.json", headers=SEC_UA).json()
KART = {v["ticker"].upper(): str(v["cik_str"]).zfill(10) for v in tick.values()}
for tk in PAPIRER:
    if tk not in KART:
        continue
    try:
        f = get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{KART[tk]}.json", headers=SEC_UA, timeout=120).json()["facts"]
    except Exception as e:
        print(f"   {tk:6s} {type(e).__name__}"); continue
    aar = {}
    for tak, b in (("us-gaap", "NetCashProvidedByUsedInOperatingActivities"),
                   ("us-gaap", "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"),
                   ("ifrs-full", "CashFlowsFromUsedInOperatingActivities")):
        for enh, pkt in (f.get(tak, {}).get(b, {}).get("units") or {}).items():
            for p in pkt:
                if p.get("form") in ("10-K", "20-F", "40-F") and p.get("fp") == "FY" and p.get("start"):
                    dager = (pd.Timestamp(p["end"]) - pd.Timestamp(p["start"])).days
                    if 330 <= dager <= 400:
                        aar.setdefault(int(p["end"][:4]), p["val"] / 1e6)
    if not aar:
        print(f"   {tk:6s} ingen driftskontantstroem"); continue
    s = pd.Series(aar).sort_index()
    print(f"   {tk:6s} {len(s):2d} aar {s.index[0]} til {s.index[-1]}, verste {s.idxmin()} ({s.min():,.0f} mill.), "
          f"negative aar: {[int(a) for a in s.index[s < 0]]}")
    time.sleep(0.3)

# ============================================================ 4 beskrivende
print("\n\n4. BESKRIVENDE: AVKASTNING MOT SPY ETTER HENDELSER (ikke en test)\n")


def mot_spy(s, t, h):
    if SPY is None or t not in s.index or t + h not in s.index or t not in SPY.index or t + h not in SPY.index:
        return np.nan
    return (s[t + h] / s[t]) - (SPY[t + h] / SPY[t])


VIS = [tk for tk in ("OIH", "XES", "IEZ", "SLB", "HAL", "BKR", "NOV", "RIG", "SUBC.OL") if tk in KURS]
for navn, nokkel in (("a  Brent bunnsone", "brent"), ("b  PPI boring bunnsone", "PCU213111213111"),
                     ("c  aktivitetsbunn", "aktivitet")):
    print(f"   {navn}")
    for t in [t for t in FLAGG.get(nokkel, []) if t.year >= 1995]:
        rad = []
        for tk in VIS:
            v = [mot_spy(KURS[tk], t, h) for h in H]
            if all(np.isnan(x) for x in v):
                continue
            rad.append(f"{tk} " + "/".join("  - " if np.isnan(x) else f"{100 * x:+.0f}" for x in v))
        print(f"      {t}: " + ("  |  ".join(rad) if rad else "ingen papirer med kurs"))
    print()
print("   Tall per papir: avkastning minus SPY i prosentpoeng etter " + "/".join(f"{h}" for h in H) + " mnd.")
print("   Konkurser: Yahoo viser bare dagens notering. Papirer som gikk konkurs (Seadrill,")
print("   Valaris, Noble, Pacific Drilling, Diamond) mangler eller starter paa nytt, saa")
print("   tallene over er skjevt oppover for riggselskapene.")
