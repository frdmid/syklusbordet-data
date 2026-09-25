# ---------------------------------------------------------------------------
# timing_motor: regnestykket bak timingtesten, skilt ut fra sonden slik at det
# kan kalibreres paa simulerte data med noyaktig samme kode.
# Brukes av sonde_kjor_timing.py. Se den for hva testen maaler og hvorfor.
# ---------------------------------------------------------------------------

import numpy as np
import pandas as pd

HORISONT = 36   # alle strategier maales fram til 36 maaneder etter flagget
MAKS_VENT = 24  # venter en regel lenger enn dette, blir pengene staaende i kontanter
KLYNGEGAP = 6
PAUSE = 12
KONT = MAKS_VENT + 1   # kode for "aldri kjoept, kontanter hele veien"


def bekreftet(real):
    """Samme regel som trendfeltet paa bordet (signaler.trend): hoyere enn for
    tolv maaneder siden OG over eget ti maaneders snitt. real er pris, ikke log."""
    v = np.asarray(real, float)
    n = len(v)
    ma10 = pd.Series(v).rolling(10).mean().values
    m12 = np.full(n, np.nan)
    if n > 12:
        m12[12:] = v[12:] / v[:-12] - 1
    with np.errstate(invalid="ignore"):
        return (m12 > 0) & (v > ma10)


def forste(b, t, maks=MAKS_VENT):
    """Antall maaneder fra t til foerste True i b, eller KONT."""
    for d in range(0, maks + 1):
        if t + d < len(b) and b[t + d]:
            return d
    return KONT


def innslag(fl):
    ut, siste = [], None
    for i in np.flatnonzero(fl):
        if siste is None or i - siste > PAUSE:
            ut.append(int(i))
        siste = i
    return ut


def formue(lp, C, t, plan, h=HORISONT):
    """Log formue ved t+h for 1 krone ved t, og verste punkt underveis.
    plan: liste av (d, vekt), kjoep ved slutten av maaned t+d. Resten staar i
    kontanter med realavkastning C (kumulativ log). lp: log realkurs."""
    e = t + h
    if e >= len(lp) or not np.isfinite(lp[t]) or not np.isfinite(lp[e]):
        return np.nan, np.nan
    for d, _ in plan:
        if not np.isfinite(lp[t + d]):
            return np.nan, np.nan
    sti = []
    for m in range(t, e + 1):
        if not np.isfinite(lp[m]):
            return np.nan, np.nan
        w = 0.0
        rest = 1.0
        for d, v in plan:
            if d <= m - t:
                w += v * np.exp(C[t + d] - C[t] + lp[m] - lp[t + d])
                rest -= v
        w += rest * np.exp(C[m] - C[t])
        sti.append(w)
    return float(np.log(sti[-1])), float(min(sti) - 1)


def plan_for(d):
    return [] if d == KONT else [(d, 1.0)]


def spre(k):
    return [(d, 1.0 / k) for d in range(k)]


def klynger(pos):
    """pos: kalenderposisjoner. Returnerer klyngenummer per element i samme rekkefoelge."""
    rek = np.argsort(pos, kind="stable")
    kl = np.zeros(len(pos), int)
    c, sist = 0, None
    for i in rek:
        if sist is not None and pos[i] - sist > KLYNGEGAP:
            c += 1
        kl[i] = c; sist = pos[i]
    return kl


def S(diff, kl):
    """Snitt over episoder av median forskjell. Og antall positive episoder."""
    ok = np.isfinite(diff)
    if not ok.any():
        return np.nan, 0, 0
    v = np.array([np.median(diff[ok & (kl == c)]) for c in np.unique(kl[ok])])
    return float(v.mean()), int((v > 0).sum()), len(v)


def tabell(lp_av, C, innsl, h=HORISONT):
    """For hvert innslag: log formue for alle forsinkelser 0..MAKS_VENT og
    kontanter, pluss spredning over 6 og 12 maaneder. innsl: liste av
    (navn, t). Returnerer W (n x KONT+1), W6, W12, verste (n x KONT+1), V6, V12."""
    n = len(innsl)
    W = np.full((n, KONT + 1), np.nan); V = np.full((n, KONT + 1), np.nan)
    W6, W12, V6, V12 = (np.full(n, np.nan) for _ in range(4))
    for i, (navn, t) in enumerate(innsl):
        lp = lp_av[navn]
        for d in range(KONT + 1):
            W[i, d], V[i, d] = formue(lp, C, t, plan_for(d), h)
        W6[i], V6[i] = formue(lp, C, t, spre(6), h)
        W12[i], V12[i] = formue(lp, C, t, spre(12), h)
    return W, W6, W12, V, V6, V12


def mot_tilfeldig(W, forsinkelse, kl, rng, trekk=1000, gruppe=None):
    """Er regelens ventetid bedre enn en tilfeldig ventetid med samme fordeling?

    Observert: S av (formue med regelens ventetid - formue ved flagget).
    Null: hver gruppe faar EN tilfeldig ventetid, trukket fra fordelingen av
    regelens ventetider paa tvers av alle innslag (kontanter inkludert), og
    alle innslag i gruppen bruker den. Gruppen er det som deler ventetid i
    regelen selv: for raavaretrenden alle papirer paa samme raavare i samme
    episode, for papirets egen trend hvert innslag for seg. Da er det bare
    TIDSPUNKTET regelen velger som testes, ikke det at den venter.

    Foerste utkast ga alle innslag i en episode samme tilfeldige ventetid.
    Det var for strengt: 0 % falske funn for papirets egen trend der 5 % er
    riktig, fordi nullen da svinger mer enn regelen selv."""
    n = len(forsinkelse)
    rad = np.arange(n)
    ok = np.isfinite(W[:, 0])
    obs = S(W[rad, forsinkelse] - W[:, 0], kl)[0]
    pool = np.asarray(forsinkelse)[ok]
    if gruppe is None:
        gruppe = np.arange(n)
    gruppe = np.asarray(gruppe)
    gr = np.unique(gruppe)
    gidx = np.searchsorted(gr, gruppe)
    null = []
    for _ in range(trekk):
        d = rng.choice(pool, len(gr))[gidx]
        null.append(S(W[rad, d] - W[:, 0], kl)[0])
    null = np.array([x for x in null if np.isfinite(x)])
    p = float(((null >= obs).sum() + 1) / (len(null) + 1)) if np.isfinite(obs) else np.nan
    return obs, p, float(np.median(null)) if len(null) else np.nan
