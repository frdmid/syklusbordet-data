# ---------------------------------------------------------------------------
# sonde_kjor_instrumenttest: kan bunnflagget kjoeres rett paa papirene
#
# Spoersmaalet (Frode, 24.09.2026): kan metodikken kjoeres direkte paa
# instrumentene med samme regler, i stedet for aa gaa veien om raavarene?
#
# Fire varianter, maalt paa de samme papirene, i samme vindu, med samme
# utfall og samme statistikk. Det er sammenligningen som er poenget, ikke
# nivaaet paa hver enkelt.
#
#   a    RAAVAREFLAGGET. Papiret flagges naar ett av dets egne raavaresegmenter
#        staar i bunnsone (raa A >= 80 og detrendet A >= 80), slik bordet gjoer
#        i dag. Referansen.
#   b    SAMME REGEL PAA KURSEN. Raa og detrendet persentil av papirets egen
#        realkurs (totalavkastning, dollar, deflatert med amerikansk KPI), begge
#        >= 80. Ventet svakhet: aksjer har langsiktig drift og utvanning, og
#        dette ligner mye paa D, som allerede maaler fall paa papiret.
#   a+b  BEGGE I SAMME MAANED. Raavaren i bunnsone og papiret selv like lavt.
#        Naermest det bordet egentlig ber om naar A og D leses sammen.
#   c    VERDSETTELSE. Persentil av pris mot bokfoert egenkapital per aksje,
#        mot papirets egen historikk, >= 80 (billigste femtedel). Bare
#        amerikanske papirer som rapporterer i dollar til SEC, fordi det er de
#        eneste med gratis bokfoert egenkapital kvartal for kvartal. Bokfoert
#        verdi brukes foerst fra maaneden rapporten ble levert, ikke fra
#        periodens slutt, saa signalet kunne vaert kjent paa datoen.
#
# UNIVERS
#   Papirene fra IKZ-sonden som var ventet aa folge en av de seksten aktive
#   raavarene som PRODUSENT (forbrukerne tas ut av a og a+b, fordi inngangen
#   for dem er raavarens topp, og det er en annen regel). Pluss papirene paa
#   tavlen for skipssegmentene i b og c, der a ikke finnes. Uran er med, paa
#   Camecos serie, ikke IMF-serien med brudd fra 2021.
#   To delmengder rapporteres: TAVLE (papirene som staar paa dashbordet i dag)
#   og UTVIDET (alle produsentpapirene).
#
# VINDU OG UTFALL
#   Signalmaaneder 2011-09 til 2024-09, altsaa samme periode som flaggtesten,
#   og siste signal med 24 maaneder fasit. Utfallet er realavkastning 12 og 24
#   maaneder etter signalet, i dollar med utbytte. Et papir kan ha nytt
#   innslag foerst etter tolv maaneder uten signal.
#
#   Meravkastning = avkastningen etter signalet minus papirets egen
#   gjennomsnittlige avkastning over like lange perioder fra alle maaneder i
#   vinduet. Da sammenlignes et signal med tilfeldige kjoepsdatoer i samme
#   papir, og papirer som bare har steget hele perioden faar ikke aeren.
#
# TEST
#   Kalenderportefolje: hver maaned holdes alle papirer som har faatt et
#   innslag de siste 12 eller 24 maanedene, likt vektet, mot snittet av hele
#   universet samme maaned. Nullen beholder alle innslagsdatoene, men bytter
#   hvert papir med et tilfeldig papir som har kurs paa datoen, 1000 ganger.
#   Spoersmaalet blir da: slaar de flaggede papirene tilfeldige papirer
#   kjoept paa de samme dagene? Klumpingen i tid er noyaktig bevart, saa 30
#   innslag i samme nedtur teller som det de er.
#
#   Kalibrert paa simulerte tilfeldige kurser foer bruk, der en riktig test
#   gir p under 0,05 i 5 % av tilfellene:
#     mot papirets egne tilfeldige datoer     23 %  forkastet. Skjevt for b og
#                                                   a+b: et papir med kurssignal
#                                                   har hatt en daarlig periode,
#                                                   saa snittet av egne datoer
#                                                   blir lavt
#     kalenderportefolje, Newey-West-t        11-16 % for a, forkastet. For
#                                                   faa episoder til at t holder
#     kalenderportefolje, tilfeldige papirer  4,2 % av 716 tester (45
#                                                   simuleringer), 2 til 8 % per
#                                                   variant. Denne brukes.
#
#   Episoder (innslag med hoyst seks maaneder mellom) er beskrivende.
#
#   Fallende kniv: hvor mye papiret falt videre de neste tolv maanedene, og
#   andelen innslag med mer enn 30 % videre fall.
#
# TRE FORBEHOLD SOM ER REELLE
#   1. Overlevelse. Papirene er hentet fra dagens kurslister. Selskaper som
#      gikk konkurs ved en bunn finnes ikke, og det trekker b og c opp.
#      Variant a er like utsatt i denne testen, siden utfallet maales paa de
#      samme papirene.
#   2. Faa hendelser. Vinduet har rundt fire uavhengige nedturer (2015-16,
#      2018, 2020, 2022). Ingen p-verdi her kan bli svaert liten.
#   3. Klyngeregelen er satt her og ikke hentet fra flaggtesten, men den er
#      den samme for alle fire variantene.
# ---------------------------------------------------------------------------

