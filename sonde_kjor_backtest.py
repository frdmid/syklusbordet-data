# ---------------------------------------------------------------------------
# sonde_kjor_backtest: full backtest av bunnflagget, 1, 2, 3, 6 og 12 maaneder
#
# Frodes bestilling 28.09.2026: avkastning 1, 2, 3, 6 og 12 maaneder etter at
# raavareflagget er utloest, maalt paa (A) enkeltpapirene som staar paa
# dashbordet og (B) flerfaktorfondene ved fondsflagg.
#
# SIGNALET
#   Bunnsone: raa A >= 80 og detrendet A >= 80, punkt i tid, fra bordets egen
#   kode (raavare_hist, samme serier og samme avkorting som priser.py).
#   Innslag = foerste flaggede maaned etter mer enn tolv uten (PAUSE), som i
#   alle de andre sondene. d95 (detrendet A >= 95, Brent og WTI) testes
#   separat, fordi det er et parallelt signal og ikke bunnsonen.
#
# (A) ENKELTPAPIRER
#   Papirene i instrumenter.py, bare de med vanlig retning. De omvendte
#   (Air Liquide, Heidelberg, Hershey, Barry Callebaut, Nestle) har inngang
#   paa raavarens topp og hoerer ikke hjemme i en test av bunnflagget.
#   Laks har ikke flagg, og skipssegmentene har ikke A.
#
# (B) FLERFAKTORFOND
#   Kartet i sonder/fondkart_forslag.json (fondssonden 28.09.2026). Regelen er
#   Frodes fra 26.09.2026: minst to av fondets raavarer i et kvalifisert par
#   har raa A >= 80, og minst en av dem staar i bunnsone. Til sammenligning:
#   fondet kjoept naar bare EN av dets raavarer staar i bunnsone.
#   Fondene maales paa lengste kursserie (som i fondssonden). De tre
#   raavarefondene har samme tvilling (DBC) og telles derfor en gang.
#
# UTFALL, per horisont h
#   abs      totalavkastning i dollar (justert for utbytte og splitt), fra
#            slutten av flaggmaaneden (T0) til h maaneder etter
#   mer      samme, minus papirets egen snittavkastning over h maaneder fra
#            ALLE maaneder (tilfeldig kjoepsdato). Hovedtallet.
#   verden   samme, minus verdensindeksen (ACWI, SPY foer 2008) i samme vindu
#   raavare  raavarens egen realendring i samme vindu, som referanse
#   Alt regnes i log og vises som prosent.
#
#   Episoder: innslag paa tvers av segmenter med hoeyst seks maaneder mellom
#   (KLYNGEGAP), som i terskelsonden. S = snittet over episoder av episodens
#   median "mer". Det er S og antall positive episoder som sier noe, ikke
#   antall innslag, fordi 2008, 2015 og 2020 rammer mange papirer samtidig.
#
#   p: andelen av 2000 trekk der hver episode flyttes til en tilfeldig
#   kalendermaaned (alle papirer i episoden flyttes likt, saa klumpingen
#   beholdes) og S ble minst like hoey. Enveis. Faa episoder gir lav styrke.
#
# FORBEHOLD SATT FOER KJOERING
#   1. Papirene er valgt i 2026 paa korrelasjon fra 2016. Innslag fra 2016 er
#      derfor ikke uavhengige av utvalget. Resultatet deles i foer og fra 2016.
#   2. Kursene er dagens kurslister: papirer som gikk konkurs er ikke med.
#   3. T0 er slutten av flaggmaaneden. Pink Sheet for maaned t publiseres de
#      foerste virkedagene i t+1, saa T0 er noen dager for tidlig. Inngang en
#      maaned senere (T+1) vises som kontroll.
#   4. Fondskartet (hvilke raavarer et fond foelger) er maalt fra 2016 og brukt
#      bakover.
# ---------------------------------------------------------------------------

import json, os, time, warnings
import numpy as np
import pandas as pd
import requests
import terskel_motor as M
from instrumenter import INSTR

warnings.filterwarnings("ignore")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
HORISONTER = (1, 2, 3, 6, 12)
KLYNGEGAP, PAUSE, TREKK = 6, M.PAUSE, 2000
SPLITT = pd.Period("2016-01", "M")
NAA = pd.Period(pd.Timestamp.utcnow().strftime("%Y-%m"), "M")   # innevaerende maaned er ikke ferdig
rng = np.random.default_rng(20260928)

