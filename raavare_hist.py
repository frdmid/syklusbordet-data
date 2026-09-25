# ---------------------------------------------------------------------------
# raavare_hist: hele realprishistorikken for raavaresegmentene, slik bordet
# ser den, til bruk i sondene.
#
# Segmentfilene i repoet har bare grafvinduet fra 2011-09. Terskeltesten og
# timingtesten trenger hele historikken tilbake til 1960. I stedet for aa
# kopiere kildelesingen kjoeres priser.py sin egen kode fram til og med
# raavarene (del 1 til 3), med en endring: legg_til tar vare paa serien i
# stedet for aa bygge segmentet. Da er seriene noyaktig de samme som bordet
# bruker, med samme kilder, samme avkorting og samme uranserie. Endres
# priser.py, foelger dette med.
#
# Ingenting skrives til repoet: GITHUB_TOKEN tommes foer koden kjoeres.
#
# To raske versjoner av persentilfunksjonene ligger her ogsaa. Originalene i
# priser.py tilpasser en ny trend for hver maaned med polyfit, og det er for
# tregt naar nullfordelingen skal regnes paa nytt flere hundre ganger. De raske
# gir samme tall, og hent() kontrollerer det paa de ekte seriene hver gang.
# ---------------------------------------------------------------------------

import ast, os
import numpy as np
import pandas as pd

KUTT = 'print("\\n4. Magasinfylling'
GAMMEL = "def legg_til(seg_id, navn, gruppe, enhet, serie, cpi, kilde, url, merknad=None):"


def pct_raa(lr, min_hist=60):
    """Samme som (1 - expanding_pct(lr)) * 100 i priser.py."""
    v = np.asarray(lr, float)
    n = len(v)
    le = (v[None, :] <= v[:, None]) & np.tri(n, dtype=bool)
    ut = le.sum(1) / np.arange(1, n + 1)
    ut[: min_hist - 1] = np.nan
    return (1 - ut) * 100


def pct_det(lr, minn=60):
    """Samme som expanding_pct_detrend(lr) i priser.py.

    For hver maaned i tilpasses en linje paa 0..i. Residualet for j er
    y_j - a_i - b_i*j, og persentilen teller j <= i med residual <= residualet
    for i. a_i faller bort i sammenligningen, saa bare b_i trengs, og den
    faas fra kumulative summer."""
    y = np.asarray(lr, float)
    n = len(y)
    t = np.arange(n, dtype=float)
    m = np.arange(1, n + 1, dtype=float)
    St, Sy = np.cumsum(t), np.cumsum(y)
    Stt, Sty = np.cumsum(t * t), np.cumsum(t * y)
    nev = m * Stt - St * St
    with np.errstate(invalid="ignore", divide="ignore"):
        b = (m * Sty - St * Sy) / nev
    # r_j - r_i = (y_j - y_i) - b_i (j - i)
    D = (y[None, :] - y[:, None]) - b[:, None] * (t[None, :] - t[:, None])
    le = (D <= 1e-12) & np.tri(n, dtype=bool)
    ut = le.sum(1) / m
    ut[: minn - 1] = np.nan
    return (1 - ut) * 100


def hent(fil="priser.py", kontroll=True):
    """Returnerer (REAL, NOM, cpi): dict segment -> log realpris og nominell
    pris som maanedsserier, og deflatoren."""
    os.environ["GITHUB_TOKEN"] = ""
    src = open(fil, encoding="utf-8").read()
    k = src.find(KUTT)
    if k < 0 or src.count(GAMMEL) != 1:
        raise SystemExit("raavare_hist: priser.py har endret form (fant ikke kuttpunktet "
                         "eller legg_til). Send utskriften til Claude.")
    ny = (GAMMEL + "\n    _RAA[seg_id] = serie.copy()\n    return None\n\n"
          + GAMMEL.replace("def legg_til", "def _legg_til_ubrukt"))
    src = src[:k].replace(GAMMEL, ny)
    ns = {"__name__": "raavare_hist_priser", "_RAA": {}}
    exec(compile(src, fil, "exec"), ns)
    cpi = ns["cpi"]
    REAL, NOM = {}, {}
    for sid, nom in ns["_RAA"].items():
        # noyaktig som build_segment i priser.py
        nom = nom.dropna().sort_index()
        real = (nom * (cpi.dropna().iloc[-1] / cpi.reindex(nom.index).ffill())).dropna()
        REAL[sid] = np.log(real)
        NOM[sid] = nom.reindex(real.index)

    if kontroll:
        P = _originaler(fil)
        avvik = []
        for sid, lr in REAL.items():
            a0 = (1 - P["expanding_pct"](lr.values)) * 100
            d0 = P["expanding_pct_detrend"](lr.values)
            a1, d1 = pct_raa(lr.values), pct_det(lr.values)
            fa = np.nanmax(np.abs(a0 - a1)) if np.isfinite(a0).any() else 0
            fd = np.nanmax(np.abs(d0 - d1)) if np.isfinite(d0).any() else 0
            if not (np.array_equal(np.isnan(a0), np.isnan(a1)) and np.array_equal(np.isnan(d0), np.isnan(d1))) \
                    or fa > 1e-6 or fd > 1e-6:
                avvik.append(f"{sid} (raa {fa:.4f}, detrendet {fd:.4f})")
        print(f"   kontroll av de raske persentilfunksjonene mot priser.py: "
              f"{'like paa alle ' + str(len(REAL)) + ' serier' if not avvik else 'AVVIK: ' + ', '.join(avvik)}")
        if avvik:
            raise SystemExit("De raske funksjonene gir ikke samme tall som priser.py. Send utskriften til Claude.")
    return REAL, NOM, cpi


def _originaler(fil):
    t = ast.parse(open(fil, encoding="utf-8").read())
    kropp = [n for n in t.body if isinstance(n, ast.FunctionDef)
             and n.name in ("expanding_pct", "expanding_pct_detrend")]
    ns = {"np": np, "MIN_HIST": 60}
    exec(compile(ast.Module(body=kropp, type_ignores=[]), fil, "exec"), ns)
    return ns
