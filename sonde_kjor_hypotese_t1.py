# ---------------------------------------------------------------------------
# sonde_kjor_hypotese_t1: hypotesen "kjoep en maaned etter bunnsonen, selg tre
# maaneder etter kjoepet" testet paa data den ikke ble funnet i
#
# Frodes bestilling 29.09.2026, etter den uavhengige vurderingen samme dag
# (notater/2026-09-29_vurdering.md). Hypotesen i flagglogg.py ble funnet i
# kontrollraden "inngang en maaned senere (T+1)" i sonde_kjor_backtest, altsaa
# paa tavlens papirer. Ken French sine bransjeportefoljer foer 2011-09 og
# landportefoljene ble ikke brukt til aa finne den. Der kan den testes naa, i
# stedet for aa vente aar paa flaggloggen.
#
# REGELEN SOM TESTES (samme som i flagglogg.py, oversatt til maanedsdata)
#   Innslag t: foerste maaned i bunnsone (raa og detrendet A >= 80) etter mer
#   enn tolv maaneder uten, fra bordets egen kode (raavare_hist, terskel_motor).
#   Kjoep ved slutten av maaned t+1, selg ved slutten av maaned t+4.
#   Utfall: log avkastning i vinduet minus det amerikanske aksjemarkedet
#   (Mkt-RF + RF) i samme vindu. Markedet staar for ACWI, som ikke finnes foer
#   2008. Mot eget snitt (alle tremaanedersvinduer) vises ved siden av.
#
# DATA
#   Bransjer: samme kart som sonde_kjor_backtest_lang (Oil, Gold, Mines, Steel,
#   Coal), verdivektet, i dollar, uten overlevelsesskjevhet. En bransje telles
#   en gang per maaned selv om to raavarer flagger den (Brent og WTI).
#   Land: Norge og Australia fra F-F_International_Countries, med fondsregelen
#   fra sonder/fondkart_forslag.json (som sonde_kjor_land) og, ved siden av,
#   "en av landets raavarer i bunnsone".
#   Episoder: innslag med hoeyst seks maaneder mellom. S = snittet over
#   episodene av episodens median. p: andelen av 2000 trekk der hver episode
#   flyttes til en tilfeldig kalendermaaned (samme bransjer, samme vindu) og S
#   ble minst like hoey. Enveis.
#
# BESLUTNINGSREGEL, SATT FOER KJOERING (skal ikke endres etter)
#   Hovedtest: bransjene, innslag foer 2011-09, mot markedet.
#     STOETTET      hvis andelen positive episoder er minst 80 % (samme krav
#                   som i flaggloggen) og S > 0.
#     SVAK STOETTE  hvis ikke stoettet, men S > 0, flere enn halvparten av
#                   episodene positive og p <= 0,10.
#     IKKE STOETTET ellers.
#   Kontroll (avgjoer ikke): det samme uten episoder som ligger innenfor seks
#   maaneder fra et innslag i papirtesten (sonder/backtest.json), saa ingen
#   episode overlapper i tid med dataene hypotesen ble funnet i.
#   Land: bare beskrivende. For faa innslag foer 2011 til aa avgjoere noe.
#   Ved siden av, beskrivende: samme vindu med kjoep ved flagget (T0 til T+3),
#   for aa se om ventemaaneden betyr noe, og innslag fra 2011-09.
#
#   Konsekvens, ogsaa satt foer kjoering: IKKE STOETTET betyr at hypotesen
#   ikke har stoette utenfor dataene den ble funnet i, og den boer bare logges,
#   ikke brukes til kjoep. Sonden endrer ingenting paa bordet eller i loggen.
#
# FORBEHOLD
#   Bransjetabellene for T0 (1 til 24 mnd) ble sett 28.09, saa dataene er ikke
#   helt urort, men T+1 til T+4 ble aldri regnet paa dem. Bransjene er
#   amerikanske og brede. Utfallet er tre maaneder, saa hvert tall er stoeyete.
# ---------------------------------------------------------------------------

import io, json, os, re, time, warnings, zipfile
import numpy as np
import pandas as pd
import requests
import terskel_motor as M