import ast, io, json, os, re, time, warnings
import numpy as np
import pandas as pd
import requests

warnings.filterwarnings("ignore")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
SEC_UA = {"User-Agent": "Syklusbordet frode@h-k.no"}
MIRROR = "https://raw.githubusercontent.com/datasets/"

FRA, TIL = pd.Period("2011-09", "M"), pd.Period("2024-09", "M")
PAUSE_MND = 12      # nytt innslag i samme papir foerst etter tolv maaneder uten signal
KLYNGEGAP = 6       # maaneder
AKTIVE = {"brent", "wti", "henryhub", "ttf", "gold", "kobber", "nikkel", "aluminium",
          "sink", "bly", "tinn", "jernmalm", "kull", "kakao", "palmeolje", "uran"}


def get(url, headers=UA, **kw):
    for i in range(3):
        try:
            r = requests.get(url, headers=headers, timeout=kw.pop("timeout", 40), **kw)
            if r.status_code in (429, 502, 503):
                time.sleep(4 * (i + 1)); continue
            r.raise_for_status()
            return r
        except requests.RequestException:
            if i == 2:
                raise
            time.sleep(2 * (i + 1))
    raise RuntimeError("ga opp")


# ------------------------------------------------ samme regler som priser.py
# Funksjonene hentes fra priser.py selv, ikke kopieres, slik at testen maaler
# noyaktig det bordet gjoer.
def last_fra(fil, navn):
    t = ast.parse(open(fil, encoding="utf-8").read())
    kropp = [n for n in t.body if isinstance(n, ast.FunctionDef) and n.name in navn]
    ns = {"np": np, "MIN_HIST": 60}
    exec(compile(ast.Module(body=kropp, type_ignores=[]), fil, "exec"), ns)
    return ns

P = last_fra("priser.py", {"expanding_pct", "expanding_pct_detrend"})
expanding_pct, expanding_pct_detrend = P["expanding_pct"], P["expanding_pct_detrend"]


def flagg_paa(serie):
    """Raa og detrendet A >= 80 paa log av en realserie. Returnerer bool-serie."""
    lr = np.log(serie.values)
    A = (1 - expanding_pct(lr)) * 100
    Ad = expanding_pct_detrend(lr)
    f = [(not np.isnan(A[i])) and (not np.isnan(Ad[i])) and A[i] >= 80 and Ad[i] >= 80
         for i in range(len(lr))]
    return pd.Series(f, index=serie.index)


# ================================================================ 1. univers
print("1. Univers\n")
src = ast.parse(open("sonde_ikz.py", encoding="utf-8").read())
kropp = [n for n in src.body if isinstance(n, ast.Assign) and any(
    isinstance(x, ast.Name) and x.id in ("E", "F", "KANDIDATER", "FORBRUKER", "BLANDET")
    for x in n.targets)]
