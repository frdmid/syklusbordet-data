# ---------------------------------------------------------------------------
# challenger_laks_adar_v1: bunnflagg for laks fra detrendet og rullende A
# (Frodes beslutning 25.11.2026). Registrert foer den ser nye data; endres
# aldri. En endret regel er en ny Challenger.
#
# BAKGRUNN (in-sample, ikke bevis): sonde_kjor_laks_signal 25.11.2026.
# Kriteriet slaar inn 17 av 180 maaneder, i fire klynger: 2012-01, 2015-04,
# 2020-04 og 2025-04. Tre av dem har kjent utfall, og alle tre er positive
# mot MSCI World fra 9 maaneder og ut (+21, +44 og +12 pp paa 9 mnd, +57,
# +59 og +20 pp paa 12 mnd). Den fjerde, aapen fra april 2025, er negativ paa
# alle horisonter til naa. Med tre klynger er beste mulige p 0,125 i en
# ensidig fortegnstest, saa regelen KAN IKKE etableres paa historikken.
# Terskelene 80 og 85 er Frodes, valgt etter aa ha sett serien, som d95 for
# Brent og WTI og som 95 for kull. Derfor denne Challengeren: regelen logges
# ved siden av Champion fra sin egen startdato, og avgjoeres paa nye
# episoder.
#
# Championen har ingen flagg for laks i det hele tatt. Laksesonden
# 25.09.2026 fant at verken marginen (p 0,35) eller prisnivaaet sa noe om
# papirene 24 maaneder fram, og laks staar derfor som observasjon paa bordet.
# Denne Challengeren proever et annet kriterium enn den sonden: detrendet OG
# rullende A, ikke marginen.
#
# REGEL (segmentet laks, alle andre segmenter er Championens):
#   bottom_zone  Championens A_detrended > 80 OG A_rolling > 85. Strengt
#                stoerre enn, slik Frode skrev det og slik sonden maalte det.
#                Raa A inngaar IKKE: for laks maales den mot en kort serie
#                der sesongjusteringen alt har tatt ut det meste av
#                stoeyen, og det var detrendet og rullende Frode pekte paa.
#   observation_only  false for segmentet. Championen har true, fordi laks
#                staar uten flagg der. Under denne regelen er flagget ekte.
#   watch, B, C, D, d95 og papirene: Championens, uendret. Papirene er de
#                fire paa bordet (MOWI.OL, SALM.OL, LSG.OL, BAKKA.OL).
#   Ny episode: Championens regel (minst 12 maaneder uten signal).
#   Mangler A_detrended eller A_rolling, settes bottom_zone til NULL.
#
# UTGANGEN er dokumentert i spesifikasjonen og ikke i koden her, fordi
# rammeverket modner utfall paa faste horisonter (3, 6, 12 og 24 maaneder).
# Den tenkte utgangen er raa A tilbake paa 50, med tak paa 24 maaneder, og
# den kan regnes i ettertid av A-banen som ligger i snapshotene. Primaert
# utfall er 12 maaneder, fordi Frode mener laksesyklusen er kortere enn
# bordets to aar. Sonden ga median holdetid 5 maaneder og +16,9 pp for den
# utgangen over fire klynger.
# ---------------------------------------------------------------------------

CID = "challenger_laks_adar_v1"
SEGMENTER = ("laks",)
AD_MIN, AR_MIN = 80, 85


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
            ad, ar = _tall(c.get("A_detrended")), _tall(c.get("A_rolling"))
            mangler = [n for n, v in (("A_detrended", ad), ("A_rolling", ar)) if v is None]
            rad.update({"bottom_zone": None if mangler else (ad > AD_MIN and ar > AR_MIN),
                        "observation_only": False,
                        "missing_fields": ";".join(mangler) or None,
                        "data_stale": bool(mangler),
                        "source_version": ("bottom_zone=A_detrended > 80 og A_rolling > 85 "
                                           "(Championens skaarer)")})
        ut.append(rad)
    return ut