warnings.filterwarnings("ignore")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
KLYNGEGAP, PAUSE, TREKK = 6, M.PAUSE, 2000
SPLITT = pd.Period("2011-09", "M")
rng = np.random.default_rng(20260929)
FRENCH = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
BRANSJE = {"brent": ["Oil"], "wti": ["Oil"], "henryhub": ["Oil"], "ttf": ["Oil"], "gold": ["Gold"],
           "kobber": ["Mines"], "nikkel": ["Mines"], "aluminium": ["Steel"], "sink": ["Mines"],
           "bly": ["Mines"], "tinn": ["Mines"], "jernmalm": ["Mines", "Steel"], "kull": ["Coal"],
           "uran": ["Mines"]}
LAND = {"norge": "Norway", "australia": "Austrlia"}   # filnavnene hos French
VARIANTER = {"T+1 til T+4 (hypotesen)": (1, 4), "T0 til T+3 (kjoep ved flagget)": (0, 3)}
HOVED = "T+1 til T+4 (hypotesen)"


def get(url, timeout=90):
    for i in range(3):
        try:
            r = requests.get(url, headers=UA, timeout=timeout)
            if r.status_code in (429, 502, 503):
                time.sleep(3 * (i + 1)); continue
            r.raise_for_status()
            return r
        except requests.RequestException:
            if i == 2:
                raise
            time.sleep(2 * (i + 1))
    raise RuntimeError(url)


def zip_linjer(fil, navn=None):
    z = zipfile.ZipFile(io.BytesIO(get(FRENCH + fil).content))
    if navn is None:
        return z.read(z.namelist()[0]).decode("latin1").splitlines()
    treff = [x for x in z.namelist() if navn.lower() in x.lower()]
    return z.read(treff[0]).decode("latin1").splitlines() if treff else None


def csv_blokk(linjer, blokk=None):
    """Som french() i sonde_kjor_backtest_lang: foerste maanedsblokk etter
    teksten blokk. Prosent, -99.99 som manglende."""
    i = next(j for j, l in enumerate(linjer) if blokk in l) if blokk else 0
    while not (linjer[i].strip().startswith(",") and len(linjer[i].split(",")) > 1):
        i += 1
    kol = [c.strip() for c in linjer[i].split(",")[1:]]
    rader = {}
    for l in linjer[i + 1:]:
        f = [x.strip() for x in l.split(",")]
        if not f[0].isdigit() or len(f[0]) != 6:
            break
        try:
            rader[pd.Period(f"{f[0][:4]}-{f[0][4:]}", "M")] = [float(x) for x in f[1:len(kol) + 1]]
        except ValueError:
            continue
    d = pd.DataFrame.from_dict(rader, orient="index", columns=kol).sort_index()
    return d.where(d > -99.0)


def land_mkt(linjer):
    """Markedskolonnen (Mkt) i en landfil, verdivektet i dollar. Som les_land i
    sonde_kjor_land: foerste blokk, stopper naar datoene begynner paa nytt."""
    rader = {}
    for l in linjer:
        f = [x for x in re.split(r"[,\s]+", l.strip()) if x]
        if f and re.fullmatch(r"\d{6}", f[0]):
            p = pd.Period(f"{f[0][:4]}-{f[0][4:]}", "M")
            if rader and p <= max(rader):
                break
            try:
                rader[p] = float(f[1])
            except (ValueError, IndexError):
                continue
    s = pd.Series(rader).sort_index()
    return s.where(s > -99.0)


niva = lambda r_pst: np.log1p(r_pst.dropna() / 100.0).cumsum()

# ===================================================================== data
print("0. Raavarene fra bordets egen kode\n")
from raavare_hist import hent
REAL, _NOM, cpi = hent()
BUNN, SONE = {}, {}
for sid, lr in REAL.items():
    if sid == "laks":
        continue
    lr = lr.dropna()
    full = pd.period_range(lr.index[0], lr.index[-1], freq="M")
    lr = lr.reindex(full).interpolate()
    s = M.Segment(sid, lr.values, np.array([p.ordinal for p in lr.index]))
    ok = np.isfinite(s.A) & np.isfinite(s.Ad)
    BUNN[sid] = pd.Series(ok & (s.A >= 80) & (s.Ad >= 80), index=lr.index)
    SONE[sid] = pd.Series(ok & (s.A >= 80), index=lr.index)


