# ---------------------------------------------------------------------------
# challenger_gull_begge_v1: BEGGE for gullgruvene (Frodes beslutning
# 29.10.2026). Registrert foer den ser nye data; endres aldri. En endret regel
# er en ny Challenger.
#
# BAKGRUNN (in-sample, holdt ikke): sju sonder paa gruvene (sonde_kjor_miners_*
# 28. og 29.10.2026) fant ingen regel som holdt paa 1993 til 2014. BEGGE kom
# naermest: 3 mnd p 0,048 paa kurven av gruveaksjer og ^XAU, men maaneder med
# bare S1 ga like mye. Etter 2015 +17,5 % mot -6,0 % over 6 mnd mot SPY.
# Challengeren skal avgjoere paa data som ikke er brukt i testingen.
#
# REGEL (segmentet gold, alle andre segmenter er Championens):
#   S1  endring i log(gull/Brent), nominelt, over 3 mnd i oeverste tredjedel
#       mot alle tidligere verdier (punkt i tid, minst 36 mnd).
#   S2  endring i olje-A over 6 mnd i oeverste tredjedel paa samme maate.
#       olje-A = (1 - persentil av log Brent realpris mot hele kjent
#       historikk, minst 60 mnd) x 100.
#   Maaned = siste maaned i serier/priser_mnd.csv der gull og Brent finnes.
#   watch        S1 eller S2
#   bottom_zone  S1 og S2 (BEGGE)
#   Papirer: Championens for gold (GDX.L, GJGB.L, SPGP.L), uendret.
#   Ny episode: Championens regel (minst 12 mnd uten signal). Evalueringen
#   bruker likevel maanedene med og uten BEGGE, se decision_rule.
#   Kan S1 eller S2 ikke regnes, settes signalene til NULL og feltet listes.
#
# Funksjonene er kopier av kontekst_miners.py per 29.10.2026, frosset her saa
# regelen ikke endres hvis dashbordkoden endres.
# ---------------------------------------------------------------------------

import io
import numpy as np
import pandas as pd

CID = "challenger_gull_begge_v1"
MIN_HIST, MIN_TOPP = 60, 36


def _expanding_pct(v):
    out = np.full(len(v), np.nan)
    for i in range(len(v)):
        if i + 1 >= MIN_HIST:
            out[i] = (v[: i + 1] <= v[i]).sum() / (i + 1)
    return out


def _toppen(serie, minn=MIN_TOPP):
    v = serie.values; ut = {}
    for i in range(len(v)):
        h = v[: i + 1]; h = h[np.isfinite(h)]
        if np.isfinite(v[i]) and len(h) >= minn:
            ut[str(serie.index[i])] = bool((h <= v[i]).mean() >= 2 / 3)
    return ut


def punkter(priser_csv):
    p = pd.read_csv(io.StringIO(priser_csv))

    def serie(seg, kol):
        s = p[p.segment == seg].set_index("t")[kol].astype(float)
        s.index = pd.PeriodIndex(s.index, freq="M"); return s.sort_index()
    gm = (np.log(serie("gold", "nom")) - np.log(serie("brent", "nom"))).dropna()
    ol = serie("brent", "real")
    oA = pd.Series((1 - _expanding_pct(np.log(ol.values))) * 100, index=ol.index)
    t1, t2 = _toppen((gm - gm.shift(3)).dropna()), _toppen((oA - oA.shift(6)).dropna())
    mnd = str(gm.index[-1])
    return mnd, t1.get(mnd), t2.get(mnd)


def snapshot(champion_rader, kontekst):
    try:
        mnd, s1, s2 = punkter(kontekst["les"]("serier/priser_mnd.csv"))
        mangler = [n for n, x in (("S1", s1), ("S2", s2)) if x is None]
    except Exception as e:
        mnd, s1, s2, mangler = None, None, None, [f"S1;S2 ({type(e).__name__})"]
    ok = not mangler
    ut = []
    for c in champion_rader:
        if c.get("segment") != "gold":
            continue
        rad = {k: (v if v != "" else None) for k, v in c.items()
               if k not in ("snapshot_id", "model_version", "run_id", "created_at", "code_changed")}
        if c.get("level") == "segment":
            rad.update({"watch": (s1 or s2) if ok else None, "bottom_zone": (s1 and s2) if ok else None,
                        "strong_candidate": None, "d95": None, "months_in_zone": None,
                        "observation_date": mnd, "missing_fields": ";".join(mangler) or None,
                        "data_stale": bool(mangler),
                        "source_version": (f"watch=S1 eller S2, bottom_zone=S1 og S2 ({mnd}): "
                                           f"S1 {'mangler' if s1 is None else ('på' if s1 else 'av')}, "
                                           f"S2 {'mangler' if s2 is None else ('på' if s2 else 'av')}")})
        ut.append(rad)
    return ut
