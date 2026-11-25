# ---------------------------------------------------------------------------
# sonde_kjor_laks_salg: salgsregler for laksesignalet
#
# Frodes bestilling 25.11.2026: «Det er tilfeller hvor signal utloeses ved
# allerede hoey A. Kan du vurdere en regel for salg basert paa oekning i
# nominell A i stedet? Test ulike regler.»
#
# ===========================================================================
# KRITERIET FOR DENNE SONDEN, SKREVET FOER UTFALLET ER MAALT
# ===========================================================================
# PREMISSET ER KONTROLLERT FOERST, og det holder. Inngangene (Ad > 80 og
# Ar > 85, Challengerens regel) har raa A paa 91,8, 92,0, 94,8 og 78,4. Alle
# fire starter altsaa hoeyt oppe paa A, og dagens utgang, «raa A tilbake paa
# 50», er derfor et langt fall og ikke en liten korreksjon.
#
# A-banen de foerste tolv maanedene etter hver inngang:
#   2012-01  92 76 80 83 86 99 99 85 84 79 58 32
#   2015-04  92 92 75 76 72 62 50 44 35 31 31 22
#   2020-04  95 80 49 76 70 68 75 79 87 89 79 48
#   2025-04  78 93 84 94 85 42 45 36 24 55 44 51
# 2020 viser svakheten: A faller til 49 i maaned 2, utgangen loeser ut, og saa
# gaar A opp igjen til 76, 87 og 89. Et enkelt stoeyete maanedstall avslutter
# posisjonen midt i episoden. Det samme skjer i 2025 (42 i maaned 5, deretter
# 55, 51 og 69). Det er dette Frode har sett.
#
# SONDEN KAN IKKE VELGE REGEL, og det er avgjort foer maalingen. Fire
# episoder og tretten regler: den beste av dem er stoey. Med tre lukkede
# episoder er beste mulige p 0,125 i en ensidig fortegnstest, og her
# sammenlignes reglene mot hverandre paa de SAMME fire episodene, noe som er
# svakere enn det igjen. Sonden er beskrivende.
#
# Den svarer paa tre spoersmaal, alle beskrivende:
#   1. Hvor foelsom er utfallet for valget av salgsregel?
#   2. Loeser en regel basert paa ENDRING i A fra inngang problemet med at
#      inngangen alt ligger hoeyt?
#   3. Hjelper det aa kreve at utgangskravet holder i to maaneder paa rad,
#      slik regimefeltet gjoer for aa unngaa blafring?
#
# HVA JEG IKKE SKAL GJOERE, SKREVET FOER MAALING: anbefale regelen med
# hoeyeste median. Rapporten skal vise spredningen og hvor mye svaret endrer
# seg naar parameteren flyttes, og ingenting annet. En regel som bare er best
# i ett av de fire tilfellene, eller som faller sammen naar terskelen flyttes
# et hakk, er ikke robust uansett hvor pen medianen er.
#
# Challengeren `challenger_laks_adar_v1` har alt registrert utgangen «raa A
# tilbake paa 50, tak 24 maaneder» og kan ikke endres: en endret regel er en
# NY Challenger fra en ny dato. Denne sonden kan altsaa foere til en ny
# Challenger, aldri til en retting av den som gaar.
# ===========================================================================
#
# VALG SOM ER GJORT FOER MAALING
#   - Inngangene er de fire episodene fra Challengeren: foerste maaned i hver
#     klynge, 12 maaneders pause mellom klynger.
#   - Reglene som maales, alle med tak paa 24 maaneder:
#       F1 nivaa        raa A <= 50 (dagens), <= 60, <= 40
#       F2 fall i A     A har falt 20, 30 eller 40 poeng fra inngangsnivaaet
#       F3 andel        A er under 70 % eller 50 % av inngangsnivaaet
#       F4 prisoppgang  nominell pris opp 20, 30 eller 50 % fra inngang
#       F5 utholdenhet  «A <= 50» og «A falt 30 poeng», men kravet maa holde
#                       to maaneder paa rad; det selges ved slutten av den
#                       andre maaneden
#     F2 og F3 er Frodes forslag om aa bruke endringen i A i stedet for et
#     nivaa. F4 er den samme ideen malt paa prisen i stedet for paa skaaren.
#   - Utfallet er den likt vektede kurven av laksepapirene paa bordet
#     (MOWI.OL, SALM.OL, LSG.OL, BAKKA.OL), total avkastning med utbytte
#     reinvestert, i kroner, fra maanedsslutt i inngangsmaaneden til
#     maanedsslutt i utgangsmaaneden. Meravkastning maales mot MSCI World
#     (IWDA.L) regnet om til kroner.
#   - Et papir er med naar det har kurs i begge maanedene; kurven krever minst
#     to papirer.
#   - Skaarene og prisene leses fra dashbord/data.json, segmentet laks. De er
#     punkt-i-tid, altsaa slik de sto den maaneden.
#   - Ingen nettkall utenom Yahoo. Sonden skriver ingenting til dashbordet,
#     databasen eller Shadow-OOS.
# ---------------------------------------------------------------------------

