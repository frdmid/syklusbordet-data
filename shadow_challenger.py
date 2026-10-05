# ---------------------------------------------------------------------------
# shadow_challenger: Challengere som egne grener i Shadow-OOS (Frodes
# beslutning 05.10.2026)
#
# En Challenger er en ny regel som logges ved siden av Champion fra sin egen
# startdato, uten aa endre Champion eller historikken. Denne fila er IKKE med
# i Championens frosne kodefiler, saa nye Challengere endrer aldri Champion.
# Den kalles fra shadow_oos.kjor_challengere etter at Champion er skrevet.
#
# REGISTRERE (foer Challengeren faar se data, punkt 33):
#   1. Skriv regelen i challengers/<id>.py med funksjonen
#        snapshot(champion_rader, kontekst) -> liste med rader
#      Radene har feltene i shadow_oos.F_SNAP (manglende felt blir NULL).
#      champion_rader er ukens Champion-snapshot, lest fra CSV (strenger).
#      kontekst har lager, rot, snapshot_date, uke og les(sti) -> tekst, som
#      ogsaa noterer hvilken versjon av fila som ble lest (git-blob-sha).
#      Valgfritt: ny_innslag(segment, flagg_uke, dato) -> (bool, grunn) hvis
#      regelen for ny episode skal vaere en annen enn Championens.
#   2. Skriv en spesifikasjon (JSON) med feltene i KREVES under, og kjoer
#        python shadow_challenger.py registrer <spesifikasjon.json>
#      Det lager config/challengers/<id>.json med hash av regelen og koden,
#      og en linje i shadow/model_registry.csv.
#   3. effective_from maa vaere en onsdag etter i dag. Commit og push foer den.
#
# KJOERE: hver uke, for hver Challenger med startdato passert:
#   egne snapshots i shadow/snapshots/<id>/<uke>.csv, egne hendelser i den
#   felles shadow_events.csv (model_version skiller), egen manifestlinje og
#   egen hashkjede. Samme regler som Champion: bare tillegg, foerste kjoering
#   i uken teller, og endret Challenger-kode merkes code_changed. En endret
#   regel er en NY Challenger, ikke en ny versjon av den gamle.
#
# Champion og Challengere sammenlignes bare fra Challengerens startdato
# (punkt 32). En Challenger kan bli Champion v2.0 bare fra en ny dato.
# ---------------------------------------------------------------------------

import datetime as dt
import importlib.util
import json, os, sys

import shadow_oos as so

MAPPE = "config/challengers"
KREVES = ["id", "effective_from", "hypothesis", "changed_variables", "unchanged_variables", "primary_endpoint",
          "expected_direction", "decision_rule", "modul"]


def _last_modul(rot, modul):
    p = os.path.join(rot, modul)
    spes = importlib.util.spec_from_file_location(os.path.splitext(os.path.basename(modul))[0], p)
    m = importlib.util.module_from_spec(spes)
    spes.loader.exec_module(m)
    return m


# ------------------------------------------------------------------ registrering
def lag_konfig(rot, spes, idag, code_commit=None):
    mangler = [k for k in KREVES if not spes.get(k)]
    if mangler:
        raise ValueError("spesifikasjonen mangler " + ", ".join(mangler))
    cid = spes["id"]
    if not cid.startswith("challenger_") or cid == so.MODELL:
        raise ValueError("id maa begynne med challenger_")
    eff = dt.date.fromisoformat(spes["effective_from"])
    if eff.weekday() != so.UKEDAG_START or eff <= idag:
        raise ValueError("effective_from maa vaere en onsdag etter i dag")
    if not os.path.exists(os.path.join(rot, spes["modul"])):
        raise ValueError(f"finner ikke {spes['modul']}")
    k = {"model": {"id": cid, "status": "challenger", "created_at": idag.isoformat(),
                   "effective_from": eff.isoformat(), "parent_model": spes.get("parent_model", so.MODELL),
                   "data_schema_version": so.SCHEMA},
         "spesifikasjon": {**{x: spes[x] for x in KREVES if x not in ("id", "effective_from")},
                           **{x: v for x, v in spes.items() if x not in KREVES and x != "parent_model"},
                           "kodefiler": so.kodehasher(rot, [spes["modul"]])},
         "metadata": {"code_commit": code_commit, "notes": spes.get("notes", "")}}
    k["metadata"]["specification_hash"] = so.spesifikasjonshash(k)
    return k


