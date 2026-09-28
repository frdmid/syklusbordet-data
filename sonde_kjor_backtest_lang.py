# ---------------------------------------------------------------------------
# sonde_kjor_backtest_lang: bunnflagget testet bakover med lange proxyer
#
# Frodes beslutning 28.09.2026 (punkt 1 etter backtesten samme dag): rundt 40
# av 57 raavareflagg ligger foer papirene paa tavlen fikk kurser, saa de er
# aldri testet mot noe som kan kjoepes. Denne sonden tester dem mot
#
#   HOVED  Ken French sine 49 bransjeporteføljer (verdivektet totalavkastning
#          i dollar, fra 1926). Portefoljene inneholder ogsaa selskaper som
#          senere gikk konkurs eller ble kjoept opp, saa de har ikke den
#          overlevelsesskjevheten dagens kurslister har. Derfor er det dem
#          konklusjonen hviler paa.
#   STOETTE store, gamle enkeltaksjer fra Yahoo (Exxon, Newmont, Freeport,
#          Alcoa osv.). De har overlevelsesskjevhet og vises bare ved siden av.
#
# KARTET, satt foer kjoering og ikke endret etter:
#   olje (brent, wti, henryhub, ttf)   Oil     XOM CVX COP OXY (+ EQT for gass)
#   gull                               Gold    NEM AEM HL
#   kobber                             Mines   FCX SCCO TECK
#   nikkel                             Mines   BHP VALE
#   aluminium                          Steel   AA CENX   (SIC 3334 ligger i Steel)
#   sink, bly                          Mines   TECK
#   tinn                               Mines
#   jernmalm                           Mines, Steel   RIO BHP CLF VALE
#   kull                               Coal    ARLP
#   uran                               Mines   CCJ
#   Kakao og palmeolje er utelatt: ingen bransje eller aksje med lang
#   historikk er begrunnet paa forhaand som kjoeper av en bunn i dem.
#
# SAMME REGNESTYKKE SOM sonde_kjor_backtest
#   Bunnsone (raa og detrendet A >= 80), innslag etter mer enn tolv maaneder
#   uten, inngang ved slutten av flaggmaaneden. Horisont 1, 2, 3, 6, 12 og 24
#   maaneder. "mer" = mot proxyens eget snitt over alle maaneder. "marked" =
#   mot hele det amerikanske aksjemarkedet (Mkt-RF + RF). Episoder med hoeyst
#   seks maaneder mellom. S = snitt over episoder av episodens median. p fra
#   2000 trekk der hver episode flyttes til en tilfeldig kalendermaaned.
#   Samme proxy flagget av to raavarer samme maaned (Brent og WTI paa Oil)
#   telles en gang.
#
# DET SOM AVGJOER, satt foer kjoering
#   Flaggregelen ble valgt paa data fra 2011 til 2026. Innslag FOER 2011-09 er
#   derfor utenfor utvalget for selve regelen, og det er den delen som er den
#   egentlige testen. Holder bransjeporteføljene S > 0 og flertall positive
#   episoder ved 12 og 24 maaneder foer 2011, styrker det modellen. Gjoer de
#   ikke det, hviler modellen paa 2011 til 2026 alene.
#
# FORBEHOLD
#   Proxyene er amerikanske. De tester om flagget virker, ikke om akkurat
#   papirene paa tavlen virker. Bransjene er brede (Mines er mer enn kobber).
# ---------------------------------------------------------------------------

import io, json, os, time, warnings, zipfile
import numpy as np
import pandas as pd
import requests
import terskel_motor as M

warnings.filterwarnings("ignore")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
HORISONTER = (1, 2, 3, 6, 12, 24)
KLYNGEGAP, PAUSE, TREKK = 6, M.PAUSE, 2000
SPLITT = pd.Period("2011-09", "M")
NAA = pd.Period(pd.Timestamp.utcnow().strftime("%Y-%m"), "M")
rng = np.random.default_rng(20260928)
FRENCH = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"

OLJE = ["XOM", "CVX", "COP", "OXY"]
KART = {
    "brent":     (["Oil"], OLJE),
    "wti":       (["Oil"], OLJE),
    "henryhub":  (["Oil"], OLJE + ["EQT"]),
    "ttf":       (["Oil"], OLJE),
    "gold":      (["Gold"], ["NEM", "AEM", "HL"]),
    "kobber":    (["Mines"], ["FCX", "SCCO", "TECK"]),
    "nikkel":    (["Mines"], ["BHP", "VALE"]),
    "aluminium": (["Steel"], ["AA", "CENX"]),
    "sink":      (["Mines"], ["TECK"]),
    "bly":       (["Mines"], ["TECK"]),
    "tinn":      (["Mines"], []),
    "jernmalm":  (["Mines", "Steel"], ["RIO", "BHP", "CLF", "VALE"]),
    "kull":      (["Coal"], ["ARLP"]),
    "uran":      (["Mines"], ["CCJ"]),
}

