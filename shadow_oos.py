# ---------------------------------------------------------------------------
# shadow_oos: ekte fremoverlogg for Champion v1.0 (Frodes bestilling 05.10.2026,
# etter dokumentet "Shadow-OOS-oppsett for Syklusdashboard", fase 1)
#
# Hvorfor: nesten all evidens bordet hviler paa er historikk som allerede er
# sett og brukt til aa lage reglene. Den eneste uavhengige testen er aa fryse
# modellen og skrive ned hva den sa hver uke, foer utfallet er kjent. Se
# notater/shadow_oos_plan.md for plan, filformat og aapne spoersmaal.
#
# HOVEDREGEL: alt her er bare tillegg (append-only). Gamle snapshots, hendelser
# og manifestlinjer endres aldri. En feil rettes i shadow/correction_log.csv,
# og originalverdien blir staaende. En ny modell blir en Challenger med egen
# startdato. Fortiden regenereres aldri.
#
# Filer (alle i repoet, git-historikken viser naar hver linje kom):
#   config/champion_v1_0.json             frosne regler, kodefilenes hash
#   shadow/model_registry.csv             en linje per modell
#   shadow/snapshots/champion_v1_0/<uke>.csv
#                                         ukens bilde, segment x papir. Skrives
#                                         EN gang per ISO-uke og aldri igjen.
#   shadow/inndata/champion_v1_0/<uke>.json
#                                         git-blob-sha for hver inndatafil, saa
#                                         snapshotet kan kobles til tallene bak
#   shadow/shadow_events.csv              hendelser, bare tillegg
#   shadow/shadow_outcomes.csv            tom i fase 1 (bare overskrift)
#   shadow/correction_log.csv             rettelser, bare tillegg
#   shadow/run_manifest.csv               en linje per kjoering, med hash av
#                                         snapshotet og en hashkjede
#
# Kalles sist i bygg_shipping.py (siste steg i ukentlig innhenting), etter
# endringer og helse. Skriver ingenting foer effective_from (07.10.2026).
# Feiler noe her, stopper ikke resten av innhentingen.
#
# Lokal kjoering:
#   python shadow_oos.py test <utmappe> [dato]   skriv til utmappe, ikke repoet
#   python shadow_oos.py kontroller              sjekk integriteten i repoet
#   python shadow_oos.py frys [--commit SHA]     lag config og register (bare
#                                                foer effective_from)
# ---------------------------------------------------------------------------

import base64, csv, hashlib, io, json, os, re, sys, time
import datetime as dt
import requests

REPO, BRANCH = "frdmid/syklusbordet-data", "main"
MODELL = "champion_v1_0"
KONFIG = f"config/{MODELL}.json"
REGISTER = "shadow/model_registry.csv"
HENDELSER = "shadow/shadow_events.csv"
UTFALL = "shadow/shadow_outcomes.csv"
RETTELSER = "shadow/correction_log.csv"
MANIFEST = "shadow/run_manifest.csv"
SNAP_MAPPE = f"shadow/snapshots/{MODELL}"
INNDATA_MAPPE = f"shadow/inndata/{MODELL}"
SCHEMA = 1

# Skipssegmentene staar ikke i index.json. Samme liste som endringer.py, men
# kopiert hit, saa en endring der ikke endrer Champion stille.
SKIP = ["ship_vlcc", "ship_suezmax", "ship_aframax", "ship_kamsarmax", "ship_ultramax",
        "ship_capesize", "ship_handysize"]

# Koden som bestemmer tallene i snapshotet. Hashen av hver fil fryses i
# config. Avviker en fil senere, merkes kjoeringen (code_changed) i
# snapshotet og manifestet. Snapshotet skrives likevel: klokken skal ikke
# stoppe, men avviket skal synes. Se plan, spoersmaal om kodeendringer.
KODEFILER = ["priser.py", "signaler.py", "instrumenter.py", "uran_kilde.py", "laks_innhent.py",
             "kurve_innhent.py", "flagglogg.py", "kapitulasjon_d.py", "overlevelse_c.py",
             "c_manuell.py", "tilbud_b.py", "rigg_b.py", "shipping.py", "bygg_shipping.py",
             "helse.py", "shadow_oos.py"]

HORISONTER = [3, 6, 12, 24, 36]          # modningshendelser, maaneder
KLYNGE_DAGER = 183                       # som flagglogg.KLYNGE_DAGER

F_REGISTER = ["model_id", "created_at", "effective_from", "parent_model", "status", "specification_hash",
              "code_commit", "data_schema_version", "config_file", "notes"]

F_SNAP = [
    # noekler
    "snapshot_id", "snapshot_date", "iso_week", "model_version", "run_id", "segment", "instrument", "level",
    "data_cutoff", "created_at",
    # signaldata (4.1)
    "A_raw", "A_detrended", "A_rolling", "A_anchor", "B", "B1", "B2", "B_rigg_max", "C", "C_open_n",
    "C_measured_n", "D", "D_papers", "S",
    # signalstatus (4.2)
    "watch", "bottom_zone", "strong_candidate", "survival_gate", "d95", "observation_only", "months_in_zone",
    # kontekst (4.3)
    "trend_signal", "trend_12m", "trend_6m", "trend_10m", "above_ma10", "cot_manager", "cot_manager_pct",
    "cot_producer", "cot_date", "curve_12m", "curve_3m", "curve_form", "curve_date", "inventory",
    "supply_metric",
    # datakvalitet (4.4)
    "price_last_observation", "price_real", "price_nominal", "B_last_observation", "C_last_observation",
    "D_last_observation", "data_stale", "stale_fields", "missing_fields", "source_version", "code_changed",
    "observation_date", "publication_date", "available_from",
    # papir (4.5 og 8)
    "company_name", "exchange", "currency", "instrument_type", "instrument_price", "price_date",
    "usd_per_unit", "dividend", "commodity_price", "commodity_beta", "correlation", "residual_correlation",
    "inverse", "tradeable", "on_dashboard", "instrument_eligible", "reason_if_not_eligible", "C_status",
    "C_score", "C_bottom_year", "C_years", "D_instrument", "drawdown_pct", "shares_outstanding", "market_cap"]

