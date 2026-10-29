# ---------------------------------------------------------------------------
# sonde_kjor_miners_kurv: holder olje-signalet for gullgruvene på en kurv av
# gruveaksjer med lang historikk? (Frodes bestilling 28.10.2026)
#
# Signalet ble funnet på UCITS-fondene 2015 til 2026 (sonde_kjor_miners_dA):
# endringen i olje-A (Brent realpris, rå A som på bordet) over 6 mnd varslet
# gruvefondene minus MSCI World de neste 3 og 6 mnd. Denne testen AVGJØRES på
# 1992 til 2014, altså før perioden signalet ble funnet i: en test utenfor
# utvalget. Signaldatoer til og med 2014-06, så utfallene slutter før 2015.
#
# Papirer (Yahoo, månedsslutt, utbyttejustert, USD):
#   KURV  likevekt av de aksjene som finnes hver måned:
#         store: NEM, B (Barrick), AEM, GFI, AU, HMY, KGC
#         mindre (fra 2003): AGI, IAG, EGO, BVN
#         Bare overlevende selskaper (overlevelsesskjevhet), derfor også:
#   ^XAU  PHLX gull- og sølvgruveindeksen (prisindeks, fra 1985), som også
#         rommer selskaper som senere forsvant.
# Marked: SPY (S&P 500 med utbytte, fra 1993). Utfall: papir minus SPY, log,
# de neste h = 3 og 6 mnd.
#
# Signaler (fra serier/priser_mnd.csv, månedssnitt):
#   O6  endring i olje-A over 6 mnd (forventet positiv; hovedsignalet)
#   S1  endring i log(gull/Brent) over 3 mnd (forventet positiv; det første
#       signalet, her på månedssnitt i stedet for Yahoo-terminer)
#
# KRITERIER (satt før kjøring, 28.10.2026). Et signal holder på en horisont h
# hvis, i 1992 til 2014 og for BÅDE kurven og ^XAU:
#   (a) rangkorrelasjonen er positiv med p under 0,05 mot sirkulært forskjøvet
#       signal (2000 trekk, minst 12 mnd, ensidig),
#   (b) positiv i begge halvdelene (1992 til 2003 og 2003 til 2014),
#   (c) beste mot svakeste tredjedel av månedene minst 2 prosentpoeng per
#       3 mnd (snitt av kurven og ^XAU), og
#   (d) Benjamini-Hochberg på 10 % over 2 signaler x 2 horisonter (på den
#       største av de to p-verdiene).
# 2015 til 2026 og hele perioden vises, avgjør ikke. Skriver ingenting til
# dashbordet. Utdata sonder/miners_kurv.csv.
# ---------------------------------------------------------------------------

import time
from math import erf, sqrt
import numpy as np
import pandas as pd
import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
rng = np.random.default_rng(20261028)
STORE = ["NEM", "B", "AEM", "GFI", "AU", "HMY", "KGC"]
MINDRE = ["AGI", "IAG", "EGO", "BVN"]
MIN_HIST = 60
UTVALG = (pd.Period("1992-01", "M"), pd.Period("2014-06", "M"))


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
olje = serie("brent", "real"); v = np.log(olje.values)
o = np.full(len(v), np.nan)
for i in range(len(v)):
    if i + 1 >= MIN_HIST:
        o[i] = (v[: i + 1] <= v[i]).sum() / (i + 1)
oljeA = pd.Series((1 - o) * 100, index=olje.index)
gm = np.log(serie("gold", "nom") / serie("brent", "nom")).dropna()
SIG = {"O6 olje-A endring 6 mnd": oljeA - oljeA.shift(6), "S1 gull mot olje 3 mnd": gm - gm.shift(3)}

px = {s: mnd(s) for s in STORE + MINDRE + ["^XAU", "SPY"]}
R = pd.DataFrame({s: px[s] for s in STORE + MINDRE}).diff()
def kurv(navn):
    r = R[navn].mean(axis=1, skipna=True)
    r[R[navn].notna().sum(axis=1) == 0] = np.nan
    return r.cumsum()
