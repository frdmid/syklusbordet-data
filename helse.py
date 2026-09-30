# ---------------------------------------------------------------------------
# helse: enkel helsesjekk av seriene paa dashbordet (Frodes bestilling
# 30.09.2026, etter en vurdering av Groks forslag)
#
# Skriver helse.json med en rad per serie: siste observasjon, forventet
# frekvens og forventet etterslep. Status regnes paa dashbordet mot dagens
# dato, saa den blir gul og roed ogsaa naar selve innhentingen stopper opp.
#
# AUTOMATISKE SERIER
#   slutt      siste dag i perioden til siste observasjon (maaned: siste dag
#              i maaneden, uke og dag: datoen selv, aar: 31.12)
#   forventet  slutten av neste periode pluss etterslep
#   status     groenn til forventet pluss 3 dager, gul til pluss 7, roed over
#   Etterslepet er tiden fra periodens slutt til tallet er paa dashbordet,
#   og tar med at innhentingen bare gaar om onsdagen. Satt 30.09.2026 ut fra
#   naar kildene publiserer:
#     Pink Sheet 14    tidlig i maaneden etter, hentes foerste onsdag etter
#     speilene 10      EIA/LBMA via datasets, hel maaned, foerste onsdag
#     Cameco 14, SSB laks (maaned) 14
#     FRED 24          BLS og Fed publiserer rundt den 15. i maaneden etter
#     KPI-speilet 45   speilet henger etter BLS; priser.py godtar to maaneder
#     COT 9            tirsdagstall, publisert fredag, hentet onsdag uka etter
#     Fearnleys 7, laks uke 7, uran futures 5 (soendagsdato)
#     daglige kurser 2 (VIX, DXY, USD/NOK, kurveform, jernmalm fersk): de
#                      hentes bare om onsdagen, saa frekvensen er en uke
#     kvartalsvis innhenting 5, OWID 300 (usikkert), laksekostnad 350
#                      (kjent i desember aaret etter)
#
# MANUELLE POSTER (c_manuell.json og b_manuell.json, eies av Cowork, leses
# bare): roed naar siste regnskapsaar sluttet for mer enn 15 maaneder siden,
# ellers groenn.
#
# FEIL: kilder med status FEIL i loggen i index.json staar som roede rader.
# ---------------------------------------------------------------------------

import calendar, csv, io, json, os, re
import datetime as dt

MND = {"januar": 1, "februar": 2, "mars": 3, "april": 4, "mai": 5, "juni": 6, "juli": 7,
       "august": 8, "september": 9, "oktober": 10, "november": 11, "desember": 12}
KILDE_ETTERSLEP = [(r"Pink Sheet", 14, "Verdensbanken Pink Sheet"), (r"datasets-speil", 10, "EIA/LBMA via datasets-speil"),
                   (r"Cameco", 14, "Cameco"), (r"SSB", 14, "SSB"), (r"FRED", 24, "BLS via FRED")]


def _mnd_slutt(t):
    a, m = int(t[:4]), int(t[5:7])
    return dt.date(a, m, calendar.monthrange(a, m)[1])


def _rad(id_, navn, kilde, frek, etterslep, siste, slutt, merknad=None):
    r = {"id": id_, "navn": navn, "kilde": kilde, "type": "auto", "frekvens": frek,
         "etterslep": etterslep, "siste": siste, "slutt": slutt.isoformat() if slutt else None}
    if merknad:
        r["merknad"] = merknad
    return r


def _aarsslutt(aar, mnd):
    return dt.date(aar, mnd, calendar.monthrange(aar, mnd)[1])


def _pluss_mnd(d, n):
    m = d.month - 1 + n
    a, m = d.year + m // 12, m % 12 + 1
    return dt.date(a, m, min(d.day, calendar.monthrange(a, m)[1]))


