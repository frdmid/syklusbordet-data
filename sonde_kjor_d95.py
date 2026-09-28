# ---------------------------------------------------------------------------
# sonde_kjor_d95: full test av regelen detrendet A >= 95, uansett raa A
#
# Bakgrunn: Frode innfoerte 25.09.2026 et parallelt signal for Brent, detrendet
# A >= 95 uansett raa A, uten test. Samme dag ba han om en full test med
# horisontene 1, 3, 6 og 12 maaneder fra flagget. Denne sonden er den testen.
# Den endrer ingenting paa bordet.
#
# DATA
#   Hele realprishistorikken for de seksten raavaresegmentene (ikke laks), med
#   priser.py sin egen kode (raavare_hist.py), samme som terskeltesten. A og
#   detrendet A punkt i tid. Kontrollert mot flagg_d95 i segments/brent.json.
#
# TRE VARIANTER
#   d95          detrendet A >= 95, alle innslag
#   d95_utenom   detrendet A >= 95 i maaneder der bunnsonen IKKE gjelder (raa A
#                under 80). Det er dette det parallelle signalet tilfoerer utover
#                regelen som gjelder, og den varianten beslutningen hviler paa.
#   dagens       raa A >= 80 og detrendet A >= 80, til sammenligning
#
# UTFALL
#   Endring i log realpris 1, 3, 6 og 12 maaneder etter innslaget (24 som
#   referanse), minus segmentets eget snitt over alle maaneder. Innslag: foerste
#   flaggede maaned etter mer enn tolv uten. Episode: innslag paa tvers av
#   segmenter med hoyst seks maaneder mellom. S = snittet over episodene av
#   episodens median meravkastning. Nullen: felles blokkbootstrap av alle
#   segmenter (24 maaneder), 500 trekk, samme som terskel- og indikatortesten.
#
# BESLUTNINGSREGEL, SATT FOER KJOERING (25.09.2026)
#   To spoersmaal, samme krav for begge:
#     S1 Har regelen informasjon? Variant d95.
#     S2 Tilfoerer den noe utover bunnsonen? Variant d95_utenom.
#   Kravene:
#     a) S > 0 og p <= 0,0125 ved 12 maaneder (0,05 delt paa fire horisonter)
#     b) S > 0 ved 6 maaneder
#     c) minst fem episoder ved 12 maaneder
#   Det parallelle signalet for Brent regnes som stoettet bare hvis S2 bestaar.
#   Bestaar S1 men ikke S2, har regelen informasjon, men den overlapper
#   bunnsonen. Bestaar ingen, merkes signalet "testet, ikke stoettet" og er
#   Frodes eget valg. 1 og 3 maaneder rapporteres og leses som beskrivelse av
#   forloepet rett etter flagget, ikke som krav. Brent alene har for faa
#   innslag til en test og vises beskrivende. Styrken er maalt paa simulerte
#   paneler med sykluser (kal_d95_styrke.py), og et nei leses i lys av den.
#
# KALIBRERING OG STYRKE (foer kjoering, 25.09.2026)
#   Uten sammenheng (kal_d95.py, 144 simulerte paneler, 200 trekk): andelen
#   p <= 0,0125 ved 12 maaneder er 0,7 % for d95 og 0,0 % for d95_utenom, og
#   hoeyst 2,1 % paa alle horisonter og varianter. Andelen under 0,05 er 1,4 til
#   6,2 %. Testen gir ikke falske funn.
#   Med ekte sykluser (kal_d95_styrke.py, 50 paneler der dagens regel og d95
#   gir rundt +16 % over 12 maaneder): testen fant effekten i 4 % av panelene
#   for d95 og 0 % for d95_utenom. Nullen (felles blokkbootstrap) tar med seg
#   syklusene innenfor blokkene, og da skiller den daarlig. Et JA kan stoles
#   paa. Et NEI betyr ikke at regelen er uten verdi, bare at testen ikke kan
#   avgjoere det. Resultatet leses derfor mest som beskrivelse.
#   En annen null ble proevd (rotasjon: alle innslag flyttes like mye i
#   kalenderen, kal_d95_rot.py). Den fant syklusen oftere (27 % for d95 ved 12
#   maaneder), men ga falske funn i 4 til 8 % av panelene der 1,25 % er riktig,
#   ogsaa med strengere grense. Den er forkastet. For tillegget utenom
#   bunnsonen fant ingen av metodene noe (0 til 2 %), selv med ekte sykluser.
# ---------------------------------------------------------------------------

