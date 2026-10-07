# ---------------------------------------------------------------------------
# challenger_laks_tilbud_v1: tilbudsflagg for norsk laks (Frodes beslutning
# 07.10.2026). Registrert foer den ser data; endres aldri. En endret regel er
# en ny Challenger.
#
# BAKGRUNN (in-sample, ikke bevis): sonde_kjor_biomasse viste at staaende
# biomasse varsler slakten (desember mot aaret etter: +0,72, n 19).
# sonde_kjor_laks_valuta viste at prisen i EUR alene var den beste delen av
# A for laks (rho 0,29, p 0,10), og at valuta ikke tilfoerte noe. Ingen av
# delene er testet mot papirene som flagg.
#
# REGEL (segmentet laks, alle andre segmenter er Championens):
#   A_pris   persentil av log nominell eksportpris for laks i EUR, med trenden
#            trukket ut punkt-i-tid (samme metode som Ad i Champion, 60 mnd
#            minimum). Prisen er den sesongjusterte maanedsprisen i USD fra
#            segments/laks.json, regnet om med Norges Banks USDNOK og EURNOK.
#            Ingen KPI: trenden tar inflasjonen.
#   dB       staaende biomasse for laks i Norge (Fiskeridirektoratet), snitt
#            av de tre siste publiserte maanedene mot samme tre maaneder aaret
#            foer, i prosent.
#   watch        A_pris >= 70
#   bottom_zone  A_pris >= 70 OG dB < 0 (lav pris og krympende tilbud)
#   Ny episode: Championens regel (minst 12 mnd uten signal).
#   Papirer: bare SalMar og Leroy er kjoepbare (mest norsk produksjon). Mowi og
#   Bakkafrost logges, men er ikke kjoepbare i denne Challengeren.
#   Mangler data, settes signalene til NULL og feltet listes; klokken stopper
#   ikke.
#
# FELTENE: A_detrended = A_pris (EUR), A_raw = Championens A (USD, uendret),
# supply_metric = dB, observation_date = siste biomassemaaned.
# Raadataene som brukes, lagres i shadow/raadata/challenger_laks_tilbud_v1/.
# ---------------------------------------------------------------------------

import io, json, time
import numpy as np
import pandas as pd
import requests

CID = "challenger_laks_tilbud_v1"
GRENSE_A, MIN_HIST = 70, 60
KJOEPBARE = {"SALM.OL", "LSG.OL"}
BIOSTAT = "https://register.fiskeridir.no/biomassestatistikk/BIOSTAT-LAKS-FLK/biostat-total-flk.csv"
UA = {"User-Agent": "Syklusbordet"}


def _get(url):
    for i in range(4):
        try:
            r = requests.get(url, headers=UA, timeout=120)
            if r.status_code == 200:
                return r
        except requests.RequestException:
            pass
        time.sleep(2 ** (i + 1))
    raise RuntimeError(f"ingen svar fra {url[:60]}")


def pct_detrend(x, minn=MIN_HIST):
    """Kopi av priser.expanding_pct_detrend (frosset her, saa regelen ikke
    endres hvis priser.py endres). Hoey verdi = lav pris mot trenden."""
    v = np.asarray(x, dtype=float)
    out = np.full(len(v), np.nan)
    for i in range(minn - 1, len(v)):
        y = v[: i + 1]
        t = np.arange(i + 1)
        b, a = np.polyfit(t, y, 1)
        r = y - (a + b * t)
        out[i] = (r <= r[i]).sum() / len(r)
    return (1 - out) * 100


def norges_bank(kode):
    r = _get(f"https://data.norges-bank.no/api/data/EXR/M.{kode}.NOK.SP?format=csv&startPeriod=2000&locale=en")
    d = pd.read_csv(io.StringIO(r.text), sep=None, engine="python")
    tk = next(c for c in d.columns if "TIME" in c.upper())
    vk = next(c for c in d.columns if "OBS_VALUE" in c.upper())
    s = pd.Series(pd.to_numeric(d[vk].astype(str).str.replace(",", "."), errors="coerce").values,
                  index=d[tk].astype(str)).dropna()
    return s[~s.index.duplicated(keep="last")].sort_index()


