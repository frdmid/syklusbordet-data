# ---------------------------------------------------------------------------
# sonde_kjor_raavarefond: gir et fond paa raavaren selv mer enn papirene naar
# bunnsonen staar? (Frodes bestilling 03.11.2026, punkt 4 i traderforslagene)
#
# Bakgrunn: sonde_kjor_verdi_trend_kurve fant at bunnsonen ga +6,2 % mot
# -1,5 % i realpris over 12 mnd (1965 til 2014, strauk bare paa BH), mens
# sonde_kjor_backtest_lang viste at papirene ved flagg har ligget under
# markedet. Spoersmaalet er om fondet tar med seg prisoppgangen naar rulle-
# kostnaden i terminene er trukket fra.
#
# Fond (Yahoo, kurs i USD; uran i CAD regnet om):
#   wti USO, brent BNO, henryhub UNG, gold GLD, kobber COPA.L, aluminium
#   ALUM.L, nikkel NICK.L, sink ZINC.L, kakao COCO.L, uran U-UN.TO (fysisk).
#   Ingen fond med historikk for bly, tinn, palmeolje, TTF, kull, jernmalm og
#   laks. NB: ETC og amerikanske ETF er ikke lov paa IKZ (instrumenter.py,
#   krav 1); de maa holdes paa vanlig konto.
# Papirer: dagens papirer i segments/<id>.json (likt vektet, adjclose, i USD).
#   Kakao er utelatt fra papirsammenligningen (papirene er omvendte). For uran
#   er U-UN.TO tatt ut av papirene (det er fondet). Papirene er valgt i 2026
#   paa data fra 2016, saa sammenligningen er skjev i papirenes favoer.
# Signal: bunnsone, A raa >= 80 og A detrendet >= 80 i maaned t (realpris,
#   punkt i tid, som Championen). Inngang ved maanedsslutt t, utgang t + h.
#   Ny episode etter 12 mnd uten signal; episoden maales fra foerste maaned.
# Marked: SPY. Spot: endring i log nominell pris (maanedssnitt) i samme
#   vindu, for aa se rullekostnaden.
#
# KRITERIER (satt foer kjoering, 03.11.2026). Fondet slaar papirene ved
# signal hvis, paa BAADE h 12 og h 24 og over alle aar med data (2006 til
# 2026):
#   (a) median over episodene av fond minus papirer er over 0, og snittet
#       over alle signalmaaneder er over 0,
#   (b) flertallet av episodene har fond over papirer,
#   (c) p under 0,10 i tilfeldig fortegnsbytte paa episodene (10 000 trekk),
#   (d) minst 8 episoder fra minst 4 raavarer.
# Samme krav for fond minus marked. h 6 vises, avgjoer ikke. Verste punkt
# underveis (median per episode) og rullekostnad vises, avgjoer ikke.
# Fond minus papirer i maaneder uten signal vises til sammenligning.
# Skriver ingenting til dashbordet. Utdata sonder/raavarefond.csv.
# ---------------------------------------------------------------------------

import json, time
import numpy as np
import pandas as pd
import requests

rng = np.random.default_rng(20261103)
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0 Safari/537.36"}
MIN_HIST = 60
FOND = {"wti": "USO", "brent": "BNO", "henryhub": "UNG", "gold": "GLD", "kobber": "COPA.L",
        "aluminium": "ALUM.L", "nikkel": "NICK.L", "sink": "ZINC.L", "kakao": "COCO.L", "uran": "U-UN.TO"}
VALUTA = {"GBP": "GBPUSD=X", "GBp": "GBPUSD=X", "CAD": "CADUSD=X", "NOK": "NOKUSD=X", "SEK": "SEKUSD=X",
          "EUR": "EURUSD=X", "CHF": "CHFUSD=X", "AUD": "AUDUSD=X", "DKK": "DKKUSD=X"}
_cache = {}


