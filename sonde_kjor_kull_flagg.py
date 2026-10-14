# ---------------------------------------------------------------------------
# sonde_kjor_kull_flagg: krymping paa kull, og andre maater aa lage
# bunnflagget for kull (Frodes bestilling 14.10.2026)
#
# BESKRIVENDE, ingen kriterier. Kull har realpris fra 2000 (Verdensbanken,
# australsk termisk kull; foer det aarlige kontraktspriser og avkortet med
# vilje), A fra 2005, og bare to eller tre bunner. Alt som ser bra ut her er
# tilpasset paa samme historikk som det maales paa. En regel herfra kan bare
# provees framover som Challenger.
#
# Reglene (alle maanedlige, punkt i tid):
#   R0 Champion: A raa og A detrendet 80 eller mer.
#   R1 krymping: samme med 75 (det krymping gir kull naar den tilpasses paa
#      2006 og senere: n = 1 episode, beste T 60, 80 + 1/5 * (60 - 80) = 76).
#   R2 bare detrendet: Ad 80 eller mer (raa A paa 26 aar med to topper
#      over 300 USD leser lite billig).
#   R3 rullende: A mot siste ti aar (Ar) og Ad 80 eller mer.
#   R4 tilbud: Ad 80 eller mer og B2 50 eller mer (lite investert; B2 for
#      aar t brukes fra april aaret etter, naar aarsregnskapene er ute).
#   R5 snuoperasjon: Ad 80 eller mer og prisen over snittet siste 3 mnd
#      (fallet har stoppet).
#   R6 Ad 70 eller mer og B2 50 eller mer.
# Utfall: realprisens log-endring 12 og 24 mnd fram, mot snittet for alle
# maaneder. Episoder: ny start etter 12 mnd utenfor.
# ---------------------------------------------------------------------------

import json
import numpy as np
import pandas as pd


def A_raa(v, w=None):
    o = np.full(len(v), np.nan)
    for i in range(59, len(v)):
        y = v[: i + 1] if w is None else v[max(0, i - w + 1): i + 1]
        o[i] = (y <= v[i]).mean()
    return (1 - o) * 100


def A_det(v):
    o = np.full(len(v), np.nan)
    for i in range(59, len(v)):
        y = v[: i + 1]; t = np.arange(i + 1)
        b, a = np.polyfit(t, y, 1)
        r = y - (a + b * t)
        o[i] = (r <= r[i]).mean()
    return (1 - o) * 100


p = pd.read_csv("serier/priser_mnd.csv")
g = p[p.segment == "kull"]
idx = pd.PeriodIndex(g.t, freq="M")
lv = np.log(g.real.astype(float).values)
df = pd.DataFrame({"real": g.real.astype(float).values, "lv": lv, "A": A_raa(lv), "Ad": A_det(lv),
                   "Ar": A_raa(lv, 120)}, index=idx)
for h in (12, 24):
    df[f"u{h}"] = df.lv.shift(-h) - df.lv
df["over3"] = df.real > df.real.rolling(3).mean()
b = json.load(open("b_capex.json", encoding="utf-8"))["metaller"]["kull"]
b2 = {a: v for a, v in zip(b["aar"], b["B2"]) if v is not None}
df["B2"] = [b2.get(t.year - 1 if t.month >= 4 else t.year - 2, np.nan) for t in df.index]

print("1. KULL PER HALVAAR (realpris i dagens USD, A, Ad, Ar, B2 i bruk)\n")
for t in df.index:
    if t.month in (1, 7) and t.year >= 2004:
        r = df.loc[t]
        print(f"   {t}  {r.real:7.1f}  A {r.A:5.1f}  Ad {r.Ad:5.1f}  Ar {r.Ar:5.1f}  B2 {r.B2:5.1f}"
              f"  u24 {100 * r.u24:+6.1f} %")
r = df.iloc[-1]
print(f"   {df.index[-1]}  {r.real:7.1f}  A {r.A:5.1f}  Ad {r.Ad:5.1f}  Ar {r.Ar:5.1f}  B2 {r.B2:5.1f}  (siste)")

REGLER = {
    "R0 Champion (A og Ad 80)": (df.A >= 80) & (df.Ad >= 80),
    "R1 krymping (A og Ad 75)": (df.A >= 75) & (df.Ad >= 75),
    "R2 bare Ad 80": df.Ad >= 80,
    "R3 Ar og Ad 80": (df.Ar >= 80) & (df.Ad >= 80),
    "R4 Ad 80 og B2 50": (df.Ad >= 80) & (df.B2 >= 50),
    "R5 Ad 80 og over 3 mnd snitt": (df.Ad >= 80) & df.over3,
    "R6 Ad 70 og B2 50": (df.Ad >= 70) & (df.B2 >= 50),
}
gyldig = df.A.notna()
mu = {h: df[f"u{h}"][gyldig].mean() for h in (12, 24)}
print(f"\n2. REGLENE (snitt for alle maaneder: 12 mnd {100 * mu[12]:+.1f} %, 24 mnd {100 * mu[24]:+.1f} %)\n")
for navn, z in REGLER.items():
    z = z & gyldig
    st, sist = [], -99
    for i, x in enumerate(z.values):
        if x:
            if i - sist > 12:
                st.append(i)
            sist = i
    u12, u24 = df.u12[z].dropna(), df.u24[z].dropna()
    print(f"   {navn:32} {int(z.sum()):3} mnd, {len(st)} episoder, i sonen naa: {'ja' if z.iloc[-1] else 'nei'}")
    if len(u24):
        print(f"      snitt 12 mnd {100 * u12.mean():+6.1f} %, 24 mnd {100 * u24.mean():+6.1f} %, "
              f"andel positive 24 mnd {100 * (u24 > 0).mean():.0f} %")
    for i in st:
        t = df.index[i]; e = df.iloc[i]
        slutt = df.index[min(len(df) - 1, i + int(z.iloc[i:].values.argmin() if not z.iloc[i:].all() else len(z) - i) - 1)]
        print(f"      start {t} (A {e.A:.0f}, Ad {e.Ad:.0f}, pris {e.real:.0f}) til {slutt}: "
              f"12 mnd {100 * e.u12:+.0f} %, 24 mnd {100 * e.u24:+.0f} %" if pd.notna(e.u24) else
              f"      start {t} (A {e.A:.0f}, Ad {e.Ad:.0f}, pris {e.real:.0f}): utfall ikke kjent ennaa")

print("\n3. HVA SKAL TIL FOR AT KULL KOMMER I SONEN NAA (realpris som gir A og Ad paa 80)\n")
v = df.lv.values
for T in (80, 75, 70):
    q = np.quantile(v, (100 - T) / 100)
    t = np.arange(len(v)); bb, aa = np.polyfit(t, v, 1); res = v - (aa + bb * t)
    qd = np.quantile(res, (100 - T) / 100) + aa + bb * (len(v) - 1)
    print(f"   T {T}: A krever under {np.exp(q):6.1f}, Ad krever under {np.exp(qd):6.1f} USD (i dag {df.real.iloc[-1]:.1f})")

df.reset_index(names="t").to_csv("sonder/kull_flagg.csv", index=False)
print("\nLagret sonder/kull_flagg.csv")
