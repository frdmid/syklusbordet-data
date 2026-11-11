# ---------------------------------------------------------------------------
# sonde_kjor_vvix_sjokk: kan sjokkleddet i regimepanelet bli bedre med
# maanedssnitt av VVIX, eller med spredningen i VIX innenfor maaneden, enn med
# maanedssnittet av VIX alene? (Frodes bestilling 11.11.2026, etter
# gjennomgangen notater/2026-11-11_gjennomgang.md)
#
# BAKGRUNN. kontekst_regime.py bruker i dag maanedssnittet av ^VIX og
# papirkorrelasjonen, kombinert med max(), terskel 95 paa persentilen punkt i
# tid. Sonden sonde_kjor_regime fant at sjokkleddet ikke holder. Frodes
# spoersmaal: maanedssnittet visker ut bevegelsen innenfor maaneden, saa maaler
# vi den i stedet, eller maaler vi volatiliteten i VIX direkte (VVIX)?
#
# TRE MAAL, alle maanedlige, alle som persentil punkt i tid:
#   vix_snitt      maanedssnitt av daglig ^VIX (fra 1990). Dagens maal.
#   vix_spredning  standardavviket til daglige logendringer i ^VIX innenfor
#                  maaneden (fra 1990). Fanger bevegelse, ikke nivaa.
#   vvix_snitt     maanedssnitt av daglig ^VVIX (fra januar 2007).
# Hel maaned: en maaned med under 15 handledager tas ikke med, slik priser.py
# kaster en paabegynt maaned. Maalt 11.11.2026 gir Yahoo ^VIX fra 1990-01-02 og
# ^VVIX fra 2007-01-03 med dagsdata.
#
# SIGNAL. Championens bunnsone, A raa >= 80 og A detrendet >= 80 i maaned t,
#   realpris fra serier/priser_mnd.csv, punkt i tid, alle 18 raavarer.
# UTFALL. Endring i log realpris for raavaren de neste h maanedene (6, 12, 24).
#   Raavaren og ikke papirene, slik at overlevelsesskjevheten i instrumentene
#   ikke kommer inn. Papirene staar beskrivende til slutt.
# TEST A. Hver signalmaaned plasseres i nederste, midterste eller oeverste
#   tredjedel av maalet mot det som var kjent da (minst 36 mnd). Forskjellen er
#   snittet i oeverste tredjedel minus snittet i nederste.
#
# KRITERIER (satt foer kjoering 11.11.2026, samme krav som
# sonde_kjor_signal_vix_dxy_move 03.11.2026, saa de to kan leses sammen).
# Et maal betyr noe hvis alle disse holder:
#   (a) |forskjellen| er minst 5 prosentpoeng per 12 mnd (2,5 per 6, 10 per 24),
#   (b) p under 0,05 tosidig mot sirkulaert forskjoevet maalserie (minst 24 mnd,
#       2000 trekk),
#   (c) samme fortegn i begge halvdelene av perioden,
#   (d) minst 3 episoder (ny etter 12 mnd uten signal) i hver av de to
#       tredjedelene, og
#   (e) Benjamini-Hochberg paa 10 % over de maalene som kan avgjoeres x 3
#       horisonter.
# vix_snitt og vix_spredning avgjoeres paa oppstart til og med 2014-12.
# 2015 til 2026 vises, men avgjoerer ikke.
#
# VVIX KAN IKKE AVGJOERES HER, og det staar her foer kjoering: serien starter i
# 2007, saa tredjedelen finnes foerst fra 2010 og persentilen fra slutten av
# 2011. Vinduet foer 2015 er for kort til aa gi tre episoder i hver tredjedel.
# VVIX rapporteres beskrivende over hele sin periode og er holdt utenfor
# BH-korreksjonen. Blir VVIX staaende som kandidat, maa den avgjoeres
# fremoverskuende som Challenger med egen startdato, ikke her.
#
# TEST B, beskrivende. De tre maalene som sjokkord med terskelen 95 fra
#   kontekst_regime (persentil punkt i tid, minst 60 mnd): hvilke maaneder hver
#   av dem kaller sjokk, hvor mye de overlapper, korrelasjonene, og hvor mange
#   bunnsone-episoder som kom i sjokk etter hver definisjon. Ingen terskel
#   velges i denne sonden; 95 og 60 er tallene som alt staar i koden.
# TEST C, beskrivende. De 13 posisjonene i papirporteføljen (handel.json) med
#   de tre maalene ved inngang og papirenes avkastning mot MSCI World.
#
# Skriver ingenting til dashbordet og ingenting til shadow. Utdata
# sonder/vvix_sjokk.csv. Grensene over flyttes ikke etter kjoering.
# ---------------------------------------------------------------------------

import datetime as dt
import json, time
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import requests

