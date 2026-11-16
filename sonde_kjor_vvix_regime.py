# ---------------------------------------------------------------------------
# sonde_kjor_vvix_regime: gir bunnsonen ulik avkastning i ulike VVIX-regimer,
# og i kombinasjoner av hoy og lav VIX og VVIX? (Frodes bestilling 16.11.2026)
#
# BAKGRUNN. sonde_kjor_signal_vix_dxy_move (03.11.2026) testet nivaaet paa VIX,
# DXY og MOVE ved signal, i tredjedeler av persentilen, og ingenting holdt.
# sonde_kjor_vvix_sjokk (11.11.2026) testet VVIX og spredningen i VIX som
# sjokkmaal, ogsaa i tredjedeler, og ingenting holdt; VVIX kunne ikke avgjoeres.
# Det nye her er tre ting: ABSOLUTTE grenser i stedet for persentiltredjedeler
# (Frodes poeng 11.11: vol er vol), KOMBINASJONER av to ledd, og horisonten
# 9 maaneder. Prioren er altsaa lav, og det staar her foer kjoering.
#
# SIGNAL. Championens bunnsone, A raa >= 80 og A detrendet >= 80 i maaned t,
#   realpris fra serier/priser_mnd.csv, punkt i tid, alle 18 raavarer.
# UTFALL. Endring i log realpris for raavaren de neste h maanedene
#   (3, 6, 9, 12, 24). Raavaren og ikke papirene, saa overlevelsesskjevheten i
#   instrumentene ikke kommer inn. Papirene staar beskrivende til slutt.
# REGIMENE, absolutte grenser, maanedssnitt av dagsdata, hel maaned (minst 15
#   handledager, som priser.py kaster en paabegynt maaned):
#     nivaa        ^VIX, hoy fra 20      (grensen regimepanelet fikk 12.11.2026)
#     volvariasjon ^VVIX, hoy fra 105    (samme sted)
#     spredning    standardavviket til daglige logendringer i ^VIX innenfor
#                  maaneden, hoy fra medianen FOER 2015. Den grensen avhenger
#                  bare av X og aldri av utfallet, og den er satt her foer
#                  kjoering. Spredningen er den LANGE stedfortrederen for
#                  volvariasjon: den finnes fra 1990, VVIX bare fra 2007.
#
# HVA SOM KAN AVGJOERES, og hva som ikke kan. Telt 16.11.2026 FOER kjoering,
# paa antall observasjoner og ikke paa utfall:
#   VVIX-aeraen 2007-2026 har 20 episoder i alt. Fordelingen er brukbar over
#   hele aeraen (VVIX hoy 15, VVIX lav 15, begge hoy 14, begge lav 12), men
#   vinduet FOER 2015 har bare 2 episoder med hoy VVIX, 2 med begge hoye og 0
#   med lav VIX og hoy VVIX. Et avgjoerende vindu paa eldre data finnes altsaa
#   ikke for VVIX.
#   DERFOR: alt som bruker VVIX er BESKRIVENDE og avgjoer ingenting. Det
#   rapporteres over hele 2007-2026 med episodetall, slik at en senere oekt ser
#   utvalget. Samme behandling som MOVE fikk 03.11.2026.
#   Det som KAN avgjoeres, paa oppstart til og med 2014-12: nivaa (VIX fra
#   1990, 37 og 41 episoder i alt), spredning (fra 1990, 47 og 42) og
#   kombinasjonen nivaa x spredning (21 og 31 episoder foer 2015).
#
# KRITERIER (satt foer kjoering 16.11.2026, samme krav som
# sonde_kjor_signal_vix_dxy_move 03.11.2026, saa sondene kan leses sammen).
# Et regime betyr noe hvis ALLE disse holder:
#   (a) |forskjellen| er minst 5 prosentpoeng per 12 mnd, altsaa 1,25 ved
#       3 mnd, 2,5 ved 6, 3,75 ved 9, 5 ved 12 og 10 ved 24,
#   (b) p under 0,05 tosidig mot sirkulaert forskjoevet regimeserie (minst
#       24 mnd forskyvning, 2000 trekk),
#   (c) samme fortegn i begge halvdelene av det avgjoerende vinduet,
#   (d) minst 3 episoder (ny etter 12 mnd uten signal) i BEGGE cellene som
#       sammenlignes, og
#   (e) Benjamini-Hochberg paa 10 % over de 15 testene som kan avgjoeres
#       (3 maal x 5 horisonter).
# For kombinasjonen testes BARE kontrasten «begge hoye mot begge lave», valgt
# her foer kjoering. De to diagonalcellene rapporteres, men inngaar ikke i en
# test, for aa unngaa seks sammenligninger der det er plass til en.
#
# Grensene og kriteriene over flyttes ikke etter kjoering. Skriver ingenting
# til dashbordet og ingenting til shadow. Utdata sonder/vvix_regime.csv.
# ---------------------------------------------------------------------------

