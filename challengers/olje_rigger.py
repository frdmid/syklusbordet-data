# ---------------------------------------------------------------------------
# challenger_olje_rigger_v1: tilbudsmaal B for Brent og WTI fra oljeriggene
# (Frodes beslutning 12.10.2026). Registrert foer den ser data; endres aldri.
# En endret regel er en ny Challenger.
#
# BAKGRUNN (in-sample, ikke bevis): sonde_kjor_b_mekanisme viste at endringen
# i riggene i Permian, Eagle Ford og Bakken varsler amerikansk
# raaoljeproduksjon 12 mnd senere (+0,51; uten overlapp +0,57, n 17).
# Flagget er ikke testet mot papirene.
#
# REGEL (segmentene brent og wti, alle andre segmenter er Championens):
#   x        rigger i Permian + Eagle Ford + Bakken, snitt 3 mnd, endring fra
#            aaret foer i log-prosent. Kilde: EIA DPR-arkiv (2007 til 2021) og
#            STEO tabell 10a fra 2022, rigger til og med maaneden to foer STEOs
#            prognosedato (prognosen brukes aldri).
#   B_olje   persentil av -x mot egen historikk punkt-i-tid (minst 60 mnd):
#            hoey naar riggene faller mer enn vanlig.
#   bottom_zone  Championens A >= 80 OG Ad >= 80 OG x < 0 (lav pris og
#                krympende boring).
#   watch, d95 og papirer: Championens, uendret. Det parallelle signalet d95
#   er ikke en del av denne Challengeren.
#   Ny episode: Championens regel (minst 12 mnd uten signal).
#   Mangler riggdata, settes B og bottom_zone til NULL og feltet listes.
#
# FELTENE: B = B_olje, supply_metric = x, observation_date = siste riggmaaned.
# Raadataene som brukes, lagres i shadow/raadata/challenger_olje_rigger_v1/.
# ---------------------------------------------------------------------------

import io, json, re, time
import numpy as np
import pandas as pd
import requests

CID = "challenger_olje_rigger_v1"
SEGMENTER = ("brent", "wti")
MIN_HIST = 60
UA = {"User-Agent": "Syklusbordet frode@h-k.no"}
DPR = "https://www.eia.gov/petroleum/drilling/xls/dpr-data.xlsx"
STEO = "https://www.eia.gov/outlooks/steo/xls/STEO_m.xlsx"
BASS = {"Permian": "PM", "Eagle Ford": "EF", "Bakken": "BK"}


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


def hent_rigger():
    """{basseng: {'YYYY-MM': rigger}}, DPR foer 2022 og STEO fra 2022."""
    dpr = pd.read_excel(io.BytesIO(_get(DPR).content), sheet_name=None, header=None)
    steo = pd.read_excel(io.BytesIO(_get(STEO).content), sheet_name="10atab", header=None)
    m = re.search(r"(\w+) (\d+), (\d{4})", str(steo.iloc[3, 0]))
    siste = pd.Period(pd.Timestamp(f"{m.group(1)} {m.group(2)} {m.group(3)}"), "M") - 2
    kol = list(range(2, steo.shape[1]))
    sidx = pd.period_range(f"{int(steo.iloc[2, 2])}-01", periods=len(kol), freq="M")
    kode = {str(steo.iloc[i, 0]).strip(): i for i in range(len(steo))}
    ut = {}
    for b, k in BASS.items():
        d = dpr[f"{b} Region"].iloc[2:]
        a = pd.Series(pd.to_numeric(d[1], errors="coerce").values,
                      index=pd.PeriodIndex(pd.to_datetime(d[0]), freq="M")).dropna()
        s = pd.Series(pd.to_numeric(steo.iloc[kode[f"RIGS{k}"], kol], errors="coerce").values, index=sidx)
        s = s[s.index <= siste].dropna()
        r = pd.concat([a[a.index < pd.Period("2022-01", "M")], s])
        r = r[~r.index.duplicated(keep="last")].sort_index()
        ut[b] = {str(p): float(v) for p, v in r.items()}
    return ut


def beregn(rigger):
    """Ren funksjon av raadataene, saa kjoeringen kan gjenskapes."""
    ser = [pd.Series({pd.Period(k, "M"): v for k, v in rigger[b].items()}) for b in BASS]
    if any(s.empty for s in ser):
        return {"x": None, "B": None, "mnd": None}
    g = pd.concat(ser, axis=1).dropna().sum(axis=1).sort_index()
    r3 = g.rolling(3).mean()
    x = (100 * np.log(r3 / r3.shift(12))).dropna()
    v = -x.values
    pct = np.full(len(v), np.nan)
    for i in range(len(v)):
        if i + 1 >= MIN_HIST:
            pct[i] = (v[: i + 1] <= v[i]).sum() / (i + 1) * 100
    return {"x": float(x.iloc[-1]), "B": None if not np.isfinite(pct[-1]) else float(pct[-1]),
            "mnd": str(x.index[-1]), "rigger": float(g.iloc[-1])}


def _tall(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def snapshot(champion_rader, kontekst):
    lager = kontekst["lager"]
    mangler = []
    try:
        rigger = hent_rigger()
    except Exception as e:
        rigger = {b: {} for b in BASS}
        mangler.append(f"rigger ({type(e).__name__})")
    try:
        lager.opprett(f"shadow/raadata/{CID}/{kontekst['uke']}.json",
                      json.dumps(rigger, ensure_ascii=False, sort_keys=True) + "\n")
    except Exception:
        pass        # finnes fra foer (gjenopptatt kjoering)
    r = beregn(rigger)
    if r["x"] is None:
        mangler.append("x")
    ut = []
    for c in champion_rader:
        if c.get("segment") not in SEGMENTER:
            continue
        rad = {k: (v if v != "" else None) for k, v in c.items()
               if k not in ("snapshot_id", "model_version", "run_id", "created_at", "code_changed")}
        if c.get("level") == "segment":
            a, ad = _tall(c.get("A_raw")), _tall(c.get("A_detrended"))
            bunn = None if (a is None or ad is None or r["x"] is None) else (a >= 80 and ad >= 80 and r["x"] < 0)
            rad.update({"B": None if r["B"] is None else round(r["B"], 1),
                        "supply_metric": None if r["x"] is None else round(r["x"], 2),
                        "bottom_zone": bunn, "observation_date": r["mnd"],
                        "missing_fields": ";".join(mangler) or None, "data_stale": bool(mangler),
                        "source_version": "B=B_olje (persentil av fall i oljerigger Permian, Eagle Ford, Bakken; "
                                          "EIA DPR+STEO 10a), supply_metric=endring i rigger 12 mnd, log-%"})
        ut.append(rad)
    return ut
