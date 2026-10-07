# ---------------------------------------------------------------------------
# sonde_kjor_laks_valuta: A for norsk laks som kompositt av pris og valuta,
# og test av vektene i kompositten.
#
# Frodes bestilling 07.10.2026. Sonden endrer ingenting paa dashbordet. Laks
# har ikke flagg i Champion v1.0; et flagg kan bare bli Challenger.
#
# DELSKAARENE (alle punkt-i-tid, persentil mot egen historikk som A ellers):
#   a_pris    realpris i EUR: sesongjustert eksportpris i NOK fra laksesonden
#             (sonder/laks.csv, just_nok_log) delt paa EURNOK fra Norges Bank,
#             deflatert med HICP for euroomraadet (Eurostat). Lav pris gir
#             hoey skaar.
#   a_valuta  realkursen for kronen mot en fast laksekurv, 75 % EUR og 25 %
#             USD (satt foer kjoering), justert for KPI i Norge (SSB),
#             euroomraadet og USA. Sterk krone gir hoey skaar.
#   Kostnaden er med vilje utenfor kompositten: kostnadssjokk (2023) er
#   strukturelle og vender ikke tilbake slik pris og valuta gjoer.
#
# KOMPOSITTEN: A = 100 * a_pris^(1-w) * a_valuta^w, med a i [0, 1].
# Vektene som testes er satt foer kjoering: w = 0, 0,25, 0,5, 0,75 og 1.
# w = 0 er pris alene, w = 1 er valuta alene. Margin-A fra panelet i dag
# (pris i NOK mot kostnad) vises ved siden av som referanse.
#
# UTFALL: norske laksepapirer, SalMar, Leroy, Grieg og Masoval (Mowi og
# Bakkafrost har mye produksjon utenfor Norge og er utenfor), likt vektet
# maanedlig log-avkastning i NOK. Primaert utfall 24 maaneder fram.
# Sekundaert: samme kurv minus OSEBX, og 12 maaneder.
#
# TESTEN, samme maskineri som laksesonden 25.09.2026:
#   T1  informasjon uten terskel: rangkorrelasjon mellom A og kurvens
#       24-maanedersutfall, p fra sirkulaer blokkbootstrap (24 mnd) av
#       kurvens maanedsavkastninger. Laksesonden kalibrerte denne nullen til
#       5,0 % falske funn paa 200 simuleringer.
#   T2  episoder ved fast terskel A >= 80 (ikke soekt): foerste maaned etter
#       mer enn 12 uten signal. Median utfall, og median naar hver episode tas
#       ut en og en.
#   T3  stabilitet: rho i foerste og andre halvdel av perioden hver for seg.
#
# BESLUTNINGSREGEL, skrevet foer kjoering:
#   B1  Fem vekter testes, saa en vekt regnes bare som informativ med
#       p <= 0,02 (0,10 delt paa 5). Ellers: ingen kompositt har vist
#       informasjon, og laks faar ikke flagg fra denne sonden.
#   B2  w = 0,5 staar som standard. En annen vekt velges bare hvis den er
#       informativ etter B1, 0,5 ikke er det (p over 0,10), OG den har hoeyere
#       rho enn 0,5 i begge halvdeler. Vektene optimaliseres ikke utover dette.
#   B3  Valuta tilfoerer noe bare hvis rho for w = 0,5 er hoeyere enn for
#       w = 0 i begge halvdeler.
# Alt her er IN_SAMPLE. Et flagg som bygges paa dette, maa registreres som
# Challenger og maales fremover.
# ---------------------------------------------------------------------------

import ast, io, json, time
import numpy as np
import pandas as pd
import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
MIRROR = "https://raw.githubusercontent.com/datasets/"
VEKTER = [0.0, 0.25, 0.5, 0.75, 1.0]
KURV_EUR, KURV_USD = 0.75, 0.25
PAPIR = {"SALM.OL": "SalMar", "LSG.OL": "Leroy", "GSF.OL": "Grieg", "MAS.OL": "Masoval"}
TERSKEL, PAUSE, BLOKK, TREKK = 80, 12, 24, 500
rng = np.random.default_rng(20261007)


def get(url, **kw):
    for i in range(3):
        try:
            r = requests.get(url, headers=kw.pop("headers", UA), timeout=kw.pop("timeout", 60), **kw)
            if r.status_code in (429, 502, 503):
                time.sleep(4 * (i + 1)); continue
            return r
        except requests.RequestException:
            if i == 2:
                raise
            time.sleep(2 * (i + 1))


