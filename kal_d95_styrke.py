# Styrke for d95-testen: simulerte paneler MED en syklisk komponent som vender
# tilbake (AR(1) rundt en tilfeldig gang), slik at en ekstrem detrendet A faktisk
# varsler oppgang. Syklusen: AR(1) med phi 0,95 og 7 % stoey per maaned, rundt en
# tilfeldig gang med 2 % egen stoey og en felles faktor. Da gir dagens regel
# rundt +15 % over 12 maaneder, paa hoeyde med det ekte bordet. Hvor ofte finner testen det ved 12 maaneder, p <= 0,0125?
# Bruk: python kal_d95_styrke.py <paneler> <trekk> <froe> <phi>
import json, sys, time
import numpy as np, pandas as pd
import terskel_motor as M
import d95_motor as D
from kal_terskel import START, SLUTT


def panel_syklus(rng, phi):
    g0 = pd.Period("1960-01", "M"); T = SLUTT.ordinal - g0.ordinal + 1
    hv = np.zeros(T)
    for t in range(1, T):
        hv[t] = 0.95 * hv[t - 1] + rng.normal(0, 0.25)
    vol = np.exp(hv)
    f = rng.standard_t(4, T) / np.sqrt(2) * 0.035 * vol
    segs = []
    for sid, st in START.items():
        a = pd.Period(st, "M").ordinal - g0.ordinal
        mu = rng.uniform(-0.003, 0.002)
        e = rng.standard_t(4, T) / np.sqrt(2) * 0.02 * vol
        c = np.zeros(T)
        u = rng.standard_t(4, T) / np.sqrt(2) * 0.07 * vol
        for t in range(1, T):
            c[t] = phi * c[t - 1] + u[t]
        r = (mu + rng.uniform(0.5, 1.5) * f + e)
        lr = (np.cumsum(r) + c)[a:] + 4
        o = np.arange(g0.ordinal + a, SLUTT.ordinal + 1)
        segs.append(M.Segment(sid, lr, o))
    return segs


if __name__ == "__main__":
    ant, trekk, seed, phi = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), float(sys.argv[4])
    rng = np.random.default_rng(seed)
    ut, t0 = [], time.time()
    for i in range(ant):
        segs = panel_syklus(rng, phi)
        obs, p = D.test(segs, rng, trekk=trekk, varianter=["d95", "d95_utenom", "dagens"], horisonter=[6, 12])
        ut.append({f"{v}|{k}": (p[(v, 12)] if k == "p12" else obs[(v, 12 if k != "S6" else 6)][{"S12": "S", "S6": "S", "ep12": "episoder"}[k]])
                   for v in ("d95", "d95_utenom", "dagens") for k in ("p12", "S12", "S6", "ep12")})
        print(i, round(time.time() - t0), ut[-1], flush=True)
        json.dump(ut, open(f"kal_d95_styrke_{seed}.json", "w"))
