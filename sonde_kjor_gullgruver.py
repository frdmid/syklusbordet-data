# ---------------------------------------------------------------------------
# sonde_kjor_gullgruver: følger gullgruvene gullprisen opp og oljeprisen
# motsatt vei, og gir det et signal? (Frodes hypotese 28.10.2026)
#
# Papirer (UCITS, notert i USD i London, Yahoo):
#   STORE   GDX.L  VanEck Gold Miners UCITS (fra 2015)
#           IAUP.L iShares Gold Producers UCITS (fra 2011)
#   SMÅ     GDXJ.L VanEck Junior Gold Miners UCITS (fra 2015)
#   BLANDET AUCO.L L&G Gold Mining UCITS (fra 2008)
#   Kontroll med lengre historikk (ikke UCITS, avgjør ikke): GDX (2006),
#   GDXJ (2009).
# Faktorer: gull GC=F, olje Brent BZ=F (WTI CL=F før 2007-08), verden IWDA.L
# (MSCI World UCITS). Alle i USD, dagskurser, ukeslutt og månedsslutt.
#
# DEL 1, SAMTIDIG (beskrivende): ukeavkastning (log) for hvert fond mot gull,
# olje og verden samtidig. Hypotesen sier beta mot gull over 1 og beta mot
# olje under 0 når gull og marked holdes fast. Viser også beta i uker med
# stigende og fallende gull (følger de gullet opp mer enn ned?), og olje-beta
# rullende over 104 uker.
#
# DEL 2, SIGNAL (kriterier satt før kjøring, 28.10.2026). Tre signaler ved
# månedsslutt t, utfall = fondets avkastning de neste h mnd minus MSCI World
# (IWDA.L), h = 1, 3 og 6:
#   S1 marginen: endring i log(gull/olje) siste 3 mnd (gull stiger mot
#      oljen = bedre margin for gruvene). Forventet positiv.
#   S2 etterslep: hvor mye fondet har gått mindre enn gull og olje tilsier de
#      siste 3 mnd (betaene fra del 1, regnet bare på data før t), med motsatt
#      fortegn. Forventet positiv (gruvene tar igjen).
#   S3 gulltrend: gullets avkastning siste 3 mnd. Forventet positiv.
# Et signal holder på en horisont hvis, for de UCITS-fondene som har minst 60
# måneder med utfall:
#   (a) rangkorrelasjonen er positiv for både GDX.L (store) og GDXJ.L (små),
#   (b) samme fortegn i begge halvdelene av perioden for begge,
#   (c) p under 0,05 mot sirkulært forskjøvet signal (2000 trekk, minst 12
#       mnd, ensidig) for begge, og
#   (d) de beste tredjedelene av månedene ga minst 2 prosentpoeng mer per
#       3 mnd enn de svakeste tredjedelene (snitt av GDX.L og GDXJ.L),
#   (e) Benjamini-Hochberg på 10 % over 3 signaler x 3 horisonter (på den
#       største p-verdien av de to fondene).
# IAUP.L, AUCO.L og de amerikanske vises som kontroll. Skriver ingenting til
# dashbordet. Utdata sonder/gullgruver.csv.
# ---------------------------------------------------------------------------

import time
import numpy as np
import pandas as pd
import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
STORE, SMAA, BLAND, KONTROLL = ["GDX.L", "IAUP.L"], ["GDXJ.L"], ["AUCO.L"], ["GDX", "GDXJ"]
FOND = STORE + SMAA + BLAND + KONTROLL
rng = np.random.default_rng(20261028)


def dag(sym):
    r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}",
                     params={"period1": 0, "period2": int(time.time()), "interval": "1d", "events": "div,split"},
                     headers=UA, timeout=60)
    res = r.json()["chart"]["result"][0]
    if (res.get("meta") or {}).get("dataGranularity") != "1d":
        raise ValueError(f"{sym}: ikke dagskurser")
    if res["meta"].get("currency") != "USD":
        raise ValueError(f"{sym}: valuta {res['meta'].get('currency')}")
    adj = res["indicators"].get("adjclose", [{}])[0].get("adjclose") or res["indicators"]["quote"][0]["close"]
    s = pd.Series(adj, index=pd.to_datetime(res["timestamp"], unit="s").normalize()).dropna()
    time.sleep(0.3)
    return s[s > 0]


px = {s: dag(s) for s in FOND + ["GC=F", "BZ=F", "CL=F", "IWDA.L"]}
olje = px["BZ=F"].combine_first(px["CL=F"][px["CL=F"].index < px["BZ=F"].index[0]])
D = pd.DataFrame({**{s: px[s] for s in FOND}, "gull": px["GC=F"], "olje": olje, "verden": px["IWDA.L"]}).sort_index()
D = D.ffill(limit=3)
U = np.log(D.resample("W-FRI").last()).diff()
M = np.log(D.resample("ME").last())
M.index = M.index.to_period("M")
U = U.replace([np.inf, -np.inf], np.nan)


