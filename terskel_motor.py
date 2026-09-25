# ---------------------------------------------------------------------------
# terskel_motor: regnestykket bak terskeltesten, skilt ut fra sonden slik at
# det kan kalibreres paa simulerte data med noyaktig den samme koden.
# Brukes av sonde_kjor_terskel.py. Se den for hva testen maaler og hvorfor.
# ---------------------------------------------------------------------------

import numpy as np
from raavare_hist import pct_raa, pct_det

GRID = [60, 65, 70, 75, 80, 85, 90, 95]
H = 24          # utfallet: endring i log realpris 24 maaneder etter innslaget
PAUSE = 12      # nytt innslag i samme segment foerst etter tolv maaneder uten flagg
KLYNGEGAP = 6   # innslag med hoyst seks maaneder mellom, paa tvers av segmenter, er en episode
BLOKK = 24      # blokklengde i nullfordelingen


class Segment:
    """lr: log realpris som numpy-array, o: maanedsnummer (Period.ordinal) per punkt."""
    def __init__(self, sid, lr, o):
        self.sid, self.lr, self.o = sid, np.asarray(lr, float), np.asarray(o, int)
        self.A, self.Ad = pct_raa(self.lr), pct_det(self.lr)

    def med_bane(self, lr):
        return Segment(self.sid, lr, self.o)


def fram(lr, h=H):
    f = np.full(len(lr), np.nan)
    if len(lr) > h:
        f[:-h] = lr[h:] - lr[:-h]
    return f


def flagg(seg, k):
    A, Ad = seg.A, seg.Ad
    return np.isfinite(A) & np.isfinite(Ad) & (A >= k) & (Ad >= k)


def innslag(fl):
    """Posisjoner der et nytt innslag starter: flagget, og mer enn PAUSE
    maaneder siden forrige flaggede maaned. Samme regel som de andre sondene."""
    ut, siste = [], None
    for i in np.flatnonzero(fl):
        if siste is None or i - siste > PAUSE:
            ut.append(int(i))
        siste = i
    return ut


def klynger(rader):
    """rader: liste av (maanedsnummer, meravkastning). Episoder paa tvers av
    segmenter. Returnerer liste av lister med meravkastninger."""
    rader = sorted(rader)
    kl, cur, sist = [], [], None
    for o, x in rader:
        if cur and o - sist > KLYNGEGAP:
            kl.append(cur); cur = []
        cur.append(x); sist = o
    if cur:
        kl.append(cur)
    return kl


def statistikk(rader):
    """S = snittet over episoder av episodens median meravkastning."""
    kl = klynger(rader)
    if not kl:
        return {"S": np.nan, "S_median": np.nan, "episoder": 0, "positive": 0, "innslag": 0}
    v = np.array([np.median(k) for k in kl])
    return {"S": float(v.mean()), "S_median": float(np.median(v)), "episoder": len(kl),
            "positive": int((v > 0).sum()), "innslag": int(sum(len(k) for k in kl))}


def rader_for(segs, k, h=H, til=None, fra=None, bench_til=None, fwd=None):
    """Innslag for nivaa k i alle segmenter, med meravkastning mot segmentets
    eget snitt over alle maaneder med skaar og ferdig utfall.
    til/fra: grenser for innslagsdatoen (maanedsnummer). bench_til: bare
    maaneder til og med dette nummeret brukes i snittet (for trinn 2, der
    snittet skal vaere kjent paa valgdatoen)."""
    ut = []
    for j, s in enumerate(segs):
        f = fwd[j] if fwd is not None else fram(s.lr, h)
        gyldig = np.isfinite(f) & np.isfinite(s.A) & np.isfinite(s.Ad)
        if bench_til is not None:
            gyldig &= s.o <= bench_til
        if not gyldig.any():
            continue
        b = f[gyldig].mean()
        for i in innslag(flagg(s, k)):
            if not np.isfinite(f[i]):
                continue
            if til is not None and s.o[i] > til:
                continue
            if fra is not None and s.o[i] < fra:
                continue
            ut.append((int(s.o[i]), float(f[i] - b)))
    return ut


def kurve(segs, h=H, grid=GRID):
    fwd = [fram(s.lr, h) for s in segs]
    return {k: statistikk(rader_for(segs, k, h, fwd=fwd)) for k in grid}


def felles_bootstrap(segs, rng, L=BLOKK):
    """Nye prisbaner for alle segmenter paa en gang.

    Blokker paa L maaneder trekkes paa en felles kalender, og hvert segment
    henter sine maanedsendringer fra de samme kalendermaanedene. Da beholdes
    samvariasjonen mellom segmentene (2008, 2015 og 2020 rammer alle samtidig),
    og det er den som gjoer at innslag klumper seg i tid. En kalendermaaned
    utenfor et segments egen historikk legges inn i historikken med modulo.
    Nivaaene i A og detrendet A regnes paa nytt fra den nye banen, saa nullen
    har den samme selvreferansen som den ekte testen."""
    g0 = min(int(s.o[0]) for s in segs)
    g1 = max(int(s.o[-1]) for s in segs)
    Lg = g1 - g0 + 1
    q = []
    while len(q) < Lg:
        c = int(rng.integers(Lg))
        q.extend((c + np.arange(L)) % Lg)
    q = np.array(q[:Lg])
    ny = []
    for s in segs:
        d = np.diff(s.lr)
        m = len(d)
        a = int(s.o[0]) - g0
        kilde = (q[a + 1:a + 1 + m] - a - 1) % m
        ny.append(s.med_bane(s.lr[0] + np.concatenate([[0.0], np.cumsum(d[kilde])])))
    return ny


def trinn1(segs, rng, trekk=500, h=H, grid=GRID, obs=None):
    obs = obs or kurve(segs, h, grid)
    null = {k: [] for k in grid}
    for _ in range(trekk):
        kv = kurve(felles_bootstrap(segs, rng), h, grid)
        for k in grid:
            if np.isfinite(kv[k]["S"]):
                null[k].append(kv[k]["S"])
    p = {}
    for k in grid:
        nk = np.array(null[k])
        p[k] = (float(((nk >= obs[k]["S"]).sum() + 1) / (len(nk) + 1))
                if np.isfinite(obs[k]["S"]) and len(nk) else np.nan)
    return obs, p


def plataa(kv, p, k, grid=GRID, pgrense=0.10):
    i = grid.index(k)
    nab = [grid[j] for j in (i - 1, i + 1) if 0 <= j < len(grid)]
    return (all(np.isfinite(kv[x]["S"]) and kv[x]["S"] > 0 for x in nab + [k])
            and np.isfinite(p.get(k, np.nan)) and p[k] <= pgrense)