import json
import os
import time
import warnings

import numpy as np
import pandas as pd
import requests

warnings.filterwarnings("ignore")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
PAPIR = ("MOWI.OL", "SALM.OL", "LSG.OL", "BAKKA.OL")
GRENSE_AD, GRENSE_AR = 80, 85
PAUSE, TAK = 12, 24
ROT = os.path.dirname(os.path.abspath(__file__))


def get(url):
    for i in range(3):
        try:
            r = requests.get(url, headers=UA, timeout=45)
            if r.status_code in (429, 502, 503):
                time.sleep(4 * (i + 1))
                continue
            return r
        except requests.RequestException:
            if i == 2:
                raise
            time.sleep(4 * (i + 1))


def yahoo(sym):
    r = get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}"
            f"?period1=0&period2={int(time.time())}&interval=1mo"
            f"&events=div%7Csplit&includeAdjustedClose=true").json()
    res = r["chart"]["result"][0]
    tz = (res.get("meta") or {}).get("exchangeTimezoneName") or "UTC"
    idx = pd.to_datetime(res["timestamp"], unit="s", utc=True).tz_convert(tz).to_period("M")
    adj = (res["indicators"].get("adjclose") or [{}])[0].get("adjclose")
    if not adj:
        adj = res["indicators"]["quote"][0]["close"]
    s = pd.Series(adj, index=idx).dropna()
    s = s[s > 0]
    return s[~s.index.duplicated(keep="last")], (res.get("meta") or {}).get("currency")


print("=" * 78)
print("sonde_kjor_laks_salg: salgsregler for laksesignalet")
print("BESKRIVENDE. Velger ingen regel. Se kriteriet i toppen av fila.")
print("=" * 78)

with open(os.path.join(ROT, "dashbord", "data.json"), encoding="utf-8") as f:
    serie = json.load(f)["segments"]["laks"]["series"]
R = [{"t": r["t"], "A": r.get("A"), "Ad": r.get("Ad"), "Ar": r.get("Ar"), "nom": r.get("nom")}
     for r in serie]
P = [pd.Period(r["t"], freq="M") for r in R]


def mnd(t):
    y, m = str(t).split("-")
    return int(y) * 12 + int(m)


inn = []
for i, r in enumerate(R):
    if r["Ad"] is None or r["Ar"] is None or not (r["Ad"] > GRENSE_AD and r["Ar"] > GRENSE_AR):
        continue
    if not inn or mnd(r["t"]) - mnd(inn[-1]["sist"]) > PAUSE:
        inn.append({"i": i, "t": r["t"], "sist": r["t"], "A": r["A"], "nom": r["nom"]})
    else:
        inn[-1]["sist"] = r["t"]
print(f"\nEpisoder: {len(inn)}")
for e in inn:
    print(f"   {e['t']}  raa A ved inngang {e['A']:.1f}, nominell pris {e['nom']:.3f}")