FX = {"USD": None, "EUR": ("EURUSD=X", False), "GBP": ("GBPUSD=X", False), "GBp": ("GBPUSD=X", False),
      "NOK": ("NOK=X", True), "SEK": ("SEK=X", True), "CAD": ("CAD=X", True), "CHF": ("CHF=X", True),
      "DKK": ("DKK=X", True), "AUD": ("AUDUSD=X", False)}


def get(url, timeout=60):
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


_fx = {}
def yahoo(sym, justert=True):
    """Maanedskurs i dollar, justert for utbytte og splitt, tidsstemplet i
    boersens egen tidssone (se yahoo_monthly i priser.py for hvorfor)."""
    j = "&events=div%7Csplit&includeAdjustedClose=true" if justert else ""
    res = get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}"
              f"?period1=0&period2={int(time.time())}&interval=1mo{j}").json()["chart"]["result"][0]
    meta = res.get("meta") or {}
    idx = pd.to_datetime(res["timestamp"], unit="s", utc=True).tz_convert(meta.get("exchangeTimezoneName") or "UTC")
    v = None
    if justert:
        try:
            v = res["indicators"]["adjclose"][0]["adjclose"]
        except Exception:
            v = None
    if v is None:
        v = res["indicators"]["quote"][0]["close"]
    s = pd.Series(v, index=idx).dropna()
    s = s[s > 0]
    s.index = s.index.to_period("M")
    s = s[~s.index.duplicated(keep="last")]
    val = meta.get("currency") or "USD"
    if val not in FX:
        raise ValueError(f"valuta {val}")
    if FX[val]:
        fs, inv = FX[val]
        if fs not in _fx:
            f = yahoo(fs, justert=False)
            _fx[fs] = (1.0 / f) if inv else f
        s = (s * _fx[fs].reindex(s.index).ffill()).dropna()
    if val == "GBp":
        s = s / 100.0
    return s[s.index < NAA]


def hent_kurs(sym):
    try:
        s = yahoo(sym)
        return s if len(s) >= 24 else None
    except Exception as e:
        print(f"      {sym}: {type(e).__name__}: {str(e)[:60]}")
        return None


# ===================================================================== data
print("0. Raavarene fra bordets egen kode\n")
from raavare_hist import hent
REAL, _NOM, cpi = hent()
LR, SEG, BUNN, SONE, D95 = {}, {}, {}, {}, {}
for sid, lr in REAL.items():
    if sid == "laks":
        continue
    lr = lr.dropna()
    full = pd.period_range(lr.index[0], lr.index[-1], freq="M")
    lr = lr.reindex(full).interpolate()
    s = M.Segment(sid, lr.values, np.array([p.ordinal for p in lr.index]))
    ok = np.isfinite(s.A) & np.isfinite(s.Ad)
    LR[sid], SEG[sid] = lr, s
    BUNN[sid] = pd.Series(ok & (s.A >= 80) & (s.Ad >= 80), index=lr.index)
    SONE[sid] = pd.Series(ok & (s.A >= 80), index=lr.index)
    D95[sid] = pd.Series(np.isfinite(s.Ad) & (s.Ad >= 95), index=lr.index)
print(f"\n   {len(LR)} segmenter: {', '.join(sorted(LR))}")


def innslag(fl):
    ut, siste = [], None
    for t in fl.index[fl.values]:
        if siste is None or t.ordinal - siste.ordinal > PAUSE:
            ut.append(t)
        siste = t
    return ut


INNSLAG = {sid: innslag(BUNNSONE) for sid, BUNNSONE in BUNN.items()}
print("\n   Innslag i bunnsone per segment (foerste flaggede maaned etter mer enn tolv uten):")
for sid in sorted(INNSLAG):
    if INNSLAG[sid]:
        print(f"      {sid:10} {len(INNSLAG[sid]):2d}  " + " ".join(str(t) for t in INNSLAG[sid]))

print("\n1. Kurser\n")
VERDEN = {}
for sym in ("ACWI", "SPY"):
    VERDEN[sym] = hent_kurs(sym)
