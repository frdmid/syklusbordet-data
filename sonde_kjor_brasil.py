# ---------------------------------------------------------------------------
# sonde_kjor_brasil: hvilke raavarer folger et rent Brasil-fond best?
#
# Frodes spoersmaal 26.09.2026. Ingen Brasil-fond er maalt foer: IKZ-sonden
# maalte papirer mot bordets raavarer, ikke motsatt. Her snus det: tre
# Brasil-fond maales mot ALLE maanedsseriene i Verdensbankens Pink Sheet
# (energi, metaller, landbruk, gjoedsel), pluss dollar mot real.
#
# Fondene:
#   IBZL.L   iShares MSCI Brazil UCITS (London). Kjoepbar paa IKZ.
#   XMBR.DE  Xtrackers MSCI Brazil UCITS (Xetra). Kjoepbar paa IKZ.
#   EWZ      iShares MSCI Brazil (USA, fra 2000). IKKE kjoepbar paa IKZ
#            (amerikansk domisil), men lengst historikk. Brukes som kontroll.
#
# Maalingen er den samme som i sonde_ikz.py:
#   rf1  korrelasjon i maanedlige realendringer i fast vindu fra 2016-01
#   r1   det samme over hele felles historikk
#   rp   partiell korrelasjon i r1 etter at verdensindeksen (IWDA.L) er tatt
#        ut: hva raavaren forklarer utover at aksjer generelt steg
#   r12  overlappende tolvmaanedersendringer (bare beskrivende, se README i
#        sonde_ikz.py om hvorfor den ikke brukes til utvalg)
# Alt i dollar og deflatert med samme KPI. Serier som staar stille i over
# 40 % av maanedene fra 2000 er forhandlede priser og tas ikke med.
#
# Mange raavarer testes mot samme fond, saa noe vil se sterkt ut ved flaks.
# Rangeringen er beskrivende. Et funn under 0,30 i rp leses som svakt.
# ---------------------------------------------------------------------------

import io, json, os, re, time, warnings
import numpy as np
import pandas as pd
import requests

warnings.filterwarnings("ignore")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
MIRROR = "https://raw.githubusercontent.com/datasets/"
FIKS, FRA, MIN_N = "2016-01", "2000-01", 60
FOND = [("IBZL.L", "iShares MSCI Brazil UCITS", "IE00B0M63516"),
        ("XMBR.DE", "Xtrackers MSCI Brazil UCITS", "LU0292109344"),
        ("EWZ", "iShares MSCI Brazil (USA, kontroll)", None)]
KONTROLL = "IWDA.L"
FX = {"USD": None, "EUR": ("EURUSD=X", False), "GBP": ("GBPUSD=X", False),
      "GBp": ("GBPUSD=X", False)}


def get(url, timeout=60):
    for i in range(3):
        try:
            r = requests.get(url, headers=UA, timeout=timeout)
            if r.status_code in (429, 502, 503):
                time.sleep(3 * (i + 1)); continue
            r.raise_for_status()
            return r
        except requests.RequestException:
            if i == 2:
                raise
            time.sleep(2 * (i + 1))


def yahoo(sym, justert=True):
    j = "&events=div%7Csplit&includeAdjustedClose=true" if justert else ""
    res = get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}"
              f"?period1=0&period2={int(time.time())}&interval=1mo{j}").json()["chart"]["result"][0]
    meta = res.get("meta") or {}
    idx = pd.to_datetime(res["timestamp"], unit="s", utc=True).tz_convert(meta.get("exchangeTimezoneName") or "UTC")
    v = None
    if justert:
        try:
            v = res["indicators"]["adjclose"][0]["adjclose"]
        except Exception:
            v = None
    if v is None:
        v = res["indicators"]["quote"][0]["close"]
    s = pd.Series(v, index=idx).dropna()
    s = s[s > 0]
    s.index = s.index.to_period("M")
    s = s[~s.index.duplicated(keep="last")]
    s.attrs["valuta"] = meta.get("currency") or "USD"
    return s


