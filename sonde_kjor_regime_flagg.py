# ---------------------------------------------------------------------------
# sonde_kjor_regime_flagg: virker bunnflaggene ulikt i ulike regimer?
# (Frodes bestilling 15.10.2026, steg 3 av regimepanelet)
#
# Flagg: Championens bunnsone (raa A og detrendet A 80 eller mer) for de 18
# raavaresegmentene i serier/priser_mnd.csv, regnet punkt i tid. Ny episode
# etter minst 12 mnd uten flagg; inngang = foerste maaned. Inngangene samles i
# makroklynger som i Shadow-OOS (ny klynge naar inngangen er mer enn 183 dager
# etter klyngens foerste inngang); klyngen er enheten i testen, med median av
# sine episoder og regimet ved klyngens foerste inngang.
#
# Regimet ved inngangen fra sonder/regime.csv (punkt i tid):
#   H1 SJOKK    hoeyeste av VIX-persentil og persentilen til korrelasjonen
#               mellom papirene (fra 2004) er 80 eller mer, mot under 80.
#               Forventet: flagg i uro eller sjokk gir MER.
#   H2 VEKST    bredde (andel raavarer opp over 12 mnd) 0,4 eller lavere, mot
#               over 0,4. Forventet: flagg i bred nedgang gir MER.
#   H3 LIKVIDITET Feds netto likviditet steg siste 13 uker, mot falt (fra
#               2003). Forventet: flagg mens likviditeten stiger gir MER.
# Utfall: realprisens log-endring 24 mnd etter inngang (avgjoer), 12 mnd
# vises. Papirene vises ved siden av (snittet av segmentets papirer paa bordet
# minus SPY, 24 mnd, omvendte papirer og kakao utelatt), avgjoer ikke.
# Inngang fra 1995-01 (VIX-persentil finnes), utfall maa vaere kjent.
#
# KRITERIER (satt foer kjoering, 15.10.2026). En hypotese holder hvis:
#   (a) medianen over klyngene i forventet gruppe er minst 10 prosentpoeng
#       hoeyere enn i den andre,
#   (b) samme fortegn foer og etter 2010 (der begge grupper har klynger),
#   (c) p under 0,10 mot omstokking av regimemerkene mellom klyngene (5000
#       trekk, ensidig), og
#   (d) bestaar Benjamini-Hochberg paa 10 % over de tre hypotesene.
#   Minst tre klynger i hver gruppe, ellers kan hypotesen ikke avgjoeres.
# Holder en, kan den bli en Challenger. Skriver ingenting til dashbordet.
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
                u24 = ser.get(t + 24, np.nan) - lv[i]; u12 = ser.get(t + 12, np.nan) - lv[i]
                if np.isfinite(u24):
                    inng.append({"segment": s, "t": t, "u12": u12, "u24": u24})
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
pap = []
for _, e in E.iterrows():
    v = [k.get(e.t + 24, np.nan) - k.get(e.t, np.nan) for (s, _s), k in kurs.items() if s == e.segment]
    v = [x for x in v if np.isfinite(x)]
    m = spy.get(e.t + 24, np.nan) - spy.get(e.t, np.nan)
    pap.append(np.mean(v) - m if v and np.isfinite(m) else np.nan)
E["pap24"] = pap

# klynger
kl, start = [], None
for t in E.t:
    if start is None or (t.to_timestamp() - start.to_timestamp()).days > 183:
        start = t
    kl.append(str(start))
E["klynge"] = kl
for k in ("sjokk", "bredde", "fed_netto_13u_pst"):
    E[k] = [reg[k].get(t, np.nan) for t in E.t]
K = E.groupby("klynge").agg(t=("t", "first"), n=("segment", "size"), segmenter=("segment", lambda x: ", ".join(x)),
                            u12=("u12", "median"), u24=("u24", "median"), pap24=("pap24", "median")).reset_index()
for k in ("sjokk", "bredde", "fed_netto_13u_pst"):
    K[k] = [reg[k].get(t, np.nan) for t in K.t]

