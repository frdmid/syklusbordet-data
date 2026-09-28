# ---------------------------------------------------------------------------
# sonde_kjor_fond_norge: Norge i fondskartet via vanlige indeksfond
#
# Fondssonden (28.09.2026) fant at Norge (maalt paa ENOR, amerikansk ETF)
# foelger olje sterkt (rp 0,58) og kvalifiserte med brent+ttf og
# brent+aluminium (samlet 0,61), men fant ikke et OBX-fond kjoepbart paa IKZ.
# Frode foreslo vanlige fond. Denne sonden er fondssonden med bare de to
# norske indeksfondene, samme krav, samme maaling og samme historiske test.
# Resultatet skrives til sonder/fond_norge.json og sonder/fondkart_forslag_norge.json,
# slik at fondssondens egne filer ikke overskrives.
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# sonde_kjor_fond: flerfaktorfond. Hvilke fond fanger flere av bordets
# raavarer samtidig, og ville et flagg paa kombinasjonen gitt noe?
#
# Frodes ide 26.09.2026: et land- eller sektorfond kan fange flere raavarer
# samtidig (olje og jern = Brasil). Staar to av dem i sonen samtidig, trenger
# man ikke treffe den enkelte raavaren. Bildet er aa satse paa en tredel av
# rulettbordet i stedet for ett tall.
#
# REGELEN (valgt av Frode 26.09.2026, foer denne sonden er kjoert)
#   Et fond flagges naar minst to av fondets raavarer har raa A >= 80, og minst
#   en av dem staar i bunnsone (raa og detrendet A >= 80). Vises paa dashbordet
#   som kontekst merket "ikke testet". Denne sonden gir kartet og testen.
#
# DEL 1  Kart: hvilke raavarer foelger hvert fond?
#   Maaling i maanedlige realendringer i dollar, fast vindu fra 2016-01, samme
#   deflator som bordet. rp = partiell korrelasjon etter verdensindeksen
#   (IWDA.L). Krav, satt foer kjoering:
#     a) raavaren er begrunnet paa forhaand for fondet (A_PRIORI under)
#     b) minst 72 maaneder i vinduet
#     c) rp >= 0,20 for raavaren alene. Lavere enn 0,30 for enkeltpapirer,
#        fordi et bredt fond deler seg paa mange kilder (Vale er en liten del
#        av et Brasil-fond), og det er nettopp poenget.
#     d) et PAR kvalifiserer naar den samlede partielle korrelasjonen mellom
#        fondet og de to raavarene (begge etter verdensindeksen) er >= 0,30,
#        samme grense som for enkeltpapirene. Fondet maa altsaa foelge
#        kombinasjonen minst like godt som et godkjent enkeltpapir foelger
#        sin ene raavare.
#   Fangst (beskrivende, ikke krav): fondets realendring tolv maaneder fra
#   daterte bunner i raavaren, delt paa raavarens egen, som f i instrumenter.py.
#   Korrelasjon i maanedsendringer sier om fondet foelger raavaren i vanlig
#   drift. Fangst sier om oppgangen fra bunnen faktisk blir med, og hvor mye.
#   Over 1 er en forsterker, under 1 en demper. Maales paa lengste serie.
#     e) de to raavarene i paret er ikke samme faktor: korrelasjon i
#        maanedsendringer under 0,70. Brent og WTI er ett oljeprisrisiko, ikke
#        to, og et par av dem ville flagget paa en enkelt raavare.
#   Maales paa UCITS-utgaven (kjoepbar paa IKZ) hvis den har nok historikk i
#   vinduet, ellers paa den amerikanske tvillingen som foelger samme indeks.
#
# DEL 2  Historisk test av regelen
#   A og detrendet A punkt i tid fra bordets egen kode (raavare_hist). Kartet
#   fra del 1 brukes bakover, og det er en svakhet: korrelasjonene er maalt
#   fra 2016. Innslag = foerste flaggede maaned etter mer enn tolv uten.
#   Utfall: fondets realendring 6, 12 og 24 maaneder etter, minus fondets eget
#   snitt over alle maaneder (tilfeldige kjoepsdatoer). Lengste serie brukes
#   (som regel den amerikanske tvillingen). Til sammenligning: samme maaling
#   naar bare EN av fondets raavarer er i bunnsone.
#   Episodene klumper seg i tid (2015 og 2020 rammer mange fond samtidig), saa
#   de telles ogsaa per kalenderepisode (innslag med hoeyst seks maaneder
#   mellom). Faa uavhengige episoder: resultatet er beskrivende. Det regnes
#   ingen p-verdi, fordi styrken med saa faa episoder er for lav til at et nei
#   betyr noe, og et ja fra fem episoder er ikke et bevis.
#
# DEL 3  Status i dag og forslag til fondskart (sonder/fondkart_forslag.json)
# ---------------------------------------------------------------------------