def last_fra(fil, navn):
    t = ast.parse(open(fil, encoding="utf-8").read())
    kropp = [n for n in t.body if isinstance(n, ast.FunctionDef) and n.name in navn]
    ns = {"np": np, "MIN_HIST": 60}
    exec(compile(ast.Module(body=kropp, type_ignores=[]), fil, "exec"), ns)
    return ns

expanding_pct = last_fra("priser.py", {"expanding_pct"})["expanding_pct"]


def mnd(serie):
    s = serie.dropna()
    return s[~s.index.duplicated(keep="last")].sort_index()


print("1. DATA\n")
L = pd.read_csv("sonder/laks.csv", index_col=0)
L.index = pd.PeriodIndex(L.index, freq="M")
LN_NOK = L["just_nok_log"].dropna()
print(f"   laksepris (sesongjustert, NOK) {LN_NOK.index[0]} til {LN_NOK.index[-1]}")

def norges_bank(kode):
    r = get(f"https://data.norges-bank.no/api/data/EXR/M.{kode}.NOK.SP?format=csv&startPeriod=1995&locale=en")
    d = pd.read_csv(io.StringIO(r.text), sep=None, engine="python")
    tk = next(c for c in d.columns if "TIME" in c.upper()); vk = next(c for c in d.columns if "OBS_VALUE" in c.upper())
    return mnd(pd.Series(pd.to_numeric(d[vk].astype(str).str.replace(",", "."), errors="coerce").values,
                         index=pd.PeriodIndex(d[tk].astype(str), freq="M")))

EURNOK, USDNOK = norges_bank("EUR"), norges_bank("USD")
print(f"   EURNOK {EURNOK.index[0]} til {EURNOK.index[-1]}, siste {EURNOK.iloc[-1]:.3f}")
print(f"   USDNOK {USDNOK.index[0]} til {USDNOK.index[-1]}, siste {USDNOK.iloc[-1]:.3f}")

j = get("https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/prc_hicp_midx"
        "?geo=EA&coicop=CP00&unit=I15&format=JSON").json()
tid = j["dimension"]["time"]["category"]["index"]
HICP = mnd(pd.Series({pd.Period(t, "M"): j["value"].get(str(i)) for t, i in tid.items()}).astype(float))
r = requests.post("https://data.ssb.no/api/v0/no/table/03013/", timeout=60, json={
    "query": [{"code": "Konsumgrp", "selection": {"filter": "item", "values": ["TOTAL"]}},
              {"code": "ContentsCode", "selection": {"filter": "item", "values": ["KpiIndMnd"]}}],
    "response": {"format": "json-stat2"}}).json()
KPI_NO = mnd(pd.Series(r["value"], index=pd.PeriodIndex([t.replace("M", "-") for t in r["dimension"]["Tid"]["category"]["index"]], freq="M")).astype(float))
c = pd.read_csv(io.StringIO(get(MIRROR + "cpi-us/main/data/cpiai.csv").text)).iloc[:, :2]
KPI_US = mnd(pd.Series(c.iloc[:, 1].values, index=pd.PeriodIndex(pd.to_datetime(c.iloc[:, 0]), freq="M")).astype(float))
for navn, s in (("HICP euroomraadet", HICP), ("KPI Norge", KPI_NO), ("KPI USA", KPI_US)):
    print(f"   {navn:18s} {s.index[0]} til {s.index[-1]}")
SLUTT = LN_NOK.index[-1]
def til_slutt(s):
    """KPI forlenges flatt til siste prismaaned hvis den slutter tidligere (skrives ut)."""
    if s.index[-1] < SLUTT:
        s = s.reindex(pd.period_range(s.index[0], SLUTT, freq="M")).ffill()
    return s
HICP, KPI_NO, KPI_US = til_slutt(HICP), til_slutt(KPI_NO), til_slutt(KPI_US)
print(f"   (KPI som slutter foer {SLUTT}, er forlenget flatt; utgjoer mindre enn 1 % i realkursen)")


def yahoo(sym):
    r = get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?period1=0&period2={int(time.time())}"
            f"&interval=1mo&events=div%7Csplit&includeAdjustedClose=true").json()
    res = r["chart"]["result"][0]
    tz = (res.get("meta") or {}).get("exchangeTimezoneName") or "UTC"
    idx = pd.to_datetime(res["timestamp"], unit="s", utc=True).tz_convert(tz).to_period("M")
    adj = (res["indicators"].get("adjclose") or [{}])[0].get("adjclose") or res["indicators"]["quote"][0]["close"]
    s = pd.Series(adj, index=idx).dropna()
    return mnd(s[s > 0])

