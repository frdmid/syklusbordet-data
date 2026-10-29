# ---------------------------------------------------------------------------
# sonde_kjor_miners_dA: varsler endringen i A (den deriverte) gullgruvene, og
# gir den noe ut over signalet gull mot olje? (Frodes spørsmål 28.10.2026)
#
# A-ene regnes som på bordet (rå, detrendet, rullende ti år; minst 60 mnd)
# fra serier/priser_mnd.csv:
#   GULL     realprisen for gull (fra 1971)
#   OLJE     realprisen for Brent (fra 1987)
#   FORHOLD  gull delt på WTI, nominelt (fra 1986), som i feltet Gullgruver
# Høy A = billig. Signalet er endringen i A over k = 1, 3 og 6 mnd.
# Forventet fortegn mot gruvene (satt før kjøring):
#   OLJE positivt   (olje blir billigere, kostnaden faller; det var oljedelen
#                    som bar signalet i sonde_kjor_gullgruver)
#   GULL negativt   (gull blir billigere, inntekten faller)
#   FORHOLD negativt (gull blir billigere mot olje, marginen faller)
# Utfall: fondet minus MSCI World (IWDA.L) de neste h = 3 og 6 mnd, log, fra
# månedsslutt (Yahoo). A bygger på månedssnitt, utfallet på månedsslutt.
# Avgjør på UCITS-fondene GDX.L (store) og GDXJ.L (små), fra 2015.
# Kontroll (avgjør ikke): AUCO.L (UCITS fra 2008) og GDX (USA, fra 2006).
#
# KRITERIER (satt før kjøring, 28.10.2026). Et signal (familie x A-type x k)
# holder på en horisont h hvis, for BÅDE GDX.L og GDXJ.L:
#   (a) rangkorrelasjonen har forventet fortegn, p under 0,05 mot sirkulært
#       forskjøvet signal (2000 trekk, minst 12 mnd, ensidig),
#   (b) samme fortegn i begge halvdelene av perioden, og
#   (c) Benjamini-Hochberg på 10 % over alle 3 x 3 x 3 x 2 = 54 testene, på
#       den største av de to p-verdiene.
# Holder det, spørres i tillegg (d): gir det noe ut over S1 (endringen i log
# gull/olje siste 3 mnd, Yahoo)? Delkorrelasjonen etter at S1 er trukket ut
# (rang) må ha forventet fortegn med p under 0,05 for begge fondene. Holder
# (a) til (c) men ikke (d), er signalet i praksis S1 i en annen drakt.
# Skriver ingenting til dashbordet. Utdata sonder/miners_dA.csv.
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
FOND, KONTROLL = ["GDX.L", "GDXJ.L"], ["AUCO.L", "GDX"]


def A_raa(v):
    o = np.full(len(v), np.nan)
    for i in range(len(v)):
        if i + 1 >= MIN_HIST:
            o[i] = (v[: i + 1] <= v[i]).sum() / (i + 1)
    return (1 - o) * 100


def A_det(v, minn=60):
    o = np.full(len(v), np.nan)
    for i in range(minn - 1, len(v)):
        y = v[: i + 1]; t = np.arange(i + 1)
        b, a = np.polyfit(t, y, 1); r = y - (a + b * t)
        o[i] = (r <= r[i]).sum() / len(r)
    return (1 - o) * 100


def A_rull(v, w=120, minn=60):
    o = np.full(len(v), np.nan)
    for i in range(len(v)):
        lo = max(0, i - w + 1)
        if i - lo + 1 >= minn:
            y = v[lo: i + 1]; o[i] = (y <= v[i]).sum() / len(y)
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
def serie(seg, kol):
    s = p[p.segment == seg].set_index("t")[kol].astype(float)
    s.index = pd.PeriodIndex(s.index, freq="M"); return s.sort_index()
KILDER = {"GULL": serie("gold", "real"), "OLJE": serie("brent", "real"),
          "FORHOLD": (serie("gold", "nom") / serie("wti", "nom")).dropna()}
FORTEGN = {"GULL": -1, "OLJE": 1, "FORHOLD": -1}
A = {}
for fam, s in KILDER.items():
    v = np.log(s.values)
    for typ, fn in (("A", A_raa), ("Ad", A_det), ("Ar", A_rull)):
        A[(fam, typ)] = pd.Series(fn(v), index=s.index)

px = {s: mnd(s) for s in FOND + KONTROLL + ["IWDA.L", "GC=F", "BZ=F"]}
gm = (px["GC=F"] - px["BZ=F"]).dropna()
S1 = gm - gm.shift(3)
UT = {(f, h): (px[f].shift(-h) - px[f]) - (px["IWDA.L"].shift(-h) - px["IWDA.L"]) for f in FOND + KONTROLL for h in (3, 6)}


