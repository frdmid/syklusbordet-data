# ---------------------------------------------------------------------------
# sonde_kjor_timing: naar skal man kjoepe etter at flagget gaar
#
# Instrumenttesten (24.09.2026) viste at raavareflagget bærer signal inn i
# papirene, men at det kommer tidlig: median videre fall 17 % paa tolv
# maaneder, og 43 % av innslagene falt mer enn 30 % videre. Spoersmaalet her er
# om det loenner seg aa vente, og i saa fall paa hva. Sonden endrer ingenting
# paa bordet.
#
# FEM MAATER AA GAA INN PAA, SAMME INNSLAG
#   T0   kjoep ved flagget (slik bordet leses i dag)
#   T1   vent til trendfeltet for raavaren staar paa Bekreftet (hoyere enn for
#        tolv maaneder siden OG over ti maaneders snitt, samme regel som feltet
#        paa bordet)
#   T2   vent til papirets egen kurs er Bekreftet etter samme regel
#   T3   spre kjoepet likt over seks maaneder fra flagget
#   T4   spre kjoepet likt over tolv maaneder
#   Venter T1 eller T2 mer enn 24 maaneder, blir pengene staaende i kontanter.
#   Kontanter gir realrenten paa amerikanske statskasseveksler (^IRX minus
#   KPI). Alle strategier maales fram til samme dato, 36 maaneder etter
#   flagget, slik at venting ikke faar kortere tid i markedet gratis.
#
# INNSLAG OG UNIVERS
#   Samme som variant a i instrumenttesten: papirer som skal foelge en av de
#   seksten raavarene som produsent, innslag naar en av papirets raavarer staar
#   i bunnsone, nytt innslag foerst etter tolv maaneder uten. Kursene leses fra
#   sonder/instrument_kurser.csv, som instrumenttesten skriver i samme
#   kjoering. Innslag fra 2011-09 til 36 maaneder foer siste kurs.
#   To utvalg som i instrumenttesten: TAVLE og UTVIDET. UTVIDET er primaert
#   fordi det har flest papirer i samme episoder.
#
#   Ved siden av: det samme paa raavareprisen selv, over hele historikken fra
#   1965, med T0, T1, T3 og T4. Raavaren kan ikke kjoepes paa IKZ, men har
#   mange flere episoder, og viser om et funn paa papirene holder over tid.
#
# MAAL
#   Per innslag: log formue ved 36 maaneder for hver strategi minus T0.
#   Episoder (innslag med hoyst seks maaneder mellom) er enheten: S = snittet
#   over episodene av episodens median forskjell. Vist som prosentpoeng i aaret.
#   Verste punkt: laveste verdi underveis mot 1 krone ved flagget, median.
#
# TEST FOR VENTING (T1, T2)
#   Venting i seg selv kan loenne seg eller koste bare fordi prisen i snitt
#   stiger eller faller etter flagget. Det testes ikke. Det som testes er om
#   regelen velger et bedre TIDSPUNKT enn tilfeldig venting: hver episode faar
#   en tilfeldig ventetid trukket fra regelens egne ventetider, 1000 ganger.
#   p er andelen trekk som gjorde det minst like godt.
#
# BESLUTNINGSREGEL, SATT FOER KJOERING
#   T1 (vent paa raavaretrend) anbefales hvis BEGGE holder:
#     papirene, UTVIDET: S > 0 mot T0 og flertallet av episodene positive
#     raavaren, hele historikken: S > 0 og fortegnstest paa episodene p <= 0,10
#   T2 (vent paa papirets trend) anbefales hvis S > 0 paa UTVIDET og
#     fortegnstesten paa episodene gir p <= 0,10. Raavaren har ikke noe
#     motstykke til T2.
#   Spredning (T3 eller T4) anbefales hvis S >= 0 mot T0 paa UTVIDET, altsaa
#   lavere risiko uten tapt avkastning. Er S negativ, vises kostnaden per aar
#   og hvor mye verste punkt bedres, og valget er Frodes.
#   Ellers staar T0: kjoep ved flagget.
#   Testen mot tilfeldig venting rapporteres, men avgjoer ikke (se under).
#
# KALIBRERING OG STYRKE (kal_timing.py, simulerte raavarer og papirer med
# lengder og universstoerrelse som de ekte)
#   Uten forutsigbarhet (200 datasett), andel p under 0,05 mot tilfeldig
#   venting: T1 2,5 %, T2 2,0 % paa UTVIDET, 0,5 til 2,5 % ellers. Gyldig,
#   og streng: aa vente paa bekreftet trend betyr aa kjoepe etter en oppgang,
#   og uten momentum taper regelen den oppgangen mot tilfeldig venting.
#   Med sterkt momentum lagt inn (AR(1) 0,3 i raavarenes maanedsendringer,
#   40 datasett) fant den samme testen det i 0 til 8 %. Den har altsaa nesten
#   ingen styrke med aatte episoder, og et krav om p <= 0,05 ville gitt T0
#   uansett data. Foerste utkast av regelen hadde det kravet. Det er byttet ut
#   FOER sonden er kjoert paa ekte data.
#   Regelen over for T1: 2 % falske funn uten momentum (48 datasett), 9 % med
#   sterkt momentum (44). For T2: 2 % uten momentum. Lav styrke betyr at et nei
#   her er "ikke paavist", ikke "virker ikke".
# ---------------------------------------------------------------------------

