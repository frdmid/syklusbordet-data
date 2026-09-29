# ---------------------------------------------------------------------------
# sonde_kjor_faktor: er avkastningen etter bunnflagget bare kjente faktorer?
#
# Frodes beslutning 29.09.2026 (punkt 3). Flagget kjoeper raavareaksjer som
# har falt i flere aar. Det ligner paa verdifaktoren (billig paa bok) og
# langsiktig reversering (kjoep fem aars taperne), og 2009 og 2020 var aar da
# nettopp slike aksjer steg mest i hele markedet. Sonden sjekker om det
# positive resultatet fra 2011 til 2026 blir borte naar det justeres for dette.
#
# DATA
#   Papirene paa tavlen (instrumenter.py, vanlig retning), totalavkastning i
#   dollar fra Yahoo, mot Ken French sine faktorer for utviklede markeder
#   (Developed 5 faktorer og Developed momentum, fra 1990-07).
#   Ken French sine bransjeporteføljer (samme kart som sonde_kjor_backtest_lang)
#   mot de amerikanske faktorene (5 faktorer og momentum fra 1963-07, pluss
#   langsiktig reversering).
#
# MODELLER
#   raa     papirets meravkastning mot risikofri rente, minus eget snitt
#   CAPM    residual etter markedet
#   FF5+M   residual etter marked, stoerrelse, verdi, loennsomhet, investering
#           og momentum
#   +LTR    (bare bransjene) i tillegg langsiktig reversering
#   Betaene estimeres per papir paa alle maaneder UTENFOR 24 maaneder etter
#   hvert innslag, saa hendelsene ikke farger sin egen normal. Residualen
#   inkluderer ikke konstantleddet, samme logikk som "mot eget snitt".
#   Utfall: sum av maanedlige residualer over 3, 6, 12 og 24 maaneder etter
#   innslaget. Episoder, S og p som i de andre backtestene.
#
# LESING, satt foer kjoering
#   For papirene paa tavlen ved 12 maaneder: er S etter FF5+M hoeyst en
#   tredel av raa S, eller negativ, er resultatet i hovedsak forklart av
#   faktorene. Ellers har flagget noe eget. Faktorbidragene (beta ganger
#   faktoravkastning i vinduet) vises, saa det synes hvilken faktor som bar.
# ---------------------------------------------------------------------------

import io, json, os, time, warnings, zipfile
import numpy as np
import pandas as pd
import requests
import terskel_motor as M
from instrumenter import INSTR

warnings.filterwarnings("ignore")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
HORISONTER = (3, 6, 12, 24)
KLYNGEGAP, PAUSE, TREKK, VINDU = 6, M.PAUSE, 2000, 24
SPLITT = pd.Period("2011-09", "M")
NAA = pd.Period(pd.Timestamp.utcnow().strftime("%Y-%m"), "M")
rng = np.random.default_rng(20260929)
FRENCH = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
OLJE = ["Oil"]
BRANSJE = {"brent": ["Oil"], "wti": ["Oil"], "henryhub": ["Oil"], "ttf": ["Oil"], "gold": ["Gold"],
           "kobber": ["Mines"], "nikkel": ["Mines"], "aluminium": ["Steel"], "sink": ["Mines"],
           "bly": ["Mines"], "tinn": ["Mines"], "jernmalm": ["Mines", "Steel"], "kull": ["Coal"],
           "uran": ["Mines"]}
FX = {"USD": None, "EUR": ("EURUSD=X", False), "GBP": ("GBPUSD=X", False), "GBp": ("GBPUSD=X", False),
      "NOK": ("NOK=X", True), "SEK": ("SEK=X", True), "CAD": ("CAD=X", True), "CHF": ("CHF=X", True),
      "DKK": ("DKK=X", True), "AUD": ("AUDUSD=X", False)}


def get(url, timeout=90):
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
    raise RuntimeError(url)


