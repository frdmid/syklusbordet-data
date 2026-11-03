# ---------------------------------------------------------------------------
# kontekst_handel: handlingslisten og papirporteføljen til dashbordet (Frodes
# bestilling 03.11.2026, punkt 1, 3 og 8 i traderforslagene). Kontekst, ikke
# en modell: endrer ingen flagg og er ikke hashet av noen modell.
#
# HANDLINGSLISTEN: alle segmentene på bordet, sortert etter hvor nær de er
#   Championens bunnsone (A rå og A detrendet begge minst 80). avstand = det
#   som mangler på A rå pluss det som mangler på A detrendet, i poeng. Ved
#   siden av: hvilke signaler som står (Championens bunnsone, oppsikt og d95,
#   og Challengernes bunnsone eller watch fra siste snapshot), hver med
#   evidensgrad.
# EVIDENSGRAD (punkt 8):
#   sterk    holdt kravene satt før kjøring, og ikke motsagt senere
#   middels  holdt én gang, men ikke gjentatt; eller nær (klarte de fleste
#            kravene); eller sterk bare etter 2015
#   svak     holdt ikke, eller ikke testet som regel
# PAPIRPORTEFØLJEN (punkt 3):
#   Historisk (i utvalget): Championens regel spilt av fra segmentenes
#   månedsserie (2011-10 til nå): ny episode ved bunnsone etter minst 12 mnd
#   uten, inngang ved månedsslutt i flaggmåneden, holdt 24 mnd, likt vektet i
#   dagens kjøpbare papirer (ikke omvendte), i NOK. Hver åpen posisjon får
#   20 % (høyst fem), resten står i MSCI World (IWDA.L). Rebalanseres
#   månedlig. Samme regel bare i bred nedgang (40 % eller færre av råvarene
#   i oppgang), som challenger_bred_nedgang_v1. Papirene er valgt i 2026, så
#   historikken er skjev i papirenes favør.
#   Live: innganger fra Shadow-OOS (bottom_zone_enter som ny episode, alle
#   modeller), med avkastning til nå mot OSEBX og MSCI World.
# Skriver handel.json. Kalles fra shadow_challenger.kjor etter Challengerne.
# ---------------------------------------------------------------------------

import csv, io, json, time
import datetime as dt
import numpy as np
import pandas as pd
import requests

FIL = "handel.json"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0 Safari/537.36"}
HOLD, PAUSE, VEKT, MAKS = 24, 12, 0.20, 5
WORLD, OSEBX = "IWDA.L", "OSEBX.OL"

EVIDENS = {
    "bunnsone": ("Championens bunnsone", "middels",
                 "Råvaren har steget 6,2 % mot −1,5 % ellers over 12 mnd (1965 til 2014) og klarte alle krav unntatt "
                 "korreksjonen for mange tester. Papirene har gitt +25 % i median over 24 mnd, men under markedet, og "
                 "regelen holdt ikke før 2011."),
    "oppsikt": ("Oppsikt (bare A rå over 80)", "svak",
                "Rå A alene kunne ikke skilles fra tilfeldige kjøpsdatoer (2011 til 2026)."),
    "d95": ("Parallelt signal d95 (detrendet A 95)", "svak", "Holdt ikke i sonden d95. Frodes eget valg."),
    "challenger_bred_nedgang_v1": ("Bunnsone i bred nedgang", "middels",
                                   "+33 % mot −3 % over 24 mnd (15 makroklynger fra 1995, holdt), men valgt etter at "
                                   "regimesonden var kjent og ikke gjentatt på råvarens pris (sonden 03.11.2026)."),
    "challenger_gull_begge_v1": ("Gullgruver BEGGE", "middels",
                                 "Nær før 2015 (p 0,048 over 3 mnd, men måneder med bare S1 ga like mye), sterk etter "
                                 "2015 (+17,5 % mot −6,0 % over 6 mnd)."),
    "challenger_kull_ar95_v1": ("Kull, rullende A 95", "svak",
                                "To episoder, terskelen valgt etter å ha sett dataene, ikke testet som regel."),
    "challenger_laks_tilbud_v1": ("Laks, lav pris og krympende biomasse", "svak",
                                  "Delene er sett i data, flagget er ikke testet mot papirene."),
    "challenger_gass_rigger_v1": ("Henry Hub, bunnsone og færre gassrigger", "svak",
                                  "Riggene varsler produksjonen, men flagget er ikke testet mot papirene."),
    "challenger_olje_rigger_v1": ("Olje, bunnsone og færre oljerigger", "svak",
                                  "Riggene varsler produksjonen, men flagget er ikke testet mot papirene."),
}
NIVAA = {"sterk": "holdt kravene satt før kjøring, og ikke motsagt senere",
         "middels": "holdt én gang, men ikke gjentatt; nær; eller sterk bare etter 2015",
         "svak": "holdt ikke, eller ikke testet som regel"}