def placebo(x, y, n=2000, minsk=12):
    a, b = x.rank().values, y.rank().values
    obs = np.corrcoef(a, b)[0, 1]
    null = [np.corrcoef(np.roll(a, rng.integers(minsk, len(a) - minsk)), b)[0, 1] for _ in range(n)]
    z = (obs - np.mean(null)) / np.std(null)
    return obs, z


def p_en(z, fortegn):
    zz = z * fortegn
    return 0.5 * (1 - erf(zz / sqrt(2)))


rader, tester = [], []
for (fam, typ), a in A.items():
    for k in (1, 3, 6):
        sig = a - a.shift(k)
        for h in (3, 6):
            res = {}
            for f in FOND + KONTROLL:
                d = pd.concat([sig, UT[(f, h)], S1], axis=1, keys=["x", "y", "s1"]).dropna()
                if len(d) < 60:
                    continue
                r, z = placebo(d.x, d.y)
                pv = p_en(z, FORTEGN[fam])
                mid = d.index[len(d) // 2]
                h1 = d[d.index < mid][["x", "y"]].rank().corr().iloc[0, 1]
                h2 = d[d.index >= mid][["x", "y"]].rank().corr().iloc[0, 1]
                # delkorrelasjon etter S1 (rang)
                rk = d.rank()
                rx = rk.x - np.polyval(np.polyfit(rk.s1, rk.x, 1), rk.s1)
                ry = rk.y - np.polyval(np.polyfit(rk.s1, rk.y, 1), rk.s1)
                rp, zp = placebo(pd.Series(rx.values), pd.Series(ry.values))
                res[f] = dict(r=r, p=pv, h1=h1, h2=h2, rpart=rp, ppart=p_en(zp, FORTEGN[fam]), n=len(d))
                rader.append({"familie": fam, "type": typ, "k": k, "h": h, "fond": f, **res[f]})
            if all(f in res for f in FOND):
                s = FORTEGN[fam]
                ok = all(res[f]["r"] * s > 0 and res[f]["p"] < 0.05 and res[f]["h1"] * s > 0 and res[f]["h2"] * s > 0 for f in FOND)
                ny = all(res[f]["rpart"] * s > 0 and res[f]["ppart"] < 0.05 for f in FOND)
                tester.append({"signal": f"{fam} {typ} k={k}", "h": h, "p": max(res[f]["p"] for f in FOND), "ok": ok, "ny": ny,
                               "txt": "  ".join(f"{f} r{res[f]['r']:+.2f} p{res[f]['p']:.3f} ({res[f]['h1']:+.2f}/{res[f]['h2']:+.2f}) del{res[f]['rpart']:+.2f}"
                                                for f in FOND + KONTROLL if f in res)})

T = pd.DataFrame(tester).sort_values("p").reset_index(drop=True)
m = len(T)
grense = max([i + 1 for i in range(m) if T.p[i] <= 0.10 * (i + 1) / m], default=0)
T["bh"] = [i < grense for i in range(m)]
T["holder"] = T.ok & T.bh
print(f"{m} tester. Forventet fortegn: OLJE +, GULL -, FORHOLD -. Utfall: fond minus MSCI World.\n")
for fam in ("OLJE", "GULL", "FORHOLD"):
    print(f"==================== {fam}")
    for _, t in T[T.signal.str.startswith(fam)].sort_values(["signal", "h"]).iterrows():
        status = ("HOLDER, og gir noe ut over S1" if t.ny else "HOLDER, men er S1 i annen drakt") if t.holder else "holder ikke"
        print(f"   {t.signal:16} h={t.h}: {status:34} (største p {t.p:.3f}, BH {'ja' if t.bh else 'nei'})")
        print(f"      {t.txt}")
    print()
print("OPPSUMMERING: " + (", ".join(f"{t.signal} h={t.h}{' (ny)' if t.ny else ''}" for _, t in T[T.holder].iterrows()) or "ingen holder"))
print("\nI DAG (endring i A siste 3 mnd):")
for fam in ("OLJE", "GULL", "FORHOLD"):
    print("   " + fam + ": " + ", ".join(f"{typ} {A[(fam, typ)].iloc[-1] - A[(fam, typ)].iloc[-4]:+.1f} (nå {A[(fam, typ)].iloc[-1]:.1f})" for typ in ("A", "Ad", "Ar")))
pd.DataFrame(rader).to_csv("sonder/miners_dA.csv", index=False)
print("\nLagret sonder/miners_dA.csv")