import io, json, os, time, warnings
import numpy as np
import pandas as pd
import requests

import timing_motor as T

warnings.filterwarnings("ignore")
rng = np.random.default_rng(20260925)
FRA = pd.Period("2011-09", "M")
TREKK = 1000
KALIBRERT = {"null_p05": {"UTVIDET_T1": 0.025, "UTVIDET_T2": 0.020, "TAVLE_T1": 0.025,
                          "TAVLE_T2": 0.005, "RAAVARE_T1": 0.020, "datasett": 200},
             "momentum_p05": {"UTVIDET_T1": 0.0, "UTVIDET_T2": 0.05, "RAAVARE_T1": 0.08, "datasett": 40},
             "regel_T1": {"uten_momentum": 0.02, "med_momentum": 0.09}}
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
RES = {"kjort": time.strftime("%Y-%m-%d %H:%M:%S"), "kalibrering": KALIBRERT}
pp = lambda v: "-" if v is None or not np.isfinite(v) else f"{100 * v * 12 / T.HORISONT:+6.1f}"
pr = lambda v: "-" if v is None or not np.isfinite(v) else f"{100 * v:+6.1f} %"

# ================================================================ 1. data
print("1. Data\n")
TEST = os.environ.get("SONDE_TEST_PKL")
if TEST:
    import pickle
    REAL, KURS, UNIV, CPI, IRX = pickle.load(open(TEST, "rb"))
    print("   TESTDATA, ikke ekte")
else:
    try:
        uv = json.load(open("sonder/instrument_univers.json", encoding="utf-8"))
        alder = (pd.Timestamp.now() - pd.Timestamp(uv["kjort"])).days
        UNIV = uv["univers"]
        KURS = pd.read_csv("sonder/instrument_kurser.csv", index_col=0)
        KURS.index = pd.PeriodIndex(KURS.index, freq="M")
        print(f"   kurser fra instrumenttesten {uv['kjort']} ({alder} dager gamle): {KURS.shape[1]} papirer")
    except Exception as e:
        raise SystemExit(f"   Fant ikke kursene fra instrumenttesten ({type(e).__name__}: {e}). "
                         "Den maa kjoere foer denne. Send utskriften til Claude.")
    from raavare_hist import hent
    REAL, _NOM, CPI = hent()
    IRX = None
    try:
        r = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/%5EIRX"
                         f"?period1=0&period2={int(time.time())}&interval=1mo", headers=UA, timeout=40).json()
        r = r["chart"]["result"][0]
        idx = pd.to_datetime(r["timestamp"], unit="s", utc=True).to_period("M")
        IRX = pd.Series(r["indicators"]["quote"][0]["close"], index=idx).dropna()
        IRX = IRX[~IRX.index.duplicated(keep="last")]
    except Exception as e:
        print(f"   ^IRX feilet ({type(e).__name__}), kontanter regnes med nominell rente 0")