rng = np.random.default_rng(20261111)
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
MIN_HIST = 60          # som priser.py og kontekst_regime
MIN_TRED = 36          # som sonde_kjor_signal_vix_dxy_move
MIN_DAGER = 15         # hel maaned
SJOKK_PCT = 95         # terskelen i kontekst_regime
TIL = pd.Period("2014-12", "M")
NYTT = (pd.Period("2015-01", "M"), pd.Period("2026-12", "M"))
AVGJOER = ("vix_snitt", "vix_spredning")


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


def pit(s, minn=MIN_HIST):
    """Persentil punkt i tid, hoeyt tall = hoeyt nivaa (som vix_pct i regime)."""
    v = s.values; ut = np.full(len(v), np.nan)
    for i in range(len(v)):
        h = v[: i + 1]; h = h[np.isfinite(h)]
        if np.isfinite(v[i]) and len(h) >= minn:
            ut[i] = (h <= v[i]).mean() * 100
    return pd.Series(ut, index=s.index)


def tredjedel(s, minn=MIN_TRED):
    v = s.values; ut = np.full(len(v), np.nan)
    for i in range(len(v)):
        h = v[: i + 1]; h = h[np.isfinite(h)]
        if np.isfinite(v[i]) and len(h) >= minn:
            q = (h <= v[i]).mean()
            ut[i] = 0 if q <= 1 / 3 else (2 if q > 2 / 3 else 1)
    return pd.Series(ut, index=s.index)


def yahoo_dag(sym):
    for f in range(4):
        try:
            r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}",
                             params={"period1": 0, "period2": int(time.time()), "interval": "1d"},
                             headers=UA, timeout=60)
            res = r.json()["chart"]["result"][0]
            if (res.get("meta") or {}).get("dataGranularity") != "1d":
                raise ValueError("ikke dagskurser")
            s = pd.Series(res["indicators"]["quote"][0]["close"],
                          index=pd.to_datetime(res["timestamp"], unit="s")).dropna()
            time.sleep(0.3)
            return s[s > 0]
        except Exception as e:
            if f == 3:
                raise
            print(f"   {sym} forsoek {f+1} feilet ({type(e).__name__}), nytt forsoek")
            time.sleep(2 ** (f + 1))


def hel_maaned(s):
    """Maanedsgrupper med minst MIN_DAGER handledager."""
    g = s.groupby(s.index.to_period("M"))
    return g, g.size()


def mnd_snitt(s):
    g, n = hel_maaned(s)
    m = g.mean()[n >= MIN_DAGER]
    return m.sort_index()


def mnd_spredning(s):
    d = np.log(s).diff().dropna()
    g = d.groupby(d.index.to_period("M"))
    m = g.std()[g.size() >= MIN_DAGER]
    return m.dropna().sort_index()


print("sonde_kjor_vvix_sjokk, kjort",
      dt.datetime.now(ZoneInfo("Europe/Oslo")).strftime("%Y-%m-%d %H:%M:%S"),
      "norsk tid")
print("Kriteriene staar i toppen av fila og er satt foer kjoering.\n")

# ------------------------------------------------------------------ raavarene
p = pd.read_csv("serier/priser_mnd.csv"); p = p[~p.segment.str.startswith("ship_")]
real = p.pivot(index="t", columns="segment", values="real").astype(float).sort_index()
real.index = pd.PeriodIndex(real.index, freq="M")
lr = np.log(real)
A = pd.DataFrame(np.nan, index=lr.index, columns=lr.columns); Ad = A.copy()
for c in lr.columns:
    s = lr[c].dropna()
    A.loc[s.index, c] = expanding_pct(s.values)
    Ad.loc[s.index, c] = expanding_pct_detrend(s.values)
SIG = ((A >= 80) & (Ad >= 80)).values
print(f"{lr.shape[1]} raavarer, {lr.index[0]} til {lr.index[-1]}, "
      f"{int(SIG.sum())} signalmaaneder i alt")

# ---------------------------------------------------------------------- maalene
vix = yahoo_dag("%5EVIX")
vvix = yahoo_dag("%5EVVIX")
print(f"^VIX  {vix.index[0].date()} til {vix.index[-1].date()}, {len(vix)} dager")
print(f"^VVIX {vvix.index[0].date()} til {vvix.index[-1].date()}, {len(vvix)} dager")

MAAL = {"vix_snitt": mnd_snitt(vix),
        "vix_spredning": mnd_spredning(vix),
        "vvix_snitt": mnd_snitt(vvix)}
