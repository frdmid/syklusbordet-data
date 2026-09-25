# ---------------------------------------------------------------------------
# sonde_kjor_terskel: er 80 riktig nivaa for bunnflagget
#
# Kravet (Frode, 24.09.2026): flaggnivaaet skal testes, ikke arves. Det ble
# stilt for laksemarginen, og gjelder like mye for resten av bordet. Flaggtesten
# i september sammenlignet REGLER ved 80 (raa A alene mot raa og detrendet),
# ikke NIVAAER. Denne sonden tester nivaaet. Den endrer ingenting paa bordet.
#
# REGELEN SOM TESTES
#   Flagg ved nivaa k: raa A >= k og detrendet A >= k, samme k i begge ledd.
#   k i 60, 65, 70, 75, 80, 85, 90, 95.
#
# DATA
#   Hele realprishistorikken for de seksten raavaresegmentene, hentet med
#   priser.py sin egen kode (raavare_hist.py), altsaa samme kilder, avkorting
#   og uranserie som bordet. A og detrendet A regnes punkt i tid som i
#   priser.py, og sonden kontrollerer at de gir samme flagg som segmentfilene
#   ved 80.
#
# UTFALL
#   Primaert: endring i log realpris 24 maaneder etter innslaget, minus
#   segmentets eget snitt over alle maaneder (tilfeldige kjoepsdatoer i samme
#   raavare). 12 maaneder rapporteres ved siden av.
#   Innslag: foerste flaggede maaned etter mer enn tolv maaneder uten flagg.
#   Episode: innslag paa tvers av segmenter med hoyst seks maaneder mellom.
#   S = snittet over episodene av episodens median meravkastning. Episoden,
#   ikke innslaget, er enheten, slik at 2015 ikke teller elleve ganger.
#
# FIRE TRINN, SAMME OPPLEGG SOM LAKSEN
#   Trinn 1, informasjon per nivaa: S mot en null der prisbanene lages paa nytt
#     med felles blokkbootstrap (24 maaneder, samme kalendermaaneder for alle
#     segmenter), og A, detrendet A, innslag og utfall regnes paa nytt fra
#     hver bane. 500 trekk.
#   Trinn 2, valg uten fasit: hvert aarsskifte fra 1990 velges nivaaet med
#     hoeyest S paa innslag med ferdig utfall paa valgdatoen (snittet ogsaa bare
#     med data kjent da), minst tre episoder. Valget brukes paa aarets innslag.
#     Utfallet av disse sammenlignes med fast 80 i de samme aarene.
#   Trinn 3, plataa: nivaaet og begge naboene har positiv S paa hele utvalget,
#     og nivaaet selv har p <= 0,10 i trinn 1.
#   Trinn 4, papirene: instrumenttesten kjoerer foer denne (alfabetisk) og maaler
#     raavareflagget ved alle nivaaene paa papirene, 2011 til 2024. Leses
#     herfra hvis den er fersk (under seks timer).
#
# BESLUTNINGSREGEL, SATT FOER KJOERING
#   Et annet nivaa k* erstatter 80 bare hvis ALT dette holder:
#     a) k* er nivaaet trinn 2 velger i siste aar
#     b) k* bestaar plataatesten
#     c) valgt nivaa i trinn 2 slo fast 80 utenfor utvalget, OG fast k* slo fast
#        80 utenfor utvalget
#     d) minst fem episoder paa hele utvalget, og flagget staar hoyst 25 % av
#        maanedene samlet
#     e) papirene: k* gjoer det minst like godt som 80 paa tavlen over 24
#        maaneder, hvis instrumenttesten har maalt k*. Mangler den, er
#        beslutningen foreloepig.
#   Ellers blir 80 staaende. Bestaar ikke 80 selv plataatesten, sies det
#   rett ut: nivaaet er ikke robust, og 80 er et foreloepig valg.
#
# KALIBRERING (trinn 1, kal_terskel.py)
#   160 simulerte paneler uten sammenheng mellom nivaa og framtid: seksten
#   tilfeldige gange med segmentlengder som de ekte, felles faktor, tykke haler
#   og skiftende volatilitet, 200 trekk i nullen per panel. Riktig andel er 5 %
#   under 0,05 og 10 % under 0,10.
#     samlet over alle nivaaer (1280 tester)   5,9 %   10,5 %
#     ved 80                                   5,6 %   10,6 %
#     spenn over nivaaene                      4,4 til 7,5 %   8,1 til 15,0 %
#   Testen holder. Ved 95 er den litt for villig (15 % under 0,10), fordi det
#   er faa innslag der. Et plataa som bare hviler paa 95 skal leses med det.
# ---------------------------------------------------------------------------

import json, os, time, warnings
import numpy as np
import pandas as pd

import terskel_motor as M

warnings.filterwarnings("ignore")
rng = np.random.default_rng(20260925)
TREKK = 500
WF_FRA = 1990
KALIBRERT = {"paneler": 160, "trekk": 200, "p05_samlet": 0.059, "p10_samlet": 0.105,
             "p05_80": 0.056, "p10_80": 0.106, "p05_spenn": [0.044, 0.075], "p10_spenn": [0.081, 0.150]}