# ------------------------------------------------------------------ kursene
print("\nKursene fra Yahoo, maanedsslutt, utbytte reinvestert")
kurs = {}
for tk in PAPIR:
    try:
        s, _ = yahoo(tk)
        kurs[tk] = s
        print(f"   {tk:10} {len(s):4} mnd")
    except Exception as e:
        print(f"   {tk:10} FEILET: {type(e).__name__}")
    time.sleep(0.3)
if len(kurs) < 2:
    raise SystemExit("for faa papirer, sonden stopper")
world, val = yahoo("IWDA.L")
nokx, _ = yahoo("NOK=X")
if val and val.upper() == "USD":
    world = (world * nokx.reindex(world.index)).dropna()
print(f"   IWDA.L     {len(world):4} mnd (MSCI World i kroner)")


def kurv(i0, i1):
    t0, t1 = P[i0], P[i1]
    enk = []
    for s in kurs.values():
        if t0 in s.index and t1 in s.index:
            enk.append(float(s.loc[t1] / s.loc[t0] - 1) * 100)
    if len(enk) < 2:
        return None, None
    k = float(np.mean(enk))
    if t0 not in world.index or t1 not in world.index:
        return k, None
    return k, k - float(world.loc[t1] / world.loc[t0] - 1) * 100


# ----------------------------------------------------------------- reglene
def ut_nivaa(e, grense):
    for j in range(e["i"] + 1, len(R)):
        if mnd(R[j]["t"]) - mnd(e["t"]) > TAK:
            break
        if R[j]["A"] is not None and R[j]["A"] <= grense:
            return j
    return None


def ut_fall(e, poeng):
    maal = e["A"] - poeng
    for j in range(e["i"] + 1, len(R)):
        if mnd(R[j]["t"]) - mnd(e["t"]) > TAK:
            break
        if R[j]["A"] is not None and R[j]["A"] <= maal:
            return j
    return None


def ut_andel(e, andel):
    maal = e["A"] * andel
    for j in range(e["i"] + 1, len(R)):
        if mnd(R[j]["t"]) - mnd(e["t"]) > TAK:
            break
        if R[j]["A"] is not None and R[j]["A"] <= maal:
            return j
    return None


def ut_pris(e, pst):
    maal = e["nom"] * (1 + pst / 100)
    for j in range(e["i"] + 1, len(R)):
        if mnd(R[j]["t"]) - mnd(e["t"]) > TAK:
            break
        if R[j]["nom"] is not None and R[j]["nom"] >= maal:
            return j
    return None


def ut_to_mnd(e, test):
    """Kravet maa holde to maaneder paa rad; selges ved slutten av den andre."""
    forrige = False
    for j in range(e["i"] + 1, len(R)):
        if mnd(R[j]["t"]) - mnd(e["t"]) > TAK:
            break
        na = test(R[j], e)
        if na and forrige:
            return j
        forrige = na
    return None


REGLER = [
    ("F1 A <= 50 (dagens)", lambda e: ut_nivaa(e, 50)),
    ("F1 A <= 60", lambda e: ut_nivaa(e, 60)),
    ("F1 A <= 40", lambda e: ut_nivaa(e, 40)),
    ("F2 A falt 20 poeng", lambda e: ut_fall(e, 20)),
    ("F2 A falt 30 poeng", lambda e: ut_fall(e, 30)),
    ("F2 A falt 40 poeng", lambda e: ut_fall(e, 40)),
    ("F3 A under 70 % av inng.", lambda e: ut_andel(e, 0.70)),
    ("F3 A under 50 % av inng.", lambda e: ut_andel(e, 0.50)),
    ("F4 pris opp 20 %", lambda e: ut_pris(e, 20)),
    ("F4 pris opp 30 %", lambda e: ut_pris(e, 30)),
    ("F4 pris opp 50 %", lambda e: ut_pris(e, 50)),
    ("F5 A <= 50 i to mnd", lambda e: ut_to_mnd(e, lambda r, e: r["A"] is not None and r["A"] <= 50)),
    ("F5 A falt 30 i to mnd", lambda e: ut_to_mnd(e, lambda r, e: r["A"] is not None and r["A"] <= e["A"] - 30)),
]

