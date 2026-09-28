# Kalibrering og styrke for d95-testen med rotasjonsnull.
# Bruk: python kal_d95_rot.py <null|syklus> <paneler> <trekk> <froe>
import json, sys, time
import numpy as np
import d95_motor as D
from kal_terskel import panel
from kal_d95_styrke import panel_syklus

if __name__ == "__main__":
    modus, ant, trekk, seed = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
    rng = np.random.default_rng(seed)
    ut, t0 = [], time.time()
    for i in range(ant):
        segs = panel(rng) if modus == "null" else panel_syklus(rng, 0.95)
        obs, p = D.test_rotasjon(segs, rng, trekk=trekk, horisonter=[1, 3, 6, 12])
        ut.append({f"{v}|{h}": [p[(v, h)], obs[(v, h)]["S"], obs[(v, h)]["episoder"]] for (v, h) in p})
        print(i, round(time.time() - t0), flush=True)
        json.dump(ut, open(f"kal_d95_rot_{modus}_{seed}.json", "w"))