F_EVENT = ["event_id", "model_version", "event_date", "iso_week", "segment", "instrument", "event",
           "snapshot_id", "run_id", "episode_id", "new_episode", "macro_cluster_id", "commodity_signal",
           "investable_signal", "A_raw", "A_detrended", "B", "C", "D", "S", "n_instruments", "n_C_open",
           "n_C_tight", "n_C_closed", "n_C_unknown", "n_C_not_applicable", "ref_event_id", "maturity_date",
           "note"]

F_OUTCOME = ["event_id", "model_version", "segment", "instrument", "portfolio_id", "signal_date", "horizon",
             "maturity_date", "commodity_return", "instrument_return", "portfolio_return", "benchmark_return",
             "excess_return", "factor_adjusted_return", "max_drawdown", "max_adverse_excursion",
             "max_favorable_excursion", "share_dilution", "capital_raise", "restructuring", "delisting",
             "bankruptcy", "outcome_status", "calculated_at"]

F_RETTELSE = ["correction_id", "snapshot_id", "field", "original_value", "corrected_value", "error_description",
              "discovered_at", "correction_version"]

F_MANIFEST = ["run_id", "run_date", "iso_week", "model_version", "run_event", "code_commit",
              "configuration_hash", "specification_ok", "code_changed", "raw_data_manifest", "started_at",
              "completed_at", "status", "snapshot_file", "snapshot_rows", "snapshot_sha256", "inndata_sha256",
              "events_new", "events_rows_after", "events_sha256_after", "chain_sha256", "warnings", "errors"]

C_HENDELSE = {"aapen": "C_open", "trang": "C_tight", "stengt": "C_closed", "ukjent": "C_unknown",
              "uaktuell": "C_not_applicable"}


class FinnesAllerede(Exception):
    pass


# ------------------------------------------------------------------ hjelpere
def sha256(tekst):
    return hashlib.sha256(tekst.encode("utf-8")).hexdigest()


def lf(b):
    """Linjeskift som i git (LF), saa hashen blir lik paa Windows og i Actions."""
    return b.replace(b"\r\n", b"\n")


def blob_sha(tekst):
    """Samme sha som git og GitHub gir filen."""
    b = tekst.encode("utf-8")
    return hashlib.sha1(b"blob %d\0" % len(b) + b).hexdigest()


def kanonisk(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def ukenokkel(d):
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def pluss_mnd(d, n):
    import calendar
    m = d.month - 1 + n
    a, m = d.year + m // 12, m % 12 + 1
    return dt.date(a, m, min(d.day, calendar.monthrange(a, m)[1]))


def _dato(x):
    try:
        return dt.date.fromisoformat(str(x)[:10])
    except ValueError:
        return None


def celle(v):
    """NULL er tom celle, aldri 0. Sannhetsverdier skrives true/false."""
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        return repr(round(v, 6))
    if isinstance(v, (list, tuple)):
        return ";".join(str(x) for x in v)
    return str(v)


def til_csv(rader, felt, overskrift=True):
    b = io.StringIO()
    w = csv.DictWriter(b, fieldnames=felt, lineterminator="\n", extrasaction="raise")
    if overskrift:
        w.writeheader()
    for r in rader:
        w.writerow({k: celle(r.get(k)) for k in felt})
    return b.getvalue()


def fra_csv(tekst):
    return list(csv.DictReader(io.StringIO(tekst))) if tekst else []


def sann(x):
    return {"true": True, "false": False}.get(str(x).lower())


def tall(x):
    try:
        return float(x) if x not in (None, "") and not isinstance(x, bool) else None
    except (TypeError, ValueError):
        return None


# ------------------------------------------------------------------ lager
class GitHubLager:
    """Leser og skriver repoet gjennom GitHub-API. opprett() feiler hvis
    filen finnes, erstatt() feiler hvis filen er endret siden den ble lest
    (sha). Begge deler er en del av vernet mot overskriving."""

    def __init__(self, token):
        self.h = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}

    def _get(self, url, headers=None):
        for vent in (2, 4, 8, 0):
            try:
                r = requests.get(url, headers=headers or self.h, params={"ref": BRANCH}, timeout=60)
                if r.status_code < 500:
                    return r
            except requests.RequestException:
                if not vent:
                    raise
            time.sleep(vent)
        return r

    def les(self, sti):
        r = self._get(f"https://api.github.com/repos/{REPO}/contents/{sti}")
        if r.status_code == 404:
            return None, None
        r.raise_for_status()
        j = r.json()
        if j.get("encoding") == "base64" and j.get("content") is not None and (j.get("content") or j.get("size") == 0):
            return base64.b64decode(j["content"]).decode("utf-8"), j["sha"]
        rr = self._get(f"https://api.github.com/repos/{REPO}/contents/{sti}",
                       headers={**self.h, "Accept": "application/vnd.github.raw"})
        rr.raise_for_status()
        return rr.content.decode("utf-8"), j["sha"]

    def liste(self, mappe):
        r = self._get(f"https://api.github.com/repos/{REPO}/contents/{mappe}")
        if r.status_code == 404:
            return []
        r.raise_for_status()
        return sorted(x["name"] for x in r.json() if x.get("type") == "file")

    def _put(self, sti, tekst, sha=None):
        body = {"message": f"oppdatert {sti}", "branch": BRANCH,
                "content": base64.b64encode(tekst.encode("utf-8")).decode()}
        if sha:
            body["sha"] = sha
        r = requests.put(f"https://api.github.com/repos/{REPO}/contents/{sti}", headers=self.h, json=body, timeout=60)
        if r.status_code == 422 and not sha:
            raise FinnesAllerede(sti)
        r.raise_for_status()

    def opprett(self, sti, tekst):
        self._put(sti, tekst)

    def erstatt(self, sti, tekst, sha):
        self._put(sti, tekst, sha)