def ols(y, X):
    d = pd.concat([y, X], axis=1).dropna()
    if len(d) < 52:
        return None
    A = np.column_stack([np.ones(len(d)), d.iloc[:, 1:].values])
    b, *_ = np.linalg.lstsq(A, d.iloc[:, 0].values, rcond=None)
    res = d.iloc[:, 0].values - A @ b
    # Newey-West-feil med 4 ukers etterslep
    n, k = A.shape
    XtXi = np.linalg.inv(A.T @ A)
    S = (A * res[:, None]).T @ (A * res[:, None])
    for L in range(1, 5):
        w = 1 - L / 5
        G = (A[L:] * res[L:, None]).T @ (A[:-L] * res[:-L, None])
        S += w * (G + G.T)
    se = np.sqrt(np.diag(XtXi @ S @ XtXi))
    r2 = 1 - res.var() / d.iloc[:, 0].var()
    return b, se, len(d), r2


print("DEL 1. SAMTIDIG: ukeavkastning mot gull, olje og verden (Newey-West t)\n")
print(f"   {'fond':7} {'uker':>5} {'fra':>8} {'b gull':>7} {'t':>5} {'b olje':>7} {'t':>5} {'b verden':>8} {'t':>5} {'R2':>5}"
      f" {'gull opp':>8} {'gull ned':>8}")
del1 = {}
for s in FOND:
    r = ols(U[s], U[["gull", "olje", "verden"]])
    if r is None:
        continue
    b, se, n, r2 = r
    opp = ols(U[s][U.gull > 0], U[["gull", "olje", "verden"]][U.gull > 0])
    ned = ols(U[s][U.gull < 0], U[["gull", "olje", "verden"]][U.gull < 0])
    fra = U[s].dropna().index[0].strftime("%Y-%m")
    del1[s] = b
    print(f"   {s:7} {n:5} {fra:>8} {b[1]:7.2f} {b[1]/se[1]:5.1f} {b[2]:7.2f} {b[2]/se[2]:5.1f} {b[3]:8.2f} {b[3]/se[3]:5.1f}"
          f" {r2:5.2f} {opp[0][1] if opp else np.nan:8.2f} {ned[0][1] if ned else np.nan:8.2f}")

print("\n   Olje-beta rullende 104 uker (gull og verden holdt fast), GDX og GDX.L, ved årsslutt:")
for s in ("GDX", "GDX.L", "GDXJ.L"):
    rad = []
    for t in pd.date_range("2009-12-31", U.index[-1], freq="YE"):
        w = U.loc[t - pd.Timedelta(weeks=104): t]
        r = ols(w[s], w[["gull", "olje", "verden"]])
        if r:
            rad.append(f"{t.year}:{r[0][2]:+.2f}")
    print(f"      {s:7} " + " ".join(rad))

print("\n   Uten verden (bare gull og olje), hele perioden:")
for s in FOND:
    r = ols(U[s], U[["gull", "olje"]])
    if r:
        print(f"      {s:7} b gull {r[0][1]:.2f}  b olje {r[0][2]:+.2f} (t {r[0][2]/r[1][2]:+.1f})")

# ------------------------------------------------------------------ del 2
print("\n\nDEL 2. SIGNAL: neste h mnd, fond minus MSCI World\n")
mg = M.gull - M.olje
S1 = mg - mg.shift(3)
S3 = M.gull - M.gull.shift(3)


def etterslep(s):
    """Faktisk 3 mnd avkastning minus det gull og olje tilsa, betaer fra
    månedsdata før t (minst 36 mnd), med motsatt fortegn."""
    dm = M.diff()
    ut = pd.Series(np.nan, index=M.index)
    for i in range(len(M)):
        hist = dm.iloc[:i][[s, "gull", "olje"]].dropna()
        if len(hist) < 36 or i < 3:
            continue
        A = np.column_stack([np.ones(len(hist)), hist[["gull", "olje"]].values])
        b, *_ = np.linalg.lstsq(A, hist[s].values, rcond=None)
        r3 = M[s].iloc[i] - M[s].iloc[i - 3]
        g3 = M.gull.iloc[i] - M.gull.iloc[i - 3]
        o3 = M.olje.iloc[i] - M.olje.iloc[i - 3]
        if np.isfinite([r3, g3, o3]).all():
            ut.iloc[i] = -(r3 - (3 * b[0] + b[1] * g3 + b[2] * o3))
    return ut


def placebo_p(x, y, n=2000, minsk=12):
    d = pd.concat([x, y], axis=1).dropna()
    a, b = d.iloc[:, 0].rank().values, d.iloc[:, 1].rank().values
    obs = np.corrcoef(a, b)[0, 1]
    null = [np.corrcoef(np.roll(a, rng.integers(minsk, len(a) - minsk)), b)[0, 1] for _ in range(n)]
    z = (obs - np.mean(null)) / np.std(null)
    from math import erf, sqrt
    return obs, 0.5 * (1 - erf(z / sqrt(2))), len(d)


