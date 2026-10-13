# ---------------------------------------------------------------------------
# sonde_kjor_kurve_a: forklarer terminkurven A, og varsler endringer i kurven
# at A snur? (Frodes bestilling 13.10.2026, WTI og Henry Hub)
#
# Data: EIA, NYMEX kontrakt 1 og 4, daglig (WTI fra 1983, Henry Hub fra 1994,
# begge til april 2024). Maanedsslutt. Helning H = (K4 / K1 - 1) * 100,
# positiv er contango. Henry Hub har sterk sesong i kurven; der brukes H minus
# snittet av H i samme kalendermaaned, regnet bare paa det som var kjent da
# (minst fem tidligere aar for den maaneden). A regnes som paa bordet, fra
# realprisen i serier/priser_mnd.csv: A raa = 100 minus persentilen mot hele
# egen historikk, A detrendet = det samme mot trenden. HOEY A ER BILLIG.
#
# Forventet retning: contango hoerer sammen med fulle lagre og lav pris, altsaa
# hoey A. Varselet er at kurven flytter seg FOER A: kurven mot contango varsler
# at A stiger (prisen faller videre), kurven mot backwardation at A faller.
#
# KRITERIER (satt foer kjoering, 13.10.2026)
# Test 1, samtidig: Spearman mellom H og A. Beskrivende, intet kriterium.
# Test 2, varsel: x = endring i H siste 3 mnd, renset for endringen i log
#   realpris siste 3 mnd (residual fra regresjon). y = A om 12 mnd minus A naa.
#   Holder for en raavare hvis, for BAADE A raa og A detrendet:
#   (a) korrelasjonen er 0,30 eller mer og positiv,
#   (b) samme fortegn i begge halvdelene av perioden,
#   (c) samme fortegn i ikke-overlappende utvalg (hver 12. maaned),
#   (d) p under 0,05 mot sirkulaert forskjoevet x (placebo, minst 24 mnd
#       forskyvning, 2000 trekk, p fra normalhalen), og
#   (e) bestaar Benjamini-Hochberg paa 10 % over de fire testene (2 raavarer,
#       2 A-varianter) paa 12 mnd.
#   6 mnd vises, avgjoer ikke.
# Test 3, hendelser (bare A raa): bunnsone A 80 eller mer der H har falt
#   siste 3 mnd (contango krymper) mot andre maaneder med A 80 eller mer:
#   andel der A faller 20 poeng eller mer innen 12 mnd. Toppsone A 20 eller
#   lavere der H har steget (backwardation svekkes): andel der A stiger 20
#   poeng eller mer. Holder hvis treffandelen er minst 15 pp hoeyere enn i
#   kontrollmaanedene, hendelsene kommer fra minst tre episoder (12 mnd
#   mellom), og forskjellen har samme fortegn i begge halvdelene.
#
# Skriver ingenting til dashbordet. Utdata sonder/kurve_a.csv.
# ---------------------------------------------------------------------------

import io, subprocess, sys, time
import numpy as np
import pandas as pd
import requests

try:
    import xlrd  # noqa
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "xlrd"], check=False)

UA = {"User-Agent": "Syklusbordet (frdmid)"}
EIA = {"wti": ("pet", "RCLC"), "henryhub": ("ng", "RNGC")}
MIN_HIST = 60
rng = np.random.default_rng(20261013)


def eia(omr, kode, i):
    u = f"https://www.eia.gov/dnav/{omr}/hist_xls/{kode}{i}d.xls"
    for f in range(3):
        try:
            r = requests.get(u, headers=UA, timeout=60)
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


def expanding_pct(v):
    out = np.full(len(v), np.nan)
    for i in range(len(v)):
        if i + 1 >= MIN_HIST:
            out[i] = (v[: i + 1] <= v[i]).sum() / (i + 1)
    return (1 - out) * 100


