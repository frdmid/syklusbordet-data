# ---------------------------------------------------------------------------
# sonde_kjor_miners_k1_varianter: kan K1 for gullgruvene gjøres bedre?
# (Frodes bestilling 29.10.2026, fire spørsmål)
#
# K1 (signalet i feltet Gullgruver fra 29.10): S1 gull mot Brent 3 mnd i
# øverste tredjedel minst 3 mnd på rad, og O6 olje-A 6 mnd i øverste tredjedel
# samme måned (tredjedelene mot det som var kjent da, minst 36 mnd).
# Varianter, valgt før kjøring:
#   V1   K1 med 2 mnd: BEGGE og S1 minst 2 mnd på rad
#   V2a  K1 forsinket 1 mnd: signal i måneder der K1 sto måneden før
#   V2b  K1 forsinket 2 mnd: signal i måneder der K1 sto to måneder før
#   V3   K1 med rullende olje-A: O6 regnet på olje-A mot siste 10 år
#        (120 mnd, minst 60) i stedet for hele historikken
#   V4   K1 og gull mot olje ikke dyrt: nivået i log(gull/Brent) under 80.
#        persentil mot siste 10 år (120 mnd, minst 60)
# Utfall: kurven av gruveaksjer og ^XAU minus SPY, neste 3 og 6 mnd.
# AVGJØRES på 1993-01 til 2014-06. Dette er sjette sonde på gruvene og de
# samme årene; kravet om å slå K1 er satt for å ta høyde for det.
#
# KRITERIER (satt før kjøring, 29.10.2026). En variant holder på horisont h
# hvis, i 1993 til 2014 og for BÅDE kurven og ^XAU:
#   (a) snittet i variantens måneder er minst 3 prosentpoeng per 3 mnd høyere
#       enn i alle andre måneder, med p under 0,05 mot sirkulært forskjøvet
#       variantserie (2000 trekk, minst 24 mnd),
#   (b) positiv forskjell i begge halvdelene (1993 til 2003, 2004 til 2014),
#   (c) både snittet og forskjellen mot andre måneder er høyere enn for K1
#       på samme horisont og papir,
#   (d) minst 10 måneder og 4 sammenhengende perioder med signal, og
#   (e) Benjamini-Hochberg på 10 % over 5 varianter x 2 horisonter.
# K1 og BEGGE vises til sammenligning. 2015 til 2026 vises, avgjør ikke.
# Skriver ingenting til dashbordet. Utdata sonder/miners_k1_varianter.csv.
# ---------------------------------------------------------------------------

import time
import numpy as np
import pandas as pd
import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
rng = np.random.default_rng(20261029)
AKSJER = ["NEM", "B", "AEM", "GFI", "AU", "HMY", "KGC", "AGI", "IAG", "EGO", "BVN"]
UTVALG = (pd.Period("1993-01", "M"), pd.Period("2014-06", "M"))


def mnd(sym):
    r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}",
                     params={"period1": 0, "period2": int(time.time()), "interval": "1d", "events": "div,split"},
                     headers=UA, timeout=60)
    res = r.json()["chart"]["result"][0]
    if (res.get("meta") or {}).get("dataGranularity") != "1d":
        raise ValueError(f"{sym}: ikke dagskurser")
    adj = res["indicators"].get("adjclose", [{}])[0].get("adjclose") or res["indicators"]["quote"][0]["close"]
    s = pd.Series(adj, index=pd.to_datetime(res["timestamp"], unit="s")).dropna()
    s = s[s > 0].resample("ME").last(); s.index = s.index.to_period("M")
    time.sleep(0.3)
    return np.log(s)


def toppen(serie, minn=36):
    v = serie.values; ut = np.full(len(v), np.nan)
    for i in range(len(v)):
        h = v[: i + 1]; h = h[np.isfinite(h)]
        if np.isfinite(v[i]) and len(h) >= minn:
            ut[i] = float((h <= v[i]).mean() >= 2 / 3)
    return pd.Series(ut, index=serie.index)


def rekke(x):
    r, n = [], 0
    for v in x:
        n = n + 1 if v == 1 else 0
        r.append(n)
    return np.array(r)


def pctl(v, vindu=None, minn=60):
    ut = np.full(len(v), np.nan)
    for i in range(len(v)):
        w = v[: i + 1] if vindu is None else v[max(0, i + 1 - vindu): i + 1]
        if len(w) >= minn:
            ut[i] = (w <= v[i]).mean()
    return ut


p = pd.read_csv("serier/priser_mnd.csv")
def serie(seg, kol):
    s = p[p.segment == seg].set_index("t")[kol].astype(float)
    s.index = pd.PeriodIndex(s.index, freq="M"); return s.sort_index()
ol = serie("brent", "real"); v = np.log(ol.values)
oljeA = pd.Series((1 - pctl(v)) * 100, index=ol.index)
oljeAr = pd.Series((1 - pctl(v, 120)) * 100, index=ol.index)
gm = np.log(serie("gold", "nom")) - np.log(serie("brent", "nom"))
gm_r = pd.Series(pctl(gm.values, 120), index=gm.index)
S = pd.concat([toppen((gm - gm.shift(3)).dropna()), toppen((oljeA - oljeA.shift(6)).dropna()),
               toppen((oljeAr - oljeAr.shift(6)).dropna()), gm_r],
              axis=1, keys=["s1", "o6", "o6r", "gm_r"]).dropna()