FX = {"USD": None, "EUR": ("EURUSD=X", False), "GBP": ("GBPUSD=X", False), "GBp": ("GBPUSD=X", False),
      "NOK": ("NOK=X", True), "SEK": ("SEK=X", True), "CAD": ("CAD=X", True), "CHF": ("CHF=X", True),
      "DKK": ("DKK=X", True), "AUD": ("AUDUSD=X", False)}


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
    raise RuntimeError(url)


_fx = {}
def yahoo(sym, justert=True, valutakurs=False):
    """Som i sonde_kjor_backtest: maanedskurs i dollar, justert for utbytte."""
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


def french(fil, blokk):
    """Leser foerste maanedsblokk som inneholder teksten blokk (eller den
    foerste datablokken hvis blokk er None). Returnerer DataFrame med
    maanedlige avkastninger i prosent, -99.99 som manglende."""
    z = zipfile.ZipFile(io.BytesIO(get(FRENCH + fil, timeout=90).content))
    tekst = z.read(z.namelist()[0]).decode("latin1").splitlines()
    start = 0
    if blokk:
        start = next(i for i, l in enumerate(tekst) if blokk in l)
    i = start
    while not (tekst[i].strip().startswith(",") and len(tekst[i].split(",")) > 2):
        i += 1
    kol = [c.strip() for c in tekst[i].split(",")[1:]]
    rader = {}
    for l in tekst[i + 1:]:
        f = [x.strip() for x in l.split(",")]
        if not f[0].isdigit() or len(f[0]) != 6:
            break
        rader[pd.Period(f"{f[0][:4]}-{f[0][4:]}", "M")] = [float(x) for x in f[1:len(kol) + 1]]
    d = pd.DataFrame.from_dict(rader, orient="index", columns=kol).sort_index()
    return d.where(d > -99.0)


def nivaa(r_pst):
    """Log-indeks fra maanedlige avkastninger i prosent. Verdien i maaned t er
    nivaaet ved slutten av maaned t."""
    r = r_pst.dropna()
    return np.log1p(r / 100.0).cumsum()


# ===================================================================== data
print("0. Raavarene fra bordets egen kode\n")
from raavare_hist import hent
REAL, _NOM, cpi = hent()
LR, BUNN = {}, {}
for sid, lr in REAL.items():
    if sid not in KART:
        continue
    lr = lr.dropna()
    full = pd.period_range(lr.index[0], lr.index[-1], freq="M")
    lr = lr.reindex(full).interpolate()
    s = M.Segment(sid, lr.values, np.array([p.ordinal for p in lr.index]))
    ok = np.isfinite(s.A) & np.isfinite(s.Ad)
    LR[sid] = lr
    BUNN[sid] = pd.Series(ok & (s.A >= 80) & (s.Ad >= 80), index=lr.index)


def innslag(fl):
    ut, siste = [], None
    for t in fl.index[fl.values]:
        if siste is None or t.ordinal - siste.ordinal > PAUSE:
            ut.append(t)
        siste = t
    return ut


INNSLAG = {sid: innslag(b) for sid, b in BUNN.items()}
print("\n   Innslag i bunnsone:")
for sid in sorted(INNSLAG):
    print(f"      {sid:10} {len(INNSLAG[sid]):2d}  " + " ".join(str(t) for t in INNSLAG[sid]))

print("\n1. Ken French\n")
IND = french("49_Industry_Portfolios_CSV.zip", "Value Weighted Returns -- Monthly")
FAK = french("F-F_Research_Data_Factors_CSV.zip", None)
KURS = {}
for b in sorted({x for v in KART.values() for x in v[0]}):
    KURS[f"ff:{b}"] = nivaa(IND[b])
    print(f"   {b:6} fra {KURS['ff:' + b].index[0]} til {KURS['ff:' + b].index[-1]}")
MARKED = nivaa(FAK["Mkt-RF"] + FAK["RF"])
print(f"   marked fra {MARKED.index[0]} til {MARKED.index[-1]}")

print("\n2. Enkeltaksjer (stoette, med overlevelsesskjevhet)\n")
for tk in sorted({x for v in KART.values() for x in v[1]}):
    try:
        s = yahoo(tk)
        if len(s) >= 24:
            KURS[tk] = np.log(s)
            print(f"   {tk:5} fra {s.index[0]}")
    except Exception as e:
        print(f"   {tk:5} {type(e).__name__}: {str(e)[:60]}")
    time.sleep(0.25)


