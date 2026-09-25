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
#                   oppsikt. Inngang i bunnsone gir en tenkt kjoepslinje per
#                   papir paa tavlen (ikke de omvendte), til siste kurs.
#                   Salgslinjer kommer naar salgsregelen er vedtatt.
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
         "cot_pctl_3aar", "bunnsone", "oppsikt"]
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
               "bunnsone": bool(sc.get("flagg")), "oppsikt": bool(sc.get("oppsikt"))}
        nye_uke.append(rad)
        tilstand[s["id"]] = rad

    # ------------------------------------------------ kurser for tavlens papirer
    papirer = {}
    for s in segmenter:
        for i in s.get("instrumenter") or []:
            papirer.setdefault(i["ticker"], {"segs": set(), "info": i})["segs"].add(s["id"])
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
        for felt, navn in (("bunnsone", "bunnsone"), ("oppsikt", "oppsikt")):
            naa = r[felt]
            foer = _b(f[felt]) if f else None
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
            if navn == "bunnsone" and hend != "bunnsone_slutt":
                seg = next(s for s in segmenter if s["id"] == sid)
                for i in seg.get("instrumenter") or []:
                    if i.get("omvendt"):
                        continue
                    k = kurs.get(i["ticker"], (None, None, None))
                    nye_hend.append({**base, "hendelse": "tenkt_kjoep", "ticker": i["ticker"],
                                     "kurs": k[0], "valuta": k[1], "kursdato": k[2],
                                     "merknad": ("inngang ved flagget (T0)" if not merk else merk)
                                                + ("" if k[0] is not None else "; kurs manglet")})

    skriv("logg/flagg_uke.csv", skriv_csv(gml_uke + nye_uke, F_UKE))
    skriv("logg/kurser_uke.csv", skriv_csv(gml_kurs + nye_kurs, F_KURS))
    skriv("logg/hendelser.csv", skriv_csv(gml_hend + nye_hend, F_HEND))
    note("flagglogg", True, f"uke {uke}: {len(nye_uke)} segmenter, {len(nye_kurs)} kurser"
         + (f" ({len(mangler)} uten kurs)" if mangler else "")
         + f", {sum(1 for h in nye_hend if h['ticker'] == '')} hendelser")
    return nye_uke, nye_kurs, nye_hend
