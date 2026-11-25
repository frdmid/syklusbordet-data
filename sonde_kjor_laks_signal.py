# ---------------------------------------------------------------------------
# sonde_kjor_laks_signal: Frodes forslag til bunnsignal for laks
#
#   Ad > 80 OG Ar > 85
#
# altsaa detrendet prisnivaaskaar over 80 og rullende (siste ti aar) over 85,
# paa den sesongjusterte lakseprisen, med punkt-i-tid-skaarer slik de staar paa
# bordet. Frodes bestilling 25.11.2026: «Jeg vil ha et signal for laks ogsaa. A
# detrendet over 80 og rullende A over 85 ser lovende ut som kriterie.»
#
# ===========================================================================
# KRITERIET FOR DENNE SONDEN, SKREVET FOER UTFALLET ER MAALT
# ===========================================================================
# Dette er TELLINGEN, som er gjort foerst og som er kjent naar kriteriet
# skrives (den krever ingen avkastningsdata):
#   - serien paa bordet har 180 maaneder, 2011-11 til 2026-10
#   - 17 maaneder oppfyller Ad > 80 og Ar > 85
#   - de ligger i 4 klynger med 12 maaneders pause mellom:
#       2012-01 til 2012-07, 2015-04 til 2015-05, 2020-04 til 2021-01,
#       2025-04 til 2026-07
#   - bare 3 av klyngene har kjent utfall 24 maaneder fram. Den siste er
#     aapen.
#
# DERMED, OG DETTE ER AVGJORT FOER MAALINGEN: sonden KAN IKKE etablere
# regelen. Med tre klynger gir en ensidig fortegnstest best mulig p = 0,125
# (1/8), og prosjektet har brukt 0,05 og i noen tilfeller 0,10. Selv tre av
# tre positive klynger ville altsaa ikke vaere nok. Bunnsonen paa bordet ble
# godkjent paa 7 av 7 klynger med p = 0,014; dette er et annet kaliber.
#
# Sonden er derfor BESKRIVENDE. Den avgjoer ingenting, og utfallet skal ikke
# brukes til aa sette regelen i drift. Den svarer paa ett spoersmaal: hva
# gjorde laksepapirene etter de klyngene som finnes, og er det i det hele tatt
# verdt aa foelge videre?
#
# HOLDETIDEN. Frode la til foer maaling: «Holdetid paa 24 mnd er for lenge for
# laks. Syklusene er kortere. Undersoek optimal holdetid eller regel for salg
# ogsaa.» Det er rimelig: bordets 24 maaneder ble testet paa raavaresykluser
# der tilbudssiden bruker aar paa aa svare, mens lakseprisen svinger med
# biomasse i sjoeen og sesong og vender raskere.
#
# Men «optimal holdetid» kan ikke MAALES her, og det er avgjort foer
# maalingen: med tre klynger og seks horisonter vil den beste horisonten
# vaere stoeyen og ikke et funn. Sonden rapporterer derfor HELE kurven, 3, 6,
# 9, 12, 18 og 24 maaneder, og velger ingen. Den som senere settes i drift,
# skal velges av Frode paa forhaand og fryses i Shadow-OOS, ikke plukkes som
# den hoeyeste soeylen her.
#
# Tre salgsregler maales ved siden av de faste holdetidene, alle valgt foer
# maaling og alle med tak paa 24 maaneder:
#   R1  fast holdetid, en per horisont (grunnlinjen)
#   R2  selg naar signalet slukkes, altsaa foerste maaned der Ad <= 80 eller
#       Ar <= 85. Den bruker samme maskineri som inngangen og trenger ingen
#       ny parameter.
#   R3  selg naar prisen er tilbake paa sin egen median, altsaa foerste
#       maaned der raa A <= 50. Den sier «billig er over», og er uavhengig av
#       hvor lenge det tar.
# Flere regler enn disse tre skal ikke legges til etter at tallene er sett.
#
# Terskelen for aa gaa videre, satt naa: minst 2 av 3 klynger positive mot
# verdensindeksen paa BAADE 6 og 12 maaneder, OG medianen over de 17
# signalmaanedene hoeyere enn medianen over de oevrige maanedene paa baade 6
# og 12. To horisonter og ikke en, slik at kravet ikke kan oppfylles av en
# enkelt heldig lengde, og de to er valgt fordi Frode mener syklusen er
# kortere enn to aar. Blir kravet oppfylt, er forslaget verdt aa foelge som
# CHALLENGER i Shadow-OOS, med startdato og uten tilbakevirkende kraft, slik
# prosjektet gjoer med nye regler etter at Championen ble fryst 07.10.2026.
# Blir det ikke oppfylt, er forslaget lagt bort. Ingen av utfallene gir et
# flagg paa bordet naa.
#
# Hva som IKKE skal gjoeres, uansett utfall: justere 80 og 85 til noe som
# treffer bedre. Tallene er Frodes, satt paa forhaand, og en justering etter
# aa ha sett utfallet ville vaere aa velge regel paa de samme tre episodene.
# ===========================================================================
#
# VALG SOM ER GJORT FOER MAALING
#   - Utfallet er den likt vektede kurven av laksepapirene paa bordet
#     (MOWI.OL, SALM.OL, LSG.OL, BAKKA.OL), total avkastning med utbytte
#     reinvestert (justert sluttkurs fra Yahoo), i kroner. Et papir er med
#     naar det har kurs i baade start- og sluttmaaneden; kurven krever minst
#     to papirer.
#   - Meravkastning maales mot MSCI World (IWDA.L) regnet om til kroner, samme
#     indeks som papirporteføljen paa bordet bruker. OSEBX (OSEBX.OL) staar
#     ved siden av som nummer to, fordi tre av fire papirer er notert i Oslo.
#   - Horisonter: 3, 6, 9, 12, 18 og 24 maaneder, maalt fra maanedsslutt i
#     signalmaaneden. Skaarene for en maaned er kjent ved maanedsslutt.
#   - Salgsreglene R2 og R3 selger ved maanedsslutt i den maaneden kravet
#     brytes, altsaa med samme forsinkelse som inngangen har. Slaar regelen
#     aldri til, selges det etter 24 maaneder (taket).
#   - Klyngen regnes fra sin FOERSTE maaned, fordi det er da en kjoeper ville
#     handlet. Alle 17 signalmaanedene rapporteres ogsaa for seg, men de
#     overlapper og teller ikke som uavhengige.
#   - Sammenligningsgrunnlaget er alle maaneder i samme serie som IKKE er
#     signalmaaneder og som har kjent utfall paa horisonten.
#   - Skaarene leses fra dashbord/data.json, segmentet laks, feltene Ad og Ar
#     i serien. De er regnet punkt-i-tid med ekspanderende vindu, altsaa slik
#     de sto den maaneden. Ingen ny beregning her.
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