ns = {}
exec(compile(ast.Module(body=kropp, type_ignores=[]), "sonde_ikz.py", "exec"), ns)
KAND, FORBR, BLAND = ns["KANDIDATER"], ns["FORBRUKER"], ns["BLANDET"]

from instrumenter import INSTR
TAVLE = {tk for rader in INSTR.values() for tk, *_ in rader}
TAVLE_SEG = {}
for sid, rader in INSTR.items():
    for tk, *_ in rader:
        TAVLE_SEG.setdefault(tk, set()).add(sid)

UNIV = {}
for k in KAND:
    segs = {s for s in k["segmenter"] if s in AKTIVE} - FORBR.get(k["t"], set()) - BLAND.get(k["t"], set())
    if segs:
        UNIV[k["t"]] = {"navn": k["navn"], "segs": segs, "alt": k.get("alt") or []}
for tk, segs in TAVLE_SEG.items():
    rader = [r for sid in segs for r in INSTR[sid] if r[0] == tk]
    omvendt = any(r[4].strip().startswith("-") for r in rader)
    if tk not in UNIV:
        UNIV[tk] = {"navn": rader[0][2], "segs": set() if omvendt else {s for s in segs if s in AKTIVE},
                    "alt": [], "skip": all(s.startswith("ship_") for s in segs)}
    if omvendt:
        UNIV[tk]["segs"] = set()          # forbruker: ikke med i a
print(f"   {len(UNIV)} papirer, {len(TAVLE & set(UNIV))} av dem paa tavlen")


# =========================================================== 2. data
print("\n2. Data\n")
cpi = pd.read_csv(io.StringIO(get(MIRROR + "cpi-us/main/data/cpiai.csv").text)).iloc[:, :2]
cpi.columns = ["d", "v"]
cpi = pd.Series(cpi["v"].values, index=pd.PeriodIndex(pd.to_datetime(cpi["d"]), freq="M")).dropna()
cpi = cpi.reindex(pd.period_range(cpi.index[0], cpi.index[-1], freq="M")).ffill()
BASE = float(cpi.iloc[-1])
def realt(s):
    k = cpi.reindex(s.index).fillna(BASE)
    return s * BASE / k

# raavareflagg fra segmentfilene (grafvinduet starter 2011-09, samme som FRA)
RFLAGG = {}
for sid in AKTIVE:
    try:
        d = json.load(open(f"segments/{sid}.json", encoding="utf-8"))
        RFLAGG[sid] = pd.Series({pd.Period(r["t"], "M"): bool(r.get("flagg")) for r in d["series"]})
    except Exception as e:
        print(f"   FEIL segment {sid}: {e}")
print(f"   raavareflagg: {len(RFLAGG)} segmenter, "
      f"{sum(int(s[(s.index >= FRA) & (s.index <= TIL)].sum()) for s in RFLAGG.values())} flaggmaaneder i vinduet")


def yahoo(sym):
    r = get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}"
            f"?period1=0&period2={int(time.time())}&interval=1mo"
            f"&events=div%7Csplit&includeAdjustedClose=true").json()["chart"]["result"][0]
    meta = r.get("meta") or {}
    tz = meta.get("exchangeTimezoneName") or "UTC"
    idx = pd.to_datetime(r["timestamp"], unit="s", utc=True).tz_convert(tz).to_period("M")
    q = r["indicators"]["quote"][0]
    adj = (r["indicators"].get("adjclose") or [{}])[0].get("adjclose")
    df = pd.DataFrame({"close": q.get("close"), "adj": adj}, index=idx)
    df = df[~df.index.duplicated(keep="last")].dropna()
    df = df[(df["close"] > 0) & (df["adj"] > 0)]
    splits = [(pd.Timestamp(v["date"], unit="s").to_period("M"), v["numerator"] / v["denominator"])
              for v in ((r.get("events") or {}).get("splits") or {}).values()]
    return df, meta.get("currency") or "USD", splits


FX = {"USD": None, "EUR": ("EURUSD=X", False), "GBP": ("GBPUSD=X", False),
      "GBp": ("GBPUSD=X", False), "NOK": ("NOK=X", True), "SEK": ("SEK=X", True),
      "DKK": ("DKK=X", True), "CHF": ("CHF=X", True), "CAD": ("CAD=X", True),
      "AUD": ("AUDUSD=X", False)}
