# ---------------------------------------------------------------------------
# ukerapport: ukens tall som en fil i repoet (Frodes bestilling 12.11.2026,
# steg 5 i notater/2026-11-11_gjennomgang.md).
#
# HVORFOR. Ukeloggen har bare ligget i claude.ai-prosjektet
# «Handelsalgoritme», skrevet av onsdagsrutinen. Det er den eneste delen av
# prosjektet som ikke overlever en konto. Denne modulen skriver de samme
# tallene til logg/uke/<uke>.md fra filene i repoet.
#
# DEN ERSTATTER IKKE RUTINENS RAPPORT. Et skript kan rapportere fakta, men
# ikke diagnose, og det er rutinens tolkning som har fanget feil som
# uranprisen 04.11.2026. Rutinen skriver ukeloggen som foer; denne filen er et
# tillegg, og den sier det selv i toppen.
#
# ROBUSTHET
#   - skriver med opprett(), aldri erstatt: en uke som alt har en rapport
#     roeres ikke, saa reservekjoeringen kan ikke skrive over hovedkjoeringen,
#   - hver del er pakket for seg: en fil som mangler eller er uleselig gir en
#     linje om det, ikke et unntak,
#   - ingen nettkall, bare filer som alt ligger i repoet,
#   - leser ingenting fra shadow/ og skriver ingenting dit.
#
# Kalles fra shadow_challenger.kjor, sist, som kontekstmodulene. Da er
# segmentene, skipssegmentene, flaggloggen, helse, kontekstfilene og
# miljoeloggen skrevet.
# ---------------------------------------------------------------------------

import calendar
import datetime as dt
import json
from zoneinfo import ZoneInfo

import shadow_oos as so

MAPPE = "logg/uke"
OSLO = ZoneInfo("Europe/Oslo")
UTC = dt.timezone.utc
COT_SEG = ("brent", "wti", "henryhub", "gold", "kobber", "kakao", "palmeolje")
ORD = {"gronn": "gr\u00f8nn", "gul": "gul", "rod": "r\u00f8d", "ukjent": "ukjent"}


# ------------------------------------------------------------------ formatering
def n(x, d=1):
    """Tall med komma som desimaltegn, eller en tankestrekfri strek."""
    if x is None or isinstance(x, bool):
        return "-"
    try:
        return f"{float(x):.{d}f}".replace(".", ",")
    except (TypeError, ValueError):
        return "-"


def norsk_tid(utc_tekst):
    """'YYYY-MM-DD HH:MM:SS' i UTC til norsk tid. Returnerer teksten uendret
    hvis den ikke kan tolkes, saa rapporten aldri feiler paa et tidsstempel."""
    try:
        t = dt.datetime.fromisoformat(str(utc_tekst).strip())
        return t.replace(tzinfo=UTC).astimezone(OSLO).strftime("%d.%m.%Y %H:%M")
    except Exception:
        return str(utc_tekst)


def _les_json(lager, sti):
    try:
        t = lager.les(sti)[0]
        return json.loads(t) if t else None
    except Exception:
        return None


# ------------------------------------------------------------------ datahelse
def _slutt_neste(slutt, frekvens):
    """Siste dag i perioden etter den som slutter paa `slutt`."""
    d = dt.date.fromisoformat(slutt)
    if frekvens == "mnd":
        aar, mnd = (d.year + 1, 1) if d.month == 12 else (d.year, d.month + 1)
        return dt.date(aar, mnd, calendar.monthrange(aar, mnd)[1])
    if frekvens == "aar":
        return dt.date(d.year + 1, 12, 31)
    return d + dt.timedelta(days=7)          # uke og dag


def helsestatus(rad, idag):
    """Samme regel som staar i toppen av helse.py: forventet er slutten av
    neste periode pluss etterslep, groenn til pluss 3 dager, gul til pluss 7,
    roed over. Manuelle poster er roede naar dagens dato er etter grense.
    En rad som alt har status beholder den."""
    if rad.get("status"):
        return rad["status"]
    if rad.get("grense"):
        try:
            return "rod" if idag > dt.date.fromisoformat(rad["grense"]) else "gronn"
        except Exception:
            return "ukjent"
    try:
        forventet = _slutt_neste(rad["slutt"], rad.get("frekvens", "mnd"))
        forventet += dt.timedelta(days=int(rad.get("etterslep") or 0))
    except Exception:
        return "ukjent"
    if idag <= forventet + dt.timedelta(days=3):
        return "gronn"
    return "gul" if idag <= forventet + dt.timedelta(days=7) else "rod"