import io, json, os, re, time, warnings
import numpy as np
import pandas as pd
import requests
import terskel_motor as M

warnings.filterwarnings("ignore")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
FIKS, NF_KRAV, RP_KRAV, RJ_KRAV = "2016-01", 72, 0.20, 0.30
HORISONTER = (6, 12, 24)
SAMME_FAKTOR = 0.70   # to raavarer med hoeyere korrelasjon er samme faktor, ikke et par   # 6 mnd lagt til etter oenske fra Frode 26.09.2026, foer kjoering
SEKSTEN = ["brent", "wti", "henryhub", "ttf", "uran", "gold", "kobber", "nikkel", "aluminium",
           "sink", "bly", "tinn", "jernmalm", "kull", "kakao", "palmeolje"]
METALL = ["kobber", "nikkel", "aluminium", "sink", "bly", "jernmalm", "kull"]
KONTROLL = "IWDA.L"

# navn, type, UCITS-symboler (forsoek i rekkefoelge), ISIN, amerikansk tvilling, a priori raavarer
FOND = [
    # Norge som vanlige fond (Frodes forslag 28.09.2026): verdipapirfond, ikke
    # ETF, kjoepbare paa IKZ hos Nordnet. Yahoo har kursene som Morningstar-id.
    ("norge_nordnet", "Nordnet Indeksfond Norge", "land", ["0P000134K7.IR"], None, "ENOR",
     ["brent", "wti", "ttf", "aluminium"]),
    ("norge_klp", "KLP AksjeNorge Indeks", "land", ["0P0000HNUP.IR", "0P00001BVT.IR"], None, "ENOR",
     ["brent", "wti", "ttf", "aluminium"]),
]
FX = {"USD": None, "EUR": ("EURUSD=X", False), "GBP": ("GBPUSD=X", False), "GBp": ("GBPUSD=X", False),
      "NOK": ("NOK=X", True), "SEK": ("SEK=X", True)}


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


_fx = {}
def yahoo(sym, justert=True):
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
    return s


def via_isin(isin):
    try:
        r = get(f"https://query2.finance.yahoo.com/v1/finance/search?q={isin}&quotesCount=25&newsCount=0").json()
    except Exception:
        return []
    return [q["symbol"] for q in r.get("quotes", [])
            if q.get("symbol", "").endswith((".L", ".DE", ".AS", ".SW", ".PA", ".MI", ".OL"))]


def hent_forste(symboler):
    for s in symboler:
        try:
            x = yahoo(s)
            if len(x) >= 24:
                return s, x
        except Exception:
            pass
        time.sleep(0.3)
    return None, None


# ================================================================ data
print("0. Raavarene fra bordets egen kode\n")
from raavare_hist import hent
REAL, _NOM, cpi = hent()
if not isinstance(cpi.index, pd.PeriodIndex):
    cpi.index = pd.DatetimeIndex(cpi.index).to_period("M")
defl = lambda s: (s * (cpi.dropna().iloc[-1] / cpi.reindex(s.index).ffill())).dropna()
SEG, LR = {}, {}
for sid in SEKSTEN:
    if sid not in REAL:
        print(f"   {sid}: mangler"); continue
    lr = REAL[sid].dropna()
    full = pd.period_range(lr.index[0], lr.index[-1], freq="M")
    lr = lr.reindex(full).interpolate()
    LR[sid] = lr
    SEG[sid] = M.Segment(sid, lr.values, np.array([p.ordinal for p in lr.index]))
print(f"   {len(SEG)} segmenter")
STATUS = {}
for sid, s in SEG.items():
    ok = np.isfinite(s.A) & np.isfinite(s.Ad)
    STATUS[sid] = pd.DataFrame({"sone": ok & (s.A >= 80), "bunn": ok & (s.A >= 80) & (s.Ad >= 80)},
                               index=LR[sid].index)

