# ---------------------------------------------------------------------------
# sonde_kjor_regel_foer2011: kort hypotese og regel 60/40 testet bakover
#
# Frodes beslutning 29.09.2026 (punkt 5 etter den uavhengige gjennomgangen).
# Hypotesen "kjoep en maaned etter flagget, selg tre maaneder etter kjoepet"
# ble funnet i 2011 til 2026 og logges framover i flagglogg.py. Den er aldri
# testet paa data den ikke ble funnet i. Det samme gjelder Frodes praktiske
# regel 60/40. Denne sonden tester begge paa Ken French-data foer 2011-09.
#
# ALT UNDER ER SKREVET NED FOER KJOERING OG SKAL IKKE ENDRES ETTER
#
# FLAGGET  som i sonde_kjor_backtest_lang: bunnsone (raa og detrendet A >= 80)
#          fra bordets egen kode, innslag etter mer enn tolv maaneder uten.
#          T = flaggmaaneden.
# DATA     HOVED: Ken French 49 bransjer, verdivektet, i dollar, med samme
#          kart som sonde_kjor_backtest_lang (Oil, Gold, Mines, Steel, Coal;
#          kakao og palmeolje utelatt). STOETTE: landporteføljene for Norge
#          (foer 2012-01) og Australia (foer 1996-03) med fondsregelen fra
#          sonder/fondkart_forslag.json, som i sonde_kjor_land.
# REGLER   H3:    kjoep ved slutten av T+1, selg ved slutten av T+4.
#          60/40: kjoep ved slutten av T+1. 60 % selges ved T+4, 40 % ved
#                 T+13 (12 mnd) eller T+25 (24 mnd).
# MAAL     mot det amerikanske markedet (Mkt-RF + RF) i samme vindu, fordi
#          ACWI ikke finnes saa langt tilbake. For 60/40:
#          0,6 x (proxy minus marked, T+1 til T+4)
#          + 0,4 x (proxy minus marked, T+1 til T+13 eller T+25),
#          i log-avkastning, vist som prosent.
# EPISODER innslag med hoeyst seks maaneder mellom. En proxy telles en gang
#          per episode (foerste flagg), ogsaa naar flere raavarer peker paa
#          den (Brent og WTI paa Oil). S = snitt over episoder av episodens
#          median. p = andel av 2000 trekk der hver episode flyttes til en
#          tilfeldig maaned, med minst like hoey S.
# AVGJOER  bransjene, innslag foer 2011-09. En regel BESTAAR hvis S > 0 og
#          flertallet av episodene er positive. For 60/40 avgjoer 24 mnd; 12
#          mnd vises. Er p over 0,10, skrives "bestaar, men svakt".
#          Landene er for faa til aa avgjoere noe og vises bare.
# ---------------------------------------------------------------------------

import io, json, re, time, warnings, zipfile
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
KART = {
    "brent": ["Oil"], "wti": ["Oil"], "henryhub": ["Oil"], "ttf": ["Oil"],
    "gold": ["Gold"], "kobber": ["Mines"], "nikkel": ["Mines"], "aluminium": ["Steel"],
    "sink": ["Mines"], "bly": ["Mines"], "tinn": ["Mines"], "jernmalm": ["Mines", "Steel"],
    "kull": ["Coal"], "uran": ["Mines"],
}
LAND = {"norge": ("Norway", "2012-01"), "australia": ("Austrlia", "1996-03")}


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


def french(fil, blokk):
    z = zipfile.ZipFile(io.BytesIO(get(FRENCH + fil).content))
    tekst = z.read(z.namelist()[0]).decode("latin1").splitlines()
    i = next(i for i, l in enumerate(tekst) if blokk in l) if blokk else 0
    while not (tekst[i].strip().startswith(",") and len(tekst[i].split(",")) > 2):
        i += 1
    kol = [c.strip() for c in tekst[i].split(",")[1:]]
    rader = {}
    for l in tekst[i + 1:]:
        f = [x.strip() for x in l.split(",")]
        if not f[0].isdigit() or len(f[0]) != 6:
            break
        rader[pd.Period(f"{f[0][:4]}-{f[0][4:]}", "M")] = [float(x) for x in f[1:len(kol) + 1]]
    d = pd.DataFrame.from_dict(rader, orient="index", columns=kol).sort_index()
    return d.where(d > -99.0)


def les_land(tekst):
    """Som i sonde_kjor_land."""
    rader, kol = {}, None
    for i, l in enumerate(tekst):
        f = [x for x in re.split(r"[,\s]+", l.strip()) if x]
        if f and re.fullmatch(r"\d{6}", f[0]):
            if kol is None:
                j = i - 1
                while j >= 0 and not tekst[j].strip():
                    j -= 1
                kol = [x for x in re.split(r",|\s{2,}|\t", tekst[j].strip()) if x.strip()]
            elif rader and pd.Period(f"{f[0][:4]}-{f[0][4:]}", "M") <= max(rader):
                break
            try:
                rader[pd.Period(f"{f[0][:4]}-{f[0][4:]}", "M")] = [float(x) for x in f[1:]]
            except ValueError:
                continue
    n = min(len(v) for v in rader.values())
    d = pd.DataFrame({p: v[:n] for p, v in rader.items()}).T.sort_index()
    kol = [k.strip() for k in (kol or [])]
    if len(kol) >= n:
        d.columns = kol[-n:] if len(kol) > n else kol
    return d.where(d > -99.0)


