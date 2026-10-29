# ---------------------------------------------------------------------------
# sonde_kjor_miners_gullregime: oppfører signalene for gullgruvene seg ulikt
# når gullprisen stiger, står stille eller faller? (Frodes bestilling
# 28.10.2026)
#
# Signaler (som i feltet Gullgruver, fra serier/priser_mnd.csv):
#   S1  endring i log(gull/Brent) siste 3 mnd
#   O6  endring i olje-A (Brent realpris, rå A) siste 6 mnd
# Utfall: kurven av gruveaksjer (NEM, Barrick, AEM, GFI, AU, HMY, KGC, AGI,
# IAG, EGO, BVN, likevekt, med utbytte) og ^XAU, minus SPY, de neste 3 og
# 6 mnd, 1993 til 2026. (Inkluderer perioden signalene ble funnet i.)
#
# Gullregime, to klassifiseringer (gull i nominell USD, månedssnitt):
#   ETTERPÅ (beskrivende, bruker framtiden): endringen i gull fra 6 mnd før
#     til 6 mnd etter måneden; over +10 % stigende, under -10 % fallende,
#     ellers stabil. Perioder kortere enn 6 mnd slås sammen med forrige
#     periode, så alle regimer varer minst 6 mnd.
#   SANNTID (kan brukes): endringen i gull siste 6 mnd; over +5 % stigende,
#     under -5 % fallende, ellers stabil. Ingen sammenslåing (kjent da).
#
# KRITERIER (satt før kjøring, 28.10.2026). For hvert signal, horisont og
# klassifisering regnes rangkorrelasjonen mellom signal og utfall innen hvert
# regime. Et signal oppfører seg ulikt hvis, for BÅDE kurven og ^XAU:
#   (a) forskjellen mellom høyeste og laveste regimekorrelasjon er minst 0,20,
#   (b) samme regime er høyest for begge,
#   (c) p under 0,05 for forskjellen mot sirkulært forskjøvet regimeserie
#       (2000 trekk, minst 24 mnd; bevarer hvor lenge regimene varer), og
#   (d) Benjamini-Hochberg på 10 % over 2 signaler x 2 horisonter x 2
#       klassifiseringer = 8 tester (på den største av de to p-verdiene).
# Minst 24 måneder i hvert regime, ellers kan det ikke avgjøres.
# UCITS-fondene GDX.L og GDXJ.L (2015 til 2026) vises, avgjør ikke.
# Skriver ingenting til dashbordet. Utdata sonder/miners_gullregime.csv.
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
REG = ["stigende", "stabil", "fallende"]


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
gull = np.log(serie("gold", "nom"))
ol = serie("brent", "real"); v = np.log(ol.values)
o = np.full(len(v), np.nan)
for i in range(len(v)):
    if i + 1 >= 60:
        o[i] = (v[: i + 1] <= v[i]).sum() / (i + 1)
oljeA = pd.Series((1 - o) * 100, index=ol.index)
gm = gull - np.log(serie("brent", "nom"))
SIG = {"S1 gull mot olje 3 mnd": (gm - gm.shift(3)).dropna(), "O6 olje-A 6 mnd": (oljeA - oljeA.shift(6)).dropna()}

# regimer
def klasse(x, grense):
    return pd.Series(np.where(x > grense, "stigende", np.where(x < -grense, "fallende", "stabil")), index=x.index)[x.notna()]
etter = klasse(gull.shift(-6) - gull.shift(6), np.log(1.10))
# slå sammen perioder kortere enn 6 mnd med forrige periode
lab = etter.values.copy(); i = 0
while i < len(lab):
    j = i
    while j < len(lab) and lab[j] == lab[i]:
        j += 1
    if j - i < 6 and i > 0:
        lab[i:j] = lab[i - 1]
        i = 0  # start på nytt etter sammenslåing
        continue
    i = j
etter = pd.Series(lab, index=etter.index)
sann = klasse(gull - gull.shift(6), np.log(1.05))
KLASS = {"ETTERPÅ": etter, "SANNTID": sann}

px = {s: mnd(s) for s in AKSJER + ["^XAU", "SPY", "GDX.L", "GDXJ.L", "IWDA.L"]}
R = pd.DataFrame({s: px[s] for s in AKSJER}).diff()
kr = R.mean(axis=1, skipna=True); kr[R.notna().sum(axis=1) == 0] = np.nan
PAP = {"KURV": kr.cumsum(), "^XAU": px["^XAU"], "GDX.L": px["GDX.L"], "GDXJ.L": px["GDXJ.L"]}
def ut(k, h):
    ref = px["IWDA.L"] if k in ("GDX.L", "GDXJ.L") else px["SPY"]
    return (PAP[k].shift(-h) - PAP[k]) - (ref.shift(-h) - ref)