verden = VERDEN["ACWI"]
if VERDEN["SPY"] is not None:
    spy = VERDEN["SPY"]
    if verden is None:
        verden = spy
    else:
        # SPY foer ACWI, skjoetet paa nivaa i foerste felles maaned
        f = verden.index[0]
        verden = pd.concat([spy[spy.index < f] * (verden[f] / spy[f]), verden])
LW = np.log(verden) if verden is not None else None
print(f"   verdensindeks: ACWI fra {VERDEN['ACWI'].index[0] if VERDEN['ACWI'] is not None else '-'}, "
      f"SPY foer det fra {VERDEN['SPY'].index[0] if VERDEN['SPY'] is not None else '-'}")

PAPIR = {}   # ticker -> {"segs": [...], "navn": ...}
for sid, rader in INSTR.items():
    if sid not in LR:
        continue
    for tk, bors, navn, typ, kom in rader:
        if kom.strip().startswith("-"):
            continue
        PAPIR.setdefault(tk, {"segs": [], "navn": navn, "type": typ})["segs"].append(sid)
KURS = {}
for tk in sorted(PAPIR):
    s = hent_kurs(tk)
    if s is not None:
        KURS[tk] = np.log(s)
    time.sleep(0.25)
print(f"   {len(KURS)} av {len(PAPIR)} papirer med kurs: "
      + ", ".join(f"{tk} ({KURS[tk].index[0]})" for tk in sorted(KURS)))
mangler = sorted(set(PAPIR) - set(KURS))
if mangler:
    print(f"   uten kurs: {', '.join(mangler)}")


# ================================================================= regnestykket
def fram_p(lk, h):
    """log-avkastning h maaneder fram, per maaned. Period-aritmetikk, saa et
    hull i kursserien ikke forskyver horisonten."""
    ut = {}
    for t, v in lk.items():
        e = t + h
        if e in lk.index:
            ut[t] = lk[e] - v
    return pd.Series(ut)


FWD = {h: {tk: fram_p(lk, h) for tk, lk in KURS.items()} for h in HORISONTER}
SNITT = {h: {tk: float(f.mean()) for tk, f in FWD[h].items() if len(f)} for h in HORISONTER}
FWD_W = {h: fram_p(LW, h) for h in HORISONTER} if LW is not None else None
FWD_R = {h: {sid: fram_p(lr, h) for sid, lr in LR.items()} for h in HORISONTER}


def klynger(datoer):
    """Returnerer klyngenummer per dato (samme rekkefoelge)."""
    o = np.array([d.ordinal for d in datoer])
    rek = np.argsort(o, kind="stable")
    kl = np.zeros(len(o), int)
    c, sist = 0, None
    for i in rek:
        if sist is not None and o[i] - sist > KLYNGEGAP:
            c += 1
        kl[i] = c; sist = o[i]
    return kl


def S_av(verdier, kl):
    v = np.asarray(verdier, float)
    ok = np.isfinite(v)
    if not ok.any():
        return np.nan, 0, 0
    med = np.array([np.median(v[ok & (kl == c)]) for c in np.unique(kl[ok])])
    return float(med.mean()), int((med > 0).sum()), len(med)


def utfall(hendelser, h, forsink=0):
    """hendelser: liste av (t, ticker, sid). Returnerer rader med abs, mer,
    verden og raavare for horisont h, inngang forsink maaneder etter t."""
    rader = []
    for t, tk, sid in hendelser:
        t0 = t + forsink
        f = FWD[h].get(tk)
        if f is None or t0 not in f.index:
            continue
        r = float(f[t0])
        w = float(FWD_W[h][t0]) if FWD_W is not None and t0 in FWD_W[h].index else np.nan
        rv = FWD_R[h][sid].get(t0, np.nan) if sid else np.nan
        rader.append({"t": t, "tk": tk, "sid": sid, "abs": r, "mer": r - SNITT[h][tk],
                      "verden": r - w if np.isfinite(w) else np.nan, "raavare": float(rv)})
    return rader