_kurs = {}


def _yahoo(sym):
    if sym in _kurs:
        return _kurs[sym]
    res = None
    for f in range(4):
        try:
            r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}",
                             params={"period1": 0, "period2": int(time.time()), "interval": "1d", "events": "div,split"},
                             headers=UA, timeout=60)
            res = r.json()["chart"]["result"][0]
            break
        except Exception:
            time.sleep(2 ** (f + 1))
    if res is None:
        raise RuntimeError(f"{sym}: ingen kurs")
    adj = res["indicators"].get("adjclose", [{}])[0].get("adjclose") or res["indicators"]["quote"][0]["close"]
    s = pd.Series(adj, index=pd.to_datetime(res["timestamp"], unit="s").normalize()).dropna()
    s = s[s > 0]; s = s[~s.index.duplicated(keep="last")]
    cur = res["meta"].get("currency") or "USD"
    if cur == "GBp":
        s, cur = s / 100, "GBP"
    if cur != "NOK":
        fx = _yahoo("NOK=X" if cur == "USD" else f"{cur}NOK=X")
        s = (s * fx.reindex(s.index, method="ffill")).dropna()
    time.sleep(0.25)
    _kurs[sym] = s
    return s


def _mnd(s):
    m = s.resample("ME").last(); m.index = m.index.to_period("M")
    return m


def _r(x, n=1):
    return None if x is None or not np.isfinite(x) else round(float(x), n)


def _csv(t):
    return list(csv.DictReader(io.StringIO(t))) if t else []


def _sann(v):
    return str(v).lower() in ("true", "1")


# ------------------------------------------------------------------ handlingslisten
def _signaler_naa(lager, segmenter):
    """{segment: [(id, tilstand)]} fra Championens segmentfiler og Challengernes siste snapshot."""
    ut = {s["id"]: [] for s in segmenter}
    for s in segmenter:
        sc, se = s.get("scores") or {}, s.get("series") or []
        if sc.get("flagg"):
            ut[s["id"]].append(("bunnsone", "bunnsone"))
        elif sc.get("oppsikt"):
            ut[s["id"]].append(("oppsikt", "watch"))
        if se and se[-1].get("flagg_d95"):
            ut[s["id"]].append(("d95", "bunnsone"))
    champ_watch = {s["id"]: bool((s.get("scores") or {}).get("oppsikt") or (s.get("scores") or {}).get("flagg"))
                   for s in segmenter}
    for f in lager.liste("config/challengers"):
        if not f.endswith(".json"):
            continue
        cid = f[:-5]
        uker = sorted(x for x in lager.liste(f"shadow/snapshots/{cid}") if x.endswith(".csv"))
        if not uker:
            continue
        for r in _csv(lager.les(f"shadow/snapshots/{cid}/{uker[-1]}")[0]):
            sid = r.get("segment")
            if r.get("level") != "segment" or sid not in ut:
                continue
            if _sann(r.get("bottom_zone")):
                ut[sid].append((cid, "bunnsone"))
            elif _sann(r.get("watch")) and not champ_watch.get(sid):
                ut[sid].append((cid, "watch"))
    return ut


def handlingsliste(lager, segmenter):
    sig = _signaler_naa(lager, segmenter)
    rader = []
    for s in segmenter:
        sc, tr = s.get("scores") or {}, s.get("trend") or {}
        A, Ad = sc.get("A"), sc.get("Ad")
        mangler, avstand = [], None
        if A is not None and Ad is not None:
            avstand = round(max(0, 80 - A) + max(0, 80 - Ad), 1)
            if A < 80:
                mangler.append(f"A rå {A:.1f} (mangler {80 - A:.1f})".replace(".", ","))
            if Ad < 80:
                mangler.append(f"A detrendet {Ad:.1f} (mangler {80 - Ad:.1f})".replace(".", ","))
        merk = []
        if sc.get("observasjon"):
            merk.append("observasjon, Championen har ikke flagg her")
        if sc.get("gate") == "stengt":
            merk.append("porten C er stengt")
        rader.append({"id": s["id"], "navn": s.get("name"), "A": _r(A), "Ad": _r(Ad), "Ar": _r(sc.get("Ar")),
                      "D": _r(sc.get("D")), "gate": sc.get("gate"), "trend": tr.get("signal"),
                      "observasjon": bool(sc.get("observasjon")), "avstand": avstand, "mangler": mangler,
                      "merknad": merk, "signaler": [{"id": i, "tilstand": t} for i, t in sig.get(s["id"], [])]})
    rader.sort(key=lambda r: (not r["signaler"], r["observasjon"], 999 if r["avstand"] is None else r["avstand"]))
    return rader