KURS = {}
for tk in PAPIR:
    try:
        KURS[tk] = yahoo(tk); print(f"   {tk:8s} {KURS[tk].index[0]} til {KURS[tk].index[-1]}")
    except Exception as e:
        print(f"   {tk:8s} {type(e).__name__}")
    time.sleep(0.3)
OSEBX = yahoo("OSEBX.OL")
print(f"   OSEBX    {OSEBX.index[0]} til {OSEBX.index[-1]}")


print("\n\n2. DELSKAARENE\n")
idx = LN_NOK.index
ln_eur_real = (LN_NOK - np.log(EURNOK.reindex(idx)) - np.log(HICP.reindex(idx))).dropna()
utl = KURV_EUR * np.log(HICP) + KURV_USD * np.log(KPI_US)
kurv_nom = KURV_EUR * np.log(EURNOK) + KURV_USD * np.log(USDNOK)
ln_valuta_real = (kurv_nom + utl - np.log(KPI_NO)).dropna()       # hoey = svak krone
a_pris = pd.Series(1 - expanding_pct(ln_eur_real.values), index=ln_eur_real.index)
a_val = pd.Series(1 - expanding_pct(ln_valuta_real.values), index=ln_valuta_real.index)
felles = a_pris.dropna().index.intersection(a_val.dropna().index)
a_pris, a_val = a_pris[felles], a_val[felles]
print(f"   a_pris og a_valuta regnes fra {felles[0]} (60 maaneder historikk kreves)")
print(f"   korrelasjon mellom a_pris og a_valuta: {a_pris.corr(a_val):.2f}")

A = {w: 100 * np.maximum(a_pris, 0.01) ** (1 - w) * np.maximum(a_val, 0.01) ** w for w in VEKTER}
A_MARGIN = L["A_margin"].dropna()


print("\n\n3. UTFALL\n")
kurv_ret = pd.concat({tk: np.log(s).diff() for tk, s in KURS.items()}, axis=1).mean(axis=1, skipna=True).dropna()
oseb_ret = np.log(OSEBX).diff().dropna()
mer_ret = (kurv_ret - oseb_ret.reindex(kurv_ret.index)).dropna()
def fram(ret, h):
    c = ret.cumsum()
    return c.shift(-h) - c
UTF = {"kurv24": fram(kurv_ret, 24), "kurv12": fram(kurv_ret, 12), "mer24": fram(mer_ret, 24)}
print(f"   kurv fra {kurv_ret.index[0]}, antall papirer per aar: "
      + ", ".join(f"{a}:{n}" for a, n in pd.concat({tk: s for tk, s in KURS.items()}, axis=1)
                  .notna().sum(axis=1).groupby(lambda p: p.year).max().items() if a % 3 == 0))


def rangkorr(a, b):
    d = pd.concat([a, b], axis=1).dropna()
    return (float(d.iloc[:, 0].rank().corr(d.iloc[:, 1].rank())), len(d)) if len(d) >= 36 else (np.nan, len(d))

def blokktrekk(x, n):
    ut = []
    while len(ut) < n:
        st = rng.integers(len(x)); ut.extend(x[(st + np.arange(BLOKK)) % len(x)])
    return np.array(ut[:n])

def t1(a, ret, h=24):
    obs, n = rangkorr(a, fram(ret, h))
    if not np.isfinite(obs):
        return np.nan, np.nan, n
    null = []
    for _ in range(TREKK):
        rr = pd.Series(blokktrekk(ret.values, len(ret)), index=ret.index)
        null.append(rangkorr(a, fram(rr, h))[0])
    null = np.array([x for x in null if np.isfinite(x)])
    return obs, float(((null >= obs).sum() + 1) / (len(null) + 1)), n

def innslag(sig):
    ut, siste = [], None
    for t, v in sig.items():
        if v and (siste is None or (t - siste).n > PAUSE):
            ut.append(t)
        if v:
            siste = t
    return ut

pst = lambda v: "-" if not np.isfinite(v) else f"{100 * (np.exp(v) - 1):+.0f}%"