# felles kalender
alle = [s.index for s in REAL.values()] + [KURS.index]
g0 = min(ix[0] for ix in alle); g1 = max(ix[-1] for ix in alle)
KAL = pd.period_range(g0, g1, freq="M")
POS = {p: i for i, p in enumerate(KAL)}
infl = np.log(CPI.reindex(KAL).ffill()).diff().fillna(0).values
if IRX is not None:
    nom = np.log(1 + IRX.reindex(KAL).ffill().fillna(0).values / 100 / 12)
    print(f"   kontanter: ^IRX fra {IRX.index[0]} minus KPI")
else:
    nom = np.zeros(len(KAL))
C = np.cumsum(nom - infl)
SISTE_T = KAL[-1] - T.HORISONT
print(f"   kalender {KAL[0]} til {KAL[-1]}, innslag med 36 mnd fasit til {SISTE_T}")


def paa_kal(s):
    """Paa felles kalender. Hull inne i serien paa inntil to maaneder fylles med
    forrige verdi, ellers ville ett manglende kurspunkt slette hele innslaget."""
    return s.reindex(KAL).ffill(limit=2).where(lambda x: x.index <= s.index[-1]).values


LP_RAA = {sid: paa_kal(lr) for sid, lr in REAL.items()}
BEKR_RAA = {sid: T.bekreftet(np.exp(v)) for sid, v in LP_RAA.items()}
from raavare_hist import pct_raa, pct_det
FLAGG_RAA = {}
for sid, lr in REAL.items():
    A, Ad = pct_raa(lr.values), pct_det(lr.values)
    f = np.isfinite(A) & np.isfinite(Ad) & (A >= 80) & (Ad >= 80)
    FLAGG_RAA[sid] = pd.Series(f, index=lr.index).reindex(KAL).fillna(False).values.astype(bool)
LP_PAP = {tk: paa_kal(np.log(KURS[tk].dropna())) for tk in KURS.columns}
BEKR_PAP = {tk: T.bekreftet(np.exp(v)) for tk, v in LP_PAP.items()}


# ================================================================ 2. papirene
def papirinnslag(papirer):
    """Variant a fra instrumenttesten, med ventetider for T1 og T2."""
    rader = []
    for tk in papirer:
        segs = [s for s in UNIV[tk]["segs"] if s in FLAGG_RAA]
        if not segs:
            continue
        fl = np.zeros(len(KAL), bool)
        for s in segs:
            fl |= FLAGG_RAA[s]
        fl &= np.isfinite(LP_PAP[tk])
        fl[:POS[FRA]] = False
        for t in T.innslag(fl):
            if KAL[t] > SISTE_T:
                continue
            flaggede = [s for s in segs if FLAGG_RAA[s][t]]
            d1 = min(T.forste(BEKR_RAA[s], t) for s in flaggede)
            d2 = T.forste(BEKR_PAP[tk], t)
            rader.append({"tk": tk, "t": t, "segs": flaggede, "d1": d1, "d2": d2})
    return rader