_fx = {}
def yahoo(sym, justert=True, valutakurs=False):
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
    if valutakurs:
        return s
    val = meta.get("currency") or "USD"
    if val not in FX:
        raise ValueError(f"valuta {val}")
    if FX[val]:
        fs, inv = FX[val]
        if fs not in _fx:
            f = yahoo(fs, justert=False, valutakurs=True)
            _fx[fs] = (1.0 / f) if inv else f
        s = (s * _fx[fs].reindex(s.index).ffill()).dropna()
    if val == "GBp":
        s = s / 100.0
    return s[s.index < NAA]


def french(fil, blokk=None):
    z = zipfile.ZipFile(io.BytesIO(get(FRENCH + fil).content))
    tekst = z.read(z.namelist()[0]).decode("latin1").splitlines()
    i = next(k for k, l in enumerate(tekst) if blokk in l) if blokk else 0
    while not (tekst[i].strip().startswith(",") and len(tekst[i].split(",")) > 1):
        i += 1
    kol = [c.strip() for c in tekst[i].split(",")[1:]]
    rader = {}
    for l in tekst[i + 1:]:
        f = [x.strip() for x in l.split(",")]
        if not f[0].isdigit() or len(f[0]) != 6:
            break
        try:
            rader[pd.Period(f"{f[0][:4]}-{f[0][4:]}", "M")] = [float(x) for x in f[1:len(kol) + 1]]
        except ValueError:
            continue
    d = pd.DataFrame.from_dict(rader, orient="index", columns=kol).sort_index()
    return d.where(d > -99.0)


# ===================================================================== data
print("0. Raavarene fra bordets egen kode\n")
from raavare_hist import hent
REAL, _NOM, cpi = hent()
INNSLAG = {}
for sid, lr in REAL.items():
    lr = lr.dropna()
    lr = lr.reindex(pd.period_range(lr.index[0], lr.index[-1], freq="M")).interpolate()
    s = M.Segment(sid, lr.values, np.array([p.ordinal for p in lr.index]))
    fl = pd.Series(np.isfinite(s.A) & np.isfinite(s.Ad) & (s.A >= 80) & (s.Ad >= 80), index=lr.index)
    ut, siste = [], None
    for t in fl.index[fl.values]:
        if siste is None or t.ordinal - siste.ordinal > PAUSE:
            ut.append(t)
        siste = t
    INNSLAG[sid] = ut

print("\n1. Faktorene\n")
US = french("F-F_Research_Data_5_Factors_2x3_CSV.zip")
US["Mom"] = french("F-F_Momentum_Factor_CSV.zip").iloc[:, 0]
US["LTR"] = french("F-F_LT_Reversal_Factor_CSV.zip").iloc[:, 0]
DEV = french("Developed_5_Factors_CSV.zip")
DEV["Mom"] = french("Developed_Mom_Factor_CSV.zip").iloc[:, 0]
US, DEV = US.dropna(), DEV.dropna()
print(f"   USA:       {list(US.columns)}  {US.index[0]} til {US.index[-1]}")
print(f"   Utviklede: {list(DEV.columns)}  {DEV.index[0]} til {DEV.index[-1]}")
IND = french("49_Industry_Portfolios_CSV.zip", "Value Weighted Returns -- Monthly")

print("\n2. Avkastninger (prosent per maaned, dollar)\n")
R = {}
for b in sorted({x for v in BRANSJE.values() for x in v}):
    R[f"ff:{b}"] = IND[b].dropna()
PAPIR = {}
for sid, rader in INSTR.items():
    for tk, bors, navn, typ, kom in rader:
        if not kom.strip().startswith("-") and sid in INNSLAG:
            PAPIR.setdefault(tk, []).append(sid)
for tk in sorted(PAPIR):
    try:
        s = yahoo(tk)
        if len(s) >= 72:
            R[tk] = (s.pct_change() * 100).dropna()
    except Exception as e:
        print(f"   {tk}: {type(e).__name__}: {str(e)[:50]}")
    time.sleep(0.25)
print(f"   {sum(1 for k in R if not k.startswith('ff:'))} papirer, {sum(1 for k in R if k.startswith('ff:'))} bransjer")


