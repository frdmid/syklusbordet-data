# ---------------------------------------------------------------------------
# challenger_kull_ar95_v1: bunnflagg for kull fra rullende A (Frodes
# beslutning 14.10.2026). Registrert foer den ser nye data; endres aldri.
# En endret regel er en ny Challenger.
#
# BAKGRUNN (in-sample, ikke bevis): sonde_kjor_kull_flagg viste at
# Championens bunnsone nesten aldri slaar til for kull (en maaned, 2020-08),
# fordi raa A maales mot en serie fra 2000 med lave priser i starten og
# toppene 2008 og 2022. Rullende A (siste ti aar) 95 eller mer traff begge de
# store bunnene: 2015-10 (24 mnd +54 %) og 2020-05 (+183 %), 13 maaneder i
# alt. Bommet paa 2009 og 2025. Terskelen 95 er Frodes valg etter aa ha sett
# dataene, IKKE en testet regel, som d95 for Brent og WTI.
#
# REGEL (segmentet kull, alle andre segmenter er Championens):
#   bottom_zone  Championens A_rolling >= 95 OG A_detrended >= 80.
#                Ad-kravet kostet ingenting historisk (begge episodene hadde
#                Ad 99 til 100), men stenger for at en fallende trend leser
#                billig.
#   watch, B, C, D, d95 og papirer: Championens, uendret.
#   Ny episode: Championens regel (minst 12 mnd uten signal).
#   Mangler A_rolling eller A_detrended, settes bottom_zone til NULL.
# ---------------------------------------------------------------------------

CID = "challenger_kull_ar95_v1"
SEGMENTER = ("kull",)
AR_MIN, AD_MIN = 95, 80


def _tall(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def snapshot(champion_rader, kontekst):
    ut = []
    for c in champion_rader:
        if c.get("segment") not in SEGMENTER:
            continue
        rad = {k: (v if v != "" else None) for k, v in c.items()
               if k not in ("snapshot_id", "model_version", "run_id", "created_at", "code_changed")}
        if c.get("level") == "segment":
            ar, ad = _tall(c.get("A_rolling")), _tall(c.get("A_detrended"))
            mangler = [n for n, v in (("A_rolling", ar), ("A_detrended", ad)) if v is None]
            rad.update({"bottom_zone": None if mangler else (ar >= AR_MIN and ad >= AD_MIN),
                        "missing_fields": ";".join(mangler) or None, "data_stale": bool(mangler),
                        "source_version": "bottom_zone=A_rolling >= 95 og A_detrended >= 80 (Championens skaarer)"})
        ut.append(rad)
    return ut