import json
import time

import numpy as np
import pandas as pd
import requests

rng = np.random.default_rng(20261116)
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
MIN_HIST, MIN_DAGER = 60, 15
HORISONTER = (3, 6, 9, 12, 24)
TIL = pd.Period("2014-12", "M")                      # avgjoerende vindu slutter
NYTT = (pd.Period("2015-01", "M"), pd.Period("2026-12", "M"))
VVIX_FRA = pd.Period("2007-01", "M")
GR_VIX, GR_VVIX = 20.0, 105.0
MIN_EP = 3


def expanding_pct(v):
    out = np.full(len(v), np.nan)
    for i in range(MIN_HIST - 1, len(v)):
        out[i] = (v[: i + 1] <= v[i]).sum() / (i + 1)
    return (1 - out) * 100


def expanding_pct_detrend(v):
    out = np.full(len(v), np.nan)
    for i in range(MIN_HIST - 1, len(v)):
        y = v[: i + 1]; t = np.arange(i + 1)
        b, a = np.polyfit(t, y, 1); r = y - (a + b * t)
        out[i] = (r <= r[i]).sum() / len(r)
    return (1 - out) * 100


def yahoo_dag(sym):
    for f in range(4):
        try:
            r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}",
                             params={"period1": 0, "period2": int(time.time()),
                                     "interval": "1d"}, headers=UA, timeout=60)
            res = r.json()["chart"]["result"][0]
            if (res.get("meta") or {}).get("dataGranularity") != "1d":
                raise ValueError("ikke dagskurser")
            s = pd.Series(res["indicators"]["quote"][0]["close"],
                          index=pd.to_datetime(res["timestamp"], unit="s")).dropna()
            time.sleep(0.3)
            return s[s > 0]
        except Exception:
            if f == 3:
                raise
            time.sleep(2 ** (f + 1))


def mnd_snitt(s):
    g = s.groupby(s.index.to_period("M"))
    return g.mean()[g.size() >= MIN_DAGER].sort_index()


def mnd_spredning(s):
    d = np.log(s).diff().dropna()
    g = d.groupby(d.index.to_period("M"))
    return g.std()[g.size() >= MIN_DAGER].dropna().sort_index()


print("sonde_kjor_vvix_regime")
print("Kriteriene staar i toppen av fila og er satt foer kjoering.\n")

# ------------------------------------------------------------------ signalet
p = pd.read_csv("serier/priser_mnd.csv")
p = p[~p.segment.str.startswith("ship_")]
real = p.pivot(index="t", columns="segment", values="real").astype(float).sort_index()
real.index = pd.PeriodIndex(real.index, freq="M")
lr = np.log(real)
A = pd.DataFrame(np.nan, index=lr.index, columns=lr.columns)
Ad = A.copy()
for c in lr.columns:
    s = lr[c].dropna()
    A.loc[s.index, c] = expanding_pct(s.values)
    Ad.loc[s.index, c] = expanding_pct_detrend(s.values)