import json, os, time, warnings
import numpy as np
import pandas as pd
import terskel_motor as M
import d95_motor as D

warnings.filterwarnings("ignore")
rng = np.random.default_rng(20260926)
TREKK = int(os.environ.get("SONDE_TREKK", 500))   # 500 i kjoeringen; lavere bare ved proevekjoering
SEKSTEN = {"brent", "wti", "henryhub", "ttf", "uran", "gold", "kobber", "nikkel", "aluminium",
           "sink", "bly", "tinn", "jernmalm", "kull", "kakao", "palmeolje"}
KALIBRERT = {"paneler_null": 144, "trekk": 200, "p0125_12_d95": 0.007, "p0125_12_utenom": 0.0,
             "p0125_maks": 0.021, "p05_spenn": [0.014, 0.062],
             "styrke_paneler": 50, "styrke_d95_12": 0.04, "styrke_utenom_12": 0.0}
RES = {"kjort": time.strftime("%Y-%m-%d %H:%M:%S"), "kalibrering": KALIBRERT}
pst = lambda v: "-" if v is None or not np.isfinite(v) else f"{100 * (np.exp(v) - 1):+6.1f} %"

print("1. Realprishistorikk\n")
from raavare_hist import hent
REAL, _NOM, _cpi = hent()
SEGS = []
for sid, lr in sorted(REAL.items()):
    if sid not in SEKSTEN:
        print(f"   {sid}: utelatt (ikke et av de seksten raavaresegmentene)")
        continue
    lr = lr.dropna()
    full = pd.period_range(lr.index[0], lr.index[-1], freq="M")
    if len(full) != len(lr):
        lr = lr.reindex(full).interpolate()
    SEGS.append(M.Segment(sid, lr.values, np.array([p.ordinal for p in lr.index])))
    print(f"   {sid:10} {lr.index[0]} til {lr.index[-1]}  {len(lr)} mnd")
PER = lambda o: str(pd.Period(ordinal=int(o), freq="M"))

# kontroll mot segmentfilen for Brent
try:
    d = json.load(open("segments/brent.json", encoding="utf-8"))
    s = next(x for x in SEGS if x.sid == "brent")
    f = dict(zip(s.o, D.flaggserie(s, "d95")))
    par = [(bool(f[pd.Period(r["t"], "M").ordinal]), bool(r.get("flagg_d95")))
           for r in d["series"] if "flagg_d95" in r and pd.Period(r["t"], "M").ordinal in f]
    enig = sum(a == b for a, b in par)
    print(f"\n   kontroll: d95 for Brent likt segmentfilen i {enig} av {len(par)} maaneder")
    RES["kontroll_brent"] = [enig, len(par)]
except Exception as e:
    print(f"\n   kontroll mot segmentfilen ikke gjort: {type(e).__name__}")

print(f"\n2. Hele utvalget, {TREKK} trekk i nullen\n")
t0 = time.time()
OBS, P = D.test(SEGS, rng, trekk=TREKK)
print(f"   ({time.time() - t0:.0f} s)\n")
print(f"   {'variant':12} {'mnd':>4} {'episoder':>8} {'innslag':>7} {'positive':>8} {'S':>9} {'median':>9} {'p':>7} {'andel mnd':>9}")
RES["resultat"] = {}
for v in D.VARIANTER:
    for h in D.HORISONTER:
        o = OBS[(v, h)]
        print(f"   {v:12} {h:4d} {o['episoder']:8d} {o['innslag']:7d} {o['positive']:8d} {pst(o['S']):>9} "
              f"{pst(o['S_median']):>9} {P[(v, h)]:7.3f} {100 * o['andel_mnd']:8.1f} %")
        RES["resultat"][f"{v}|{h}"] = {**o, "p": P[(v, h)]}
    print()