pct, tred = {}, {}
for n, s in MAAL.items():
    pct[n] = pit(s); tred[n] = tredjedel(s).reindex(lr.index)
    t_sist = s.index[-1]
    print(f"{n:14} {s.index[0]} til {t_sist} ({len(s)} hele mnd), siste {s.iloc[-1]:.3f}, "
          f"persentil {pct[n].iloc[-1]:.0f}" if np.isfinite(pct[n].iloc[-1]) else
          f"{n:14} {s.index[0]} til {t_sist} ({len(s)} hele mnd), siste {s.iloc[-1]:.3f}, persentil -")


def episoder(mask):
    n = 0
    for j in range(mask.shape[1]):
        forr = None
        for i in np.where(mask[:, j])[0]:
            if forr is None or i - forr > 12:
                n += 1
            forr = i
    return n


def analyse(T, h, fra, til):
    Y = (lr.shift(-h) - lr).values
    rad = (lr.index >= fra) & (lr.index <= til)
    S, Yp, Tp = SIG[rad], Y[rad], T.values[rad]

    def d(Tv):
        ok = S & np.isfinite(Yp)
        hoy, lav = ok & (Tv == 2)[:, None], ok & (Tv == 0)[:, None]
        mid = ok & (Tv == 1)[:, None]
        if not hoy.sum() or not lav.sum():
            return np.nan, hoy, lav, mid
        return Yp[hoy].mean() - Yp[lav].mean(), hoy, lav, mid
    diff, hoy, lav, mid = d(Tp)
    if not np.isfinite(diff):
        return None
    if len(Tp) <= 48:
        return None
    null = np.array([d(np.roll(Tp, rng.integers(24, len(Tp) - 24)))[0] for _ in range(2000)])
    null = np.abs(null[np.isfinite(null)])
    pv = (np.sum(null >= abs(diff)) + 1) / (len(null) + 1)
    gyldig = np.where(np.isfinite(Tp))[0]
    midt = gyldig[len(gyldig) // 2]; hv = []
    for sl in (np.arange(len(Tp)) < midt, np.arange(len(Tp)) >= midt):
        hv.append(d(np.where(sl, Tp, np.nan))[0])
    return dict(hoy=Yp[hoy].mean(), mid=Yp[mid].mean() if mid.sum() else np.nan,
                lav=Yp[lav].mean(), diff=diff, p=pv, h1=hv[0], h2=hv[1],
                n_hoy=int(hoy.sum()), n_lav=int(lav.sum()),
                ep_hoy=episoder(hoy), ep_lav=episoder(lav))


def pp(x):
    return "   -  " if x is None or not np.isfinite(x) else f"{100*x:+6.1f}"


# ------------------------------------------------------------------- TEST A
rader, tester = [], []
for n in MAAL:
    T = tred[n]
    gyldig = T.dropna()
    if not len(gyldig):
        print(f"\n==================== {n}: ingen gyldige maaneder"); continue
    start = gyldig.index[0]
    kan = n in AVGJOER
    print(f"\n==================== {n} (oeverste mot nederste tredjedel, log realpris, per h mnd)")
    print(f"   tredjedel fra {start}. " + ("Avgjoeres paa oppstart til 2014-12."
          if kan else "Beskrivende, avgjoer ikke (for kort serie, se toppen av fila)."))
    perioder = ({"avgjoer": (start, TIL), "2015-2026": NYTT} if kan
                else {"hele": (start, NYTT[1]), "2015-2026": NYTT})
    for h in (6, 12, 24):
        for pn, (fra, til) in perioder.items():
            a = analyse(T, h, fra, til)
            if a is None:
                print(f"   h {h:2} {pn:9} for faa signalmaaneder eller for kort periode")
                continue
            rader.append({"maal": n, "h": h, "periode": pn, "fra": str(fra), **a})
            print(f"   h {h:2} {pn:9} ({fra}) hoey {pp(a['hoy'])} % (n {a['n_hoy']}, ep {a['ep_hoy']})"
                  f"  midt {pp(a['mid'])} %  lav {pp(a['lav'])} % (n {a['n_lav']}, ep {a['ep_lav']})"
                  f"  forskjell {pp(a['diff'])} pp  p {a['p']:.3f}"
                  f"  halvdeler {pp(a['h1'])}/{pp(a['h2'])}")
            if kan and pn == "avgjoer":
                ok = (abs(a["diff"]) >= 0.05 * h / 12 and a["p"] < 0.05
                      and np.sign(a["h1"]) == np.sign(a["h2"]) == np.sign(a["diff"])
                      and a["ep_hoy"] >= 3 and a["ep_lav"] >= 3)
                tester.append({"test": f"{n}, h {h}", "p": a["p"], "ok": ok,
                               "retning": "bedre ved hoeyt maal" if a["diff"] > 0 else "bedre ved lavt maal"})

print("\nAVGJOERELSE (vix_snitt og vix_spredning, oppstart til 2014-12)\n")
if tester:
    Tt = pd.DataFrame(tester).sort_values("p").reset_index(drop=True); m = len(Tt)
    g = max([i + 1 for i in range(m) if Tt.p[i] <= 0.10 * (i + 1) / m], default=0)
    Tt["bh"] = [i < g for i in range(m)]
    for _, t in Tt.sort_values("test").iterrows():
        dom = "HOLDER, " + t.retning if (t.ok and t.bh) else "holder ikke"
        print(f"   {t.test:24}: {dom} (krav a til d {'ja' if t.ok else 'nei'}, "
              f"p {t.p:.3f}, BH {'ja' if t.bh else 'nei'})")
else:
    print("   ingen test kunne gjennomfoeres")
print("\n   vvix_snitt: kan ikke avgjoeres i denne sonden (serien starter 2007).")

# ------------------------------------------------------------------- TEST B
print(f"\n==================== TEST B, beskrivende: sjokkord med terskel {SJOKK_PCT}")
P = pd.DataFrame({n: pct[n] for n in MAAL}).dropna(how="all")
felles = P.dropna()
print(f"   persentil finnes for alle tre fra {felles.index[0] if len(felles) else '-'} "
      f"({len(felles)} mnd)")
if len(felles) > 2:
    print("\n   korrelasjon mellom persentilene (felles maaneder)")
    c = felles.corr()
    for a_ in MAAL:
        print("     " + a_.ljust(14) + "  ".join(f"{a_2[:9]:>10} {c.loc[a_, a_2]:+.2f}" for a_2 in MAAL))
print(f"\n   maaneder over {SJOKK_PCT} per maal (hele perioden til maalet)")
for n in MAAL:
    s = pct[n].dropna()
    over = s[s >= SJOKK_PCT]
    print(f"     {n:14} {len(over):3} av {len(s):3} mnd fra {s.index[0]}: "
          + ", ".join(str(x) for x in over.index[:14]) + (" ..." if len(over) > 14 else ""))
if len(felles) > 2:
    print(f"\n   uenighet paa felles maaneder (fra {felles.index[0]})")
    for a_ in MAAL:
        for b_ in MAAL:
            if a_ >= b_:
                continue
            x = (felles[a_] >= SJOKK_PCT) & (felles[b_] < SJOKK_PCT)
            y = (felles[b_] >= SJOKK_PCT) & (felles[a_] < SJOKK_PCT)
            z = (felles[a_] >= SJOKK_PCT) & (felles[b_] >= SJOKK_PCT)
            print(f"     {a_} mot {b_}: bare {a_} {int(x.sum()):2}, bare {b_} {int(y.sum()):2}, begge {int(z.sum()):2}")

print("\n   bunnsone-episoder som kom i sjokk etter hvert maal")
for n in MAAL:
    T = pct[n].reindex(lr.index)
    mask = SIG & (T.values >= SJOKK_PCT)[:, None]
    tot = SIG & np.isfinite(T.values)[:, None]
    print(f"     {n:14} {episoder(mask)} av {episoder(tot)} episoder i maaneder maalet dekker")

print("\n   siste 12 hele maaneder")
print("     mnd       " + "".join(f"{n:>16}" for n in MAAL))
for t in P.index[-12:]:
    rad = "".join(f"{(f'{MAAL[n][t]:8.2f} ({pct[n][t]:3.0f})' if t in MAAL[n].index and np.isfinite(pct[n].get(t, np.nan)) else '               -'):>16}" for n in MAAL)
    print(f"     {str(t):9} {rad}")

# ------------------------------------------------------------------- TEST C
print("\n==================== TEST C, beskrivende: papirporteføljen ved inngang")
try:
    pos = [q for q in json.load(open("handel.json", encoding="utf-8"))["portefolje"]["posisjoner"]
           if q["variant"] == "alle"]
    ord_ = ["lav", "midt", "hoey"]
    for q in pos:
        t = pd.Period(q["inngang"], "M")
        bit = []
        for n in MAAL:
            v = MAAL[n].get(t, np.nan); tr = tred[n].get(t, np.nan)
            bit.append(f"{n} {v:8.2f} ({ord_[int(tr)] if np.isfinite(tr) else '-'})"
                       if np.isfinite(v) else f"{n}        -      ")
        w = q.get("world")
        print(f"   {q['segment']:10} {q['inngang']}  " + "  ".join(bit)
              + f"  papirer {q['avk']:+8.1f} %  MSCI World "
              + (f"{w:+7.1f} %" if w is not None else "      -"))
except Exception as e:
    print(f"   kunne ikke lese handel.json ({type(e).__name__}: {str(e)[:60]})")

pd.DataFrame(rader).to_csv("sonder/vvix_sjokk.csv", index=False)
print("\nLagret sonder/vvix_sjokk.csv")
