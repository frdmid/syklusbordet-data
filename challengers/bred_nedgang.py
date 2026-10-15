# ---------------------------------------------------------------------------
# challenger_bred_nedgang_v1: bunnsone bare i bred nedgang (Frodes beslutning
# 15.10.2026). Registrert foer den ser nye data; endres aldri. En endret
# regel er en ny Challenger.
#
# BAKGRUNN (in-sample, en utvidelse etter at regimesonden var kjent):
# sonde_kjor_regime_flagg viste at Championens bunnflagg siden 1995 ga +33 %
# i realpris over 24 mnd naar de kom mens 40 % eller faerre av raavarene var i
# oppgang, mot -3 % ellers (10 mot 5 makroklynger, p 0,033, gjennom
# Benjamini-Hochberg). Etter 2010 har gruppen uten bred nedgang bare en
# klynge. Paa 1 til 12 mnd holdt det ikke (sonde_kjor_regime_horisont).
#
# REGEL (alle segmenter):
#   bredde       andel av raavaresegmentene i serier/priser_mnd.csv (alt som
#                ikke starter med ship_) med hoeyere realpris enn 12 mnd
#                foer, i siste maaned i fila; samme maal som regimepanelet.
#   bottom_zone  Championens bottom_zone OG bredde <= 0,4.
#   watch, B, C, D, d95, papirer og alt annet: Championens, uendret.
#   Ny episode: Championens regel (minst 12 mnd uten signal).
#   Kan bredden ikke regnes, settes bottom_zone til NULL og feltet listes.
# ---------------------------------------------------------------------------

import io
import numpy as np
import pandas as pd

CID = "challenger_bred_nedgang_v1"
GRENSE = 0.4


def bredde(priser_csv):
    p = pd.read_csv(io.StringIO(priser_csv))
    p = p[~p.segment.str.startswith("ship_")]
    real = p.pivot(index="t", columns="segment", values="real").astype(float).sort_index()
    real.index = pd.PeriodIndex(real.index, freq="M")
    d12 = np.log(real) - np.log(real.shift(12))
    n = d12.notna().sum(axis=1)
    b = ((d12 > 0).sum(axis=1) / n)[n > 0]
    return float(b.iloc[-1]), str(b.index[-1])


def snapshot(champion_rader, kontekst):
    try:
        b, mnd = bredde(kontekst["les"]("serier/priser_mnd.csv"))
        mangler = []
    except Exception as e:
        b, mnd, mangler = None, None, [f"bredde ({type(e).__name__})"]
    ut = []
    for c in champion_rader:
        rad = {k: (v if v != "" else None) for k, v in c.items()
               if k not in ("snapshot_id", "model_version", "run_id", "created_at", "code_changed")}
        if c.get("level") == "segment":
            bz = str(c.get("bottom_zone")).lower()
            champ = None if bz not in ("true", "false") else bz == "true"
            rad.update({"bottom_zone": None if (b is None or champ is None) else (champ and b <= GRENSE),
                        "missing_fields": ";".join(mangler) or None, "data_stale": bool(mangler),
                        "source_version": (f"bottom_zone=Championens bottom_zone og bredde <= 0,4; bredde "
                                           f"{'mangler' if b is None else f'{b:.3f}'} ({mnd})")})
            if mnd:
                rad["observation_date"] = mnd
        ut.append(rad)
    return ut