# ================================================================ regnestykket
def fram_p(lk, h):
    ut = {}
    for t, v in lk.items():
        e = t + h
        if e in lk.index:
            ut[t] = lk[e] - v
    return pd.Series(ut, dtype=float)


FWD = {h: {tk: fram_p(lk, h) for tk, lk in KURS.items()} for h in HORISONTER}
SNITT = {h: {tk: float(f.mean()) for tk, f in FWD[h].items() if len(f)} for h in HORISONTER}
FWD_M = {h: fram_p(MARKED, h) for h in HORISONTER}
FWD_R = {h: {sid: fram_p(lr, h) for sid, lr in LR.items()} for h in HORISONTER}


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


def utfall(hend, h):
    rader = []
    for t, tk, sid in hend:
        f = FWD[h].get(tk)
        if f is None or t not in f.index:
            continue
        r = float(f[t])
        m = float(FWD_M[h][t]) if t in FWD_M[h].index else np.nan
        rader.append({"t": t, "tk": tk, "sid": sid, "abs": r, "mer": r - SNITT[h][tk],
                      "marked": r - m if np.isfinite(m) else np.nan,
                      "raavare": float(FWD_R[h][sid].get(t, np.nan))})
    return rader


def null_S(rader, h):
    kl = klynger([r["t"] for r in rader])
    ep = {}
    for r, c in zip(rader, kl):
        ep.setdefault(c, []).append(r["tk"])
    alle = sorted({p for f in FWD[h].values() for p in f.index})
    d = {tk: {p: float(x) - SNITT[h][tk] for p, x in FWD[h][tk].items()}
         for tk in {t for v in ep.values() for t in v}}
    kand = []
    for tks in ep.values():
        med = []
        for m in alle:
            v = [d[tk][m] for tk in tks if m in d[tk]]
            if v and len(v) * 2 >= len(tks):
                med.append(float(np.median(v)))
        if med:
            kand.append(np.array(med))
    if not kand:
        return np.array([])
    return np.column_stack([k[rng.integers(len(k), size=TREKK)] for k in kand]).mean(axis=1)


pst = lambda v: "     -  " if v is None or not np.isfinite(v) else f"{100 * (np.exp(v) - 1):+7.1f} %"


def oppsummer(rader, h):
    if not rader:
        return None
    kl = klynger([r["t"] for r in rader])
    a = np.array([r["abs"] for r in rader]); m = np.array([r["mer"] for r in rader])
    w = np.array([r["marked"] for r in rader]); rv = np.array([r["raavare"] for r in rader])
    S, pos, n_ep = S_av(m, kl)
    Sw, posw, _ = S_av(w, kl)
    nu = null_S(rader, h)
    p = float(((nu >= S).sum() + 1) / (len(nu) + 1)) if len(nu) and np.isfinite(S) else np.nan
    fin = lambda x: x[np.isfinite(x)]
    return {"h": h, "innslag": len(rader), "episoder": n_ep,
            "abs_median": float(np.median(a)), "abs_treff": float(np.mean(a > 0)),
            "mer_median": float(np.median(m)), "mer_treff": float(np.mean(m > 0)),
            "S": S, "S_pos": pos, "p": p,
            "marked_median": float(np.median(fin(w))) if len(fin(w)) else np.nan,
            "S_marked": Sw, "S_marked_pos": posw,
            "raavare_median": float(np.median(fin(rv))) if len(fin(rv)) else np.nan}


def tabell(tittel, hend):
    print(f"\n   {tittel}")
    print("   h    innsl ep | abs: median treff | mot eget snitt: median |   S      ep+    p    "
          "| mot marked: median   S     ep+ | raavare")
    ut = {}
    for h in HORISONTER:
        o = oppsummer(utfall(hend, h), h)
        ut[h] = o
        if o is None:
            print(f"   {h:2d}   ingen"); continue
        print(f"   {h:2d}   {o['innslag']:4d} {o['episoder']:3d} | {pst(o['abs_median'])} {100 * o['abs_treff']:4.0f} % | "
              f"{pst(o['mer_median'])}      | {pst(o['S'])} {o['S_pos']:2d}/{o['episoder']:<2d} "
              f"{'  -  ' if not np.isfinite(o['p']) else format(o['p'], '.3f')} | "
              f"{pst(o['marked_median'])} {pst(o['S_marked'])} {o['S_marked_pos']:2d} | {pst(o['raavare_median'])}",
              flush=True)
    return ut