def rapport(navn, rader, lp_av, strategier, raavare=False):
    if not rader:
        print(f"   {navn}: ingen innslag"); return None
    inn = [(r["tk"], r["t"]) for r in rader]
    W, W6, W12, V, V6, V12 = T.tabell(lp_av, C, inn)
    ok = np.isfinite(W[:, 0])
    if not ok.any():
        print(f"   {navn}: {len(rader)} innslag, ingen med fullstendig kurs 36 maaneder fram"); return None
    rader = [r for r, o in zip(rader, ok) if o]
    W, W6, W12, V, V6, V12 = W[ok], W6[ok], W12[ok], V[ok], V6[ok], V12[ok]
    pos = np.array([r["t"] for r in rader])
    kl = T.klynger(pos)
    rad = np.arange(len(rader))
    print(f"\n   {navn}: {len(rader)} innslag, {len(np.unique(kl))} episoder, "
          f"{len({r['tk'] for r in rader})} {'raavarer' if raavare else 'papirer'}\n")
    print(f"   {'':34} {'S mot T0':>9} {'pos ep':>7} {'p':>6} | {'formue':>8} {'verste':>8} {'ventet':>7} {'aldri':>6}")
    print(f"   {'':34} {'pp/aar':>9} {'':>7} {'':>6} | {'median':>8} {'median':>8} {'median':>7} {'kjoept':>6}")
    ut = {}
    s0 = W[:, 0]
    fmt = lambda x: "-" if not np.isfinite(x) else f"{100 * (np.exp(x) - 1):+7.1f}%"
    print(f"   {'T0 kjoep ved flagget':34} {'':>9} {'':>7} {'':>6} | {fmt(np.median(s0))} "
          f"{100 * np.median(V[:, 0]):+7.1f}% {0:7} {'':>6}")
    ut["T0"] = {"formue_median": float(np.median(s0)), "verste_median": float(np.median(V[:, 0]))}
    for kode, tekst in strategier:
        if kode in ("T1", "T2"):
            d = np.array([r["d1" if kode == "T1" else "d2"] for r in rader])
            w, v = W[rad, d], V[rad, d]
            if kode == "T1" and not raavare:
                nokler = sorted({(int(c), tuple(r["segs"])) for c, r in zip(kl, rader)})
                gruppe = np.array([nokler.index((int(c), tuple(r["segs"]))) for c, r in zip(kl, rader)])
            else:
                gruppe = None          # hvert innslag for seg
            obs, p, nullmed = T.mot_tilfeldig(W, d, kl, rng, TREKK, gruppe)
            vent = d[d != T.KONT]
            ventet = float(np.median(vent)) if len(vent) else np.nan
            aldri = float(np.mean(d == T.KONT))
        else:
            w, v = (W6, V6) if kode == "T3" else (W12, V12)
            p, nullmed, ventet, aldri = np.nan, np.nan, np.nan, np.nan
        s, npos, nep = T.S(w - s0, kl)
        print(f"   {kode + ' ' + tekst:34} {pp(s):>9} {npos:3}/{nep:<3} {('-' if not np.isfinite(p) else f'{p:.3f}'):>6} | "
              f"{fmt(np.median(w))} {100 * np.nanmedian(v):+7.1f}% "
              f"{('-' if not np.isfinite(ventet) else f'{ventet:.0f} mnd'):>7} "
              f"{('-' if not np.isfinite(aldri) else f'{100 * aldri:.0f} %'):>6}")
        ut[kode] = {"S": s, "S_pp_aar": None if not np.isfinite(s) else 100 * s * 12 / T.HORISONT,
                    "pos": npos, "ep": nep, "p": p, "null_median": nullmed,
                    "formue_median": float(np.median(w)), "verste_median": float(np.nanmedian(v)),
                    "ventet_median": ventet, "aldri": aldri}
    # episodene
    print("\n   Per episode (fra, innslag, median forskjell mot T0 over 36 mnd i prosentpoeng log):")
    for c in np.unique(kl):
        m = kl == c
        fra = KAL[pos[m].min()]
        linje = []
        for kode, _ in strategier:
            if kode in ("T1", "T2"):
                d = np.array([r["d1" if kode == "T1" else "d2"] for r in rader])
                x = W[rad, d][m] - s0[m]
            else:
                x = (W6 if kode == "T3" else W12)[m] - s0[m]
            linje.append(f"{kode} {100 * np.median(x):+6.1f}")
        print(f"      {fra}  n={m.sum():3}   " + "   ".join(linje))
    ut["episoder"] = int(len(np.unique(kl)))
    ut["innslag"] = [{"navn": r["tk"], "t": str(KAL[r["t"]]), "d1": int(r["d1"]), "d2": int(r["d2"])} for r in rader]
    return ut


print("\n2. Papirene (primaert)")
print("   S: snittet over episodene av median forskjell i log formue mot T0, i prosentpoeng per aar.")
print("   p: mot tilfeldig venting med samme fordeling av ventetider. Verste: laveste punkt underveis.")
STRAT = [("T1", "vent paa raavaretrend"), ("T2", "vent paa papirets trend"),
         ("T3", "spre over 6 mnd"), ("T4", "spre over 12 mnd")]