print(f"{len(E)} innganger i {len(K)} klynger, {E.t.min()} til {E.t.max()}\n")
print("1. KLYNGENE (regime ved foerste inngang)\n")
print(f"   {'klynge':8} {'n':>2}  {'sjokk':>5} {'bredde':>6} {'Fed13u':>6}   {'12 mnd':>7} {'24 mnd':>7} {'papir24':>7}  segmenter")
for _, r in K.iterrows():
    print(f"   {r.klynge:8} {r.n:2}  {r.sjokk:5.0f} {r.bredde:6.2f} {r.fed_netto_13u_pst:+6.1f}   "
          f"{100 * r.u12:+6.0f}% {100 * r.u24:+6.0f}% {100 * r.pap24:+6.0f}%  {r.segmenter}")

HYP = {"H1 sjokk (uro eller sjokk mot rolig)": lambda d: d.sjokk >= 80,
       "H2 vekst (bred nedgang mot ikke)": lambda d: d.bredde <= 0.4,
       "H3 likviditet (stigende mot fallende)": lambda d: d.fed_netto_13u_pst > 0}
GYLDIG = {"H1 sjokk (uro eller sjokk mot rolig)": lambda d: d.sjokk.notna(),
          "H2 vekst (bred nedgang mot ikke)": lambda d: d.bredde.notna(),
          "H3 likviditet (stigende mot fallende)": lambda d: d.fed_netto_13u_pst.notna()}
print("\n2. HYPOTESENE (median over klynger, realpris 24 mnd)\n")
res = []
for navn, f in HYP.items():
    d = K[GYLDIG[navn](K)].copy()
    g = f(d).values
    y = d.u24.values
    if g.sum() < 3 or (~g).sum() < 3:
        print(f"   {navn}: for faa klynger ({int(g.sum())} mot {int((~g).sum())}), kan ikke avgjoeres")
        res.append({"navn": navn, "p": 1.0, "ok_abc": False, "avgj": False}); continue
    diff = np.median(y[g]) - np.median(y[~g])
    null = []
    for _ in range(5000):
        gg = rng.permutation(g)
        null.append(np.median(y[gg]) - np.median(y[~gg]))
    pv = (np.sum(np.array(null) >= diff) + 1) / 5001
    halv = []
    for m in (d.t < pd.Period("2010-01", "M"), d.t >= pd.Period("2010-01", "M")):
        a, b = y[m.values & g], y[m.values & ~g]
        halv.append(np.median(a) - np.median(b) if len(a) and len(b) else np.nan)
    b_ok = all(np.isnan(h) or h > 0 for h in halv) and any(np.isfinite(h) for h in halv)
    ok = diff >= 0.10 and b_ok and pv < 0.10
    pd12 = np.median(d.u12.values[g]) - np.median(d.u12.values[~g])
    pp = d.pap24.values
    pdp = np.nanmedian(pp[g]) - np.nanmedian(pp[~g])
    print(f"   {navn}: {int(g.sum())} mot {int((~g).sum())} klynger")
    print(f"      24 mnd: {100 * np.median(y[g]):+.0f} % mot {100 * np.median(y[~g]):+.0f} %, forskjell "
          f"{100 * diff:+.0f} pp (a {'ok' if diff >= 0.10 else 'nei'}); foer/etter 2010 "
          f"{100 * halv[0]:+.0f} / {100 * halv[1]:+.0f} pp (b {'ok' if b_ok else 'nei'}); p {pv:.3f}")
    print(f"      12 mnd forskjell {100 * pd12:+.0f} pp; papirene 24 mnd mot SPY forskjell {100 * pdp:+.0f} pp")
    res.append({"navn": navn, "p": pv, "ok_abc": ok, "avgj": True})

R = pd.DataFrame(res).sort_values("p").reset_index(drop=True)
m = len(R)
grense = max([i + 1 for i in range(m) if R.p[i] <= 0.10 * (i + 1) / m], default=0)
R["bh"] = [i < grense for i in range(m)]
print("\n3. AVGJOERELSE\n")
for _, r in R.iterrows():
    hold = r.ok_abc and r.bh
    print(f"   {r.navn}: {'HOLDER' if hold else ('kan ikke avgjoeres' if not r.avgj else 'holder ikke')}"
          f" (p {r.p:.3f}, BH {'ja' if r.bh else 'nei'})")
E.to_csv("sonder/regime_flagg.csv", index=False)
print("\nLagret sonder/regime_flagg.csv")
