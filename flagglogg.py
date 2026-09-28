# ---------------------------------------------------------------------------
# flagglogg: logg over flagg og tenkte handler, framover i tid
#
# Hvorfor: alle resultatene bordet hviler paa er historiske, med rundt sju
# episoder og papirer hentet fra dagens kurslister. Den eneste testen uten
# den skjevheten er aa skrive ned hvert flagg og hver tenkte handel NAAR det
# skjer, foer utfallet er kjent. Loggen skrives av den ukentlige kjoeringen og
# ligger i repoet, saa git-historikken viser naar hver linje ble skrevet. Den
# kan ikke rettes i ettertid uten at det synes.
#
# Tre filer i logg/:
#   flagg_uke.csv   hver uke, hvert raavaresegment: A, detrendet A, D, port,
#                   trend, COT-persentil, bunnsone og oppsikt
#   kurser_uke.csv  hver uke, hvert papir paa tavlen: siste kurs og valuta.
#                   Gjoer det mulig aa regne ut enhver inngang og salgsregel
#                   senere paa data som ble logget foer utfallet var kjent
#   hendelser.csv   naar et segment gaar inn i eller ut av bunnsone eller
#                   oppsikt, eller (Brent, fra 25.09.2026) inn i eller ut av det
#                   parallelle signalet detrendet A >= 95 ("detrendet_ekstrem",
#                   med tenkte kjoep merket "tenkt_kjoep_d95"). Inngang i bunnsone gir en tenkt kjoepslinje per
#                   papir paa tavlen (ikke de omvendte), til siste kurs.
#                   Salgslinjer kommer naar salgsregelen er vedtatt.
#
#   hypotese_3mnd.csv  (fra 28.09.2026) regnes paa nytt hver uke fra de to
#                   over. Se HYPOTESE under.
#
# Uken er noekkelen. Kjoeres innhentingen to ganger samme uke, erstattes ukens
# linjer, saa loggen faar aldri dobbeltlinjer. Tidligere uker roeres aldri.
# Feiler noe her, stopper ikke resten av innhentingen.
# ---------------------------------------------------------------------------

import csv, io, time
import datetime as dt
import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}

F_UKE = ["uke", "dato", "segment", "siste_obs", "A", "Ad", "D", "port", "trend",
         "cot_pctl_3aar", "bunnsone", "oppsikt", "d95"]
F_KURS = ["uke", "dato", "ticker", "segmenter", "kurs", "valuta", "kursdato"]
F_HEND = ["uke", "dato", "segment", "hendelse", "ticker", "kurs", "valuta", "kursdato",
          "A", "Ad", "D", "port", "trend", "merknad"]


def ukenokkel(d):
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def siste_kurs(tk):
    """Siste dagskurs fra Yahoo: (kurs, valuta, dato) eller (None, None, None)."""
    try:
        r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{tk}"
                         "?range=10d&interval=1d", headers=UA, timeout=25).json()["chart"]["result"][0]
        q = r["indicators"]["quote"][0]["close"]
        ts = r["timestamp"]
        par = [(t, v) for t, v in zip(ts, q) if v is not None]
        if not par:
            return None, None, None
        t, v = par[-1]
        return round(float(v), 4), (r.get("meta") or {}).get("currency"), \
            dt.datetime.utcfromtimestamp(t).strftime("%Y-%m-%d")
    except Exception:
        return None, None, None


def les_csv(tekst):
    if not tekst:
        return []
    return list(csv.DictReader(io.StringIO(tekst)))


def skriv_csv(rader, felt):
    b = io.StringIO()
    w = csv.DictWriter(b, fieldnames=felt, extrasaction="ignore", lineterminator="\n")
    w.writeheader()
    for r in rader:
        w.writerow(r)
    return b.getvalue()


def _b(x):
    return str(x).lower() in ("true", "1", "ja")