def null_S(rader, h):
    """Episodene flyttes til tilfeldige kalendermaaneder, alle papirer i en
    episode likt. Returnerer nullfordelingen for S."""
    if not rader:
        return np.array([])
    kl = klynger([r["t"] for r in rader])
    ep = {}
    for r, c in zip(rader, kl):
        ep.setdefault(c, []).append(r["tk"])
    # Paa forhaand, per episode: for hver kalendermaaned der minst halvparten
    # av episodens papirer har utfall, medianen av deres "mer". Da blir hvert
    # trekk bare et oppslag i en liste. Samme null som foer, men foerste
    # versjon slo opp i pandas for hvert papir i hvert trekk og var for treg.
    alle = sorted({p for f in FWD[h].values() for p in f.index})
    d = {tk: {p: float(x) - SNITT[h][tk] for p, x in FWD[h][tk].items()} for tk in {t for v in ep.values() for t in v}}
    kand = []
    for tks in ep.values():
        med = []
        for m in alle:
            v = [d[tk][m] for tk in tks if m in d[tk]]
            if v and len(v) * 2 >= len(tks):
                med.append(float(np.median(v)))
        kand.append(np.array(med))
    if any(len(k) == 0 for k in kand):
        kand = [k for k in kand if len(k)]
    if not kand:
        return np.array([])
    trekk = np.column_stack([k[rng.integers(len(k), size=TREKK)] for k in kand])
    return trekk.mean(axis=1)


pst = lambda v: "     -  " if v is None or not np.isfinite(v) else f"{100 * (np.exp(v) - 1):+7.1f} %"


def oppsummer(rader, h, med_p=True):
    if not rader:
        return None
    kl = klynger([r["t"] for r in rader])
    a = np.array([r["abs"] for r in rader]); m = np.array([r["mer"] for r in rader])
    w = np.array([r["verden"] for r in rader]); rv = np.array([r["raavare"] for r in rader])
    S, pos, n_ep = S_av(m, kl)
    Sw, posw, _ = S_av(w, kl)
    p = np.nan
    if med_p:
        nu = null_S(rader, h)
        if len(nu) and np.isfinite(S):
            p = float(((nu >= S).sum() + 1) / (len(nu) + 1))
    fin = lambda x: x[np.isfinite(x)]
    return {"h": h, "innslag": len(rader), "episoder": n_ep,
            "abs_median": float(np.median(a)), "abs_snitt": float(np.mean(a)),
            "abs_treff": float(np.mean(a > 0)),
            "mer_median": float(np.median(m)), "mer_treff": float(np.mean(m > 0)),
            "S": S, "S_pos": pos, "p": p,
            "verden_median": float(np.median(fin(w))) if len(fin(w)) else np.nan,
            "verden_treff": float(np.mean(fin(w) > 0)) if len(fin(w)) else np.nan,
            "S_verden": Sw, "S_verden_pos": posw,
            "raavare_median": float(np.median(fin(rv))) if len(fin(rv)) else np.nan,
            "verste": float(np.min(a)), "beste": float(np.max(a))}


def skriv_tabell(tittel, hendelser, forsink=0, med_p=True):
    print(f"\n   {tittel}")
    print("   h    innsl ep | abs: median   snitt  treff | mot eget snitt: median treff |   S       ep+   p    "
          "| mot verden: median  S      ep+ | raavare median")
    ut = {}
    for h in HORISONTER:
        o = oppsummer(utfall(hendelser, h, forsink), h, med_p)
        ut[h] = o
        if o is None:
            print(f"   {h:2d}   ingen"); continue
        print(f"   {h:2d}   {o['innslag']:4d} {o['episoder']:3d} | {pst(o['abs_median'])} {pst(o['abs_snitt'])} "
              f"{100 * o['abs_treff']:4.0f} % | {pst(o['mer_median'])} {100 * o['mer_treff']:4.0f} % | "
              f"{pst(o['S'])} {o['S_pos']:2d}/{o['episoder']:<2d} "
              f"{'  -  ' if not np.isfinite(o['p']) else format(o['p'], '.3f')} | "
              f"{pst(o['verden_median'])} {pst(o['S_verden'])} {o['S_verden_pos']:2d} | {pst(o['raavare_median'])}", flush=True)
    return ut


# ============================================================ (A) enkeltpapirer
print("\n\n2. (A) ENKELTPAPIRENE PAA DASHBORDET, VED BUNNSONE I EGEN RAAVARE")
print("   abs = totalavkastning i dollar. mer = mot papirets eget snitt (tilfeldig dato).")
print("   S = snitt over episoder av episodens median 'mer'. ep+ = episoder med positiv median.")
print("   p = andel av 2000 tilfeldige episodedatoer med minst like hoey S (enveis).")

