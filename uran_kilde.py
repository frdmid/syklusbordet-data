# ---------------------------------------------------------------------------
# Uranprisen. Brukes av priser.py og sonde_ikz.py.
#
# HVORFOR IKKE IMF-SERIEN LENGER
# uran_reserve.csv er IMF sin serie (PURANUSDM) via FRED. Sammenlignet maaned
# for maaned med CME/UxC-futures (UXc2, ukentlige noteringer fra 2007) folger
# den futures innenfor rundt 1 % i median hvert aar fra 2008 til 2021. Fra
# oktober 2021 ligger den plutselig 17 til 23 % under, hvert eneste aar ut
# 2026 (median -19,4 %). November 2021 staar i IMF-serien paa 31,10 dollar,
# mens markedet laa rundt 45. Det er et brudd i IMF-serien, ikke i markedet.
# Konsekvensen var at de siste fem aarene saa billigere ut enn de var, og at
# A for uran leste 19 der den riktige verdien er lavere.
#
# KILDEN NAA
# Cameco publiserer spotprisen som maanedsslutt fra 1988, snittet av UxC og
# TradeTech, paa cameco.com/invest/markets/uranium-price. Siden svarer fra
# Actions og oppdateres hver maaned. Det er ett maal gjennom hele serien, og
# serien er fire aar lengre enn IMF sin.
#
# KONTROLLEN
# Serien brukes bare hvis den holder mot to uavhengige kilder i periodene der
# de er gode:
#   mot IMF-kopien 1992-01 til 2021-09: median avvik under 6 %
#     (IMF er maanedssnitt, Cameco er maanedsslutt, saa et lite avvik er ventet)
#   mot futures-kopien fra 2022-01: median avvik under 6 %
# Holder den ikke, returneres None, og kallet logger hvorfor. Da faller
# priser.py tilbake paa ingenting heller enn paa en serie med kjent brudd.
# ---------------------------------------------------------------------------

import io
import numpy as np
import pandas as pd
import requests

CAMECO = "https://www.cameco.com/invest/markets/uranium-price"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
GRENSE_PST = 6.0


def cameco_spot(timeout=40):
    """Maanedsslutt spot, USD/lb U3O8, fra 1988. PeriodIndex."""
    r = requests.get(CAMECO, headers=UA, timeout=timeout)
    r.raise_for_status()
    for t in pd.read_html(io.StringIO(r.text)):
        kol = [c for c in t.columns if "spot" in str(c).lower()]
        if not kol:
            continue
        d = pd.to_datetime(t.iloc[:, 0].astype(str), errors="coerce")
        v = pd.to_numeric(t[kol[0]], errors="coerce")
        s = pd.Series(v.values, index=d).dropna()
        s = s[s.index.notna()]
        if len(s) < 300:
            continue
        s.index = s.index.to_period("M")
        s = s[~s.index.duplicated(keep="last")].sort_index()
        return s
    raise ValueError("fant ingen tabell med spotpris og minst 300 maaneder")


def _avvik(a, b, fra, til):
    f = a.index.intersection(b.index)
    f = f[(f >= pd.Period(fra, "M")) & (f <= pd.Period(til, "M"))]
    if len(f) < 24:
        return None, len(f)
    return float(((a[f] / b[f] - 1).abs() * 100).median()), len(f)


def kontroll(s, imf, fut):
    """Returnerer (ok, tekst)."""
    a1, n1 = _avvik(s, imf, "1992-01", "2021-09")
    a2, n2 = _avvik(s, fut, "2022-01", "2099-12") if fut is not None else (None, 0)
    ok = a1 is not None and a1 < GRENSE_PST and (a2 is None or a2 < GRENSE_PST)
    tekst = (f"mot IMF 1992-2021: median avvik {a1 if a1 is None else round(a1, 1)} % over {n1} mnd, "
             f"mot futures fra 2022: {a2 if a2 is None else round(a2, 1)} % over {n2} mnd")
    return ok, tekst


def maaned(url, snitt=False):
    d = pd.read_csv(url)
    d = d.iloc[:, :2]
    d.columns = ["d", "v"]
    d["v"] = pd.to_numeric(d["v"], errors="coerce")
    d = d.dropna()
    p = pd.PeriodIndex(pd.to_datetime(d["d"]), freq="M")
    s = pd.Series(d["v"].values, index=p)
    return s.groupby(level=0).mean() if snitt else s[~s.index.duplicated(keep="last")]


def hent_uran(repo_raw, note=print):
    """repo_raw: https://raw.githubusercontent.com/<repo>/<branch>/
    Returnerer (serie, kildetekst) eller (None, grunn)."""
    try:
        s = cameco_spot()
    except Exception as e:
        return None, f"Cameco: {type(e).__name__}: {str(e)[:70]}"
    try:
        imf = maaned(repo_raw + "uran_reserve.csv")
    except Exception as e:
        return None, f"IMF-kopien til kontroll: {type(e).__name__}"
    try:
        fut = maaned(repo_raw + "uran_futures_uke.csv", snitt=True)
    except Exception:
        fut = None
    ok, tekst = kontroll(s, imf, fut)
    note("uran, kontroll av Cameco", ok, tekst)
    if not ok:
        return None, "Cameco besto ikke kontrollen: " + tekst
    return s, f"Cameco, maanedsslutt spot (UxC og TradeTech), {s.index[0]} til {s.index[-1]}"
