# ---------------------------------------------------------------------------
# sonde_kjor_jernmalm_flagg: bunnflagget for jernmalm, krymping og andre
# regler (Frodes bestilling 14.10.2026), samme oppsett som
# sonde_kjor_kull_flagg.
#
# BESKRIVENDE, ingen kriterier. Jernmalm har realpris fra 2010 (Verdensbanken,
# 62 % Fe; foer det aarlig forhandlet referansepris og avkortet med vilje), A
# fra 2015, og bare en eller to bunner. Alt som ser bra ut her er tilpasset
# paa samme historikk som det maales paa. B2 for jernmalm har ligget paa 0
# til 43, saa reglene med B2 slaar knapt til.
#
# Reglene er de samme som for kull, pluss R7 rullende A 95 og Ad 80 (regelen
# i challenger_kull_ar95_v1). Rullende A er her nesten lik raa A, fordi
# serien bare er 16 aar lang.
# ---------------------------------------------------------------------------

import json
import numpy as np
import pandas as pd

SEG = "jernmalm"


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
g = p[p.segment == SEG]
idx = pd.PeriodIndex(g.t, freq="M")
lv = np.log(g.real.astype(float).values)
df = pd.DataFrame({"real": g.real.astype(float).values, "lv": lv, "A": A_raa(lv), "Ad": A_det(lv),
                   "Ar": A_raa(lv, 120)}, index=idx)
for h in (12, 24):
    df[f"u{h}"] = df.lv.shift(-h) - df.lv
df["over3"] = df.real > df.real.rolling(3).mean()
b = json.load(open("b_capex.json", encoding="utf-8"))["metaller"][SEG]
b2 = {a: v for a, v in zip(b["aar"], b["B2"]) if v is not None}
df["B2"] = [b2.get(t.year - 1 if t.month >= 4 else t.year - 2, np.nan) for t in df.index]

print("1. JERNMALM PER HALVAAR (realpris i dagens USD, A, Ad, Ar, B2 i bruk)\n")
for t in df.index:
    if t.month in (1, 7) and t.year >= 2014:
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
    "R7 Ar 95 og Ad 80": (df.Ar >= 95) & (df.Ad >= 80),
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

print("\n3. HVA SKAL TIL FOR AT JERNMALM KOMMER I SONEN NAA (realpris som gir A og Ad paa 80)\n")
v = df.lv.values
for T in (80, 75, 70):
    q = np.quantile(v, (100 - T) / 100)
    t = np.arange(len(v)); bb, aa = np.polyfit(t, v, 1); res = v - (aa + bb * t)
    qd = np.quantile(res, (100 - T) / 100) + aa + bb * (len(v) - 1)
    print(f"   T {T}: A krever under {np.exp(q):6.1f}, Ad krever under {np.exp(qd):6.1f} USD (i dag {df.real.iloc[-1]:.1f})")

df.reset_index(names="t").to_csv("sonder/jernmalm_flagg.csv", index=False)
print("\nLagret sonder/jernmalm_flagg.csv")
