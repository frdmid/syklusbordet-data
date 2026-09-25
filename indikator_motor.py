# ---------------------------------------------------------------------------
# indikator_motor: regnestykket bak den sammensatte timingindikatoren, skilt
# ut slik at det kan kalibreres paa simulerte data med noyaktig samme kode.
# Brukes av sonde_kjor_indikator.py. Se den for hva som testes og hvorfor.
# ---------------------------------------------------------------------------

import numpy as np
import pandas as pd
import terskel_motor as M
from timing_motor import bekreftet

H = 24          # primaerutfall: realprisendring 24 maaneder fram, mot segmentets eget snitt
SONE = 80       # indikatoren regnes bare naar raa A >= 80 (bunnsone eller oppsikt)


def nei(real):
    v = np.asarray(real, float)
    ma10 = pd.Series(v).rolling(10).mean().values
    m12 = np.full(len(v), np.nan)
    if len(v) > 12:
        m12[12:] = v[12:] / v[:-12] - 1
    with np.errstate(invalid="ignore"):
        return (m12 <= 0) & (v <= ma10)


def trendskaar(lr):
    """0, 50, 100 for Nei, Begynnende, Bekreftet. Samme regel som feltet."""
    v = np.exp(np.asarray(lr, float))
    t = np.where(bekreftet(v), 100.0, np.where(nei(v), 0.0, 50.0))
    t[:12] = np.nan
    return t


def rang(x):
    return pd.Series(x).rank().values


def spearman(a, b):
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 12:
        return np.nan
    ra, rb = rang(a[ok]), rang(b[ok])
    if np.std(ra) == 0 or np.std(rb) == 0:
        return np.nan
    return float(np.corrcoef(ra, rb)[0, 1])


def sonerader(segs, h=H, cot=None):
    """Alle maaneder i sonen, samlet over segmentene.
    cot: dict sid -> array (COT-skaar paa segmentets egne maaneder) eller None.
    Returnerer dict med arrays: niva, trend, cot, mer (meravkastning), o, sid."""
    deler = {k: [] for k in ("niva", "trend", "cot", "mer", "o", "sid")}
    for s in segs:
        f = M.fram(s.lr, h)
        gyldig = np.isfinite(f) & np.isfinite(s.A) & np.isfinite(s.Ad)
        if not gyldig.any():
            continue
        b = f[gyldig].mean()
        tr = trendskaar(s.lr)
        c = cot.get(s.sid) if cot else None
        with np.errstate(invalid="ignore"):
            sone = gyldig & (s.A >= SONE) & np.isfinite(tr)
        deler["niva"].append((s.A[sone] + s.Ad[sone]) / 2)
        deler["trend"].append(tr[sone])
        deler["cot"].append(np.full(sone.sum(), np.nan) if c is None else np.asarray(c, float)[sone])
        deler["mer"].append(f[sone] - b)
        deler["o"].append(s.o[sone].astype(int))
        deler["sid"].append(np.array([s.sid] * int(sone.sum()), dtype=object))
    return {k: (np.concatenate(v) if v else np.array([])) for k, v in deler.items()}


def lag1(segs, h=H):
    r = sonerader(segs, h)
    i1 = (r["niva"] + r["trend"]) / 2
    rho1, rho0 = spearman(i1, r["mer"]), spearman(r["niva"], r["mer"])
    return {"rho_indikator": rho1, "rho_niva": rho0, "delta_trend": rho1 - rho0,
            "maaneder": int(len(r["mer"])), "segmenter": int(len(set(r["sid"])))}


def lag1_test(segs, rng, trekk=500, h=H):
    obs = lag1(segs, h)
    n1, nd, n0 = [], [], []
    for _ in range(trekk):
        x = lag1(M.felles_bootstrap(segs, rng), h)
        if np.isfinite(x["rho_indikator"]):
            n1.append(x["rho_indikator"]); nd.append(x["delta_trend"]); n0.append(x["rho_niva"])
    p = lambda null, v: float(((np.array(null) >= v).sum() + 1) / (len(null) + 1)) if np.isfinite(v) else np.nan
    return {**obs, "p_indikator": p(n1, obs["rho_indikator"]), "p_niva": p(n0, obs["rho_niva"]),
            "p_trend": p(nd, obs["delta_trend"]), "trekk": len(n1)}


def lag2(segs, cot, med_trend, h=H):
    """Forbedrer COT indikatoren fra lag 1, paa maanedene der COT finnes?"""
    r = sonerader(segs, h, cot)
    ok = np.isfinite(r["cot"])
    if ok.sum() < 24:
        return {"maaneder": int(ok.sum()), "rho_uten": np.nan, "rho_med": np.nan, "delta_cot": np.nan}
    base = (r["niva"] + r["trend"]) / 2 if med_trend else r["niva"]
    med = ((r["niva"] + r["trend"] + r["cot"]) / 3) if med_trend else ((r["niva"] + r["cot"]) / 2)
    ru, rm = spearman(base[ok], r["mer"][ok]), spearman(med[ok], r["mer"][ok])
    return {"maaneder": int(ok.sum()), "segmenter": int(len(set(r["sid"][ok]))),
            "rho_uten": ru, "rho_med": rm, "delta_cot": rm - ru}


def forskyv(c, rng, min_skift=24):
    """COT-serien forskjoevet sirkulaert innenfor maanedene der den finnes.
    Samme forskyvning for alle segmenter, saa samvariasjonen mellom dem beholdes."""
    ut, k = {}, None
    for sid, arr in c.items():
        ok = np.flatnonzero(np.isfinite(arr))
        if len(ok) < 2 * min_skift + 1:
            ut[sid] = arr; continue
        if k is None:
            k = float(rng.uniform(0, 1))
        n = len(ok)
        skift = int(min_skift + k * (n - 2 * min_skift))
        ny = np.full(len(arr), np.nan)
        ny[ok] = np.roll(arr[ok], skift)
        ut[sid] = ny
    return ut


def lag2_test(segs, cot, med_trend, rng, trekk=1000, h=H):
    obs = lag2(segs, cot, med_trend, h)
    if not np.isfinite(obs["delta_cot"]):
        return {**obs, "p_cot": np.nan}
    null = []
    for _ in range(trekk):
        x = lag2(segs, forskyv(cot, rng), med_trend, h)
        if np.isfinite(x["delta_cot"]):
            null.append(x["delta_cot"])
    null = np.array(null)
    return {**obs, "p_cot": float(((null >= obs["delta_cot"]).sum() + 1) / (len(null) + 1)), "trekk": len(null)}
