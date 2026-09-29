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
#                   papir paa tavlen (ikke de omvendte), til siste kurs,
#                   men bare ved et nytt innslag (se PAUSE under).
#
#   hypotese_3mnd.csv  (fra 28.09.2026) regnes paa nytt hver uke fra de to
#                   over. Se HYPOTESE under.
#   regel_6040.csv  (fra 29.09.2026) Frodes praktiske salgsregel, regnet paa
#                   samme maate. Se REGEL 60/40 under.
#   dom.csv         (fra 29.09.2026) episodene og dommen for begge reglene,
#                   regnet i koden etter kriteriet som er skrevet ned her.
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

# B, B1, B2 og Ar lagt til 29.09.2026 (Frodes beslutning), slik at kombinasjoner
# som "flagg pluss B" eller "flagg pluss D" kan regnes framover paa loggede tall.
# D_pap og B2_rigg lagt til 29.09.2026 for test-flagget "hoey B og kapitulerte
# papirer": D for papirene alene (uten fondet) og hoeyeste B2 blant
# riggsegmentene for oljeservice.
F_UKE = ["uke", "dato", "segment", "siste_obs", "A", "Ad", "Ar", "B", "B1", "B2", "D", "D_pap", "B2_rigg", "port",
         "trend", "cot_pctl_3aar", "bunnsone", "oppsikt", "d95"]
# utbytte og usd_per_enhet lagt til 29.09.2026. utbytte er summen av utbytte
# per aksje med eksdato etter forrige loggede kursdato for papiret og til og
# med denne, i papirets valuta. usd_per_enhet er dollar per enhet av valutaen
# samme dag (GBp er pence). Uten dem kan totalavkastning i en valuta ikke regnes.
F_KURS = ["uke", "dato", "ticker", "segmenter", "kurs", "valuta", "kursdato", "utbytte", "usd_per_enhet"]
F_HEND = ["uke", "dato", "segment", "hendelse", "ticker", "kurs", "valuta", "kursdato",
          "A", "Ad", "D", "port", "trend", "merknad"]


def ukenokkel(d):
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def siste_kurs(tk):
    """Siste dagskurs fra Yahoo, med utbytte siste maaned.
    Returnerer dict med kurs, valuta, kursdato og utbytte [(dato, beloep)],
    eller kurs None.

    Utbyttet regnes i kursens egen valuta og enhet, ut fra hvor mye Yahoo selv
    har justert kursen (adjclose) paa eksdagen. Det rapporterte beloepet
    brukes ikke direkte: sonde_kjor_utbytte (29.09.2026) fant at det er i
    dollar for papirer notert i kroner eller danske kroner (Frontline,
    Hafnia, Himalaya, Okeanis, 2020 Bulkers, TORM) og i pund der kursen er i
    pence (Glencore, Atalaya, M.P. Evans, Taylor Maritime). Justeringen i
    adjclose var riktig for alle. Mangler adjclose rundt eksdagen, brukes det
    rapporterte beloepet bare hvis kurs og utbytte har samme valuta."""
    tom = {"kurs": None, "valuta": None, "kursdato": None, "utbytte": []}
    try:
        r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{tk}"
                         "?range=1mo&interval=1d&events=div%7Csplit&includeAdjustedClose=true",
                         headers=UA, timeout=25).json()["chart"]["result"][0]
        q = r["indicators"]["quote"][0]["close"]
        adj = ((r["indicators"].get("adjclose") or [{}])[0] or {}).get("adjclose") or [None] * len(q)
        rader = [(t, v, a) for t, v, a in zip(r["timestamp"], q, adj) if v is not None]
        if not rader:
            return tom
        t, v, _ = rader[-1]
        dag = lambda x: dt.datetime.utcfromtimestamp(int(x)).strftime("%Y-%m-%d")
        meta = r.get("meta") or {}
        div = []
        for d in ((r.get("events") or {}).get("dividends") or {}).values():
            eks = dag(d["date"])
            foer = [x for x in rader if dag(x[0]) < eks]
            paa = [x for x in rader if dag(x[0]) >= eks]
            beloep = None
            if foer and paa and foer[-1][2] and paa[0][2]:
                k0, k1 = foer[-1][2] / foer[-1][1], paa[0][2] / paa[0][1]
                if k1 > k0:
                    beloep = (1 - k0 / k1) * foer[-1][1]
            if beloep is None and meta.get("currency") not in ("GBp",) and not tk.endswith((".OL", ".CO")):
                beloep = float(d["amount"])
            if beloep is not None:
                div.append((eks, round(beloep, 6)))
        return {"kurs": round(float(v), 4), "valuta": meta.get("currency"),
                "kursdato": dag(t), "utbytte": sorted(div)}
    except Exception:
        return tom