RES = {"kjort": time.strftime("%Y-%m-%d %H:%M:%S"), "grid": M.GRID, "kalibrering": KALIBRERT}
fp = lambda v: "-" if v is None or not np.isfinite(v) else f"{100 * (np.exp(v) - 1):+6.1f} %"

# ================================================================ 1. data
print("1. Realprishistorikk for raavaresegmentene\n")
if os.environ.get("SONDE_TEST_PKL"):
    import pickle
    REAL = pickle.load(open(os.environ["SONDE_TEST_PKL"], "rb"))
    print("   TESTDATA, ikke ekte")
else:
    from raavare_hist import hent
    REAL, _NOM, _cpi = hent()

SEGS = []
for sid, lr in sorted(REAL.items()):
    lr = lr.dropna()
    full = pd.period_range(lr.index[0], lr.index[-1], freq="M")
    hull = len(full) - len(lr)
    if hull:
        lr = lr.reindex(full).interpolate()
        print(f"   {sid}: {hull} manglende maaneder fylt lineaert i log")
    SEGS.append(M.Segment(sid, lr.values, np.array([p.ordinal for p in lr.index])))
    print(f"   {sid:10} {lr.index[0]} til {lr.index[-1]}  {len(lr)} mnd")
PER = lambda o: str(pd.Period(ordinal=int(o), freq="M"))
SISTE = max(int(s.o[-1]) for s in SEGS)
TIL = SISTE - M.H

# kontroll mot segmentfilene ved 80
enig, n = 0, 0
for s in SEGS:
    try:
        d = json.load(open(f"segments/{s.sid}.json", encoding="utf-8"))
    except Exception:
        continue
    f = dict(zip(s.o, M.flagg(s, 80)))
    for r in d["series"]:
        o = pd.Period(r["t"], "M").ordinal
        if o in f:
            n += 1; enig += int(bool(f[o]) == bool(r.get("flagg")))
print(f"\n   kontroll: flagget ved 80 er likt segmentfilene i {enig} av {n} maaneder"
      + ("" if enig == n else "  OBS: avvik, trolig ny datavintage siden sist onsdag"))
RES["kontroll_80"] = [enig, n]


# ================================================================ 2. hele utvalget
print("\n2. Hele utvalget (trinn 1 og grunnlaget for plataatesten)\n")
t0 = time.time()
KV = M.kurve(SEGS)
KV12 = M.kurve(SEGS, h=12)
_, P = M.trinn1(SEGS, rng, trekk=TREKK, obs=KV)
print(f"   ({TREKK} trekk i nullen, {time.time() - t0:.0f} s)\n")


def andel(k):
    fl = np.concatenate([M.flagg(s, k)[np.isfinite(s.A) & np.isfinite(s.Ad)] for s in SEGS])
    return float(fl.mean())


print(f"   {'nivaa':>5} {'mnd flagget':>11} {'innslag':>7} {'episoder':>8} {'pos':>4} | "
      f"{'S 24 mnd':>9} {'median ep':>9} {'p':>6} | {'S 12 mnd':>9}")
for k in M.GRID:
    r = KV[k]
    print(f"   {k:5} {100 * andel(k):10.1f}% {r['innslag']:7} {r['episoder']:8} {r['positive']:4} | "
          f"{fp(r['S'])} {fp(r['S_median'])} {P[k]:6.3f} | {fp(KV12[k]['S'])}")
print("\n   S er snittet over episodene av median meravkastning mot tilfeldige kjoepsdatoer i")
print("   samme raavare, vist som prosent realprisendring. p fra trinn 1.")
RES["kurve"] = {k: {**KV[k], "p": P[k], "andel_mnd": andel(k), "S12": KV12[k]["S"]} for k in M.GRID}
PL = {k: M.plataa(KV, P, k) for k in M.GRID}
print("\n   Plataatesten (nivaaet og naboene positive, p <= 0,10):",
      ", ".join(f"{k} {'ja' if PL[k] else 'nei'}" for k in M.GRID))
RES["plataa"] = PL

print("\n   Episodene ved 80 (fra, antall innslag, median meravkastning 24 mnd):")
_rs = sorted(M.rader_for(SEGS, 80))
_cur, _sist, _ep = [], None, []
for o, x in _rs:
    if _cur and o - _sist > M.KLYNGEGAP:
        _ep.append(_cur); _cur = []
    _cur.append((o, x)); _sist = o
if _cur:
    _ep.append(_cur)
for e in _ep:
    print(f"      {PER(e[0][0])} til {PER(e[-1][0])}  n={len(e):2}  {fp(float(np.median([x for _, x in e])))}")


# ================================================================ 3. trinn 2
print(f"\n3. Trinn 2: nivaa valgt hvert aarsskifte fra {WF_FRA} med data kjent da\n")
aar_til = pd.Period(ordinal=TIL, freq="M").year
valg, OOS = {}, {"valgt": []}
for k in M.GRID:
    OOS[k] = []