TAV = [tk for tk, u in UNIV.items() if u.get("tavle") and tk in LP_PAP]
UTV = [tk for tk in UNIV if tk in LP_PAP]
RES["UTVIDET"] = rapport("UTVIDET", papirinnslag(UTV), LP_PAP, STRAT)
RES["TAVLE"] = rapport("TAVLE", papirinnslag(TAV), LP_PAP, STRAT)


# ================================================================ 3. raavaren
print("\n3. Raavaren selv over hele historikken (ved siden av)")
rr = []
for sid in LP_RAA:
    for t in T.innslag(FLAGG_RAA[sid]):
        if KAL[t] > SISTE_T:
            continue
        rr.append({"tk": sid, "t": t, "d1": T.forste(BEKR_RAA[sid], t), "d2": T.KONT})
RES["RAAVARE"] = rapport("RAAVARE", rr, LP_RAA, [("T1", "vent paa trend"), ("T3", "spre over 6 mnd"),
                                                 ("T4", "spre over 12 mnd")], raavare=True)


# ================================================================ 4. beslutning
print("\n4. Beslutning etter regelen satt foer kjoering\n")
U, R = RES.get("UTVIDET") or {}, RES.get("RAAVARE") or {}
anbef = []
from math import comb
def fortegn_p(k, n):
    """Ensidig fortegnstest: sannsynligheten for minst k positive av n ved myntkast."""
    return sum(comb(n, j) for j in range(k, n + 1)) / 2 ** n if n else 1.0
for kode in ("T1", "T2"):
    x = U.get(kode)
    if not x:
        continue
    if kode == "T1":
        r = R.get("T1")
        krav = [x["S"] > 0, x["pos"] > x["ep"] / 2,
                bool(r) and r["S"] > 0, bool(r) and fortegn_p(r["pos"], r["ep"]) <= 0.10]
        tekst = ("papirer S > 0", "flertall positive episoder",
                 "raavaren S > 0", f"raavaren fortegnstest p <= 0,10 ({fortegn_p(r['pos'], r['ep']):.3f})" if r else "raavaren")
    else:
        krav = [x["S"] > 0, fortegn_p(x["pos"], x["ep"]) <= 0.10]
        tekst = ("papirer S > 0", f"fortegnstest p <= 0,10 ({fortegn_p(x['pos'], x['ep']):.3f})")
    print(f"   {kode}: " + ", ".join(f"{t} {'ja' if k else 'nei'}" for t, k in zip(tekst, krav))
          + f"   (mot tilfeldig venting: p = {x['p']:.3f}, avgjoer ikke)")
    if all(krav):
        anbef.append(kode)
for kode in ("T3", "T4"):
    x = U.get(kode)
    if not x:
        continue
    if x["S"] >= 0:
        print(f"   {kode}: S >= 0, spredningen kostet ikke avkastning. Anbefales.")
        anbef.append(kode)
    else:
        bedre = 100 * (x["verste_median"] - U["T0"]["verste_median"])
        kost = 100 * -x["S"] * 12 / T.HORISONT
        print(f"   {kode}: kostet {kost:.1f} prosentpoeng i aaret mot T0. Verste punkt underveis ble "
              f"{abs(bedre):.1f} prosentpoeng {'bedre' if bedre >= 0 else 'daarligere'} i median. "
              + ("Avveiing, Frodes valg." if bedre > 0 else "Daarligere paa begge, anbefales ikke."))
if not any(k in anbef for k in ("T1", "T2", "T3", "T4")):
    print("\n   T0 staar: kjoep ved flagget.")
else:
    print(f"\n   Anbefalt etter regelen: {', '.join(anbef)}")
RES["anbefalt"] = anbef or ["T0"]

os.makedirs("sonder", exist_ok=True)
json.dump(RES, open("sonder/timing.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
print("\n   lagret sonder/timing.json")
print("\nSend hele utskriften tilbake.")