print("\n1. Fondene\n")
_, w = hent_forste([KONTROLL])
w = defl(w) if w is not None else None
KURS = {}
for fid, navn, typ, ucits, isin, tvilling, ap in FOND:
    sym, s = hent_forste(ucits)
    if s is None and isin:
        sym, s = hent_forste(via_isin(isin))
    tsym, ts = hent_forste([tvilling]) if tvilling else (None, None)
    KURS[fid] = {"ucits": sym, "u": None if s is None else defl(s),
                 "tvilling": tsym, "t": None if ts is None else defl(ts)}
    u, t = KURS[fid]["u"], KURS[fid]["t"]
    print(f"   {fid:18} UCITS {sym or '-':12} {'' if u is None else str(u.index[0]):8}   "
          f"tvilling {tsym or '-':6} {'' if t is None else str(t.index[0])}")

dl = lambda s: np.log(s).diff().dropna()


BUNNVINDU = 18   # samme som sonde_ikz.py


def bunner(lr):
    """Maaneder som er laveste realpris i +/- 18 mnd, naboer slaatt sammen."""
    v, ut = lr.values, []
    for i in range(BUNNVINDU, len(v) - BUNNVINDU):
        if v[i] == v[i - BUNNVINDU:i + BUNNVINDU + 1].min():
            if not ut or i - ut[-1] > BUNNVINDU:
                ut.append(i)
    return [lr.index[i] for i in ut]


def fangst(lr, serie, h=12):
    """Fondets samlede realendring h mnd fra daterte bunner i raavaren, delt
    paa raavarens. Samme maal som f i instrumenter.py. Svarer paa det
    korrelasjonen ikke svarer paa: blir oppgangen fra bunnen med?"""
    lk = np.log(serie)
    par = []
    for b in bunner(lr):
        bt = b + h
        if b in lk.index and bt in lk.index and bt in lr.index:
            par.append((str(b), float(lr[bt] - lr[b]), float(lk[bt] - lk[b])))
    sc = sum(x[1] for x in par)
    return (round(sum(x[2] for x in par) / sc, 2) if len(par) >= 2 and abs(sc) > 0.05 else None), par


def rest(y, w_):
    """Residual av y etter verdensindeksen (OLS med konstant)."""
    X = np.column_stack([np.ones(len(w_)), w_])
    b = np.linalg.lstsq(X, y, rcond=None)[0]
    return y - X @ b