# ------------------------------------------------------------------ delene
def _del_segmenter(lager, idx, L):
    ider = list(idx.get("segmenter") or [])
    skip = ["ship_vlcc", "ship_suezmax", "ship_aframax", "ship_kamsarmax",
            "ship_ultramax", "ship_capesize", "ship_handysize"]
    rader, mangler_D, flagg, oppsikt, d95 = [], [], [], [], {}
    for sid in ider + skip:
        d = _les_json(lager, f"segments/{sid}.json")
        if d is None:
            rader.append({"id": sid, "navn": sid, "feil": "filen mangler"})
            continue
        s = d.get("scores") or {}
        rader.append({"id": sid, "navn": d.get("name") or sid, "A": s.get("A"),
                      "Ad": s.get("Ad"), "Ar": s.get("Ar"), "B2": s.get("B2"),
                      "D": s.get("D"), "siste": d.get("last_obs"),
                      "gate": s.get("gate"), "cot": d.get("cot")})
        if s.get("D") is None and not sid.startswith("ship_"):
            mangler_D.append(sid)
        if s.get("flagg"):
            flagg.append(d.get("name") or sid)
        if s.get("oppsikt"):
            oppsikt.append(d.get("name") or sid)
        if sid in ("brent", "wti"):
            d95[sid] = (s.get("flagg_d95"), s.get("Ad"))

    L.append(f"Segmenter lest: {len(rader)} ({len(ider)} prissegmenter, {len(skip)} skip).")
    L.append("")
    L.append("| Segment | A | Ad | Ar | B2 | D | Siste obs. | Port C |")
    L.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for r in sorted(rader, key=lambda x: (x.get("A") is None, -(x.get("A") or 0))):
        if r.get("feil"):
            L.append(f"| {r['navn']} | {r['feil']} | | | | | | |")
            continue
        L.append(f"| {r['navn']} | {n(r['A'])} | {n(r['Ad'])} | {n(r['Ar'])} | "
                 f"{n(r['B2'], 2)} | {n(r['D'])} | {r.get('siste') or '-'} | {r.get('gate') or '-'} |")
    L.append("")
    L.append(f"- Bunnsone: {', '.join(flagg) if flagg else 'ingen'}")
    L.append(f"- Under oppsikt: {', '.join(oppsikt) if oppsikt else 'ingen'}")
    for sid in ("brent", "wti"):
        if sid in d95:
            staar, ad = d95[sid]
            L.append(f"- Parallelt signal d95, {sid}: {'ja' if staar else 'nei'} "
                     f"(detrendet A {n(ad)}). Frodes valg, ikke testet.")
    L.append(f"- Mangler D: {', '.join(mangler_D) if mangler_D else 'ingen'}")
    cot = [r for r in rader if r.get("cot")]
    if cot:
        biter = []
        for r in cot:
            p = (r["cot"] or {}).get("mm_pctl_3aar")
            merke = " (ytterkant)" if isinstance(p, (int, float)) and (p <= 10 or p >= 90) else ""
            biter.append(f"{r['id']} {n(p, 1)}{merke}")
        L.append("- COT, forvalternes persentil mot tre \u00e5r: " + ", ".join(biter))
    return rader