def usd_per(valuta, kursfunk=None):
    """Dollar per enhet av valutaen, fra Yahoo. GBp er pence."""
    if not valuta:
        return None
    if valuta == "USD":
        return 1.0
    grunn, deler = ("GBP", 100.0) if valuta == "GBp" else (valuta, 1.0)
    k = (kursfunk or siste_kurs)(f"{grunn}USD=X")
    return None if k["kurs"] is None else round(k["kurs"] / deler, 8)


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
#   Maal:      papirets totalavkastning minus ACWI (verdensindeksen, logget som
#              referanse) i samme vindu, begge i dollar og med utbytte. Endret
#              29.09.2026, foer noe utfall fantes: foerste versjon brukte kurs
#              uten utbytte og papirets egen valuta. For kursrader logget foer
#              29.09 mangler utbytte og valutakurs, og da faller maalingen
#              tilbake til egen valuta uten utbytte. Kolonnen grunnlag sier hva
#              som ble brukt.
#   Med:       bare rene innslag (hendelse tenkt_kjoep). Ikke papirer som sto i
#              sonen da loggen startet, og ikke d95.
#   Bekreftet: naar minst fem episoder er ferdige (innslag med hoeyst seks
#              maaneder mellom er en episode), og episodens median mot ACWI er
#              positiv i minst fire av fem, eller i minst 80 % hvis det er
#              flere. Ellers forkastet. Grensen skal ikke flyttes etter at
#              utfallene kommer.
#              Presisert 29.09.2026, foer noe utfall fantes: dommen faelles
#              paa de fem FOERSTE ferdige episodene og regnes i koden (dom.csv).
#              "Eller 80 % hvis flere" gjelder ikke lenger; et fast maalepunkt
#              hindrer at man venter paa et bedre tall. Se FELLES under.
# ---------------------------------------------------------------------------
REFERANSE = "ACWI"
F_HYP = ["episode", "segment", "ticker", "flaggdato", "status", "inngang_dato", "inngang_kurs", "utgang_dato",
         "utgang_kurs", "valuta", "utbytte", "grunnlag", "avk_pst", "acwi_avk_pst", "mot_acwi_pst"]


