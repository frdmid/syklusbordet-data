# ---------------------------------------------------------------------------
# kontekst_miners: feltet «Gullgruver» på dashbordet (Frodes bestilling
# 28.10.2026, etter sonde_kjor_gullgruver, sonde_kjor_miners_a og
# sonde_kjor_miners_feilpris). Observasjon, ikke flagg, og ikke shadow-data.
#
# Skriver miners.json i samme format som et segment, slik at dashbordet viser
# det som et vanlig panel (samlingen segments, dokument «miners»). Fila ligger
# i roten og IKKE i segments/, så Championens skript (shadow_oos, endringer,
# helse) aldri plukker den opp.
#
# Innhold:
#   SERIEN    gull (nominell USD/unse) delt på WTI (USD/fat), månedlig fra
#             serier/priser_mnd.csv: hvor mange fat olje en unse gull kjøper.
#             Forholdet er realt i seg selv, så real = nom.
#   A, Ad, Ar samme formler som bordet (priser.py), på log(forholdet). Høy A =
#             gull billig mot olje. Bunnsonen holdt IKKE i sonde_kjor_miners_a
#             (6 klynger, median -14 % for ^XAU), så feltet har ingen flagg.
#   SIGNAL    ingen (fra 29.10.2026, Frodes beslutning). Kombinasjonen av
#             gull mot olje og olje-A (28.10) og K1 (29.10) er tatt ut: ingen
#             av dem holdt på 1993 til 2014, og heller ikke variantene med
#             rekkelengde, forsinkelse, rullende A eller ekstrem olje
#             (sondene sonde_kjor_miners_*).
#   PUNKTENE  sig1 og sig2 i serien (Frodes ønske 29.10.2026, som i v70 og
#             v71): måneder der S1 (endring i log(gull/Brent) siste 3 mnd) og
#             S2 (endring i olje-A siste 6 mnd) var i øverste tredjedel mot det
#             som var kjent da. Månedssnitt, som i sondene. Vises, er ikke signal.
#   REGIMET   gull siste 6 mnd (over +5 % stigende, under -5 % fallende).
#   PAPIRENE  UCITS-fondene i USD: GDX.L, GDXJ.L, IAUP.L, AUCO.L. D med samme
#             formel som kapitulasjon_d.py (kopiert, ikke importert, fordi den
#             fila kjører ved import), segmentets D = median av papirene. C er
#             «uaktuell»: fond har ingen balanse.
#
# Kalles hver uke fra shadow_challenger.kjor (som kontekst_laks, _regime og
# _uran). Ikke med i Championens frosne filer eller i noen Challengers kode.
# Onsdagsrutinen skriver fila til segments/miners (steg 6k).
# ---------------------------------------------------------------------------

import datetime as dt
import io
import json
import time
import numpy as np
import pandas as pd
import requests

from signaler import trend

FIL = "miners.json"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
MIN_HIST, TOPPVINDU, FULLT_FALL, VIS_MND = 60, 60, 30, 180
PAPIRER = [
    ("GDX.L", "VanEck Gold Miners UCITS", "Store gruver. Samme uke: beta mot gull 1,8, mot olje 0,0 (sonden 28.10.2026)."),
    ("GDXJ.L", "VanEck Junior Gold Miners UCITS", "Små gruver. Beta mot gull 1,9, mot olje 0,0. Svinger mest."),
    ("IAUP.L", "iShares Gold Producers UCITS", "Store produsenter. Beta mot gull 1,7, mot olje 0,0."),
    ("AUCO.L", "L&G Gold Mining UCITS", "Blandet størrelse, fra 2008. Beta mot gull 1,7, mot olje 0,0."),
]


# ---------------------------------------------------- A (som priser.py)
def _expanding_pct(v):
    out = np.full(len(v), np.nan)
    for i in range(len(v)):
        if i + 1 >= MIN_HIST:
            out[i] = (v[: i + 1] <= v[i]).sum() / (i + 1)
    return out


def _detrend(v, minn=60):
    out = np.full(len(v), np.nan)
    for i in range(minn - 1, len(v)):
        y = v[: i + 1]; t = np.arange(i + 1)
        b, a = np.polyfit(t, y, 1); r = y - (a + b * t)
        out[i] = (r <= r[i]).sum() / len(r)
    return (1 - out) * 100


def _rolling(v, w=120, minn=60):
    out = np.full(len(v), np.nan)
    for i in range(len(v)):
        lo = max(0, i - w + 1)
        if i - lo + 1 >= minn:
            y = v[lo: i + 1]; out[i] = (y <= v[i]).sum() / len(y)
    return (1 - out) * 100


def _bands(v, qs=(10, 25, 50, 75, 90)):
    res = {q: np.full(len(v), np.nan) for q in qs}
    for i in range(len(v)):
        if i + 1 >= MIN_HIST:
            for q in qs:
                res[q][i] = np.percentile(v[: i + 1], q)
    return res


