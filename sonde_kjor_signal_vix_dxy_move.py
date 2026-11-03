# ---------------------------------------------------------------------------
# sonde_kjor_signal_vix_dxy_move: gir bunnsonen ulik avkastning etter nivået
# paa VIX, dollaren (DXY) og renteuroen (MOVE) naar signalet kommer? (Frodes
# bestilling 03.11.2026)
#
# Signal: Championens bunnsone, A raa >= 80 og A detrendet >= 80 i maaned t
#   (realpris fra serier/priser_mnd.csv, punkt i tid), alle 18 raavarer.
# Utfall: endring i log realpris for raavaren de neste h maanedene (6, 12, 24).
# Nivaa: maanedssnitt av ^VIX (fra 1990), DX-Y.NYB (fra 1985) og ^MOVE (fra
#   2002), alle fra Yahoo. Hver maaned plasseres i nederste, midterste eller
#   oeverste tredjedel mot det som var kjent da (minst 36 mnd).
# Test per maal og horisont: snitt i signalmaaneder i oeverste tredjedel minus
#   snitt i nederste tredjedel.
#
# KRITERIER (satt foer kjoering, 03.11.2026). Nivaaet betyr noe hvis:
#   (a) |forskjellen| er minst 5 prosentpoeng per 12 mnd (2,5 per 6, 10 per 24),
#   (b) p under 0,05 tosidig mot sirkulaert forskjoevet nivaaserie (minst 24
#       mnd, 2000 trekk),
#   (c) samme fortegn i begge halvdelene av perioden,
#   (d) minst 3 episoder (ny etter 12 mnd uten signal) i hver av de to
#       tredjedelene, og
#   (e) Benjamini-Hochberg paa 10 % over VIX og DXY x 3 horisonter.
#   VIX og DXY avgjoeres paa oppstart til 2014 (VIX 1993, DXY 1974; Yahoo hadde
#   DXY fra 1971, ikke 1988 som antatt foer kjoering). MOVE har
#   bare data fra 2002 og vises over hele perioden, avgjoer ikke. 2015 til
#   2026 vises for alle.
# I tillegg, beskrivende: de 13 posisjonene i papirporteføljen (handel.json)
#   med nivaaene ved inngang og papirenes avkastning mot MSCI World.
# Skriver ingenting til dashbordet. Utdata sonder/signal_vix_dxy_move.csv.
# ---------------------------------------------------------------------------

import json, time
import numpy as np
import pandas as pd
import requests

rng = np.random.default_rng(20261103)
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0 Safari/537.36"}
MIN_HIST = 60
TIL = pd.Period("2014-12", "M")
NYTT = (pd.Period("2015-01", "M"), pd.Period("2026-12", "M"))
MAAL = {"VIX": "^VIX", "DXY": "DX-Y.NYB", "MOVE": "^MOVE"}


def expanding_pct(v):
    out = np.full(len(v), np.nan)
    for i in range(MIN_HIST - 1, len(v)):
        out[i] = (v[: i + 1] <= v[i]).sum() / (i + 1)
    return (1 - out) * 100


def expanding_pct_detrend(v):
    out = np.full(len(v), np.nan)
    for i in range(MIN_HIST - 1, len(v)):
        y = v[: i + 1]; t = np.arange(i + 1)
        b, a = np.polyfit(t, y, 1); r = y - (a + b * t)
        out[i] = (r <= r[i]).sum() / len(r)
    return (1 - out) * 100


def tredjedel(s, minn=36):
    v = s.values; ut = np.full(len(v), np.nan)
    for i in range(len(v)):
        h = v[: i + 1]; h = h[np.isfinite(h)]
        if np.isfinite(v[i]) and len(h) >= minn:
            q = (h <= v[i]).mean()
            ut[i] = 0 if q <= 1 / 3 else (2 if q > 2 / 3 else 1)
    return pd.Series(ut, index=s.index)


def yahoo(sym):
    r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}",
                     params={"period1": 0, "period2": int(time.time()), "interval": "1d"}, headers=UA, timeout=60)
    res = r.json()["chart"]["result"][0]
    s = pd.Series(res["indicators"]["quote"][0]["close"], index=pd.to_datetime(res["timestamp"], unit="s")).dropna()
    s = s.resample("ME").mean(); s.index = s.index.to_period("M")
    time.sleep(0.3)
    return s


p = pd.read_csv("serier/priser_mnd.csv"); p = p[~p.segment.str.startswith("ship_")]
real = p.pivot(index="t", columns="segment", values="real").astype(float).sort_index()
real.index = pd.PeriodIndex(real.index, freq="M")
lr = np.log(real)
A = pd.DataFrame(np.nan, index=lr.index, columns=lr.columns); Ad = A.copy()
for c in lr.columns:
    s = lr[c].dropna()
    A.loc[s.index, c] = expanding_pct(s.values); Ad.loc[s.index, c] = expanding_pct_detrend(s.values)
SIG = ((A >= 80) & (Ad >= 80)).values

nivaa, tred = {}, {}
for n, sym in MAAL.items():
    nivaa[n] = yahoo(sym)
    tred[n] = tredjedel(nivaa[n]).reindex(lr.index)
    print(f"{n}: {nivaa[n].index[0]} til {nivaa[n].index[-1]}, siste {nivaa[n].iloc[-1]:.1f}, "
          f"tredjedel naa {['nederste', 'midterste', 'oeverste'][int(tred[n].dropna().iloc[-1])]}")