def bygg(les, les_tekst):
    """les(sti) -> json eller None, les_tekst(sti) -> str eller None."""
    rader = []
    idx = les("index.json") or {}
    if idx.get("oppdatert"):
        d = dt.date.fromisoformat(idx["oppdatert"][:10])
        rader.append(_rad("innhenting", "Ukentlig innhenting", "GitHub Actions", "uke", 2, idx["oppdatert"][:16], d))
    kpi = les_tekst("cpi_kopi.csv")
    if kpi:
        t = [l.split(",")[0] for l in kpi.strip().splitlines()[1:] if re.match(r"\d{4}-\d{2}", l)]
        if t:
            rader.append(_rad("kpi", "Deflator (amerikansk KPI)", "BLS via GitHub-speil cpi-us", "mnd", 45, t[-1], _mnd_slutt(t[-1])))

    cot, kurve = [], []
    for sid in idx.get("segmenter") or []:
        s = les(f"segments/{sid}.json")
        if not s:
            rader.append({"id": sid, "navn": sid, "type": "auto", "status": "rod", "merknad": "segmentfila mangler"})
            continue
        navn, kilde = s.get("name", sid), s.get("source", "")
        lag, kn = next(((l, n) for m, l, n in KILDE_ETTERSLEP if re.search(m, kilde)), (14, kilde[:40]))
        if s.get("last_obs"):
            rader.append(_rad(sid, navn, kn, "mnd", lag, s["last_obs"], _mnd_slutt(s["last_obs"])))
        c = s.get("cot") or {}
        if c.get("dato"):
            cot.append(_rad(f"{sid}_cot", f"{navn}, COT", "CFTC", "uke", 9, c["dato"], dt.date.fromisoformat(c["dato"])))
        k = s.get("kurve") or {}
        if k.get("dato"):
            kurve.append(_rad(f"{sid}_kurve", f"{navn}, kurveform", "Yahoo", "uke", 2, k["dato"], dt.date.fromisoformat(k["dato"])))
        r = s.get("rate") or {}
        if r.get("t") and sid == "oljeservice":
            rader.append(_rad(f"{sid}_akt", f"{navn}, aktivitet", "Fed via FRED", "mnd", 24, r["t"], _mnd_slutt(r["t"])))
        lk = s.get("laks") or {}
        if lk.get("uke"):
            rader.append(_rad("laks_uke", "Laks, ukepris", "SSB", "uke", 7, lk["uke"], dt.date.fromisoformat(lk["uke"])))
        if lk.get("kost_siste_aar"):
            a = int(lk["kost_siste_aar"])
            rader.append(_rad("laks_kost", "Laks, produksjonskostnad", "Fiskeridirektoratet", "aar", 350, str(a), dt.date(a, 12, 31)))
        f = s.get("fersk") or {}
        if f.get("dato"):
            rader.append(_rad(f"{sid}_fersk", f"{navn}, fersk pris", "Yahoo", "uke", 2, f["dato"], dt.date.fromisoformat(f["dato"])))
    rader += cot + kurve

    uf = les_tekst("uran_futures_uke.csv")
    if uf:
        t = [l.split(",")[0] for l in uf.strip().splitlines()[1:] if re.match(r"\d{4}-\d{2}-\d{2}", l)]
        if t:
            rader.append(_rad("uran_fut", "Uran, futures (kontroll)", "UxC via Cameco", "uke", 5, t[-1], dt.date.fromisoformat(t[-1])))

    sh = les("shipping.json") or {}
    dd = [r.get("dato") for r in sh.get("rader") or [] if r.get("dato")]
    if dd:
        rader.append(_rad("fearnleys", "Skip, Fearnleys ukerapport", "Fearnleys via Hellenic Shipping News", "uke", 7, max(dd), dt.date.fromisoformat(max(dd))))
    bdi = les("bdi.json") or {}
    if bdi.get("siste_obs"):
        rader.append(_rad("bdi", "Baltic Dry Index", "Baltic Exchange", "mnd", 7, bdi["siste_obs"], _mnd_slutt(bdi["siste_obs"]),
                          "Maaneden fylles fortloepende, saa stopp oppdages foerst etter neste maanedsslutt."))

    mk = les("marked.json") or {}
    if mk.get("t"):
        rader.append(_rad("vix", "VIX", "Cboe via Yahoo", "uke", 2, mk["t"], dt.date.fromisoformat(mk["t"])))
    dol = les("dollar.json") or {}
    for k, n, kl in (("dxy", "Dollar (DXY)", "ICE via Yahoo"), ("usdnok", "USD/NOK", "Norges Bank")):
        if (dol.get(k) or {}).get("t"):
            rader.append(_rad(k, n, kl, "uke", 2, dol[k]["t"], dt.date.fromisoformat(dol[k]["t"][:10])))

    et = les("etterspørsel.json") or {}
    aar = [max(v.get("aar") or [0]) for v in (et.get("baerere") or {}).values()]
    if aar and max(aar):
        a = min(aar)
        rader.append(_rad("owid", "Etterspørsel (OWID)", "Our World in Data", "aar", 300, str(a), dt.date(a, 12, 31),
                          "Publiseringstidspunktet er usikkert."))

    for sti, navn in (("c_overlevelse.json", "Overlevelsesport C (SEC)"), ("b_capex.json", "Tilbud B, metaller (SEC)"),
                      ("b_rigg.json", "Tilbud B, rigger (SEC)")):
        x = les(sti) or {}
        if x.get("oppdatert"):
            rader.append(_rad(sti.split(".")[0], navn, "Kvartalsvis innhenting", "kvartal", 5, x["oppdatert"][:10],
                              dt.date.fromisoformat(x["oppdatert"][:10])))

    # manuelle poster, bare lest
    c = les("c_manuell.json") or {}
    for tk, x in c.items():
        if tk.startswith("_") or not isinstance(x, dict):
            continue
        a = (x.get("siste") or {}).get("aar") or max((int(k) for k in (x.get("drift") or {})), default=None)
        if not a:
            continue
        m = re.search(r"31\.\s*(\w+)", x.get("kilde", ""))
        mnd = MND.get(m.group(1).lower(), 12) if m else 12
        slutt = _aarsslutt(int(a), mnd)
        rader.append({"id": f"c_{tk}", "navn": f"{tk}, overlevelse C", "kilde": "c_manuell.json", "type": "manuell",
                      "siste": f"regnskapsår {a}" + ("" if mnd == 12 else f" (til {m.group(1).lower()})"),
                      "slutt": slutt.isoformat(), "grense": _pluss_mnd(slutt, 15).isoformat()})
    b = les("b_manuell.json") or {}
    for met, sel in b.items():
        if met.startswith("_") or not isinstance(sel, dict):
            continue
        for tk, x in sel.items():
            if not isinstance(x, dict) or not x.get("aar"):
                continue
            a = max(int(k) for k in x["aar"])
            mnd = MND.get(str(x.get("regnskapsaar", "desember")).lower(), 12)
            slutt = _aarsslutt(a, mnd)
            rader.append({"id": f"b_{tk}", "navn": f"{x.get('navn', tk)}, tilbud B", "kilde": "b_manuell.json", "type": "manuell",
                          "siste": f"regnskapsår {a}" + ("" if mnd == 12 else f" (til {x.get('regnskapsaar')})"),
                          "slutt": slutt.isoformat(), "grense": _pluss_mnd(slutt, 15).isoformat()})

    for l in idx.get("logg") or []:
        if l.get("status") == "FEIL":
            rader.append({"id": "feil_" + re.sub(r"\W+", "_", l.get("kilde", "")), "navn": l.get("kilde", ""), "kilde": "index.json",
                          "type": "auto", "status": "rod", "siste": None, "merknad": "FEIL: " + (l.get("detalj") or "")})

    return {"id": "helse", "laget": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M"), "rader": rader}


def status(r, idag=None):
    """Samme regel som paa dashbordet, til kontroll og utskrift."""
    idag = idag or dt.date.today()
    if r.get("status"):
        return r["status"], None
    s = dt.date.fromisoformat(r["slutt"])
    if r["type"] == "manuell":
        return ("rod" if idag > dt.date.fromisoformat(r["grense"]) else "gronn"), (idag - s).days
    f = r["frekvens"]
    neste = (_mnd_slutt(_pluss_mnd(s.replace(day=1), 1).isoformat()[:7]) if f == "mnd" else
             s + dt.timedelta(days={"uke": 7, "kvartal": 92, "aar": 365}[f]))
    over = (idag - (neste + dt.timedelta(days=r["etterslep"]))).days
    return ("gronn" if over <= 3 else "gul" if over <= 7 else "rod"), (idag - s).days


def kjor(note=print):
    import endringer
    def tekst(sti):
        import base64, requests
        g = requests.get(f"https://api.github.com/repos/{endringer.REPO}/contents/{sti}", headers=endringer._h(),
                         params={"ref": endringer.BRANCH}, timeout=60)
        return base64.b64decode(g.json()["content"]).decode() if g.status_code == 200 else None
    h = bygg(endringer.les, tekst)
    endringer.skriv("helse.json", h)
    st = [status(r)[0] for r in h["rader"]]
    note(f"   helse: {len(st)} serier, {st.count('gul')} gule, {st.count('rod')} roede")


if __name__ == "__main__":
    def les(sti):
        try:
            return json.load(open(sti, encoding="utf-8"))
        except Exception:
            return None
    def tekst(sti):
        try:
            return open(sti, encoding="utf-8").read()
        except Exception:
            return None
    h = bygg(les, tekst)
    for r in h["rader"]:
        s, dager = status(r)
        print(f"   {s:5s} {r['type']:7s} {r['navn'][:40]:40s} {str(r.get('siste')):22s} {r.get('frekvens', ''):7s} "
              f"{str(r.get('etterslep', '')):>4s} {str(dager):>5s}")
    json.dump(h, open("helse.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
