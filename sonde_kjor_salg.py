# ---------------------------------------------------------------------------
# sonde_kjor_salg: naar skal man selge etter et bunnkjoep
#
# Bordet sier naar noe er billig, og timingsonden maaler naar man skal gaa
# inn. Ingenting har sagt naar man skal ut, og det avgjoer avkastningen like
# mye. Sonden endrer ingenting paa bordet. Beslutningsregelen under er
# godkjent av Frode 24.09.2026, foer sonden er kjoert paa ekte data.
#
# INNGANG
#   Samme innslag som instrumenttesten og timingsonden: raavaren gaar inn i
#   bunnsone (raa og detrendet A >= 80), kjoep ved flagget, nytt innslag i
#   samme papir foerst etter tolv maaneder uten flagg.
#
# FEM SALGSREGLER, den som slaar til foerst avslutter
#   S0  fast holdetid 24 maaneder. Referansen, fordi instrumenttesten maalte
#       signalet over 24 maaneder.
#   S1  normalisering: selg foerste maaned raavarens A er 50 eller lavere,
#       altsaa prisen er tilbake over medianen av egen historikk. Det er det
#       bunnflagget satser paa.
#   S2  toppsone: selg naar raavarens raa og detrendete A begge er 20 eller
#       lavere. Speilbildet av inngangen.
#   S3  trendbrudd i raavaren: etter at trenden har vaert Bekreftet minst en
#       gang siden kjoepet, selg foerste maaned den staar paa Nei.
#   S4  trendbrudd i papiret selv, samme regel. Bare paa papirene.
#   S5  armert normalisering (lagt til 24.09.2026 etter godkjenning fra Frode,
#       foer kjoering): naar raavarens A foerst er 50 eller lavere, er regelen
#       armert, men salget skjer foerste maaned fra da av der trenden i
#       raavaren staar paa Nei. Skal hindre at en nivaaregel selger midt i en
#       oppgang som skyter over.
#   Har ingen regel slaatt til innen 60 maaneder, verdsettes posisjonen da.
#   Etter salg staar pengene i kontanter (realrenten paa statskasseveksler).
#   Alle regler maales fram til samme dato, 60 maaneder etter kjoepet, slik at
#   tidlig salg ikke faar noe gratis. Er flere raavarer flagget for samme
#   papir, gjelder den foerste som utloeser regelen.
#
# TO LAG
#   Raavaren selv over hele historikken fra 1965 (primaert, fordi det gir
#   rundt 40 episoder: papirene har bare fire eller fem med 60 maaneders
#   fasit). Papirene 2011 til 2021 fra instrumenttesten, beskrivende og som
#   kontroll av fortegn.
#
# MAAL
#   Per innslag: log formue ved 60 maaneder med regelen minus med S0.
#   S = snittet over episodene (innslag med hoyst seks maaneder mellom) av
#   episodens median forskjell, vist som prosentpoeng i aaret.
#   Mot tilfeldig salg: holdetiden trekkes tilfeldig fra regelens egne
#   holdetider, 1000 ganger. Det skiller "regelen treffer tidspunktet" fra
#   "regelen holder bare kortere eller lenger".
#
# BESLUTNINGSREGEL, SATT FOER KJOERING (godkjent av Frode 24.09.2026)
#   S1, S2, S3 eller S5 erstatter S0 bare hvis ALT holder:
#     raavaren: S > 0 mot S0, og p <= 0,0125 mot tilfeldig salg (0,05 delt
#     paa fire regler)
#     papirene (UTVIDET): S >= 0 mot S0
#   Bestaar flere, velges den med hoeyest S paa raavaren. Ellers staar S0.
#   S4 er beskrivende, for faa episoder.
#   I tillegg, uten test (for lite data): stenger overlevelsesporten C for et
#   papir, selges det. Det er en risikoregel, ikke en avkastningsregel.
#
# KALIBRERING OG STYRKE (kal_salg.py, sonden kjoert paa simulerte data)
#   Foerste utkast trakk tilfeldig holdetid per innslag. Det ga 7 til 14 %
#   falske funn for S1 og S2 der 5 % er riktig, fordi nivaaregler selger alle
#   raavarene i en episode omtrent samtidig. Nullen trekker naa en holdetid per
#   episode. Rettet foer kjoering paa ekte data.
#   Uten tilbakevending (149 datasett), andel p <= 0,05 per regel: S1 4,7 %,
#   S2 6,0 %, S3 2,7 %, S5 6,7 %. Gyldig per regel. Men med fire regler ville
#   en av dem blitt valgt i 17 % av tilfellene ved 0,05. Grensen er derfor
#   0,05 delt paa fire, 0,0125, som ga 6,0 % samlet feilvalg foer papirkravet,
#   som senker det videre.
#   Med en tilbakevendende syklus lagt inn (60 datasett, halveringstid rundt to
#   aar) valgte regelen S1 eller S2 i 33 % av tilfellene ved 0,0125. S5 fant
#   lite (2 %), men simuleringen har ingen overskyting med momentum, som er det
#   S5 skal fange. At S5 ikke vinner i simuleringen sier derfor ingenting om
#   den ekte historikken. S3 fant ingenting, som ventet.
# ---------------------------------------------------------------------------