# Yahoo-tidsstemplene er tidssonebevisste, og to_period dropper sonen. Det er
# riktig her (vi vil ha maaneden paa boersen), men pandas advarer om det en
# gang per kall og fyller rapporten. Samme filter som i sonde_kjor_laks.
warnings.filterwarnings("ignore")

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
PAPIR = ("MOWI.OL", "SALM.OL", "LSG.OL", "BAKKA.OL")
VERDEN = "IWDA.L"
OSEBX = "OSEBX.OL"
GRENSE_AD, GRENSE_AR = 80, 85
PAUSE = 12                      # maaneder mellom klynger
HOR = (3, 6, 9, 12, 18, 24)
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
    """Maanedsslutt, utbyttejustert."""
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


def mnd(t):
    y, m = str(t).split("-")[:2]
    return int(y) * 12 + int(m)


print("=" * 75)
print("sonde_kjor_laks_signal: Ad > 80 og Ar > 85 paa laks")
print("BESKRIVENDE. Avgjoer ingenting. Se kriteriet i toppen av fila.")
print("=" * 75)

# ------------------------------------------------------- signalet fra bordet
with open(os.path.join(ROT, "dashbord", "data.json"), encoding="utf-8") as f:
    serie = json.load(f)["segments"]["laks"]["series"]