print("REGIMENE (antall måneder 1993 til 2026)")
for kn, kl in KLASS.items():
    k = kl[kl.index >= pd.Period("1993-01", "M")]
    runs = (k != k.shift()).cumsum()
    print(f"   {kn:8}: " + ", ".join(f"{r} {int((k == r).sum())} mnd" for r in REG)
          + f"; {runs.nunique()} perioder")
print("   ETTERPÅ, periodene: " + "; ".join(
    f"{g.index[0]}..{g.index[-1]} {g.iloc[0]}" for _, g in etter[etter.index >= pd.Period("1993-01", "M")].groupby((etter != etter.shift()).cumsum())))
print()


def rk(x, y):
    return np.corrcoef(x.rank().values, y.rank().values)[0, 1]


def regimekorr(x, y, reg):
    d = pd.concat([x, y, reg], axis=1, keys=["x", "y", "r"]).dropna()
    out = {}
    for r in REG:
        dd = d[d.r == r]
        out[r] = (rk(dd.x, dd.y), len(dd)) if len(dd) >= 24 else (np.nan, len(dd))
    return out, d


rader, tester = [], []
for sn, sx in SIG.items():
    for h in (3, 6):
        for kn, kl in KLASS.items():
            res = {}
            for k in PAP:
                out, d = regimekorr(sx, ut(k, h), kl)
                d = d[d.index >= pd.Period("1993-01", "M")]
                vals = {r: c for r, (c, n) in out.items() if np.isfinite(c)}
                spenn = max(vals.values()) - min(vals.values()) if len(vals) == 3 else np.nan
                hoy = max(vals, key=vals.get) if vals else None
                pv = np.nan
                if k in ("KURV", "^XAU") and np.isfinite(spenn):
                    rv = d.r.values; null = []
                    for _ in range(2000):
                        rs = np.roll(rv, rng.integers(24, len(rv) - 24))
                        cs = [rk(d.x[rs == r], d.y[rs == r]) for r in REG if (rs == r).sum() >= 24]
                        null.append(max(cs) - min(cs) if len(cs) == 3 else np.nan)
                    null = np.array(null); null = null[np.isfinite(null)]
                    pv = (np.sum(null >= spenn) + 1) / (len(null) + 1)
                res[k] = dict(out=out, spenn=spenn, hoy=hoy, p=pv)
                rader.append({"signal": sn, "h": h, "klass": kn, "papir": k, **{f"r_{r}": out[r][0] for r in REG},
                              **{f"n_{r}": out[r][1] for r in REG}, "spenn": spenn, "hoyest": hoy, "p": pv})
            print(f"{sn}, h {h} mnd, {kn}")
            for k, v in res.items():
                print(f"   {k:7} " + "  ".join(f"{r} {v['out'][r][0]:+.2f} (n {v['out'][r][1]})" for r in REG)
                      + f"  | spenn {v['spenn']:.2f}, høyest {v['hoy']}" + (f", p {v['p']:.3f}" if np.isfinite(v['p']) else ""))
            a, b = res["KURV"], res["^XAU"]
            ok = (np.isfinite(a["spenn"]) and np.isfinite(b["spenn"]) and a["spenn"] >= 0.20 and b["spenn"] >= 0.20
                  and a["hoy"] == b["hoy"] and a["p"] < 0.05 and b["p"] < 0.05)
            tester.append({"test": f"{sn}, h {h}, {kn}", "p": np.nanmax([a["p"], b["p"]]), "ok": ok, "hoy": a["hoy"]})
            print()

T = pd.DataFrame(tester).sort_values("p").reset_index(drop=True)
m = len(T)
grense = max([i + 1 for i in range(m) if T.p[i] <= 0.10 * (i + 1) / m], default=0)
T["bh"] = [i < grense for i in range(m)]
print("AVGJØRELSE: oppfører signalet seg ulikt etter gullregime?\n")
for _, t in T.iterrows():
    print(f"   {t.test:40}: {'JA, sterkest i ' + t.hoy if (t.ok and t.bh) else 'nei'} (største p {t.p:.3f}, BH {'ja' if t.bh else 'nei'})")
print(f"\nI DAG: gull siste 6 mnd {100*(gull.iloc[-1]-gull.iloc[-7]):+.1f} % (log), sanntidsregime: {sann.iloc[-1]}")
pd.DataFrame(rader).to_csv("sonder/miners_gullregime.csv", index=False)
print("Lagret sonder/miners_gullregime.csv")