SIG = ((A >= 80) & (Ad >= 80)).values
print(f"{lr.shape[1]} raavarer, {lr.index[0]} til {lr.index[-1]}, "
      f"{int(SIG.sum())} signalmaaneder i alt")

# ------------------------------------------------------------------ regimene
vix_d = yahoo_dag("%5EVIX")
vvix_d = yahoo_dag("%5EVVIX")
vix, vvix, spred = mnd_snitt(vix_d), mnd_snitt(vvix_d), mnd_spredning(vix_d)
GR_SPRED = float(spred[spred.index <= TIL].median())
print(f"^VIX  {vix.index[0]} til {vix.index[-1]} ({len(vix)} hele mnd), siste {vix.iloc[-1]:.2f}")
print(f"^VVIX {vvix.index[0]} til {vvix.index[-1]} ({len(vvix)} hele mnd), siste {vvix.iloc[-1]:.2f}")
print(f"spredning {spred.index[0]} til {spred.index[-1]}, siste {spred.iloc[-1]:.4f}")
print(f"grenser: VIX {GR_VIX:.0f}, VVIX {GR_VVIX:.0f}, "
      f"spredning {GR_SPRED:.4f} (median foer {TIL})\n")

H = {"nivaa": (vix >= GR_VIX).reindex(lr.index),
     "volvariasjon": (vvix >= GR_VVIX).reindex(lr.index),
     "spredning": (spred >= GR_SPRED).reindex(lr.index)}
FINNES = {k: v.notna().reindex(lr.index).fillna(False) for k, v in H.items()}
HOY = {k: v.fillna(False).astype(bool) for k, v in H.items()}

MAAL = {
    # navn: (hoy-maske, lav-maske, kan avgjoeres, foerste maaned maalet finnes)
    "nivaa (VIX >= 20)":
        (HOY["nivaa"], ~HOY["nivaa"] & FINNES["nivaa"], True, vix.index[0]),
    "spredning (VIX, >= median)":
        (HOY["spredning"], ~HOY["spredning"] & FINNES["spredning"], True, spred.index[0]),
    "nivaa OG spredning hoye":
        (HOY["nivaa"] & HOY["spredning"],
         ~HOY["nivaa"] & ~HOY["spredning"] & FINNES["nivaa"] & FINNES["spredning"],
         True, max(vix.index[0], spred.index[0])),
    "volvariasjon (VVIX >= 105)":
        (HOY["volvariasjon"], ~HOY["volvariasjon"] & FINNES["volvariasjon"], False, vvix.index[0]),
    "nivaa OG volvariasjon hoye":
        (HOY["nivaa"] & HOY["volvariasjon"],
         ~HOY["nivaa"] & ~HOY["volvariasjon"] & FINNES["nivaa"] & FINNES["volvariasjon"],
         False, max(vix.index[0], vvix.index[0])),
}


def episoder(mask):
    n = 0
    for j in range(mask.shape[1]):
        forr = None
        for i in np.where(mask[:, j])[0]:
            if forr is None or i - forr > 12:
                n += 1
            forr = i
    return n


def analyse(hoy, lav, h, fra, til):
    """Snitt i hoy-regime minus snitt i lav-regime, med p fra sirkulaer
    forskyvning av regimeserien."""
    Y = (lr.shift(-h) - lr).values
    rad = (lr.index >= fra) & (lr.index <= til)
    S, Yp = SIG[rad], Y[rad]
    hv, lv = hoy.values[rad], lav.values[rad]
    if len(Yp) <= 48:
        return None

    def d(hm, lm):
        ok = S & np.isfinite(Yp)
        a, b = ok & hm[:, None], ok & lm[:, None]
        if not a.sum() or not b.sum():
            return np.nan, a, b
        return Yp[a].mean() - Yp[b].mean(), a, b

    diff, a, b = d(hv, lv)
    if not np.isfinite(diff):
        return None
    null = []
    for _ in range(2000):
        k = rng.integers(24, len(hv) - 24)
        null.append(d(np.roll(hv, k), np.roll(lv, k))[0])
    null = np.abs(np.array([x for x in null if np.isfinite(x)]))
    pv = (np.sum(null >= abs(diff)) + 1) / (len(null) + 1)
    midt = len(hv) // 2
    halv = []
    for sl in (np.arange(len(hv)) < midt, np.arange(len(hv)) >= midt):
        halv.append(d(hv & sl, lv & sl)[0])
    return dict(hoy=Yp[a].mean(), lav=Yp[b].mean(), diff=diff, p=pv,
                h1=halv[0], h2=halv[1], n_hoy=int(a.sum()), n_lav=int(b.sum()),
                ep_hoy=episoder(a), ep_lav=episoder(b))