import json, os, time, warnings
import numpy as np
import pandas as pd
import requests

warnings.filterwarnings("ignore")
rng = np.random.default_rng(20260925)
FRA = pd.Period("2011-09", "M")
H = 60
TREKK = 1000
KLYNGEGAP = 6
PAUSE = 12
KALIBRERT = {"null_datasett": 149, "null_p05": {"S1": 0.047, "S2": 0.060, "S3": 0.027, "S5": 0.067},
             "grense": 0.0125, "feilvalg_grense": 0.060, "sykel_datasett": 60, "styrke_grense": 0.333}
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
RES = {"kjort": time.strftime("%Y-%m-%d %H:%M:%S"), "horisont": H, "kalibrering": KALIBRERT}
pp = lambda v: "-" if v is None or not np.isfinite(v) else f"{100 * v * 12 / H:+6.1f}"
fmt = lambda x: "-" if not np.isfinite(x) else f"{100 * (np.exp(x) - 1):+7.1f}%"

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
        UNIV = uv["univers"]
        KURS = pd.read_csv("sonder/instrument_kurser.csv", index_col=0)
        KURS.index = pd.PeriodIndex(KURS.index, freq="M")
        print(f"   kurser fra instrumenttesten {uv['kjort']}: {KURS.shape[1]} papirer")
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

from raavare_hist import pct_raa, pct_det
from timing_motor import bekreftet

alle = [s.index for s in REAL.values()] + [KURS.index]
KAL = pd.period_range(min(ix[0] for ix in alle), max(ix[-1] for ix in alle), freq="M")
POS = {p: i for i, p in enumerate(KAL)}
infl = np.log(CPI.reindex(KAL).ffill()).diff().fillna(0).values
nom = (np.log(1 + IRX.reindex(KAL).ffill().fillna(0).values / 100 / 12) if IRX is not None
       else np.zeros(len(KAL)))
C = np.cumsum(nom - infl)
SISTE_T = KAL[-1] - H
print(f"   kalender {KAL[0]} til {KAL[-1]}, innslag med {H} mnd fasit til {SISTE_T}")


def paa_kal(s):
    return s.reindex(KAL).ffill(limit=2).where(lambda x: x.index <= s.index[-1]).values


def nei(real):
    """Trendfeltet paa Nei: ikke hoyere enn for tolv maaneder siden OG under ti maaneders snitt."""
    v = np.asarray(real, float)
    ma10 = pd.Series(v).rolling(10).mean().values
    m12 = np.full(len(v), np.nan)
    m12[12:] = v[12:] / v[:-12] - 1
    with np.errstate(invalid="ignore"):
        return (m12 <= 0) & (v <= ma10)


RAA = {}
for sid, lr in REAL.items():
    A, Ad = pct_raa(lr.values), pct_det(lr.values)
    ser = lambda x: pd.Series(x, index=lr.index).reindex(KAL).values
    lp = paa_kal(lr)
    RAA[sid] = {"lp": lp, "A": ser(A), "Ad": ser(Ad),
                "flagg": np.nan_to_num(ser(np.isfinite(A) & np.isfinite(Ad) & (A >= 80) & (Ad >= 80)
                                           ).astype(float)).astype(bool),
                "bekr": bekreftet(np.exp(lp)), "nei": nei(np.exp(lp))}
PAP = {}
for tk in KURS.columns:
    lp = paa_kal(np.log(KURS[tk].dropna()))
    PAP[tk] = {"lp": lp, "bekr": bekreftet(np.exp(lp)), "nei": nei(np.exp(lp))}


# ================================================================ 2. reglene
def forste(b, t, fra=1):
    for m in range(t + fra, t + H + 1):
        if m < len(b) and b[m]:
            return m
    return t + H


def trendbrudd(bekr, neiv, t):
    m1 = None
    for m in range(t + 1, t + H + 1):
        if m1 is None and bekr[m]:
            m1 = m
        elif m1 is not None and neiv[m]:
            return m
    return t + H


def armert(A, neiv, t):
    """S5: foerste maaned med A <= 50 armerer, salg foerste maaned fra da med trend Nei."""
    m1 = None
    for m in range(t + 1, t + H + 1):
        if m1 is None and np.isfinite(A[m]) and A[m] <= 50:
            m1 = m
        if m1 is not None and neiv[m]:
            return m
    return t + H