# ---------------------------------------------------------------------------
# HYPOTESE, skrevet ned 28.09.2026 foer noe utfall er kjent
#
# Backtestene 28.09 (notater/2026-09-28_backtest.md) fant at bunnflagget ikke
# holdt paa 12 og 24 maaneder utenfor perioden det ble valgt paa, men at
# den foerste maaneden etter flagget var svak og at kjoep en maaned senere ga
# bedre tall etter tre maaneder. Det er en ide funnet i de samme dataene, ikke
# et resultat. Den kan bare testes framover, og det er det denne fila gjoer.
#
#   Regel:     kjoep en maaned etter at bunnsonen slaar inn, selg tre maaneder
#              etter kjoepet. Alle papirer paa tavlen for segmentet, likt vektet.
#   Inngang:   foerste loggede ukekurs med kursdato minst 28 dager etter
#              flaggdatoen.
#   Utgang:    foerste loggede ukekurs med kursdato minst 91 dager etter inngang.
#   Maal:      papirets avkastning minus ACWI (verdensindeksen, logget som
#              referanse) i samme vindu. Papiret i egen valuta, ACWI i dollar,
#              saa valutautslag inngaar. Kurser er siste omsetning, ikke
#              justert for utbytte.
#   Med:       bare rene innslag (hendelse tenkt_kjoep). Ikke papirer som sto i
#              sonen da loggen startet, og ikke d95.
#   Bekreftet: naar minst fem episoder er ferdige (innslag med hoeyst seks
#              maaneder mellom er en episode), og episodens median mot ACWI er
#              positiv i minst fire av fem, eller i minst 80 % hvis det er
#              flere. Ellers forkastet. Grensen skal ikke flyttes etter at
#              utfallene kommer.
# ---------------------------------------------------------------------------
REFERANSE = "ACWI"
F_HYP = ["segment", "ticker", "flaggdato", "status", "inngang_dato", "inngang_kurs", "utgang_dato",
         "utgang_kurs", "valuta", "avk_pst", "acwi_avk_pst", "mot_acwi_pst"]


def _dato(x):
    try:
        return dt.date.fromisoformat(str(x)[:10])
    except ValueError:
        return None


def hypotese_3mnd(hendelser, kurser, idag):
    """Regner hypotesefila fra hele hendelses- og kursloggen. Bare loggede
    kurser brukes, saa ingenting kan hentes i ettertid."""
    serie = {}
    for r in kurser:
        d, k = _dato(r.get("kursdato")), r.get("kurs")
        try:
            k = float(k)
        except (TypeError, ValueError):
            continue
        if d:
            serie.setdefault(r["ticker"], {})[d] = (k, r.get("valuta"))
    serie = {tk: sorted(v.items()) for tk, v in serie.items()}

    def forste_etter(tk, grense):
        for d, (k, v) in serie.get(tk, []):
            if d >= grense:
                return d, k, v
        return None

    ut = []
    for h in hendelser:
        if h.get("hendelse") != "tenkt_kjoep" or not h.get("ticker"):
            continue
        if "sto allerede" in str(h.get("merknad", "")):   # ikke et rent innslag
            continue
        f0 = _dato(h.get("dato"))
        rad = {"segment": h["segment"], "ticker": h["ticker"], "flaggdato": str(f0)}
        inn = forste_etter(h["ticker"], f0 + dt.timedelta(days=28)) if f0 else None
        if not inn:
            ut.append({**rad, "status": "venter_inngang"}); continue
        rad.update({"inngang_dato": str(inn[0]), "inngang_kurs": inn[1], "valuta": inn[2]})
        uts = forste_etter(h["ticker"], inn[0] + dt.timedelta(days=91))
        if not uts:
            ut.append({**rad, "status": "aapen"}); continue
        rad.update({"utgang_dato": str(uts[0]), "utgang_kurs": uts[1],
                    "avk_pst": round(100 * (uts[1] / inn[1] - 1), 2)})
        ai, au = forste_etter(REFERANSE, inn[0]), forste_etter(REFERANSE, uts[0])
        if ai and au:
            rad["acwi_avk_pst"] = round(100 * (au[1] / ai[1] - 1), 2)
            rad["mot_acwi_pst"] = round(rad["avk_pst"] - rad["acwi_avk_pst"], 2)
        ut.append({**rad, "status": "ferdig"})
    return ut