rader, tester = [], []
for sname, sfun in (("S1 margin (gull mot olje 3 mnd)", lambda s: S1), ("S2 etterslep mot gull og olje", etterslep),
                    ("S3 gulltrend 3 mnd", lambda s: S3)):
    print(f"   {sname}")
    for h in (1, 3, 6):
        res = {}
        for s in FOND:
            x = sfun(s)
            y = (M[s].shift(-h) - M[s]) - (M.verden.shift(-h) - M.verden)
            d = pd.concat([x, y], axis=1).dropna()
            if len(d) < 60:
                continue
            r, p, n = placebo_p(d.iloc[:, 0], d.iloc[:, 1])
            mid = d.index[len(d) // 2]
            h1 = d[d.index < mid].rank().corr().iloc[0, 1]
            h2 = d[d.index >= mid].rank().corr().iloc[0, 1]
            q = d.iloc[:, 0].quantile([1 / 3, 2 / 3]).values
            topp = d.iloc[:, 1][d.iloc[:, 0] >= q[1]].mean(); bunn = d.iloc[:, 1][d.iloc[:, 0] <= q[0]].mean()
            spr = (topp - bunn) * 3 / h
            res[s] = (r, p, h1, h2, spr, n)
            rader.append({"signal": sname, "h": h, "fond": s, "r": r, "p": p, "h1": h1, "h2": h2, "spread_3m": spr, "n": n})
        linje = "  ".join(f"{s} r{v[0]:+.2f} p{v[1]:.2f} ({v[2]:+.2f}/{v[3]:+.2f}) {100*v[4]:+.1f}pp n{v[5]}" for s, v in res.items())
        print(f"      {h} mnd: {linje}")
        if "GDX.L" in res and "GDXJ.L" in res:
            a, b = res["GDX.L"], res["GDXJ.L"]
            ok = (a[0] > 0 and b[0] > 0 and min(a[2], a[3], b[2], b[3]) > 0 and a[1] < 0.05 and b[1] < 0.05
                  and (a[4] + b[4]) / 2 >= 0.02)
            tester.append({"signal": sname, "h": h, "p": max(a[1], b[1]), "ok": ok})
    print()

T = pd.DataFrame(tester).sort_values("p").reset_index(drop=True)
m = len(T)
grense = max([i + 1 for i in range(m) if T.p[i] <= 0.10 * (i + 1) / m], default=0)
T["bh"] = [i < grense for i in range(m)]
print("AVGJØRELSE (UCITS: GDX.L store og GDXJ.L små)\n")
for _, t in T.sort_values(["signal", "h"]).iterrows():
    print(f"   {t.signal:34} {t.h} mnd: {'HOLDER' if (t.ok and t.bh) else 'holder ikke'} (største p {t.p:.3f}, BH {'ja' if t.bh else 'nei'})")

print("\nI DAG")
s1, s3 = S1.dropna(), S3.dropna()
print(f"   S1 margin siste 3 mnd: {100*s1.iloc[-1]:+.1f} % (persentil {100*(s1 <= s1.iloc[-1]).mean():.0f} siden {s1.index[0]})")
print(f"   S3 gull siste 3 mnd: {100*s3.iloc[-1]:+.1f} % (persentil {100*(s3 <= s3.iloc[-1]).mean():.0f})")
for s in ("GDX.L", "GDXJ.L"):
    e = etterslep(s).dropna()
    print(f"   S2 etterslep {s}: {100*e.iloc[-1]:+.1f} % (persentil {100*(e <= e.iloc[-1]).mean():.0f})")
pd.DataFrame(rader).to_csv("sonder/gullgruver.csv", index=False)
print("\nLagret sonder/gullgruver.csv")


# ------------------------------------------------------------------ tillegg
# TILLEGG (lagt til ETTER kjøringen 28.10.2026, avgjør ikke): hva bærer S1,
# og tåler det at 2020 tas ut? Rangkorrelasjon mot neste 3 og 6 mnd minus
# MSCI World, GDX.L og GDXJ.L.
print("\nTILLEGG (etter kjøring, avgjør ikke)\n")
O3 = -(M.olje - M.olje.shift(3))
for s in ("GDX.L", "GDXJ.L", "GDX"):
    for h in (3, 6):
        y = (M[s].shift(-h) - M[s]) - (M.verden.shift(-h) - M.verden)
        d = pd.concat([S1, S3, O3, y], axis=1, keys=["S1", "gull", "minus_olje", "y"]).dropna()
        u20 = d[(d.index < pd.Period("2020-01", "M")) | (d.index > pd.Period("2020-12", "M"))]
        rk = d.rank().corr()["y"]; ru = u20.rank().corr()["y"]
        print(f"   {s:7} {h} mnd: S1 {rk.S1:+.2f} (uten 2020 {ru.S1:+.2f}) | bare gull {rk.gull:+.2f} | bare minus olje"
              f" {rk.minus_olje:+.2f} (uten 2020 {ru.minus_olje:+.2f}) | n {len(d)}")