# ================================================================ del 1
print("\n2. Kart: raavarer per fond (fast vindu fra 2016, etter verdensindeksen)\n")
KART = {}
for fid, navn, typ, ucits, isin, tvilling, ap in FOND:
    k = KURS[fid]
    kilde, serie = None, None
    for navn_s, s in (("UCITS " + str(k["ucits"]), k["u"]), ("tvilling " + str(k["tvilling"]), k["t"])):
        if s is not None and (s.index >= pd.Period(FIKS, "M")).sum() >= NF_KRAV + 1:
            kilde, serie = navn_s, s
            break
    if serie is None or w is None:
        print(f"   {fid}: for kort historikk i vinduet, ikke maalt"); continue
    y_all = dl(serie)
    rader, res = {}, {}
    for sid in ap:
        if sid not in LR:
            continue
        x_all = LR[sid].diff().dropna()
        i = y_all.index.intersection(x_all.index).intersection(dl(w).index)
        i = i[i >= pd.Period(FIKS, "M")]
        if len(i) < NF_KRAV:
            continue
        ww = dl(w).reindex(i).values
        yr, xr = rest(y_all.reindex(i).values, ww), rest(x_all.reindex(i).values, ww)
        rp = float(np.corrcoef(yr, xr)[0, 1])
        rf1 = float(np.corrcoef(y_all.reindex(i).values, x_all.reindex(i).values)[0, 1])
        lengst = max([s for s in (k["u"], k["t"]) if s is not None], key=len)
        fg, fpar = fangst(LR[sid], lengst)
        rader[sid] = {"nf": len(i), "rf1": round(rf1, 3), "rp": round(rp, 3), "fangst": fg,
                      "bunner": [[b, round(x, 3), round(y, 3)] for b, x, y in fpar]}
        res[sid] = (i, yr, xr)
    kval = [s for s, r in rader.items() if r["rp"] >= RP_KRAV]
    par = []
    for a in range(len(kval)):
        for b in range(a + 1, len(kval)):
            s1, s2 = kval[a], kval[b]
            i = res[s1][0].intersection(res[s2][0])
            if len(i) < NF_KRAV:
                continue
            ww = dl(w).reindex(i).values
            # To raavarer som er samme faktor (Brent og WTI) er ikke en
            # kombinasjon. Korrelasjon over SAMME_FAKTOR i maanedsendringer:
            # paret telles ikke.
            rr = float(np.corrcoef(LR[s1].diff().reindex(i).values, LR[s2].diff().reindex(i).values)[0, 1])
            if rr > SAMME_FAKTOR:
                par.append({"par": [s1, s2], "r_samlet": None, "ok": False, "samme_faktor": round(rr, 2)})
                continue
            yr = rest(y_all.reindex(i).values, ww)
            X = np.column_stack([np.ones(len(i)),
                                 rest(LR[s1].diff().reindex(i).values, ww),
                                 rest(LR[s2].diff().reindex(i).values, ww)])
            fit = X @ np.linalg.lstsq(X, yr, rcond=None)[0]
            rj = float(np.sqrt(max(0.0, 1 - ((yr - fit) ** 2).sum() / ((yr - yr.mean()) ** 2).sum())))
            par.append({"par": [s1, s2], "r_samlet": round(rj, 3), "ok": rj >= RJ_KRAV})
    KART[fid] = {"navn": navn, "type": typ, "kilde": kilde, "ucits": k["ucits"], "tvilling": k["tvilling"],
                 "raavarer": rader, "kvalifisert": kval, "par": [p for p in par if p["ok"]], "alle_par": par}
    print(f"   {fid} ({navn}, maalt paa {kilde})")
    for sid, r in sorted(rader.items(), key=lambda x: -x[1]["rp"]):
        print(f"      {sid:10} rf1 {r['rf1']:+.2f}  rp {r['rp']:+.2f}  fangst fra bunner "
              f"{'-' if r['fangst'] is None else format(r['fangst'], '.2f'):>5} ({len(r['bunner'])} bunner)  "
              f"{'med' if sid in kval else ''}")
    for p in sorted(par, key=lambda p: -(p["r_samlet"] or 0)):
        if p.get("samme_faktor") is not None:
            print(f"      par {p['par'][0]}+{p['par'][1]}: samme faktor (raavarene korrelerer {p['samme_faktor']:.2f}), telles ikke")
        else:
            print(f"      par {p['par'][0]}+{p['par'][1]}: samlet {p['r_samlet']:.2f}  {'KVALIFISERER' if p['ok'] else ''}")
    print()


# ================================================================ del 2
def flaggserie(pars, kun_en=False):
    """Maanedsserie: regelen sann. kun_en=True: minst en av fondets
    raavarer i bunnsone (sammenligning)."""
    sids = sorted({s for p in pars for s in p})
    idx = None
    for s in sids:
        idx = STATUS[s].index if idx is None else idx.union(STATUS[s].index)
    if idx is None:
        return pd.Series(dtype=bool)
    st = {s: STATUS[s].reindex(idx).fillna(False) for s in sids}
    if kun_en:
        return pd.concat([st[s]["bunn"] for s in sids], axis=1).any(axis=1)
    ut = pd.Series(False, index=idx)
    for a, b in pars:
        ut |= st[a]["sone"] & st[b]["sone"] & (st[a]["bunn"] | st[b]["bunn"])
    return ut


def innslag(fl):
    ut, siste = [], None
    for t in fl.index[fl.values]:
        if siste is None or t.ordinal - siste.ordinal > M.PAUSE:
            ut.append(t)
        siste = t
    return ut


