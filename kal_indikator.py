# Kalibrering av indikatorsonden paa simulerte data uten sammenheng mellom
# skaarene og framtidig avkastning. Riktig test gir p < 0,05 i 5 % av tilfellene.
#   lag1: seksten tilfeldige gange (samme paneler som terskeltesten)
#   lag2: samme, pluss en COT-lignende serie (AR(1), 0 til 100) uavhengig av prisen
# Bruk: python kal_indikator.py <lag1|lag2> <antall> <trekk> <froe>
import sys, os, json, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kal_terskel as K, indikator_motor as I
COT_SEG = ["brent", "wti", "henryhub", "gold", "kobber", "kakao"]
START_COT = 2009 * 12 - 1  # Period-ordinal for 2009-01 er (2009-1970)*12, se under
def cot_sim(segs, rng):
    import pandas as pd
    o0 = pd.Period("2009-01", "M").ordinal
    ut = {}
    for s in segs:
        if s.sid not in COT_SEG:
            continue
        x = np.zeros(len(s.o))
        for i in range(1, len(x)):
            x[i] = 0.9 * x[i - 1] + rng.normal()
        p = 100 * (np.argsort(np.argsort(x)) / (len(x) - 1))
        p[s.o < o0] = np.nan
        ut[s.sid] = p
    return ut
if __name__ == "__main__":
    lag, ant, trekk, seed = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
    rng = np.random.default_rng(seed); ut = []; t0 = time.time()
    for i in range(ant):
        segs = K.panel(rng)
        if lag == "lag1":
            r = I.lag1_test(segs, rng, trekk)
            rad = {k: r[k] for k in ("p_indikator", "p_niva", "p_trend", "maaneder")}
        else:
            r = I.lag2_test(segs, cot_sim(segs, rng), True, rng, trekk)
            rad = {"p_cot": r["p_cot"], "maaneder": r["maaneder"]}
        ut.append(rad); print(i, round(time.time() - t0), rad, flush=True)
    json.dump(ut, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), f"kal_indikator_{lag}_{seed}.json"), "w"))