def innslag(fl):
    ut, siste = [], None
    for t in fl.index[fl.values]:
        if siste is None or t.ordinal - siste.ordinal > PAUSE:
            ut.append(t)
        siste = t
    return ut


INNSLAG = {sid: innslag(b) for sid, b in BUNN.items()}
print("\n   Innslag i bunnsone:")
for sid in sorted(INNSLAG):
    if INNSLAG[sid]:
        print(f"      {sid:10} {len(INNSLAG[sid]):2d}  " + " ".join(str(t) for t in INNSLAG[sid]))

print("\n1. Ken French\n")
IND = csv_blokk(zip_linjer("49_Industry_Portfolios_CSV.zip"), "Value Weighted Returns -- Monthly")
FAK = csv_blokk(zip_linjer("F-F_Research_Data_Factors_CSV.zip"))
MARKED = niva(FAK["Mkt-RF"] + FAK["RF"])
KURS = {}
for b in sorted({x for v in BRANSJE.values() for x in v}):
    KURS[f"ff:{b}"] = niva(IND[b])
    print(f"   {b:6} fra {KURS['ff:' + b].index[0]} til {KURS['ff:' + b].index[-1]}")
print(f"   marked fra {MARKED.index[0]} til {MARKED.index[-1]}")
for fid, fil in LAND.items():
    linjer = zip_linjer("F-F_International_Countries.zip", fil)
    if linjer is None:
        print(f"   {fid}: ingen fil"); continue
    KURS[f"land:{fid}"] = niva(land_mkt(linjer))
    print(f"   {fid:9} fra {KURS['land:' + fid].index[0]} til {KURS['land:' + fid].index[-1]}")


# ================================================================ regnestykket
def vindu(lk, a, b):
    """log avkastning fra slutten av t+a til slutten av t+b, per t."""
    ut = {}
    for t in lk.index:
        if t + a in lk.index and t + b in lk.index:
            ut[t] = lk[t + b] - lk[t + a]
    return pd.Series(ut, dtype=float)


def klynger(datoer):
    o = np.array([d.ordinal for d in datoer])
    rek = np.argsort(o, kind="stable")
    kl = np.zeros(len(o), int)
    c, sist = 0, None
    for i in rek:
        if sist is not None and o[i] - sist > KLYNGEGAP:
            c += 1
        kl[i] = c; sist = o[i]
    return kl


def S_av(v, kl):
    v = np.asarray(v, float)
    ok = np.isfinite(v)
    if not ok.any():
        return np.nan, 0, 0, []
    med = np.array([np.median(v[ok & (kl == c)]) for c in np.unique(kl[ok])])
    return float(med.mean()), int((med > 0).sum()), len(med), list(med)


FWD, MOT, SNITT = {}, {}, {}
for navn, (a, b) in VARIANTER.items():
    fm = vindu(MARKED, a, b)
    FWD[navn] = {k: vindu(v, a, b) for k, v in KURS.items()}
    MOT[navn] = {k: (f - fm.reindex(f.index)).dropna() for k, f in FWD[navn].items()}
    SNITT[navn] = {k: float(f.mean()) for k, f in FWD[navn].items()}


def null_S(rader, navn):
    """Hver episode flyttes til en tilfeldig kalendermaaned med samme
    aktiva. Maalet er mot markedet, som hovedtallet."""
    kl = klynger([t for t, _ in rader])
    ep = {}
    for (t, k), c in zip(rader, kl):
        ep.setdefault(c, []).append(k)
    d = {k: MOT[navn][k].to_dict() for k in {k for _, k in rader}}
    alle = sorted({p for v in d.values() for p in v})
    kand = []
    for ks in ep.values():
        med = [float(np.median([d[k][m] for k in ks if m in d[k]])) for m in alle
               if sum(m in d[k] for k in ks) * 2 >= len(ks)]
        if med:
            kand.append(np.array(med))
    if not kand:
        return np.array([])
    return np.column_stack([k[rng.integers(len(k), size=TREKK)] for k in kand]).mean(axis=1)


