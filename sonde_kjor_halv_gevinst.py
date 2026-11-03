# ---------------------------------------------------------------------------
# sonde_kjor_halv_gevinst: selg halvparten etter 6 mnd hvis posisjonen har
# steget kraftig, hold resten til 24 mnd (Frodes bestilling 03.11.2026, etter
# sonde_kjor_holdetid_nok).
#
# Oppsett som papirporteføljen i kontekst_handel.py: Championens bunnsone
# (2011-10 til nå), ny episode etter 12 mnd uten flagg, inngang ved
# månedsslutt i flaggmåneden, likt vektet i dagens kjøpbare papirer, NOK.
# Den solgte halvparten står i MSCI World (IWDA.L) resten av de 24 mnd, så
# alle varianter måles over samme vindu.
#
# VARIANTER (satt før kjøring, 03.11.2026):
#   H0  hold alt i 24 mnd (Championens regel)
#   H1  selg halvparten etter 6 mnd hvis gevinsten da er minst 25 %
#   H2  selg halvparten etter 6 mnd uansett
#   Følsomhet, avgjør ikke: H1 med grense 15 % og 40 %.
# LESING (satt før kjøring): en variant er bedre enn H0 hvis medianen av
#   (variant minus H0) over episodene er over 0 OG den er bedre i flertallet
#   av episodene. Verste punkt underveis og verste episode vises. Bare
#   ferdige episoder (24 mnd passert). 13 episoder og papirer valgt i 2026:
#   beskrivende, endrer ikke salgsregelen.
# Utdata sonder/halv_gevinst.csv.
# ---------------------------------------------------------------------------

import json
import numpy as np
import pandas as pd
import kontekst_handel as kh

idx = json.load(open("index.json", encoding="utf-8"))
seg = [json.load(open(f"segments/{s}.json", encoding="utf-8")) for s in idx["segmenter"]]
world = kh._mnd(kh._yahoo(kh.WORLD))
naa = world.index[-1]
SALG, HOLD = 6, 24
VAR = {"H0 hold alt 24 mnd": None, "H1 halv ved +25 %": 0.25, "H2 halv uansett": -9.0,
       "H1 halv ved +15 % (følsomhet)": 0.15, "H1 halv ved +40 % (følsomhet)": 0.40}

rader = []
for s in seg:
    if (s.get("scores") or {}).get("observasjon"):
        continue
    pap = [i["ticker"] for i in s.get("instrumenter") or [] if i.get("handlbar") and not i.get("omvendt")]
    fl = [(pd.Period(r["t"], "M"), bool(r.get("flagg"))) for r in s.get("series") or []]
    starter = kh._episoder(fl)
    if not pap or not starter:
        continue
    K = kh._kurv(pap, print)
    for t0 in starter:
        if t0 + HOLD > naa or t0 not in K.index:
            continue
        med = [c for c in K.columns if np.isfinite(K.loc[t0, c])]
        v = (K[med].loc[t0:t0 + HOLD] / K[med].loc[t0]).mean(axis=1)      # papirene, 1 ved inngang
        w = world.loc[t0 + SALG:t0 + HOLD] / world[t0 + SALG]              # World fra salget
        v6 = v[t0 + SALG]
        rad = {"segment": s["id"], "inngang": str(t0), "gevinst_6": 100 * (v6 - 1)}
        for navn, grense in VAR.items():
            if grense is None or v6 - 1 < grense:
                sti = v; solgt = False
            else:
                sti = pd.concat([v[v.index < t0 + SALG], 0.5 * v6 * w + 0.5 * v.loc[t0 + SALG:]])
                solgt = True
            rad[navn] = 100 * (sti.iloc[-1] - 1)
            rad[navn + " verst"] = 100 * (sti.min() - 1)
            rad[navn + " solgt"] = solgt
        rad["world 24"] = 100 * (world[t0 + HOLD] / world[t0] - 1)
        rader.append(rad)
D = pd.DataFrame(rader).sort_values("inngang")

print("PER EPISODE (prosent i NOK etter 24 mnd; * = halvparten solgt etter 6 mnd)")
print(f"   {'segment':10} inngang  6 mnd   " + "   ".join(n.split(' ')[0] + (n[-12:] if 'følsomhet' in n else '') for n in VAR) + "   World")
for _, r in D.iterrows():
    print(f"   {r.segment:10} {r.inngang} {r.gevinst_6:+6.1f}  " + "  ".join(
        f"{r[n]:+7.1f}{'*' if r[n + ' solgt'] else ' '}" for n in VAR) + f"  {r['world 24']:+6.1f}")

print("\nSAMMENDRAG (ferdige episoder)")
print("   variant                          median   snitt   mot H0: median  bedre i   verste ep  verste punkt (median)")
h0 = D["H0 hold alt 24 mnd"]
for n in VAR:
    d = D[n] - h0
    print(f"   {n:32} {D[n].median():+7.1f} {D[n].mean():+7.1f}   {d.median():+7.1f}       {(d > 0).sum():2} av {len(D)}   "
          f"{D[n].min():+7.1f}    {D[n + ' verst'].median():+6.1f}")
print("\nLESING (H1 og H2 mot H0, regelen satt før kjøring)")
for n in ("H1 halv ved +25 %", "H2 halv uansett"):
    d = D[n] - h0
    print(f"   {n}: {'bedre' if d.median() > 0 and (d > 0).sum() > len(D) / 2 else 'ikke bedre'} "
          f"(median {d.median():+.1f} pp, bedre i {(d > 0).sum()} av {len(D)}, solgt i {int(D[n + ' solgt'].sum())})")
D.to_csv("sonder/halv_gevinst.csv", index=False)
print("\nLagret sonder/halv_gevinst.csv")