class LokalLager:
    """Til lokal test: leser fra ut_rot hvis filen finnes der, ellers fra
    inn_rot (repoet). Skriver bare til ut_rot."""

    def __init__(self, inn_rot, ut_rot):
        self.inn, self.ut = inn_rot, ut_rot

    def _sti(self, sti):
        u = os.path.join(self.ut, sti)
        return u if os.path.exists(u) else os.path.join(self.inn, sti)

    def les(self, sti):
        p = self._sti(sti)
        if not os.path.exists(p):
            return None, None
        t = lf(open(p, "rb").read()).decode("utf-8")
        return t, blob_sha(t)

    def liste(self, mappe):
        ut = set()
        for rot in (self.inn, self.ut):
            p = os.path.join(rot, mappe)
            if os.path.isdir(p):
                ut |= {f for f in os.listdir(p) if os.path.isfile(os.path.join(p, f))}
        return sorted(ut)

    def _skriv(self, sti, tekst):
        p = os.path.join(self.ut, sti)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as f:
            f.write(tekst.encode("utf-8"))

    def opprett(self, sti, tekst):
        if self.les(sti)[0] is not None:
            raise FinnesAllerede(sti)
        self._skriv(sti, tekst)

    def erstatt(self, sti, tekst, sha):
        if self.les(sti)[1] != sha:
            raise RuntimeError(f"{sti} er endret siden den ble lest")
        self._skriv(sti, tekst)


def legg_til_rader(lager, sti, felt, nye):
    """Bare tillegg: den nye teksten MAA begynne med den gamle, byte for
    byte. Overskriften maa vaere den samme. Returnerer hele den nye teksten."""
    gml, sha = lager.les(sti)
    if gml is None:
        ny = til_csv(nye, felt)
        lager.opprett(sti, ny)
        return ny
    if gml.split("\n", 1)[0] != ",".join(felt):
        raise RuntimeError(f"{sti}: overskriften er endret, skriver ikke")
    if gml and not gml.endswith("\n"):
        raise RuntimeError(f"{sti}: slutter ikke med linjeskift, skriver ikke")
    ny = gml + til_csv(nye, felt, overskrift=False)
    assert ny.startswith(gml)
    if nye:
        lager.erstatt(sti, ny, sha)
    return ny


# ------------------------------------------------------------------ konfig
def kodehasher(rot):
    ut = {}
    for f in KODEFILER:
        p = os.path.join(rot, f)
        ut[f] = hashlib.sha256(lf(open(p, "rb").read())).hexdigest() if os.path.exists(p) else None
    return ut


def spesifikasjonshash(konfig):
    return sha256(kanonisk({"model": konfig["model"], "spesifikasjon": konfig["spesifikasjon"]}))


def lag_konfig(rot, code_commit, created_at="2026-10-05", effective_from="2026-10-07"):
    k = {
        "model": {"id": MODELL, "status": "champion", "created_at": created_at, "effective_from": effective_from,
                  "parent_model": None, "data_schema_version": SCHEMA},
        "spesifikasjon": {
            "omfang": "Champion v1.0 er A-modellen slik koden er 05.10.2026. B, C, D og kontekst logges som "
                      "data, men styrer ikke signalet. Alle terskler og definisjoner er de som staar i "
                      "kodefilene under, med hashene i kodefiler.",
            "A": {"A_raw": "scores.A: persentil av log realpris mot hele egen historikk, punkt i tid "
                           "(priser.build_segment, expanding_pct), minst 60 mnd",
                  "A_detrended": "scores.Ad: samme mot egen trend (expanding_pct_detrend)",
                  "A_rolling": "scores.Ar: rullende ti aar, vises, inngaar ikke i flagget",
                  "A_anchor": "scores.A2: paritet mot kostnadsanker, bare skipssegmentene",
                  "deflator": "amerikansk KPI (cpi_kopi.csv og reservekjeden i priser.py)"},
            "bunnsone": {"A_raw_min": 80, "A_detrended_min": 80, "felt": "scores.flagg",
                         "observasjonssegmenter": "laks og oljeservice har aldri flagg (scores.observasjon)",
                         "skipssegmenter": "ingen A og ingen bunnsone"},
            "watch": {"regel": "scores.oppsikt: A_raw >= 80 og ikke bunnsone"},
            "strong_candidate": {"definert": False, "merknad": "finnes ikke i dagens kode, logges som NULL"},
            "d95": {"segmenter": ["brent", "wti"], "A_detrended_min": 95, "felt": "scores.flagg_d95",
                    "rolle": "separat eksperimentelt signal, ikke testet, egne hendelser"},
            "B": {"felt": "scores.B", "definisjon": "B2 siste aar fra b_capex.json (tilbud_b.py), bare "
                  "metallene som har B; rigger (rigg_b.py) er kontekst for oljeservice (B_rigg_max)",
                  "beslutningsvariabel": False},
            "C": {"felt": "scores.gate", "definisjon": "overlevelse_c.py og c_manuell.py: kvartaler kontantene "
                  "holder i verste aar, under 8 stengt, oljeservice stengt ved netto gjeld over 1,5 x EK. "
                  "Segmentet er aapent hvis minst ett maalt papir paa tavlen er aapent, ellers trang, ellers "
                  "stengt; fond gir uaktuell (priser.py)",
                  "beslutningsvariabel": False,
                  "exit_ved_C_stenging": "C_forced_exit registreres separat og endrer ikke hovedutfallet"},
            "D": {"felt": "scores.D", "definisjon": "kapitulasjon_d.py: median av papirenes D vektet mot "
                  "temaets kursfall", "beslutningsvariabel": False},
            "S": {"operativ": False, "formel_i_dokumentet": "S = 100 * a^0.4 * b^0.4 * d^0.2",
                  "merknad": "S regnes ikke i dagens kode (scores.S er alltid tom) og logges som NULL. "
                             "Champion S faar egen startdato naar S er definert i koden, og arver ikke "
                             "startdatoen til A."},
            "kontekst": {"trend": "signaler.trend, ikke beslutningsvariabel",
                         "cot": "signaler.cot_for_segmenter, ikke beslutningsvariabel",
                         "kurve": "kurve_innhent og signaler.kurveform, ikke beslutningsvariabel",
                         "inventory": "finnes ikke, NULL", "supply_metric": "finnes ikke, NULL"},
            "ny_episode": {"regel": "foerste bunnsone etter mer enn 12 maaneder uten flagg: segmentets "
                                    "maanedsserie og logg/flagg_uke.csv (flagglogg.ny_innslag), og ingen "
                                    "bunnsone i shadow_events.csv siste 365 dager. Bunnsone som staar ved "
                                    "oppstart er ikke en ny episode.",
                           "pause_mnd": 12,
                           "d95": "ingen d95 i logg/flagg_uke.csv eller shadow_events.csv siste 365 dager"},
            "makroklynge": {"regel": "hypotetiske innganger med hoeyst 183 dager mellom paafoelgende "
                                     "datoer er samme klynge, paa tvers av segmenter", "dager": KLYNGE_DAGER},
            "holdetid": {"primaer_mnd": 24, "sekundaer_mnd": [3, 6, 12, 36],
                         "modningshendelser_mnd": HORISONTER,
                         "inngang": "signaldatoen: kursen i snapshotet den uken (T0)",
                         "primaert_utfall": "24 maaneders avkastning fra foerste signal i en ny episode"},
            "instrumentvalg": {"univers": "papirene paa tavlen for segmentet paa signaldatoen "
                                          "(instrumenter.py), fryses i snapshotet",
                               "instrument_eligible": "paa tavlen og ikke omvendt eksponering",
                               "C_i_universet": "C registreres per papir. Om stengt eller ukjent C utelukker "
                                                "papiret, er ikke avgjort (se plan); investable_signal er "
                                                "derfor NULL i fase 1."},
            "posisjonsstoerrelse": "ikke del av testen",
            "benchmark": "ikke fastsatt i fase 1; fastsettes i en egen evalueringsspesifikasjon foer foerste "
                         "utfall er modent (se plan)",
            "datakvalitet": {"data_stale": "helse.status gul eller roed for segmentets egne rader, "
                                           "innhenting, kpi, C og B, eller FEIL i index.json"},
            "skrivemaate": {"NULL": "tom celle, aldri 0", "en_per_uke": "foerste kjoering i ISO-uken skriver "
                            "snapshotet; senere kjoeringer samme uke skriver det ikke paa nytt"},
            "kodefiler": kodehasher(rot),
        },
        "metadata": {"code_commit": code_commit,
                     "code_commit_merknad": "commiten der config og kodefilene over ligger slik de er hashet",
                     "notes": "Fase 1 av Shadow-OOS. Se notater/shadow_oos_plan.md."},
    }
    k["metadata"]["specification_hash"] = spesifikasjonshash(k)
    return k


