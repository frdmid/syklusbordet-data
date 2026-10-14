# ---------------------------------------------------------------------------
# sonde_kjor_a_terskel: er A 80 for rigid paa tvers av raavarer? Tre maater aa
# tilpasse terskelen mot den felles 80 (Frodes bestilling 14.10.2026)
#
# Bunnsonen er A raa og A detrendet begge paa terskelen T eller mer (som
# Championen med T = 80). A regnes som paa bordet fra realprisen i
# serier/priser_mnd.csv (18 raavaresegmenter; skipsfart har ikke maanedsserie
# der og er ikke med).
#
# Utfall: realprisens log-endring de neste 24 mnd (avgjoer) og 12 mnd (vises).
# Papirene har for kort historikk, saa raavaren selv maales, ikke papirer mot
# OSEBX. Maal per raavare: J = summen over maaneder i sonen av (utfall minus
# raavarens snittutfall i samme periode), delt paa antall maaneder i perioden.
# J belonner baade treffsikkerhet og at sonen faktisk slaar til; for hoey T
# gir faa maaneder, for lav T gir svakt snitt.
#
# Variantene (rutenett for T: 60, 65, ..., 95):
#   V0 felles: T = 80 for alle.
#   V1 grupper: en T per gruppe (energi, metall, jordbruk), den som gir
#      hoeyest samlet J i treningsdelen. 3 frie tall.
#   V2 egenskap: T = 80 + b * z, der z er standardisert log halveringstid for
#      realprisen mot trenden (AR(1) paa detrendet log pris, treningsdelen),
#      klippet til 60..95. b velges i treningsdelen fra -15..15. 1 fritt tall.
#   V3 krymping: hver raavare faar sin beste T i treningsdelen, trukket mot 80
#      med vekt n / (n + 4), der n er antall episoder med T = 80 i
#      treningsdelen (episode: ny start etter 12 mnd utenfor sonen). Tallet 4
#      er satt her og tilpasses ikke. Raavarer uten treningsdata faar 80.
#
# Utvalg: delt i 2006-01. Retning 1: tilpass paa foer 2006, test paa 2006 og
# senere. Retning 2: tilpass paa 2006 og senere, test paa foer 2006. Utfall som
# strekker seg over delingen telles i delen der maaneden ligger.
#
# KRITERIER (satt foer kjoering, 14.10.2026). En variant holder hvis, paa 24
# mnd og i BEGGE retninger:
#   (a) samlet J i testdelen (sum over raavarer) er hoeyere enn for V0,
#   (b) blant raavarene der varianten gir en annen T enn 80, er J bedre enn V0
#       i flertallet, og
#   (c) (a) holder fortsatt naar raavaren med stoerst gevinst tas ut.
# Holder flere, foretrekkes den med faerrest frie tall. Skriver ingenting til
# dashbordet. Utdata sonder/a_terskel.csv.
# ---------------------------------------------------------------------------

import numpy as np
import pandas as pd

GRID = list(range(60, 100, 5))
GRUPPE = {"energi": ["brent", "wti", "henryhub", "ttf", "kull", "uran", "oljeservice"],
          "metall": ["gold", "kobber", "aluminium", "nikkel", "sink", "bly", "tinn", "jernmalm"],
          "jordbruk": ["kakao", "palmeolje", "laks"]}
GR = {s: g for g, ss in GRUPPE.items() for s in ss}
DEL = pd.Period("2006-01", "M")
K = 4


def A_raa(v):
    o = np.full(len(v), np.nan)
    for i in range(59, len(v)):
        o[i] = (v[: i + 1] <= v[i]).mean()
    return (1 - o) * 100


def A_det(v):
    o = np.full(len(v), np.nan)
    for i in range(59, len(v)):
        y = v[: i + 1]; t = np.arange(i + 1)
        b, a = np.polyfit(t, y, 1)
        r = y - (a + b * t)
        o[i] = (r <= r[i]).mean()
    return (1 - o) * 100


def episoder(z):
    n, sist = 0, -99
    for i, x in enumerate(z):
        if x:
            if i - sist > 12:
                n += 1
            sist = i
    return n


def halveringstid(lv):
    if len(lv) < 60:
        return np.nan
    t = np.arange(len(lv)); b, a = np.polyfit(t, lv, 1); r = lv - (a + b * t)
    phi = np.polyfit(r[:-1], r[1:], 1)[0]
    return np.log(0.5) / np.log(phi) if 0 < phi < 1 else 600.0


p = pd.read_csv("serier/priser_mnd.csv")
D = {}
for s, g in p.groupby("segment"):
    if s not in GR:
        continue
    idx = pd.PeriodIndex(g.t, freq="M")
    lv = np.log(g.real.astype(float).values)
    df = pd.DataFrame({"lv": lv, "A": A_raa(lv), "Ad": A_det(lv)}, index=idx)
    for h in (12, 24):
        df[f"u{h}"] = df.lv.shift(-h) - df.lv
    D[s] = df
print(f"{len(D)} raavarer: {', '.join(D)}")


def J(df, T, h, maske):
    d = df[maske & df[f"u{h}"].notna() & df.A.notna()]
    if len(d) == 0:
        return 0.0, 0
    z = (d.A >= T) & (d.Ad >= T)
    mu = d[f"u{h}"].mean()
    return float((d[f"u{h}"][z] - mu).sum() / len(d)), int(z.sum())