print("\n\n4. T1 OG T3: INFORMASJON UTEN TERSKEL (kurv 24 mnd, rangkorrelasjon)\n")
f_idx = A[0.5].index.intersection(UTF["kurv24"].dropna().index)
midt = f_idx[len(f_idx) // 2]
print(f"   felles periode med utfall: {f_idx[0]} til {f_idx[-1]}, halvdelene deles ved {midt}\n")
print(f"   {'kompositt':14s} {'rho':>6s} {'p':>6s} {'n':>4s} | {'rho 1. halvdel':>14s} {'rho 2. halvdel':>14s} | {'rho mer24':>9s} {'rho kurv12':>10s}")
RES = {}
kandidater = [(f"w={w}", A[w]) for w in VEKTER] + [("margin-A (ref)", A_MARGIN)]
for navn, a in kandidater:
    rho, p, n = t1(a, kurv_ret, 24)
    h1, _ = rangkorr(a[a.index < midt], UTF["kurv24"]); h2, _ = rangkorr(a[a.index >= midt], UTF["kurv24"])
    m24, _ = rangkorr(a, UTF["mer24"]); k12, _ = rangkorr(a, UTF["kurv12"])
    RES[navn] = {"rho": rho, "p": p, "h1": h1, "h2": h2}
    print(f"   {navn:14s} {rho:6.3f} {p:6.3f} {n:4d} | {h1:14.3f} {h2:14.3f} | {m24:9.3f} {k12:10.3f}")

print(f"\n\n5. T2: EPISODER VED A >= {TERSKEL} (fast terskel, pause {PAUSE} mnd)\n")
for navn, a in kandidater:
    inn = innslag(a >= TERSKEL)
    v = {t: UTF["kurv24"].get(t, np.nan) for t in inn}
    med = [x for x in v.values() if np.isfinite(x)]
    loo = [np.median([x for s, x in v.items() if s != t and np.isfinite(x)]) for t in v if len(med) > 1]
    loo = [x for x in loo if np.isfinite(x)]
    print(f"   {navn:14s} {len(inn)} episoder, {len(med)} med fasit, median kurv 24 mnd {pst(np.median(med) if med else np.nan)}"
          + (f", uten en og en {pst(min(loo))} til {pst(max(loo))}" if loo else ""))
    print(f"   {'':14s} " + ", ".join(f"{t} {pst(v[t])}" for t in inn))

print("\n\n6. BESLUTNING (regelen satt foer kjoering)\n")
INFO = 0.10 / len(VEKTER)
info = [w for w in VEKTER if RES[f"w={w}"]["p"] <= INFO]
print(f"   B1 informativ (p <= {INFO:.2f}): {', '.join(f'w={w}' for w in info) or 'ingen'}")
valgt = 0.5
r5 = RES["w=0.5"]
for w in info:
    r = RES[f"w={w}"]
    if w != 0.5 and r5["p"] > 0.10 and r["h1"] > r5["h1"] and r["h2"] > r5["h2"]:
        if valgt == 0.5 or r["rho"] > RES[f"w={valgt}"]["rho"]:
            valgt = w
print(f"   B2 vekt: w = {valgt}" + ("  (standard, ingen annen vekt oppfylte kravet)" if valgt == 0.5 else ""))
r0 = RES["w=0.0"]
tilf = r5["h1"] > r0["h1"] and r5["h2"] > r0["h2"]
print(f"   B3 valuta tilfoerer noe (w=0,5 over w=0 i begge halvdeler): {'ja' if tilf else 'nei'}"
      f"  ({r5['h1']:.3f}/{r5['h2']:.3f} mot {r0['h1']:.3f}/{r0['h2']:.3f})")
print("   " + ("Minst en kompositt viste informasjon." if info else
             "Ingen kompositt viste informasjon etter B1. Laks faar ikke flagg fra denne sonden."))

print("\n\n7. I DAG\n")
s = felles[-1]
print(f"   {s}: a_pris {100 * a_pris[s]:.0f}, a_valuta {100 * a_val[s]:.0f}, "
      + ", ".join(f"A(w={w}) {A[w][s]:.0f}" for w in VEKTER) + f", margin-A {A_MARGIN.iloc[-1]:.0f}")
print(f"   EURNOK {EURNOK.iloc[-1]:.2f}, realpris {np.exp(ln_eur_real.iloc[-1]) * 100:.2f} (EUR/kg i HICP-2015-kroner)")
ks = {int(k): float(v) for k, v in json.load(open("laks_kost.json", encoding="utf-8"))["ny"].items()}
if ks:
    if 2021 in ks and max(ks) >= 2023:
        a1, a2 = 2021, max(ks)
        d_pris = LN_NOK[str(a2)].mean() - LN_NOK[str(a1)].mean()
        d_eur = np.log(EURNOK[str(a2)].mean() / EURNOK[str(a1)].mean())
        d_kost = np.log(ks[a2] / ks[a1])
        print(f"\n   Hvorfor marginen er lav: endring {a1} til {a2} i log")
        print(f"     laksepris i EUR {d_pris - d_eur:+.3f}, EURNOK (svak krone hjelper) {d_eur:+.3f}, kostnad {d_kost:+.3f}"
              f"  -> margin {d_pris - d_kost:+.3f}")
