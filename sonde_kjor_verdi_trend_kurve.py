# ---------------------------------------------------------------------------
# sonde_kjor_verdi_trend_kurve: billig og stramt marked samtidig, og betyr
# regimet noe for avkastningen ved signal? (Frodes bestilling 03.11.2026,
# punkt 5 i traderforslagene)
#
# Data: serier/priser_mnd.csv (realpris per raavaresegment, maanedssnitt),
# EIA NYMEX kontrakt 1 og 4 for WTI og Henry Hub (maanedsslutt, til 2024),
# ^VIX fra Yahoo (fra 1990). Utfall: endring i log realpris de neste h
# maanedene for raavaren selv (ikke papirene), og det samme minus snittet av
# alle raavarer med data den maaneden (tverrsnitt).
#
# SIGNALER (punkt i tid, valgt foer kjoering):
#   S0  bunnsone: A raa >= 80 og A detrendet >= 80 (som Championen)
#   S1  S0 og realprisen hoeyere enn for 12 mnd siden (billig og stigende)
#   S2  S0 og realprisen lavere enn for 12 mnd siden (billig og fallende)
#   S3  tverrsnitt: i oeverste tredjedel av A raa OG oeverste tredjedel av
#       12 mnd endring blant raavarene den maaneden (minst 6 raavarer)
#   K1  WTI og Henry Hub: A raa >= 80 og backwardation (K4 under K1; for Henry
#       Hub sesongrenset helning under 0)
#   K2  WTI og Henry Hub: A raa >= 80 og contango
# REGIMER:
#   R1  bred nedgang: 40 % eller faerre av raavarene har hoeyere realpris enn
#       12 mnd foer (samme maal som regimepanelet, minst 5 raavarer)
#   R2  uro: VIX (maanedssnitt) i oeverste tredjedel mot det som var kjent
#       da (minst 36 mnd)
#
# DEL 1, virker signalet (h 6 og 12 mnd). Holder hvis, i 1965 til 2014 og
# for BAADE absolutt og tverrsnitt:
#   (a) snittet i signalmaanedene er minst 5 prosentpoeng per 12 mnd (2,5 per
#       6 mnd) hoeyere enn i alle andre maaneder, p under 0,05 mot sirkulaert
#       forskjoevet signal (hele panelet samme forskyvning, minst 24 mnd,
#       2000 trekk),
#   (b) positiv forskjell i begge halvdelene,
#   (c) minst 5 episoder (ny episode etter 12 mnd uten signal) fra minst 3
#       raavarer (K: fra begge), og
#   (d) Benjamini-Hochberg paa 10 % over alle testene i del 1.
#   I tillegg S1 mot S2 direkte (snitt S1 minus snitt S2, samme krav a til d,
#   placebo ved aa bytte merkene S1 og S2 innen hver episode tilfeldig).
# DEL 2, betyr regimet noe (S0 til S3, h 6, 12 og 24 mnd, bare absolutt):
#   forskjellen i snitt mellom signalmaaneder i regimet og utenfor. Holder
#   hvis |forskjellen| er minst 5 pp per 12 mnd, p under 0,05 tosidig mot
#   sirkulaert forskjoevet regimeserie (minst 24 mnd), samme fortegn i begge
#   halvdelene, minst 3 episoder i hver gruppe, og Benjamini-Hochberg paa
#   10 % over del 2. R2 avgjoeres paa 1993 til 2014 (VIX fra 1990, 36 mnd).
#   Kjent fra foer: sonde_kjor_regime_flagg fant +33 % mot -3 % over 24 mnd
#   for Championens flagg i bred nedgang, men ikke paa 1 til 12 mnd.
# 2015 til 2026 vises, avgjoer ikke. Skriver ingenting til dashbordet.
# Utdata sonder/verdi_trend_kurve.csv.
# ---------------------------------------------------------------------------

import io, time
import numpy as np
import pandas as pd
import requests

rng = np.random.default_rng(20261103)
UA = {"User-Agent": "Syklusbordet (frdmid)"}
UA_Y = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/124.0 Safari/537.36"}
MIN_HIST = 60
FRA, MIDT_TIL = pd.Period("1965-01", "M"), pd.Period("2014-12", "M")
NYTT = (pd.Period("2015-01", "M"), pd.Period("2026-12", "M"))


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