pst = lambda v: "     -  " if v is None or not np.isfinite(v) else f"{100 * (np.exp(v) - 1):+7.1f} %"


def maal(tittel, hend, navn, med_p=True, vis_episoder=False):
    """hend: liste av (t, aktivum). Skriver en linje og returnerer tallene."""
    rader = [(t, k) for t, k in hend if t in MOT[navn][k].index]
    if not rader:
        print(f"   {tittel:58} ingen innslag med utfall")
        return None
    kl = klynger([t for t, _ in rader])
    mot = [float(MOT[navn][k][t]) for t, k in rader]
    mer = [float(FWD[navn][k][t]) - SNITT[navn][k] for t, k in rader]
    S, pos, n, med = S_av(mot, kl)
    Se, pose, _, _ = S_av(mer, kl)
    p = np.nan
    if med_p:
        nu = null_S(rader, navn)
        p = float(((nu >= S).sum() + 1) / (len(nu) + 1)) if len(nu) and np.isfinite(S) else np.nan
    print(f"   {tittel:58} {len(rader):3d} {n:3d} | {pst(S)} {pos:2d}/{n:<2d} "
          f"{'  -  ' if not np.isfinite(p) else format(p, '.3f')} | {pst(Se)} {pose:2d}/{n:<2d}")
    if vis_episoder:
        for c in np.unique(kl):
            ts = sorted({t for (t, _), cc in zip(rader, kl) if cc == c})
            ks = sorted({k.split(':')[1] for (t, k), cc in zip(rader, kl) if cc == c})
            m = np.median([v for v, cc in zip(mot, kl) if cc == c])
            print(f"        {str(ts[0])} til {str(ts[-1])}  n={sum(kl == c):2d}  {pst(m)}  ({', '.join(ks)})")
    return {"innslag": len(rader), "episoder": n, "S": S, "S_pos": pos, "p": p,
            "S_eget": Se, "S_eget_pos": pose, "episodemedianer": med}


HODE = ("   " + " " * 58 + " inn  ep | mot marked: S  ep+   p    | mot eget snitt: S  ep+")

# bransjene, en gang per maaned
HB, sett = [], set()
for sid, ts in INNSLAG.items():
    for t in ts:
        for b in BRANSJE.get(sid, []):
            if (t, f"ff:{b}") not in sett:
                sett.add((t, f"ff:{b}")); HB.append((t, f"ff:{b}"))
HB.sort()

# datoene hypotesen ble funnet i: innslagene i papirtesten
try:
    FUNNET = sorted({pd.Period(r["t"], "M") for r in json.load(open("sonder/backtest.json", encoding="utf-8"))["innslag_papirer"]})
except Exception as e:
    FUNNET = []
    print(f"   sonder/backtest.json kunne ikke leses ({type(e).__name__}), kontrollen hoppes over")
naer_funnet = lambda t: any(abs(t.ordinal - f.ordinal) <= KLYNGEGAP for f in FUNNET)

print("\n\n2. BRANSJENE (hovedtest)")
print(f"   Datoer i papirtesten (utelates i kontrollen): {' '.join(str(f) for f in FUNNET)}")
RES = {}
for navn in VARIANTER:
    print(f"\n   {navn}")
    print(HODE)
    foer = [x for x in HB if x[0] < SPLITT]
    RES[f"bransjer_foer2011 | {navn}"] = maal("Foer 2011-09 (AVGJOER for hypotesen)" if navn == HOVED
                                              else "Foer 2011-09", foer, navn, vis_episoder=(navn == HOVED))
    RES[f"bransjer_foer2011_uten_funnet | {navn}"] = maal(
        "Foer 2011-09, uten tidsoverlapp med papirtesten", [x for x in foer if not naer_funnet(x[0])], navn)
    RES[f"bransjer_fra2011 | {navn}"] = maal("Fra 2011-09 (inne i utvalget)", [x for x in HB if x[0] >= SPLITT], navn)
    RES[f"bransjer_alle | {navn}"] = maal("Alle", HB, navn)

# land
print("\n\n3. LANDENE (beskrivende)")
KART = json.load(open("sonder/fondkart_forslag.json", encoding="utf-8"))