# ---------------------------------------------------- D (som kapitulasjon_d.py)
def _dagskurs(sym):
    r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}",
                     params={"period1": 0, "period2": int(time.time()), "interval": "1d", "events": "div,split"},
                     headers=UA, timeout=60)
    r.raise_for_status()
    res = r.json()["chart"]["result"][0]
    if (res.get("meta") or {}).get("dataGranularity") != "1d":
        raise ValueError("ikke dagskurser")
    tz = (res.get("meta") or {}).get("exchangeTimezoneName") or "UTC"
    idx = pd.to_datetime(res["timestamp"], unit="s", utc=True).tz_convert(tz).normalize().tz_localize(None)
    adj = ((res["indicators"].get("adjclose") or [{}])[0] or {}).get("adjclose")
    s = pd.Series(adj if adj else res["indicators"]["quote"][0]["close"], index=idx, dtype=float).dropna()
    time.sleep(0.3)
    return s[~s.index.duplicated(keep="last")]


def _exp_pct(v, minn=MIN_HIST):
    v = np.asarray(v, float); out = np.full(len(v), np.nan)
    for i in range(len(v)):
        if i + 1 >= minn and not np.isnan(v[i]):
            h = v[: i + 1]; h = h[~np.isnan(h)]
            if len(h) >= minn:
                out[i] = (1 - (h <= v[i]).sum() / len(h)) * 100
    return out


def _d(daglig):
    m = daglig.resample("ME").last().dropna(); m.index = m.index.to_period("M")
    topp = m.rolling(TOPPVINDU, min_periods=12).max()
    fall = (m / topp - 1) * 100
    ma = daglig.rolling(200, min_periods=120).mean()
    uke = (daglig < ma).resample("W").last().dropna().astype(float)
    a = (uke.rolling(52, min_periods=26).mean() * 100).resample("ME").last()
    a.index = a.index.to_period("M"); a = a.reindex(fall.index)
    d = np.nanmean(np.vstack([_exp_pct(fall.values), _exp_pct(-a.values)]), axis=0)
    d = d * np.clip(np.abs(fall.values) / FULLT_FALL, 0, 1)
    i = len(d) - 1
    while i >= 0 and np.isnan(d[i]):
        i -= 1
    return None if i < 0 else (round(float(d[i]), 1), round(float(fall.values[i]), 1))


def _toppen(serie, minn=36):
    """Sann der verdien er i øverste tredjedel mot det som var kjent da."""
    v = serie.values; ut = {}
    for i in range(len(v)):
        h = v[: i + 1]; h = h[np.isfinite(h)]
        if np.isfinite(v[i]) and len(h) >= minn:
            ut[str(serie.index[i])] = bool((h <= v[i]).mean() >= 2 / 3)
    return ut


def _r(x, n=1):
    return None if x is None or not np.isfinite(x) else round(float(x), n)