S["begge"] = ((S.s1 == 1) & (S.o6 == 1)).astype(float)
S["r_s1"] = rekke(S.s1.values)
k1 = (S.begge == 1) & (S.r_s1 >= 3)
VAR = {"BEGGE uten krav": S.begge == 1,
       "K1": k1,
       "V1 K1 med 2 mnd": (S.begge == 1) & (S.r_s1 >= 2),
       "V2a K1 forsinket 1 mnd": k1.shift(1, fill_value=False),
       "V2b K1 forsinket 2 mnd": k1.shift(2, fill_value=False),
       "V3 K1 med rullende olje-A": (S.s1 == 1) & (S.r_s1 >= 3) & (S.o6r == 1),
       "V4 K1 og gull mot olje ikke dyrt": k1 & (S.gm_r < 0.8)}

px = {s: mnd(s) for s in AKSJER + ["^XAU", "SPY"]}
R = pd.DataFrame({s: px[s] for s in AKSJER}).diff()
kr = R.mean(axis=1, skipna=True); kr[R.notna().sum(axis=1) == 0] = np.nan
PAP = {"KURV": kr.cumsum(), "^XAU": px["^XAU"]}
def ut(k, h):
    return (PAP[k].shift(-h) - PAP[k]) - (px["SPY"].shift(-h) - px["SPY"])


def analyse(var, k, h, fra, til):
    d = pd.concat([var.astype(float), ut(k, h)], axis=1).dropna()
    d.columns = ["v", "y"]
    d = d[(d.index >= fra) & (d.index <= til)]
    b = d.v.values; y = d.y.values
    if b.sum() < 3:
        return None
    diff = y[b == 1].mean() - y[b == 0].mean()
    null = []
    for _ in range(2000):
        s = np.roll(b, rng.integers(24, len(b) - 24))
        if s.sum() and (1 - s).sum():
            null.append(y[s == 1].mean() - y[s == 0].mean())
    pv = (np.sum(np.array(null) >= diff) + 1) / (len(null) + 1)
    mid = d.index[len(d) // 2]; halv = []
    for m in (d.index < mid, d.index >= mid):
        dd = d[m]
        halv.append(dd.y[dd.v == 1].mean() - dd.y[dd.v == 0].mean() if dd.v.sum() and (1 - dd.v).sum() else np.nan)
    per = int(((b == 1) & (np.r_[0, b[:-1]] == 0)).sum())
    return dict(snitt=y[b == 1].mean(), andre=y[b == 0].mean(), diff=diff, p=pv, h1=halv[0], h2=halv[1],
                n=int(b.sum()), per=per)


PER = {"1993-2014 (avgjør)": UTVALG, "2015-2026": (pd.Period("2015-01", "M"), pd.Period("2026-12", "M"))}
rader, tester = [], []
for h in (3, 6):
    print(f"==================== h = {h} mnd (per {h} mnd, log, minus SPY)")
    res = {}
    for vn, var in VAR.items():
        print(f"   {vn}")
        for pn, (fra, til) in PER.items():
            for k in PAP:
                a = analyse(var, k, h, fra, til)
                if a is None:
                    print(f"      {pn:18} {k:5} for få måneder"); continue
                res[(vn, pn, k)] = a
                rader.append({"variant": vn, "h": h, "periode": pn, "papir": k, **a})
                print(f"      {pn:18} {k:5} signal {100*a['snitt']:+5.1f}% (n {a['n']}, {a['per']} perioder)  andre {100*a['andre']:+5.1f}%"
                      f"  forskjell {100*a['diff']:+5.1f} pp p {a['p']:.3f}  halvdeler {100*a['h1']:+.1f}/{100*a['h2']:+.1f}")
        if vn.startswith("V"):
            avg = "1993-2014 (avgjør)"
            if all((vn, avg, k) in res for k in PAP):
                ok = True
                for k in PAP:
                    t, r1 = res[(vn, avg, k)], res[("K1", avg, k)]
                    ok &= (t["diff"] * 3 / h >= 0.03 and t["p"] < 0.05 and t["h1"] > 0 and t["h2"] > 0
                           and t["snitt"] > r1["snitt"] and t["diff"] > r1["diff"] and t["n"] >= 10 and t["per"] >= 4)
                tester.append({"test": f"{vn}, h {h}", "p": max(res[(vn, avg, k)]["p"] for k in PAP), "ok": ok})
            else:
                tester.append({"test": f"{vn}, h {h}", "p": 1.0, "ok": False})
    print()

T = pd.DataFrame(tester).sort_values("p").reset_index(drop=True)
m = len(T)
grense = max([i + 1 for i in range(m) if T.p[i] <= 0.10 * (i + 1) / m], default=0)
T["bh"] = [i < grense for i in range(m)]
print("AVGJØRELSE (1993 til 2014)\n")
for _, t in T.sort_values("test").iterrows():
    print(f"   {t.test:44}: {'HOLDER' if (t.ok and t.bh) else 'holder ikke'} (krav a til d {'ja' if t.ok else 'nei'}, største p {t.p:.3f}, BH {'ja' if t.bh else 'nei'})")
s = S.iloc[-1]
print(f"\nI DAG ({S.index[-1]}): S1 rekke {int(s.r_s1)}, O6 {int(s.o6)}, O6 rullende {int(s.o6r)}, "
      f"gull mot olje persentil siste 10 år {100*s.gm_r:.0f}, " + ", ".join(f"{vn} {'på' if bool(var.iloc[-1]) else 'av'}" for vn, var in VAR.items()))
pd.DataFrame(rader).to_csv("sonder/miners_k1_varianter.csv", index=False)
print("Lagret sonder/miners_k1_varianter.csv")
