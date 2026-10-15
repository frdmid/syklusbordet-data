# ---------------------------------------------------------------------------
# sonde_kjor_ventetid_hold: kjoep papirene 9 mnd etter at en bred nedgang
# starter, og hold 1, 3, 6, 12 eller 24 mnd (Frodes bestilling 15.10.2026).
#
# Skiftene og kurvene er de samme som i sonde_kjor_regime_ventetid:
#   skifte    bredde (andel raavarer opp over 12 mnd) krysser ned til 0,4
#             eller lavere etter aa ha vaert over, minst 12 mnd mellom skifter
#   PAPIRER   likevektet snitt av maanedlig log-avkastning for papirene paa
#             bordet (omvendte utelatt) og fondene XOP, GDX, COPX, XME, MOO,
#             IEZ, OIH, fra 1990; ogsaa minus SPY
#   RAAVARER  likevektet realpris for de 18 raavaresegmentene (vises)
# Inngang 9 mnd etter skiftet. Utgangspunktet for sammenligning er inngang i
# en tilfeldig maaned med samme holdetid (alle maaneder fra 1990 med kjent
# utfall).
#
# NB: 9 mnd er valgt etter aa ha sett sonde_kjor_regime_ventetid, der 9 mnd
# ga mest for papirene. Testen sier om resultatet holder over holdetidene,
# ikke om 9 mnd er det beste tallet.
#
# KRITERIER (satt foer kjoering, 15.10.2026). En holdetid H holder hvis, for
# papirene (absolutt):
#   (a) medianen etter skiftene er hoeyere enn medianen for alle maaneder,
#   (b) minst to av tre skifter slaar medianen for alle maaneder,
#   (c) p under 0,10 mot tilfeldige inngangsdatoer (samme antall, 5000
#       trekk, ensidig, paa medianen), og
#   (d) bestaar Benjamini-Hochberg paa 10 % over de fem holdetidene.
# Avkastning per aar vises for aa sammenligne holdetidene. Papirene mot SPY
# vises, avgjoer ikke.
# ---------------------------------------------------------------------------

import time
import numpy as np
import pandas as pd
import requests

from instrumenter import INSTR

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
FONDER = ["XOP", "GDX", "COPX", "XME", "MOO", "IEZ", "OIH"]
VENT = 9
HOLD = [1, 3, 6, 12, 24]
rng = np.random.default_rng(20261015)


def mnd_kurs(sym):
    r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}",
                     params={"period1": 0, "period2": int(time.time()), "interval": "1d", "events": "div,split"},
                     headers=UA, timeout=60)
    res = r.json()["chart"]["result"][0]
    if (res.get("meta") or {}).get("dataGranularity") != "1d":
        raise ValueError("ikke dagskurser")
    adj = res["indicators"].get("adjclose", [{}])[0].get("adjclose") or res["indicators"]["quote"][0]["close"]
    s = pd.Series(adj, index=pd.to_datetime(res["timestamp"], unit="s")).dropna()
    s = s[s > 0].resample("ME").last(); s.index = s.index.to_period("M")
    time.sleep(0.3)
    return np.log(s)


reg = pd.read_csv("sonder/regime.csv"); reg.index = pd.PeriodIndex(reg.t, freq="M")
b = reg.bredde.dropna()
skifter, sist, aktiv = [], None, False
for t, x in b.items():
    ny = x <= 0.4
    if ny and not aktiv and b.get(t - 1, 1) > 0.4 and (sist is None or (t - sist).n >= 12):
        skifter.append(t); sist = t
    aktiv = ny

p = pd.read_csv("serier/priser_mnd.csv"); p = p[~p.segment.str.startswith("ship_")]
real = p.pivot(index="t", columns="segment", values="real").astype(float)
real.index = pd.PeriodIndex(real.index, freq="M"); real = real.sort_index()
RAA = np.log(real).diff().mean(axis=1).fillna(0).cumsum()
syms = sorted({x[0] for v in INSTR.values() for x in v if not str(x[4]).startswith("-")} | set(FONDER))
lp = {}
for s in syms:
    try:
        lp[s] = mnd_kurs(s)
    except Exception:
        pass
dr = pd.DataFrame(lp).diff()
dr = dr[dr.index >= pd.Period("1990-01", "M")]
PAP = dr.mean(axis=1).fillna(0).cumsum()
spy = mnd_kurs("SPY")
PAPX = (dr.mean(axis=1) - spy.diff().reindex(dr.index)).fillna(0).cumsum()


def fram(kurv, h):
    return (kurv.shift(-h) - kurv)


inng = [t + VENT for t in skifter if t + VENT >= PAP.index[0] + 1]
print(f"Skifter inn i bred nedgang med papirkurs: {len(inng)}; inngang 9 mnd etter: "
      + ", ".join(str(t) for t in inng) + "\n")

res = []
print(f"   {'hold':>5} {'n':>3} {'median':>8} {'alle mnd':>9} {'slo':>5} {'p':>6} {'per aar':>8} {'alle/aar':>9}"
      f" {'mot SPY':>8} {'raavarer':>9}")
for h in HOLD:
    f = fram(PAP, h); fx = fram(PAPX, h); fr = fram(RAA, h)
    alle = f.dropna()
    y = np.array([f.get(t, np.nan) for t in inng]); ok = np.isfinite(y); y = y[ok]
    base = float(alle.median())
    med = float(np.median(y))
    slo = float((y > base).mean())
    null = np.array([np.median(rng.choice(alle.values, len(y), replace=False)) for _ in range(5000)])
    pv = (np.sum(null >= med) + 1) / 5001
    ok_abc = med > base and slo >= 2 / 3 and pv < 0.10
    mx = np.nanmedian([fx.get(t, np.nan) for t in inng]); mr = np.nanmedian([fr.get(t, np.nan) for t in inng])
    per = 100 * (np.exp(med * 12 / h) - 1); pb = 100 * (np.exp(base * 12 / h) - 1)
    print(f"   {h:4}m {len(y):3} {100 * med:+7.1f}% {100 * base:+8.1f}% {100 * slo:4.0f}% {pv:6.3f} "
          f"{per:+7.1f}% {pb:+8.1f}% {100 * mx:+7.1f}% {100 * mr:+8.1f}%")
    res.append({"hold": h, "n": len(y), "median": med, "alle": base, "slo": slo, "p": pv, "ok_abc": ok_abc,
                "per_aar": per, "alle_per_aar": pb, "mot_spy": mx, "raavarer": mr})

R = pd.DataFrame(res).sort_values("p").reset_index(drop=True)
m = len(R)
grense = max([i + 1 for i in range(m) if R.p[i] <= 0.10 * (i + 1) / m], default=0)
R["bh"] = [i < grense for i in range(m)]
print("\nAVGJOERELSE\n")
for _, r in R.sort_values("hold").iterrows():
    print(f"   hold {r.hold:2} mnd: {'HOLDER' if (r.ok_abc and r.bh) else 'holder ikke'} "
          f"(median {100 * r["median"]:+.1f} % mot {100 * r.alle:+.1f} %, slo {100 * r.slo:.0f} %, p {r.p:.3f}, "
          f"BH {'ja' if r.bh else 'nei'})")

print("\nPER SKIFTE (papirer, absolutt)\n")
print("   inngang  " + "  ".join(f"{h:>6}m" for h in HOLD))
for t in inng:
    print(f"   {t}  " + "  ".join(f"{100 * fram(PAP, h).get(t, np.nan):+6.0f}%" for h in HOLD))
R.to_csv("sonder/ventetid_hold.csv", index=False)
print("\nLagret sonder/ventetid_hold.csv")
