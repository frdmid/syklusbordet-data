# Kalibrering av timingtestens test mot tilfeldig venting. Simulerte raavarer og
# papirer uten forutsigbarhet: ingen regel kan velge et bedre tidspunkt enn
# tilfeldig, saa en riktig test gir p < 0,05 i 5 % av tilfellene.
# Kjoerer selve sonden paa hvert simulerte datasett, i en egen mappe.
# Bruk: python kal_timing.py <antall datasett> <froe>
import numpy as np, pandas as pd, pickle, subprocess, sys, os, json, shutil, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kal_terskel as K
HER = os.path.dirname(os.path.abspath(__file__))
def datasett(rng, n_pap=150):
    segs = K.panel(rng)
    REAL = {s.sid: pd.Series(s.lr, index=pd.PeriodIndex([pd.Period(ordinal=int(o), freq="M") for o in s.o]))
            for s in segs}
    kal = pd.period_range("1998-01", "2026-08", freq="M"); T = len(kal)
    mkt = rng.standard_t(4, T) / np.sqrt(2) * 0.04
    KURS, UNIV = {}, {}
    ids = list(REAL)
    for j in range(n_pap):
        segs_j = list(rng.choice(ids, rng.integers(1, 3), replace=False))
        rr = np.zeros(T)
        for s in segs_j:
            d = REAL[s].diff().reindex(kal).fillna(0).values
            rr += rng.uniform(0.3, 1.0) * d / len(segs_j)
        rr += mkt * rng.uniform(0.6, 1.4) + rng.standard_t(4, T) / np.sqrt(2) * 0.08 + rng.uniform(-0.004, 0.01)
        st = rng.integers(0, 120)
        lp = np.cumsum(rr); lp[:st] = np.nan
        KURS[f"P{j}"] = np.exp(lp)
        UNIV[f"P{j}"] = {"navn": f"P{j}", "segs": segs_j, "tavle": j < 40}
    KURS = pd.DataFrame(KURS, index=kal)
    ck = pd.period_range("1959-01", "2026-08", freq="M")
    CPI = pd.Series(np.exp(np.cumsum(np.full(len(ck), 0.003))), index=ck)
    IRX = pd.Series(np.clip(3 + np.cumsum(rng.normal(0, 0.2, len(ck))), 0, 15), index=ck)
    return REAL, KURS, UNIV, CPI, IRX
if __name__ == "__main__":
    ant, seed = int(sys.argv[1]), int(sys.argv[2])
    rng = np.random.default_rng(seed)
    import tempfile
    mappe = os.path.join(tempfile.gettempdir(), f"kal_timing_{seed}")
    os.makedirs(mappe + "/sonder", exist_ok=True)
    for f in ("sonde_kjor_timing.py", "timing_motor.py", "raavare_hist.py"):
        shutil.copy(os.path.join(HER, f), mappe)
    ut = []
    t0 = time.time()
    for i in range(ant):
        pickle.dump(datasett(rng), open(mappe + "/d.pkl", "wb"))
        env = dict(os.environ, SONDE_TEST_PKL=mappe + "/d.pkl")
        p = subprocess.run([sys.executable, "sonde_kjor_timing.py"], cwd=mappe, env=env, capture_output=True, text=True)
        if p.returncode:
            print(p.stdout[-2000:], p.stderr[-3000:]); break
        r = json.load(open(mappe + "/sonder/timing.json"))
        rad = {f"{u}_{k}": r[u][k]["p"] for u in ("UTVIDET", "TAVLE", "RAAVARE") if r.get(u)
               for k in ("T1", "T2") if k in r[u]}
        rad["ep"] = r["UTVIDET"]["episoder"] if r.get("UTVIDET") else 0
        ut.append(rad)
        print(i, round(time.time() - t0), rad, flush=True)
    json.dump(ut, open(f"{HER}/kal_timing_{seed}.json", "w"))
