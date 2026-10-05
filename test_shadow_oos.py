# ---------------------------------------------------------------------------
# Tester for shadow_oos.py (punkt 46 og 47 i dokumentet). Kjoeres lokalt mot
# dagens filer i repoet, uten nett og uten aa skrive til repoet:
#
#   python test_shadow_oos.py
#
# Alt skrives til en midlertidig mappe. Testene virker ogsaa med pytest.
# ---------------------------------------------------------------------------

import datetime as dt
import json, os, shutil, tempfile

import shadow_oos as so

ROT = os.path.dirname(os.path.abspath(__file__))
UTC = dt.timezone.utc


def _naa(d, kl="06:40:00"):
    return dt.datetime.fromisoformat(f"{d} {kl}").replace(tzinfo=UTC)


def _lager():
    return so.LokalLager(ROT, tempfile.mkdtemp(prefix="shadow_test_"))


def _osebx(tk):
    return {"kurs": 2067.06, "valuta": "NOK", "kursdato": "2026-10-05", "utbytte": []} if tk == "OSEBX.OL" \
        else {"kurs": 0.1, "valuta": "USD", "kursdato": "2026-10-05", "utbytte": []}


def _kjor(lager, d, kl="06:40:00", oppdatert=None):
    """Kjoerer som om prisinnhentingen gikk samme dag (eller paa `oppdatert`)."""
    idx = json.loads(_les(lager, "index.json"))
    idx["oppdatert"] = f"{oppdatert or d} 06:27:00"
    lager._skriv("index.json", json.dumps(idx, ensure_ascii=False))
    return so.kjor(lager, ROT, naa=_naa(d, kl), run_event="test", note=lambda *a: None, kursfunk=_osebx)


def _les(lager, sti):
    return lager.les(sti)[0]


def _endre_segment(lager, sid, fn):
    d = json.loads(_les(lager, f"segments/{sid}.json"))
    fn(d)
    lager._skriv(f"segments/{sid}.json", json.dumps(d, ensure_ascii=False))


def test_ikke_foer_start():
    l = _lager()
    assert _kjor(l, "2026-10-06") is None
    assert l.liste(so.SNAP_MAPPE) == []
    assert _les(l, so.MANIFEST) is None


def test_uken_starter_onsdag():
    assert so.periodenokkel(dt.date(2026, 10, 7)) == "2026-W41"      # onsdag
    assert so.periodenokkel(dt.date(2026, 10, 12)) == "2026-W41"     # mandag etter
    assert so.periodenokkel(dt.date(2026, 10, 13)) == "2026-W41"     # tirsdag etter
    assert so.periodenokkel(dt.date(2026, 10, 14)) == "2026-W42"
    l = _lager()
    assert _kjor(l, "2026-10-07") == "ok"
    # kjoering for haand mandag tar ikke plassen til onsdag 14.10
    assert _kjor(l, "2026-10-12", "10:00:00", oppdatert="2026-10-12") == "hoppet_over"
    assert _kjor(l, "2026-10-14") == "ok"
    assert l.liste(so.SNAP_MAPPE) == ["2026-W41.csv", "2026-W42.csv"]


def test_venter_paa_onsdagsoppdateringen():
    l = _lager()
    # onsdag, men prisene er fra forrige uke: ingenting skrives
    assert _kjor(l, "2026-10-07", "05:00:00", oppdatert="2026-09-30") == "venter"
    assert l.liste(so.SNAP_MAPPE) == []
    assert _kjor(l, "2026-10-07") == "ok"
    man = so.fra_csv(_les(l, so.MANIFEST))
    assert [m["status"] for m in man] == ["venter_paa_onsdagsoppdatering", "ok"]
    assert so.kontroller(l) == []


def test_snapshots_are_immutable():
    l = _lager()
    assert _kjor(l, "2026-10-07") == "ok"
    sti = f"{so.SNAP_MAPPE}/2026-W41.csv"
    foer = _les(l, sti)
    assert foer and len(so.fra_csv(foer)) > 50
    # ny kjoering samme uke, med endrede tall: snapshotet skal staa
    _endre_segment(l, "kobber", lambda d: d["scores"].update(A=99.9))
    assert _kjor(l, "2026-10-08", "12:00:00") == "hoppet_over"
    assert _les(l, sti) == foer
    # neste uke: ny fil, den gamle uendret
    assert _kjor(l, "2026-10-14") == "ok"
    assert _les(l, sti) == foer
    assert so.kontroller(l) == []
    man = so.fra_csv(_les(l, so.MANIFEST))
    assert [m["status"] for m in man] == ["ok", "hoppet_over_uke_finnes", "ok"]
    # manipulert gammelt snapshot skal oppdages
    l._skriv(sti, foer.replace("champion_v1_0", "champion_v1_1", 1))
    assert any("snapshot endret" in a for a in so.kontroller(l))


