# ---------------------------------------------------------------------------
# sonde_kjor_kurve_papirer: varsler terminkurven avkastningen paa papirene for
# WTI og Henry Hub? (Frodes bestilling 13.10.2026, etter sonde_kjor_kurve_a)
#
# Papirene er de som staar paa bordet (instrumenter.py): WTI CVE.TO, WCP.TO,
# IOGP.L; Henry Hub BIR.TO, TOU.TO, EQT. Kurv per raavare = likevektet snitt
# av papirene som har kurs den maaneden. XOP (tema-ETF for D) vises ved siden
# av, avgjoer ikke. Avkastning er log, dagskurser (period1/period2, justert
# for utbytte og splitt), maanedsslutt, i egen valuta, minus S&P 500 (SPY)
# samme periode.
#
# Kurven: EIA, NYMEX kontrakt 1 og 4, til april 2024. H = (K4 / K1 - 1) * 100,
# positiv er contango. Henry Hub sesongrenset med bare tidligere aar (som i
# sonde_kjor_kurve_a).
#
# Forventet retning: contango er fulle lagre og svak pris framover, altsaa
# svakere papirer. Begge signalene forventes NEGATIVE mot avkastningen.
#   x1 = H, nivaa, renset for prisendringen siste 3 mnd (residual)
#   x2 = endring i H siste 3 mnd, renset for prisendringen siste 3 mnd
#   y  = kurvens meravkastning mot SPY de neste 12 mnd
#
# KRITERIER (satt foer kjoering, 13.10.2026). Et signal holder for en raavare
# hvis: (a) korrelasjonen er -0,30 eller lavere, (b) negativ i begge
# halvdelene av perioden, (c) negativ i ikke-overlappende utvalg (hver 12.
# maaned), (d) p under 0,05 mot sirkulaert forskjoevet x (placebo, minst 24
# mnd, 2000 trekk, p fra normalhalen, ensidig i forventet retning), og (e)
# bestaar Benjamini-Hochberg paa 10 % over de fire testene (2 raavarer, 2
# signaler). 6 mnd, hvert papir og XOP vises, avgjoer ikke.
#
# Merk: kort overlapp (papirene fra 2000-tallet, kurven til 2024), saa testen
# har lav styrke. Skriver ingenting til dashbordet. Utdata sonder/kurve_papirer.csv.
# ---------------------------------------------------------------------------

import io, subprocess, sys, time
from math import erf, sqrt
import numpy as np
import pandas as pd
import requests

try:
    import xlrd  # noqa
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "xlrd"], check=False)

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
EIA = {"wti": ("pet", "RCLC"), "henryhub": ("ng", "RNGC")}
PAPIRER = {"wti": ["CVE.TO", "WCP.TO", "IOGP.L"], "henryhub": ["BIR.TO", "TOU.TO", "EQT"]}
rng = np.random.default_rng(20261013)


def eia(omr, kode, i):
    u = f"https://www.eia.gov/dnav/{omr}/hist_xls/{kode}{i}d.xls"
    for f in range(3):
        try:
            r = requests.get(u, headers={"User-Agent": "Syklusbordet (frdmid)"}, timeout=60)
            if r.status_code == 200:
                break
        except requests.RequestException:
            pass
        time.sleep(3 * (f + 1))
    ark = pd.read_excel(io.BytesIO(r.content), sheet_name=None, header=None)
    data = next((df for navn, df in ark.items() if "data" in str(navn).lower()), list(ark.values())[-1])
    df = data.dropna()
    df = df[pd.to_datetime(df.iloc[:, 0], errors="coerce").notna()]
    return pd.Series(pd.to_numeric(df.iloc[:, 1], errors="coerce").values,
                     index=pd.to_datetime(df.iloc[:, 0])).dropna()


def mnd_kurs(sym):
    r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}",
                     params={"period1": 0, "period2": int(time.time()), "interval": "1d", "events": "div,split"},
                     headers=UA, timeout=60)
    res = r.json()["chart"]["result"][0]
    if (res.get("meta") or {}).get("dataGranularity") != "1d":
        raise ValueError(f"{sym}: ikke dagskurser")
    adj = res["indicators"].get("adjclose", [{}])[0].get("adjclose") or res["indicators"]["quote"][0]["close"]
    s = pd.Series(adj, index=pd.to_datetime(res["timestamp"], unit="s")).dropna()
    s = s[s > 0].resample("ME").last()
    s.index = s.index.to_period("M")
    time.sleep(0.4)
    return s


def sesongrenset(h):
    ut = pd.Series(np.nan, index=h.index)
    for t in h.index:
        f = h[(h.index < t) & (h.index.month == t.month)]
        if len(f) >= 5:
            ut[t] = h[t] - f.mean()
    return ut


def resid(x, z):
    d = pd.concat([x, z], axis=1).dropna()
    b = np.polyfit(d.iloc[:, 1], d.iloc[:, 0], 1)
    return (d.iloc[:, 0] - np.polyval(b, d.iloc[:, 1])).reindex(x.index)


