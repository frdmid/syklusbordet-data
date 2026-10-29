# ---------------------------------------------------------------------------
# sonde_kjor_miners_begge: er «begge gruvesignalene samme måned» et signal som
# holder utenfor perioden det ble sett i? (Frodes bestilling 28.10.2026; skal
# i så fall erstatte de to signalene i feltet Gullgruver)
#
# Signalpunktene som i sonde_kjor_miners_rekker (øverste tredjedel mot det
# som var kjent da, minst 36 mnd, månedssnitt fra serier/priser_mnd.csv):
#   S1  endring i log(gull/Brent) siste 3 mnd
#   O6  endring i olje-A (Brent realpris) siste 6 mnd
# BEGGE = måneder der både S1 og O6 har punkt.
# Utfall: kurven av gruveaksjer (NEM, Barrick, AEM, GFI, AU, HMY, KGC, AGI,
# IAG, EGO, BVN; likevekt, med utbytte) og ^XAU, minus SPY, neste 3 og 6 mnd.
#
# AVGJØRES på 1993-01 til 2014-06 (utfallene slutter før 2015): mønsteret ble
# sett på data som inkluderer 2015 til 2026, og signalene ble funnet der.
#
# KRITERIER (satt før kjøring, 28.10.2026). BEGGE holder på horisont h hvis,
# i 1993 til 2014 og for BÅDE kurven og ^XAU:
#   (a) snittet i BEGGE-måneder er minst 3 prosentpoeng per 3 mnd høyere enn
#       i alle andre måneder,
#   (b) p under 0,05 mot sirkulært forskjøvet BEGGE-serie (2000 trekk, minst
#       24 mnd; bevarer hvor lenge signalene står),
#   (c) forskjellen er positiv i begge halvdelene (1993 til 2003 og 2004 til
#       2014),
#   (d) snittet i BEGGE-måneder er høyere enn i måneder med bare S1 og i
#       måneder med bare O6 (for å kunne erstatte dem), og
#   (e) Benjamini-Hochberg på 10 % over de to horisontene (på den største av
#       de to p-verdiene).
# Antall sammenhengende perioder med BEGGE vises, siden overlappende utfall
# gjør månedene avhengige. 2015 til 2026 og hele perioden vises, avgjør ikke;
# UCITS GDX.L og GDXJ.L mot MSCI World vises for 2015 til 2026.
# Skriver ingenting til dashbordet. Utdata sonder/miners_begge.csv.
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

px = {s: mnd(s) for s in AKSJER + ["^XAU", "SPY", "GDX.L", "GDXJ.L", "IWDA.L"]}
R = pd.DataFrame({s: px[s] for s in AKSJER}).diff()
kr = R.mean(axis=1, skipna=True); kr[R.notna().sum(axis=1) == 0] = np.nan
PAP = {"KURV": kr.cumsum(), "^XAU": px["^XAU"], "GDX.L": px["GDX.L"], "GDXJ.L": px["GDXJ.L"]}
def ut(k, h):
    ref = px["IWDA.L"] if k in ("GDX.L", "GDXJ.L") else px["SPY"]
    return (PAP[k].shift(-h) - PAP[k]) - (ref.shift(-h) - ref)


def perioder(b):
    return int(((b == 1) & (np.r_[0, b[:-1]] == 0)).sum())


