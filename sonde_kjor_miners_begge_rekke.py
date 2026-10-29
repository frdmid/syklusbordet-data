# ---------------------------------------------------------------------------
# sonde_kjor_miners_begge_rekke: blir kombinasjonssignalet for gullgruvene
# bedre med krav til rekkelengde? (Frodes bestilling 28.10.2026)
#
# Grunnlag: kombinasjonssignalet BEGGE (S1 gull mot Brent 3 mnd og O6 olje-A
# 6 mnd begge i øverste tredjedel, punkt i tid) fra sonde_kjor_miners_begge,
# og mønstrene i sonde_kjor_miners_rekker (ikke sikre): S1 ga lite i rekker på
# 1 til 2 mnd og mye fra 3 mnd; O6 var best i rekker på 3 til 5 mnd og
# negativ fra 6 mnd. Tre varianter, valgt ut fra de mønstrene (dermed etter
# å ha sett data som inkluderer 1993 til 2014):
#   K1  BEGGE, og S1 har hatt punkt minst 3 mnd på rad
#   K2  BEGGE har stått minst 2 mnd på rad
#   K3  BEGGE, og O6 har hatt punkt høyst 5 mnd på rad
# Utfall: kurven av gruveaksjer og ^XAU minus SPY, neste 3 og 6 mnd.
# AVGJØRES på 1993-01 til 2014-06.
#
# KRITERIER (satt før kjøring, 28.10.2026). En variant holder på horisont h
# hvis, i 1993 til 2014 og for BÅDE kurven og ^XAU:
#   (a) snittet i variantens måneder er minst 3 prosentpoeng per 3 mnd høyere
#       enn i alle andre måneder, med p under 0,05 mot sirkulært forskjøvet
#       variantserie (2000 trekk, minst 24 mnd),
#   (b) positiv forskjell i begge halvdelene (1993 til 2003, 2004 til 2014),
#   (c) snittet i variantens måneder er høyere enn i BEGGE-måneder som
#       varianten tar bort (kravet gjør signalet bedre, ikke bare smalere),
#   (d) snittet i variantens måneder er høyere enn i måneder med bare S1
#       (det BEGGE strandet på),
#   (e) minst 10 måneder og 4 sammenhengende perioder med signal, og
#   (f) Benjamini-Hochberg på 10 % over 3 varianter x 2 horisonter.
# BEGGE uten krav vises til sammenligning. 2015 til 2026 vises, avgjør ikke.
# Skriver ingenting til dashbordet. Utdata sonder/miners_begge_rekke.csv.
# ---------------------------------------------------------------------------

import time
import numpy as np
import pandas as pd
import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
rng = np.random.default_rng(20261028)
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


p = pd.read_csv("serier/priser_mnd.csv")
def serie(seg, kol):
    s = p[p.segment == seg].set_index("t")[kol].astype(float)
    s.index = pd.PeriodIndex(s.index, freq="M"); return s.sort_index()
ol = serie("brent", "real"); v = np.log(ol.values)
o = np.full(len(v), np.nan)
for i in range(len(v)):
    if i + 1 >= 60:
        o[i] = (v[: i + 1] <= v[i]).sum() / (i + 1)
oljeA = pd.Series((1 - o) * 100, index=ol.index)
gm = np.log(serie("gold", "nom")) - np.log(serie("brent", "nom"))
S = pd.concat([toppen((gm - gm.shift(3)).dropna()), toppen((oljeA - oljeA.shift(6)).dropna())],
              axis=1, keys=["s1", "o6"]).dropna()
S["begge"] = ((S.s1 == 1) & (S.o6 == 1)).astype(float)
S["r_s1"], S["r_o6"], S["r_begge"] = rekke(S.s1.values), rekke(S.o6.values), rekke(S.begge.values)
VAR = {"BEGGE uten krav": S.begge == 1,
       "K1 BEGGE og S1 minst 3 mnd på rad": (S.begge == 1) & (S.r_s1 >= 3),
       "K2 BEGGE minst 2 mnd på rad": S.r_begge >= 2,
       "K3 BEGGE og O6 høyst 5 mnd på rad": (S.begge == 1) & (S.r_o6 <= 5)}

px = {s: mnd(s) for s in AKSJER + ["^XAU", "SPY"]}
R = pd.DataFrame({s: px[s] for s in AKSJER}).diff()
kr = R.mean(axis=1, skipna=True); kr[R.notna().sum(axis=1) == 0] = np.nan
PAP = {"KURV": kr.cumsum(), "^XAU": px["^XAU"]}
def ut(k, h):
    return (PAP[k].shift(-h) - PAP[k]) - (px["SPY"].shift(-h) - px["SPY"])


def analyse(var, k, h, fra, til):
    d = pd.concat([var.astype(float), S, ut(k, h)], axis=1).dropna()
    d.columns = ["v"] + list(S.columns) + ["y"]
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
    tatt_bort = d.y[(d.begge == 1) & (d.v == 0)]
    bare_s1 = d.y[(d.s1 == 1) & (d.o6 == 0)].mean()
    per = int(((b == 1) & (np.r_[0, b[:-1]] == 0)).sum())
    return dict(snitt=y[b == 1].mean(), andre=y[b == 0].mean(), diff=diff, p=pv, h1=halv[0], h2=halv[1],
                tatt_bort=tatt_bort.mean() if len(tatt_bort) else np.nan, n_tatt=len(tatt_bort),
                bare_s1=bare_s1, n=int(b.sum()), per=per)


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
                      f"  forskjell {100*a['diff']:+5.1f} pp p {a['p']:.3f}  halvdeler {100*a['h1']:+.1f}/{100*a['h2']:+.1f}"
                      f"  | tatt bort fra BEGGE {100*a['tatt_bort']:+.1f}% (n {a['n_tatt']})  bare S1 {100*a['bare_s1']:+.1f}%")
        if vn.startswith("K") and ("1993-2014 (avgjør)", "KURV") in res and ("1993-2014 (avgjør)", "^XAU") in res:
            A, B = res[("1993-2014 (avgjør)", "KURV")], res[("1993-2014 (avgjør)", "^XAU")]
            ok = all(t["diff"] * 3 / h >= 0.03 and t["p"] < 0.05 and t["h1"] > 0 and t["h2"] > 0
                     and t["n_tatt"] > 0 and t["snitt"] > t["tatt_bort"] and t["snitt"] > t["bare_s1"]
                     and t["n"] >= 10 and t["per"] >= 4 for t in (A, B))
            tester.append({"test": f"{vn}, h {h}", "p": max(A["p"], B["p"]), "ok": ok})
    print()

T = pd.DataFrame(tester).sort_values("p").reset_index(drop=True)
m = len(T)
grense = max([i + 1 for i in range(m) if T.p[i] <= 0.10 * (i + 1) / m], default=0)
T["bh"] = [i < grense for i in range(m)]
print("AVGJØRELSE (1993 til 2014)\n")
for _, t in T.sort_values("test").iterrows():
    print(f"   {t.test:44}: {'HOLDER' if (t.ok and t.bh) else 'holder ikke'} (største p {t.p:.3f}, BH {'ja' if t.bh else 'nei'})")
s = S.iloc[-1]
print(f"\nI DAG ({S.index[-1]}): S1 rekke {int(s.r_s1)}, O6 rekke {int(s.r_o6)}, BEGGE rekke {int(s.r_begge)}")
pd.DataFrame(rader).to_csv("sonder/miners_begge_rekke.csv", index=False)
print("Lagret sonder/miners_begge_rekke.csv")
