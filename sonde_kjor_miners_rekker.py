# ---------------------------------------------------------------------------
# sonde_kjor_miners_rekker: betyr det noe hvor mange måneder på rad et
# gruvesignal har stått? (Frodes spørsmål 28.10.2026)
#
# Signalpunktene som i grafen i feltet Gullgruver: en måned har punkt når
# signalet er i øverste tredjedel mot det som var kjent da (minst 36 mnd).
#   S1  endring i log(gull/Brent) siste 3 mnd (månedssnitt, priser_mnd)
#   O6  endring i olje-A siste 6 mnd
# Rekke = antall måneder på rad med punkt, til og med denne måneden (1, 2, ...).
# Utfall: kurven av gruveaksjer og ^XAU minus SPY de neste 3 og 6 mnd,
# 1993 til 2026. UCITS GDX.L og GDXJ.L minus MSCI World vises (2015 til 2026).
#
# KRITERIER (satt før kjøring, 28.10.2026). Blant månedene med punkt holder
# «lengre rekke gir sterkere signal» for et signal og en horisont hvis, for
# BÅDE kurven og ^XAU:
#   (a) rangkorrelasjonen mellom rekkelengde og utfall er positiv med p under
#       0,05 mot sirkulært forskjøvet punktserie (2000 trekk, minst 24 mnd;
#       rekkene regnes på nytt for hvert trekk),
#   (b) snittet for rekker på 3 mnd eller mer er høyere enn for rekker på
#       1 mnd, og
#   (c) Benjamini-Hochberg på 10 % over 2 signaler x 2 horisonter.
# Holder det motsatte (kortere rekke sterkere), rapporteres det som funn i
# motsatt retning, uten krav. Beskrivende i tillegg: begge signalene samme
# måned mot bare ett mot ingen. Skriver ingenting til dashbordet.
# Utdata sonder/miners_rekker.csv.
# ---------------------------------------------------------------------------

import time
from math import erf, sqrt
import numpy as np
import pandas as pd
import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
rng = np.random.default_rng(20261028)
AKSJER = ["NEM", "B", "AEM", "GFI", "AU", "HMY", "KGC", "AGI", "IAG", "EGO", "BVN"]


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


def rekker(on):
    r, n = [], 0
    for x in on:
        n = n + 1 if x == 1 else 0
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
PUNKT = {"S1 gull mot olje 3 mnd": toppen((gm - gm.shift(3)).dropna()),
         "O6 olje-A 6 mnd": toppen((oljeA - oljeA.shift(6)).dropna())}

px = {s: mnd(s) for s in AKSJER + ["^XAU", "SPY", "GDX.L", "GDXJ.L", "IWDA.L"]}
R = pd.DataFrame({s: px[s] for s in AKSJER}).diff()
kr = R.mean(axis=1, skipna=True); kr[R.notna().sum(axis=1) == 0] = np.nan
PAP = {"KURV": kr.cumsum(), "^XAU": px["^XAU"], "GDX.L": px["GDX.L"], "GDXJ.L": px["GDXJ.L"]}
def ut(k, h):
    ref = px["IWDA.L"] if k in ("GDX.L", "GDXJ.L") else px["SPY"]
    return (PAP[k].shift(-h) - PAP[k]) - (ref.shift(-h) - ref)


def rk(a, b):
    return np.corrcoef(pd.Series(a).rank().values, pd.Series(b).rank().values)[0, 1]


rader, tester = [], []
for sn, pk in PUNKT.items():
    print(f"==================== {sn}")
    for h in (3, 6):
        print(f"   h = {h} mnd")
        res = {}
        for k in PAP:
            d = pd.concat([pk, ut(k, h)], axis=1, keys=["on", "y"]).dropna()
            d = d[d.index >= pd.Period("1993-01", "M")]
            if len(d) < 60:
                continue
            d["rekke"] = rekker(d.on.values)
            on = d[d.rekke > 0]
            r = rk(on.rekke, on.y)
            grp = {"av": d[d.rekke == 0].y, "1": on[on.rekke == 1].y, "2": on[on.rekke == 2].y,
                   "3-5": on[(on.rekke >= 3) & (on.rekke <= 5)].y, "6+": on[on.rekke >= 6].y}
            pv = np.nan
            if k in ("KURV", "^XAU"):
                null = []
                onv, yv = d.on.values, d.y.values
                for _ in range(2000):
                    s = np.roll(onv, rng.integers(24, len(onv) - 24)); rr = rekker(s)
                    m = rr > 0
                    null.append(rk(rr[m], yv[m]) if m.sum() > 10 else np.nan)
                null = np.array(null); null = null[np.isfinite(null)]
                z = (r - null.mean()) / null.std(); pv = 0.5 * (1 - erf(z / sqrt(2)))
            res[k] = dict(r=r, p=pv, grp=grp, n=len(on))
            snitt = "  ".join(f"{g} {100*x.mean():+5.1f}% (n {len(x)})" for g, x in grp.items() if len(x))
            print(f"      {k:7} r(rekke, utfall) {r:+.2f}" + (f" p {pv:.3f}" if np.isfinite(pv) else "") + f"  | {snitt}")
            rader.append({"signal": sn, "h": h, "papir": k, "r": r, "p": pv, **{f"snitt_{g}": x.mean() for g, x in grp.items()},
                          **{f"n_{g}": len(x) for g, x in grp.items()}})
        a, b = res["KURV"], res["^XAU"]
        ok = all(t["r"] > 0 and t["p"] < 0.05 and t["grp"]["3-5"].append(t["grp"]["6+"]).mean() > t["grp"]["1"].mean() for t in (a, b))
        mot = all(t["r"] < 0 and (1 - t["p"]) < 0.05 for t in (a, b))
        tester.append({"test": f"{sn}, h {h}", "p": max(a["p"], b["p"]), "ok": ok, "mot": mot})
    print()

print("==================== Begge signalene samme måned (beskrivende)")
d0 = pd.concat(PUNKT.values(), axis=1, keys=["s1", "o6"]).dropna()
for h in (3, 6):
    for k in ("KURV", "^XAU", "GDX.L", "GDXJ.L"):
        d = pd.concat([d0, ut(k, h)], axis=1).dropna(); d.columns = ["s1", "o6", "y"]
        d = d[d.index >= pd.Period("1993-01", "M")]
        ant = d.s1 + d.o6
        print(f"   h {h} {k:7}: " + "  ".join(f"{int(a)} signal {100*d.y[ant == a].mean():+5.1f}% (n {int((ant == a).sum())})" for a in (0, 1, 2)))

T = pd.DataFrame(tester).sort_values("p").reset_index(drop=True)
m = len(T)
grense = max([i + 1 for i in range(m) if T.p[i] <= 0.10 * (i + 1) / m], default=0)
T["bh"] = [i < grense for i in range(m)]
print("\nAVGJØRELSE: gir lengre rekke sterkere signal?\n")
for _, t in T.iterrows():
    print(f"   {t.test:30}: {'JA' if (t.ok and t.bh) else ('nei, heller motsatt' if t.mot else 'nei')} (største p {t.p:.3f}, BH {'ja' if t.bh else 'nei'})")
pd.DataFrame(rader).to_csv("sonder/miners_rekker.csv", index=False)
print("\nLagret sonder/miners_rekker.csv")