def beregn(priser_csv, idag=None, note=print):
    p = pd.read_csv(io.StringIO(priser_csv))
    def serie(seg):
        s = p[p.segment == seg].set_index("t").nom.astype(float)
        s.index = pd.PeriodIndex(s.index, freq="M"); return s.sort_index()
    f = (serie("gold") / serie("wti")).dropna()
    lv = np.log(f.values)
    A = (1 - _expanding_pct(lv)) * 100
    Ad, Ar = _detrend(lv), _rolling(lv)
    bands = _bands(f.values)
    serie_ut = []
    for i in range(max(0, len(f) - VIS_MND), len(f)):
        serie_ut.append({"t": str(f.index[i]), "nom": round(float(f.iloc[i]), 3), "real": round(float(f.iloc[i]), 3),
                         **{f"p{q}": _r(bands[q][i], 3) for q in bands},
                         "A": _r(A[i]), "Ad": _r(Ad[i]), "Ar": _r(Ar[i]), "flagg": False, "oppsikt": False})
    tr = trend(serie_ut)
    b, _ = np.polyfit(np.arange(len(lv)), lv, 1)

    # punktene S1 og S2 i grafen (vises, er ikke signal)
    gm = np.log(serie("gold")) - np.log(serie("brent"))
    ol = p[p.segment == "brent"].set_index("t").real.astype(float)
    ol.index = pd.PeriodIndex(ol.index, freq="M"); ol = ol.sort_index()
    oA = pd.Series((1 - _expanding_pct(np.log(ol.values))) * 100, index=ol.index)
    t1, t2 = _toppen((gm - gm.shift(3)).dropna()), _toppen((oA - oA.shift(6)).dropna())
    for pt in serie_ut:
        if pt["t"] in t1:
            pt["sig1"] = t1[pt["t"]]
        if pt["t"] in t2:
            pt["sig2"] = t2[pt["t"]]
    sist = lambda d: max([t for t, x in d.items() if x], default=None)
    punkter = {"mnd1": max(t1), "sig1": t1[max(t1)], "sist_sig1": sist(t1),
               "mnd2": max(t2), "sig2": t2[max(t2)], "sist_sig2": sist(t2)}

    # gullregime i sanntid (sonde_kjor_miners_gullregime): gull siste 6 mnd, ±5 %
    g6 = np.log(serie("gold")); g6 = (g6 - g6.shift(6)).dropna()
    regime = {"mnd": str(g6.index[-1]), "gull_6m_pst": _r(100 * (np.exp(g6.iloc[-1]) - 1)),
              "regime": "stigende" if g6.iloc[-1] > np.log(1.05) else ("fallende" if g6.iloc[-1] < -np.log(1.05) else "stabil")}

    # papirene og D
    instr, dverdier = [], []
    for tk, navn, kom in PAPIRER:
        rad = {"ticker": tk, "bors": "London", "navn": navn, "type": "ETF", "kommentar": kom,
               "omvendt": False, "handlbar": True, "D": None, "fall_pst": None}
        try:
            r = _d(_dagskurs(tk))
            if r:
                rad["D"], rad["fall_pst"] = r
                dverdier.append(r[0])
        except Exception as e:
            note(f"   miners: {tk} uten D ({type(e).__name__})")
        instr.append(rad)
    Dseg = _r(float(np.median(dverdier))) if dverdier else None

    siste = serie_ut[-1]
    return {
        "id": "miners", "name": "Gullgruver (gull mot olje)", "group": "Metall",
        "unit": "fat olje per unse gull", "status": "live", "laget": str(idag or dt.date.today()),
        "note": ("Forholdet mellom gullpris og oljepris, et grovt mål på gruvenes margin. Observasjon uten flagg: "
                 "bunnsonen på dette forholdet holdt ikke (sonden 28.10.2026), og heller ikke feilprising av "
                 "gruvene mot gull og olje, og ingen av signalene som ble testet."),
        "source": "Gull, WTI og Brent fra serier/priser_mnd.csv (Verdensbanken og GitHub-speil)",
        "source_url": "https://github.com/frdmid/syklusbordet-data/blob/main/kontekst_miners.py",
        "hist_start": str(f.index[0]), "last_obs": siste["t"], "last_nom": siste["nom"], "last_real": siste["real"],
        "trend_pst_aar": _r(100 * (np.exp(b * 12) - 1), 2),
        "scores": {"A": siste["A"], "Ad": siste["Ad"], "Ar": siste["Ar"], "flagg": False, "oppsikt": False,
                   "A2": None, "B": None, "D": Dseg, "S": None, "gate": "uaktuell", "months_in_zone": 0,
                   "observasjon": True,
                   "observasjon_grunn": ("Gullgruvene har ikke flagg. Bunnsonen på gull mot olje ga median -14 % for "
                                         "gruveindeksen over 24 mnd (6 klynger, sonden 28.10.2026). Ingen signal: "
                                         "ingen av de testede signalene holdt på 1993 til 2014.")},
        "series": serie_ut, "trend": tr,
        "instrumenter": instr,
        "d_detalj": {"D_aksjer": Dseg, "tema": None, "tema_D": None, "tema_navn": None, "n": len(dverdier),
                     "spredning": [min(dverdier), max(dverdier)] if dverdier else None},
        "gate_detalj": {"aapne": 0, "malte": 0},
        "miners": {"regime": regime, "signal": None, "punkter": punkter,
                   "tester": ("Testet på gruveaksjer 1993 til 2014, før signalene ble funnet: kombinasjonen av gull mot olje "
                              "og olje-A, K1 med krav til rekkelengde, varianter med forsinkelse og rullende A, og ekstremt "
                              "billig olje eller oljekrakk. Ingen holdt. Billig olje ga svakere gruver, ikke sterkere."),
                   "kilde": "sondene sonde_kjor_miners_* 28. og 29.10.2026"},
    }


def kjor(lager, note=print):
    try:
        priser = lager.les("serier/priser_mnd.csv")[0]
        tekst = json.dumps(beregn(priser, note=note), ensure_ascii=False, indent=1) + "\n"
        t, sha = lager.les(FIL)
        if t is None:
            lager.opprett(FIL, tekst)
        elif t != tekst:
            lager.erstatt(FIL, tekst, sha)
        note(f"   kontekst {FIL}: skrevet")
    except Exception as e:
        note(f"   kontekst {FIL} feilet: {type(e).__name__}: {str(e)[:80]}")


if __name__ == "__main__":
    ut = beregn(open("serier/priser_mnd.csv", encoding="utf-8").read())
    json.dump(ut, open(FIL, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in ut.items() if k not in ("series",)}, ensure_ascii=False, indent=1)[:2500])