HEND = [(t, tk, sid) for tk, p in PAPIR.items() if tk in KURS for sid in p["segs"] for t in INNSLAG[sid]]
RES = {"A_alle": skriv_tabell("Alle innslag, inngang T0 (slutten av flaggmaaneden)", HEND)}
RES["A_T1"] = skriv_tabell("Kontroll: inngang en maaned senere (T+1)", HEND, forsink=1, med_p=False)
RES["A_foer2016"] = skriv_tabell("Innslag foer 2016 (utenfor vinduet papirene ble valgt paa)",
                                 [x for x in HEND if x[0] < SPLITT])
RES["A_fra2016"] = skriv_tabell("Innslag fra 2016 (inne i utvalgsvinduet)",
                                [x for x in HEND if x[0] >= SPLITT])

print("\n   Per segment, 3 og 12 mnd (median abs, median mot eget snitt, antall innslag x papirer):")
PER_SEG = {}
for sid in sorted(INNSLAG):
    hs = [x for x in HEND if x[2] == sid]
    if not hs:
        continue
    PER_SEG[sid] = {}
    tekst = []
    for h in (3, 12):
        r = utfall(hs, h)
        if not r:
            tekst.append(f"{h:2d} mnd    -"); continue
        a = np.median([x["abs"] for x in r]); m = np.median([x["mer"] for x in r])
        PER_SEG[sid][h] = {"n": len(r), "abs_median": float(a), "mer_median": float(m)}
        tekst.append(f"{h:2d} mnd {pst(a)} / {pst(m)} (n {len(r):2d})")
    print(f"      {sid:10} " + "   ".join(tekst))

print("\n   Hvert innslag, median over segmentets papirer (abs, dollar):")
print("      " + "segment    innslag  papirer " + "".join(f"{h:>9d} mnd" for h in HORISONTER) + "    raavare 12 mnd")
EPI_LISTE = []
for sid in sorted(INNSLAG):
    for t in INNSLAG[sid]:
        tks = [tk for tk, p in PAPIR.items() if tk in KURS and sid in p["segs"] and t in FWD[1][tk].index]
        if not tks:
            continue
        v = {}
        for h in HORISONTER:
            xs = [FWD[h][tk][t] for tk in tks if t in FWD[h][tk].index]
            v[h] = float(np.median(xs)) if xs else np.nan
        rv = FWD_R[12][sid].get(t, np.nan)
        EPI_LISTE.append({"sid": sid, "t": str(t), "papirer": tks, **{f"h{h}": v[h] for h in HORISONTER},
                          "raavare12": float(rv)})
        print(f"      {sid:10} {str(t):8} {len(tks):3d}    " + "".join(f"{pst(v[h]):>13}" for h in HORISONTER)
              + f"   {pst(rv)}")

# d95, parallelt signal for olje
print("\n\n3. d95 (detrendet A >= 95), Brent og WTI, samme papirer")
HEND95 = [(t, tk, sid) for sid in ("brent", "wti") if sid in D95 for t in innslag(D95[sid])
          for tk, p in PAPIR.items() if tk in KURS and sid in p["segs"]]
for sid in ("brent", "wti"):
    if sid in D95:
        print(f"   {sid} innslag: {' '.join(str(t) for t in innslag(D95[sid]))}")
RES["d95"] = skriv_tabell("d95, inngang T0", HEND95)


# ============================================================ (B) flerfaktorfond
print("\n\n4. (B) FLERFAKTORFOND VED FONDSFLAGG")
KART = json.load(open("sonder/fondkart_forslag.json", encoding="utf-8"))
# Samme kilde som fondssonden: lengste serie av UCITS og tvilling.
FONDSYM = {"brasil": ["IBZL.L", "EWZ"], "norge": ["ENOR"], "australia": ["SAUS.L", "EWA"],
           "gruve_europa": ["EXV6.DE", "PICK"], "gruve_vaneck": ["GDIG.L", "PICK"],
           "raavare_ishares": ["EXXY.DE", "DBC"], "raavare_xtrackers": ["XDBC.DE", "DBC"],
           "raavare_invesco": ["CMOD.L", "DBC"]}