S = pd.DataFrame([{"t": r["t"], "Ad": r.get("Ad"), "Ar": r.get("Ar"), "A": r.get("A")}
                  for r in serie])
S["t"] = pd.PeriodIndex(S["t"], freq="M")
S = S.set_index("t").sort_index()
sig = S[(S.Ad > GRENSE_AD) & (S.Ar > GRENSE_AR)].index
print(f"\nSerien: {len(S)} maaneder, {S.index[0]} til {S.index[-1]}")
print(f"Signalmaaneder (Ad > {GRENSE_AD} og Ar > {GRENSE_AR}): {len(sig)}")

klynger = []
for t in sig:
    if not klynger or mnd(t) - mnd(klynger[-1][-1]) > PAUSE:
        klynger.append([t])
    else:
        klynger[-1].append(t)
print(f"Klynger med {PAUSE} maaneders pause: {len(klynger)}")
for k in klynger:
    print(f"   {k[0]} til {k[-1]}  ({len(k)} maaneder)")

# ------------------------------------------------------------------ kursene
print("\nKursene fra Yahoo, maanedsslutt, utbytte reinvestert")
kurs = {}
for tk in PAPIR:
    try:
        s, val = yahoo(tk)
        kurs[tk] = s
        print(f"   {tk:10} {len(s):4} mnd, {s.index[0]} til {s.index[-1]}, {val}")
    except Exception as e:
        print(f"   {tk:10} FEILET: {type(e).__name__} {str(e)[:60]}")
    time.sleep(0.3)
if len(kurs) < 2:
    raise SystemExit("for faa papirer, sonden stopper")

ref = {}
for tk, navn in ((VERDEN, "MSCI World"), (OSEBX, "OSEBX")):
    try:
        s, val = yahoo(tk)
        ref[navn] = (s, val)
        print(f"   {tk:10} {len(s):4} mnd, {s.index[0]} til {s.index[-1]}, {val} ({navn})")
    except Exception as e:
        print(f"   {tk:10} FEILET: {type(e).__name__}")
    time.sleep(0.3)

# MSCI World er i USD paa London; regnes om til kroner med Yahoo NOK=X.
try:
    nokx, _ = yahoo("NOK=X")
    print(f"   NOK=X      {len(nokx):4} mnd, kroner per dollar")
except Exception as e:
    nokx = None
    print(f"   NOK=X      FEILET: {type(e).__name__}")

if "MSCI World" in ref:
    s, val = ref["MSCI World"]
    if val and val.upper() == "USD" and nokx is not None:
        ref["MSCI World"] = (s * nokx.reindex(s.index), "NOK")
        print("   MSCI World regnet om til kroner")


def avk(s, t0, h):
    """Avkastning i prosent fra maanedsslutt t0 til t0 + h maaneder."""
    t1 = t0 + h
    if t0 not in s.index or t1 not in s.index:
        return None
    return float(s.loc[t1] / s.loc[t0] - 1) * 100


def kurv(t0, h):
    """Likt vektet kurv av papirene som har kurs i begge maanedene."""
    enk = [avk(s, t0, h) for s in kurs.values()]
    enk = [x for x in enk if x is not None]
    if len(enk) < 2:
        return None, 0
    return float(np.mean(enk)), len(enk)


def mer(t0, h, navn):
    k, n = kurv(t0, h)
    if k is None or navn not in ref:
        return None, n
    r = avk(ref[navn][0], t0, h)
    return (None if r is None else k - r), n