def test_hendelser_kan_ikke_skrives_om():
    l = _lager()
    _kjor(l, "2026-10-07")
    _kjor(l, "2026-10-14")
    t = _les(l, so.HENDELSER)
    l._skriv(so.HENDELSER, t + "")       # uendret er ok
    assert so.kontroller(l) == []
    linjer = t.splitlines(keepends=True)
    if len(linjer) > 1:
        l._skriv(so.HENDELSER, linjer[0] + "".join(linjer[2:]))
        assert any("hendelser endret" in a for a in so.kontroller(l))


def test_legg_til_er_bare_tillegg():
    l = _lager()
    so.legg_til_rader(l, "shadow/x.csv", ["a", "b"], [{"a": 1, "b": None}])
    so.legg_til_rader(l, "shadow/x.csv", ["a", "b"], [{"a": 2, "b": True}])
    assert _les(l, "shadow/x.csv") == "a,b\n1,\n2,true\n"
    try:
        so.legg_til_rader(l, "shadow/x.csv", ["a", "c"], [{"a": 3, "c": 1}])
        assert False, "skulle feilet paa ny overskrift"
    except RuntimeError:
        pass
    try:
        l.opprett("shadow/x.csv", "noe annet")
        assert False, "opprett skulle feilet"
    except so.FinnesAllerede:
        pass


def test_no_future_data():
    l = _lager()
    _kjor(l, "2026-10-07")
    for r in so.fra_csv(_les(l, f"{so.SNAP_MAPPE}/2026-W41.csv")):
        sd = r["snapshot_date"]
        assert r["available_from"] <= sd
        if r["observation_date"]:
            assert r["observation_date"][:7] <= sd[:7] and r["observation_date"][:10] <= sd, r["snapshot_id"]
        if r["price_date"]:
            assert r["price_date"] <= sd


def test_null_er_ikke_null():
    l = _lager()
    _kjor(l, "2026-10-07")
    rader = so.fra_csv(_les(l, f"{so.SNAP_MAPPE}/2026-W41.csv"))
    seg = {r["segment"]: r for r in rader if r["level"] == "segment"}
    assert all(r["S"] == "" for r in seg.values())                 # S er ikke operativ
    assert all(r["strong_candidate"] == "" for r in seg.values())
    assert seg["ship_vlcc"]["A_raw"] == ""
    assert "S" in seg["brent"]["missing_fields"]
    ref = [r for r in rader if r["level"] == "benchmark"]
    assert len(ref) == 1 and ref[0]["instrument"] == "OSEBX.OL" and ref[0]["currency"] == "NOK"


def test_c_stengt_er_ikke_kjoepbar():
    l = _lager()
    _kjor(l, "2026-10-07")
    for r in so.fra_csv(_les(l, f"{so.SNAP_MAPPE}/2026-W41.csv")):
        if r["level"] != "instrument":
            continue
        if r["C_status"] == "stengt":
            assert r["instrument_eligible"] == "false" and r["reason_if_not_eligible"] == "C stengt"
        elif r["inverse"] == "false":
            assert r["instrument_eligible"] == "true", r["snapshot_id"]      # ogsaa ukjent C


def test_reproduserbar():
    """Punkt 47: samme inndata, kode og konfig gir samme snapshot."""
    l = _lager()
    idx = json.loads(_les(l, "index.json"))
    segs = [json.loads(_les(l, f"segments/{s}.json")) for s in idx["segmenter"] + so.SKIP]
    inn = {"index": idx, "segmenter": segs, "kurser": [], "helse": json.loads(_les(l, "helse.json"))}
    a = so.til_csv(so.bygg_snapshot(inn, dt.date(2026, 10, 7), "2026-10-07 06:40:00", "r", []), so.F_SNAP)
    b = so.til_csv(so.bygg_snapshot(inn, dt.date(2026, 10, 7), "2026-10-07 06:40:00", "r", []), so.F_SNAP)
    assert so.sha256(a) == so.sha256(b)


