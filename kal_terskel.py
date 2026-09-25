# Kalibrering av terskeltestens trinn 1 paa simulerte paneler uten sammenheng
# mellom nivaa og framtidig avkastning. Riktig test gir p < 0,05 i 5 % av tilfellene.
# Bruk: python kal_terskel.py <antall paneler> <trekk i nullen> <froe>
# Paneler: seksten tilfeldige gange med segmentlengder som de ekte, en felles
# faktor (korrelasjon rundt 0,25), t-fordelte haler og skiftende volatilitet.
import numpy as np, pandas as pd, time, sys, json
import terskel_motor as M
START = {"brent":"1987-05","wti":"1986-01","henryhub":"1997-01","gold":"1971-08","uran":"1988-01",
         "kobber":"1960-01","sink":"1960-01","bly":"1960-01","tinn":"1960-01","palmeolje":"1960-01",
         "nikkel":"1980-01","aluminium":"1980-01","kakao":"1980-01","ttf":"2000-01","kull":"2000-01",
         "jernmalm":"2010-01"}
SLUTT = pd.Period("2026-08","M")
def panel(rng, garch=True):
    g0 = pd.Period("1960-01","M"); T = SLUTT.ordinal - g0.ordinal + 1
    hv = np.zeros(T)
    for t in range(1,T): hv[t] = 0.95*hv[t-1] + rng.normal(0,0.25)
    vol = np.exp(hv) if garch else np.ones(T)
    f = rng.standard_t(4,T)/np.sqrt(2)*0.035*vol
    segs=[]
    for sid, st in START.items():
        a = pd.Period(st,"M").ordinal - g0.ordinal
        mu = rng.uniform(-0.003,0.002)
        e = rng.standard_t(4,T)/np.sqrt(2)*0.06*vol
        r = (mu + rng.uniform(0.5,1.5)*f + e)[a+1:]
        lr = np.concatenate([[0.0], np.cumsum(r)]) + 4
        o = np.arange(g0.ordinal + a, SLUTT.ordinal + 1)
        segs.append(M.Segment(sid, lr, o))
    return segs
if __name__ == "__main__":
    ant, trekk, seed = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
    rng = np.random.default_rng(seed)
    ut = []
    t0=time.time()
    for i in range(ant):
        segs = panel(rng)
        obs, p = M.trinn1(segs, rng, trekk=trekk)
        ut.append({"p": {str(k): p[k] for k in p}, "S": {str(k): obs[k]["S"] for k in obs},
                   "ep": {str(k): obs[k]["episoder"] for k in obs}})
        print(i, round(time.time()-t0), {k: round(v,3) for k,v in p.items()}, flush=True)
    json.dump(ut, open(f"kal_terskel_{seed}.json","w"))
