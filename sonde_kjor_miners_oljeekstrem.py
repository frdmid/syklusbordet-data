# ---------------------------------------------------------------------------
# sonde_kjor_miners_oljeekstrem: gjør gullgruvene det godt når oljen er
# ekstremt billig? (Frodes bestilling 29.10.2026, etter at K1 ble tatt ut)
#
# Bakgrunn: i sonde_kjor_miners_k1_varianter var de beste K1-månedene etter
# 2015 oljekrakk (2015-16, 2020), der gull ble ekstremt dyrt mot olje. Ideen
# er altså sett i data, også i 2008 som ligger i 1993 til 2014.
# Varianter, valgt før kjøring (olje = Brent realpris, månedssnitt):
#   E1  olje-A minst 90 (olje blant de billigste 10 % mot hele kjent historikk)
#   E2  olje-Ar minst 90 (blant de billigste 10 % mot siste 10 år, minst 60 mnd)
#   E3  oljekrakk: Brent minst 40 % under høyeste måned siste 12 mnd
#   E4  E1 og S1 (gull mot Brent 3 mnd i øverste tredjedel, punkt i tid)
#   E5  E2 og S1
# Utfall: kurven av gruveaksjer og ^XAU minus SPY, neste 3 og 6 mnd.
# AVGJØRES på 1993-01 til 2014-06.
#
# KRITERIER (satt før kjøring, 29.10.2026). En variant holder på horisont h
# hvis, i 1993 til 2014 og for BÅDE kurven og ^XAU:
#   (a) snittet i variantens måneder er minst 3 prosentpoeng per 3 mnd høyere
#       enn i alle andre måneder, med p under 0,05 mot sirkulært forskjøvet
#       variantserie (2000 trekk, minst 24 mnd),
#   (b) positiv forskjell i begge halvdelene (1993 til 2003, 2004 til 2014),
#   (c) minst 10 måneder og 3 sammenhengende perioder med signal, og
#   (d) Benjamini-Hochberg på 10 % over 5 varianter x 2 horisonter.
# Episodene listes. 2015 til 2026 vises, avgjør ikke.
# Skriver ingenting til dashbordet. Utdata sonder/miners_oljeekstrem.csv.
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
bn = np.log(serie("brent", "nom"))
krakk = (bn - bn.rolling(12, min_periods=12).max()) <= np.log(0.6)
gm = np.log(serie("gold", "nom")) - np.log(serie("brent", "nom"))
S = pd.concat([toppen((gm - gm.shift(3)).dropna()), oljeA, oljeAr, krakk.astype(float)],
              axis=1, keys=["s1", "oA", "oAr", "krakk"]).dropna()
VAR = {"E1 olje-A minst 90": S.oA >= 90,
       "E2 olje-Ar minst 90": S.oAr >= 90,
       "E3 oljekrakk 40 %": S.krakk == 1,
       "E4 olje-A minst 90 og S1": (S.oA >= 90) & (S.s1 == 1),
       "E5 olje-Ar minst 90 og S1": (S.oAr >= 90) & (S.s1 == 1)}

px = {s: mnd(s) for s in AKSJER + ["^XAU", "SPY"]}
R = pd.DataFrame({s: px[s] for s in AKSJER}).diff()
kr = R.mean(axis=1, skipna=True); kr[R.notna().sum(axis=1) == 0] = np.nan
PAP = {"KURV": kr.cumsum(), "^XAU": px["^XAU"]}
def ut(k, h):
    return (PAP[k].shift(-h) - PAP[k]) - (px["SPY"].shift(-h) - px["SPY"])


def episoder(var):
    m = [t for t, x in var.items() if x and t >= pd.Period("1993-01", "M")]
    ep, start, forr = [], None, None
    for t in m:
        if forr is None or t != forr + 1:
            if start is not None:
                ep.append((start, forr))
            start = t
        forr = t
    if start is not None:
        ep.append((start, forr))
    return ", ".join(f"{a}" if a == b else f"{a} til {b}" for a, b in ep)


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


print("EPISODER (fra 1993)")
for vn, var in VAR.items():
    print(f"   {vn}: {episoder(var)}")
print()

PER = {"1993-2014 (avgjør)": UTVALG, "2015-2026": (pd.Period("2015-01", "M"), pd.Period("2026-12", "M"))}
rader, tester = [], []
for h in (3, 6):
    print(f"==================== h = {h} mnd (per {h} mnd, log, minus SPY)")
    for vn, var in VAR.items():
        print(f"   {vn}")
        res = {}
        for pn, (fra, til) in PER.items():
            for k in PAP:
                a = analyse(var, k, h, fra, til)
                if a is None:
                    print(f"      {pn:18} {k:5} for få måneder"); continue
                res[(pn, k)] = a
                rader.append({"variant": vn, "h": h, "periode": pn, "papir": k, **a})
                print(f"      {pn:18} {k:5} signal {100*a['snitt']:+5.1f}% (n {a['n']}, {a['per']} perioder)  andre {100*a['andre']:+5.1f}%"
                      f"  forskjell {100*a['diff']:+5.1f} pp p {a['p']:.3f}  halvdeler {100*a['h1']:+.1f}/{100*a['h2']:+.1f}")
        avg = "1993-2014 (avgjør)"
        if all((avg, k) in res for k in PAP):
            ok = all(t["diff"] * 3 / h >= 0.03 and t["p"] < 0.05 and t["h1"] > 0 and t["h2"] > 0
                     and t["n"] >= 10 and t["per"] >= 3 for t in (res[(avg, k)] for k in PAP))
            tester.append({"test": f"{vn}, h {h}", "p": max(res[(avg, k)]["p"] for k in PAP), "ok": ok})
        else:
            tester.append({"test": f"{vn}, h {h}", "p": 1.0, "ok": False})
    print()

T = pd.DataFrame(tester).sort_values("p").reset_index(drop=True)
m = len(T)
grense = max([i + 1 for i in range(m) if T.p[i] <= 0.10 * (i + 1) / m], default=0)
T["bh"] = [i < grense for i in range(m)]
print("AVGJØRELSE (1993 til 2014)\n")
for _, t in T.sort_values("test").iterrows():
    print(f"   {t.test:34}: {'HOLDER' if (t.ok and t.bh) else 'holder ikke'} (krav a til c {'ja' if t.ok else 'nei'}, største p {t.p:.3f}, BH {'ja' if t.bh else 'nei'})")
s = S.iloc[-1]
print(f"\nI DAG ({S.index[-1]}): olje-A {s.oA:.0f}, olje-Ar {s.oAr:.0f}, krakk {'ja' if s.krakk else 'nei'}, S1 {'punkt' if s.s1 else 'ikke punkt'}")
pd.DataFrame(rader).to_csv("sonder/miners_oljeekstrem.csv", index=False)
print("Lagret sonder/miners_oljeekstrem.csv")