def test_bunnsone_episode_og_c_exit():
    """Kunstig bunnsone i nikkel: inngang, fortsettelse, C-stenging, utgang,
    og at en ny bunnsone innen tolv maaneder ikke blir ny episode."""
    l = _lager()
    _kjor(l, "2026-10-07")
    seg0 = json.loads(_les(l, "segments/nikkel.json"))
    tk = next(i["ticker"] for i in seg0["instrumenter"] if not i.get("omvendt"))

    def inn(d):
        d["scores"].update(flagg=True, oppsikt=False, A=85.0, Ad=82.0)
        d["series"][-1]["flagg"] = True
        for i in d["instrumenter"]:
            if i["ticker"] == tk:
                i["port"] = "aapen"
    _endre_segment(l, "nikkel", inn)
    _kjor(l, "2026-10-14")
    _endre_segment(l, "nikkel", lambda d: [i.update(port="stengt") for i in d["instrumenter"] if i["ticker"] == tk])
    _kjor(l, "2026-10-21")

    def ut(d):
        d["scores"].update(flagg=False)
        d["series"][-1]["flagg"] = False
    _endre_segment(l, "nikkel", ut)
    _kjor(l, "2026-10-28")
    _endre_segment(l, "nikkel", inn)
    _kjor(l, "2026-11-04")
    h = [x for x in so.fra_csv(_les(l, so.HENDELSER)) if x["segment"] == "nikkel"]
    ev = [(x["event_date"], x["event"]) for x in h]
    assert ("2026-10-14", "bottom_zone_enter") in ev
    assert ("2026-10-14", "hypothetical_entry") in ev
    assert ("2026-10-21", "bottom_zone_continue") in ev
    assert ("2026-10-21", "C_forced_exit") in ev
    assert ("2026-10-28", "bottom_zone_exit") in ev
    assert ("2026-11-04", "bottom_zone_reentry_no_new_episode") in ev
    assert sum(1 for x in h if x["event"] == "hypothetical_entry") == 1
    e = next(x for x in h if x["event"] == "hypothetical_entry")
    assert e["macro_cluster_id"] == "cluster_2026_10" and e["investable_signal"] == "true"
    assert int(e["n_instruments"]) >= int(e["n_eligible"]) >= 1
    assert so.kontroller(l) == []


def test_klynge_regnes_fra_foerste_inngang():
    """Innganger dag 0, 147 og 287: kjedet ville gitt én klynge (140 dager
    mellom de to siste). Regelen fra klyngens foerste inngang gir to."""
    l = _lager()
    _kjor(l, "2026-10-07")

    def flagg(paa):
        def fn(d):
            d["scores"].update(flagg=paa, oppsikt=False)
            d["series"][-1]["flagg"] = paa
        return fn
    for sid, inn, ut in (("nikkel", "2026-10-14", "2026-10-21"), ("sink", "2027-03-10", "2027-03-17"),
                         ("kakao", "2027-07-28", "2027-08-04")):
        _endre_segment(l, sid, flagg(True))
        _kjor(l, inn)
        _endre_segment(l, sid, flagg(False))
        _kjor(l, ut)
    e = {x["segment"]: x["macro_cluster_id"] for x in so.fra_csv(_les(l, so.HENDELSER))
         if x["event"] == "hypothetical_entry"}
    assert e == {"nikkel": "cluster_2026_10", "sink": "cluster_2026_10", "kakao": "cluster_2027_07"}, e
    assert so.kontroller(l) == []


def test_kodeendring_merkes():
    k = json.loads(open(os.path.join(ROT, so.KONFIG), encoding="utf-8").read())
    assert so.kodeavvik(k, ROT) == [], "kodefilene i repoet er endret etter frysing"
    tmp = tempfile.mkdtemp(prefix="shadow_kode_")
    for f in so.KODEFILER:
        shutil.copy(os.path.join(ROT, f), tmp)
    with open(os.path.join(tmp, "priser.py"), "a", encoding="utf-8") as f:
        f.write("\n# endring\n")
    assert so.kodeavvik(k, tmp) == ["priser.py"]


def test_config_og_register():
    l = so.LokalLager(ROT, ROT)
    k = json.loads(_les(l, so.KONFIG))
    assert so.spesifikasjonshash(k) == k["metadata"]["specification_hash"]
    reg = so.fra_csv(_les(l, so.REGISTER))
    assert reg[0]["specification_hash"] == k["metadata"]["specification_hash"]
    assert k["model"]["effective_from"] == "2026-10-07"


if __name__ == "__main__":
    feil = 0
    for navn, f in sorted(globals().items()):
        if navn.startswith("test_") and callable(f):
            try:
                f()
                print(f"OK    {navn}")
            except Exception as e:
                feil += 1
                print(f"FEIL  {navn}: {type(e).__name__}: {e}")
    print(f"\n{feil} feil")
    raise SystemExit(1 if feil else 0)