def _del_marked(lager, idx, L):
    L.append("")
    L.append("## Marked og kontekst")
    L.append("")
    dato_idx = str(idx.get("oppdatert") or "")[:10]

    vix = _les_json(lager, "marked.json")
    L.append(f"- VIX: {n((vix or {}).get('verdi'), 2)} per {(vix or {}).get('t', '-')}, "
             f"persentil {n((vix or {}).get('pctl_alle'), 0)}" if vix else "- VIX: filen mangler")

    dol = _les_json(lager, "dollar.json") or {}
    for k, navn in (("dxy", "DXY"), ("usdnok", "USD/NOK")):
        f = dol.get(k)
        L.append(f"- {navn}: {n((f or {}).get('verdi'), 4)} per {(f or {}).get('t', '-')}, "
                 f"persentil {n((f or {}).get('pctl_alle'), 0)}, "
                 f"12 mnd {n((f or {}).get('endring_12m_pst'), 1)} %"
                 if f else f"- {navn}: mangler")

    for sti, navn, felt in (("gass_b.json", "Tilbud B, gass", ("B", "endring_12m_logpst", "mnd")),
                            ("laks_biomasse.json", "Biomasse laks", ("dB", "mnd")),
                            ("uran_kontrakt.json", "Uran, kontrakt", ("kontrakt", "spot", "spread_pst", "mnd"))):
        d = _les_json(lager, sti)
        if not d:
            L.append(f"- {navn}: filen mangler")
            continue
        fersk = "" if str(d.get("laget", ""))[:10] == dato_idx else " (ELDRE DATO enn index.json)"
        L.append(f"- {navn}: " + ", ".join(f"{f} {n(d.get(f), 2) if isinstance(d.get(f), (int, float)) else d.get(f)}"
                                           for f in felt) + fersk)

    rg = _les_json(lager, "regime.json")
    if rg:
        v, sj, bo = rg.get("vekst") or {}, rg.get("sjokk") or {}, rg.get("boom") or {}
        L.append(f"- Regime ({rg.get('mnd', '-')}): vekst {v.get('ord', '-')} "
                 f"(bredde {n(v.get('bredde'), 2)}), uro {sj.get('ord', '-')} "
                 f"(nivaa {n(sj.get('nivaa'), 2)}, volvariasjon {n(sj.get('volvar'), 2)}, "
                 f"papirkorrelasjon {n(sj.get('korr_papirer'), 2)} utenfor ordet), "
                 f"boom {bo.get('ord', '-')} (median A {n(bo.get('median_A'), 1)})")
        if "nivaa_grenser" not in sj:
            L.append("  - regime.json har forrige feltstruktur (uro ble delt i to 11.11.2026); "
                     "feltene nivaa og volvar kommer fra f\u00f8rste onsdagskj\u00f8ring etter det")
        elif sj.get("volvar") is None:
            L.append("  - volvariasjonen mangler denne uken, s\u00e5 ordet er satt av niv\u00e5et alene")
    else:
        L.append("- Regime: filen mangler")

    mn = _les_json(lager, "miners.json")
    if mn:
        s = mn.get("scores") or {}
        p = mn.get("punkter") or {}
        L.append(f"- Gullgruver: {n(mn.get('last_nom'), 2)} fat per unse, A {n(s.get('A'))}, "
                 f"Ad {n(s.get('Ad'))}, Ar {n(s.get('Ar'))}, D {n(s.get('D'))}, "
                 f"S1 {'paa' if p.get('sig1') else 'av'}, S2 {'paa' if p.get('sig2') else 'av'}")
    else:
        L.append("- Gullgruver: filen mangler")

    h = _les_json(lager, "handel.json")
    if h:
        liste = h.get("liste") or []
        L.append(f"- Handlingslisten: {len(liste)} rader, \u00e5pne posisjoner {len(h.get('live') or [])}")
        for r in liste[:3]:
            sig = ", ".join(x.get("id", "") for x in (r.get("signaler") or [])) or "ingen"
            L.append(f"  - {r.get('navn', '-')}: avstand {n(r.get('avstand'), 1)}, signaler {sig}")
    else:
        L.append("- Handlingslisten: filen mangler")


def _del_helse(lager, L, idag):
    L.append("")
    L.append("## Datahelse")
    L.append("")
    h = _les_json(lager, "helse.json")
    if not h:
        L.append("- helse.json mangler")
        return
    rader = h.get("rader") or []
    teller = {"gronn": 0, "gul": 0, "rod": 0, "ukjent": 0}
    verst = []
    for r in rader:
        s = helsestatus(r, idag)
        teller[s] = teller.get(s, 0) + 1
        if s in ("gul", "rod", "ukjent"):
            verst.append(f"{r.get('navn') or r.get('id')} ({ORD.get(s, s)}, siste {r.get('siste', '-')})")
    L.append(f"- {len(rader)} rader: {teller.get('gronn', 0)} gr\u00f8nne, {teller.get('gul', 0)} gule, "
             f"{teller.get('rod', 0)} r\u00f8de, {teller.get('ukjent', 0)} ukjente")
    L.append("- Ikke gr\u00f8nne: " + (", ".join(verst) if verst else "ingen"))