nivaa = lambda r_pst: np.log1p(r_pst.dropna() / 100.0).cumsum()


def innslag(fl):
    ut, siste = [], None
    for t in fl.index[fl.values]:
        if siste is None or t.ordinal - siste.ordinal > PAUSE:
            ut.append(t)
        siste = t
    return ut


# ===================================================================== data
print("0. Raavarene fra bordets egen kode\n")
from raavare_hist import hent
REAL, _NOM, cpi = hent()
BUNN, SONE = {}, {}
for sid, lr in REAL.items():
    lr = lr.dropna()
    full = pd.period_range(lr.index[0], lr.index[-1], freq="M")
    lr = lr.reindex(full).interpolate()
    s = M.Segment(sid, lr.values, np.array([p.ordinal for p in lr.index]))
    ok = np.isfinite(s.A) & np.isfinite(s.Ad)
    BUNN[sid] = pd.Series(ok & (s.A >= 80) & (s.Ad >= 80), index=lr.index)
    SONE[sid] = pd.Series(ok & (s.A >= 80), index=lr.index)

print("\n1. Ken French\n")
IND = french("49_Industry_Portfolios_CSV.zip", "Value Weighted Returns -- Monthly")
FAK = french("F-F_Research_Data_Factors_CSV.zip", None)
KURS = {f"ff:{b}": nivaa(IND[b]) for b in sorted({x for v in KART.values() for x in v})}
MARKED = nivaa(FAK["Mkt-RF"] + FAK["RF"])
z = zipfile.ZipFile(io.BytesIO(get(FRENCH + "F-F_International_Countries.zip").content))
for fid, (land, _) in LAND.items():
    treff = [x for x in z.namelist() if land.lower() in x.lower()]
    if treff:
        d = les_land(z.read(treff[0]).decode("latin1").splitlines())
        k = next((c for c in d.columns if str(c).lower() in ("mkt", "market")), d.columns[0])
        KURS[f"land:{fid}"] = nivaa(d[k])
for k, v in KURS.items():
    print(f"   {k:14s} fra {v.index[0]} til {v.index[-1]}")


# ================================================================ regnestykket
def vindu(lk, a, b):
    """Log-avkastning fra slutten av maaned a til slutten av maaned b."""
    return lk[b] - lk[a] if a in lk.index and b in lk.index else np.nan


def ex(tk, t, fra, til):
    r, m = vindu(KURS[tk], t + fra, t + til), vindu(MARKED, t + fra, t + til)
    return r - m


_memo = {}
def regler(tk, t):
    if (tk, t) not in _memo:
        h3 = ex(tk, t, 1, 4)
        _memo[(tk, t)] = {"H3": h3,
                          "6040_12": 0.6 * h3 + 0.4 * ex(tk, t, 1, 13),
                          "6040_24": 0.6 * h3 + 0.4 * ex(tk, t, 1, 25)}
    return _memo[(tk, t)]


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


def hendelser_bransje():
    rader = [(t, f"ff:{p}", sid) for sid, lst in KART.items() if sid in BUNN
             for t in innslag(BUNN[sid]) for p in lst if f"ff:{p}" in KURS]
    return en_per_episode(rader)


def en_per_episode(rader):
    rader = sorted(rader)
    kl = klynger([r[0] for r in rader]) if rader else []
    ut, sett = [], set()
    for r, c in zip(rader, kl):
        if (c, r[1]) not in sett:
            sett.add((c, r[1])); ut.append(r + (int(c),))
    return ut


def fondsflagg(fid):
    par = [tuple(p["par"]) for p in json.load(open("sonder/fondkart_forslag.json", encoding="utf-8"))[fid]["par"]]
    sids = sorted({s for p in par for s in p})
    idx = None
    for s in sids:
        idx = BUNN[s].index if idx is None else idx.union(BUNN[s].index)
    b = {s: BUNN[s].reindex(idx).fillna(False) for s in sids}
    zz = {s: SONE[s].reindex(idx).fillna(False) for s in sids}
    ut = pd.Series(False, index=idx)
    for a, c in par:
        ut |= zz[a] & zz[c] & (b[a] | b[c])
    return ut


def S_av(verdier, kl):
    v = np.asarray(verdier, float); kl = np.asarray(kl)
    ok = np.isfinite(v)
    if not ok.any():
        return np.nan, 0, 0, []
    med = [float(np.median(v[ok & (kl == c)])) for c in np.unique(kl[ok])]
    return float(np.mean(med)), sum(m > 0 for m in med), len(med), med


