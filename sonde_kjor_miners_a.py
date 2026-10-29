# ---------------------------------------------------------------------------
# sonde_kjor_miners_a: A for gullgruvene fra forholdet gull mot olje
# (Frodes bestilling 28.10.2026, før feltet «miners» bygges)
#
# Serie: gull (nominell USD/unse) delt på WTI (nominell USD/fat), månedlig fra
# serier/priser_mnd.csv (WTI fra 1986). Forholdet er realt i seg selv.
# A, Ad og Ar regnes med de samme formlene som på bordet, på log(forholdet):
# A rå mot hele historikken, Ad mot trenden, Ar mot siste ti år; minst 60 mnd.
# Høy A = gull billig mot olje = presset margin for gruvene.
#
# Utfall: PHLX gull- og sølvgruveindeksen ^XAU (Yahoo, månedsslutt, fra 1985,
# prisindeks), log-endring 24 mnd etter inngang, absolutt og minus S&P 500
# (^GSPC). GDX (fra 2006) og AUCO.L (UCITS, fra 2008) vises for innganger der
# de finnes, avgjør ikke.
#
# Regler (bunnsone som på bordet, ny episode etter minst 12 mnd uten signal,
# inngang = første måned, klynger på 183 dager som i Shadow-OOS):
#   R1 A og Ad 80 eller mer
#   R2 R1 OG forholdet høyere enn for 3 mnd siden (har snudd opp; bygger på
#      sonde_kjor_gullgruver, der endringen i forholdet varslet gruvene)
#
# KRITERIER (satt før kjøring, 28.10.2026). En regel holder hvis:
#   (a) minst 4 klynger med kjent 24 mnd utfall,
#   (b) median over klyngene for ^XAU 24 mnd er høyere enn medianen for like
#       mange tilfeldige innganger, p under 0,10 (5000 trekk, ensidig),
#   (c) median over klyngene for ^XAU minus S&P 500 er positiv,
#   (d) klyngene før og etter 2008 har begge positiv median mot S&P 500 (der
#       begge har klynger), og
#   (e) Benjamini-Hochberg på 10 % over de to reglene.
# Beskrivende i tillegg: rangkorrelasjon mellom A (og Ad) og ^XAU minus
# S&P 500 de neste 24 mnd for alle måneder. Skriver ingenting til dashbordet.
# Utdata sonder/miners_a.csv.
# ---------------------------------------------------------------------------

import time
import numpy as np
import pandas as pd
import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
rng = np.random.default_rng(20261028)
MIN_HIST = 60


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
g = p[p.segment == "gold"].set_index("t").nom.astype(float)
o = p[p.segment == "wti"].set_index("t").nom.astype(float)
f = (g / o).dropna()
f.index = pd.PeriodIndex(f.index, freq="M"); f = f.sort_index()
lf = np.log(f.values)
D = pd.DataFrame({"forhold": f.values, "A": A_raa(lf), "Ad": A_det(lf), "Ar": A_rull(lf)}, index=f.index)
D["opp3"] = D.forhold > D.forhold.shift(3)
xau, spx = mnd("^XAU"), mnd("^GSPC")
gdx, auco = mnd("GDX"), mnd("AUCO.L")
for navn, k in (("xau", xau), ("spx", spx), ("gdx", gdx), ("auco", auco)):
    D[f"{navn}24"] = (k.shift(-24) - k).reindex(D.index)
D["xau_mot_spx"] = D.xau24 - D.spx24
D["gdx_mot_spx"] = D.gdx24 - D.spx24
D["auco_mot_spx"] = D.auco24 - D.spx24
print(f"Forholdet gull mot WTI {D.index[0]} til {D.index[-1]}; A fra {D.A.first_valid_index()}; "
      f"^XAU fra {xau.index[0]}\n")

print("1. BESKRIVENDE: rangkorrelasjon med ^XAU minus S&P 500 de neste 24 mnd (alle måneder)")
d = D.dropna(subset=["A", "Ad", "xau_mot_spx"])
for k in ("A", "Ad", "Ar"):
    print(f"   {k:2}: {d[k].rank().corr(d.xau_mot_spx.rank()):+.2f} (n {len(d)})")