def expanding_pct_detrend(v, minn=60):
    out = np.full(len(v), np.nan)
    for i in range(minn - 1, len(v)):
        y = v[: i + 1]
        t = np.arange(i + 1)
        b, a = np.polyfit(t, y, 1)
        r = y - (a + b * t)
        out[i] = (r <= r[i]).sum() / len(r)
    return (1 - out) * 100


def sesongrenset(h):
    """H minus snittet av H i samme kalendermaaned, bare fra tidligere aar."""
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
    d = pd.concat([x, y], axis=1).dropna()
    a, b = d.iloc[:, 0].values, d.iloc[:, 1].values
    obs = np.corrcoef(a, b)[0, 1]
    null = [np.corrcoef(np.roll(a, rng.integers(minsk, len(a) - minsk)), b)[0, 1] for _ in range(n)]
    z = (obs - np.mean(null)) / np.std(null)
    from math import erf, sqrt
    return obs, 0.5 * (1 - erf(z / sqrt(2)))


def episoder(datoer, gap=12):
    n, sist = 0, None
    for t in sorted(datoer):
        if sist is None or (t.year - sist.year) * 12 + t.month - sist.month > gap:
            n += 1
        sist = t
    return n


pris = pd.read_csv("serier/priser_mnd.csv")
alle, test2, test3 = [], [], {}
for seg, (omr, kode) in EIA.items():
    print(f"\n==================== {seg}")
    k1, k4 = eia(omr, kode, 1), eia(omr, kode, 4)
    d = pd.concat([k1, k4], axis=1).dropna()
    d = d[(d.iloc[:, 0] > 0) & (d.iloc[:, 1] > 0)].resample("ME").last()
    h = 100 * (d.iloc[:, 1] / d.iloc[:, 0] - 1)
    h.index = h.index.to_period("M")
    if seg == "henryhub":
        h = sesongrenset(h)
    p = pris[pris.segment == seg].copy()
    p.index = pd.PeriodIndex(p.t, freq="M")
    lr = np.log(p.real.astype(float))
    A = pd.Series(expanding_pct(lr.values), index=lr.index)
    Ad = pd.Series(expanding_pct_detrend(lr.values), index=lr.index)
    df = pd.DataFrame({"H": h, "A": A, "Ad": Ad, "lr": lr}).dropna(subset=["lr"])
    df["dH3"] = df.H - df.H.shift(3)
    df["dP3"] = df.lr - df.lr.shift(3)
    df["x"] = resid(df.dH3, df.dP3)
    for v in ("A", "Ad"):
        for hz in (6, 12):
            df[f"y_{v}_{hz}"] = df[v].shift(-hz) - df[v]
    df["A_min12"] = df.A[::-1].rolling(12, min_periods=1).min()[::-1].shift(-1)
    df["A_max12"] = df.A[::-1].rolling(12, min_periods=1).max()[::-1].shift(-1)
    df = df[df.H.notna() & df.A.notna()]
    df["segment"] = seg
    alle.append(df)
    print(f"   periode {df.index[0]} til {df.index[-1]}, {len(df)} mnd. Andel contango {100 * (df.H > 0).mean():.0f} %"
          + (" (sesongrenset H)" if seg == "henryhub" else ""))

    print("\n   Test 1, samtidig (Spearman)")
    for v in ("A", "Ad"):
        print(f"      H mot {v:2}: {df.H.rank().corr(df[v].rank()):+.2f}")
    print(f"      H mot endring i pris siste 3 mnd (dH3 mot dP3): {df.dH3.corr(df.dP3):+.2f}  (det som renses bort)")

    print("\n   Test 2, varsel: renset endring i H siste 3 mnd mot endring i A framover")
    mid = df.index[len(df) // 2]
    for v in ("A", "Ad"):
        for hz in (6, 12):
            y = df[f"y_{v}_{hz}"]
            r, pv = placebo_p(df.x, y)
            h1 = df.x[df.index < mid].corr(y[df.index < mid])
            h2 = df.x[df.index >= mid].corr(y[df.index >= mid])
            no = df.iloc[::hz]
            rno = no.x.corr(no[f"y_{v}_{hz}"])
            ra = df.dH3.corr(y)
            print(f"      {v:2} {hz:2} mnd: r {r:+.2f} (urenset {ra:+.2f}), halvdeler {h1:+.2f} / {h2:+.2f}, "
                  f"ikke-overlapp {rno:+.2f} (n {no[f'y_{v}_{hz}'].notna().sum()}), p {pv:.3f}")
            if hz == 12:
                test2.append({"seg": seg, "v": v, "r": r, "h1": h1, "h2": h2, "rno": rno, "p": pv})

    print("\n   Test 3, hendelser (A raa)")
    res3 = []
    for navn, sone, kurve, utfall in (
            ("bunn: A 80+ og contango krymper, A faller 20+ innen 12 mnd", df.A >= 80, df.dH3 < 0,
             df.A - df.A_min12 >= 20),
            ("topp: A 20 eller lavere og backwardation svekkes, A stiger 20+ innen 12 mnd", df.A <= 20, df.dH3 > 0,
             df.A_max12 - df.A >= 20)):
        gyldig = df.index <= df.index[-1] - 12
        hend, kontr = sone & kurve & gyldig, sone & ~kurve & df.dH3.notna() & gyldig
        if hend.sum() == 0 or kontr.sum() == 0:
            print(f"      {navn}: for faa maaneder (hendelser {hend.sum()}, kontroll {kontr.sum()})")
            res3.append(False); continue
        a, b = utfall[hend].mean() * 100, utfall[kontr].mean() * 100
        ep = episoder(df.index[hend])
        diffs = []
        for halv in (df.index < mid, df.index >= mid):
            hh, kk = hend & halv, kontr & halv
            diffs.append(utfall[hh].mean() * 100 - utfall[kk].mean() * 100 if hh.sum() and kk.sum() else np.nan)
        ok = (a - b >= 15) and ep >= 3 and all(np.isfinite(diffs)) and all(x > 0 for x in diffs)
        print(f"      {navn}:\n         {a:.0f} % av {hend.sum()} hendelsesmnd ({ep} episoder) mot {b:.0f} % av "
              f"{kontr.sum()} kontrollmnd, forskjell {a - b:+.0f} pp; halvdeler {diffs[0]:+.0f} / {diffs[1]:+.0f} pp"
              f" -> {'HOLDER' if ok else 'holder ikke'}")
        res3.append(ok)
    test3[seg] = res3

# Benjamini-Hochberg over de fire 12-mnd-testene
t = pd.DataFrame(test2).sort_values("p").reset_index(drop=True)
m = len(t)
grense = max([i + 1 for i in range(m) if t.p[i] <= 0.10 * (i + 1) / m], default=0)
t["bh"] = [i < grense for i in range(m)]
t["holder"] = (t.r >= 0.30) & (t.h1 > 0) & (t.h2 > 0) & (t.rno > 0) & (t.p < 0.05) & t.bh

print("\n\nAVGJOERELSE (12 mnd)\n")
for _, r in t.iterrows():
    print(f"   {r.seg:9} {r.v:2}: r {r.r:+.2f}, p {r.p:.3f}, BH {'ja' if r.bh else 'nei'} -> "
          f"{'holder' if r.holder else 'holder ikke'}")
print()
for seg in EIA:
    t2 = t[t.seg == seg].holder.all()
    print(f"   {seg}: test 2 (varsel) {'HOLDER' if t2 else 'HOLDER IKKE'}; test 3 bunn "
          f"{'holder' if test3[seg][0] else 'holder ikke'}, topp {'holder' if test3[seg][1] else 'holder ikke'}")

pd.concat(alle).reset_index(names="t").to_csv("sonder/kurve_a.csv", index=False)
print("\nLagret sonder/kurve_a.csv")