def salg(raa_list, pap, t):
    """Salgsmaaned for hver regel. raa_list: de flaggede raavarene (dicts)."""
    with np.errstate(invalid="ignore"):
        e = {"S0": t + 24,
             "S1": min(forste(r["A"] <= 50, t) for r in raa_list),
             "S2": min(forste((r["A"] <= 20) & (r["Ad"] <= 20), t) for r in raa_list),
             "S3": min(trendbrudd(r["bekr"], r["nei"], t) for r in raa_list),
             "S5": min(armert(r["A"], r["nei"], t) for r in raa_list)}
    if pap is not None:
        e["S4"] = trendbrudd(pap["bekr"], pap["nei"], t)
    return e


def logw(lp, t, e):
    """Kjoep ved t, selg ved e, kontanter til t+H."""
    if t + H >= len(lp) or not (np.isfinite(lp[t]) and np.isfinite(lp[e])):
        return np.nan
    return lp[e] - lp[t] + C[t + H] - C[e]


def klynger(pos):
    rek = np.argsort(pos, kind="stable")
    kl = np.zeros(len(pos), int); c, sist = 0, None
    for i in rek:
        if sist is not None and pos[i] - sist > KLYNGEGAP:
            c += 1
        kl[i] = c; sist = pos[i]
    return kl


def S(diff, kl):
    ok = np.isfinite(diff)
    if not ok.any():
        return np.nan, 0, 0
    v = np.array([np.median(diff[ok & (kl == c)]) for c in np.unique(kl[ok])])
    return float(v.mean()), int((v > 0).sum()), len(v)


def innslag(fl):
    ut, siste = [], None
    for i in np.flatnonzero(fl):
        if siste is None or i - siste > PAUSE:
            ut.append(int(i))
        siste = i
    return ut


def rapport(navn, rader, regler, raavare):
    """rader: dict med lp, t, e (regel -> salgsmaaned)."""
    if not rader:
        print(f"\n   {navn}: ingen innslag"); return None
    W = {k: np.array([logw(r["lp"], r["t"], r["e"][k]) for r in rader]) for k in ["S0"] + regler}
    ok = np.isfinite(W["S0"])
    for k in regler:
        ok &= np.isfinite(W[k])
    if not ok.any():
        print(f"\n   {navn}: {len(rader)} innslag, ingen med fullstendig kurs {H} maaneder fram"); return None
    rader = [r for r, o in zip(rader, ok) if o]
    W = {k: v[ok] for k, v in W.items()}
    pos = np.array([r["t"] for r in rader]); kl = klynger(pos)
    print(f"\n   {navn}: {len(rader)} innslag, {len(np.unique(kl))} episoder, "
          f"{len({r['navn'] for r in rader})} {'raavarer' if raavare else 'papirer'}\n")
    print(f"   {'':30} {'S mot S0':>9} {'pos ep':>7} {'p':>6} | {'formue':>8} {'holdt':>7} {'aldri':>6}")
    print(f"   {'':30} {'pp/aar':>9} {'':>7} {'':>6} | {'median':>8} {'median':>7} {'utloest':>6}")
    TEKST = {"S0": "fast 24 mnd", "S1": "normalisering, A <= 50", "S2": "toppsone, A og Ad <= 20",
             "S3": "trendbrudd raavaren", "S4": "trendbrudd papiret",
             "S5": "armert A <= 50, selg Nei"}
    print(f"   {'S0 ' + TEKST['S0']:30} {'':>9} {'':>7} {'':>6} | {fmt(np.median(W['S0']))} {24:4} mnd {'':>6}")
    ut = {"S0": {"formue_median": float(np.median(W["S0"]))}, "episoder": int(len(np.unique(kl)))}
    TAB = np.array([[logw(r["lp"], r["t"], r["t"] + l) for l in range(H + 1)] for r in rader])
    for k in regler:
        L = np.array([r["e"][k] - r["t"] for r in rader])
        s, npos, nep = S(W[k] - W["S0"], kl)
        # Mot tilfeldig holdetid fra regelens egen fordeling. En trekning per
        # episode, brukt paa alle innslag i episoden. Foerste utkast trakk per
        # innslag, og ga 7 til 14 % falske funn for S1 og S2 der 5 % er riktig:
        # nivaaregler selger alle raavarene i en episode omtrent samtidig, og
        # uavhengige trekk gir en null som svinger for lite.
        ukl, kidx = np.unique(kl, return_inverse=True)
        null = []
        for _ in range(TREKK):
            Lr = rng.choice(L, len(ukl))[kidx]
            wr = TAB[np.arange(len(rader)), Lr]
            null.append(S(wr - W["S0"], kl)[0])
        null = np.array([x for x in null if np.isfinite(x)])
        p = float(((null >= s).sum() + 1) / (len(null) + 1)) if len(null) and np.isfinite(s) else np.nan
        aldri = float(np.mean(L >= H))
        print(f"   {k + ' ' + TEKST[k]:30} {pp(s):>9} {npos:3}/{nep:<3} {p:6.3f} | {fmt(np.median(W[k]))} "
              f"{np.median(L):4.0f} mnd {100 * aldri:5.0f} %")
        ut[k] = {"S": s, "S_pp_aar": 100 * s * 12 / H if np.isfinite(s) else None, "pos": npos, "ep": nep,
                 "p_mot_tilfeldig": p, "formue_median": float(np.median(W[k])),
                 "holdt_median": float(np.median(L)), "aldri_utloest": aldri}
    print("\n   Per episode (fra, innslag, median forskjell mot S0 over 60 mnd, prosentpoeng log):")
    for c in np.unique(kl):
        m = kl == c
        print(f"      {KAL[pos[m].min()]}  n={m.sum():3}   "
              + "   ".join(f"{k} {100 * np.median(W[k][m] - W['S0'][m]):+6.1f}" for k in regler))
    ut["innslag"] = [{"navn": r["navn"], "t": str(KAL[r["t"]]), **{k: str(KAL[min(v, len(KAL) - 1)]) for k, v in r["e"].items()}}
                     for r in rader]
    return ut