def hent(sym):
    if sym in _cache:
        return _cache[sym]
    for f in range(4):
        try:
            r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}",
                             params={"period1": 0, "period2": int(time.time()), "interval": "1d", "events": "div,split"},
                             headers=UA, timeout=60)
            res = r.json()["chart"]["result"][0]
            break
        except Exception:
            time.sleep(2 ** (f + 1))
    else:
        raise RuntimeError(f"{sym}: ingen data")
    adj = res["indicators"].get("adjclose", [{}])[0].get("adjclose") or res["indicators"]["quote"][0]["close"]
    s = pd.Series(adj, index=pd.to_datetime(res["timestamp"], unit="s")).dropna()
    s = s[s > 0].resample("ME").last(); s.index = s.index.to_period("M")
    cur = res["meta"].get("currency", "USD")
    if cur == "GBp":
        s = s / 100
    if cur != "USD":
        fx = hent(VALUTA[cur])[0]
        s = (s * fx).dropna()
    time.sleep(0.3)
    _cache[sym] = (s, cur)
    return _cache[sym]


def logkurs(sym):
    return np.log(hent(sym)[0])


def expanding_pct(v):
    out = np.full(len(v), np.nan)
    for i in range(MIN_HIST - 1, len(v)):
        out[i] = (v[: i + 1] <= v[i]).sum() / (i + 1)
    return (1 - out) * 100


def expanding_pct_detrend(v):
    out = np.full(len(v), np.nan)
    for i in range(MIN_HIST - 1, len(v)):
        y = v[: i + 1]; t = np.arange(i + 1)
        b, a = np.polyfit(t, y, 1); r = y - (a + b * t)
        out[i] = (r <= r[i]).sum() / len(r)
    return (1 - out) * 100


p = pd.read_csv("serier/priser_mnd.csv")
spy = logkurs("SPY")


def fram(s, t, h):
    if t not in s.index or (t + h) not in s.index:
        return np.nan
    return s[t + h] - s[t]


def verst(s, t, h):
    if t not in s.index or (t + h) not in s.index:
        return np.nan
    w = s[(s.index >= t) & (s.index <= t + h)]
    return w.min() - s[t]


rader = []
print("DEKNING")
for seg, f in FOND.items():
    sr = p[p.segment == seg].set_index("t").astype({"real": float, "nom": float})
    sr.index = pd.PeriodIndex(sr.index, freq="M"); sr = sr.sort_index()
    lr, ln = np.log(sr.real), np.log(sr.nom)
    A, Ad = expanding_pct(lr.values), expanding_pct_detrend(lr.values)
    sig = pd.Series((A >= 80) & (Ad >= 80), index=lr.index)
    fk = logkurs(f)
    pap = []
    if seg != "kakao":
        for i in json.load(open(f"segments/{seg}.json", encoding="utf-8"))["instrumenter"]:
            if i["ticker"] != f and not i.get("omvendt"):
                try:
                    pap.append(logkurs(i["ticker"]))
                except Exception as e:
                    print(f"   {seg}: {i['ticker']} mangler ({type(e).__name__})")
    pk = None
    if pap:
        R = pd.concat([x.diff() for x in pap], axis=1)
        pk = R.mean(axis=1, skipna=True)[R.notna().sum(axis=1) > 0].cumsum()
    print(f"   {seg:10} fond {f:8} fra {fk.index[0]}  papirer {len(pap)} fra {pk.index[0] if pk is not None else '-'}"
          f"  signalmaaneder med fond {int(sig[sig.index >= fk.index[0]].sum())}")
    forr = None
    for t in fk.index:
        if t not in sig.index:
            continue
        s_ = bool(sig[t])
        ny = False
        if s_:
            ny = forr is None or (t - forr).n > 12
            forr = t
        for h in (6, 12, 24):
            F = fram(fk, t, h)
            if not np.isfinite(F):
                continue
            rader.append({"segment": seg, "t": str(t), "h": h, "signal": s_, "ny_episode": ny,
                          "fond": F, "papirer": fram(pk, t, h) if pk is not None else np.nan, "marked": fram(spy, t, h),
                          "spot": fram(ln, t, h), "fond_verst": verst(fk, t, h),
                          "papirer_verst": verst(pk, t, h) if pk is not None else np.nan})
D = pd.DataFrame(rader)
D["fond_m_pap"], D["fond_m_mkt"], D["pap_m_mkt"], D["rulle"] = (D.fond - D.papirer, D.fond - D.marked,
                                                                D.papirer - D.marked, D.fond - D.spot)
# episodenummer per segment
D = D.sort_values(["segment", "h", "t"])
D["episode"] = D.groupby(["segment", "h"]).ny_episode.cumsum()