_fx = {}
def fx(val):
    sym, inv = FX[val]
    if sym not in _fx:
        s = yahoo(sym)[0]["close"]
        _fx[sym] = 1 / s if inv else s
    return _fx[sym]

KURS, RAA, SPLIT, VAL = {}, {}, {}, {}
bom = []
for tk, u in UNIV.items():
    ok = False
    for sym in [tk] + u["alt"]:
        try:
            df, val, sp = yahoo(sym)
            if len(df) < 72 or val not in FX:
                continue
            s = df["adj"]
            if FX[val]:
                s = (s * fx(val).reindex(s.index).ffill()).dropna()
            if val == "GBp":
                s = s / 100
            KURS[tk] = realt(s)
            RAA[tk] = df["close"]; SPLIT[tk] = sp; VAL[tk] = val
            ok = True
            break
        except Exception:
            pass
        time.sleep(0.25)
    if not ok:
        bom.append(tk)
    time.sleep(0.2)
print(f"   kurser: {len(KURS)} av {len(UNIV)} papirer med minst 72 maaneder. Bom: {', '.join(bom) or 'ingen'}")


# ------------------------------------------ bokfoert egenkapital fra SEC (c)
print("\n   SEC, bokfoert egenkapital for amerikanske papirer i dollar")
BPS = {}
try:
    kart = get("https://www.sec.gov/files/company_tickers.json", headers=SEC_UA).json()
    CIK = {str(v["ticker"]).upper(): str(v["cik_str"]).zfill(10) for v in kart.values()}
except Exception as e:
    CIK = {}
    print(f"   SEC-kartet feilet: {e}")

def fakta(f, tak, begrep, enhet):
    d = f.get(tak, {}).get(begrep, {}).get("units", {}).get(enhet, [])
    return [x for x in d if x.get("end") and x.get("filed") and x.get("val") is not None]