# ------------------------------------------------------------- klyngene
print("\n" + "=" * 75)
print("KLYNGENE, maalt fra foerste maaned (det er da en kjoeper ville handlet)")
print("Meravkastning i prosentpoeng mot indeksen, total avkastning i kroner")
print("=" * 75)
rader = []
for k in klynger:
    t0 = k[0]
    print(f"\n{t0} (klyngen varte {len(k)} maaneder, til {k[-1]})")
    for h in HOR:
        kv, n = kurv(t0, h)
        mw, _ = mer(t0, h, "MSCI World")
        ob, _ = mer(t0, h, "OSEBX")
        if kv is None:
            print(f"   {h:2} mnd: utfallet er ikke kjent enda")
            continue
        print(f"   {h:2} mnd: kurv {kv:+7.1f} %   mot world {('%+7.1f' % mw) if mw is not None else '    ---'} pp"
              f"   mot osebx {('%+7.1f' % ob) if ob is not None else '    ---'} pp   ({n} papirer)")
        rader.append({"klynge": str(t0), "h": h, "kurv_pst": round(kv, 1),
                      "mot_world_pp": None if mw is None else round(mw, 1),
                      "mot_osebx_pp": None if ob is None else round(ob, 1),
                      "papirer": n})

# ----------------------------------------------------------- salgsreglene
print("\n" + "=" * 75)
print("SALGSREGLENE, maalt fra foerste maaned i hver klynge")
print("R2 selger naar signalet slukkes (Ad <= 80 eller Ar <= 85), tak 24 mnd")
print("R3 selger naar raa A <= 50 (prisen tilbake paa egen median), tak 24 mnd")
print("=" * 75)


def naar_slukkes(t0):
    """Foerste maaned etter t0 der signalet ikke lenger staar. Tak 24."""
    for h in range(1, 25):
        t = t0 + h
        if t not in S.index:
            return None
        r = S.loc[t]
        if not (r.Ad > GRENSE_AD and r.Ar > GRENSE_AR):
            return h
    return 24


def naar_median(t0):
    """Foerste maaned etter t0 der raa A er 50 eller lavere. Tak 24."""
    for h in range(1, 25):
        t = t0 + h
        if t not in S.index:
            return None
        if S.loc[t].A is not None and S.loc[t].A <= 50:
            return h
    return 24


salg = []
for k in klynger:
    t0 = k[0]
    print(f"\n{t0}")
    for navn, fn in (("R2 signalet slukkes", naar_slukkes), ("R3 raa A tilbake til 50", naar_median)):
        h = fn(t0)
        if h is None:
            print(f"   {navn:24}: holdetiden er ikke ferdig enda")
            continue
        kv, n = kurv(t0, h)
        mw, _ = mer(t0, h, "MSCI World")
        if kv is None:
            print(f"   {navn:24}: {h:2} mnd, utfallet er ikke kjent enda")
            continue
        print(f"   {navn:24}: {h:2} mnd   kurv {kv:+7.1f} %"
              f"   mot world {('%+7.1f' % mw) if mw is not None else '    ---'} pp")
        salg.append({"klynge": str(t0), "regel": navn, "holdetid_mnd": h,
                     "kurv_pst": round(kv, 1),
                     "mot_world_pp": None if mw is None else round(mw, 1)})

print("\nMedian over klyngene med kjent utfall")
for navn in ("R2 signalet slukkes", "R3 raa A tilbake til 50"):
    rr = [r for r in salg if r["regel"] == navn and r["mot_world_pp"] is not None]
    if not rr:
        print(f"   {navn:24}: ingen ferdige")
        continue
    print(f"   {navn:24}: {len(rr)} klynger, median holdetid "
          f"{int(np.median([r['holdetid_mnd'] for r in rr]))} mnd, "
          f"median mot world {np.median([r['mot_world_pp'] for r in rr]):+.1f} pp")
for h in HOR:
    rr = [r for r in rader if r["h"] == h and r["mot_world_pp"] is not None]
    if rr:
        print(f"   R1 fast {h:2} mnd{'':12}: {len(rr)} klynger, "
              f"median mot world {np.median([r['mot_world_pp'] for r in rr]):+.1f} pp")

