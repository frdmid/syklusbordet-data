# Kalibrering av salgsonden. To slags simulerte data:
#   null:  tilfeldige gange uten tilbakevending (ingen salgsregel kan treffe
#          tidspunktet, en riktig test gir p < 0,05 i 5 % av tilfellene)
#   sykel: samme, pluss en tilbakevendende komponent (halveringstid rundt to
#          aar), for aa se om testen finner noe naar det finnes
# Kjoerer selve sonden paa hvert datasett, i en egen mappe.
# Bruk: python kal_salg.py <antall> <froe> <null|sykel>
import numpy as np, pandas as pd, pickle, subprocess, sys, os, json, shutil, time, tempfile
HER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HER)
import kal_terskel as K, terskel_motor as M, kal_timing as KT
if __name__ == "__main__":
    ant, seed, modus = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
    rng = np.random.default_rng(seed)
    if modus == "sykel":
        orig = K.panel
        def panel(rng, garch=True):
            ut = []
            for s in orig(rng, garch):
                n = len(s.lr); x = np.zeros(n)
                for i in range(1, n):
                    x[i] = 0.97 * x[i - 1] + rng.normal(0, 0.08)
                ut.append(M.Segment(s.sid, 0.5 * s.lr + x, s.o))
            return ut
        K.panel = panel
    mappe = os.path.join(tempfile.gettempdir(), f"kal_salg_{seed}")
    os.makedirs(mappe + "/sonder", exist_ok=True)
    for f in ("sonde_kjor_salg.py", "timing_motor.py", "raavare_hist.py"):
        shutil.copy(os.path.join(HER, f), mappe)
    ut = []; t0 = time.time()
    for i in range(ant):
        pickle.dump(KT.datasett(rng), open(mappe + "/d.pkl", "wb"))
        p = subprocess.run([sys.executable, "sonde_kjor_salg.py"], cwd=mappe, capture_output=True, text=True,
                           env=dict(os.environ, SONDE_TEST_PKL=mappe + "/d.pkl"))
        if p.returncode:
            print(p.stdout[-1500:], p.stderr[-2500:]); break
        r = json.load(open(mappe + "/sonder/salg.json"))
        rad = {f"{k}": (r["RAAVARE"][k]["p_mot_tilfeldig"], r["RAAVARE"][k]["S_pp_aar"]) for k in ("S1", "S2", "S3", "S5")
               if r.get("RAAVARE") and k in r["RAAVARE"]}
        rad["valgt"] = r["valgt"]; rad["ep"] = r["RAAVARE"]["episoder"] if r.get("RAAVARE") else 0
        ut.append(rad)
        print(i, round(time.time() - t0), rad, flush=True)
    json.dump(ut, open(os.path.join(HER, f"kal_salg_{modus}_{seed}.json"), "w"))