def registrer(rot, spes, idag=None, lager=None):
    """Skriver config/challengers/<id>.json og en linje i registeret. Feiler
    hvis Challengeren finnes fra foer: en endret regel er en ny Challenger."""
    idag = idag or dt.date.today()
    lager = lager or so.LokalLager(rot, rot)
    k = lag_konfig(rot, spes, idag)
    sti = f"{MAPPE}/{k['model']['id']}.json"
    reg = so.fra_csv(lager.les(so.REGISTER)[0])
    if any(r["model_id"] == k["model"]["id"] for r in reg):
        raise so.FinnesAllerede(k["model"]["id"])
    lager.opprett(sti, json.dumps(k, ensure_ascii=False, indent=1) + "\n")
    m = k["model"]
    so.legg_til_rader(lager, so.REGISTER, so.F_REGISTER, [{
        "model_id": m["id"], "created_at": m["created_at"], "effective_from": m["effective_from"],
        "parent_model": m["parent_model"], "status": "challenger",
        "specification_hash": k["metadata"]["specification_hash"], "code_commit": None,
        "data_schema_version": so.SCHEMA, "config_file": sti, "notes": spes.get("notes", "")}])
    return k


# ------------------------------------------------------------------ kjoering
def kjor(lager, rot, naa, note=print):
    """Kalles fra shadow_oos.kjor_challengere. Returnerer {id: status}."""
    ut = {}
    for f in lager.liste(MAPPE):
        if not f.endswith(".json"):
            continue
        try:
            ut[f[:-5]] = kjor_en(lager, rot, naa, f"{MAPPE}/{f}", note)
        except Exception as e:
            ut[f[:-5]] = f"feil: {type(e).__name__}"
            note(f"   challenger {f[:-5]} feilet: {type(e).__name__}: {str(e)[:80]}")
    return ut