for tk in sorted(KURS):
    if "." in tk or VAL.get(tk) != "USD" or tk.upper() not in CIK:
        continue
    try:
        f = get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{CIK[tk.upper()]}.json",
                headers=SEC_UA, timeout=90).json().get("facts", {})
        ek = (fakta(f, "us-gaap", "StockholdersEquity", "USD")
              or fakta(f, "us-gaap", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest", "USD"))
        ak = (fakta(f, "us-gaap", "CommonStockSharesOutstanding", "shares")
              or fakta(f, "dei", "EntityCommonStockSharesOutstanding", "shares"))
        if not ek or not ak:
            continue
        # foerste innlevering per periodeslutt: det som var kjent da, ikke en
        # senere rettelse
        ek0 = {}
        for x in sorted(ek, key=lambda x: x["filed"]):
            ek0.setdefault(x["end"], x)
        ek = ek0
        ak = sorted(ak, key=lambda x: x["end"])
        akd = [(pd.Timestamp(x["end"]), float(x["val"])) for x in ak if float(x["val"]) > 0]
        rader = []
        for end, x in ek.items():
            te = pd.Timestamp(end)
            naer = min(akd, key=lambda a: abs((a[0] - te).days), default=None)
            if naer is None or abs((naer[0] - te).days) > 100 or float(x["val"]) <= 0:
                continue
            rader.append((pd.Timestamp(x["filed"]).to_period("M"), te, float(x["val"]) / naer[1]))
        if len(rader) < 12:
            continue
        # kjent-fra-maaned: siste periode som var levert innen maaneden
        rader.sort(key=lambda r: (r[0], r[1]))
        s, nyest = {}, None
        for filed, te, bps in rader:
            if nyest is None or te >= nyest:   # en sen rettelse av en gammel periode
                s[filed] = bps; nyest = te      # skal ikke erstatte en nyere periode
        BPS[tk] = pd.Series(s).sort_index()
        time.sleep(0.15)
    except Exception as e:
        print(f"      {tk}: {type(e).__name__} {str(e)[:50]}")
print(f"   {len(BPS)} papirer med bokfoert egenkapital per aksje")


def pb_serie(tk):
    """Pris mot bok. Yahoo sin 'close' er splittjustert, SEC sitt aksjetall er
    det ikke, saa kursen gjoeres om til faktisk kurs paa datoen foer deling."""
    raa = RAA[tk].copy()
    for p, faktor in SPLIT.get(tk, []):
        raa[raa.index < p] = raa[raa.index < p] * faktor
    b = BPS[tk].reindex(pd.period_range(BPS[tk].index[0], raa.index[-1], freq="M")).ffill()
    pb = (raa / b.reindex(raa.index)).dropna()
    return pb[(pb > 0) & (pb < 100)]


# =========================================================== 3. signaler
print("\n3. Signaler")
SIG = {"a": {}, "b": {}, "a+b": {}, "c": {}}
for tk, s in KURS.items():
    u = UNIV[tk]
    fb = flagg_paa(s)
    SIG["b"][tk] = fb
    if u["segs"]:
        fa = None
        for sid in u["segs"]:
            if sid in RFLAGG:
                x = RFLAGG[sid].reindex(s.index).fillna(False).astype(bool)
                fa = x if fa is None else (fa | x)
        if fa is not None:
            SIG["a"][tk] = fa
            SIG["a+b"][tk] = fa & fb
    if tk in BPS:
        pb = pb_serie(tk)
        if len(pb) >= 72:
            A = (1 - expanding_pct(np.log(pb.values))) * 100
            SIG["c"][tk] = pd.Series([(not np.isnan(a)) and a >= 80 for a in A], index=pb.index).reindex(s.index).fillna(False).astype(bool)
for v, d in SIG.items():
    m = sum(int(x[(x.index >= FRA) & (x.index <= TIL)].sum()) for x in d.values())
    print(f"   {v:4} {len(d):3} papirer, {m} signalmaaneder i vinduet")


# =========================================================== 4. utfall
def fram(s, h):
    """Log-realavkastning h maaneder fram, per maaned."""
    return np.log(s.shift(-h) / s)

FWD = {h: {tk: fram(s, h) for tk, s in KURS.items()} for h in (12, 24)}
SNITT = {h: {tk: float(x[(x.index >= FRA) & (x.index <= TIL)].dropna().mean())
             for tk, x in FWD[h].items()} for h in (12, 24)}

def videre_fall(s, t):
    i = s.index.get_loc(t)
    fram12 = s.iloc[i + 1:i + 13]
    return None if len(fram12) < 12 else float(fram12.min() / s.iloc[i] - 1)


def innslag(sig, tk):
    x = sig[(sig.index >= FRA) & (sig.index <= TIL)]
    ut, siste = [], None
    for t, v in x.items():
        if v and (siste is None or (t - siste).n > PAUSE_MND):
            ut.append(t)
        if v:
            siste = t
    return ut


def klynger(inn):
    inn = sorted(inn, key=lambda e: e["t"])
    kl, cur = [], []
    for e in inn:
        if cur and (e["t"] - cur[-1]["t"]).n > KLYNGEGAP:
            kl.append(cur); cur = []
        cur.append(e)
    if cur:
        kl.append(cur)
    return kl


MND = pd.period_range(FRA, TIL, freq="M")

# Maanedlige log-realavkastninger i en tabell: rad = maaned, kolonne = papir.
RET = pd.DataFrame({tk: np.log(s / s.shift(1)) for tk, s in KURS.items()})


RV = RET.values                       # T x N, NaN der papiret ikke finnes
GYLDIG = np.isfinite(RV)
RIDX = {p: i for i, p in enumerate(RET.index)}
CIDX = {c: j for j, c in enumerate(RET.columns)}
I_FRA, I_TIL = RIDX.get(FRA, 0), RIDX.get(TIL, len(RET.index) - 1)
TREKK = 1000
rng = np.random.default_rng(20260924)


def kal_stat(rader, kol, h, cols):
    """Snitt av maanedlig meravkastning for kalenderportefoljen: papirer holdt
    i h maaneder etter innslag, likt vektet, mot snittet av universet."""
    T = RV.shape[0]
    H = np.zeros((T, RV.shape[1]), bool)
    for r, c in zip(rader, kol):
        H[r + 1:r + 1 + h, c] = True
    H &= GYLDIG
    H[:, ~cols] = False
    n = H.sum(1)
    uni = np.where(GYLDIG[:, cols], RV[:, cols], 0).sum(1) / np.maximum(GYLDIG[:, cols].sum(1), 1)
    port = np.where(H, RV, 0).sum(1) / np.maximum(n, 1)
    m = (n > 0) & (np.arange(T) > I_FRA) & (np.arange(T) <= I_TIL + h)
    return (float(np.mean(port[m] - uni[m])), int(m.sum())) if m.any() else (np.nan, 0)


def kalendertest(inn, papirer, h):
    """Kalenderportefolje mot universet, med tilfeldige papirer som null.

    Hver maaned holdes papirene som har faatt innslag de siste h maanedene,
    likt vektet, mot snittet av hele universet samme maaned. Nullen beholder
    ALLE innslagsdatoene, men bytter hvert papir med et tilfeldig papir i
    universet som har kurs paa datoen. Da er klumpingen i tid noyaktig lik,
    og spoersmaalet blir: slaar de flaggede papirene tilfeldige papirer
    kjoept paa samme dager?

    To tidligere utkast ble forkastet etter simulering paa tilfeldige kurser,
    der riktig andel p under 0,05 er 5 %:
      mot papirets egne tilfeldige datoer        23 % (skjevt for b og a+b)
      kalenderportefolje med Newey-West-t          11-16 % for a (for faa
                                                   episoder til at t holder)
    Denne ga 4,2 %, se kommentaren i toppen."""
    cols = np.array([c in papirer for c in RET.columns])
    rader = [RIDX[e["t"]] for e in inn if e["t"] in RIDX]
    kol = [CIDX[e["tk"]] for e in inn if e["t"] in RIDX]
    obs, n = kal_stat(rader, kol, h, cols)
    if not np.isfinite(obs):
        return {"mer_aar": None, "p": None, "maaneder": 0}
    kandidater = {r: np.where(GYLDIG[r + 1] & cols)[0] if r + 1 < RV.shape[0] else np.array([], int)
                  for r in set(rader)}
    null = []
    for _ in range(TREKK):
        k2 = [rng.choice(kandidater[r]) if len(kandidater[r]) else c for r, c in zip(rader, kol)]
        v, _n = kal_stat(rader, k2, h, cols)
        if np.isfinite(v):
            null.append(v)
    null = np.array(null)
    return {"mer_aar": round(100 * 12 * obs, 1), "maaneder": n,
            "p": round(float(((null >= obs).sum() + 1) / (len(null) + 1)), 3),
            "null_aar": round(100 * 12 * float(np.median(null)), 1)}


def evaluer(variant, papirer):
    inn = []
    for tk in papirer:
        if tk not in SIG[variant]:
            continue
        s = KURS[tk]
        for t in innslag(SIG[variant][tk], tk):
            e = {"tk": tk, "t": t}
            for h in (12, 24):
                v = FWD[h][tk].get(t)
                e[f"r{h}"] = None if v is None or np.isnan(v) else float(v)
            e["fall"] = videre_fall(s, t)
            inn.append(e)
    if not inn:
        return None
    kl = klynger(inn)
    res = {"innslag": len(inn), "papirer": len({e["tk"] for e in inn}),
           "episoder": len(kl), "klynger": []}
    for k in kl:
        rs = [e["r24"] for e in k if e["r24"] is not None]
        res["klynger"].append({"fra": str(k[0]["t"]), "til": str(k[-1]["t"]), "n": len(k),
                               "r24": None if not rs else round(100 * (np.exp(np.median(rs)) - 1), 1)})
    res["episoder_pos"] = sum(1 for k in res["klynger"] if (k["r24"] or 0) > 0)
    for h in (12, 24):
        rr = [e[f"r{h}"] for e in inn if e[f"r{h}"] is not None]
        res[f"h{h}"] = {**kalendertest(inn, papirer, h),
                        "innslag_median_r": round(100 * (np.exp(np.median(rr)) - 1), 1) if rr else None,
                        "innslag_treff": round(100 * np.mean([x > 0 for x in rr]), 0) if rr else None}
    fall = [e["fall"] for e in inn if e["fall"] is not None]
    res["fall_median"] = round(100 * float(np.median(fall)), 1) if fall else None
    res["fall_over30"] = round(100 * float(np.mean([f < -0.30 for f in fall])), 0) if fall else None
    res["_innslag"] = [{**e, "t": str(e["t"])} for e in inn]
    return res


print("\n4. Resultater\n")
print("   mer/aar = kalenderportefoljen mot snittet av hele universet samme maaned,")
print("             annualisert log-avkastning i prosent. p: andelen av 1000 trekk med")
print("             tilfeldige papirer paa de samme datoene som gjorde det minst like godt")
print("   ep      = episoder (innslag med hoyst seks maaneder mellom) og hvor mange")
print("             av dem med positiv median realavkastning over 24 maaneder")
print("   r24     = median realavkastning 24 maaneder etter innslag, absolutt\n")
UTVIDET = set(KURS)
TAV = TAVLE & set(KURS)
UT = {}
fm = lambda v, f: "-" if v is None or (isinstance(v, float) and np.isnan(v)) else format(v, f)
for navn, papirer in [("TAVLE", TAV), ("UTVIDET", UTVIDET)]:
    print(f"   {navn}  ({len(papirer)} papirer)\n")
    print("   variant papirer innslag  ep pos | 24 mnd: mer/aar    p    | 12 mnd: mer/aar   p    |"
          "    r24   treff | videre fall  >30 %")
    for v in ("a", "b", "a+b", "c"):
        r = evaluer(v, papirer)
        UT.setdefault(navn, {})[v] = r
        if not r:
            print(f"   {v:5}   ingen innslag"); continue
        x24, x12 = r["h24"], r["h12"]
        print(f"   {v:5}   {r['papirer']:4}   {r['innslag']:4}   {r['episoder']:3} {r['episoder_pos']:3} | "
              f"{fm(x24['mer_aar'], '+8.1f')} %  {fm(x24['p'], '.3f')} | "
              f"{fm(x12['mer_aar'], '+8.1f')} %  {fm(x12['p'], '.3f')} | "
              f"{fm(x24['innslag_median_r'], '+6.1f')} %  {fm(x24['innslag_treff'], '3.0f')} % | "
              f"{fm(r['fall_median'], '+7.1f')} %  {fm(r['fall_over30'], '4.0f')} %")
    print()

print("   Episodene, UTVIDET (fra, til, innslag, median realavkastning 24 mnd):")
for v in ("a", "b", "a+b", "c"):
    r = UT["UTVIDET"].get(v)
    if not r:
        continue
    print(f"   {v}")
    for k in r["klynger"]:
        print(f"      {k['fra']} til {k['til']}  n={k['n']:3}  r24 {fm(k['r24'], '7.1f')} %")

# overlapp mellom a og b: hvor ofte fyrer papirets egen kurs samtidig med raavaren
ab = [(tk, int(SIG['a'][tk][(SIG['a'][tk].index >= FRA) & (SIG['a'][tk].index <= TIL)].sum()),
       int(SIG['a+b'][tk][(SIG['a+b'][tk].index >= FRA) & (SIG['a+b'][tk].index <= TIL)].sum()))
      for tk in SIG["a"]]
na, nab = sum(x[1] for x in ab), sum(x[2] for x in ab)
print(f"\n   Overlapp: av {na} maaneder med raavareflagg sto papiret selv i bunnsone i {nab} "
      f"({100 * nab / na if na else 0:.0f} %).")

os.makedirs("sonder", exist_ok=True)
with open("sonder/instrumenttest.json", "w", encoding="utf-8") as f:
    json.dump({"kjort": time.strftime("%Y-%m-%d %H:%M:%S"), "vindu": [str(FRA), str(TIL)],
               "resultat": UT, "papirer": sorted(KURS), "tavle": sorted(TAV),
               "bps": sorted(BPS)}, f, ensure_ascii=False, indent=1, default=str)
print("\n   lagret sonder/instrumenttest.json")
print("\nSend hele utskriften tilbake.")
