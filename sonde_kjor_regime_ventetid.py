# ---------------------------------------------------------------------------
# sonde_kjor_regime_ventetid: hvor lenge etter et regimeskifte boer man gaa
# inn? (Frodes spoersmaal 15.10.2026)
#
# Hendelsesstudie. Regimet fra sonder/regime.csv (punkt i tid):
#   R1 inn i bred nedgang   bredde (andel raavarer opp over 12 mnd) krysser
#                           ned til 0,4 eller lavere (fra 1966)
#   R2 ut av bred nedgang   bredde krysser opp over 0,4
#   R3 inn i sjokk          hoeyeste av VIX-persentil og papirkorrelasjonens
#                           persentil krysser opp til 95 eller mer (fra 1995)
#   R4 ut av sjokk          samme maal faller under 80 etter aa ha vaert 95+
# Et nytt skifte av samme slag teller bare etter minst 12 mnd siden forrige.
#
# Inngang L mnd etter skiftet, L = 0, 1, 2, 3, 4, 6, 9, 12, og hold i 24 mnd.
# Maales paa to kurver:
#   RAAVARER  likevektet snitt av maanedlig log-endring i realpris for de 18
#             raavaresegmentene i serier/priser_mnd.csv
#   PAPIRER   likevektet snitt av maanedlig log-avkastning for papirene paa
#             bordet (omvendte utelatt) og fondene XOP, GDX, COPX, XME, MOO,
#             IEZ, OIH, i USD fra Yahoo (fra 1990), og det samme minus SPY
# For hver L: median avkastning over skiftene, andel skifter der L slo L = 0,
# og verste fall underveis (laveste punkt i de 24 mnd, median).
#
# BESKRIVENDE, med et forhaandssatt krav for aa si at det loenner seg aa
# vente (satt foer kjoering, 15.10.2026): en ventetid L > 0 er bedre enn aa
# gaa inn med en gang hvis den slaar L = 0 i minst to av tre skifter OG
# medianen er minst 5 prosentpoeng hoeyere, paa BEGGE kurvene (raavarer og
# papirer, absolutt). Med 4 slags skifter og 7 ventetider er det 28
# sammenligninger paa faa skifter; et enkelt treff er svakt.
# Skriver ingenting til dashbordet. Utdata sonder/regime_ventetid.csv.
# ---------------------------------------------------------------------------

import time
import numpy as np
import pandas as pd
import requests

from instrumenter import INSTR

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
FONDER = ["XOP", "GDX", "COPX", "XME", "MOO", "IEZ", "OIH"]
LAG = [0, 1, 2, 3, 4, 6, 9, 12]
HOLD = 24


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
reg["sjokk"] = reg[["vix_pct", "korr_papirer_pct"]].max(axis=1)

# kurvene (kumulativ log-indeks)
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
print(f"Raavarekurv {RAA.index[0]}..{RAA.index[-1]}; papirkurv {PAP.index[0]}..{PAP.index[-1]} "
      f"({dr.shape[1]} papirer og fond, snitt {dr.notna().sum(axis=1).median():.0f} per mnd)\n")


def skifter(serie, inn, ut=None):
    """Datoer der tilstanden starter (inn). Ved ut: datoer der den slutter."""
    v = serie.dropna(); ev, sist, aktiv = [], None, False
    for t, x in v.items():
        if ut is None:
            ny = inn(x)
            if ny and not aktiv and (sist is None or (t - sist).n >= 12):
                ev.append(t); sist = t
            aktiv = ny
        else:
            if inn(x):
                aktiv = True
            elif aktiv and ut(x):
                if sist is None or (t - sist).n >= 12:
                    ev.append(t); sist = t
                aktiv = False
    return ev


SK = {"R1 inn i bred nedgang": skifter(reg.bredde, lambda x: x <= 0.4),
      "R2 ut av bred nedgang": skifter(reg.bredde, lambda x: x <= 0.4, lambda x: x > 0.4),
      "R3 inn i sjokk": skifter(reg.sjokk, lambda x: x >= 95),
      "R4 ut av sjokk": skifter(reg.sjokk, lambda x: x >= 95, lambda x: x < 80)}
# R1 krever ogsaa at bredden var over 0,4 maaneden foer (et ekte skifte)
SK["R1 inn i bred nedgang"] = [t for t in SK["R1 inn i bred nedgang"] if reg.bredde.get(t - 1, 1) > 0.4]


def utfall(kurv, t0):
    a = kurv.get(t0, np.nan); b = kurv.get(t0 + HOLD, np.nan)
    if not (np.isfinite(a) and np.isfinite(b)):
        return np.nan, np.nan
    sti = kurv.loc[t0: t0 + HOLD] - a
    return b - a, sti.min()


rader = []
for navn, ev in SK.items():
    print(f"==================== {navn}: {len(ev)} skifter")
    print("   " + ", ".join(str(t) for t in ev))
    for knavn, kurv in (("raavarer", RAA), ("papirer", PAP), ("papirer mot SPY", PAPX)):
        tab = {L: [utfall(kurv, t + L) for t in ev] for L in LAG}
        r0 = np.array([x[0] for x in tab[0]])
        print(f"   {knavn}:")
        print(f"      {'vent':>5} {'n':>3} {'median 24m':>11} {'slo L=0':>8} {'verste fall':>12}")
        for L in LAG:
            r = np.array([x[0] for x in tab[L]]); dd = np.array([x[1] for x in tab[L]])
            ok = np.isfinite(r) & np.isfinite(r0)
            slo = (r[ok] > r0[ok]).mean() if L and ok.sum() else np.nan
            med = np.nanmedian(r) if np.isfinite(r).any() else np.nan
            print(f"      {L:4}m {np.isfinite(r).sum():3} {100 * med:+10.1f}% "
                  f"{'' if L == 0 else f'{100 * slo:7.0f}%':>8} {100 * np.nanmedian(dd) if np.isfinite(dd).any() else np.nan:+11.1f}%")
            rader.append({"skifte": navn, "kurv": knavn, "vent": L, "n": int(np.isfinite(r).sum()),
                          "median": med, "slo_L0": slo, "med_L0": np.nanmedian(r0[ok]) if ok.any() else np.nan,
                          "med_L": np.nanmedian(r[ok]) if ok.any() else np.nan,
                          "verste": np.nanmedian(dd) if np.isfinite(dd).any() else np.nan})
    print()

R = pd.DataFrame(rader)
print("AVGJOERELSE: ventetider som slaar aa gaa inn med en gang paa begge kurvene\n")
for navn in SK:
    treff = []
    for L in LAG[1:]:
        ok = True
        for k in ("raavarer", "papirer"):
            x = R[(R.skifte == navn) & (R.kurv == k) & (R.vent == L)].iloc[0]
            ok &= bool(np.isfinite(x.slo_L0) and x.slo_L0 >= 2 / 3 and (x.med_L - x.med_L0) >= 0.05 and x.n >= 3)
        if ok:
            treff.append(f"{L} mnd")
    print(f"   {navn}: {', '.join(treff) if treff else 'ingen; aa gaa inn med en gang er ikke slaatt'}")
R.to_csv("sonder/regime_ventetid.csv", index=False)
print("\nLagret sonder/regime_ventetid.csv")
