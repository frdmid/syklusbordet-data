# ---------------------------------------------------------------------------
# dashbord/bygg: setter sammen dashbord/data.json av filene i repoet
# (Frodes bestilling 12.11.2026, steg 3 i notater/2026-11-11_gjennomgang.md).
#
# HVORFOR. Dashbordet har lest databasen sin, og databasen har bare blitt
# fylt av onsdagsrutinen: en spraakmodell som gjor ETL etter tolv steg prosa.
# Den feilet 30.09.2026, og 04.11.2026 maatte Actions startes for haand.
# Leser dashbordet i stedet denne filen rett fra det offentlige repoet, er den
# fersk i samme sekund som Actions er ferdig.
#
# DATABASEN BLIR IKKE SLAATT AV. Rutinen gaar som foer, og dashbordet velger
# den ferskeste av de to. Denne filen er altsaa et TILLEGG: feiler den, eller
# blir den avvist, viser dashbordet det databasen har, som i dag.
#
# ALU_TILBUD SKAL ALDRI HIT. marked/alu_tilbud er IAI-tall med vilkaar om
# personlig bruk, og repoet er offentlig. Dokumentet ligger bare i databasen
# og i data_privat/. Det staar en assert under; den skal ikke fjernes.
#
# SPERREN MOT GAMMEL KODE ER BEHOLDT. Rutinens punkt 5 sammenligner hver fil
# med dokumentet som alt ligger i databasen og legger tilbake felt som er
# falt bort, fordi en eldre arbeidsflyt en gang slettet instrumentlister usett.
# Denne filen gjor det samme mot FORRIGE dashbord/data.json, ellers ville
# sperren forsvinne naar databasen ikke lenger er hovedkilden.
#
# ROBUSTHET
#   - en fil som ikke bestaar kravene tas ikke inn; forrige versjon av det
#     dokumentet baeres videre, og grunnen staar i "avvist",
#   - bestaar for faa segmenter, skrives ingenting i det hele tatt,
#   - ingen nettkall, bare filer i repoet,
#   - skriver bare naar innholdet er endret,
#   - alt er pakket i try/except i kjor().
#
# Kalles fra shadow_challenger.kjor, sist, som kontekstmodulene.
# ---------------------------------------------------------------------------

import datetime as dt
import json
from zoneinfo import ZoneInfo

FIL = "dashbord/data.json"
OSLO = ZoneInfo("Europe/Oslo")
SKIP = ("ship_vlcc", "ship_suezmax", "ship_aframax", "ship_kamsarmax",
        "ship_ultramax", "ship_capesize", "ship_handysize")
# Dokumenter i samlingen marked som hentes fra repoet. alu_tilbud staar med
# vilje IKKE her, se toppen av fila.
MARKED = ("vix", "dollar", "endringer", "helse", "gass_b", "laks_biomasse",
          "regime", "uran_kontrakt", "handel")
FORBUDT = ("alu_tilbud",)
# Felt som skal baeres videre hvis de faller bort (rutinens punkt 5).
BEVAR_TOPP = ("ettersp", "cot", "trend", "rate", "rigg_b", "instrumenter")
BEVAR_SCORES = ("B", "B1", "B2", "B_forhold", "B_aar")
MIN_SEGMENTER = 20          # under dette skrives ingenting