# ------------------------------------------------- signalmaaneder mot resten
print("\n" + "=" * 75)
print("ALLE SIGNALMAANEDER MOT ALLE ANDRE MAANEDER (overlappende, ikke uavhengige)")
print("=" * 75)
sammen = []
for h in HOR:
    s_mer = [mer(t, h, "MSCI World")[0] for t in sig]
    s_mer = [x for x in s_mer if x is not None]
    a_mer = [mer(t, h, "MSCI World")[0] for t in S.index if t not in sig]
    a_mer = [x for x in a_mer if x is not None]
    if not s_mer or not a_mer:
        print(f"   {h:2} mnd: for lite data")
        continue
    print(f"   {h:2} mnd: signal median {np.median(s_mer):+7.1f} pp (n {len(s_mer):3})"
          f"   andre median {np.median(a_mer):+7.1f} pp (n {len(a_mer):3})"
          f"   forskjell {np.median(s_mer) - np.median(a_mer):+7.1f} pp")
    sammen.append({"h": h, "signal_median_pp": round(float(np.median(s_mer)), 1),
                   "andre_median_pp": round(float(np.median(a_mer)), 1),
                   "n_signal": len(s_mer), "n_andre": len(a_mer)})

# ------------------------------------------------------------- terskelen
print("\n" + "=" * 75)
print("TERSKELEN SOM BLE SATT FOER MAALINGEN")
print("=" * 75)
krav1 = krav2 = True
for h in (6, 12):
    lukket = [r for r in rader if r["h"] == h and r["mot_world_pp"] is not None]
    pos = [r for r in lukket if r["mot_world_pp"] > 0]
    dh = [r for r in sammen if r["h"] == h]
    ok1 = len(lukket) >= 3 and len(pos) >= 2
    ok2 = bool(dh) and dh[0]["signal_median_pp"] > dh[0]["andre_median_pp"]
    krav1 = krav1 and ok1
    krav2 = krav2 and ok2
    print(f"   {h:2} mnd: {len(pos)} av {len(lukket)} klynger positive mot world"
          f"   ({'OPPFYLT' if ok1 else 'IKKE oppfylt'})")
    if dh:
        print(f"          signalmedian {dh[0]['signal_median_pp']:+.1f} pp mot "
              f"{dh[0]['andre_median_pp']:+.1f} pp for de andre"
              f"   ({'OPPFYLT' if ok2 else 'IKKE oppfylt'})")
print(f"   krav 1, minst 2 av 3 positive paa baade 6 og 12 mnd : "
      f"{'OPPFYLT' if krav1 else 'IKKE oppfylt'}")
print(f"   krav 2, signalmedian over de andre paa baade 6 og 12: "
      f"{'OPPFYLT' if krav2 else 'IKKE oppfylt'}")
print()
if krav1 and krav2:
    print("   BEGGE OPPFYLT. Forslaget er verdt aa foelge som Challenger i")
    print("   Shadow-OOS, med startdato og uten tilbakevirkende kraft.")
    print("   Det er ikke et bevis: med tre klynger er beste mulige p 0,125.")
else:
    print("   IKKE OPPFYLT. Forslaget legges bort. Terskelene skal ikke")
    print("   justeres for aa treffe bedre; det ville vaere aa velge regel")
    print("   paa de samme tre episodene.")

os.makedirs(os.path.join(ROT, "sonder"), exist_ok=True)
with open(os.path.join(ROT, "sonder", "laks_signal.json"), "w", encoding="utf-8") as f:
    json.dump({"regel": {"Ad": GRENSE_AD, "Ar": GRENSE_AR, "pause_mnd": PAUSE},
               "signalmaaneder": [str(t) for t in sig],
               "klynger": [[str(x) for x in k] for k in klynger],
               "klyngeutfall": rader, "signal_mot_andre": sammen,
               "salgsregler": salg,
               "krav1_2av3": krav1, "krav2_median": krav2,
               "merknad": ("Beskrivende sonde. Tre klynger med kjent utfall gir best "
                           "mulig p 0,125 i en ensidig fortegnstest, saa regelen kan "
                           "ikke etableres her, og den beste av seks horisonter er "
                           "stoey og ikke et funn. Se toppen av "
                           "sonde_kjor_laks_signal.py.")},
              f, ensure_ascii=False, indent=1)
print("\nLagret sonder/laks_signal.json")