def placebo_p(x, y, n=2000, minsk=24):
    """Ensidig p for negativ korrelasjon."""
    d = pd.concat([x, y], axis=1).dropna()
    a, b = d.iloc[:, 0].values, d.iloc[:, 1].values
    obs = np.corrcoef(a, b)[0, 1]
    null = [np.corrcoef(np.roll(a, rng.integers(minsk, len(a) - minsk)), b)[0, 1] for _ in range(n)]
    z = (obs - np.mean(null)) / np.std(null)
    return obs, 0.5 * (1 + erf(z / sqrt(2))), len(d)


def fram(lp, hz):
    return lp.shift(-hz) - lp


pris = pd.read_csv("serier/priser_mnd.csv")
spy = np.log(mnd_kurs("SPY"))
xop = np.log(mnd_kurs("XOP"))
alle, tester = [], []
for seg, (omr, kode) in EIA.items():
    print(f"\n==================== {seg}")
    k1, k4 = eia(omr, kode, 1), eia(omr, kode, 4)
    d = pd.concat([k1, k4], axis=1, sort=True).dropna()
    d = d[(d.iloc[:, 0] > 0) & (d.iloc[:, 1] > 0)].resample("ME").last()
    h = 100 * (d.iloc[:, 1] / d.iloc[:, 0] - 1)
    h.index = h.index.to_period("M")
    if seg == "henryhub":
        h = sesongrenset(h)
    p = pris[pris.segment == seg].copy()
    p.index = pd.PeriodIndex(p.t, freq="M")
    lr = np.log(p.nom.astype(float))
    df = pd.DataFrame({"H": h, "lr": lr})
    df["dP3"] = df.lr - df.lr.shift(3)
    df["x1"] = resid(df.H, df.dP3)
    df["x2"] = resid(df.H - df.H.shift(3), df.dP3)

    mer = {}
    for sym in PAPIRER[seg] + ["XOP"]:
        try:
            lp = xop if sym == "XOP" else np.log(mnd_kurs(sym))
        except Exception as e:
            print(f"   {sym}: ingen kurs ({type(e).__name__})"); continue
        for hz in (6, 12):
            mer[(sym, hz)] = (fram(lp, hz) - fram(spy, hz)).reindex(df.index)
        print(f"   {sym:7} kurs fra {lp.index[0]}")
    for hz in (6, 12):
        df[f"kurv_{hz}"] = pd.concat([mer[(s, hz)] for s in PAPIRER[seg] if (s, hz) in mer], axis=1).mean(axis=1)
        df[f"XOP_{hz}"] = mer[("XOP", hz)]
    df = df[df.H.notna()]
    brukt = df[df.kurv_12.notna() & df.x1.notna()]
    print(f"   overlapp kurve og kurv (12 mnd): {brukt.index[0]} til {brukt.index[-1]}, {len(brukt)} mnd")
    mid = brukt.index[len(brukt) // 2]

    for xn, xtxt in (("x1", "H nivaa, renset"), ("x2", "endring i H 3 mnd, renset")):
        print(f"\n   {xtxt}")
        for hz in (6, 12):
            for yn in (f"kurv_{hz}", f"XOP_{hz}") + tuple(f"{s}_{hz}" for s in PAPIRER[seg]):
                if yn.startswith(tuple(PAPIRER[seg])):
                    s = yn.rsplit("_", 1)[0]
                    if (s, hz) not in mer:
                        continue
                    y = mer[(s, hz)]
                else:
                    y = df[yn]
                r, pv, n = placebo_p(df[xn], y)
                if yn == f"kurv_{hz}":
                    dd = pd.concat([df[xn], y], axis=1).dropna()
                    h1 = dd[dd.index < mid].corr().iloc[0, 1]
                    h2 = dd[dd.index >= mid].corr().iloc[0, 1]
                    no = dd.iloc[::hz]
                    rno = no.corr().iloc[0, 1]
                    print(f"      {hz:2} mnd  KURV   r {r:+.2f}  n {n:3}  halvdeler {h1:+.2f} / {h2:+.2f}  "
                          f"ikke-overlapp {rno:+.2f} (n {len(no)})  p {pv:.3f}")
                    if hz == 12:
                        tester.append({"seg": seg, "x": xtxt, "r": r, "h1": h1, "h2": h2, "rno": rno, "p": pv})
                else:
                    print(f"      {hz:2} mnd  {yn.rsplit('_', 1)[0]:7} r {r:+.2f}  n {n:3}  p {pv:.3f}")
    df["segment"] = seg
    alle.append(df)

t = pd.DataFrame(tester).sort_values("p").reset_index(drop=True)
m = len(t)
grense = max([i + 1 for i in range(m) if t.p[i] <= 0.10 * (i + 1) / m], default=0)
t["bh"] = [i < grense for i in range(m)]
t["holder"] = (t.r <= -0.30) & (t.h1 < 0) & (t.h2 < 0) & (t.rno < 0) & (t.p < 0.05) & t.bh
print("\n\nAVGJOERELSE (kurven av papirer, 12 mnd)\n")
for _, r in t.sort_values(["seg", "x"]).iterrows():
    print(f"   {r.seg:9} {r.x:27} r {r.r:+.2f}  p {r.p:.3f}  BH {'ja' if r.bh else 'nei'}  -> "
          f"{'HOLDER' if r.holder else 'holder ikke'}")

pd.concat(alle).reset_index(names="t").to_csv("sonder/kurve_papirer.csv", index=False)
print("\nLagret sonder/kurve_papirer.csv")