ALLE_T = sorted(MARKED.index)


def null_S(rader, regel):
    ep = {}
    for r in rader:
        ep.setdefault(r[3], []).append(r[1])
    kand = []
    for tks in ep.values():
        med = []
        for m in ALLE_T:
            v = [regler(tk, m)[regel] for tk in tks]
            v = [x for x in v if np.isfinite(x)]
            if v and len(v) * 2 >= len(tks):
                med.append(float(np.median(v)))
        if med:
            kand.append(np.array(med))
    if not kand:
        return np.array([])
    return np.column_stack([k[rng.integers(len(k), size=TREKK)] for k in kand]).mean(axis=1)


pst = lambda v: "     -  " if v is None or not np.isfinite(v) else f"{100 * (np.exp(v) - 1):+7.1f} %"


def tabell(tittel, rader, med_p=True):
    print(f"\n   {tittel}: {len(rader)} innslag, {len({r[3] for r in rader})} episoder")
    ut = {}
    for regel, navn in (("H3", "H3 (T+1 til T+4)"), ("6040_12", "60/40, 12 mnd"), ("6040_24", "60/40, 24 mnd")):
        v = [regler(r[1], r[0])[regel] for r in rader]
        S, pos, n, med = S_av(v, [r[3] for r in rader])
        nu = null_S(rader, regel) if med_p and n else np.array([])
        p = float(((nu >= S).sum() + 1) / (len(nu) + 1)) if len(nu) and np.isfinite(S) else np.nan
        treff = np.mean([x > 0 for x in v if np.isfinite(x)]) if any(np.isfinite(v)) else np.nan
        ut[regel] = {"S": S, "pos": pos, "n": n, "p": p, "treff": treff, "medianer": med}
        print(f"      {navn:18s} S {pst(S)}  {pos:2d}/{n:<2d} episoder positive  "
              f"p {'  -  ' if not np.isfinite(p) else format(p, '.3f')}  "
              f"treff per innslag {'-' if not np.isfinite(treff) else format(100 * treff, '.0f') + ' %'}")
    return ut


print("\n\n2. BRANSJENE (avgjoer: innslag foer 2011-09)")
HB = hendelser_bransje()
RES = {"foer2011": tabell("Foer 2011-09 (AVGJOER)", [r for r in HB if r[0] < SPLITT]),
       "fra2011": tabell("Fra 2011-09 (inne i perioden hypotesen ble funnet i)", [r for r in HB if r[0] >= SPLITT])}

print("\n   Hvert innslag foer 2011-09 (proxy minus marked):")
print("      episode innslag  proxy   segment        H3     60/40 12m  60/40 24m")
for t, tk, sid, c in HB:
    if t >= SPLITT:
        continue
    r = regler(tk, t)
    print(f"      {c:5d}   {str(t):8s} {tk[3:]:6s}  {sid:10s} {pst(r['H3'])} {pst(r['6040_12'])} {pst(r['6040_24'])}")

print("\n\n3. LANDENE (stoette, foer fondenes egen historikk)")
for fid, (_, start) in LAND.items():
    if f"land:{fid}" not in KURS:
        print(f"   {fid}: ingen data"); continue
    try:
        rr = en_per_episode([(t, f"land:{fid}", "fondsregel") for t in innslag(fondsflagg(fid))
                             if t < pd.Period(start, "M")])
    except Exception as e:
        print(f"   {fid}: {type(e).__name__}: {e}"); continue
    print(f"   {fid}: innslag " + " ".join(str(r[0]) for r in rr))
    for r in rr:
        g = regler(r[1], r[0])
        print(f"      {str(r[0])}  H3 {pst(g['H3'])}  60/40 12m {pst(g['6040_12'])}  24m {pst(g['6040_24'])}")

print("\n\n4. Beslutning etter regelen satt foer kjoering (bransjene foer 2011-09)")
DOM = {}
for regel, navn in (("H3", "H3 (kjoep T+1, selg T+4)"), ("6040_24", "60/40 (dom paa 24 mnd)")):
    o = RES["foer2011"][regel]
    ok = np.isfinite(o["S"]) and o["S"] > 0 and o["pos"] * 2 > o["n"]
    DOM[regel] = "bestaar ikke" if not ok else ("bestaar, men svakt" if not (o["p"] <= 0.10) else "bestaar")
    print(f"   {navn:26s} S {pst(o['S'])}, {o['pos']} av {o['n']} episoder positive, p {o['p']:.3f}  ->  {DOM[regel]}")

json.dump({"res": {k: {r: {kk: vv for kk, vv in v.items()} for r, v in d.items()} for k, d in RES.items()},
           "dom": DOM, "innslag": [(str(t), tk, sid, c) for t, tk, sid, c in HB]},
          open("sonder/regel_foer2011.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
print("\nlagret sonder/regel_foer2011.json")