PAP = {"KURV": kurv(STORE + MINDRE), "KURV store": kurv(STORE), "KURV mindre": kurv(MINDRE), "^XAU": px["^XAU"]}
spy = px["SPY"]
UT = {(k, h): (s.shift(-h) - s) - (spy.shift(-h) - spy) for k, s in PAP.items() for h in (3, 6)}


def test(x, y, fra, til):
    d = pd.concat([x, y], axis=1, keys=["x", "y"]).dropna()
    d = d[(d.index >= fra) & (d.index <= til)]
    if len(d) < 36:
        return None
    a, b = d.x.rank().values, d.y.rank().values
    r = np.corrcoef(a, b)[0, 1]
    null = [np.corrcoef(np.roll(a, rng.integers(12, len(a) - 12)), b)[0, 1] for _ in range(2000)]
    z = (r - np.mean(null)) / np.std(null); pv = 0.5 * (1 - erf(z / sqrt(2)))
    mid = d.index[len(d) // 2]
    h1 = d[d.index < mid].rank().corr().iloc[0, 1]; h2 = d[d.index >= mid].rank().corr().iloc[0, 1]
    q = d.x.quantile([1 / 3, 2 / 3]).values
    spr = d.y[d.x >= q[1]].mean() - d.y[d.x <= q[0]].mean()
    return dict(r=r, p=pv, h1=h1, h2=h2, spr=spr, n=len(d), fra=str(d.index[0]), til=str(d.index[-1]))


PERIODER = {"1992-2014 (avgjør)": UTVALG, "2015-2026": (pd.Period("2015-01", "M"), pd.Period("2026-12", "M")),
            "hele": (pd.Period("1992-01", "M"), pd.Period("2026-12", "M"))}
rader, tester = [], []
for sn, sx in SIG.items():
    print(f"==================== {sn}")
    for h in (3, 6):
        print(f"   h = {h} mnd")
        res = {}
        for pn, (fra, til) in PERIODER.items():
            for k in PAP:
                t = test(sx, UT[(k, h)], fra, til)
                if t is None:
                    continue
                rader.append({"signal": sn, "h": h, "periode": pn, "papir": k, **t})
                res[(pn, k)] = t
                print(f"      {pn:18} {k:12} r {t['r']:+.2f} p {t['p']:.3f}  halvdeler {t['h1']:+.2f}/{t['h2']:+.2f}"
                      f"  topp mot bunn {100*t['spr']*3/h:+5.1f} pp per 3 mnd  n {t['n']} ({t['fra']}..{t['til']})")
        a, b = res.get(("1992-2014 (avgjør)", "KURV")), res.get(("1992-2014 (avgjør)", "^XAU"))
        if a and b:
            ok = all(t["r"] > 0 and t["p"] < 0.05 and t["h1"] > 0 and t["h2"] > 0 for t in (a, b)) and \
                 (a["spr"] + b["spr"]) / 2 * 3 / h >= 0.02
            tester.append({"signal": sn, "h": h, "p": max(a["p"], b["p"]), "ok": ok})
    print()

T = pd.DataFrame(tester).sort_values("p").reset_index(drop=True)
m = len(T)
grense = max([i + 1 for i in range(m) if T.p[i] <= 0.10 * (i + 1) / m], default=0)
T["bh"] = [i < grense for i in range(m)]
print("AVGJØRELSE (1992 til 2014, utenfor perioden signalet ble funnet i)\n")
for _, t in T.sort_values(["signal", "h"]).iterrows():
    print(f"   {t.signal:26} h={t.h}: {'HOLDER' if (t.ok and t.bh) else 'holder ikke'} (største p {t.p:.3f}, BH {'ja' if t.bh else 'nei'})")
print(f"\nI DAG: olje-A {oljeA.iloc[-1]:.1f}, endring 6 mnd {SIG['O6 olje-A endring 6 mnd'].iloc[-1]:+.1f}; "
      f"gull mot olje 3 mnd {100*SIG['S1 gull mot olje 3 mnd'].iloc[-1]:+.1f} % (månedssnitt til {oljeA.index[-1]})")
pd.DataFrame(rader).to_csv("sonder/miners_kurv.csv", index=False)
print("Lagret sonder/miners_kurv.csv")