def toppen(s, minn=36):
    v = s.values; ut = np.full(len(v), np.nan)
    for i in range(len(v)):
        h = v[: i + 1]; h = h[np.isfinite(h)]
        if np.isfinite(v[i]) and len(h) >= minn:
            ut[i] = float((h <= v[i]).mean() >= 2 / 3)
    return pd.Series(ut, index=s.index)


def eia(omr, kode, i):
    u = f"https://www.eia.gov/dnav/{omr}/hist_xls/{kode}{i}d.xls"
    r = None
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
    df = data.dropna(); df = df[pd.to_datetime(df.iloc[:, 0], errors="coerce").notna()]
    s = pd.Series(pd.to_numeric(df.iloc[:, 1], errors="coerce").values, index=pd.to_datetime(df.iloc[:, 0])).dropna()
    s = s.resample("ME").last(); s.index = s.index.to_period("M")
    return s


def vix():
    r = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/%5EVIX",
                     params={"period1": 0, "period2": int(time.time()), "interval": "1d"}, headers=UA_Y, timeout=60)
    res = r.json()["chart"]["result"][0]
    s = pd.Series(res["indicators"]["quote"][0]["close"], index=pd.to_datetime(res["timestamp"], unit="s")).dropna()
    s = s.resample("ME").mean(); s.index = s.index.to_period("M")
    return s


# ------------------------------------------------------------------ panelet
p = pd.read_csv("serier/priser_mnd.csv")
p = p[~p.segment.str.startswith("ship_")]
real = p.pivot(index="t", columns="segment", values="real").astype(float).sort_index()
real.index = pd.PeriodIndex(real.index, freq="M")
real = real[real.index <= real.dropna(how="all").index[-1]]
lr = np.log(real)
A = pd.DataFrame(np.nan, index=lr.index, columns=lr.columns); Ad = A.copy()
for c in lr.columns:
    s = lr[c].dropna()
    A.loc[s.index, c] = expanding_pct(s.values)
    Ad.loc[s.index, c] = expanding_pct_detrend(s.values)
d12 = lr - lr.shift(12)
gyldig = A.notna() & d12.notna()

bunn = (A >= 80) & (Ad >= 80) & gyldig
SIG = {"S0 bunnsone": bunn, "S1 bunnsone og stigende": bunn & (d12 > 0), "S2 bunnsone og fallende": bunn & (d12 < 0)}
nA, nT = A.where(gyldig).rank(axis=1, pct=True), d12.where(gyldig).rank(axis=1, pct=True)
nok = gyldig.sum(axis=1) >= 6
SIG["S3 tverrsnitt billig og stigende"] = ((nA > 2 / 3) & (nT > 2 / 3)).mul(nok, axis=0) & gyldig

kurve = pd.DataFrame(np.nan, index=lr.index, columns=lr.columns)
for seg, (omr, kode) in {"wti": ("pet", "RCLC"), "henryhub": ("ng", "RNGC")}.items():
    h = (eia(omr, kode, 4) / eia(omr, kode, 1) - 1) * 100
    if seg == "henryhub":
        ut = pd.Series(np.nan, index=h.index)
        for t in h.index:
            f = h[(h.index < t) & (h.index.month == t.month)]
            if len(f) >= 5:
                ut[t] = h[t] - f.mean()
        h = ut
    kurve[seg] = h.reindex(lr.index)
billig = (A >= 80) & gyldig
SIG["K1 billig og backwardation"] = billig & (kurve < 0)
SIG["K2 billig og contango"] = billig & (kurve > 0)
KURVE_SEG = ["wti", "henryhub"]

bredde = ((d12 > 0) & gyldig).sum(axis=1) / gyldig.sum(axis=1)
bredde[gyldig.sum(axis=1) < 5] = np.nan
v = vix()
REG = {"R1 bred nedgang": (bredde <= 0.4).astype(float).where(bredde.notna()),
       "R2 uro (VIX oeverste tredjedel)": toppen(v).reindex(lr.index).astype(float)}


def utfall(h, rel):
    y = lr.shift(-h) - lr
    if rel:
        y = y.sub(y.mean(axis=1), axis=0)
    return y