def oppdater(segmenter, les, skriv, note=print, idag=None, kursfunk=siste_kurs):
    """segmenter: listen fra priser.py (dict med id, scores, trend, cot,
    instrumenter, last_obs). les(sti) -> tekst eller None. skriv(sti, tekst)."""
    idag = idag or dt.datetime.utcnow().date()
    uke, dato = ukenokkel(idag), idag.isoformat()

    gml_uke = [r for r in les_csv(les("logg/flagg_uke.csv")) if r["uke"] != uke]
    gml_kurs = [r for r in les_csv(les("logg/kurser_uke.csv")) if r["uke"] != uke]
    gml_hend = [r for r in les_csv(les("logg/hendelser.csv")) if r["uke"] != uke]

    forrige = {}
    if gml_uke:
        siste_uke = max(r["uke"] for r in gml_uke)
        forrige = {r["segment"]: r for r in gml_uke if r["uke"] == siste_uke}

    # ------------------------------------------------ ukens tilstand per segment
    nye_uke, tilstand = [], {}
    for s in segmenter:
        if str(s.get("id", "")).startswith("ship_"):
            continue
        sc = s.get("scores") or {}
        rad = {"uke": uke, "dato": dato, "segment": s["id"], "siste_obs": s.get("last_obs"),
               "A": sc.get("A"), "Ad": sc.get("Ad"), "D": sc.get("D"), "port": sc.get("gate"),
               "trend": (s.get("trend") or {}).get("signal"),
               "cot_pctl_3aar": (s.get("cot") or {}).get("mm_pctl_3aar"),
               "bunnsone": bool(sc.get("flagg")), "oppsikt": bool(sc.get("oppsikt")),
               "d95": "" if "flagg_d95" not in sc else bool(sc.get("flagg_d95"))}
        nye_uke.append(rad)
        tilstand[s["id"]] = rad

    # ------------------------------------------------ kurser for tavlens papirer
    papirer = {}
    for s in segmenter:
        for i in s.get("instrumenter") or []:
            papirer.setdefault(i["ticker"], {"segs": set(), "info": i})["segs"].add(s["id"])
    # Verdensindeksen logges ved siden av, som maalestokk for hypotesen.
    papirer.setdefault(REFERANSE, {"segs": set(), "info": {}})["segs"].add("referanse")
    kurs = {}
    for tk in sorted(papirer):
        kurs[tk] = kursfunk(tk)
        time.sleep(0.2)
    nye_kurs = [{"uke": uke, "dato": dato, "ticker": tk, "segmenter": " ".join(sorted(p["segs"])),
                 "kurs": kurs[tk][0], "valuta": kurs[tk][1], "kursdato": kurs[tk][2]}
                for tk, p in sorted(papirer.items())]
    mangler = [tk for tk in papirer if kurs[tk][0] is None]

    # ------------------------------------------------ hendelser
    nye_hend = []
    forste = not forrige
    for sid, r in tilstand.items():
        f = forrige.get(sid)
        for felt, navn in (("bunnsone", "bunnsone"), ("oppsikt", "oppsikt"), ("d95", "detrendet_ekstrem")):
            if r[felt] == "":
                continue
            naa = bool(r[felt])
            foer = _b(f.get(felt, "")) if f else None
            if forste or f is None:
                if naa:
                    hend, merk = f"{navn}_aktiv_ved_loggstart", "sto allerede i sonen da loggen startet, ikke et rent innslag"
                else:
                    continue
            elif naa and not foer:
                hend, merk = f"{navn}_start", ""
            elif foer and not naa:
                hend, merk = f"{navn}_slutt", ""
            else:
                continue
            base = {"uke": uke, "dato": dato, "segment": sid, "hendelse": hend, "A": r["A"],
                    "Ad": r["Ad"], "D": r["D"], "port": r["port"], "trend": r["trend"], "merknad": merk}
            nye_hend.append({**base, "ticker": "", "kurs": "", "valuta": "", "kursdato": ""})
            if navn in ("bunnsone", "detrendet_ekstrem") and not hend.endswith("_slutt"):
                parallell = navn == "detrendet_ekstrem"
                seg = next(s for s in segmenter if s["id"] == sid)
                for i in seg.get("instrumenter") or []:
                    if i.get("omvendt"):
                        continue
                    k = kurs.get(i["ticker"], (None, None, None))
                    nye_hend.append({**base, "hendelse": "tenkt_kjoep_d95" if parallell else "tenkt_kjoep",
                                     "ticker": i["ticker"],
                                     "kurs": k[0], "valuta": k[1], "kursdato": k[2],
                                     "merknad": ("parallelt signal, detrendet A >= 95, ikke testet; " if parallell else "")
                                                + ("inngang ved flagget (T0)" if not merk else merk)
                                                + ("" if k[0] is not None else "; kurs manglet")})

    skriv("logg/flagg_uke.csv", skriv_csv(gml_uke + nye_uke, F_UKE))
    skriv("logg/kurser_uke.csv", skriv_csv(gml_kurs + nye_kurs, F_KURS))
    skriv("logg/hendelser.csv", skriv_csv(gml_hend + nye_hend, F_HEND))
    hyp = hypotese_3mnd(gml_hend + nye_hend, gml_kurs + nye_kurs, idag)
    skriv("logg/hypotese_3mnd.csv", skriv_csv(hyp, F_HYP))
    note("flagglogg", True, f"uke {uke}: {len(nye_uke)} segmenter, {len(nye_kurs)} kurser"
         + (f" ({len(mangler)} uten kurs)" if mangler else "")
         + f", {sum(1 for h in nye_hend if h['ticker'] == '')} hendelser"
         + f", hypotese 3 mnd: {sum(1 for h in hyp if h['status'] == 'ferdig')} ferdige av {len(hyp)}")
    return nye_uke, nye_kurs, nye_hend
