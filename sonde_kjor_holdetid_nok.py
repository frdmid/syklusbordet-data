# ---------------------------------------------------------------------------
# sonde_kjor_holdetid_nok: inngang ved signal og salg etter 3, 6, 9 og 12 mnd,
# i NOK (Frodes bestilling 03.11.2026). 24 mnd (Championens regel) vises til
# sammenligning.
#
# Samme oppsett som papirporteføljen i kontekst_handel.py: Championens
# bunnsone fra segmentenes månedsserie (2011-10 til nå), ny episode etter 12
# mnd uten flagg, inngang ved månedsslutt i flaggmåneden, likt vektet i dagens
# kjøpbare papirer (ikke omvendte), kurser i NOK. Mot MSCI World (IWDA.L) og
# OSEBX i samme vindu. Også bare flagg i bred nedgang.
# Porteføljen per holdetid: 20 % per åpen posisjon (høyst fem), resten i MSCI
# World, fra 2013-03.
#
# BESKRIVENDE, ingen avgjørelse: papirene er valgt i 2026 med kjennskap til
# årene, og det er 13 episoder. Salgsregelen ble testet i sonde_kjor_salg
# (24.09.2026, fast holdetid 24 mnd sto); denne sonden endrer ikke regelen.
# Utdata sonder/holdetid_nok.csv.
# ---------------------------------------------------------------------------

import json
import numpy as np
import pandas as pd
import kontekst_handel as kh
import shadow_oos as so

lager = so.LokalLager(".", ".")
idx = json.load(open("index.json", encoding="utf-8"))
seg = [json.load(open(f"segments/{s}.json", encoding="utf-8")) for s in idx["segmenter"]]
priser = open("serier/priser_mnd.csv", encoding="utf-8").read()
world, osebx = kh._mnd(kh._yahoo(kh.WORLD)), kh._mnd(kh._yahoo(kh.OSEBX))
naa = world.index[-1]


def fram(s, t, h):
    b = t + h
    return 100 * (s[b] / s[t] - 1) if t in s.index and b in s.index and b <= naa else np.nan


rader, nav = [], {}
for h in (3, 6, 9, 12, 24):
    kh.HOLD = h
    pf = kh.portefolje(seg, priser, note=lambda *_: None)
    nav[h] = pf
    for p in pf["posisjoner"]:
        t = pd.Period(p["inngang"], "M")
        ferdig = t + h <= naa
        rader.append({"h": h, "variant": p["variant"], "segment": p["segment"], "inngang": p["inngang"], "ferdig": ferdig,
                      "papirer": p["avk"], "world": fram(world, t, h), "osebx": fram(osebx, t, h)})
D = pd.DataFrame(rader)
D["mot_world"], D["mot_osebx"] = D.papirer - D.world, D.papirer - D.osebx

print("PER EPISODE (alle flagg, prosent i NOK, papirene / MSCI World)")
P = D[D.variant == "alle"].pivot_table(index=["segment", "inngang"], columns="h", values=["papirer", "world"])
for (s, t), r in P.sort_index(level=1).iterrows():
    print(f"   {s:10} {t}  " + "  ".join(f"{h:2} mnd {r[('papirer', h)]:+7.1f} / {r[('world', h)]:+6.1f}"
                                         if np.isfinite(r[('papirer', h)]) else f"{h:2} mnd    -   /   -  " for h in (3, 6, 9, 12, 24)))

for v, navn in (("alle", "ALLE FLAGG"), ("bred", "BARE I BRED NEDGANG")):
    print(f"\n{navn} (bare ferdige posisjoner; median og snitt i prosent, NOK)")
    print("   mnd  ep   papirer median  snitt   world median  OSEBX median   slo world  slo OSEBX   verste ep   årlig portefølje / world / OSEBX")
    for h in (3, 6, 9, 12, 24):
        g = D[(D.h == h) & (D.variant == v) & D.ferdig]
        a = nav[h]["aarlig"]
        print(f"   {h:3} {len(g):3}   {g.papirer.median():+7.1f}  {g.papirer.mean():+7.1f}   {g.world.median():+7.1f}      "
              f"{g.osebx.median():+7.1f}     {(g.mot_world > 0).sum():2} av {len(g):2}   {(g.mot_osebx > 0).sum():2} av {g.osebx.notna().sum():2}"
              f"    {g.papirer.min():+7.1f}    {a['flagg' if v == 'alle' else 'bred']:+5.1f} / {a['world']:+5.1f} / {a['osebx']:+5.1f}")

print("\nUTEN 2020 (alle flagg, ferdige): median papirer / MSCI World, slo world")
for h in (3, 6, 9, 12, 24):
    g = D[(D.h == h) & (D.variant == "alle") & D.ferdig & ~D.inngang.str.startswith("2020")]
    print(f"   {h:3} mnd  {len(g):2} ep  {g.papirer.median():+7.1f} / {g.world.median():+6.1f}   {(g.mot_world > 0).sum()} av {len(g)}")
D.to_csv("sonder/holdetid_nok.csv", index=False)
print("\nLagret sonder/holdetid_nok.csv")