# ------------------------------------------------------------------ porteføljen
def _bredde(priser_csv):
    p = pd.read_csv(io.StringIO(priser_csv)); p = p[~p.segment.str.startswith("ship_")]
    real = p.pivot(index="t", columns="segment", values="real").astype(float).sort_index()
    real.index = pd.PeriodIndex(real.index, freq="M")
    d12 = np.log(real) - np.log(real.shift(12)); n = d12.notna().sum(axis=1)
    return ((d12 > 0).sum(axis=1) / n)[n >= 5]


def _episoder(flagg):
    """flagg: sortert liste av (Period, bool). Første flaggmåned etter minst 12 mnd uten."""
    ut, forr = [], None
    for t, f in flagg:
        if f:
            if forr is None or (t - forr).n > PAUSE:
                ut.append(t)
            forr = t
    return ut


def _kurv(tickere, note):
    m = {}
    for t in tickere:
        try:
            m[t] = _mnd(_yahoo(t))
        except Exception as e:
            note(f"   handel: {t} mangler ({type(e).__name__})")
    return pd.DataFrame(m)


def portefolje(segmenter, priser_csv, note=print):
    bredde = _bredde(priser_csv)
    world, osebx = _mnd(_yahoo(WORLD)), _mnd(_yahoo(OSEBX))
    naa = world.index[-1]
    pos = []
    for s in segmenter:
        if (s.get("scores") or {}).get("observasjon"):
            continue
        fl = [(pd.Period(r["t"], "M"), bool(r.get("flagg"))) for r in s.get("series") or []]
        pap = [i["ticker"] for i in s.get("instrumenter") or [] if i.get("handlbar") and not i.get("omvendt")]
        if not pap:
            continue
        reg = {"alle": _episoder(fl),
               "bred": _episoder([(t, f and bool(bredde.get(t, 1) <= 0.4)) for t, f in fl])}
        if not (reg["alle"] or reg["bred"]):
            continue
        K = _kurv(pap, note)
        for variant, starter in reg.items():
            for t0 in starter:
                if t0 not in K.index:
                    continue
                med = [c for c in K.columns if np.isfinite(K.loc[t0, c])]
                if not med:
                    continue
                t1 = min(t0 + HOLD, naa)
                v = (K[med].loc[t0:t1] / K[med].loc[t0]).mean(axis=1)     # kjøpt og holdt, likt vektet ved inngang
                pos.append({"variant": variant, "segment": s["id"], "navn": s.get("name"), "inngang": str(t0),
                            "utlop": str(t0 + HOLD), "apen": t0 + HOLD > naa, "papirer": med, "verdi": v})

    def avk(serie, a, b):
        if a not in serie.index or b not in serie.index:
            return None
        return _r(100 * (serie[b] / serie[a] - 1))

    start = osebx.index[0]
    ut = {}
    for variant in ("alle", "bred"):
        P = [p for p in pos if p["variant"] == variant]
        mnd = world.loc[start:].index
        nav, rad = 100.0, []
        for i, m in enumerate(mnd):
            if i:
                forr = mnd[i - 1]
                aapne = [p for p in P if p["verdi"].index[0] <= forr and forr < p["verdi"].index[-1]][:MAKS]
                rw = world[m] / world[forr] - 1
                r = (1 - VEKT * len(aapne)) * rw + sum(VEKT * (p["verdi"][m] / p["verdi"][forr] - 1) for p in aapne)
                nav *= 1 + r
            rad.append({"t": str(m), "nav": round(nav, 2), "n": len([p for p in P if p["verdi"].index[0] <= m < p["verdi"].index[-1]])})
        ut[variant] = rad
    w0, o0 = world[start], osebx[start]
    serie = [{"t": a["t"], "flagg": a["nav"], "bred": b["nav"], "n": a["n"],
              "world": round(100 * world[pd.Period(a["t"], "M")] / w0, 2),
              "osebx": round(100 * osebx[pd.Period(a["t"], "M")] / o0, 2) if pd.Period(a["t"], "M") in osebx.index else None}
             for a, b in zip(ut["alle"], ut["bred"])]
    poslist = []
    for p in sorted(pos, key=lambda p: (p["inngang"], p["segment"])):
        a, b = pd.Period(p["inngang"], "M"), p["verdi"].index[-1]
        poslist.append({"variant": p["variant"], "segment": p["segment"], "navn": p["navn"], "inngang": p["inngang"],
                        "utlop": p["utlop"], "apen": p["apen"], "papirer": p["papirer"],
                        "avk": _r(100 * (p["verdi"].iloc[-1] - 1)), "world": avk(world, a, b), "osebx": avk(osebx, a, b)})
    s1 = serie[-1]
    aar = (len(serie) - 1) / 12
    cagr = lambda x: _r(100 * ((x / 100) ** (1 / aar) - 1)) if aar > 0 else None
    return {"regel": f"Hver åpen posisjon får {int(VEKT * 100)} % (høyst {MAKS}), resten står i MSCI World. Inngang ved "
                     f"månedsslutt i flaggmåneden, holdt {HOLD} mnd, likt vektet i dagens papirer, i NOK.",
            "fra": serie[0]["t"], "serie": serie, "posisjoner": poslist,
            "aarlig": {"flagg": cagr(s1["flagg"]), "bred": cagr(s1["bred"]), "world": cagr(s1["world"]),
                       "osebx": cagr(s1["osebx"]) if s1["osebx"] else None}}