def fondsflagg(fid, kun_en=False):
    par = [tuple(p["par"]) for p in KART[fid]["par"]]
    sids = sorted({s for p in par for s in p if s in BUNN})
    idx = None
    for s in sids:
        idx = BUNN[s].index if idx is None else idx.union(BUNN[s].index)
    b = {s: BUNN[s].reindex(idx).fillna(False) for s in sids}
    z = {s: SONE[s].reindex(idx).fillna(False) for s in sids}
    if kun_en:
        return pd.concat([b[s] for s in sids], axis=1).any(axis=1)
    ut = pd.Series(False, index=idx)
    for a, c in par:
        if a in b and c in b:
            ut |= z[a] & z[c] & (b[a] | b[c])
    return ut


HL = {"regelen": [], "en": []}
for fid in LAND:
    if fid not in KART or f"land:{fid}" not in KURS:
        continue
    for navn, kun in (("regelen", False), ("en", True)):
        HL[navn] += [(t, f"land:{fid}") for t in innslag(fondsflagg(fid, kun))]
    print(f"   {fid:10} regelen: {' '.join(str(t) for t, k in HL['regelen'] if k == 'land:' + fid) or '-'}")
    print(f"   {'':10} en i bunnsone: {' '.join(str(t) for t, k in HL['en'] if k == 'land:' + fid) or '-'}")
for navn in VARIANTER:
    print(f"\n   {navn}")
    print(HODE)
    RES[f"land_regelen_foer2011 | {navn}"] = maal("Fondsregelen, foer 2011-09", [x for x in HL["regelen"] if x[0] < SPLITT], navn)
    RES[f"land_en_foer2011 | {navn}"] = maal("En i bunnsone, foer 2011-09", [x for x in HL["en"] if x[0] < SPLITT], navn)
    RES[f"land_en_alle | {navn}"] = maal("En i bunnsone, alle", HL["en"], navn)

print("\n   Hvert landinnslag, T+1 til T+4 mot markedet:")
for navn in ("regelen", "en"):
    for t, k in sorted(HL[navn]):
        v = MOT[HOVED][k].get(t, np.nan)
        print(f"      {navn:8} {k[5:]:10} {str(t)}  {pst(v)}{'' if t < SPLITT else '   (fra 2011-09)'}")

# ============================================================ beslutning
print("\n\n4. Beslutning etter regelen satt foer kjoering")
o = RES[f"bransjer_foer2011 | {HOVED}"]
if not o:
    dom = "IKKE AVGJORT: ingen innslag med utfall"
else:
    andel = o["S_pos"] / o["episoder"]
    if andel >= 0.8 and o["S"] > 0:
        dom = "STOETTET"
    elif o["S"] > 0 and o["S_pos"] * 2 > o["episoder"] and np.isfinite(o["p"]) and o["p"] <= 0.10:
        dom = "SVAK STOETTE"
    else:
        dom = "IKKE STOETTET"
    print(f"   Bransjene foer 2011-09, T+1 til T+4 mot markedet: S {pst(o['S'])}, "
          f"{o['S_pos']} av {o['episoder']} episoder positive ({100 * andel:.0f} %), p {o['p']:.3f}")
print(f"   ->  {dom}")
if dom == "IKKE STOETTET":
    print("   Hypotesen har ikke stoette utenfor dataene den ble funnet i. Den boer bare logges,")
    print("   ikke brukes til kjoep.")

os.makedirs("sonder", exist_ok=True)


def rens(x):
    if isinstance(x, dict):
        return {str(k): rens(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [rens(v) for v in x]
    if isinstance(x, (float, np.floating)):
        return None if not np.isfinite(x) else round(float(x), 5)
    if isinstance(x, (np.integer, np.bool_)):
        return x.item()
    if isinstance(x, pd.Period):
        return str(x)
    return x


json.dump(rens({"kjort": time.strftime("%Y-%m-%d %H:%M:%S"), "dom": dom, "resultat": RES,
                "innslag_bransjer": [(str(t), k) for t, k in HB], "funnet_datoer": [str(f) for f in FUNNET]}),
          open("sonder/hypotese_t1.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("\n   lagret sonder/hypotese_t1.json")