FKURS, brukt = {}, {}
for fid in KART:
    kand = [(sym, hent_kurs(sym)) for sym in FONDSYM.get(fid, [])]
    kand = [(sym, s) for sym, s in kand if s is not None]
    if not kand:
        print(f"   {fid}: ingen kurs"); continue
    sym, s = max(kand, key=lambda x: len(x[1]))
    if sym in brukt.values():
        print(f"   {fid}: samme serie som {[k for k, v in brukt.items() if v == sym][0]} ({sym}), telles ikke paa nytt")
        continue
    brukt[fid] = sym
    FKURS[fid] = np.log(s)
    print(f"   {fid:18} {sym:8} fra {s.index[0]}")
for fid, lk in FKURS.items():
    KURS[f"fond:{fid}"] = lk
    for h in HORISONTER:
        FWD[h][f"fond:{fid}"] = fram_p(lk, h)
        SNITT[h][f"fond:{fid}"] = float(FWD[h][f"fond:{fid}"].mean())


def fondsflagg(fid, kun_en=False):
    par = [tuple(p["par"]) for p in KART[fid]["par"]]
    sids = sorted({s for p in par for s in p})
    idx = None
    for s in sids:
        idx = BUNN[s].index if idx is None else idx.union(BUNN[s].index)
    b = {s: BUNN[s].reindex(idx).fillna(False) for s in sids}
    z = {s: SONE[s].reindex(idx).fillna(False) for s in sids}
    if kun_en:
        return pd.concat([b[s] for s in sids], axis=1).any(axis=1)
    ut = pd.Series(False, index=idx)
    for a, c in par:
        ut |= z[a] & z[c] & (b[a] | b[c])
    return ut


FHEND = {"regelen": [], "en_i_bunnsone": []}
for fid in FKURS:
    for navn, kun in (("regelen", False), ("en_i_bunnsone", True)):
        for t in innslag(fondsflagg(fid, kun)):
            FHEND[navn].append((t, f"fond:{fid}", None))
    print(f"   {fid:18} regelen: {' '.join(str(t) for t, f, _ in FHEND['regelen'] if f == 'fond:' + fid) or '-'}"
          f"   |   en i bunnsone: {' '.join(str(t) for t, f, _ in FHEND['en_i_bunnsone'] if f == 'fond:' + fid) or '-'}")

RES["B_regelen"] = skriv_tabell("Fondsregelen (to i sonen, minst en i bunnsone), inngang T0", FHEND["regelen"])
RES["B_regelen_T1"] = skriv_tabell("Fondsregelen, inngang T+1 (kontroll)", FHEND["regelen"], forsink=1, med_p=False)
RES["B_en"] = skriv_tabell("Sammenligning: en av fondets raavarer i bunnsone, inngang T0", FHEND["en_i_bunnsone"])

print("\n   Hvert fondsinnslag etter regelen (abs, dollar):")
print("      fond               innslag " + "".join(f"{h:>9d} mnd" for h in HORISONTER))
FOND_LISTE = []
for t, tk, _ in sorted(FHEND["regelen"], key=lambda x: (x[1], x[0])):
    v = {h: (float(FWD[h][tk][t]) if t in FWD[h][tk].index else np.nan) for h in HORISONTER}
    FOND_LISTE.append({"fond": tk[5:], "t": str(t), **{f"h{h}": v[h] for h in HORISONTER}})
    print(f"      {tk[5:]:18} {str(t):8}" + "".join(f"{pst(v[h]):>13}" for h in HORISONTER))


# ============================================================== lagre
def rens(x):
    if isinstance(x, dict):
        return {str(k): rens(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [rens(v) for v in x]
    if isinstance(x, (float, np.floating)):
        return None if not np.isfinite(x) else round(float(x), 5)
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, pd.Period):
        return str(x)
    return x


os.makedirs("sonder", exist_ok=True)
json.dump(rens({"kjort": time.strftime("%Y-%m-%d %H:%M:%S"), "horisonter": HORISONTER,
                "innslag": {s: [str(t) for t in v] for s, v in INNSLAG.items() if v},
                "resultat": RES, "per_segment": PER_SEG, "innslag_papirer": EPI_LISTE,
                "fond_innslag": FOND_LISTE, "fond_serier": brukt,
                "papirer_uten_kurs": mangler}),
          open("sonder/backtest.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("\n   lagret sonder/backtest.json")