def tilpass(tren, h):
    """Returnerer T per raavare for V0..V3, tilpasset paa treningsmasken."""
    ut = {"V0": {s: 80 for s in D}}
    # V1 grupper
    v1 = {}
    for g, ss in GRUPPE.items():
        best = max(GRID, key=lambda T: (sum(J(D[s], T, h, tren(D[s]))[0] for s in ss), -abs(T - 80)))
        for s in ss:
            v1[s] = best
    ut["V1"] = v1
    # V2 egenskap
    hl = {s: halveringstid(D[s].lv[tren(D[s])].values) for s in D}
    lhl = pd.Series({s: np.log(x) for s, x in hl.items() if np.isfinite(x)})
    z = ((lhl - lhl.mean()) / lhl.std()).to_dict()
    def v2(b):
        return {s: int(np.clip(round((80 + b * z[s]) / 5) * 5, 60, 95)) if s in z else 80 for s in D}
    bb = max(range(-15, 16, 5), key=lambda b: (sum(J(D[s], v2(b)[s], h, tren(D[s]))[0] for s in D), -abs(b)))
    ut["V2"] = v2(bb); ut["_b"] = bb; ut["_hl"] = hl
    # V3 krymping
    v3, n3 = {}, {}
    for s in D:
        m = tren(D[s]); d = D[s][m & D[s].A.notna()]
        n = episoder(((d.A >= 80) & (d.Ad >= 80)).values) if len(d) else 0
        if n == 0:
            v3[s] = 80; n3[s] = 0; continue
        Ti = max(GRID, key=lambda T: (J(D[s], T, h, m)[0], -abs(T - 80)))
        v3[s] = int(round((80 + n / (n + K) * (Ti - 80)) / 5) * 5); n3[s] = (n, Ti)
    ut["V3"] = v3; ut["_n3"] = n3
    return ut


rader, sammen = [], {}
for retning, (tren, test) in {"1 (tilpass foer 2006, test etter)": (lambda d: d.index < DEL, lambda d: d.index >= DEL),
                              "2 (tilpass etter 2006, test foer)": (lambda d: d.index >= DEL, lambda d: d.index < DEL)}.items():
    for h in (24, 12):
        T = tilpass(tren, h)
        print(f"\n==================== Retning {retning}, {h} mnd")
        print(f"   V2: b = {T['_b']}")
        print(f"   {'raavare':12} {'V0':>4} {'V1':>4} {'V2':>4} {'V3':>4}   hl(mnd) V3(n, beste)  |  J test x100: V0 V1 V2 V3  (mnd i sonen V0)")
        tot = {v: 0.0 for v in ("V0", "V1", "V2", "V3")}
        per = {v: {} for v in tot}
        for s in D:
            js = {}
            for v in tot:
                j, n = J(D[s], T[v][s], h, test(D[s]))
                js[v] = j; tot[v] += j; per[v][s] = j
                if v == "V0":
                    n0 = n
            hl = T["_hl"][s]
            print(f"   {s:12} {T['V0'][s]:4} {T['V1'][s]:4} {T['V2'][s]:4} {T['V3'][s]:4}   "
                  f"{hl:7.0f} {str(T['_n3'][s]):12} |  " + "  ".join(f"{100 * js[v]:+6.2f}" for v in tot) + f"  ({n0})")
            rader.append({"retning": retning[0], "h": h, "segment": s, **{f"T_{v}": T[v][s] for v in tot},
                          **{f"J_{v}": js[v] for v in tot}})
        print("   SUM x100      " + "  ".join(f"{v} {100 * tot[v]:+.2f}" for v in tot))
        sammen[(retning[0], h)] = (T, tot, per)


print("\n\nAVGJOERELSE (24 mnd, begge retninger)\n")
for v, navn, fri in (("V1", "grupper", 3), ("V2", "egenskap (halveringstid)", 1), ("V3", "krymping", "0 tilpasset")):
    ok_alle, tekst = True, []
    for r in ("1", "2"):
        T, tot, per = sammen[(r, 24)]
        a = tot[v] > tot["V0"]
        ulik = [s for s in D if T[v][s] != 80]
        bedre = sum(per[v][s] > per["V0"][s] for s in ulik)
        b = len(ulik) > 0 and bedre > len(ulik) / 2
        gev = {s: per[v][s] - per["V0"][s] for s in D}
        topp = max(gev, key=gev.get)
        c = (tot[v] - per[v][topp]) > (tot["V0"] - per["V0"][topp])
        ok = a and b and c
        ok_alle &= ok
        tekst.append(f"retning {r}: sum {100 * tot[v]:+.2f} mot {100 * tot['V0']:+.2f} ({'a ok' if a else 'a nei'}), "
                     f"bedre i {bedre} av {len(ulik)} med annen T ({'b ok' if b else 'b nei'}), "
                     f"uten {topp} ({'c ok' if c else 'c nei'})")
    print(f"   {v} {navn} [{fri} frie tall]: {'HOLDER' if ok_alle else 'HOLDER IKKE'}")
    for t in tekst:
        print(f"      {t}")

pd.DataFrame(rader).to_csv("sonder/a_terskel.csv", index=False)
print("\nLagret sonder/a_terskel.csv")