def hendelser(kilde):
    """kilde 0 = bransjer, 1 = aksjer. En proxy telles en gang per maaned."""
    ut, sett = [], set()
    for sid, t_liste in INNSLAG.items():
        for t in t_liste:
            for p in KART[sid][kilde]:
                tk = f"ff:{p}" if kilde == 0 else p
                if tk in KURS and (t, tk) not in sett:
                    sett.add((t, tk)); ut.append((t, tk, sid))
    return ut


print("\n\n3. BRANSJEPORTEFOLJENE (hovedtesten, uten overlevelsesskjevhet)")
print("   mer = mot bransjens eget snitt. marked = mot hele det amerikanske aksjemarkedet.")
HF = hendelser(0)
RES = {"ff_alle": tabell("Alle innslag", HF),
       "ff_foer2011": tabell("Foer 2011-09: utenfor perioden flaggregelen ble valgt paa (AVGJOER)",
                             [x for x in HF if x[0] < SPLITT]),
       "ff_fra2011": tabell("Fra 2011-09: inne i perioden regelen ble valgt paa",
                            [x for x in HF if x[0] >= SPLITT])}

print("\n   Hvert innslag (abs, dollar):")
print("      segment    innslag  bransje " + "".join(f"{h:>8d} mnd" for h in HORISONTER) + "   raavare 12 mnd")
LISTE = []
for t, tk, sid in sorted(HF, key=lambda x: (x[0], x[2])):
    v = {h: (float(FWD[h][tk][t]) if t in FWD[h][tk].index else np.nan) for h in HORISONTER}
    LISTE.append({"sid": sid, "t": str(t), "proxy": tk, **{f"h{h}": v[h] for h in HORISONTER}})
    print(f"      {sid:10} {str(t):8} {tk[3:]:6}" + "".join(f"{pst(v[h]):>12}" for h in HORISONTER)
          + f"   {pst(FWD_R[12][sid].get(t, np.nan))}")

print("\n   Per bransje, 12 og 24 mnd (median mot eget snitt, positive av innslag):")
PER = {}
for b in sorted({tk for _, tk, _ in HF}):
    tekst = []
    for h in (12, 24):
        r = utfall([x for x in HF if x[1] == b], h)
        if r:
            mm = [x["mer"] for x in r]
            PER.setdefault(b, {})[h] = {"n": len(r), "mer_median": float(np.median(mm)),
                                        "pos": int(sum(x > 0 for x in mm))}
            tekst.append(f"{h:2d} mnd {pst(np.median(mm))} ({sum(x > 0 for x in mm)}/{len(r)})")
    print(f"      {b[3:]:6} " + "   ".join(tekst))

print("\n\n4. ENKELTAKSJENE (stoette, overlevere, trekker opp)")
HA = hendelser(1)
RES["aksjer_alle"] = tabell("Alle innslag", HA)
RES["aksjer_foer2011"] = tabell("Foer 2011-09", [x for x in HA if x[0] < SPLITT])

print("\n\n5. Beslutning etter regelen satt foer kjoering")
fo = RES["ff_foer2011"]
ok = {h: (fo.get(h) is not None and np.isfinite(fo[h]["S"]) and fo[h]["S"] > 0
          and fo[h]["S_pos"] * 2 > fo[h]["episoder"]) for h in (12, 24)}
for h in (12, 24):
    o = fo.get(h)
    if o:
        print(f"   {h} mnd foer 2011: S {pst(o['S'])}, {o['S_pos']} av {o['episoder']} episoder positive, "
              f"p {o['p']:.3f}  ->  {'bestaar' if ok[h] else 'bestaar ikke'}")
print("   " + ("Flagget holder utenfor perioden det ble valgt paa. Det styrker modellen."
             if all(ok.values()) else
             "Flagget holder ikke utenfor perioden det ble valgt paa. Modellen hviler paa 2011 til 2026."))

os.makedirs("sonder", exist_ok=True)


def rens(x):
    if isinstance(x, dict):
        return {str(k): rens(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [rens(v) for v in x]
    if isinstance(x, (float, np.floating)):
        return None if not np.isfinite(x) else round(float(x), 5)
    if isinstance(x, np.integer):
        return int(x)
    if isinstance(x, pd.Period):
        return str(x)
    return x


json.dump(rens({"kjort": time.strftime("%Y-%m-%d %H:%M:%S"), "kart": KART, "resultat": RES,
                "innslag": LISTE, "per_bransje": PER, "bestaar": ok}),
          open("sonder/backtest_lang.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("\n   lagret sonder/backtest_lang.json")