print("\n" + "=" * 78)
print("HVER REGEL, EPISODE FOR EPISODE")
print("holdetid i maaneder, kurvens avkastning i prosent, meravkastning mot world i pp")
print("Naar regelen ikke slaar til innen 24 maaneder, selges det ved taket.")
print("=" * 78)
tab = []
for navn, fn in REGLER:
    rad = {"regel": navn, "episoder": []}
    print(f"\n{navn}")
    for e in inn:
        j = fn(e)
        tak = j is None
        if tak:
            j = next((k for k in range(e["i"] + 1, len(R)) if mnd(R[k]["t"]) - mnd(e["t"]) == TAK), None)
        if j is None:
            print(f"   {e['t']}: ikke modnet enda")
            rad["episoder"].append({"t": e["t"], "h": None})
            continue
        h = mnd(R[j]["t"]) - mnd(e["t"])
        k, mer = kurv(e["i"], j)
        if k is None:
            print(f"   {e['t']}: kurs mangler")
            rad["episoder"].append({"t": e["t"], "h": h})
            continue
        print(f"   {e['t']} -> {R[j]['t']}  {h:2} mnd   kurv {k:+7.1f} %"
              f"   mot world {('%+7.1f' % mer) if mer is not None else '    ---'} pp"
              f"{'   (taket)' if tak else ''}")
        rad["episoder"].append({"t": e["t"], "ut": R[j]["t"], "h": h, "kurv": round(k, 1),
                                "mer": None if mer is None else round(mer, 1), "tak": tak})
    ok = [x for x in rad["episoder"] if x.get("mer") is not None]
    if ok:
        rad["n"] = len(ok)
        rad["median_h"] = float(np.median([x["h"] for x in ok]))
        rad["median_mer"] = round(float(np.median([x["mer"] for x in ok])), 1)
        rad["min_mer"] = min(x["mer"] for x in ok)
        rad["positive"] = sum(1 for x in ok if x["mer"] > 0)
    tab.append(rad)

print("\n" + "=" * 78)
print("OPPSUMMERING, sortert slik reglene er skrevet og IKKE etter resultat")
print("=" * 78)
print(f"{'regel':26} {'n':>2} {'median h':>9} {'median mer':>11} {'svakeste':>9} {'positive':>9}")
for r in tab:
    if "median_mer" not in r:
        print(f"{r['regel']:26} ingen ferdige")
        continue
    print(f"{r['regel']:26} {r['n']:2} {r['median_h']:8.0f}m {r['median_mer']:+10.1f} "
          f"{r['min_mer']:+9.1f} {r['positive']:4} av {r['n']}")

print("\n" + "=" * 78)
print("FOELSOMHET: hvor mye flytter svaret seg naar parameteren flyttes ett hakk")
print("=" * 78)
for fam, navn in (("F1", "nivaa"), ("F2", "fall i poeng"), ("F3", "andel"), ("F4", "prisoppgang")):
    rr = [r for r in tab if r["regel"].startswith(fam) and "median_mer" in r]
    if len(rr) < 2:
        continue
    v = [r["median_mer"] for r in rr]
    print(f"   {fam} ({navn}): median mer gaar fra {min(v):+.1f} til {max(v):+.1f} pp "
          f"over {len(rr)} terskler, spenn {max(v) - min(v):.1f} pp")

print("\nMINNER OM, fra kriteriet i toppen: fire episoder og tretten regler.")
print("Den hoeyeste medianen her er ikke et funn, og sonden anbefaler ingen regel.")
print("Challengeren som gaar har utgangen A <= 50 registrert og kan ikke endres;")
print("en annen utgang maatte bli en NY Challenger fra en ny dato.")

with open(os.path.join(ROT, "sonder", "laks_salg.json"), "w", encoding="utf-8") as f:
    json.dump({"episoder": [{"t": e["t"], "A": e["A"], "nom": e["nom"]} for e in inn],
               "regler": tab,
               "merknad": ("Beskrivende. Fire episoder og tretten regler, saa den beste er "
                           "stoey. Velger ingen regel. Se toppen av sonde_kjor_laks_salg.py.")},
              f, ensure_ascii=False, indent=1)
print("\nLagret sonder/laks_salg.json")