def episoder(sig):
    n, segs = 0, set()
    for c in sig.columns:
        m = sig.index[sig[c].fillna(False).astype(bool)]
        forr = None
        for t in m:
            if forr is None or (t - forr).n > 12:
                n += 1; segs.add(c)
            forr = t
    return n, len(segs)


def periode(df, fra, til):
    return df[(df.index >= fra) & (df.index <= til)]


def snitt_diff(sig, y):
    s, yy = sig.values, y.values
    ok = np.isfinite(yy)
    a, b = yy[ok & s], yy[ok & ~s]
    return (a.mean() - b.mean() if len(a) and len(b) else np.nan), len(a)


def del1(navn, sig, h, rel, fra, til, segs=None):
    y = utfall(h, rel)
    if segs:
        sig, y = sig[segs], y[segs]
    sig = periode(sig.fillna(False).astype(bool), fra, til); y = periode(y, fra, til).where(gyldig)
    diff, n = snitt_diff(sig, y)
    if not n:
        return None
    S, Y = sig.values, y.values
    null = []
    for _ in range(2000):
        k = rng.integers(24, len(S) - 24)
        null.append(snitt_diff(pd.DataFrame(np.roll(S, k, axis=0)), pd.DataFrame(Y))[0])
    null = np.array(null); null = null[np.isfinite(null)]
    pv = (np.sum(null >= diff) + 1) / (len(null) + 1)
    mid = sig.index[len(sig) // 2]
    h1 = snitt_diff(sig[sig.index < mid], y[y.index < mid])[0]
    h2 = snitt_diff(sig[sig.index >= mid], y[y.index >= mid])[0]
    ep, ns = episoder(sig)
    snitt = np.nanmean(Y[S & np.isfinite(Y)])
    return dict(snitt=snitt, diff=diff, p=pv, h1=h1, h2=h2, n=n, ep=ep, nseg=ns)


def s1_mot_s2(h, rel, fra, til):
    y = periode(utfall(h, rel).where(gyldig), fra, til)
    a = periode(SIG["S1 bunnsone og stigende"].fillna(False).astype(bool), fra, til)
    b = periode(SIG["S2 bunnsone og fallende"].fillna(False).astype(bool), fra, til)
    Y = y.values; A_, B_ = a.values & np.isfinite(Y), b.values & np.isfinite(Y)
    if not A_.sum() or not B_.sum():
        return None
    diff = Y[A_].mean() - Y[B_].mean()
    # placebo: bytt merkene tilfeldig innen hver raavare og episode (sammenhengende blokk)
    alle = A_ | B_
    blokker = []
    for j in range(Y.shape[1]):
        idx = np.where(alle[:, j])[0]
        if not len(idx):
            continue
        start = 0
        for k in range(1, len(idx) + 1):
            if k == len(idx) or idx[k] - idx[k - 1] > 12:
                blokker.append((j, idx[start:k])); start = k
    null = []
    for _ in range(2000):
        a2, b2 = [], []
        for j, ii in blokker:
            lab = A_[ii, j]
            if rng.random() < 0.5:
                lab = ~lab
            a2 += list(Y[ii[lab], j]); b2 += list(Y[ii[~lab], j])
        if a2 and b2:
            null.append(np.mean(a2) - np.mean(b2))
    pv = (np.sum(np.array(null) >= diff) + 1) / (len(null) + 1)
    mid = y.index[len(y) // 2]; m1 = (y.index < mid)[:, None]
    hv = []
    for m in (m1, ~m1):
        aa, bb = Y[A_ & m], Y[B_ & m]
        hv.append(aa.mean() - bb.mean() if len(aa) and len(bb) else np.nan)
    ea, na = episoder(a); eb, nb = episoder(b)
    return dict(snitt=Y[A_].mean(), andre=Y[B_].mean(), diff=diff, p=pv, h1=hv[0], h2=hv[1],
                n=int(A_.sum()), ep=min(ea, eb), nseg=min(na, nb))


def del2(sig, reg, h, fra, til):
    y = periode(utfall(h, False).where(gyldig), fra, til)
    s = periode(sig.fillna(False).astype(bool), fra, til)
    r = periode(reg.reindex(lr.index), fra, til)
    S, Y, R = s.values, y.values, r.values
    def d(Rv):
        ok = S & np.isfinite(Y) & np.isfinite(Rv)[:, None]
        inn, ut = ok & (Rv == 1)[:, None], ok & (Rv == 0)[:, None]
        if not inn.sum() or not ut.sum():
            return np.nan, Y[inn].mean() if inn.sum() else np.nan, Y[ut].mean() if ut.sum() else np.nan, inn, ut
        return Y[inn].mean() - Y[ut].mean(), Y[inn].mean(), Y[ut].mean(), inn, ut
    diff, mi, mu, inn, ut = d(R)
    if not np.isfinite(diff):
        return None
    null = []
    for _ in range(2000):
        null.append(d(np.roll(R, rng.integers(24, len(R) - 24)))[0])
    null = np.abs(np.array(null)); null = null[np.isfinite(null)]
    pv = (np.sum(null >= abs(diff)) + 1) / (len(null) + 1)
    mid = len(R) // 2; hv = []
    for sl in (slice(0, mid), slice(mid, None)):
        Rh = R.copy().astype(float); Rh[[i for i in range(len(R)) if not (sl.start or 0) <= i < (sl.stop or len(R))]] = np.nan
        hv.append(d(Rh)[0])
    ei = episoder(pd.DataFrame(inn, index=s.index))[0]; eu = episoder(pd.DataFrame(ut, index=s.index))[0]
    return dict(i_regime=mi, utenfor=mu, diff=diff, p=pv, h1=hv[0], h2=hv[1], n_inn=int(inn.sum()),
                n_ut=int(ut.sum()), ep_inn=ei, ep_ut=eu)


def pp(x):
    return "   -  " if x is None or not np.isfinite(x) else f"{100*x:+6.1f}"


def bh(T, q=0.10):
    T = T.sort_values("p").reset_index(drop=True); m = len(T)
    g = max([i + 1 for i in range(m) if T.p[i] <= q * (i + 1) / m], default=0)
    T["bh"] = [i < g for i in range(m)]
    return T


rader = []
print("DAGENS STILLING (siste maaned)")
siste = lr.index[-1]
for navn, sig in SIG.items():
    paa = [c for c in sig.columns if bool(sig.loc[siste, c]) is True]
    print(f"   {navn:34}: {', '.join(paa) or 'ingen'}")
print(f"   bredde {bredde.dropna().iloc[-1]:.2f} ({bredde.dropna().index[-1]}), VIX {v.iloc[-1]:.1f} ({v.index[-1]}), "
      f"uro {'ja' if toppen(v).iloc[-1] == 1 else 'nei'}\n")

print("==================== DEL 1: virker signalet (log realpris, per h mnd)")
t1 = []
for h in (6, 12):
    krav = 0.05 * h / 12
    for navn, sig in SIG.items():
        segs = KURVE_SEG if navn.startswith("K") else None
        res = {}
        for rel in (False, True):
            for pn, (fra, til) in {"1965-2014": (FRA, MIDT_TIL), "2015-2026": NYTT}.items():
                a = del1(navn, sig, h, rel, fra, til, segs)
                if a is None:
                    continue
                res[(rel, pn)] = a
                rader.append({"del": 1, "test": navn, "h": h, "maal": "tverrsnitt" if rel else "absolutt", "periode": pn, **a})
                print(f"   h {h:2} {navn:34} {'tverrsn' if rel else 'absolutt':8} {pn}  signal {pp(a['snitt'])} %  forskjell {pp(a['diff'])} pp"
                      f"  p {a['p']:.3f}  halvdeler {pp(a['h1'])}/{pp(a['h2'])}  n {a['n']}  ep {a['ep']} fra {a['nseg']}")
        ok = all((rel, "1965-2014") in res for rel in (False, True))
        if ok:
            tt = [res[(rel, "1965-2014")] for rel in (False, True)]
            ok = all(t["diff"] >= krav and t["p"] < 0.05 and t["h1"] > 0 and t["h2"] > 0 and t["ep"] >= 5
                     and t["nseg"] >= (2 if navn.startswith("K") else 3) for t in tt)
            t1.append({"test": f"{navn}, h {h}", "p": max(t["p"] for t in tt), "ok": ok})
        else:
            t1.append({"test": f"{navn}, h {h}", "p": 1.0, "ok": False})
    res = {}
    for rel in (False, True):
        for pn, (fra, til) in {"1965-2014": (FRA, MIDT_TIL), "2015-2026": NYTT}.items():
            a = s1_mot_s2(h, rel, fra, til)
            if a is None:
                continue
            res[(rel, pn)] = a
            rader.append({"del": 1, "test": "S1 mot S2", "h": h, "maal": "tverrsnitt" if rel else "absolutt", "periode": pn, **a})
            print(f"   h {h:2} {'S1 mot S2':34} {'tverrsn' if rel else 'absolutt':8} {pn}  S1 {pp(a['snitt'])} %  S2 {pp(a['andre'])} %"
                  f"  forskjell {pp(a['diff'])} pp  p {a['p']:.3f}  halvdeler {pp(a['h1'])}/{pp(a['h2'])}  ep {a['ep']} fra {a['nseg']}")
    tt = [res.get((rel, "1965-2014")) for rel in (False, True)]
    ok = all(t is not None for t in tt) and all(t["diff"] >= krav and t["p"] < 0.05 and t["h1"] > 0 and t["h2"] > 0
                                               and t["ep"] >= 5 and t["nseg"] >= 3 for t in tt)
    t1.append({"test": f"S1 mot S2, h {h}", "p": max(t["p"] for t in tt) if ok or all(tt) else 1.0, "ok": ok})
    print()

print("==================== DEL 2: betyr regimet noe (absolutt, log realpris, per h mnd)")
t2 = []
for h in (6, 12, 24):
    krav = 0.05 * h / 12
    for rn, reg in REG.items():
        avg = (pd.Period("1993-01", "M"), MIDT_TIL) if rn.startswith("R2") else (FRA, MIDT_TIL)
        for navn in ("S0 bunnsone", "S1 bunnsone og stigende", "S2 bunnsone og fallende", "S3 tverrsnitt billig og stigende"):
            res = {}
            for pn, (fra, til) in {"avgjoer": avg, "2015-2026": NYTT}.items():
                a = del2(SIG[navn], reg, h, fra, til)
                if a is None:
                    continue
                res[pn] = a
                rader.append({"del": 2, "test": f"{navn} | {rn}", "h": h, "maal": "absolutt", "periode": pn, **a})
                print(f"   h {h:2} {navn:34} {rn:32} {pn:9} i regimet {pp(a['i_regime'])} % (n {a['n_inn']}, ep {a['ep_inn']})"
                      f"  utenfor {pp(a['utenfor'])} % (n {a['n_ut']}, ep {a['ep_ut']})  forskjell {pp(a['diff'])} pp  p {a['p']:.3f}"
                      f"  halvdeler {pp(a['h1'])}/{pp(a['h2'])}")
            t = res.get("avgjoer")
            ok = t is not None and abs(t["diff"]) >= krav and t["p"] < 0.05 and np.sign(t["h1"]) == np.sign(t["h2"]) == np.sign(t["diff"]) \
                and t["ep_inn"] >= 3 and t["ep_ut"] >= 3
            t2.append({"test": f"{navn} | {rn}, h {h}", "p": t["p"] if t else 1.0, "ok": ok,
                       "retning": ("bedre i regimet" if t["diff"] > 0 else "daarligere i regimet") if t else ""})
    print()

print("AVGJOERELSE DEL 1 (1965 til 2014)\n")
for _, t in bh(pd.DataFrame(t1)).sort_values("test").iterrows():
    print(f"   {t.test:46}: {'HOLDER' if (t.ok and t.bh) else 'holder ikke'} (krav a til c {'ja' if t.ok else 'nei'}, største p {t.p:.3f}, BH {'ja' if t.bh else 'nei'})")
print("\nAVGJOERELSE DEL 2 (R1 1965 til 2014, R2 1993 til 2014)\n")
for _, t in bh(pd.DataFrame(t2)).sort_values("test").iterrows():
    print(f"   {t.test:72}: {'HOLDER, ' + t.retning if (t.ok and t.bh) else 'holder ikke'} (krav {'ja' if t.ok else 'nei'}, p {t.p:.3f}, BH {'ja' if t.bh else 'nei'})")
pd.DataFrame(rader).to_csv("sonder/verdi_trend_kurve.csv", index=False)
print("\nLagret sonder/verdi_trend_kurve.csv")