# ================================================================ modellene
MODELLER = {"raa": [], "CAPM": ["Mkt-RF"], "FF5+M": ["Mkt-RF", "SMB", "HML", "RMW", "CMA", "Mom"],
            "+LTR": ["Mkt-RF", "SMB", "HML", "RMW", "CMA", "Mom", "LTR"]}


def residualer(aktiva, F, hend_datoer):
    """For ett aktivum: dict modell -> (residualserie, betaer, bidragsserier)."""
    r = R[aktiva]
    i = r.index.intersection(F.index)
    y = r[i] - F.loc[i, "RF"]
    ute = pd.Series(True, index=i)
    for t in hend_datoer:
        ute &= ~((i >= t) & (i <= t + VINDU))
    ut = {}
    for navn, kol in MODELLER.items():
        if any(k not in F.columns for k in kol):
            continue
        if not kol:
            ut[navn] = (y - y[ute].mean(), {}, {})
            continue
        X = F.loc[i, kol]
        Xe = np.column_stack([np.ones(int(ute.sum())), X[ute].values])
        if ute.sum() < 60:
            continue
        b = np.linalg.lstsq(Xe, y[ute].values, rcond=None)[0]
        bidrag = {k: X[k] * b[j + 1] for j, k in enumerate(kol)}
        ut[navn] = (y - b[0] - X.values @ b[1:], dict(zip(kol, np.round(b[1:], 2))), bidrag)
    return ut


def sum_fram(s, h):
    """Sum av maanedene t+1 .. t+h, per t."""
    v = s.rolling(h).sum().shift(-h)
    return v.dropna()


def klynger(datoer):
    o = np.array([d.ordinal for d in datoer])
    rek = np.argsort(o, kind="stable")
    kl = np.zeros(len(o), int)
    c, sist = 0, None
    for i in rek:
        if sist is not None and o[i] - sist > KLYNGEGAP:
            c += 1
        kl[i] = c; sist = o[i]
    return kl


def S_av(v, kl):
    v = np.asarray(v, float)
    ok = np.isfinite(v)
    if not ok.any():
        return np.nan, 0, 0
    med = np.array([np.median(v[ok & (kl == c)]) for c in np.unique(kl[ok])])
    return float(med.mean()), int((med > 0).sum()), len(med)


def null_S(rader, fram):
    kl = klynger([r[0] for r in rader])
    ep = {}
    for (t, a), c in zip(rader, kl):
        ep.setdefault(c, []).append(a)
    alle = sorted({p for f in fram.values() for p in f.index})
    d = {a: fram[a].to_dict() for a in {a for _, a in rader}}
    kand = []
    for aa in ep.values():
        med = [float(np.median([d[a][m] for a in aa if m in d[a]])) for m in alle
               if sum(m in d[a] for a in aa) * 2 >= len(aa)]
        if med:
            kand.append(np.array(med))
    if not kand:
        return np.array([])
    return np.column_stack([k[rng.integers(len(k), size=TREKK)] for k in kand]).mean(axis=1)


