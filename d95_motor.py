# ---------------------------------------------------------------------------
# d95_motor: regnestykket bak testen av detrendet A >= 95, skilt ut slik at
# det kalibreres paa simulerte data med noyaktig den samme koden som kjoeres
# paa ekte data. Bruker terskel_motor for segmenter, innslag, episoder og den
# felles blokkbootstrappen. Se sonde_kjor_d95.py for hva som testes.
# ---------------------------------------------------------------------------

import numpy as np
import terskel_motor as M

HORISONTER = [1, 3, 6, 12, 24]
VARIANTER = ["d95", "d95_utenom", "dagens"]


def flaggserie(s, variant):
    A, Ad = s.A, s.Ad
    ok = np.isfinite(A) & np.isfinite(Ad)
    dagens = ok & (A >= 80) & (Ad >= 80)
    if variant == "dagens":
        return dagens
    d95 = ok & (Ad >= 95)
    if variant == "d95":
        return d95
    if variant == "d95_utenom":
        # det signalet tilfoerer: detrendet A >= 95 i maaneder der bunnsonen
        # IKKE gjelder (raa A under 80)
        return d95 & ~dagens
    raise ValueError(variant)


def rader(segs, variant, h, fwd=None):
    """(maanedsnummer, meravkastning over h maaneder, segment) per innslag.
    Meravkastning = endring i log realpris minus segmentets eget snitt over alle
    maaneder med skaar og ferdig utfall (tilfeldige kjoepsdatoer)."""
    ut = []
    for j, s in enumerate(segs):
        f = fwd[j] if fwd is not None else M.fram(s.lr, h)
        gyldig = np.isfinite(f) & np.isfinite(s.A) & np.isfinite(s.Ad)
        if not gyldig.any():
            continue
        b = f[gyldig].mean()
        for i in M.innslag(flaggserie(s, variant)):
            if np.isfinite(f[i]):
                ut.append((int(s.o[i]), float(f[i] - b), s.sid))
    return ut


def kurve(segs, varianter=VARIANTER, horisonter=HORISONTER):
    ut = {}
    for h in horisonter:
        fwd = [M.fram(s.lr, h) for s in segs]
        for v in varianter:
            r = rader(segs, v, h, fwd)
            st = M.statistikk([(o, x) for o, x, _ in r])
            st["andel_mnd"] = float(np.mean(np.concatenate([flaggserie(s, v)[np.isfinite(s.Ad)] for s in segs])))
            ut[(v, h)] = st
    return ut


def test(segs, rng, trekk=500, varianter=VARIANTER, horisonter=HORISONTER, obs=None):
    obs = obs or kurve(segs, varianter, horisonter)
    null = {k: [] for k in obs}
    for _ in range(trekk):
        kv = kurve(M.felles_bootstrap(segs, rng), varianter, horisonter)
        for k in obs:
            if np.isfinite(kv[k]["S"]):
                null[k].append(kv[k]["S"])
    p = {}
    for k in obs:
        nk = np.array(null[k])
        p[k] = (float(((nk >= obs[k]["S"]).sum() + 1) / (len(nk) + 1))
                if np.isfinite(obs[k]["S"]) and len(nk) else np.nan)
    return obs, p


# ---------------------------------------------------------------------------
# Rotasjonsnull (lagt til 25.09.2026 etter at styrkesjekken viste at den
# felles blokkbootstrappen nesten aldri finner en ekte syklus).
#
# Innslagene beholdes som de er, men alle flyttes like mye i kalenderen, med
# en tilfeldig forskyvning paa minst 24 maaneder. Da beholdes baade hvor mange
# innslag hvert segment har, avstanden mellom dem og klumpingen paa tvers av
# segmentene (2008, 2015 og 2020 rammer alle samtidig). Det eneste som brytes,
# er koblingen mellom flagget og prisen etterpaa. Faller en flyttet dato
# utenfor segmentets historikk, legges den inn igjen fra starten (modulo).
# Prisbanene roeres ikke, saa syklusene i prisene er de samme i nullen som i
# den ekte testen, og det er nettopp det som gir styrke.
# ---------------------------------------------------------------------------

def _posisjoner(segs, variant, h):
    """Per segment: (innslagsposisjoner, fram-avkastning, snitt, gyldige posisjoner)."""
    ut = []
    for s in segs:
        f = M.fram(s.lr, h)
        gyldig = np.isfinite(f) & np.isfinite(s.A) & np.isfinite(s.Ad)
        if not gyldig.any():
            ut.append(None); continue
        pos = [i for i in M.innslag(flaggserie(s, variant)) if np.isfinite(f[i])]
        ut.append((pos, f, f[gyldig].mean(), np.flatnonzero(gyldig)))
    return ut


def _S(segs, info, skift=0, G0=0, Lg=1):
    """S for innslagene, eventuelt flyttet 'skift' maaneder i en felles kalender
    (G0, Lg). Episodene regnes paa de opprinnelige datoene, saa klumpingen er lik."""
    rader = []
    for s, x in zip(segs, info):
        if x is None or not x[0]:
            continue
        pos, f, b, gyl = x
        v0, v1 = int(s.o[gyl[0]]), int(s.o[gyl[-1]])
        for i in pos:
            j = i
            if skift:
                ny = G0 + (int(s.o[i]) - G0 + skift) % Lg
                if not (v0 <= ny <= v1):
                    ny = v0 + (ny - v0) % (v1 - v0 + 1)
                j = ny - int(s.o[0])
                if not np.isfinite(f[j]):
                    continue
            rader.append((int(s.o[i]), float(f[j] - b)))
    return M.statistikk(rader)


def test_rotasjon(segs, rng, trekk=2000, varianter=VARIANTER, horisonter=HORISONTER, min_skift=24):
    obs, p = {}, {}
    for h in horisonter:
        for v in varianter:
            info = _posisjoner(segs, v, h)
            o = _S(segs, info)
            o["andel_mnd"] = float(np.mean(np.concatenate([flaggserie(s, v)[np.isfinite(s.Ad)] for s in segs])))
            obs[(v, h)] = o
            if not np.isfinite(o["S"]):
                p[(v, h)] = np.nan; continue
            G0 = min(int(x.o[0]) for x in segs)
            Lg = max(int(x.o[-1]) for x in segs) - G0 + 1
            null = []
            for _ in range(trekk):
                k = int(rng.integers(min_skift, Lg - min_skift))
                null.append(_S(segs, info, skift=k, G0=G0, Lg=Lg)["S"])
            null = np.array([x for x in null if np.isfinite(x)])
            p[(v, h)] = float(((null >= o["S"]).sum() + 1) / (len(null) + 1))
    return obs, p