def _dato(x):
    try:
        return dt.date.fromisoformat(str(x)[:10])
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# REGEL 60/40, Frodes praktiske salgsregel, skrevet ned 29.09.2026 foer noe
# utfall er kjent
#
#   Inngang:   som hypotesen, foerste loggede kurs minst 28 dager etter flagget.
#   Salg:      60 % selges ved foerste loggede kurs minst 91 dager etter
#              inngang. 40 % holdes og maales ved 365 og 730 dager.
#   Maal:      0,6 x (papir minus ACWI, inngang til 3 mnd) + 0,4 x (papir minus
#              ACWI, inngang til 12 eller 24 mnd), i dollar med utbytte.
#              Salgsbeloepet regnes som kontanter uten avkastning; det er
#              derfor maalt mot ACWI i samme vindu og ikke lagt sammen.
#   Dom:       paa 24 mnd, med samme kriterium som hypotesen (under). Tallet
#              paa 12 mnd vises underveis, men avgjoer ingenting.
#
# FELLES FOR BEGGE REGLENE (29.09.2026, etter den uavhengige gjennomgangen)
#
#   PAUSE:     et innslag er foerste bunnsonemaaned etter mer enn tolv
#              maaneder uten flagg, som i backtestene. Sjekkes mot segmentets
#              egen maanedsserie og mot flagg_uke.csv. Starter bunnsonen paa
#              nytt innen tolv maaneder, logges bunnsone_start, men ingen
#              tenkte kjoep.
#   PAPIRENE:  fryses ved innslaget. Papirer som tas av tavlen etterpaa,
#              logges videre i 26 maaneder, saa posisjonene kan lukkes.
#   EPISODE:   innslag i alle segmenter med hoeyst seks maaneder (183 dager)
#              mellom paafoelgende flaggdatoer. Et papir telles EN gang per
#              episode (foerste flagg), selv om det staar i flere segmenter.
#   FERDIG:    en episode er ferdig naar alle papirene har utgang for maalet,
#              og det har gaatt minst 183 dager siden siste innslag i den.
#   DOM:       fast maalepunkt: de FEM FOERSTE ferdige episodene, ikke flere.
#              Bekreftet hvis episodens median mot ACWI er positiv i minst
#              fire av fem. Forkastet saa snart to er negative. Merk: med
#              fem episoder og null effekt (myntkast) er sjansen for
#              "bekreftet" 6/32, rundt 19 %. Et bekreftet resultat er altsaa
#              svakt bevis, et forkastet sterkere.
# ---------------------------------------------------------------------------
PAUSE_MND = 12
KLYNGE_DAGER = 183
HOLD_DAGER = 26 * 31
DOM_EPISODER, DOM_KRAV = 5, 4
F_6040 = ["episode", "segment", "ticker", "flaggdato", "status", "inngang_dato", "grunnlag",
          "avk_3m_pst", "acwi_3m_pst", "avk_12m_pst", "acwi_12m_pst", "avk_24m_pst", "acwi_24m_pst",
          "mot_acwi_12m_pst", "mot_acwi_24m_pst"]
F_DOM = ["regel", "episode", "segmenter", "papirer", "ferdige", "status", "median_mot_acwi_pst", "dom"]


def _kursserie(kurser):
    serie = {}
    for r in kurser:
        d, k = _dato(r.get("kursdato")), r.get("kurs")
        try:
            k = float(k)
        except (TypeError, ValueError):
            continue
        fx = r.get("usd_per_enhet")
        try:
            fx = float(fx) if fx not in (None, "") else None
        except ValueError:
            fx = None
        try:
            utb = float(r.get("utbytte")) if r.get("utbytte") not in (None, "") else None
        except ValueError:
            utb = None
        if d:
            serie.setdefault(r["ticker"], {})[d] = (k, r.get("valuta"), fx, utb)
    return {tk: sorted(v.items()) for tk, v in serie.items()}


def _forste_etter(serie, tk, grense):
    for d, v in serie.get(tk, []):
        if d >= grense:
            return (d,) + v
    return None


def _avkastning(serie, tk, a, b):
    """Fra rad a til rad b. I dollar med utbytte hvis alle rader har
    valutakurs og utbyttefelt, ellers egen valuta uten utbytte."""
    rader = [x for x in serie.get(tk, []) if a[0] < x[0] <= b[0]]
    fullt = a[3] is not None and b[3] is not None and all(x[1][3] is not None for x in rader)
    if fullt:
        utb = sum(x[1][3] for x in rader)
        return 100 * ((b[1] + utb) * b[3] / (a[1] * a[3]) - 1), utb, "dollar med utbytte"
    return 100 * (b[1] / a[1] - 1), None, "egen valuta uten utbytte"


def _mot_acwi(serie, tk, inn, dager):
    """Papirets og ACWIs avkastning fra inngang til foerste kurs minst
    `dager` etter. None hvis utgangen ikke er naadd."""
    uts = _forste_etter(serie, tk, inn[0] + dt.timedelta(days=dager))
    if not uts:
        return None
    avk, utb, grunn = _avkastning(serie, tk, inn, uts)
    ai, au = _forste_etter(serie, REFERANSE, inn[0]), _forste_etter(serie, REFERANSE, uts[0])
    aa = _avkastning(serie, REFERANSE, ai, au)[0] if ai and au and au[0] > ai[0] else None
    return {"uts": uts, "avk": avk, "utb": utb, "grunnlag": grunn, "acwi": aa}