def via_isin(isin):
    r = get(f"https://query2.finance.yahoo.com/v1/finance/search?q={isin}&quotesCount=25&newsCount=0").json()
    return [q["symbol"] for q in r.get("quotes", []) if q.get("symbol", "").endswith((".L", ".DE", ".AS", ".SW", ".PA", ".MI"))]


def i_dollar(s):
    val = s.attrs.get("valuta", "USD")
    if val not in FX:
        raise ValueError(f"ukjent valuta {val}")
    if FX[val]:
        s = (s * yahoo(FX[val][0], justert=False).reindex(s.index).ffill()).dropna()
    if val == "GBp":
        s = s / 100.0
    return s


def pink_sheet():
    kand = []
    try:
        html = get("https://www.worldbank.org/en/research/commodity-markets", 40).text
        kand += [u if u.startswith("http") else "https://www.worldbank.org" + u
                 for u in re.findall(r'https?://[^"\']*?CMO[^"\']*?Monthly[^"\']*?\.xlsx', html)]
    except Exception:
        pass
    kand.append("https://thedocs.worldbank.org/en/doc/18675f1d1639c7a34d463f59263ba0a2-0050012025/"
                "related/CMO-Historical-Data-Monthly.xlsx")
    for u in dict.fromkeys(kand):
        try:
            raw = get(u, 120).content
            for skip in (4, 5, 6):
                try:
                    df = pd.read_excel(io.BytesIO(raw), sheet_name="Monthly Prices", skiprows=skip)
                    df = df.rename(columns={df.columns[0]: "t"})
                    m = df[df["t"].astype(str).str.match(r"^\d{4}M\d{1,2}$", na=False)].copy()
                    if len(m) > 100:
                        m["t"] = pd.PeriodIndex(m["t"].astype(str).str.replace("M", "-", regex=False), freq="M")
                        return m.set_index("t").apply(pd.to_numeric, errors="coerce")
                except Exception:
                    pass
        except Exception:
            pass
    raise RuntimeError("Pink Sheet utilgjengelig")


d = pd.read_csv(io.StringIO(get(MIRROR + "cpi-us/main/data/cpiai.csv").text)).iloc[:, :2]
d.columns = ["Date", "Value"]
d["Date"] = pd.to_datetime(d["Date"])
cpi = d.set_index("Date")["Value"].astype(float).resample("ME").last().dropna()
cpi.index = cpi.index.to_period("M")
defl = lambda s: (s * (cpi.iloc[-1] / cpi.reindex(s.index).ffill())).dropna()
dl = lambda s: np.log(s).diff().dropna()

print("1. Fond og kontroll\n")
KURS, BRUKT = {}, {}
for sym, navn, isin in FOND + [(KONTROLL, "iShares Core MSCI World", None)]:
    s, bestilt = None, sym
    try:
        s = yahoo(sym)
    except Exception as e:
        print(f"   {sym}: {type(e).__name__}, proever ISIN")
    if (s is None or len(s) < 24) and isin:
        for alt in via_isin(isin):
            try:
                s2 = yahoo(alt)
                if len(s2) >= 24 and (s is None or len(s2) > len(s)):
                    s, sym = s2, alt
            except Exception:
                pass
    if s is None or len(s) < 24:
        print(f"   {navn}: ingen serie")
        continue
    try:
        KURS[bestilt] = defl(i_dollar(s))
        BRUKT[bestilt] = sym
        print(f"   {sym:9} {navn:38} {KURS[bestilt].index[0]} til {KURS[bestilt].index[-1]} ({s.attrs.get('valuta')})")
    except Exception as e:
        print(f"   {sym}: {e}")
    time.sleep(0.3)