def live(lager, note=print):
    """Innganger fra Shadow-OOS: bottom_zone_enter som ny episode, alle modeller."""
    ut = []
    hend = [h for h in _csv(lager.les("shadow/shadow_events.csv")[0])
            if h.get("event") == "bottom_zone_enter" and str(h.get("new_episode")).lower() not in ("false", "0")
            and not h.get("instrument")]
    for h in hend:
        mod, dato, seg = h["model_version"], h["event_date"], h["segment"]
        mappe = f"shadow/snapshots/{mod}"
        uke = h.get("iso_week")
        rader = _csv(lager.les(f"{mappe}/{uke}.csv")[0])
        pap = [r["instrument"] for r in rader if r.get("segment") == seg and r.get("level") == "instrument"
               and _sann(r.get("instrument_eligible")) and not _sann(r.get("inverse"))]
        d0 = pd.Timestamp(dato)

        def fra(sym):
            s = _yahoo(sym); s = s[s.index >= d0]
            return None if s.empty else 100 * (s.iloc[-1] / s.iloc[0] - 1)
        verdier = []
        for t in pap:
            try:
                x = fra(t)
                if x is not None:
                    verdier.append(x)
            except Exception as e:
                note(f"   handel: {t} mangler ({type(e).__name__})")
        ut.append({"modell": mod, "segment": seg, "inngang": dato,
                   "utlop": str((d0 + pd.DateOffset(months=HOLD)).date()), "papirer": pap,
                   "avk": _r(np.mean(verdier)) if verdier else None, "world": _r(fra(WORLD)), "osebx": _r(fra(OSEBX))})
    return ut


def beregn(lager, note=print):
    idx = json.loads(lager.les("index.json")[0] or "{}")
    segmenter = []
    for sid in idx.get("segmenter") or []:
        t = lager.les(f"segments/{sid}.json")[0]
        if t:
            segmenter.append(json.loads(t))
    ut = {"id": "handel", "oppdatert": dt.date.today().isoformat(),
          "mnd": max((s["series"][-1]["t"] for s in segmenter if s.get("series")), default=None),
          "evidens": {"nivaa": NIVAA, "signaler": {k: {"navn": v[0], "grad": v[1], "grunn": v[2]} for k, v in EVIDENS.items()}},
          "liste": handlingsliste(lager, segmenter)}
    try:
        ut["live"] = live(lager, note)
    except Exception as e:
        ut["live"] = None
        note(f"   handel: live feilet ({type(e).__name__}: {str(e)[:60]})")
    try:
        ut["portefolje"] = portefolje(segmenter, lager.les("serier/priser_mnd.csv")[0], note)
    except Exception as e:
        ut["portefolje"] = None
        note(f"   handel: portefølje feilet ({type(e).__name__}: {str(e)[:60]})")
    return ut


def kjor(lager, note=print):
    try:
        tekst = json.dumps(beregn(lager, note), ensure_ascii=False, indent=1) + "\n"
        t, sha = lager.les(FIL)
        if t is None:
            lager.opprett(FIL, tekst)
        elif t != tekst:
            lager.erstatt(FIL, tekst, sha)
        note(f"   kontekst {FIL}: skrevet")
    except Exception as e:
        note(f"   kontekst {FIL} feilet: {type(e).__name__}: {str(e)[:80]}")


if __name__ == "__main__":
    import os
    import shadow_oos as so
    rot = os.path.dirname(os.path.abspath(__file__))
    ut = beregn(so.LokalLager(rot, rot))
    json.dump(ut, open(FIL, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for r in ut["liste"][:8]:
        print(r["id"], r["avstand"], r["mangler"], r["signaler"], r["merknad"])
    pf = ut["portefolje"]
    if pf:
        print(pf["fra"], pf["serie"][-1], pf["aarlig"])
        for p in pf["posisjoner"]:
            print(p)
    print("live", ut["live"])