def innslag(hendelser):
    """Rene innslag (tenkt_kjoep, ikke loggstart), med episode, og hvert
    papir bare en gang per episode."""
    rader = [h for h in hendelser if h.get("hendelse") == "tenkt_kjoep" and h.get("ticker")
             and "sto allerede" not in str(h.get("merknad", "")) and _dato(h.get("dato"))]
    rader.sort(key=lambda h: (h["dato"], h["segment"], h["ticker"]))
    episode, forrige, ep = {}, None, None
    for d in sorted({_dato(h["dato"]) for h in rader}):
        if forrige is None or (d - forrige).days > KLYNGE_DAGER:
            ep = str(d)
        episode[d], forrige = ep, d
    ut, sett = [], set()
    for h in rader:
        e = episode[_dato(h["dato"])]
        if (e, h["ticker"]) in sett:
            continue
        sett.add((e, h["ticker"]))
        ut.append({**h, "episode": e})
    return ut


def _median(xs):
    xs = sorted(xs)
    n = len(xs)
    return None if not n else (xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2)


def dom(regel, rader, felt, idag):
    """Episodene og dommen for en regel. rader har episode, status og felt."""
    eps = {}
    for r in rader:
        eps.setdefault(r["episode"], []).append(r)
    ut, ferdige = [], []
    for e in sorted(eps):
        rr = eps[e]
        siste = max(_dato(r["flaggdato"]) for r in rr)
        verdier = [r[felt] for r in rr if r.get(felt) not in (None, "")]
        klar = len(verdier) == len(rr) and (idag - siste).days >= KLYNGE_DAGER
        med = _median(verdier) if klar else None
        rad = {"regel": regel, "episode": e, "segmenter": " ".join(sorted({r["segment"] for r in rr})),
               "papirer": len(rr), "ferdige": len(verdier), "status": "ferdig" if klar else "aapen",
               "median_mot_acwi_pst": "" if med is None else round(med, 2), "dom": ""}
        if klar:
            ferdige.append(med)
        ut.append(rad)
    telt = ferdige[:DOM_EPISODER]
    pos, neg = sum(1 for m in telt if m > 0), sum(1 for m in telt if m <= 0)
    if pos >= DOM_KRAV:
        d = "bekreftet"
    elif neg > DOM_EPISODER - DOM_KRAV:
        d = "forkastet"
    else:
        d = "venter"
    ut.append({"regel": regel, "episode": "DOM", "papirer": sum(r["papirer"] for r in ut),
               "ferdige": len(telt), "status": f"{pos} positive og {neg} negative av de {len(telt)} "
               f"foerste ferdige episodene (dom ved {DOM_EPISODER}, krav {DOM_KRAV})", "dom": d})
    return ut


def hypotese_3mnd(hendelser, kurser, idag):
    """Regner hypotesefila fra hele hendelses- og kursloggen. Bare loggede
    kurser brukes, saa ingenting kan hentes i ettertid."""
    serie = _kursserie(kurser)
    ut = []
    for h in innslag(hendelser):
        f0 = _dato(h.get("dato"))
        rad = {"episode": h["episode"], "segment": h["segment"], "ticker": h["ticker"], "flaggdato": str(f0)}
        inn = _forste_etter(serie, h["ticker"], f0 + dt.timedelta(days=28))
        if not inn:
            ut.append({**rad, "status": "venter_inngang"}); continue
        rad.update({"inngang_dato": str(inn[0]), "inngang_kurs": inn[1], "valuta": inn[2]})
        m = _mot_acwi(serie, h["ticker"], inn, 91)
        if not m:
            ut.append({**rad, "status": "aapen"}); continue
        rad.update({"utgang_dato": str(m["uts"][0]), "utgang_kurs": m["uts"][1], "grunnlag": m["grunnlag"],
                    "utbytte": "" if m["utb"] is None else round(m["utb"], 6), "avk_pst": round(m["avk"], 2)})
        if m["acwi"] is not None:
            rad["acwi_avk_pst"] = round(m["acwi"], 2)
            rad["mot_acwi_pst"] = round(rad["avk_pst"] - rad["acwi_avk_pst"], 2)
        ut.append({**rad, "status": "ferdig"})
    return ut


