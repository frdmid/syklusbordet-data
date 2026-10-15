# ---------------------------------------------------------------------------
# sonde_kjor_regime_horisont: de tre regimehypotesene fra sonde_kjor_regime_flagg
# paa kortere horisonter: 1, 3, 6 og 12 mnd (Frodes bestilling 15.10.2026).
#
# Samme flagg, klynger og regimer som sonde_kjor_regime_flagg. Utfall:
# realprisens log-endring h mnd etter inngang, median per klynge. En inngang
# er med paa en horisont naar utfallet paa den horisonten er kjent (saa
# kortere horisonter kan ha flere innganger). Papirene (snitt minus SPY)
# vises, avgjoer ikke.
#
# NB: dette er en utvidelse ETTER at 24 mnd-resultatet var kjent (H2 holdt,
# H1 ga +20 pp paa 12 mnd). Derfor korrigeres det over alle 12 testene.
#
# KRITERIER (satt foer kjoering, 15.10.2026). En hypotese holder paa en
# horisont hvis:
#   (a) medianforskjellen er positiv i forventet retning (10 pp-kravet fra
#       24 mnd passer ikke for 1 mnd),
#   (b) samme fortegn foer og etter 2010 der begge grupper har klynger,
#   (c) p under 0,10 mot omstokking av regimemerkene (5000 trekk, ensidig),
#   (d) bestaar Benjamini-Hochberg paa 10 % over alle 12 testene
#       (3 hypoteser x 4 horisonter),
#   minst tre klynger i hver gruppe.
# ---------------------------------------------------------------------------

import time
import numpy as np
import pandas as pd
import requests

from instrumenter import INSTR

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
rng = np.random.default_rng(20261015)
START = pd.Period("1995-01", "M")
HOR = (1, 3, 6, 12, 24)


def A_raa(v):
    o = np.full(len(v), np.nan)
    for i in range(59, len(v)):
        o[i] = (v[: i + 1] <= v[i]).mean()
    return (1 - o) * 100


def A_det(v):
    o = np.full(len(v), np.nan)
    for i in range(59, len(v)):
        y = v[: i + 1]; t = np.arange(i + 1)
        b, a = np.polyfit(t, y, 1); r = y - (a + b * t)
        o[i] = (r <= r[i]).mean()
    return (1 - o) * 100


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


# ------------------------------------------------------------------ flaggene
p = pd.read_csv("serier/priser_mnd.csv")
p = p[~p.segment.str.startswith("ship_")]
reg = pd.read_csv("sonder/regime.csv"); reg.index = pd.PeriodIndex(reg.t, freq="M")
reg["sjokk"] = reg[["vix_pct", "korr_papirer_pct"]].max(axis=1)
inng = []
for s, g in p.groupby("segment"):
    idx = pd.PeriodIndex(g.t, freq="M"); lv = np.log(g.real.astype(float).values)
    z = (A_raa(lv) >= 80) & (A_det(lv) >= 80)
    ser = pd.Series(lv, index=idx)
    sist = -99
    for i, x in enumerate(z):
        if x:
            if i - sist > 12 and idx[i] >= START:
                t = idx[i]
                rad = {"segment": s, "t": t}
                for h in HOR:
                    rad[f"u{h}"] = ser.get(t + h, np.nan) - lv[i]
                if np.isfinite(rad["u1"]):
                    inng.append(rad)
            sist = i
E = pd.DataFrame(inng).sort_values("t").reset_index(drop=True)

# papirene
spy = mnd_kurs("SPY"); kurs = {}
for s in E.segment.unique():
    if s == "kakao":
        continue
    for x in INSTR.get(s, []):
        if str(x[4]).startswith("-"):
            continue
        try:
            kurs[(s, x[0])] = mnd_kurs(x[0])
        except Exception:
            pass
for h in HOR:
    pap = []
    for _, e in E.iterrows():
        v = [k.get(e.t + h, np.nan) - k.get(e.t, np.nan) for (s, _s), k in kurs.items() if s == e.segment]
        v = [x for x in v if np.isfinite(x)]
        m = spy.get(e.t + h, np.nan) - spy.get(e.t, np.nan)
        pap.append(np.mean(v) - m if v and np.isfinite(m) else np.nan)
    E[f"pap{h}"] = pap

