# ---------------------------------------------------------------------------
# endringer: de viktigste endringene siden forrige kjoering, til boksen
# oeverst paa dashbordet (Frodes bestilling 30.09.2026)
#
# Arbeidsflytene henter ikke historikk (grunn checkout), saa hver kjoering
# lagrer et oeyeblikksbilde av noekkeltallene i logg/endringer_snap.json og
# sammenligner med forrige bilde. Resultatet skrives til endringer.json.
#
#   UKE      kalles sist i bygg_shipping.py (siste steg i ukentlig
#            innhenting). Sammenligner med bildet fra forrige ISO-uke, saa en
#            ny kjoering samme uke sammenligner med samme forrige uke.
#   KVARTAL  kalles sist i overlevelse_c.py (siste steg i kvartalsvis
#            innhenting). Sammenligner med forrige kvartalskjoering paa en
#            annen dato.
#
# RANGERING: priser og nivaaer etter endring i prosent, skaarer paa skala 0
# til 100 (A, D, B2, COT-persentil) etter endring i poeng, og forholdstall
# rundt 0 til 3 (netto gjeld/EK, capex/avskrivninger, paritet) etter endring
# ganger 100, fordi prosent av et tall naer null blir meningsloest. Endring i
# prosent vises for alle. Skifter (flagg, oppsikt, port, trend) listes for seg.
# ---------------------------------------------------------------------------

import base64, json, os
import datetime as dt
import requests

REPO, BRANCH = "frdmid/syklusbordet-data", "main"
SKIP = ["ship_vlcc", "ship_suezmax", "ship_aframax", "ship_kamsarmax", "ship_ultramax",
        "ship_capesize", "ship_handysize"]
TOPP = 10


def _h():
    return {"Authorization": f"Bearer {os.environ.get('GITHUB_TOKEN', '')}", "Accept": "application/vnd.github+json"}


def les(sti):
    r = requests.get(f"https://api.github.com/repos/{REPO}/contents/{sti}", headers=_h(),
                     params={"ref": BRANCH}, timeout=60)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return json.loads(base64.b64decode(r.json()["content"]))


def skriv(sti, obj):
    api = f"https://api.github.com/repos/{REPO}/contents/{sti}"
    g = requests.get(api, headers=_h(), params={"ref": BRANCH}, timeout=30)
    body = {"message": f"oppdatert {sti}", "branch": BRANCH,
            "content": base64.b64encode(json.dumps(obj, ensure_ascii=False, indent=1).encode()).decode()}
    if g.status_code == 200:
        body["sha"] = g.json().get("sha")
    requests.put(api, headers=_h(), json=body, timeout=60).raise_for_status()


def _tall(x):
    return None if x is None or isinstance(x, bool) else (float(x) if isinstance(x, (int, float)) else None)


# ------------------------------------------------------------------ bilder
def bilde_uke(segmenter, marked=None, dollar=None):
    """segmenter: liste av segment-dicts. Returnerer {noekkel: {navn, felt,
    verdi, skala}} og {noekkel: tilstand} for skifter."""
    v, s = {}, {}
    for d in segmenter:
        sid, navn, sc = d["id"], d.get("name", d["id"]), d.get("scores") or {}
        def put(felt, verdi, skala, etikett):
            if _tall(verdi) is not None:
                v[f"{sid}|{felt}"] = {"segment": navn, "felt": etikett, "verdi": _tall(verdi), "skala": skala}
        put("real", d.get("last_real"), "nivaa", "Realpris")
        put("A", sc.get("A"), "poeng", "Prisnivå A")
        put("Ad", sc.get("Ad"), "poeng", "A detrendet")
        put("D", sc.get("D"), "poeng", "Kapitulasjon D")
        put("A2", sc.get("A2"), "forhold", "Paritet A2")
        put("cot", (d.get("cot") or {}).get("mm_pctl_3aar"), "poeng", "COT-persentil")
        r = d.get("rate") or {}
        put("rate", r.get("verdi"), "nivaa", r.get("navn") or "Rate")
        s[f"{sid}|flagg"] = {"segment": navn, "felt": "Bunnsone", "verdi": bool(sc.get("flagg"))}
        s[f"{sid}|oppsikt"] = {"segment": navn, "felt": "Under oppsikt", "verdi": bool(sc.get("oppsikt"))}
        if "flagg_d95" in sc:
            s[f"{sid}|d95"] = {"segment": navn, "felt": "Parallelt signal d95", "verdi": bool(sc.get("flagg_d95"))}
        if sc.get("gate"):
            s[f"{sid}|port"] = {"segment": navn, "felt": "Port C", "verdi": sc.get("gate")}
        if (d.get("trend") or {}).get("signal"):
            s[f"{sid}|trend"] = {"segment": navn, "felt": "Trend", "verdi": d["trend"]["signal"]}
    for kilde, nk, navn in ((marked, "vix", "VIX"), ((dollar or {}).get("dxy"), "dxy", "Dollar (DXY)"),
                            ((dollar or {}).get("usdnok"), "usdnok", "USD/NOK")):
        if kilde and _tall(kilde.get("verdi")) is not None:
            v[f"marked|{nk}"] = {"segment": "Marked", "felt": navn, "verdi": float(kilde["verdi"]), "skala": "nivaa"}
    return v, s