def pp(x):
    return "   -  " if x is None or not np.isfinite(x) else f"{100 * x:+6.1f}"


rader, tester = [], []
for navn, (hoy, lav, kan, start) in MAAL.items():
    print(f"==================== {navn}")
    if kan:
        print(f"   avgjoeres paa {max(start, lr.index[0])} til {TIL}, 2015-2026 vises")
        perioder = {"avgjoer": (max(start, lr.index[0]), TIL), "2015-2026": NYTT}
    else:
        print(f"   BESKRIVENDE, avgjoer ikke: for faa episoder foer 2015 "
              f"(se toppen av fila). Vises over {start} til 2026.")
        perioder = {"hele (beskr.)": (start, NYTT[1]), "2015-2026": NYTT}
    for h in HORISONTER:
        for pn, (fra, til) in perioder.items():
            r = analyse(hoy, lav, h, fra, til)
            if r is None:
                print(f"   h {h:2} {pn:14} for faa signalmaaneder")
                continue
            rader.append({"maal": navn, "h": h, "periode": pn, "fra": str(fra),
                          "kan_avgjoeres": kan, **r})
            print(f"   h {h:2} {pn:14} hoy {pp(r['hoy'])} % (n {r['n_hoy']:3}, ep {r['ep_hoy']:2})"
                  f"  lav {pp(r['lav'])} % (n {r['n_lav']:3}, ep {r['ep_lav']:2})"
                  f"  forskjell {pp(r['diff'])} pp  p {r['p']:.3f}"
                  f"  halvdeler {pp(r['h1'])}/{pp(r['h2'])}")
            if kan and pn == "avgjoer":
                krav_a = abs(r["diff"]) >= 0.05 * h / 12
                krav_c = (np.isfinite(r["h1"]) and np.isfinite(r["h2"])
                          and np.sign(r["h1"]) == np.sign(r["h2"]) == np.sign(r["diff"]))
                krav_d = r["ep_hoy"] >= MIN_EP and r["ep_lav"] >= MIN_EP
                tester.append({"test": f"{navn}, h {h}", "p": r["p"],
                               "ok": bool(krav_a and r["p"] < 0.05 and krav_c and krav_d),
                               "a": krav_a, "c": krav_c, "d": krav_d,
                               "retning": "bedre i hoyt regime" if r["diff"] > 0
                                          else "bedre i lavt regime"})
    print()

# ------------------------------------------------------------------ dommen
print("AVGJOERELSE (bare nivaa, spredning og nivaa x spredning; "
      f"oppstart til {TIL})\n")
if tester:
    T = pd.DataFrame(tester).sort_values("p").reset_index(drop=True)
    m = len(T)
    g = max([i + 1 for i in range(m) if T.p[i] <= 0.10 * (i + 1) / m], default=0)
    T["bh"] = [i < g for i in range(m)]
    for _, t in T.sort_values("test").iterrows():
        dom = "HOLDER, " + t.retning if (t.ok and t.bh) else "holder ikke"
        print(f"   {t.test:34}: {dom}  (a {'ja' if t.a else 'nei'}, "
              f"p {t.p:.3f}, c {'ja' if t.c else 'nei'}, "
              f"d {'ja' if t.d else 'nei'}, BH {'ja' if t.bh else 'nei'})")
    print(f"\n   {int(T.ok.sum())} av {m} klarte krav a til d, "
          f"{int((T.ok & T.bh).sum())} ogsaa BH")