def fortegn_p(x, n=10000):
    x = np.asarray(x); x = x[np.isfinite(x)]
    if not len(x):
        return np.nan
    m = x.mean()
    null = np.array([(x * rng.choice([-1, 1], len(x))).mean() for _ in range(n)])
    return (np.sum(null >= m) + 1) / (n + 1)


def pp(x):
    return "   -  " if x is None or not np.isfinite(x) else f"{100*x:+6.1f}"


print("\nEPISODER (foerste signalmaaned, h 12: fond, papirer, marked, spot; prosent log)")
for _, r in D[(D.h == 12) & D.ny_episode].iterrows():
    print(f"   {r.segment:10} {r.t}  fond {pp(r.fond)}  papirer {pp(r.papirer)}  marked {pp(r.marked)}  spot {pp(r.spot)}"
          f"  rulle {pp(r.rulle)}")

print("\nRESULTAT (prosent log; median og andel over episodene, snitt over alle signalmaaneder)")
avg = []
for h in (6, 12, 24):
    print(f"\n   h = {h} mnd")
    S = D[(D.h == h) & D.signal]
    E = S[S.ny_episode]
    U = D[(D.h == h) & ~D.signal]
    print(f"      signal: {len(S)} maaneder, {len(E)} episoder fra {E.segment.nunique()} raavarer")
    for k, navn in (("fond", "fond"), ("papirer", "papirer"), ("marked", "marked"), ("spot", "spot")):
        print(f"      {navn:22} median ep {pp(E[k].median())}  snitt mnd {pp(S[k].mean())}   uten signal snitt {pp(U[k].mean())}")
    for k, navn in (("fond_m_pap", "fond minus papirer"), ("fond_m_mkt", "fond minus marked"),
                    ("pap_m_mkt", "papirer minus marked"), ("rulle", "fond minus spot (rulle)")):
        e = E[k].dropna()
        pv = fortegn_p(e)
        andel = (e > 0).mean() if len(e) else np.nan
        print(f"      {navn:22} median ep {pp(e.median())}  snitt mnd {pp(S[k].mean())}  over 0 {100*andel:4.0f} % av {len(e)} ep"
              f"  p {pv:.3f}   uten signal snitt {pp(U[k].mean())}")
        if h in (12, 24) and k in ("fond_m_pap", "fond_m_mkt"):
            ok = (e.median() > 0 and S[k].mean() > 0 and andel > 0.5 and pv < 0.10 and len(e) >= 8
                  and E.loc[e.index, "segment"].nunique() >= 4)
            avg.append({"test": navn, "h": h, "ok": ok, "median": e.median(), "p": pv, "n": len(e)})
    print(f"      verste punkt underveis, median ep: fond {pp(E.fond_verst.median())}  papirer {pp(E.papirer_verst.median())}")
    print(f"      etter 2015 (signalmaaneder): fond {pp(S[S.t >= '2015-01'].fond.mean())}  papirer {pp(S[S.t >= '2015-01'].papirer.mean())}"
          f"  marked {pp(S[S.t >= '2015-01'].marked.mean())}  (n {int((S.t >= '2015-01').sum())})")

print("\nPER RAAVARE (h 12, snitt over signalmaaneder)")
S = D[(D.h == 12) & D.signal]
for seg, g in S.groupby("segment"):
    print(f"   {seg:10} n {len(g):3}  ep {int(g.ny_episode.sum())}  fond {pp(g.fond.mean())}  papirer {pp(g.papirer.mean())}"
          f"  marked {pp(g.marked.mean())}  rulle {pp(g.rulle.mean())}")

print("\nAVGJOERELSE (krav a til d paa h 12 og h 24)")
A_ = pd.DataFrame(avg)
for navn, g in A_.groupby("test"):
    holder = bool(g.ok.all())
    print(f"   {navn:20}: {'HOLDER' if holder else 'holder ikke'}  "
          + ", ".join(f"h {r.h}: median {pp(r.median)}, p {r.p:.3f}, {r.n} ep, krav {'ja' if r.ok else 'nei'}" for r in g.itertuples()))
D.to_csv("sonder/raavarefond.csv", index=False)
print("\nLagret sonder/raavarefond.csv")