def _del_endringer(lager, L):
    e = _les_json(lager, "endringer.json")
    L.append("")
    L.append("## Endringer siden forrige uke")
    L.append("")
    if not e:
        L.append("- endringer.json mangler")
        return
    u = e.get("uke") or {}
    L.append(f"- Fra {u.get('forrige_dato', '-')} til {u.get('ny_dato', '-')}")
    skifter = u.get("skifter") or []
    L.append(f"- Skifter: {len(skifter)}")
    for s in skifter:
        L.append(f"  - {s if isinstance(s, str) else json.dumps(s, ensure_ascii=False)}")
    topp = u.get("topp") or []
    if topp:
        L.append(f"- De {min(3, len(topp))} største endringene:")
    for r in topp[:3]:
        if isinstance(r, dict):
            L.append(f"  - {r.get('segment') or r.get('navn') or r.get('id') or '-'}, "
                     f"{r.get('felt') or 'ukjent felt'}: {n(r.get('gammel'), 2)} til "
                     f"{n(r.get('ny'), 2)} ({n(r.get('endring_pst'), 1)} %)")


def _del_kilder(idx, L):
    L.append("")
    L.append("## Kj\u00f8ring og kilder")
    L.append("")
    logg = idx.get("logg") or []
    feilet = [r for r in logg if str(r.get("status")).upper() == "FEIL"]
    L.append(f"- {len(logg)} kildelinjer i index.json, {len(feilet)} med status FEIL")
    for r in feilet:
        L.append(f"  - FEIL {r.get('kilde')}: {str(r.get('detalj'))[:160]}")
    for navn in ("flagglogg", "kurveform", "kapitulasjon D", "deflator, kontroll mot BLS"):
        traff = [r for r in logg if str(r.get("kilde", "")).startswith(navn)]
        if traff:
            r = traff[0]
            L.append(f"- {r.get('kilde')}: {r.get('status')} {str(r.get('detalj'))[:140]}")
        else:
            L.append(f"- {navn}: linjen mangler i index.json")


def _del_miljo(lager, L, uke):
    L.append("")
    L.append("## Milj\u00f8")
    L.append("")
    try:
        rader = so.fra_csv(lager.les("logg/miljo.csv")[0])
    except Exception:
        rader = []
    mine = [r for r in rader if r.get("uke") == uke]
    if not mine:
        L.append("- ingen rad for denne uken i logg/miljo.csv")
        return
    for r in mine:
        L.append(f"- {r.get('plattform')}: python {r.get('python')}, pandas {r.get('pandas')}, "
                 f"numpy {r.get('numpy')}, requests {r.get('requests')}, "
                 f"openpyxl {r.get('openpyxl')}, pdfplumber {r.get('pdfplumber')}, lxml {r.get('lxml')}")
        L.append("  - avvik mot config/miljo_kjent.json: " + (r.get("avvik") or "ingen"))


# ------------------------------------------------------------------ bygg
def bygg(lager, naa=None):
    naa_dt = naa or dt.datetime.now(OSLO)
    uke = so.periodenokkel(naa_dt.date())
    idx = _les_json(lager, "index.json") or {}
    L = [f"# Ukerapport {uke}", "",
         f"Skrevet av `ukerapport.py` {naa_dt.strftime('%d.%m.%Y %H:%M')} norsk tid, fra filene i",
         "repoet. Bare fakta: denne filen inneholder ingen vurdering. Rutinens egen rapport i",
         "prosjektet «Handelsalgoritme» har tolkningen, og den er fortsatt den som gjelder",
         "n\u00e5r de to sier noe ulikt.", "",
         f"- Prisinnhentingen (index.json): {norsk_tid(idx.get('oppdatert'))} norsk tid", ""]
    L.append("## Segmenter")
    L.append("")
    _del_segmenter(lager, idx, L)
    _del_marked(lager, idx, L)
    _del_endringer(lager, L)
    _del_helse(lager, L, naa_dt.date())
    _del_kilder(idx, L)
    _del_miljo(lager, L, uke)
    L.append("")
    return uke, "\n".join(L) + "\n"


def kjor(lager, note=print, naa=None):
    try:
        uke, tekst = bygg(lager, naa)
        sti = f"{MAPPE}/{uke}.md"
        if lager.les(sti)[0] is not None:
            note(f"   ukerapport {sti}: finnes alt, skriver ikke")
            return
        lager.opprett(sti, tekst)
        note(f"   ukerapport {sti}: skrevet ({len(tekst)} tegn)")
    except Exception as e:
        note(f"   ukerapport feilet: {type(e).__name__}: {str(e)[:100]}")


if __name__ == "__main__":
    import os
    import shadow_oos as _so
    rot = os.path.dirname(os.path.abspath(__file__))
    uke, tekst = bygg(_so.LokalLager(rot, rot))
    print(tekst)