def frys(rot, code_commit, erstatt=False, idag=None):
    """Lager config og register. Bare foer effective_from, og bare med
    erstatt hvis de finnes."""
    idag = idag or dt.date.today()
    k = lag_konfig(rot, code_commit)
    if idag >= dt.date.fromisoformat(k["model"]["effective_from"]):
        raise RuntimeError("Champion er i drift; config og register kan ikke lages paa nytt")
    pk, pr = os.path.join(rot, KONFIG), os.path.join(rot, REGISTER)
    if (os.path.exists(pk) or os.path.exists(pr)) and not erstatt:
        raise RuntimeError("config eller register finnes; bruk --erstatt-foer-start")
    os.makedirs(os.path.dirname(pk), exist_ok=True)
    os.makedirs(os.path.dirname(pr), exist_ok=True)
    with open(pk, "wb") as f:
        f.write((json.dumps(k, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
    m = k["model"]
    with open(pr, "wb") as f:
        f.write(til_csv([{"model_id": m["id"], "created_at": m["created_at"], "effective_from": m["effective_from"],
                          "parent_model": m["parent_model"], "status": m["status"],
                          "specification_hash": k["metadata"]["specification_hash"], "code_commit": code_commit,
                          "data_schema_version": SCHEMA, "config_file": KONFIG,
                          "notes": "A-modellen frosset; S ikke operativ og ikke startet"}], F_REGISTER).encode("utf-8"))
    for sti, felt in ((UTFALL, F_OUTCOME), (RETTELSER, F_RETTELSE)):
        p = os.path.join(rot, sti)
        if not os.path.exists(p):
            with open(p, "wb") as f:
                f.write(til_csv([], felt).encode("utf-8"))
    return k


# ------------------------------------------------------------------ snapshot
def _komm(kommentar, noekkel):
    m = re.search(rf"(?:^|\s){noekkel}\s+(-?\d+,\d+)", kommentar or "")
    return float(m.group(1).replace(",", ".")) if m else None


def _helsestatus(helse_json, snapshot_date):
    """{id: status} for alle rader i helse.json, regnet mot snapshotdatoen."""
    import helse
    ut = {}
    for r in (helse_json or {}).get("rader") or []:
        try:
            ut[r["id"]] = helse.status(r, snapshot_date)[0]
        except Exception:
            ut[r["id"]] = "ukjent"
    return ut


def bygg_snapshot(inn, snapshot_date, created_at, run_id, kode_avvik, aapne_innganger=None):
    """Ren funksjon av inndata. inn: dict med index, segmenter (liste),
    kurser (rader for uken), helse, c, b, d (de tre siste bare oppdatert).
    aapne_innganger: {(segment, ticker)} som skal logges selv om papiret er
    tatt av tavlen. Returnerer radene."""
    dato, uke = snapshot_date.isoformat(), ukenokkel(snapshot_date)
    kurs = {r["ticker"]: r for r in inn.get("kurser") or []}
    hs = _helsestatus(inn.get("helse"), snapshot_date)
    felles = [k for k in ("innhenting", "kpi", "c_overlevelse", "b_capex", "b_rigg") if hs.get(k) in ("gul", "rod")]
    felles += [k for k, v in hs.items() if k.startswith("feil_")]
    c_obs = (inn.get("c") or {}).get("oppdatert")
    d_obs = (inn.get("d") or {}).get("oppdatert")
    kilde = f"index {(inn.get('index') or {}).get('oppdatert')}"
    basis = {"snapshot_date": dato, "iso_week": uke, "model_version": MODELL, "run_id": run_id,
             "data_cutoff": created_at, "created_at": created_at, "source_version": kilde,
             "code_changed": ";".join(kode_avvik) if kode_avvik else False, "publication_date": None,
             "available_from": dato}
    rader = []
    for s in inn["segmenter"]:
        sid, sc = s["id"], s.get("scores") or {}
        tr, cot, ku = s.get("trend") or {}, s.get("cot") or {}, s.get("kurve") or {}
        gd = s.get("gate_detalj") or {}
        egne = [k for k, v in hs.items() if (k == sid or k.startswith(sid + "_")) and v in ("gul", "rod")]
        stale = sorted(set(egne + felles))
        seg = {**basis, "snapshot_id": f"{MODELL}|{dato}|{sid}|-", "segment": sid, "instrument": None,
               "level": "segment",
               "A_raw": sc.get("A"), "A_detrended": sc.get("Ad"), "A_rolling": sc.get("Ar"),
               "A_anchor": sc.get("A2"), "B": sc.get("B"), "B1": sc.get("B1"), "B2": sc.get("B2"),
               "B_rigg_max": max([v.get("B2_siste") for v in ((s.get("rigg_b") or {}).get("segmenter") or {}).values()
                                  if v.get("B2_siste") is not None], default=None),
               "C": sc.get("gate"), "C_open_n": gd.get("aapne"), "C_measured_n": gd.get("malte"),
               "D": sc.get("D"), "D_papers": (s.get("d_detalj") or {}).get("D_aksjer"), "S": sc.get("S"),
               "watch": bool(sc.get("oppsikt")), "bottom_zone": bool(sc.get("flagg")), "strong_candidate": None,
               "survival_gate": sc.get("gate"), "d95": sc.get("flagg_d95") if "flagg_d95" in sc else None,
               "observation_only": bool(sc.get("observasjon")) or sid.startswith("ship_"),
               "months_in_zone": sc.get("months_in_zone"),
               "trend_signal": tr.get("signal"), "trend_12m": tr.get("mom12_pst"), "trend_6m": tr.get("mom6_pst"),
               "trend_10m": tr.get("avvik_ma10_pst"), "above_ma10": tr.get("over_ma10"),
               "cot_manager": cot.get("mm_pctl_3aar"), "cot_manager_pct": cot.get("mm_pct"),
               "cot_producer": cot.get("prod_pctl_3aar"), "cot_date": cot.get("dato"),
               "curve_12m": ku.get("helning12"), "curve_3m": ku.get("helning3"), "curve_form": ku.get("form"),
               "curve_date": ku.get("dato"), "inventory": None, "supply_metric": None,
               "price_last_observation": s.get("last_obs"), "price_real": s.get("last_real"),
               "price_nominal": s.get("last_nom"), "B_last_observation": sc.get("B_aar"),
               "C_last_observation": c_obs, "D_last_observation": d_obs,
               "data_stale": bool(stale), "stale_fields": stale,
               "observation_date": s.get("last_obs")}
        seg["missing_fields"] = [k for k in ("A_raw", "A_detrended", "B", "C", "D", "S")
                                 if seg[k] in (None, "ukjent")]
        rader.append(seg)
        paa_tavla = []
        for i in s.get("instrumenter") or []:
            tk = i["ticker"]
            paa_tavla.append(tk)
            rader.append(_papirrad(basis, seg, s, i, kurs.get(tk), dato, on_dashboard=True))
        for (sg, tk) in sorted(aapne_innganger or []):
            if sg == sid and tk not in paa_tavla:
                rader.append(_papirrad(basis, seg, s, {"ticker": tk}, kurs.get(tk), dato, on_dashboard=False))
    return rader


def _papirrad(basis, seg, s, i, k, dato, on_dashboard):
    tk, k = i["ticker"], k or {}
    omvendt = bool(i.get("omvendt"))
    eligible = on_dashboard and not omvendt
    return {**basis, "snapshot_id": f"{MODELL}|{dato}|{s['id']}|{tk}", "segment": s["id"], "instrument": tk,
            "level": "instrument",
            "C": seg["C"], "survival_gate": seg["survival_gate"], "bottom_zone": seg["bottom_zone"],
            "data_stale": seg["data_stale"], "stale_fields": seg["stale_fields"],
            "company_name": i.get("navn"), "exchange": i.get("bors"), "currency": k.get("valuta") or None,
            "instrument_type": i.get("type"), "instrument_price": tall(k.get("kurs")),
            "price_date": k.get("kursdato") or None, "usd_per_unit": tall(k.get("usd_per_enhet")),
            "dividend": tall(k.get("utbytte")), "commodity_price": s.get("last_nom"),
            "commodity_beta": _komm(i.get("kommentar"), "b"), "correlation": _komm(i.get("kommentar"), "r"),
            "residual_correlation": _komm(i.get("kommentar"), "rm"),
            "inverse": omvendt if on_dashboard else None, "tradeable": i.get("handlbar"),
            "on_dashboard": on_dashboard, "instrument_eligible": eligible,
            "reason_if_not_eligible": None if eligible else ("omvendt eksponering" if on_dashboard
                                                             else "tatt av tavlen etter inngang"),
            "C_status": i.get("port"), "C_score": i.get("kvartaler"), "C_bottom_year": i.get("bunnaar"),
            "C_years": i.get("aar_historikk"), "D_instrument": i.get("D"), "drawdown_pct": i.get("fall_pst"),
            "shares_outstanding": None, "market_cap": None,
            "observation_date": k.get("kursdato") or None,
            "missing_fields": [f for f, v in (("instrument_price", k.get("kurs")), ("C_status", i.get("port")),
                                              ("D_instrument", i.get("D"))) if v in (None, "")]}


# ------------------------------------------------------------------ hendelser
def _segrader(rader):
    return {r["segment"]: r for r in rader if r["level"] == "segment"}


def _n_c(rader, sid):
    pap = [r for r in rader if r["level"] == "instrument" and r["segment"] == sid and sann(r["instrument_eligible"])]
    n = {k: 0 for k in C_HENDELSE}
    for r in pap:
        n[r["C_status"] if r["C_status"] in n else ("uaktuell" if str(r["instrument_type"]).lower().startswith(
            ("etf", "etc", "etn", "fond")) else "ukjent")] += 1
    return {"n_instruments": len(pap), "n_C_open": n["aapen"], "n_C_tight": n["trang"], "n_C_closed": n["stengt"],
            "n_C_unknown": n["ukjent"], "n_C_not_applicable": n["uaktuell"]}


def finn_hendelser(naa, forrige, gamle_hend, segmenter, flagg_uke, snapshot_date, snaps_for):
    """naa og forrige: snapshotrader (strenger, som lest fra CSV). gamle_hend:
    tidligere hendelser. segmenter: {id: segment-dict} (maanedsserien til
    pausesjekken). flagg_uke: logg/flagg_uke.csv uten inneværende uke.
    snaps_for(iso_week) -> rader for et tidligere snapshot."""
    from flagglogg import ny_innslag
    dato, uke = snapshot_date.isoformat(), ukenokkel(snapshot_date)
    run_id = naa[0]["run_id"] if naa else ""
    ns, fs = _segrader(naa), _segrader(forrige or [])
    ut, finnes = [], {h["event_id"] for h in gamle_hend}

    def hend(sid, navn, instrument=None, **kw):
        r = ns[sid]
        e = {"event_id": f"{MODELL}|{dato}|{sid}|{instrument or '-'}|{navn}", "model_version": MODELL,
             "event_date": dato, "iso_week": uke, "segment": sid, "instrument": instrument, "event": navn,
             "snapshot_id": f"{MODELL}|{dato}|{sid}|{instrument or '-'}", "run_id": run_id,
             "A_raw": r["A_raw"], "A_detrended": r["A_detrended"], "B": r["B"], "C": r["C"], "D": r["D"],
             "S": r["S"], **kw}
        if e["event_id"] not in finnes:
            finnes.add(e["event_id"])
            ut.append(e)

    start = not fs
    for sid, r in ns.items():
        f = fs.get(sid)
        for felt, navn in (("watch", "watch"), ("bottom_zone", "bottom_zone"), ("d95", "d95")):
            v = sann(r[felt])
            if v is None:
                continue
            g = sann(f[felt]) if f else None
            if g is None:
                if v:
                    hend(sid, f"{navn}_active_at_start",
                         note="sto allerede i tilstanden ved foerste snapshot, ikke en ny episode")
                continue
            if v and not g:
                hend(sid, f"{navn}_enter")
                if navn == "bottom_zone":
                    ok, grunn = ny_innslag(segmenter.get(sid) or {"id": sid}, flagg_uke, snapshot_date)
                elif navn == "d95":
                    grense = str(snapshot_date - dt.timedelta(days=365))
                    ok = not any(x.get("segment") == sid and str(x.get("d95")).lower() in ("true", "1")
                                 and x.get("dato", "") >= grense for x in flagg_uke)
                    grunn = "" if ok else "d95 i loggen innen 12 mnd"
                else:
                    continue
                # Shadow-loggens egne hendelser teller ogsaa, saa regelen ikke
                # hviler paa flagg_uke.csv alene.
                grense = str(snapshot_date - dt.timedelta(days=365))
                egne = [h["event_date"] for h in gamle_hend if h["segment"] == sid and h["event_date"] >= grense
                        and h["event"] in (f"{navn}_enter", f"{navn}_continue", f"{navn}_active_at_start")]
                if ok and egne:
                    ok, grunn = False, f"{navn} i shadow-loggen {max(egne)}, innen 12 mnd"
                if not ok:
                    hend(sid, f"{navn}_reentry_no_new_episode", new_episode=False,
                         note=f"ikke ny episode: {grunn}")
                    continue
                inng = "hypothetical_entry" if navn == "bottom_zone" else "hypothetical_entry_d95"
                klynge = None
                if navn == "bottom_zone":
                    tidl = sorted((h for h in gamle_hend + ut if h["event"] == "hypothetical_entry"),
                                  key=lambda h: h["event_date"])
                    if tidl and (snapshot_date - _dato(tidl[-1]["event_date"])).days <= KLYNGE_DAGER:
                        klynge = tidl[-1]["macro_cluster_id"]
                    else:
                        klynge = f"cluster_{snapshot_date.year}_{snapshot_date.month:02d}"
                hend(sid, inng, episode_id=f"{sid}|{dato}", new_episode=True, macro_cluster_id=klynge,
                     commodity_signal=True, investable_signal=None, **_n_c(naa, sid),
                     note="univers frosset i snapshotet samme uke; investable_signal avventer Frodes "
                          "avgjoerelse om C")
            elif navn == "bottom_zone" and v and g:
                hend(sid, "bottom_zone_continue")
            elif g and not v:
                hend(sid, f"{navn}_exit")
        # C-tilstand for segmentet, bare ved endring
        if f and r["C"] != f["C"] and r["C"] in C_HENDELSE:
            hend(sid, C_HENDELSE[r["C"]], note=f"fra {f['C'] or 'NULL'}")

    # modning og C_forced_exit for aapne innganger
    alle = gamle_hend + ut
    for h in [h for h in alle if h["event"].startswith("hypothetical_entry")]:
        d0 = _dato(h["event_date"])
        for n in HORISONTER:
            md = pluss_mnd(d0, n)
            if snapshot_date >= md and h["segment"] in ns:
                hend(h["segment"], f"{n}m_maturity", ref_event_id=h["event_id"], episode_id=h.get("episode_id"),
                     maturity_date=md.isoformat())
        if h["event"] != "hypothetical_entry" or snapshot_date > pluss_mnd(d0, 24) or d0 == snapshot_date:
            continue
        univ = [r for r in snaps_for(h["iso_week"]) if r["level"] == "instrument" and r["segment"] == h["segment"]
                and sann(r["instrument_eligible"])]
        naa_c = {r["instrument"]: r["C_status"] for r in naa if r["level"] == "instrument"
                 and r["segment"] == h["segment"]}
        for r in univ:
            if naa_c.get(r["instrument"]) == "stengt" and r["C_status"] != "stengt" and h["segment"] in ns:
                if not any(x["event"] == "C_forced_exit" and x.get("ref_event_id") == h["event_id"]
                           and x.get("instrument") == r["instrument"] for x in alle + ut):
                    hend(h["segment"], "C_forced_exit", instrument=r["instrument"], ref_event_id=h["event_id"],
                         episode_id=h.get("episode_id"), note=f"C var {r['C_status'] or 'NULL'} ved inngang")
    return ut


def aapne_innganger(gamle_hend, snapshot_date, snaps_for):
    """Papirer i universet til innganger de siste 37 maanedene."""
    ut = set()
    for h in gamle_hend:
        if h["event"] != "hypothetical_entry" or snapshot_date > pluss_mnd(_dato(h["event_date"]), 37):
            continue
        for r in snaps_for(h["iso_week"]):
            if r["level"] == "instrument" and r["segment"] == h["segment"] and sann(r["instrument_eligible"]):
                ut.add((h["segment"], r["instrument"]))
    return ut


# ------------------------------------------------------------------ kontroll
def kontroller(lager):
    """Punkt 46: ingen gamle snapshots er endret. Sjekker hvert snapshot og
    hver inndatafil mot hashen i manifestet, hashkjeden, at hendelsesloggen
    begynner med det den var etter hver kjoering, og config mot registeret.
    Returnerer en liste med avvik (tom er bra)."""
    avvik = []
    man = fra_csv(lager.les(MANIFEST)[0])
    hend_tekst = lager.les(HENDELSER)[0] or ""
    kjede = ""
    for m in man:
        if m["status"] not in ("ok", "ok_gjenopptatt"):
            continue
        t = lager.les(m["snapshot_file"])[0]
        if t is None or sha256(t) != m["snapshot_sha256"]:
            avvik.append(f"snapshot endret eller borte: {m['snapshot_file']}")
        ti = lager.les(f"{INNDATA_MAPPE}/{m['iso_week']}.json")[0]
        if ti is None or sha256(ti) != m["inndata_sha256"]:
            avvik.append(f"inndata endret eller borte: {m['iso_week']}")
        kjede = sha256(kjede + m["snapshot_sha256"] + m["inndata_sha256"] + m["events_sha256_after"])
        if kjede != m["chain_sha256"]:
            avvik.append(f"hashkjeden brutt ved {m['run_id']}")
        n = int(m["events_rows_after"] or 0)
        prefiks = "".join(hend_tekst.splitlines(keepends=True)[:n + 1]) if n else ""
        if n and sha256(prefiks) != m["events_sha256_after"]:
            avvik.append(f"hendelser endret foer {m['run_id']}")
    kt, rt = lager.les(KONFIG)[0], lager.les(REGISTER)[0]
    if kt is None or rt is None:
        avvik.append("config eller register mangler")
    else:
        k = json.loads(kt)
        reg = {r["model_id"]: r for r in fra_csv(rt)}.get(MODELL)
        h = spesifikasjonshash(k)
        if h != k["metadata"]["specification_hash"] or not reg or reg["specification_hash"] != h:
            avvik.append("config stemmer ikke med specification_hash i registeret")
    return avvik


def kodeavvik(konfig, rot):
    frosset = konfig["spesifikasjon"]["kodefiler"]
    naa = kodehasher(rot)
    return sorted(f for f in frosset if naa.get(f) != frosset[f])


# ------------------------------------------------------------------ kjoering
def kjor(lager, rot=None, naa=None, run_event=None, code_commit=None, note=print):
    """Hele den ukentlige kjoeringen. naa: tidspunkt (UTC), standard naa."""
    rot = rot or os.path.dirname(os.path.abspath(__file__))
    naa = naa or dt.datetime.now(dt.timezone.utc)
    snapshot_date, started = naa.date(), naa.strftime("%Y-%m-%d %H:%M:%S")
    uke = ukenokkel(snapshot_date)
    konfig = json.loads(lager.les(KONFIG)[0])
    eff = dt.date.fromisoformat(konfig["model"]["effective_from"])
    if snapshot_date < eff:
        note(f"   shadow: {MODELL} starter {eff}, ingenting skrevet")
        return None
    run_id = f"{MODELL}|{uke}|{started}"
    varsler, feil = [], kontroller(lager)
    spes_ok = spesifikasjonshash(konfig) == konfig["metadata"]["specification_hash"]
    avvik = kodeavvik(konfig, rot)
    if avvik:
        varsler.append("kode endret siden frysing: " + ", ".join(avvik))

    snapsti, innsti = f"{SNAP_MAPPE}/{uke}.csv", f"{INNDATA_MAPPE}/{uke}.json"
    man = fra_csv(lager.les(MANIFEST)[0])
    if any(m["iso_week"] == uke and m["status"] in ("ok", "ok_gjenopptatt") for m in man):
        _manifest(lager, man, {"run_id": run_id, "run_date": snapshot_date, "iso_week": uke,
                               "model_version": MODELL, "run_event": run_event, "code_commit": code_commit,
                               "configuration_hash": konfig["metadata"]["specification_hash"],
                               "specification_ok": spes_ok, "code_changed": avvik or False, "started_at": started,
                               "completed_at": started, "status": "hoppet_over_uke_finnes",
                               "warnings": varsler, "errors": feil})
        note(f"   shadow: snapshot for {uke} finnes, ikke skrevet paa nytt")
        return "hoppet_over"

    def jles(sti):
        t, sha = lager.les(sti)
        lest[sti] = sha
        return json.loads(t) if t else None
    lest = {}
    hend_gml = fra_csv(lager.les(HENDELSER)[0])
    filer = lager.liste(SNAP_MAPPE)
    cache = {}

    def snaps_for(w):
        if w not in cache:
            cache[w] = fra_csv(lager.les(f"{SNAP_MAPPE}/{w}.csv")[0])
        return cache[w]

    idx = jles("index.json") or {}
    segmenter = []
    for sid in list(idx.get("segmenter") or []) + SKIP:
        d = jles(f"segments/{sid}.json")
        if d:
            segmenter.append(d)
        else:
            varsler.append(f"segments/{sid}.json mangler")
    kt, ksha = lager.les("logg/kurser_uke.csv")
    lest["logg/kurser_uke.csv"] = ksha
    kurser = [r for r in fra_csv(kt) if r.get("uke") == uke]
    if not kurser:
        varsler.append(f"ingen kurser for {uke} i logg/kurser_uke.csv")
    ft, fsha = lager.les("logg/flagg_uke.csv")
    lest["logg/flagg_uke.csv"] = fsha
    flagg_uke = [r for r in fra_csv(ft) if r.get("uke") != uke]
    inn = {"index": idx, "segmenter": segmenter, "kurser": kurser, "helse": jles("helse.json"),
           "c": {"oppdatert": (jles("c_overlevelse.json") or {}).get("oppdatert")},
           "d": {"oppdatert": (jles("d_kapitulasjon.json") or {}).get("oppdatert")}}
    for sti in ("b_capex.json", "b_rigg.json", "c_manuell.json", "b_manuell.json", KONFIG):
        lest[sti] = lager.les(sti)[1]

    status = "ok"
    eksisterer = lager.les(snapsti)[0]
    if eksisterer is None:
        rader = bygg_snapshot(inn, snapshot_date, started, run_id, avvik,
                              aapne_innganger(hend_gml, snapshot_date, snaps_for))
        inndata = json.dumps({"run_id": run_id, "run_event": run_event, "code_commit": code_commit,
                              "filer_git_blob_sha": dict(sorted(lest.items())),
                              "kodefiler_sha256": kodehasher(rot)}, ensure_ascii=False, indent=1) + "\n"
        snaptekst = til_csv(rader, F_SNAP)
        try:
            lager.opprett(innsti, inndata)
        except FinnesAllerede:
            inndata = lager.les(innsti)[0]
            varsler.append("inndatafil fantes fra avbrutt kjoering, beholdt")
        lager.opprett(snapsti, snaptekst)
    else:
        # En tidligere kjoering denne uken skrev snapshotet, men ble ikke
        # ferdig. Snapshotet regnes ikke paa nytt; hendelsene regnes fra det
        # som ble lagret.
        snaptekst, status = eksisterer, "ok_gjenopptatt"
        inndata = lager.les(innsti)[0] or ""
        run_id = fra_csv(snaptekst)[0]["run_id"]
        varsler.append("snapshot fantes fra avbrutt kjoering, hendelser regnet fra det lagrede")
    lagret = fra_csv(snaptekst)
    tidl = [f[:-4] for f in filer if f.endswith(".csv") and f[:-4] < uke]
    forrige = snaps_for(tidl[-1]) if tidl else []
    nye = finn_hendelser(lagret, forrige, hend_gml, {s["id"]: s for s in segmenter}, flagg_uke, snapshot_date,
                         snaps_for)
    for h in nye:
        h["run_id"] = run_id
    hend_ny = legg_til_rader(lager, HENDELSER, F_EVENT, nye)
    n_hend = len(hend_ny.splitlines()) - 1
    kjede_forrige = next((m["chain_sha256"] for m in reversed(man) if m["status"] in ("ok", "ok_gjenopptatt")), "")
    s_sha, i_sha, h_sha = sha256(snaptekst), sha256(inndata), sha256(hend_ny)
    _manifest(lager, man, {
        "run_id": run_id, "run_date": snapshot_date, "iso_week": uke, "model_version": MODELL,
        "run_event": run_event, "code_commit": code_commit,
        "configuration_hash": konfig["metadata"]["specification_hash"], "specification_ok": spes_ok,
        "code_changed": avvik or False, "raw_data_manifest": innsti, "started_at": started,
        "completed_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S"), "status": status,
        "snapshot_file": snapsti, "snapshot_rows": len(lagret), "snapshot_sha256": s_sha, "inndata_sha256": i_sha,
        "events_new": len(nye), "events_rows_after": n_hend, "events_sha256_after": h_sha,
        "chain_sha256": sha256(kjede_forrige + s_sha + i_sha + h_sha), "warnings": varsler, "errors": feil})
    note(f"   shadow: {uke} {len(lagret)} rader, {len(nye)} hendelser"
         + (f", {len(feil)} integritetsavvik" if feil else "") + (f", kode endret: {', '.join(avvik)}" if avvik else ""))
    return status


def _manifest(lager, man, rad):
    legg_til_rader(lager, MANIFEST, F_MANIFEST, [rad])


def kjor_actions(note=print):
    """Kalles fra bygg_shipping.py."""
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        note("   shadow: GITHUB_TOKEN mangler, ingenting skrevet")
        return None
    return kjor(GitHubLager(token), run_event=os.environ.get("GITHUB_EVENT_NAME"),
                code_commit=os.environ.get("GITHUB_SHA"), note=note)


if __name__ == "__main__":
    rot = os.path.dirname(os.path.abspath(__file__))
    a = sys.argv[1:]
    if a and a[0] == "frys":
        c = a[a.index("--commit") + 1] if "--commit" in a else None
        k = frys(rot, c, erstatt="--erstatt-foer-start" in a)
        print("specification_hash", k["metadata"]["specification_hash"])
    elif a and a[0] == "kontroller":
        lag = GitHubLager(os.environ["GITHUB_TOKEN"]) if os.environ.get("GITHUB_TOKEN") else LokalLager(rot, rot)
        av = kontroller(lag)
        print("\n".join(av) if av else "ingen avvik")
    elif a and a[0] == "test":
        naa = dt.datetime.fromisoformat(a[2]).replace(tzinfo=dt.timezone.utc) if len(a) > 2 else None
        print(kjor(LokalLager(rot, a[1]), rot, naa=naa, run_event="lokal_test"))
    else:
        print(__doc__ or "se toppen av fila")