def analyse(k, h, fra, til, med_p=True):
    d = pd.concat([S, ut(k, h)], axis=1).dropna(); d.columns = ["s1", "o6", "begge", "y"]
    d = d[(d.index >= fra) & (d.index <= til)]
    if len(d) < 36 or d.begge.sum() < 6:
        return None
    b = d.begge.values; y = d.y.values
    diff = y[b == 1].mean() - y[b == 0].mean()
    pv = np.nan
    if med_p:
        null = []
        for _ in range(2000):
            s = np.roll(b, rng.integers(24, len(b) - 24))
            if s.sum() and (1 - s).sum():
                null.append(y[s == 1].mean() - y[s == 0].mean())
        null = np.array(null); pv = (np.sum(null >= diff) + 1) / (len(null) + 1)
    mid = d.index[len(d) // 2]
    halv = []
    for m in (d.index < mid, d.index >= mid):
        dd = d[m]
        halv.append(dd.y[dd.begge == 1].mean() - dd.y[dd.begge == 0].mean() if dd.begge.sum() and (1 - dd.begge).sum() else np.nan)
    bare_s1 = d.y[(d.s1 == 1) & (d.o6 == 0)].mean(); bare_o6 = d.y[(d.s1 == 0) & (d.o6 == 1)].mean()
    ingen = d.y[(d.s1 == 0) & (d.o6 == 0)].mean()
    return dict(begge=y[b == 1].mean(), andre=y[b == 0].mean(), diff=diff, p=pv, h1=halv[0], h2=halv[1],
                bare_s1=bare_s1, bare_o6=bare_o6, ingen=ingen, n=int(b.sum()), per=perioder(b), N=len(d))


PER = {"1993-2014 (avgjør)": UTVALG, "2015-2026": (pd.Period("2015-01", "M"), pd.Period("2026-12", "M")),
       "hele": (pd.Period("1993-01", "M"), pd.Period("2026-12", "M"))}
rader, tester = [], []
for h in (3, 6):
    print(f"==================== h = {h} mnd (alle tall per {h} mnd, log, minus marked)")
    res = {}
    for pn, (fra, til) in PER.items():
        for k in PAP:
            a = analyse(k, h, fra, til, med_p=(k in ("KURV", "^XAU")))
            if a is None:
                continue
            res[(pn, k)] = a
            rader.append({"h": h, "periode": pn, "papir": k, **a})
            print(f"   {pn:18} {k:7} BEGGE {100*a['begge']:+5.1f}% (n {a['n']}, {a['per']} perioder)  andre {100*a['andre']:+5.1f}%"
                  f"  forskjell {100*a['diff']:+5.1f} pp" + (f" p {a['p']:.3f}" if np.isfinite(a['p']) else "")
                  + f"  halvdeler {100*a['h1']:+.1f}/{100*a['h2']:+.1f}  | bare S1 {100*a['bare_s1']:+.1f}%  bare O6 {100*a['bare_o6']:+.1f}%  ingen {100*a['ingen']:+.1f}%")
    a, b = res[("1993-2014 (avgjør)", "KURV")], res[("1993-2014 (avgjør)", "^XAU")]
    ok = all(t["diff"] * 3 / h >= 0.03 and t["p"] < 0.05 and t["h1"] > 0 and t["h2"] > 0
             and t["begge"] > t["bare_s1"] and t["begge"] > t["bare_o6"] for t in (a, b))
    tester.append({"h": h, "p": max(a["p"], b["p"]), "ok": ok})
    print()

T = pd.DataFrame(tester).sort_values("p").reset_index(drop=True)
m = len(T)
grense = max([i + 1 for i in range(m) if T.p[i] <= 0.10 * (i + 1) / m], default=0)
T["bh"] = [i < grense for i in range(m)]
print("AVGJØRELSE (1993 til 2014, utenfor perioden signalene ble funnet i)\n")
for _, t in T.sort_values("h").iterrows():
    print(f"   BEGGE, h={t.h} mnd: {'HOLDER' if (t.ok and t.bh) else 'holder ikke'} (største p {t.p:.3f}, BH {'ja' if t.bh else 'nei'})")
s = S.iloc[-1]
print(f"\nI DAG ({S.index[-1]}): S1 {'punkt' if s.s1 else 'ikke punkt'}, O6 {'punkt' if s.o6 else 'ikke punkt'}, BEGGE {'ja' if s.begge else 'nei'}")
pd.DataFrame(rader).to_csv("sonder/miners_begge.csv", index=False)
print("Lagret sonder/miners_begge.csv")