def episoder(mask):
    n = 0
    for j in range(mask.shape[1]):
        forr = None
        for i in np.where(mask[:, j])[0]:
            if forr is None or i - forr > 12:
                n += 1
            forr = i
    return n


def analyse(T, h, fra, til):
    Y = (lr.shift(-h) - lr).values
    rad = (lr.index >= fra) & (lr.index <= til)
    S, Yp, Tp = SIG[rad], Y[rad], T.values[rad]

    def d(Tv):
        ok = S & np.isfinite(Yp)
        hoy, lav = ok & (Tv == 2)[:, None], ok & (Tv == 0)[:, None]
        mid = ok & (Tv == 1)[:, None]
        if not hoy.sum() or not lav.sum():
            return np.nan, hoy, lav, mid
        return Yp[hoy].mean() - Yp[lav].mean(), hoy, lav, mid
    diff, hoy, lav, mid = d(Tp)
    if not np.isfinite(diff):
        return None
    null = np.array([d(np.roll(Tp, rng.integers(24, len(Tp) - 24)))[0] for _ in range(2000)])
    null = np.abs(null[np.isfinite(null)])
    pv = (np.sum(null >= abs(diff)) + 1) / (len(null) + 1)
    gyldig = np.where(np.isfinite(Tp))[0]
    midt = gyldig[len(gyldig) // 2]; hv = []
    for sl in (np.arange(len(Tp)) < midt, np.arange(len(Tp)) >= midt):
        Th = np.where(sl, Tp, np.nan); hv.append(d(Th)[0])
    return dict(hoy=Yp[hoy].mean(), mid=Yp[mid].mean() if mid.sum() else np.nan, lav=Yp[lav].mean(), diff=diff, p=pv,
                h1=hv[0], h2=hv[1], n_hoy=int(hoy.sum()), n_lav=int(lav.sum()), ep_hoy=episoder(hoy), ep_lav=episoder(lav))


def pp(x):
    return "   -  " if x is None or not np.isfinite(x) else f"{100*x:+6.1f}"


rader, tester = [], []
for n in MAAL:
    T = tred[n]; start = T.dropna().index[0]
    print(f"\n==================== {n} (oeverste mot nederste tredjedel, log realpris, per h mnd)")
    perioder = {"avgjoer": (start, TIL), "2015-2026": NYTT} if n != "MOVE" else {"2005-2026": (start, NYTT[1]), "2015-2026": NYTT}
    for h in (6, 12, 24):
        for pn, (fra, til) in perioder.items():
            a = analyse(T, h, fra, til)
            if a is None:
                print(f"   h {h:2} {pn:9} for faa signalmaaneder"); continue
            rader.append({"maal": n, "h": h, "periode": pn, "fra": str(fra), **a})
            print(f"   h {h:2} {pn:9} ({fra}) hoey {pp(a['hoy'])} % (n {a['n_hoy']}, ep {a['ep_hoy']})  midt {pp(a['mid'])} %"
                  f"  lav {pp(a['lav'])} % (n {a['n_lav']}, ep {a['ep_lav']})  forskjell {pp(a['diff'])} pp  p {a['p']:.3f}"
                  f"  halvdeler {pp(a['h1'])}/{pp(a['h2'])}")
            if pn == "avgjoer":
                ok = (abs(a["diff"]) >= 0.05 * h / 12 and a["p"] < 0.05 and np.sign(a["h1"]) == np.sign(a["h2"]) == np.sign(a["diff"])
                      and a["ep_hoy"] >= 3 and a["ep_lav"] >= 3)
                tester.append({"test": f"{n}, h {h}", "p": a["p"], "ok": ok, "retning": "bedre ved hoeyt nivaa" if a["diff"] > 0 else "bedre ved lavt nivaa"})

Tt = pd.DataFrame(tester).sort_values("p").reset_index(drop=True); m = len(Tt)
g = max([i + 1 for i in range(m) if Tt.p[i] <= 0.10 * (i + 1) / m], default=0)
Tt["bh"] = [i < g for i in range(m)]
print("\nAVGJOERELSE (VIX 1993 til 2014, DXY 1974 til 2014)\n")
for _, t in Tt.sort_values("test").iterrows():
    print(f"   {t.test:12}: {'HOLDER, ' + t.retning if (t.ok and t.bh) else 'holder ikke'} (krav a til d {'ja' if t.ok else 'nei'}, p {t.p:.3f}, BH {'ja' if t.bh else 'nei'})")

print("\nPAPIRPORTEFOELJEN (beskrivende): nivaa ved inngang og papirene over posisjonen, NOK")
try:
    pos = [q for q in json.load(open("handel.json", encoding="utf-8"))["portefolje"]["posisjoner"] if q["variant"] == "alle"]
    ord_ = ["lav", "midt", "hoey"]
    for q in pos:
        t = pd.Period(q["inngang"], "M")
        niv = "  ".join(f"{n} {nivaa[n].get(t, np.nan):6.1f} ({ord_[int(tred[n][t])] if np.isfinite(tred[n].get(t, np.nan)) else '-'})" for n in MAAL)
        print(f"   {q['segment']:10} {q['inngang']}  {niv}  papirer {q['avk']:+7.1f} %  MSCI World {q['world']:+6.1f} %")
except Exception as e:
    print(f"   kunne ikke lese handel.json ({type(e).__name__})")
pd.DataFrame(rader).to_csv("sonder/signal_vix_dxy_move.csv", index=False)
print("\nLagret sonder/signal_vix_dxy_move.csv")