print("   (forventet positiv hvis høy A, gull billig mot olje, er godt for gruvene)\n")

REGLER = {"R1 A og Ad 80+": (D.A >= 80) & (D.Ad >= 80),
          "R2 R1 og forholdet opp siste 3 mnd": (D.A >= 80) & (D.Ad >= 80) & D.opp3}
base = D.xau24.dropna()
res = []
print("2. REGLENE\n")
for navn, z in REGLER.items():
    z = z.fillna(False)
    inng, sist = [], -99
    for i, x in enumerate(z.values):
        if x:
            if i - sist > 12:
                inng.append(D.index[i])
            sist = i
    kl, start = [], None
    for t in inng:
        if start is None or (t.to_timestamp() - start.to_timestamp()).days > 183:
            start = t; kl.append(t)
    E = D.loc[kl]
    print(f"   {navn}: {int(z.sum())} mnd, {len(inng)} episoder, {len(kl)} klynger, i sonen nå: {'ja' if z.iloc[-1] else 'nei'}")
    for t, r in E.iterrows():
        print(f"      {t}  forhold {r.forhold:5.1f}  A {r.A:3.0f} Ad {r.Ad:3.0f} Ar {r.Ar:3.0f}  ^XAU 24m {100*r.xau24:+5.0f} %"
              f"  mot S&P {100*r.xau_mot_spx:+5.0f} %  GDX mot S&P {100*r.gdx_mot_spx:+5.0f} %  AUCO.L mot S&P {100*r.auco_mot_spx:+5.0f} %")
    Ek = E.dropna(subset=["xau24"])
    if len(Ek) == 0:
        res.append({"regel": navn, "p": 1.0, "ok": False}); print(); continue
    med = Ek.xau24.median()
    null = np.array([np.median(rng.choice(base.values, len(Ek), replace=False)) for _ in range(5000)])
    pv = (np.sum(null >= med) + 1) / 5001
    mx = Ek.xau_mot_spx.median()
    f1 = Ek[Ek.index < pd.Period("2008-01", "M")].xau_mot_spx
    f2 = Ek[Ek.index >= pd.Period("2008-01", "M")].xau_mot_spx
    halv = [x.median() for x in (f1, f2) if len(x)]
    ok = len(Ek) >= 4 and med > np.median(base) and pv < 0.10 and mx > 0 and all(h > 0 for h in halv)
    print(f"      klynger med utfall {len(Ek)}: ^XAU median {100*med:+.0f} % mot tilfeldig {100*np.median(base):+.0f} % (p {pv:.3f});"
          f" mot S&P median {100*mx:+.0f} %; før/etter 2008 {100*f1.median() if len(f1) else np.nan:+.0f} / "
          f"{100*f2.median() if len(f2) else np.nan:+.0f} %\n")
    res.append({"regel": navn, "p": pv, "ok": ok})

R = pd.DataFrame(res).sort_values("p").reset_index(drop=True)
m = len(R)
grense = max([i + 1 for i in range(m) if R.p[i] <= 0.10 * (i + 1) / m], default=0)
R["bh"] = [i < grense for i in range(m)]
print("AVGJØRELSE\n")
for _, r in R.iterrows():
    print(f"   {r.regel}: {'HOLDER' if (r.ok and r.bh) else 'holder ikke'} (p {r.p:.3f}, BH {'ja' if r.bh else 'nei'})")

r = D.iloc[-1]
print(f"\nI DAG ({D.index[-1]}): forhold {r.forhold:.1f} fat per unse, A {r.A:.1f}, Ad {r.Ad:.1f}, Ar {r.Ar:.1f}, "
      f"opp siste 3 mnd: {'ja' if r.opp3 else 'nei'}")
D.reset_index(names="t").to_csv("sonder/miners_a.csv", index=False)
print("Lagret sonder/miners_a.csv")