fwd = [M.fram(s.lr) for s in SEGS]
for aar in range(WF_FRA, aar_til + 1):
    kjent = pd.Period(f"{aar - 1}-12", "M").ordinal - M.H
    best, bv = None, -np.inf
    for k in M.GRID:
        st = M.statistikk(M.rader_for(SEGS, k, til=kjent, bench_til=kjent, fwd=fwd))
        if st["episoder"] >= 3 and np.isfinite(st["S"]) and st["S"] > bv:
            best, bv = k, st["S"]
    valg[aar] = best
    a0, a1 = pd.Period(f"{aar}-01", "M").ordinal, min(pd.Period(f"{aar}-12", "M").ordinal, TIL)
    for k in M.GRID:
        OOS[k] += M.rader_for(SEGS, k, fra=a0, til=a1, fwd=fwd)
    if best is not None:
        OOS["valgt"] += M.rader_for(SEGS, best, fra=a0, til=a1, fwd=fwd)
print("   valgt nivaa per aar:", ", ".join(f"{a}:{v}" for a, v in valg.items()))
OOS_ST = {k: M.statistikk(v) for k, v in OOS.items()}
print(f"\n   Utenfor utvalget, innslag {WF_FRA} til {PER(TIL)}:")
for k in ["valgt"] + M.GRID:
    r = OOS_ST[k]
    print(f"   {str(k):>6}  {r['innslag']:3} innslag, {r['episoder']:3} episoder, {r['positive']:3} positive,  S {fp(r['S'])}")
RES["trinn2"] = {"valg": valg, "utenfor": {str(k): v for k, v in OOS_ST.items()}}


# ================================================================ 4. papirene
print("\n4. Papirene (fra instrumenttesten i samme kjoering)\n")
PAPIR = {}
try:
    it = json.load(open("sonder/instrumenttest.json", encoding="utf-8"))
    alder = (pd.Timestamp.now() - pd.Timestamp(it["kjort"])).total_seconds() / 3600
    if alder > 6:
        print(f"   instrumenttest.json er {alder:.0f} timer gammel, brukes ikke")
    else:
        for navn in ("TAVLE", "UTVIDET"):
            for k in M.GRID:
                v = it["resultat"][navn].get("a" if k == 80 else f"a{k}")
                if v:
                    PAPIR[(navn, k)] = v["h24"]["mer_aar"]
        for navn in ("TAVLE", "UTVIDET"):
            print(f"   {navn:8} meravkastning per aar over 24 mnd: " + ", ".join(
                f"{k}: {PAPIR.get((navn, k), '-')}" for k in M.GRID))
except Exception as e:
    print(f"   ikke tilgjengelig: {type(e).__name__} {str(e)[:60]}")
RES["papirer"] = {f"{a}_{k}": v for (a, k), v in PAPIR.items()}


# ================================================================ 5. beslutning
print("\n5. Beslutning etter regelen satt foer kjoering\n")
siste = valg.get(max(valg)) if valg else None
print(f"   80 bestaar plataatesten: {'ja' if PL[80] else 'NEI'}")
print(f"   trinn 2 velger i siste aar: {siste}")
endelig, grunn = 80, []
if siste is not None and siste != 80:
    ks = siste
    a = True
    b = PL[ks]
    c = (OOS_ST["valgt"]["S"] > OOS_ST[80]["S"]) and (OOS_ST[ks]["S"] > OOS_ST[80]["S"])
    d = KV[ks]["episoder"] >= 5 and andel(ks) <= 0.25
    pe = PAPIR.get(("TAVLE", ks)); p80 = PAPIR.get(("TAVLE", 80))
    e = None if pe is None or p80 is None else pe >= p80
    grunn = [f"a) valgt siste aar: ja", f"b) plataa: {'ja' if b else 'nei'}",
             f"c) slo 80 utenfor utvalget: {'ja' if c else 'nei'}",
             f"d) minst fem episoder og hoyst 25 % av maanedene: {'ja' if d else 'nei'}",
             f"e) papirene: {'ikke maalt' if e is None else ('ja' if e else 'nei')}"]
    for g in grunn:
        print("   " + g)
    if a and b and c and d and e is not False:
        endelig = ks
        print(f"\n   {ks} erstatter 80" + (" (foreloepig, papirene er ikke maalt ved dette nivaaet)" if e is None else "."))
    else:
        print("\n   80 blir staaende.")
else:
    print("   Trinn 2 velger 80 eller ingenting. 80 blir staaende.")
if endelig == 80 and not PL[80]:
    print("   80 bestaar ikke plataatesten selv. Nivaaet er ikke robust, og 80 er et foreloepig valg.")
RES["beslutning"] = {"nivaa": endelig, "plataa_80": PL[80], "siste_valg": siste, "grunner": grunn}

os.makedirs("sonder", exist_ok=True)
json.dump(RES, open("sonder/terskel.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
print("\n   lagret sonder/terskel.json")
print("\nSend hele utskriften tilbake.")