def biomasse():
    r = _get(BIOSTAT)
    d = pd.read_csv(io.StringIO(r.content.decode("utf-8-sig", errors="replace")), sep=";")
    d = d[d["ARTSID"].str.upper() == "LAKS"]
    d["BIOMASSE_KG"] = pd.to_numeric(d["BIOMASSE_KG"].astype(str).str.replace(",", "."), errors="coerce")
    d["mnd"] = d["ÅR"].astype(int).astype(str) + "-" + d["MÅNED_KODE"].astype(int).map("{:02d}".format)
    return d.groupby("mnd")["BIOMASSE_KG"].sum().sort_index()


def beregn(seg, usdnok, eurnok, bio):
    """Ren funksjon: alt regles ut fra inndataene, saa kjoeringen kan
    gjenskapes fra raadatafila."""
    ser = {p["t"]: p["nom"] for p in seg.get("series", []) if p.get("nom") is not None}
    mnd = sorted(m for m in ser if m in usdnok and m in eurnok)
    eur = np.log([ser[m] * usdnok[m] / eurnok[m] for m in mnd])
    a = pct_detrend(eur) if len(eur) >= MIN_HIST else np.full(len(eur), np.nan)
    a_pris = float(a[-1]) if len(a) and np.isfinite(a[-1]) else None
    b = pd.Series(bio)
    b3 = b.rolling(3).mean()
    db = 100 * (b3 / b3.shift(12) - 1)
    db_siste = float(db.iloc[-1]) if len(db) and np.isfinite(db.iloc[-1]) else None
    return {"A_pris": a_pris, "pris_mnd": mnd[-1] if mnd else None, "dB": db_siste,
            "bio_mnd": b.index[-1] if len(b) else None}


def snapshot(champion_rader, kontekst):
    lager = kontekst["lager"]
    seg = json.loads(kontekst["les"]("segments/laks.json") or "{}")
    mangler, raa = [], {}
    try:
        raa["usdnok"], raa["eurnok"] = norges_bank("USD").to_dict(), norges_bank("EUR").to_dict()
    except Exception as e:
        mangler.append(f"valuta ({type(e).__name__})")
        raa["usdnok"], raa["eurnok"] = {}, {}
    try:
        raa["biomasse_kg"] = biomasse().to_dict()
    except Exception as e:
        mangler.append(f"biomasse ({type(e).__name__})")
        raa["biomasse_kg"] = {}
    try:
        lager.opprett(f"shadow/raadata/{CID}/{kontekst['uke']}.json",
                      json.dumps(raa, ensure_ascii=False, sort_keys=True) + "\n")
    except Exception:
        pass        # finnes fra foer (gjenopptatt kjoering)
    r = beregn(seg, raa["usdnok"], raa["eurnok"], raa["biomasse_kg"])
    if r["A_pris"] is None:
        mangler.append("A_pris")
    if r["dB"] is None:
        mangler.append("dB")
    watch = None if r["A_pris"] is None else r["A_pris"] >= GRENSE_A
    bunn = None if (r["A_pris"] is None or r["dB"] is None) else (r["A_pris"] >= GRENSE_A and r["dB"] < 0)

    ut = []
    for c in champion_rader:
        if c.get("segment") != "laks":
            continue
        rad = {k: (v if v != "" else None) for k, v in c.items()
               if k not in ("snapshot_id", "model_version", "run_id", "created_at", "code_changed")}
        if c.get("level") == "segment":
            rad.update({"A_detrended": None if r["A_pris"] is None else round(r["A_pris"], 1),
                        "supply_metric": None if r["dB"] is None else round(r["dB"], 2),
                        "watch": watch, "bottom_zone": bunn, "observation_only": False,
                        "observation_date": r["bio_mnd"], "price_last_observation": r["pris_mnd"],
                        "missing_fields": ";".join(mangler) or None,
                        "data_stale": bool(mangler),
                        "source_version": "A_detrended=A_pris EUR (Norges Bank), supply_metric=biomasse 3 mnd a/a "
                                          "(Fiskeridirektoratet)"})
        else:
            ok = c.get("instrument") in KJOEPBARE
            rad["instrument_eligible"] = ok and str(c.get("instrument_eligible")).lower() in ("true", "1")
            if not ok:
                rad["reason_if_not_eligible"] = "ikke kjoepbar i denne Challengeren: mye produksjon utenfor Norge"
        ut.append(rad)
    return ut