print("\n   p: andelen av 1000 trekk med tilfeldig holdetid (fra regelens egne holdetider) som gjorde")
print("   det minst like godt mot S0. Lav p betyr at regelen treffer tidspunktet, ikke bare lengden.")

# ================================================================ 3. raavaren
print("\n2. Raavaren selv over hele historikken (primaert)")
rr = []
for sid, d in RAA.items():
    for t in innslag(d["flagg"]):
        if KAL[t] > SISTE_T:
            continue
        rr.append({"navn": sid, "lp": d["lp"], "t": t, "e": salg([d], None, t)})
RES["RAAVARE"] = rapport("RAAVARE", rr, ["S1", "S2", "S3", "S5"], True)

# ================================================================ 4. papirene
print("\n3. Papirene (kontroll av fortegn, beskrivende)")


def papirinnslag(papirer):
    ut = []
    for tk in papirer:
        segs = [s for s in UNIV[tk]["segs"] if s in RAA]
        if not segs:
            continue
        fl = np.zeros(len(KAL), bool)
        for s in segs:
            fl |= RAA[s]["flagg"]
        fl &= np.isfinite(PAP[tk]["lp"])
        fl[:POS[FRA]] = False
        for t in innslag(fl):
            if KAL[t] > SISTE_T:
                continue
            flaggede = [RAA[s] for s in segs if RAA[s]["flagg"][t]]
            ut.append({"navn": tk, "lp": PAP[tk]["lp"], "t": t, "e": salg(flaggede, PAP[tk], t)})
    return ut


UTV = [tk for tk in UNIV if tk in PAP]
TAV = [tk for tk, u in UNIV.items() if u.get("tavle") and tk in PAP]
RES["UTVIDET"] = rapport("UTVIDET", papirinnslag(UTV), ["S1", "S2", "S3", "S4", "S5"], False)
RES["TAVLE"] = rapport("TAVLE", papirinnslag(TAV), ["S1", "S2", "S3", "S4", "S5"], False)

# ================================================================ 5. beslutning
print("\n4. Beslutning etter regelen satt foer kjoering\n")
R, U = RES.get("RAAVARE") or {}, RES.get("UTVIDET") or {}
best, bestS = "S0", -np.inf
for k in ("S1", "S2", "S3", "S5"):
    r, u = R.get(k), U.get(k)
    krav = [bool(r) and r["S"] > 0, bool(r) and r["p_mot_tilfeldig"] <= 0.0125,
            bool(u) and u["S"] is not None and np.isfinite(u["S"]) and u["S"] >= 0]
    tekst = ("raavaren S > 0", "raavaren p <= 0,0125 mot tilfeldig salg", "papirene S >= 0")
    print(f"   {k}: " + ", ".join(f"{t} {'ja' if x else 'nei'}" for t, x in zip(tekst, krav)))
    if all(krav) and r["S"] > bestS:
        best, bestS = k, r["S"]
print(f"\n   Salgsregel etter testen: {best}" + ("  (fast holdetid 24 maaneder staar)" if best == "S0" else ""))
print("   Risikoregel uten test: selg hvis overlevelsesporten C stenger for papiret.")
print("   Beslutningsregelen er godkjent av Frode 24.09.2026. Regelen over gjelder fra naa.")
RES["valgt"] = best

os.makedirs("sonder", exist_ok=True)
json.dump(RES, open("sonder/salg.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
print("\n   lagret sonder/salg.json")
print("\nSend hele utskriften tilbake.")
