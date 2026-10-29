# ---------------------------------------------------------------------------
# sonde_kjor_miners_feilpris: er gullgruvene feilpriset mot gull og olje, og
# rettes det opp? (Frodes bestilling 28.10.2026, etter at A på gull mot olje
# ikke holdt som bunnsone i sonde_kjor_miners_a)
#
# Gruvene: PHLX gull- og sølvgruveindeksen ^XAU (Yahoo, månedsslutt, fra 1985).
# Gull og WTI: serier/priser_mnd.csv (nominell USD, fra 1986 for WTI).
# Marked: S&P 500 (^GSPC).
#
# Tre mål på feilprising, alle punkt i tid:
#   M1 gruver mot gull: log(^XAU) minus log(gull).
#   M2 gruver mot gull og olje: residualen fra log(^XAU) = a + b log(gull)
#      + c log(olje), tilpasset bare på månedene før t (minst 120 mnd).
#   M3 som M2, med log(S&P 500) i tillegg.
# For hvert mål regnes A, Ad og Ar med formlene fra bordet på MINUS målet
# (høy A = gruvene billige mot det gull og olje tilsier).
#
# Utfall: ^XAU minus gull de neste 24 mnd (log, avgjør); 12 mnd og ^XAU
# minus S&P 500 vises. GDX (2006) og AUCO.L (UCITS, 2008) minus gull vises for
# årene der de finnes.
#
# KRITERIER (satt før kjøring, 28.10.2026). Et mål holder hvis:
#   (a) rangkorrelasjonen mellom A og utfallet (24 mnd) er positiv med
#       p under 0,05 mot sirkulært forskjøvet A (2000 trekk, minst 24 mnd),
#   (b) samme fortegn før og etter 2008,
#   (c) bunnsonen (A og Ad 80 eller mer, ny episode etter 12 mnd, klynger på
#       183 dager) har minst 4 klynger, og medianen over klyngene er positiv
#       og høyere enn for like mange tilfeldige innganger (p under 0,10), og
#   (d) Benjamini-Hochberg på 10 % over de tre målene (på den største av
#       p-verdiene i (a) og (c)).
# Skriver ingenting til dashbordet. Utdata sonder/miners_feilpris.csv.
# ---------------------------------------------------------------------------

import time
from math import erf, sqrt
import numpy as np
import pandas as pd
import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
rng = np.random.default_rng(20261028)
MIN_HIST = 60


def A_raa(v):
    o = np.full(len(v), np.nan); ok = np.isfinite(v)
    for i in range(len(v)):
        h = v[: i + 1][ok[: i + 1]]
        if ok[i] and len(h) >= MIN_HIST:
            o[i] = (h <= v[i]).sum() / len(h)
    return (1 - o) * 100


def A_det(v, minn=60):
    o = np.full(len(v), np.nan)
    for i in range(len(v)):
        y = v[: i + 1]; t = np.arange(i + 1); m = np.isfinite(y)
        if not np.isfinite(v[i]) or m.sum() < minn:
            continue
        b, a = np.polyfit(t[m], y[m], 1); r = y[m] - (a + b * t[m])
        o[i] = (r <= r[-1]).sum() / len(r)
    return (1 - o) * 100


def A_rull(v, w=120, minn=60):
    o = np.full(len(v), np.nan)
    for i in range(len(v)):
        y = v[max(0, i - w + 1): i + 1]; y = y[np.isfinite(y)]
        if np.isfinite(v[i]) and len(y) >= minn:
            o[i] = (y <= v[i]).sum() / len(y)
    return (1 - o) * 100


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


p = pd.read_csv("serier/priser_mnd.csv")
def serie(seg):
    s = p[p.segment == seg].set_index("t").nom.astype(float)
    s.index = pd.PeriodIndex(s.index, freq="M"); return np.log(s.sort_index())
D = pd.DataFrame({"xau": mnd("^XAU"), "spx": mnd("^GSPC"), "gdx": mnd("GDX"), "auco": mnd("AUCO.L"),
                  "gull": serie("gold"), "olje": serie("wti")}).sort_index()
D = D[D.index >= pd.Period("1986-01", "M")]


def residual(cols, minn=120):
    ut = pd.Series(np.nan, index=D.index)
    for i in range(len(D)):
        h = D.iloc[:i][["xau"] + cols].dropna()
        if len(h) < minn or not np.isfinite(D.iloc[i][["xau"] + cols].values).all():
            continue
        A = np.column_stack([np.ones(len(h)), h[cols].values])
        b, *_ = np.linalg.lstsq(A, h.xau.values, rcond=None)
        ut.iloc[i] = D.xau.iloc[i] - (b[0] + D.iloc[i][cols].values @ b[1:])
    return ut


MAAL = {"M1 gruver mot gull": D.xau - D.gull,
        "M2 gruver mot gull og olje": residual(["gull", "olje"]),
        "M3 gruver mot gull, olje og marked": residual(["gull", "olje", "spx"])}