def kjor(tittel, hend, F, modeller):
    """hend: liste av (t, aktivum). Skriver tabell og returnerer resultat."""
    print(f"\n   {tittel}")
    datoer = {}
    for t, a in hend:
        datoer.setdefault(a, []).append(t)
    RES = {a: residualer(a, F, datoer[a]) for a in datoer if a in R}
    ut = {}
    print("   modell    h   innsl ep |   S       ep+    p    | median")
    for navn in modeller:
        for h in HORISONTER:
            fram = {a: sum_fram(RES[a][navn][0], h) for a in RES if navn in RES[a]}
            rader = [(t, a) for t, a in hend if a in fram and t in fram[a].index]
            if not rader:
                continue
            v = [float(fram[a][t]) for t, a in rader]
            kl = klynger([t for t, _ in rader])
            S, pos, n = S_av(v, kl)
            nu = null_S(rader, fram)
            p = float(((nu >= S).sum() + 1) / (len(nu) + 1)) if len(nu) and np.isfinite(S) else np.nan
            ut[(navn, h)] = {"innslag": len(rader), "episoder": n, "S": S, "S_pos": pos, "p": p,
                             "median": float(np.median(v))}
            print(f"   {navn:7} {h:3d}   {len(rader):4d} {n:3d} | {S:+7.1f} %  {pos:2d}/{n:<2d} "
                  f"{'  -  ' if not np.isfinite(p) else format(p, '.3f')} | {np.median(v):+7.1f} %", flush=True)
    # Hvilke faktorer bar: median bidrag over 12 mnd i den fulle modellen
    full = modeller[-1]
    bid = {}
    for t, a in hend:
        if a not in RES or full not in RES[a]:
            continue
        for k, s in RES[a][full][2].items():
            f = sum_fram(s, 12)
            if t in f.index:
                bid.setdefault(k, []).append(float(f[t]))
    if bid:
        print(f"   Faktorbidrag over 12 mnd i {full}, median over innslag (prosentpoeng): "
              + ", ".join(f"{k} {np.median(v):+.1f}" for k, v in bid.items()))
    betaer = {a: RES[a][full][1] for a in RES if full in RES[a]}
    return {"tabell": {f"{m}_{h}": v for (m, h), v in ut.items()},
            "bidrag12": {k: float(np.median(v)) for k, v in bid.items()}, "betaer": betaer}


print("\n\n3. PAPIRENE PAA TAVLEN, mot faktorer for utviklede markeder")
print("   S = snitt over episoder av episodens median, sum av maanedlige residualer i prosent.")
HP = sorted({(t, tk) for tk, segs in PAPIR.items() if tk in R for sid in segs for t in INNSLAG[sid]
             if t >= DEV.index[0]})
UT = {"papirer": kjor("Alle innslag", HP, DEV, ["raa", "CAPM", "FF5+M"]),
      "papirer_fra2011": kjor("Fra 2011-09", [x for x in HP if x[0] >= SPLITT], DEV, ["raa", "CAPM", "FF5+M"])}

print("\n\n4. BRANSJEPORTEFOLJENE, mot amerikanske faktorer")
HB = sorted({(t, f"ff:{b}") for sid, bs in BRANSJE.items() for b in bs for t in INNSLAG.get(sid, [])
             if t >= US.index[0]})
UT["bransjer"] = kjor("Alle innslag fra 1963", HB, US, ["raa", "CAPM", "FF5+M", "+LTR"])
UT["bransjer_foer2011"] = kjor("Foer 2011-09", [x for x in HB if x[0] < SPLITT], US, ["raa", "CAPM", "FF5+M", "+LTR"])
UT["bransjer_fra2011"] = kjor("Fra 2011-09", [x for x in HB if x[0] >= SPLITT], US, ["raa", "CAPM", "FF5+M", "+LTR"])

print("\n\n5. Lesing etter regelen satt foer kjoering (papirene, 12 mnd)")
t = UT["papirer"]["tabell"]
raa, ff = t.get("raa_12", {}).get("S", np.nan), t.get("FF5+M_12", {}).get("S", np.nan)
if np.isfinite(raa) and np.isfinite(ff):
    forklart = ff <= 0 or (raa > 0 and ff <= raa / 3)
    print(f"   raa S {raa:+.1f} %, etter FF5+M {ff:+.1f} %  ->  "
          + ("i hovedsak forklart av faktorene" if forklart else "flagget har noe eget utover faktorene"))
    UT["lesing"] = {"raa_S12": raa, "ff5m_S12": ff, "forklart": bool(forklart)}


def rens(x):
    if isinstance(x, dict):
        return {str(k): rens(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [rens(v) for v in x]
    if isinstance(x, (float, np.floating)):
        return None if not np.isfinite(x) else round(float(x), 4)
    if isinstance(x, (np.integer, np.bool_)):
        return x.item()
    return x


os.makedirs("sonder", exist_ok=True)
json.dump(rens({"kjort": time.strftime("%Y-%m-%d %H:%M:%S"), **UT}),
          open("sonder/faktor.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("\n   lagret sonder/faktor.json")