# klynger
kl, start = [], None
for t in E.t:
    if start is None or (t.to_timestamp() - start.to_timestamp()).days > 183:
        start = t
    kl.append(str(start))
E["klynge"] = kl
for k in ("sjokk", "bredde", "fed_netto_13u_pst"):
    E[k] = [reg[k].get(t, np.nan) for t in E.t]
print(f"{len(E)} innganger, {E.t.min()} til {E.t.max()}\n")
HYP = {"H1 sjokk (uro eller sjokk mot rolig)": ("sjokk", lambda d: d.sjokk >= 80),
       "H2 vekst (bred nedgang mot ikke)": ("bredde", lambda d: d.bredde <= 0.4),
       "H3 likviditet (stigende mot fallende)": ("fed_netto_13u_pst", lambda d: d.fed_netto_13u_pst > 0)}
res = []
for h in (1, 3, 6, 12, 24):
    Eh = E[E[f"u{h}"].notna()]
    K = Eh.groupby("klynge").agg(t=("t", "first"), u=(f"u{h}", "median"), pp=(f"pap{h}", "median")).reset_index()
    for k in ("sjokk", "bredde", "fed_netto_13u_pst"):
        K[k] = [reg[k].get(t, np.nan) for t in K.t]
    print(f"==================== {h} mnd ({len(Eh)} innganger, {len(K)} klynger)")
    for navn, (kol, f) in HYP.items():
        d = K[K[kol].notna()]
        g = f(d).values; y = d.u.values
        if g.sum() < 3 or (~g).sum() < 3:
            print(f"   {navn}: for faa klynger ({int(g.sum())} mot {int((~g).sum())})")
            if h != 24:
                res.append({"h": h, "navn": navn, "p": 1.0, "ok": False, "avgj": False})
            continue
        diff = np.median(y[g]) - np.median(y[~g])
        null = np.array([np.median(y[gg]) - np.median(y[~gg]) for gg in (rng.permutation(g) for _ in range(5000))])
        pv = (np.sum(null >= diff) + 1) / 5001
        halv = []
        for m in (d.t < pd.Period("2010-01", "M"), d.t >= pd.Period("2010-01", "M")):
            a, b = y[m.values & g], y[m.values & ~g]
            halv.append(np.median(a) - np.median(b) if len(a) and len(b) else np.nan)
        b_ok = all(np.isnan(x) or x > 0 for x in halv) and any(np.isfinite(x) for x in halv)
        pp = d.pp.values
        pdp = np.nanmedian(pp[g]) - np.nanmedian(pp[~g]) if np.isfinite(pp[g]).any() and np.isfinite(pp[~g]).any() else np.nan
        print(f"   {navn}: {int(g.sum())} mot {int((~g).sum())} klynger; {100 * np.median(y[g]):+.1f} % mot "
              f"{100 * np.median(y[~g]):+.1f} %, forskjell {100 * diff:+.1f} pp; foer/etter 2010 "
              f"{100 * halv[0]:+.1f} / {100 * halv[1]:+.1f} pp; p {pv:.3f}; papirene {100 * pdp:+.1f} pp")
        if h != 24:
            res.append({"h": h, "navn": navn, "p": pv, "ok": diff > 0 and b_ok and pv < 0.10, "avgj": True})
    print()

R = pd.DataFrame(res).sort_values("p").reset_index(drop=True)
m = len(R)
grense = max([i + 1 for i in range(m) if R.p[i] <= 0.10 * (i + 1) / m], default=0)
R["bh"] = [i < grense for i in range(m)]
print("AVGJOERELSE (1, 3, 6 og 12 mnd; 24 mnd vist for sammenligning, avgjort i sonde_kjor_regime_flagg)\n")
for _, r in R.sort_values(["navn", "h"]).iterrows():
    print(f"   {r.navn:40} {r.h:2} mnd: {'HOLDER' if (r.ok and r.bh) else ('kan ikke avgjoeres' if not r.avgj else 'holder ikke')}"
          f" (p {r.p:.3f}, BH {'ja' if r.bh else 'nei'})")