def _tall(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _fersk(dato, idag, dager=10):
    try:
        return (idag - dt.date.fromisoformat(str(dato)[:10])).days <= dager
    except Exception:
        return False


# ------------------------------------------------------------------ kravene
def krav_segment(sid, d):
    """Returnerer None hvis filen bestaar, ellers grunnen som tekst.
    Samme krav som onsdagsrutinens punkt 3."""
    if not isinstance(d, dict):
        return "ikke et objekt"
    s = d.get("series")
    if not isinstance(s, list) or len(s) < 6:
        return "series mangler eller har under 6 punkter"
    if not d.get("last_obs"):
        return "last_obs mangler"
    if not isinstance(d.get("instrumenter"), list) or not d["instrumenter"]:
        return "instrumenter mangler eller er tom"
    sc = d.get("scores") or {}
    if sid.startswith("ship_"):
        if not any(p.get("real") != p.get("nom") for p in s):
            return "ingen punkt har real forskjellig fra nom (deflatoren mangler)"
    else:
        for f in ("A", "Ad", "Ar"):
            if not _tall(sc.get(f)):
                return f"scores.{f} er ikke et tall"
    if sid == "laks":
        if not sc.get("observasjon") or sc.get("flagg"):
            return "laks skal ha observasjon sann og flagg usann"
        if not _tall((d.get("laks") or {}).get("margin")):
            return "laks.margin er ikke et tall"
    return None


def krav_miners(d, idag_idx):
    if not isinstance(d, dict) or d.get("id") != "miners":
        return "id er ikke miners"
    if not isinstance(d.get("series"), list) or len(d["series"]) < 6:
        return "series mangler eller har under 6 punkter"
    if not isinstance(d.get("instrumenter"), list) or not d["instrumenter"]:
        return "instrumenter mangler"
    sc = d.get("scores") or {}
    for f in ("A", "Ad", "Ar"):
        if not _tall(sc.get(f)):
            return f"scores.{f} er ikke et tall"
    if not sc.get("observasjon") or sc.get("flagg"):
        return "miners skal ha observasjon sann og flagg usann"
    if str(d.get("laget", ""))[:10] != idag_idx:
        return f"laget {d.get('laget')} er ikke samme dato som index.json"
    return None


def krav_marked(mid, d, idag, idag_idx):
    """Samme krav som rutinens punkt 6b til 6l."""
    if not isinstance(d, dict):
        return "ikke et objekt"
    if d.get("id") != mid:
        return f"id er {d.get('id')!r}, ventet {mid!r}"
    if mid == "vix":
        if not _tall(d.get("verdi")):
            return "verdi er ikke et tall"
        return None if _fersk(d.get("t"), idag) else f"t {d.get('t')} er eldre enn 10 dager"
    if mid == "dollar":
        ok = [k for k in ("dxy", "usdnok")
              if isinstance(d.get(k), dict) and _tall(d[k].get("verdi")) and _fersk(d[k].get("t"), idag)]
        return None if ok else "verken dxy eller usdnok har ferskt tall"
    if mid == "endringer":
        return None if (d.get("uke") or {}).get("ny_dato") else "uke.ny_dato mangler"
    if mid == "helse":
        return None if isinstance(d.get("rader"), list) and d["rader"] else "rader er tom"
    # de ferske kontekstfilene: samme dato som index.json
    datokrav = {"gass_b": ("endring_12m_logpst",), "laks_biomasse": ("dB",),
                "regime": (), "uran_kontrakt": ("kontrakt", "spot"), "handel": ()}
    if mid in datokrav:
        for f in datokrav[mid]:
            if not _tall(d.get(f)):
                return f"{f} er ikke et tall"
        if mid == "gass_b" and not (_tall(d.get("B")) or d.get("B") is None):
            return "B er verken tall eller null"
        if mid == "laks_biomasse" and not (isinstance(d.get("serie"), list) and d["serie"]):
            return "serie er tom"
        if mid == "regime":
            if not isinstance(d.get("vekst"), dict) or not isinstance(d.get("sjokk"), dict):
                return "vekst eller sjokk er ikke objekter"
            if not (isinstance(d.get("serie"), list) and d["serie"]):
                return "serie er tom"
        if mid == "uran_kontrakt" and not (isinstance(d.get("serie"), list) and d["serie"]):
            return "serie er tom"
        if mid == "handel":
            if not (isinstance(d.get("liste"), list) and len(d["liste"]) >= 10):
                return "liste har under 10 rader"
            if not d.get("evidens"):
                return "evidens mangler"
        stempel = d.get("oppdatert") if mid == "handel" else d.get("laget")
        if str(stempel or "")[:10] != idag_idx:
            return f"{'oppdatert' if mid == 'handel' else 'laget'} {stempel} er ikke samme dato som index.json"
    return None


# ------------------------------------------------------------------ bevaring
def bevar(ny, gml):
    """Legger tilbake felt som finnes i gml og mangler i ny. Returnerer
    listen over hva som ble baaret videre."""
    if not isinstance(gml, dict):
        return []
    tatt = []
    for f in BEVAR_TOPP:
        if f in gml and gml[f] not in (None, [], {}) and not ny.get(f):
            ny[f] = gml[f]
            tatt.append(f)
    s_ny, s_gml = ny.setdefault("scores", {}), gml.get("scores") or {}
    for f in BEVAR_SCORES:
        if _tall(s_gml.get(f)) and s_ny.get(f) is None:
            s_ny[f] = s_gml[f]
            tatt.append(f"scores.{f}")
    return tatt


# ------------------------------------------------------------------ bygg
def _les(lager, sti):
    try:
        t = lager.les(sti)[0]
        return json.loads(t) if t else None
    except Exception:
        return None


def bygg(lager, naa=None, note=print):
    naa_dt = naa or dt.datetime.now(OSLO)
    idag = naa_dt.date()
    idx = _les(lager, "index.json")
    if not idx or not idx.get("oppdatert"):
        raise RuntimeError("index.json mangler eller har ingen oppdatert")
    idag_idx = str(idx["oppdatert"])[:10]
    forrige = _les(lager, FIL) or {}
    f_seg = (forrige.get("segments") or {})
    f_mk = (forrige.get("marked") or {})

    segments, marked, avvist, bevart = {}, {}, [], []

    for sid in list(idx.get("segmenter") or []) + list(SKIP):
        d = _les(lager, f"segments/{sid}.json")
        grunn = "filen mangler" if d is None else krav_segment(sid, d)
        if grunn:
            avvist.append({"dok": f"segments/{sid}", "grunn": grunn,
                           "forrige_baaret_videre": sid in f_seg})
            if sid in f_seg:
                segments[sid] = f_seg[sid]
            continue
        tatt = bevar(d, f_seg.get(sid))
        if tatt:
            bevart.append({"dok": f"segments/{sid}", "felt": tatt})
        segments[sid] = d

    mn = _les(lager, "miners.json")
    grunn = "filen mangler" if mn is None else krav_miners(mn, idag_idx)
    if grunn:
        avvist.append({"dok": "segments/miners", "grunn": grunn,
                       "forrige_baaret_videre": "miners" in f_seg})
        if "miners" in f_seg:
            segments["miners"] = f_seg["miners"]
    else:
        segments["miners"] = mn

    kilder = {"vix": "marked.json", "dollar": "dollar.json", "endringer": "endringer.json",
              "helse": "helse.json", "gass_b": "gass_b.json",
              "laks_biomasse": "laks_biomasse.json", "regime": "regime.json",
              "uran_kontrakt": "uran_kontrakt.json", "handel": "handel.json"}
    for mid in MARKED:
        d = _les(lager, kilder[mid])
        grunn = "filen mangler" if d is None else krav_marked(mid, d, idag, idag_idx)
        if grunn:
            avvist.append({"dok": f"marked/{mid}", "grunn": grunn,
                           "forrige_baaret_videre": mid in f_mk})
            if mid in f_mk:
                marked[mid] = f_mk[mid]
            continue
        marked[mid] = d

    # Sperre: IAI-data skal aldri i et offentlig repo.
    for f in FORBUDT:
        assert f not in marked and f not in segments, \
            f"{f} skal aldri i {FIL}: IAI-tall til personlig bruk, repoet er offentlig"

    ekte = [s for s in segments.values() if (s.get("series") or [])]
    if len(ekte) < MIN_SEGMENTER:
        raise RuntimeError(f"bare {len(ekte)} segmenter bestod, under grensen {MIN_SEGMENTER}; "
                           "skriver ingenting")

    ut = {"id": "data", "laget": naa_dt.strftime("%Y-%m-%d %H:%M"),
          "laget_tz": "Europe/Oslo",
          "index_oppdatert": idx["oppdatert"],
          "ny_dato": ((marked.get("endringer") or {}).get("uke") or {}).get("ny_dato"),
          "om": ("Satt sammen av dashbord/bygg.py av filene i repoet. Dashbordet leser den "
                 "ferskeste av denne og sin egen database. marked/alu_tilbud ligger ALDRI "
                 "her (IAI-tall, personlig bruk) og hentes alltid fra databasen."),
          "antall": {"segments": len(segments), "marked": len(marked)},
          "avvist": avvist, "bevart": bevart,
          "segments": segments, "marked": marked}
    note(f"   bygg {FIL}: {len(segments)} segmenter, {len(marked)} markedsdokumenter, "
         f"{len(avvist)} avvist, {len(bevart)} bevart")
    for a in avvist:
        note(f"      avvist {a['dok']}: {a['grunn']}"
             + (" (forrige baaret videre)" if a["forrige_baaret_videre"] else " (INGEN forrige)"))
    for b in bevart:
        note(f"      bevart {b['dok']}: {', '.join(b['felt'])}")
    return ut


def kjor(lager, note=print, naa=None):
    try:
        ut = bygg(lager, naa, note)
        tekst = json.dumps(ut, ensure_ascii=False, separators=(",", ":")) + "\n"
        gml, sha = lager.les(FIL)
        if gml is None:
            lager.opprett(FIL, tekst)
        elif gml != tekst:
            lager.erstatt(FIL, tekst, sha)
        else:
            note(f"   bygg {FIL}: uendret")
            return
        note(f"   bygg {FIL}: skrevet ({len(tekst)} tegn)")
    except Exception as e:
        note(f"   bygg {FIL} feilet: {type(e).__name__}: {str(e)[:120]}")


if __name__ == "__main__":
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import shadow_oos as so
    rot = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ut = bygg(so.LokalLager(rot, rot))
    print(json.dumps({k: v for k, v in ut.items() if k not in ("segments", "marked")},
                     ensure_ascii=False, indent=1))
    if "--skriv" in sys.argv:
        p = os.path.join(rot, FIL)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "w", encoding="utf-8", newline="\n").write(
            json.dumps(ut, ensure_ascii=False, separators=(",", ":")) + "\n")
        print(f"\nskrev {FIL} ({os.path.getsize(p)} byte)")
