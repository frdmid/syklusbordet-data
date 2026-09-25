# ---------------------------------------------------------------------------
# Kontekstfeltene over hver graf: trendbekreftelse og COT.
#
# Ingen av dem inngaar i A, B, C eller D. De staar ved siden av for at en lav
# A skal kunne leses sammen med hvordan prisen beveger seg og hvem som sitter
# paa hvilken side i futuresmarkedet.
#
# Hvorfor de ligger her og ikke bare i databasen:
# Fram til 24. september 2026 ble begge feltene skrevet rett inn i dashbordets
# database av en egen oekt, utenfor repoet. Den planlagte oppgaven som kopierer
# repofilene inn i databasen skriver hele dokumentet paa nytt hver onsdag, saa
# feltene overlevde bare fordi den oppgaven tok vare paa dem. Da ble de ogsaa
# gamle: 24. september sto trendfeltet for brent, WTI, Henry Hub og fire
# skipssegmenter regnet paa en eldre versjon av serien enn den grafen viste.
# Formelen under er kontrollert mot de 19 segmentene der serien ikke hadde
# endret seg, og gir de samme tallene paa alle 19.
#
# Brukes av priser.py og bygg_shipping.py. Testes alene av sonde_kjor_cot.py.
# ---------------------------------------------------------------------------

import time
import requests


# ============================================================ trendbekreftelse

def trend(serie):
    """Timingsignal paa realprisen, maanedlig.

    Bekreftet krever begge ledd: hoyere enn for tolv maaneder siden OG over
    eget ti maaneders snitt. Ett av to er begynnende, ingen er nei. Samme grep
    som bunnflagget, der kravet om to uavhengige ledd var det som skilte
    signal fra stoy. Det er ikke testet paa denne serien.
    """
    r = [x for x in serie if x.get("real") is not None]
    if len(r) < 13:
        return None
    v = [float(x["real"]) for x in r]
    sist = v[-1]
    ma10 = sum(v[-10:]) / 10
    m12 = 100 * (sist / v[-13] - 1)
    m6 = 100 * (sist / v[-7] - 1)
    over = sist > ma10
    if m12 > 0 and over:
        sig = "bekreftet"
    elif m12 <= 0 and not over:
        sig = "nei"
    else:
        sig = "begynnende"
    return {"t": r[-1]["t"], "basis": "realpris, maanedlig",
            "mom12_pst": round(m12, 1), "mom6_pst": round(m6, 1),
            "ma10": round(ma10, 4), "avvik_ma10_pst": round(100 * (sist / ma10 - 1), 1),
            "over_ma10": bool(over), "signal": sig}


# ========================================================================= COT
#
# CFTC Disaggregated, futures only, via Socrata. Ingen noekkel.
# Samme seks kontrakter som feltet har vist siden det kom paa bordet.
# LME-metallene, jernmalm, palmeolje, kull og skipssegmentene har ingen
# tilsvarende rapport. Brent her er NYMEX sin Brent Last Day, ikke ICE-Brent,
# som CFTC ikke rapporterer. Den er mindre, men foelger samme pris.
DATASETT = "https://publicreporting.cftc.gov/resource/72hh-3qpy.json"
KONTRAKTER = {
    "brent":    "06765T",
    "wti":      "067651",
    "henryhub": "023651",
    "gold":     "088691",
    "kobber":   "085692",
    "kakao":    "073732",
}
UKER_3AAR = 156

# Persentilen er andelen av ukene i vinduet der nettoandelen var lik eller
# lavere enn i dag. 0 er det mest korte i vinduet, 100 det mest lange.
#
# Tre aar er hovedtallet fordi sammensetningen av aapen balanse har endret seg
# mye siden rapporten startet i 2006. Forvalterne er en stoerre del av
# markedet naa enn da, saa en persentil mot hele historikken ville i praksis
# vaere en persentil mot en annen markedsstruktur. Hele historikken staar ved
# siden av som kontroll.


def _felt(rad, *moenstre):
    """Finner et felt paa navnemoenster, fordi Socrata-navnene ikke er helt
    konsekvente (swap__positions_short_all har to understreker, og noen felt
    har _all paa slutten mens andre ikke har)."""
    for m in moenstre:
        for k in rad:
            if k == m:
                return rad[k]
    for m in moenstre:
        for k in rad:
            if k.startswith(m):
                return rad[k]
    return None