def kjor_en(lager, rot, naa, konfigsti, note=print):
    snapshot_date, started = naa.date(), naa.strftime("%Y-%m-%d %H:%M:%S")
    konfig = json.loads(lager.les(konfigsti)[0])
    cid = konfig["model"]["id"]
    if snapshot_date < dt.date.fromisoformat(konfig["model"]["effective_from"]):
        return None
    uke = so.periodenokkel(snapshot_date)
    run_id = f"{cid}|{uke}|{started}"
    snapmappe, innmappe = f"shadow/snapshots/{cid}", f"shadow/inndata/{cid}"
    snapsti, innsti = f"{snapmappe}/{uke}.csv", f"{innmappe}/{uke}.json"
    feil = so.kontroller(lager, modell=cid, konfigsti=konfigsti)
    avvik = so.kodeavvik(konfig, rot)
    varsler = ["kode endret siden registrering: " + ", ".join(avvik)] if avvik else []
    man = so.fra_csv(lager.les(so.MANIFEST)[0])
    felles = {"run_id": run_id, "run_date": snapshot_date, "iso_week": uke, "model_version": cid,
              "configuration_hash": konfig["metadata"]["specification_hash"],
              "specification_ok": so.spesifikasjonshash(konfig) == konfig["metadata"]["specification_hash"],
              "code_changed": avvik or False, "started_at": started, "errors": feil}
    if any(m["iso_week"] == uke and m["model_version"] == cid and m["status"] in ("ok", "ok_gjenopptatt")
           for m in man):
        so.legg_til_rader(lager, so.MANIFEST, so.F_MANIFEST, [{**felles, "completed_at": started,
                                                               "status": "hoppet_over_uke_finnes",
                                                               "warnings": varsler}])
        return "hoppet_over"
    champsti = f"{so.SNAP_MAPPE}/{uke}.csv"
    champ_tekst, champ_sha = lager.les(champsti)
    if champ_tekst is None:
        so.legg_til_rader(lager, so.MANIFEST, so.F_MANIFEST, [{**felles, "completed_at": started,
                                                               "status": "venter_paa_champion",
                                                               "warnings": varsler}])
        return "venter"

    mod = _last_modul(rot, konfig["spesifikasjon"]["modul"])
    lest = {champsti: champ_sha}

    def les(sti):
        t, sha = lager.les(sti)
        lest[sti] = sha
        return t

    status, eksisterer = "ok", lager.les(snapsti)[0]
    if eksisterer is None:
        kontekst = {"lager": lager, "rot": rot, "snapshot_date": snapshot_date, "uke": uke, "les": les}
        rader = []
        for r in mod.snapshot(so.fra_csv(champ_tekst), kontekst):
            ukjente = set(r) - set(so.F_SNAP)
            if ukjente:
                raise ValueError(f"ukjente felt fra {cid}: {sorted(ukjente)}")
            seg, ins = r.get("segment"), r.get("instrument") or "-"
            rader.append({**r, "model_version": cid, "run_id": run_id, "created_at": started,
                          "snapshot_id": f"{cid}|{snapshot_date.isoformat()}|{seg}|{ins}",
                          "code_changed": ";".join(avvik) if avvik else False})
        inndata = json.dumps({"run_id": run_id, "filer_git_blob_sha": dict(sorted(lest.items())),
                              "kodefiler_sha256": so.kodehasher(rot, list(konfig["spesifikasjon"]["kodefiler"]))},
                             ensure_ascii=False, indent=1) + "\n"
        snaptekst = so.til_csv(rader, so.F_SNAP)
        try:
            lager.opprett(innsti, inndata)
        except so.FinnesAllerede:
            inndata = lager.les(innsti)[0]
        lager.opprett(snapsti, snaptekst)
    else:
        snaptekst, status = eksisterer, "ok_gjenopptatt"
        inndata = lager.les(innsti)[0] or ""
        run_id = so.fra_csv(snaptekst)[0]["run_id"]

    lagret = so.fra_csv(snaptekst)
    cache = {}

    def snaps_for(w):
        if w not in cache:
            cache[w] = so.fra_csv(lager.les(f"{snapmappe}/{w}.csv")[0])
        return cache[w]
    tidl = [f[:-4] for f in lager.liste(snapmappe) if f.endswith(".csv") and f[:-4] < uke]
    idx = json.loads(lager.les("index.json")[0] or "{}")
    segmenter = {}
    for sid in list(idx.get("segmenter") or []) + so.SKIP:
        t = lager.les(f"segments/{sid}.json")[0]
        if t:
            segmenter[sid] = json.loads(t)
    logguke = so.ukenokkel(snapshot_date)
    flagg_uke = [r for r in so.fra_csv(lager.les("logg/flagg_uke.csv")[0]) if r.get("uke") != logguke]
    nye = so.finn_hendelser(lagret, snaps_for(tidl[-1]) if tidl else [], so.fra_csv(lager.les(so.HENDELSER)[0]),
                            segmenter, flagg_uke, snapshot_date, snaps_for, modell=cid,
                            ny_innslag=getattr(mod, "ny_innslag", None))
    for h in nye:
        h["run_id"] = run_id
    hend_ny = so.legg_til_rader(lager, so.HENDELSER, so.F_EVENT, nye)
    kjede_forrige = next((m["chain_sha256"] for m in reversed(man) if m["model_version"] == cid
                          and m["status"] in ("ok", "ok_gjenopptatt")), "")
    s_sha, i_sha, h_sha = so.sha256(snaptekst), so.sha256(inndata), so.sha256(hend_ny)
    so.legg_til_rader(lager, so.MANIFEST, so.F_MANIFEST, [{
        **felles, "run_id": run_id, "raw_data_manifest": innsti,
        "completed_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S"), "status": status,
        "snapshot_file": snapsti, "snapshot_rows": len(lagret), "snapshot_sha256": s_sha, "inndata_sha256": i_sha,
        "events_new": len(nye), "events_rows_after": len(hend_ny.splitlines()) - 1, "events_sha256_after": h_sha,
        "chain_sha256": so.sha256(kjede_forrige + s_sha + i_sha + h_sha), "warnings": varsler}])
    note(f"   challenger {cid}: {uke} {len(lagret)} rader, {len(nye)} hendelser")
    return status


if __name__ == "__main__":
    rot = os.path.dirname(os.path.abspath(__file__))
    a = sys.argv[1:]
    if len(a) == 2 and a[0] == "registrer":
        k = registrer(rot, json.load(open(a[1], encoding="utf-8")))
        print(f"{k['model']['id']} registrert fra {k['model']['effective_from']}, "
              f"specification_hash {k['metadata']['specification_hash']}")
    elif len(a) == 2 and a[0] == "kontroller":
        print(so.kontroller(so.LokalLager(rot, rot), modell=a[1], konfigsti=f"{MAPPE}/{a[1]}.json") or "ingen avvik")
    else:
        print("bruk: python shadow_challenger.py registrer <spesifikasjon.json> | kontroller <id>")