print("3. Innslagene i d95_utenom (det signalet tilfoerer), meravkastning per horisont\n")
tab = {}
for h in D.HORISONTER:
    for o, x, sid in D.rader(SEGS, "d95_utenom", h):
        tab.setdefault((o, sid), {})[h] = x
seg = {s.sid: s for s in SEGS}
print(f"   {'innslag':8} {'segment':10} {'raa A':>6} {'detr A':>6}  " + "  ".join(f"{h:>2} mnd   " for h in D.HORISONTER))
RES["innslag_utenom"] = []
for (o, sid), v in sorted(tab.items()):
    s = seg[sid]; i = int(np.flatnonzero(s.o == o)[0])
    print(f"   {PER(o):8} {sid:10} {s.A[i]:6.1f} {s.Ad[i]:6.1f}  " + "  ".join(f"{pst(v.get(h)):>9}" for h in D.HORISONTER))
    RES["innslag_utenom"].append({"t": PER(o), "segment": sid, "A": round(float(s.A[i]), 1),
                                  "Ad": round(float(s.Ad[i]), 1),
                                  **{f"h{h}": v.get(h) for h in D.HORISONTER}})

print("\n4. Brent alene (beskrivende): alle innslag i d95, endring i realpris og mot Brent sitt eget snitt\n")
s = seg["brent"]
RES["brent"] = []
for i in M.innslag(D.flaggserie(s, "d95")):
    rad = {"t": PER(s.o[i]), "A": round(float(s.A[i]), 1), "Ad": round(float(s.Ad[i]), 1)}
    tekst = []
    for h in D.HORISONTER:
        f = M.fram(s.lr, h)
        ok = np.isfinite(f) & np.isfinite(s.A) & np.isfinite(s.Ad)
        if np.isfinite(f[i]):
            rad[f"h{h}"] = float(f[i]); rad[f"h{h}_mer"] = float(f[i] - f[ok].mean())
            tekst.append(f"{h}m {pst(f[i])} (mot snitt {pst(f[i] - f[ok].mean())})")
        else:
            tekst.append(f"{h}m -")
    RES["brent"].append(rad)
    print(f"   {rad['t']}  raa A {rad['A']:5.1f}  detr A {rad['Ad']:5.1f}   " + "; ".join(tekst))

print("\n5. Beslutning etter regelen satt foer kjoering\n")
RES["beslutning"] = {}
for v, navn in (("d95", "S1 har regelen informasjon"), ("d95_utenom", "S2 tilfoerer den noe utover bunnsonen")):
    o12, o6, p12 = OBS[(v, 12)], OBS[(v, 6)], P[(v, 12)]
    a = bool(np.isfinite(o12["S"]) and o12["S"] > 0 and p12 <= 0.0125)
    b = bool(np.isfinite(o6["S"]) and o6["S"] > 0)
    c = bool(o12["episoder"] >= 5)
    print(f"   {navn} ({v}):")
    print(f"      a) 12 mnd: S {pst(o12['S'])}, p {p12:.3f} (krav S > 0 og p <= 0,0125): {'ja' if a else 'nei'}")
    print(f"      b)  6 mnd: S {pst(o6['S'])} (krav S > 0): {'ja' if b else 'nei'}")
    print(f"      c) episoder ved 12 mnd: {o12['episoder']} (krav minst 5): {'ja' if c else 'nei'}")
    RES["beslutning"][v] = a and b and c
    print(f"      -> {'BESTAAR' if a and b and c else 'BESTAAR IKKE'}\n")
RES["stoettet"] = RES["beslutning"]["d95_utenom"]
if RES["stoettet"]:
    print("   Det parallelle signalet er STOETTET: detrendet A >= 95 tilfoerer noe utover bunnsonen.")
elif RES["beslutning"]["d95"]:
    print("   Regelen har informasjon, men tilfoerer ikke noe paavist utover bunnsonen. Signalet er IKKE STOETTET som tillegg.")
else:
    print("   IKKE STOETTET: ingen av spoersmaalene bestaar. Signalet er Frodes eget valg.")

os.makedirs("sonder", exist_ok=True)
json.dump(RES, open("sonder/d95.json", "w"), ensure_ascii=False, indent=1, default=float)
print("\nLagret sonder/d95.json")