def regel_6040(hendelser, kurser, idag):
    serie = _kursserie(kurser)
    ut = []
    for h in innslag(hendelser):
        f0 = _dato(h.get("dato"))
        rad = {"episode": h["episode"], "segment": h["segment"], "ticker": h["ticker"], "flaggdato": str(f0)}
        inn = _forste_etter(serie, h["ticker"], f0 + dt.timedelta(days=28))
        if not inn:
            ut.append({**rad, "status": "venter_inngang"}); continue
        rad["inngang_dato"] = str(inn[0])
        ben = {n: _mot_acwi(serie, h["ticker"], inn, d) for n, d in (("3m", 91), ("12m", 365), ("24m", 730))}
        for n, m in ben.items():
            if m:
                rad[f"avk_{n}_pst"] = round(m["avk"], 2)
                rad[f"acwi_{n}_pst"] = "" if m["acwi"] is None else round(m["acwi"], 2)
                rad["grunnlag"] = m["grunnlag"]
        for n in ("12m", "24m"):
            if all(ben[k] and ben[k]["acwi"] is not None for k in ("3m", n)):
                rad[f"mot_acwi_{n}_pst"] = round(0.6 * (ben["3m"]["avk"] - ben["3m"]["acwi"])
                                                 + 0.4 * (ben[n]["avk"] - ben[n]["acwi"]), 2)
        rad["status"] = "ferdig" if rad.get("mot_acwi_24m_pst") not in (None, "") else "aapen"
        ut.append(rad)
    return ut


