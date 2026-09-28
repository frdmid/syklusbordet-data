# Kalibrering av d95-testen paa simulerte paneler uten sammenheng mellom
# detrendet A og framtidig avkastning. Samme paneler som kal_terskel.py.
# Bruk: python kal_d95.py <paneler> <trekk> <froe>
import json, sys, time
import numpy as np
import d95_motor as D
from kal_terskel import panel

if __name__ == "__main__":
    ant, trekk, seed = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
    rng = np.random.default_rng(seed)
    ut, t0 = [], time.time()
    for i in range(ant):
        segs = panel(rng)
        obs, p = D.test(segs, rng, trekk=trekk)
        ut.append({"p": {f"{v}|{h}": p[(v, h)] for (v, h) in p},
                   "ep": {f"{v}|{h}": obs[(v, h)]["episoder"] for (v, h) in obs}})
        print(i, round(time.time() - t0), {k: round(x, 3) for k, x in ut[-1]["p"].items() if k.startswith("d95_utenom")}, flush=True)
        json.dump(ut, open(f"kal_d95_{seed}.json", "w"))