print("\n2. Raavarer fra Pink Sheet\n")
ps = pink_sheet()
RAA, utelatt = {}, []
for c in ps.columns:
    s = ps[c].dropna()
    s = s[(s > 0) & (s.index >= pd.Period(FRA, "M"))]
    if len(s) < 120:
        continue
    stille = float((s.diff() == 0).iloc[1:].mean())
    if stille > 0.40:
        utelatt.append(f"{c} ({100 * stille:.0f} % stille)")
        continue
    RAA[str(c).strip()] = defl(s)
try:
    brl = yahoo("BRL=X", justert=False)       # BRL=X er real per dollar, snudd til styrken i real
    RAA["Real mot dollar (dollar per real)"] = 1.0 / brl
except Exception as e:
    print(f"   BRL: {type(e).__name__}")
print(f"   {len(RAA)} serier med. Utelatt som forhandlet pris: {', '.join(utelatt) or 'ingen'}")

print("\n3. Maaling\n")
w = dl(KURS[KONTROLL]) if KONTROLL in KURS else None
RES = {"kjort": time.strftime("%Y-%m-%d %H:%M:%S"), "fond": {}}
for f, _, _ in FOND:
    if f not in KURS:
        continue
    y_all = dl(KURS[f])
    rad = []
    for navn, s in RAA.items():
        x_all = dl(s)
        i = x_all.index.intersection(y_all.index)
        if len(i) < MIN_N:
            continue
        x, y = x_all.reindex(i).values, y_all.reindex(i).values
        r1 = float(np.corrcoef(x, y)[0, 1])
        ifx = i[i >= pd.Period(FIKS, "M")]
        rf1 = float(np.corrcoef(x_all.reindex(ifx).values, y_all.reindex(ifx).values)[0, 1]) if len(ifx) >= 48 else None
        rp = None
        if w is not None:
            ww = w.reindex(i); ok = ww.notna().values
            if ok.sum() >= MIN_N:
                xw = np.corrcoef(x[ok], ww.values[ok])[0, 1]; yw = np.corrcoef(y[ok], ww.values[ok])[0, 1]
                rxy = np.corrcoef(x[ok], y[ok])[0, 1]
                dd = np.sqrt((1 - xw ** 2) * (1 - yw ** 2))
                rp = float((rxy - xw * yw) / dd) if dd > 1e-9 else None
        x12 = (np.log(s) - np.log(s).shift(12)).dropna(); y12 = (np.log(KURS[f]) - np.log(KURS[f]).shift(12)).dropna()
        i12 = x12.index.intersection(y12.index)
        r12 = float(np.corrcoef(x12.reindex(i12).values, y12.reindex(i12).values)[0, 1]) if len(i12) >= MIN_N else None
        rad.append({"raavare": navn, "n": len(i), "nf": len(ifx), "rf1": rf1, "r1": r1, "rp": rp, "r12": r12})
    rad.sort(key=lambda r: -(r["rf1"] if r["rf1"] is not None else r["r1"]))
    RES["fond"][BRUKT[f]] = rad
    g = lambda v: "   -" if v is None else f"{v:+.2f}"
    print(f"   {BRUKT[f]}: {KURS[f].index[0]} til {KURS[f].index[-1]}, sortert paa rf1 (fra {FIKS})")
    print(f"      {'raavare':42} {'n':>4} {'nf':>4} {'rf1':>6} {'r1':>6} {'rp':>6} {'r12':>6}")
    for r in rad[:20]:
        print(f"      {r['raavare'][:42]:42} {r['n']:4d} {r['nf']:4d} {g(r['rf1']):>6} {g(r['r1']):>6} {g(r['rp']):>6} {g(r['r12']):>6}")
    print("      ... svakeste fem:")
    for r in rad[-5:]:
        print(f"      {r['raavare'][:42]:42} {r['n']:4d} {r['nf']:4d} {g(r['rf1']):>6} {g(r['r1']):>6} {g(r['rp']):>6} {g(r['r12']):>6}")
    print()

os.makedirs("sonder", exist_ok=True)
json.dump(RES, open("sonder/brasil.json", "w"), ensure_ascii=False, indent=1)
print("Lagret sonder/brasil.json")