for h in (12, 24):
    D[f"ut{h}"] = (D.xau.shift(-h) - D.xau) - (D.gull.shift(-h) - D.gull)
    D[f"spx{h}"] = (D.xau.shift(-h) - D.xau) - (D.spx.shift(-h) - D.spx)
    D[f"gdx{h}"] = (D.gdx.shift(-h) - D.gdx) - (D.gull.shift(-h) - D.gull)
    D[f"auco{h}"] = (D.auco.shift(-h) - D.auco) - (D.gull.shift(-h) - D.gull)


def placebo_p(x, y, n=2000, minsk=24):
    d = pd.concat([x, y], axis=1).dropna()
    a, b = d.iloc[:, 0].rank().values, d.iloc[:, 1].rank().values
    obs = np.corrcoef(a, b)[0, 1]
    null = [np.corrcoef(np.roll(a, rng.integers(minsk, len(a) - minsk)), b)[0, 1] for _ in range(n)]
    z = (obs - np.mean(null)) / np.std(null)
    return obs, 0.5 * (1 - erf(z / sqrt(2))), len(d)


res, alle = [], []
for navn, m in MAAL.items():
    v = (-m).values
    A, Ad, Ar = A_raa(v), A_det(v), A_rull(v)
    T = pd.DataFrame({"maal": m, "A": A, "Ad": Ad, "Ar": Ar}, index=D.index).join(D[[c for c in D if c[:2] in ("ut", "sp", "gd", "au")]])
    T["navn"] = navn
    alle.append(T)
    print(f"==================== {navn}  (A fra {T.A.first_valid_index()})")
    r, pa, n = placebo_p(T.A, T.ut24)
    d = T[["A", "ut24"]].dropna(); mid = pd.Period("2008-01", "M")
    h1 = d[d.index < mid].rank().corr().iloc[0, 1]; h2 = d[d.index >= mid].rank().corr().iloc[0, 1]
    print(f"   rangkorrelasjon A mot ^XAU minus gull 24 mnd: {r:+.2f} (p {pa:.3f}, n {n}); før/etter 2008 {h1:+.2f} / {h2:+.2f}")
    for k in ("Ad", "Ar"):
        print(f"      {k}: {T[k].rank().corr(T.ut24.rank()):+.2f}")
    print(f"      12 mnd: {T.A.rank().corr(T.ut12.rank()):+.2f}; mot S&P 24 mnd: {T.A.rank().corr(T.spx24.rank()):+.2f};"
          f" GDX minus gull 24 mnd: {T.A.rank().corr(T.gdx24.rank()):+.2f}; AUCO.L minus gull 24 mnd: {T.A.rank().corr(T.auco24.rank()):+.2f}")
    z = ((T.A >= 80) & (T.Ad >= 80)).fillna(False)
    inng, sist = [], -99
    for i, x in enumerate(z.values):
        if x:
            if i - sist > 12:
                inng.append(T.index[i])
            sist = i
    kl, start = [], None
    for t in inng:
        if start is None or (t.to_timestamp() - start.to_timestamp()).days > 183:
            start = t; kl.append(t)
    E = T.loc[kl]
    print(f"   bunnsone A og Ad 80+: {int(z.sum())} mnd, {len(kl)} klynger, i sonen nå: {'ja' if z.iloc[-1] else 'nei'}")
    for t, e in E.iterrows():
        print(f"      {t}  A {e.A:3.0f} Ad {e.Ad:3.0f} Ar {e.Ar:3.0f}  ^XAU minus gull 12m {100*e.ut12:+5.0f} % 24m {100*e.ut24:+5.0f} %"
              f"  mot S&P 24m {100*e.spx24:+5.0f} %  GDX minus gull 24m {100*e.gdx24:+5.0f} %")
    Ek = E.dropna(subset=["ut24"]); base = T.ut24.dropna()
    if len(Ek):
        med = Ek.ut24.median()
        null = np.array([np.median(rng.choice(base.values, len(Ek), replace=False)) for _ in range(5000)])
        pz = (np.sum(null >= med) + 1) / 5001
    else:
        med, pz = np.nan, 1.0
    print(f"      klynger med utfall {len(Ek)}: median {100*med:+.0f} % mot tilfeldig {100*base.median():+.0f} % (p {pz:.3f})")
    ok = r > 0 and pa < 0.05 and h1 > 0 and h2 > 0 and len(Ek) >= 4 and med > 0 and med > base.median() and pz < 0.10
    res.append({"maal": navn, "p": max(pa, pz), "ok": ok})
    s = T.dropna(subset=["A"]).iloc[-1]
    print(f"   i dag ({T.dropna(subset=['A']).index[-1]}): A {s.A:.1f}, Ad {s.Ad:.1f}, Ar {s.Ar:.1f}\n")

R = pd.DataFrame(res).sort_values("p").reset_index(drop=True)
mm = len(R)
grense = max([i + 1 for i in range(mm) if R.p[i] <= 0.10 * (i + 1) / mm], default=0)
R["bh"] = [i < grense for i in range(mm)]
print("AVGJØRELSE\n")
for _, r in R.iterrows():
    print(f"   {r.maal}: {'HOLDER' if (r.ok and r.bh) else 'holder ikke'} (største p {r.p:.3f}, BH {'ja' if r.bh else 'nei'})")
pd.concat(alle).reset_index(names="t").to_csv("sonder/miners_feilpris.csv", index=False)
print("\nLagret sonder/miners_feilpris.csv")