def bilde_kvartal(c, b, rigg):
    v, s = {}, {}
    for tk, x in ((c or {}).get("selskaper") or {}).items():
        navn = f"{x.get('navn', tk)} ({tk})"
        if _tall(x.get("kvartaler")) is not None:
            v[f"C|{tk}|kv"] = {"segment": navn, "felt": "C, kvartaler", "verdi": float(x["kvartaler"]), "skala": "nivaa"}
        if _tall(x.get("netto_gjeld_ek")) is not None:
            v[f"C|{tk}|ngek"] = {"segment": navn, "felt": "Netto gjeld/EK", "verdi": float(x["netto_gjeld_ek"]), "skala": "forhold"}
        s[f"C|{tk}|port"] = {"segment": navn, "felt": "Port C", "verdi": x.get("port")}
    for sid, x in ((c or {}).get("segmenter") or {}).items():
        pen = sid.replace("ship_", "").replace("gold", "gull").capitalize()
        s[f"Cseg|{sid}"] = {"segment": pen, "felt": "Port C for segmentet", "verdi": x.get("gate")}
    for m, x in ((b or {}).get("metaller") or {}).items():
        if _tall(x.get("B2_siste")) is not None:
            v[f"B|{m}|B2"] = {"segment": m.capitalize(), "felt": "Tilbud B2", "verdi": float(x["B2_siste"]), "skala": "poeng"}
        if _tall(x.get("ratio_siste")) is not None:
            v[f"B|{m}|ratio"] = {"segment": m.capitalize(), "felt": "Capex/avskrivninger", "verdi": float(x["ratio_siste"]), "skala": "forhold"}
    for k, x in ((rigg or {}).get("segmenter") or {}).items():
        if _tall(x.get("B2_siste")) is not None:
            v[f"R|{k}|B2"] = {"segment": "Rigger, " + x.get("navn", k), "felt": "Tilbud B2", "verdi": float(x["B2_siste"]), "skala": "poeng"}
        if _tall(x.get("forhold_siste")) is not None:
            v[f"R|{k}|f"] = {"segment": "Rigger, " + x.get("navn", k), "felt": "Capex/avskrivninger", "verdi": float(x["forhold_siste"]), "skala": "forhold"}
    return v, s


# ------------------------------------------------------------------ sammenligning
def sammenlign(gml, ny):
    rader = []
    for k, n in ny["verdier"].items():
        g = gml["verdier"].get(k)
        if not g or g["verdi"] == n["verdi"]:
            continue
        a, b = g["verdi"], n["verdi"]
        pst = None if a == 0 else round(100 * (b - a) / abs(a), 1)
        poeng = round(b - a, 1)
        vekt = (abs(poeng) if n["skala"] == "poeng" else abs(b - a) * 100 if n["skala"] == "forhold"
                else (abs(pst) if pst is not None else abs(poeng)))
        rader.append({"segment": n["segment"], "felt": n["felt"], "gammel": round(a, 3), "ny": round(b, 3),
                      "endring_pst": pst, "poeng": poeng if n["skala"] == "poeng" else None, "vekt": round(vekt, 2)})
    rader.sort(key=lambda r: -r["vekt"])
    skifter = []
    for k, n in ny["skifter"].items():
        g = gml["skifter"].get(k)
        if g is not None and g["verdi"] != n["verdi"]:
            skifter.append({"segment": n["segment"], "felt": n["felt"], "gammel": g["verdi"], "ny": n["verdi"]})
    return rader[:TOPP], skifter


def _oppdater(del_, noekkel, ny, snap):
    """Velger sammenligningsgrunnlag og flytter bildene i snap."""
    naa, forrige = snap.get(del_), snap.get(del_ + "_forrige")
    if naa and naa.get("noekkel") == noekkel:
        grunn = forrige
    else:
        grunn = naa
        snap[del_ + "_forrige"] = naa
    snap[del_] = ny
    return grunn


def lag(del_, noekkel, verdier, skifter, snap, resultat):
    ny = {"noekkel": noekkel, "dato": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M"),
          "verdier": verdier, "skifter": skifter}
    grunn = _oppdater(del_, noekkel, ny, snap)
    if grunn:
        topp, sk = sammenlign(grunn, ny)
        resultat[del_] = {"forrige_dato": grunn["dato"], "ny_dato": ny["dato"],
                          "forrige": grunn["noekkel"], "ny": ny["noekkel"], "topp": topp, "skifter": sk}
    else:
        resultat[del_] = {"forrige_dato": None, "ny_dato": ny["dato"], "ny": noekkel, "topp": [], "skifter": [],
                          "merknad": "Første bilde. Endringer vises fra neste kjøring."}


def uke(note=print):
    idx = les("index.json") or {}
    segs = []
    for sid in list(idx.get("segmenter") or []) + SKIP:
        try:
            d = les(f"segments/{sid}.json")
            if d:
                segs.append(d)
        except Exception as e:
            note(f"   endringer: {sid} ikke lest ({type(e).__name__})")
    v, s = bilde_uke(segs, les("marked.json"), les("dollar.json"))
    y, w, _ = dt.date.today().isocalendar()
    snap = les("logg/endringer_snap.json") or {}
    res = les("endringer.json") or {"id": "endringer"}
    lag("uke", f"{y}-W{w:02d}", v, s, snap, res)
    skriv("logg/endringer_snap.json", snap)
    skriv("endringer.json", res)
    u = res["uke"]
    note(f"   endringer uke: {u.get('forrige')} -> {u.get('ny')}, {len(u['topp'])} tall, {len(u['skifter'])} skifter")


def kvartal(note=print):
    v, s = bilde_kvartal(les("c_overlevelse.json"), les("b_capex.json"), les("b_rigg.json"))
    snap = les("logg/endringer_snap.json") or {}
    res = les("endringer.json") or {"id": "endringer"}
    lag("kvartal", dt.date.today().isoformat(), v, s, snap, res)
    skriv("logg/endringer_snap.json", snap)
    skriv("endringer.json", res)
    k = res["kvartal"]
    note(f"   endringer kvartal: {k.get('forrige')} -> {k.get('ny')}, {len(k['topp'])} tall, {len(k['skifter'])} skifter")