print("3. Historisk test av regelen (beskrivende)\n")
pst = lambda v: "   -  " if v is None or not np.isfinite(v) else f"{100 * (np.exp(v) - 1):+6.1f} %"
TEST, alle = {}, []
for fid, kv in KART.items():
    if not kv["par"]:
        continue
    k = KURS[fid]
    serie = max([s for s in (k["u"], k["t"]) if s is not None], key=len)
    lk = np.log(serie)
    TEST[fid] = {}
    for navn_v, kun_en in (("regelen", False), ("en_i_bunnsone", True)):
        fl = flaggserie([tuple(p["par"]) for p in kv["par"]], kun_en)
        rad = []
        for h in HORISONTER:
            f = (lk.shift(-h) - lk).dropna()
            snitt = f.mean()
            for t in innslag(fl):
                if t in f.index:
                    rad.append({"t": str(t), "h": h, "mer": float(f[t] - snitt), "abs": float(f[t])})
        TEST[fid][navn_v] = rad
        if navn_v == "regelen":
            alle += [(fid, r) for r in rad]
    for h in HORISONTER:
        rh = [r for r in TEST[fid]["regelen"] if r["h"] == h]
        eh = [r for r in TEST[fid]["en_i_bunnsone"] if r["h"] == h]
        print(f"   {fid:18} {h:2d} mnd  regelen: {len(rh)} innslag, "
              f"median mot snitt {pst(np.median([r['mer'] for r in rh]) if rh else None)}, "
              f"{sum(r['mer'] > 0 for r in rh)} positive   |   en i bunnsone: {len(eh)} innslag, "
              f"median {pst(np.median([r['mer'] for r in eh]) if eh else None)}, {sum(r['mer'] > 0 for r in eh)} positive")
    for t0 in sorted({r["t"] for r in TEST[fid]["regelen"]}):
        v = {r["h"]: r["mer"] for r in TEST[fid]["regelen"] if r["t"] == t0}
        print(f"      {t0}  " + "  ".join(f"{h} mnd {pst(v.get(h))}" for h in HORISONTER) + "  (mot fondets snitt)")
    print()

print("\n   Per kalenderepisode (innslag paa tvers av fond med hoeyst seks maaneder mellom):")
EPISODER = {}
for h in HORISONTER:
    e = sorted([(pd.Period(r["t"], "M"), fid, r["mer"]) for fid, r in alle if r["h"] == h])
    EPI, cur, siste = [], [], None
    for t0, fid, x in e:
        if siste is not None and t0.ordinal - siste.ordinal > 6:
            EPI.append(cur); cur = []
        cur.append((t0, fid, x)); siste = t0
    if cur:
        EPI.append(cur)
    EPISODER[h] = [{"fra": str(ep[0][0]), "til": str(ep[-1][0]), "fond": sorted({f for _, f, _ in ep}),
                    "median_mer": float(np.median([x for _, _, x in ep]))} for ep in EPI]
    print(f"   {h} mnd:")
    for ep in EPISODER[h]:
        print(f"      {ep['fra']} til {ep['til']}: {len(ep['fond'])} fond, median {pst(ep['median_mer'])}  ({', '.join(ep['fond'])})")
    print(f"      {sum(ep['median_mer'] > 0 for ep in EPISODER[h])} av {len(EPISODER[h])} episoder positive")

# ================================================================ del 3
print("\n4. Status i dag\n")
FORSLAG = {}
for fid, kv in KART.items():
    if not kv["par"]:
        continue
    sids = sorted({s for p in kv["par"] for s in p["par"]})
    naa = {s: {"sone": bool(STATUS[s]["sone"].iloc[-1]), "bunn": bool(STATUS[s]["bunn"].iloc[-1]),
               "A": round(float(SEG[s].A[-1]), 1), "Ad": round(float(SEG[s].Ad[-1]), 1)} for s in sids}
    fl = any(naa[a]["sone"] and naa[b]["sone"] and (naa[a]["bunn"] or naa[b]["bunn"]) for a, b in
             (p["par"] for p in kv["par"]))
    print(f"   {fid:18} {'FLAGG' if fl else '     '}  " +
          "  ".join(f"{s} A{naa[s]['A']:.0f}/{naa[s]['Ad']:.0f}{'*' if naa[s]['bunn'] else ('+' if naa[s]['sone'] else '')}"
                    for s in sids))
    FORSLAG[fid] = {"navn": kv["navn"], "type": kv["type"], "ucits": kv["ucits"], "maalt_paa": kv["kilde"],
                    "raavarer": {s: kv["raavarer"][s] for s in sids},
                    "par": [{"par": p["par"], "r_samlet": p["r_samlet"]} for p in kv["par"]]}
print("   (* bunnsone, + under oppsikt)")

os.makedirs("sonder", exist_ok=True)
json.dump({"kjort": time.strftime("%Y-%m-%d %H:%M:%S"), "kart": KART, "test": TEST, "episoder": EPISODER},
          open("sonder/fond_norge.json", "w"), ensure_ascii=False, indent=1, default=str)
json.dump(FORSLAG, open("sonder/fondkart_forslag_norge.json", "w"), ensure_ascii=False, indent=1)
print(f"\nLagret sonder/fond_norge.json og sonder/fondkart_forslag_norge.json ({len(FORSLAG)} fond med minst ett par)")