def ny_innslag(seg, gml_uke, idag):
    """PAUSE: er dette foerste bunnsonemaaned etter mer enn tolv uten flagg?
    Returnerer (True, "") eller (False, grunn)."""
    serie = seg.get("series") or []
    tidligere = [r["t"] for r in serie[:-1][-PAUSE_MND:] if r.get("flagg")]
    if tidligere:
        return False, f"flagg i {tidligere[-1]}, innen {PAUSE_MND} mnd"
    grense = str(idag - dt.timedelta(days=365))
    uker = [r["dato"] for r in gml_uke if r["segment"] == seg["id"] and _b(r.get("bunnsone"))
            and r.get("dato", "") >= grense]
    if uker:
        return False, f"bunnsone i loggen {max(uker)}, innen {PAUSE_MND} mnd"
    return True, ""


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
               "A": sc.get("A"), "Ad": sc.get("Ad"), "Ar": sc.get("Ar"), "B": sc.get("B"),
               "B1": sc.get("B1"), "B2": sc.get("B2"), "D": sc.get("D"),
               "D_pap": (s.get("d_detalj") or {}).get("D_aksjer"),
               "B2_rigg": max([v.get("B2_siste") for v in ((s.get("rigg_b") or {}).get("segmenter") or {}).values()
                               if v.get("B2_siste") is not None], default=None),
               "port": sc.get("gate"),
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
    # Papirene fryses ved innslaget: et papir med tenkt kjoep siste 26
    # maaneder logges videre selv om det er tatt av tavlen.
    grense = str(idag - dt.timedelta(days=HOLD_DAGER))
    for h in gml_hend:
        if str(h.get("hendelse", "")).startswith("tenkt_kjoep") and h.get("ticker") and h.get("dato", "") >= grense:
            papirer.setdefault(h["ticker"], {"segs": set(), "info": {}})["segs"].add(h["segment"])
    # Verdensindeksen logges ved siden av, som maalestokk for hypotesen.
    papirer.setdefault(REFERANSE, {"segs": set(), "info": {}})["segs"].add("referanse")
    kurs = {}
    for tk in sorted(papirer):
        kurs[tk] = kursfunk(tk)
        time.sleep(0.2)
    # Utbytte telles fra dagen etter forrige loggede kursdato for papiret, saa
    # ingenting telles to ganger og ingenting faller mellom to uker (Yahoo gir
    # en maaned tilbake). Foerste gang et papir logges, telles bare denne uken.
    sist_dato = {}
    for r in gml_kurs:
        if r.get("kursdato"):
            sist_dato[r["ticker"]] = max(sist_dato.get(r["ticker"], ""), r["kursdato"])
    fx = {}
    for v in sorted({k["valuta"] for k in kurs.values() if k["valuta"]}):
        fx[v] = usd_per(v, kursfunk)
    nye_kurs = []
    for tk, p in sorted(papirer.items()):
        k = kurs[tk]
        fra = sist_dato.get(tk) or (str(_dato(k["kursdato"]) - dt.timedelta(days=7)) if k["kursdato"] else "")
        utb = sum(b for d, b in k["utbytte"] if fra < d <= (k["kursdato"] or ""))
        nye_kurs.append({"uke": uke, "dato": dato, "ticker": tk, "segmenter": " ".join(sorted(p["segs"])),
                         "kurs": k["kurs"], "valuta": k["valuta"], "kursdato": k["kursdato"],
                         "utbytte": round(utb, 6) if k["kurs"] is not None else "",
                         "usd_per_enhet": fx.get(k["valuta"]) if k["kurs"] is not None else ""})
    mangler = [tk for tk in papirer if kurs[tk]["kurs"] is None]

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
            # Tomt felt forrige uke (d95 foer det ble logget for segmentet)
            # betyr ukjent, ikke nei. Ellers ville WTI faatt et falskt innslag.
            ukjent = f is not None and str(f.get(felt, "")) == ""
            if forste or f is None or ukjent:
                if naa:
                    hend, merk = f"{navn}_aktiv_ved_loggstart", "sto allerede i sonen da loggen startet, ikke et rent innslag"
                else:
                    continue
            elif naa and not foer:
                hend, merk = f"{navn}_start", ""
                seg = next(s for s in segmenter if s["id"] == sid)
                if navn == "bunnsone":
                    ok, grunn = ny_innslag(seg, gml_uke, idag)
                else:   # d95 har ingen maanedsserie; bare loggen
                    ok = not any(x["segment"] == sid and _b(x.get(felt)) and
                                 x.get("dato", "") >= str(idag - dt.timedelta(days=365)) for x in gml_uke)
                    grunn = "" if ok else f"d95 i loggen innen {PAUSE_MND} mnd"
                if not ok:
                    merk = f"ikke nytt innslag: {grunn}; ingen tenkte kjoep"
            elif foer and not naa:
                hend, merk = f"{navn}_slutt", ""
            else:
                continue
            base = {"uke": uke, "dato": dato, "segment": sid, "hendelse": hend, "A": r["A"],
                    "Ad": r["Ad"], "D": r["D"], "port": r["port"], "trend": r["trend"], "merknad": merk}
            nye_hend.append({**base, "ticker": "", "kurs": "", "valuta": "", "kursdato": ""})
            if navn in ("bunnsone", "detrendet_ekstrem") and not hend.endswith("_slutt") \
                    and not merk.startswith("ikke nytt innslag"):
                parallell = navn == "detrendet_ekstrem"
                seg = next(s for s in segmenter if s["id"] == sid)
                for i in seg.get("instrumenter") or []:
                    if i.get("omvendt"):
                        continue
                    k = kurs.get(i["ticker"]) or {"kurs": None, "valuta": None, "kursdato": None}
                    k = (k["kurs"], k["valuta"], k["kursdato"])
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
    r64 = regel_6040(gml_hend + nye_hend, gml_kurs + nye_kurs, idag)
    skriv("logg/regel_6040.csv", skriv_csv(r64, F_6040))
    dommer = dom("hypotese_3mnd", hyp, "mot_acwi_pst", idag) + dom("regel_6040", r64, "mot_acwi_24m_pst", idag)
    skriv("logg/dom.csv", skriv_csv(dommer, F_DOM))
    note("flagglogg", True, f"uke {uke}: {len(nye_uke)} segmenter, {len(nye_kurs)} kurser"
         + (f" ({len(mangler)} uten kurs)" if mangler else "")
         + f", {sum(1 for h in nye_hend if h['ticker'] == '')} hendelser"
         + f", hypotese 3 mnd: {sum(1 for h in hyp if h['status'] == 'ferdig')} ferdige av {len(hyp)}"
         + f", 60/40: {sum(1 for h in r64 if h['status'] == 'ferdig')} ferdige av {len(r64)}"
         + "; dom " + ", ".join(f"{d['regel']} {d['dom']}" for d in dommer if d["episode"] == "DOM"))
    return nye_uke, nye_kurs, nye_hend