def _tall(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _persentil(verdier, x):
    v = [a for a in verdier if a is not None]
    if not v:
        return None
    return round(100.0 * sum(1 for a in v if a <= x) / len(v), 1)


def hent_kontrakt(kode, timeout=60):
    """Hele den ukentlige historikken for én kontraktkode, eldste foerst."""
    p = {"$where": f"cftc_contract_market_code='{kode}'",
         "$order": "report_date_as_yyyy_mm_dd ASC", "$limit": "5000"}
    for i in range(3):
        try:
            r = requests.get(DATASETT, params=p, timeout=timeout,
                             headers={"User-Agent": "Syklusbordet frode@h-k.no"})
            if r.status_code in (429, 502, 503):
                time.sleep(5 * (i + 1)); continue
            r.raise_for_status()
            return r.json()
        except requests.RequestException:
            if i == 2:
                raise
            time.sleep(3 * (i + 1))
    raise RuntimeError(f"{kode}: ga opp")


def cot_fra_rader(rader, kode):
    """Regner feltene dashbordet viser, fra raa Socrata-rader."""
    uker = []
    for r in rader:
        oi = _tall(_felt(r, "open_interest_all"))
        ml = _tall(_felt(r, "m_money_positions_long_all", "m_money_positions_long"))
        ms = _tall(_felt(r, "m_money_positions_short_all", "m_money_positions_short"))
        pl = _tall(_felt(r, "prod_merc_positions_long_all", "prod_merc_positions_long"))
        ps = _tall(_felt(r, "prod_merc_positions_short_all", "prod_merc_positions_short"))
        dato = str(_felt(r, "report_date_as_yyyy_mm_dd") or "")[:10]
        if not dato or not oi or None in (ml, ms, pl, ps):
            continue
        uker.append({"dato": dato, "oi": oi, "mm": ml - ms, "prod": pl - ps,
                     "mm_pct": 100 * (ml - ms) / oi, "prod_pct": 100 * (pl - ps) / oi,
                     "navn": _felt(r, "market_and_exchange_names")})
    # samme dato kan i prinsippet komme to ganger ved en rettelse; siste vinner
    uker = list({u["dato"]: u for u in sorted(uker, key=lambda u: u["dato"])}.values())
    if len(uker) < 5:
        raise ValueError(f"{kode}: bare {len(uker)} brukbare uker")
    s, f = uker[-1], uker[-5]
    tre = uker[-UKER_3AAR:]
    mm3 = [u["mm_pct"] for u in tre]
    pr3 = [u["prod_pct"] for u in tre]
    return {
        "kilde": "CFTC Disaggregated, futures only", "kode": kode,
        "kontrakt": s["navn"], "dato": s["dato"], "fra_dato": f["dato"],
        "oi": int(s["oi"]),
        "mm_net": int(s["mm"]), "mm_net_d4": int(s["mm"] - f["mm"]),
        "mm_pct": round(s["mm_pct"], 2), "mm_pct_d4": round(s["mm_pct"] - f["mm_pct"], 2),
        "prod_net": int(s["prod"]), "prod_net_d4": int(s["prod"] - f["prod"]),
        "prod_pct": round(s["prod_pct"], 2), "prod_pct_d4": round(s["prod_pct"] - f["prod_pct"], 2),
        # persentilene
        "mm_pctl_3aar": _persentil(mm3, s["mm_pct"]),
        "mm_pctl_alle": _persentil([u["mm_pct"] for u in uker], s["mm_pct"]),
        "mm_pct_min_3aar": round(min(mm3), 1), "mm_pct_maks_3aar": round(max(mm3), 1),
        "prod_pctl_3aar": _persentil(pr3, s["prod_pct"]),
        "prod_pctl_alle": _persentil([u["prod_pct"] for u in uker], s["prod_pct"]),
        "uker_3aar": len(tre), "uker_alle": len(uker), "fra_aar": uker[0]["dato"][:4],
    }


def cot_for_segmenter(note=print, pause=1.5):
    """Henter alle kontraktene SEKVENSIELT. CFTC sin anonyme grense slaar inn
    ved parallelle kall. Returnerer {segment-id: felt}."""
    ut = {}
    for sid, kode in KONTRAKTER.items():
        try:
            c = cot_fra_rader(hent_kontrakt(kode), kode)
            ut[sid] = c
            note(f"COT {sid}", True, f"{c['dato']}, forvaltere {c['mm_pct']:+.1f} % av OI, "
                 f"persentil {c['mm_pctl_3aar']} (3 aar) / {c['mm_pctl_alle']} "
                 f"(fra {c['fra_aar']}), {c['uker_alle']} uker")
        except Exception as e:
            note(f"COT {sid}", False, f"{type(e).__name__}: {str(e)[:70]}")
        time.sleep(pause)
    return ut


# ================================================================ kurveform
#
# Terminkurven 12 maaneder fram, slik Frode ba om 24.09.2026: selve kurven som
# graf, en fast betegnelse, og persentil av helningen mot egen historikk.
# Betegnelsen settes etter faste regler, slik at samme kurve alltid faar samme
# ord. Grensene (1 % flat, 10 % bratt, 5 % pukkel) er beskrivende og ikke
# testet som signal. Feltet inngaar ikke i noen skaar.

FLAT_PST, BRATT_PST, PUKKEL_PST = 1.0, 10.0, 5.0
SESONG = {"henryhub", "ttf"}


def _naermest(pkt, mnd):
    k = min(pkt, key=lambda q: abs(q["mnd"] - mnd))
    return k if abs(k["mnd"] - mnd) <= 1 else None


def kurveform(kontrakter, seg_id="", rente_pst=None):
    """kontrakter: liste av (maaned 'YYYY-MM', maaneder fram fra front, pris),
    sortert, der foerste er fronten. Returnerer feltene panelet viser."""
    if not kontrakter or len(kontrakter) < 3:
        return None
    p0 = float(kontrakter[0][2])
    pkt = [{"t": t, "mnd": int(m), "pst": round(100 * (float(p) / p0 - 1), 2)}
           for t, m, p in kontrakter if p and m <= 13]
    p12, p3 = _naermest(pkt, 12), _naermest(pkt, 3)
    if not p12:
        return None
    h12 = p12["pst"]
    h3 = p3["pst"] if p3 else None
    hb = None if h3 is None else round(100 * ((1 + h12 / 100) / (1 + h3 / 100) - 1), 2)

    if abs(h12) < FLAT_PST:
        form = "Flat"
    else:
        form = ("Contango" if h12 > 0 else "Backwardation")
        if abs(h12) >= BRATT_PST:
            form = "Bratt " + form.lower()
    besk = []
    pukkel = False
    if seg_id in SESONG and len(pkt) > 2:
        indre = max(q["pst"] for q in pkt[1:-1])
        pukkel = indre - max(0, h12) >= PUKKEL_PST
    if not pukkel and h3 is not None and abs(h3) >= FLAT_PST and abs(hb) >= FLAT_PST and (h3 > 0) != (hb > 0):
        form = "Backwardation foran, contango bak" if h3 < 0 else "Contango foran, backwardation bak"
        besk.append("Stramheten ser ut til å være kortvarig." if h3 < 0 else
                    "Markedet venter at det strammer seg til lenger ut.")
    if pukkel:
        besk.append("Vintertopp i kurven: formen foran sier mer om sesong enn om lager, "
                    "så bare helningen over tolv måneder er sammenlignbar.")
    if rente_pst is not None and h12 > 0:
        if h12 < rente_pst:
            besk.append(f"Contangoen er lavere enn renten ({rente_pst:.1f} %), så lagerholdet "
                        "betales ikke fullt. Markedet er strammere enn formen tilsier.")
        elif h12 > rente_pst + 5:
            besk.append(f"Contangoen er godt over renten ({rente_pst:.1f} %): markedet betaler "
                        "for å lagre, som er et tegn på overskudd.")
    return {"punkter": pkt, "helning12": h12, "helning3": h3, "form": form,
            "beskrivelse": besk, "rente_pst": rente_pst}


def kurvepersentil(historikk, siste):
    """historikk: liste av helning12 per maaned, eldste foerst, inkludert siste."""
    h = [x for x in historikk if x is not None]
    if len(h) < 36:
        return None, None
    tre = h[-36:]
    return (round(100 * sum(1 for x in tre if x <= siste) / len(tre), 1),
            round(100 * sum(1 for x in h if x <= siste) / len(h), 1))