else:
    print("   ingen test kunne gjennomfoeres")
print("\n   volvariasjon (VVIX) og nivaa x volvariasjon kan ikke avgjoeres her:")
print("   vinduet foer 2015 har 2 episoder med hoy VVIX og 0 med lav VIX og hoy")
print("   VVIX. Tallene over for dem er in-sample og kan ikke etablere en regel.")

# ------------------------------------------------------------------ papirene
print("\nPAPIRPORTEFOELJEN (beskrivende): regimet ved inngang og papirenes "
      "avkastning mot MSCI World")
try:
    pos = [q for q in json.load(open("handel.json", encoding="utf-8"))
           ["portefolje"]["posisjoner"] if q["variant"] == "alle"]
    for q in pos:
        t = pd.Period(q["inngang"], "M")
        v = vix.get(t, np.nan)
        w = vvix.get(t, np.nan)
        sp = spred.get(t, np.nan)
        ord_ = lambda x, gr: ("-" if not np.isfinite(x) else ("hoy" if x >= gr else "lav"))
        w_ = q.get("world")
        print(f"   {q['segment']:10} {q['inngang']}  VIX {v:6.2f} ({ord_(v, GR_VIX)})"
              f"  VVIX {w:7.2f} ({ord_(w, GR_VVIX)})"
              f"  spredning {sp:.4f} ({ord_(sp, GR_SPRED)})"
              f"  papirer {q['avk']:+8.1f} %  MSCI World "
              + (f"{w_:+7.1f} %" if w_ is not None else "      -"))
except Exception as e:
    print(f"   kunne ikke lese handel.json ({type(e).__name__}: {str(e)[:60]})")

# ------------------------------------------------------- tillegg, beskrivende
# Lagt til 16.11.2026 ETTER at hovedresultatet var lest, og merket som det.
# Kriteriene i toppen er ikke endret, og dette avgjoer ingenting. Grunnen til
# tillegget: halvdelene i VVIX-radene over er -5 og +90 prosentpoeng ved
# 24 maaneder, altsaa ligger hele forskjellen i den andre halvdelen av
# 2007-2026. Da er det naturlig aa spoerre hva som skjer uten 2020, slik
# prosjektet gjorde i backtestnotatet 29.09.2026 og i holdetidssonden 03.11.
print("\n==================== TILLEGG, beskrivende: uten 2020")
print("   Lagt til etter at hovedresultatet var lest. Avgjoer ingenting.")
print("   Signalmaaneder i kalenderaaret 2020 er tatt ut, alt annet er likt.")
AAR_UT = 2020
ute = np.array([d.year == AAR_UT for d in lr.index])
SIG_U = SIG.copy()
SIG_U[ute, :] = False
_SIG = SIG
for navn, (hoy, lav, kan, start) in MAAL.items():
    if "volvariasjon" not in navn:
        continue
    print(f"\n   {navn}")
    for h in (12, 24):
        globals()["SIG"] = _SIG
        med = analyse(hoy, lav, h, start, NYTT[1])
        globals()["SIG"] = SIG_U
        uten = analyse(hoy, lav, h, start, NYTT[1])
        globals()["SIG"] = _SIG
        if med is None or uten is None:
            print(f"      h {h:2}: for faa signalmaaneder")
            continue
        rader.append({"maal": navn + " (uten 2020)", "h": h, "periode": "hele uten 2020",
                      "fra": str(start), "kan_avgjoeres": False, **uten})
        print(f"      h {h:2}  med 2020: forskjell {pp(med['diff'])} pp "
              f"(ep {med['ep_hoy']}/{med['ep_lav']}, p {med['p']:.3f})"
              f"   uten 2020: forskjell {pp(uten['diff'])} pp "
              f"(ep {uten['ep_hoy']}/{uten['ep_lav']}, p {uten['p']:.3f})")

pd.DataFrame(rader).to_csv("sonder/vvix_regime.csv", index=False)
print("\nLagret sonder/vvix_regime.csv")
