# ---------------------------------------------------------------------------
# shadow_utfall: fase 2 av Shadow-OOS, utfallene (Frodes bestilling
# 12.11.2026). Fyller shadow/shadow_outcomes.csv, som har staatt tom med bare
# overskrift siden 07.10.2026.
#
# Protokollen som bruker tallene staar i notater/champion_evaluering.md og er
# forhaandsregistrert. Denne modulen REGNER, den avgjoer ingenting.
#
# IKKE HASHET AV CHAMPIONEN, med vilje (protokollens avsnitt 9): da kan en feil
# her rettes uten aa gjoere Championen ugyldig. Modulen roerer ingen av de 16
# hashede filene og skriver bare til shadow/shadow_outcomes.csv, med
# so.legg_til_rader, altsaa bare tillegg.
#
# INGEN NETTKALL. Alt regnes av filer som alt ligger i repoet:
#   shadow/shadow_events.csv          innganger (hypothetical_entry)
#   shadow/snapshots/<modell>/<uke>.csv  frosset papirunivers og T0-kurser,
#                                     og referansene OSEBX og MSCI World
#   logg/kurser_uke.csv               ukekurser, valuta og utbytte framover
#   serier/priser_mnd.csv             raavarens egen realpris
#
# SLIK REGNES EN AVKASTNING
#   Papiret: totalavkastning i NOK. Utbyttet reinvesteres i papirets egen
#   valuta (andeler *= 1 + utbytte/kurs den uken det ble betalt), og kursen
#   regnes om til NOK i begge ender. Reinvestering er valgt fordi MSCI World
#   maales med IWDA.L, som er akkumulerende, og OSEBX er en
#   totalavkastningsindeks: uten reinvestering ville papirene maalt mot en
#   referanse som har utbyttet inne.
#   Valutaen: kurser_uke har usd_per_enhet, altsaa USD per enhet av papirets
#   valuta (GBp har sin egen, 0,0133, saa ingen deling paa 100 trengs).
#   NOK-kursen for uken hentes fra radene som staar i NOK.
#   Segmentet: likt vektet over de KJOEPBARE papirene i snapshotet paa
#   signaldatoen (instrument_eligible), ikke dagens papirer paa tavlen.
#   Referansen: IWDA.L og OSEBX.OL fra snapshotene for signaluken og
#   modningsuken, altsaa samme frosne kilde som alt annet.
#
# KLYNGEN REGNES IKKE HER. Filen har en rad per papir og en rad per segment,
# med macro_cluster_id i portfolio_id. Klyngens tall er snittet over
# segmentradene og regnes naar protokollen leses, ikke her, saa det samme
# tallet ikke ligger lagret to steder.
#
# FELT SOM STAAR TOMME (NULL, aldri 0): factor_adjusted_return,
# max_adverse_excursion og max_favorable_excursion (de trenger referansens
# ukesti, altsaa over hundre snapshotfiler per utfall, og det er for dyrt mot
# GitHub-API), share_dilution, capital_raise, restructuring og bankruptcy
# (de maa leses for haand). max_drawdown regnes av ukeserien og er med.
#
# ROBUSTHET
#   - et utfall skrives bare naar horisonten er modnet, aldri delvis,
#   - (event_id, horisont, papir) som alt staar, skrives ikke paa nytt,
#   - mangler en kurs eller en referanse, skrives raden med outcome_status
#     som sier hvorfor, og tallet staar tomt i stedet for aa bli gjettet,
#   - alt er pakket i try/except i kjor(): en feil her stopper ingenting.
#
# Kalles fra shadow_challenger.kjor etter kontekstmodulene.
# ---------------------------------------------------------------------------

import calendar
import csv
import datetime as dt
import io
from zoneinfo import ZoneInfo

import shadow_oos as so

OSLO = ZoneInfo("Europe/Oslo")
KURSER = "logg/kurser_uke.csv"
SERIER = "serier/priser_mnd.csv"
REFERANSER = ("IWDA.L", "OSEBX.OL")
HOVEDREFERANSE = "IWDA.L"          # protokollens primaerkomparator
INNGANGER = ("hypothetical_entry", "hypothetical_entry_d95")
SLINGRING_DAGER = 21               # hvor langt fram en kurs eller et snapshot kan hentes


# ------------------------------------------------------------------ smaating
def _t(x):
    try:
        return float(x) if x not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _d(x):
    try:
        return dt.date.fromisoformat(str(x)[:10])
    except Exception:
        return None


def _r(x, n=6):
    """Seks desimaler: avkastningene er brokdeler, saa det er en hundredels
    basispunkt. Filen er et permanent register med noen faa rader i aaret, saa
    presisjon koster ingenting, og meravkastningen regnes av uavrundede tall."""
    return None if x is None else round(float(x), n)


def pluss_mnd(d, mnd):
    """Samme dag i maaneden mnd senere, kappet til siste dag i maaneden."""
    aar, m = divmod(d.month - 1 + mnd, 12)
    aar, m = d.year + aar, m + 1
    return dt.date(aar, m, min(d.day, calendar.monthrange(aar, m)[1]))


# ------------------------------------------------------------------ kursene
class Kurser:
    """logg/kurser_uke.csv, slaatt opp per papir og dato."""

    def __init__(self, tekst):
        self.per_papir = {}
        self.nok_per_uke = {}
        for r in (csv.DictReader(io.StringIO(tekst)) if tekst else []):
            d = _d(r.get("kursdato") or r.get("dato"))
            kurs, upe = _t(r.get("kurs")), _t(r.get("usd_per_enhet"))
            if d is None or not kurs or kurs <= 0 or not upe:
                continue
            self.per_papir.setdefault(r["ticker"], []).append(
                {"dato": d, "uke": r.get("uke"), "kurs": kurs, "valuta": r.get("valuta"),
                 "upe": upe, "utbytte": _t(r.get("utbytte")) or 0.0})
            if r.get("valuta") == "NOK":
                self.nok_per_uke.setdefault(r.get("uke"), upe)
        for v in self.per_papir.values():
            v.sort(key=lambda x: x["dato"])

    def usd_per_nok(self, uke):
        """USD per krone den uken, eller den naermeste uken som har den."""
        if uke in self.nok_per_uke:
            return self.nok_per_uke[uke]
        return self.nok_per_uke[max(self.nok_per_uke)] if self.nok_per_uke else None

    def i_nok(self, rad):
        upn = self.usd_per_nok(rad["uke"])
        return None if not upn else rad["kurs"] * rad["upe"] / upn

    def naermeste(self, ticker, dato):
        """Raden paa eller naermest etter dato, innenfor slingringen."""
        rader = self.per_papir.get(ticker) or []
        etter = [r for r in rader if r["dato"] >= dato]
        if etter and (etter[0]["dato"] - dato).days <= SLINGRING_DAGER:
            return etter[0]
        foer = [r for r in rader if r["dato"] < dato]
        if foer and (dato - foer[-1]["dato"]).days <= SLINGRING_DAGER:
            return foer[-1]
        return None

    def siste(self, ticker):
        rader = self.per_papir.get(ticker) or []
        return rader[-1] if rader else None

    def avkastning(self, ticker, t0, t1):
        """Totalavkastning i NOK fra t0 til t1, utbytte reinvestert.

        Returnerer (avkastning, maks_fall, status). Status er 'ok',
        'mangler_kurs' eller 'avnotert'."""
        a, b = self.naermeste(ticker, t0), self.naermeste(ticker, t1)
        if a is None:
            return None, None, "mangler_kurs"
        if b is None:
            sist = self.siste(ticker)
            if sist is None or sist["dato"] >= t1:
                return None, None, "mangler_kurs"
            b = sist                                  # serien slutter foer modning
            status = "avnotert"
        else:
            status = "ok"
        p0, p1 = self.i_nok(a), self.i_nok(b)
        if not p0 or not p1:
            return None, None, "mangler_kurs"
        # utbytte reinvestert i papirets egen valuta
        andeler, topp, fall = 1.0, None, 0.0
        for r in self.per_papir.get(ticker, []):
            if not (a["dato"] < r["dato"] <= b["dato"]):
                continue
            if r["utbytte"] and r["kurs"]:
                andeler *= 1.0 + r["utbytte"] / r["kurs"]
            v = self.i_nok(r)
            if v:
                verdi = andeler * v / p0
                topp = verdi if topp is None else max(topp, verdi)
                if topp:
                    fall = min(fall, verdi / topp - 1.0)
        return andeler * p1 / p0 - 1.0, fall, status


# ------------------------------------------------------------------ snapshot
def _snapshot(lager, modell, uke):
    try:
        t = lager.les(f"shadow/snapshots/{modell}/{uke}.csv")[0]
        return so.fra_csv(t) if t else None
    except Exception:
        return None


def _uke_av(d):
    return so.periodenokkel(d)


def referanse(lager, modell, kurser, dato, ticker):
    """Referansekursen i NOK fra snapshotet for uken til dato.

    Leter framover inntil tre uker hvis en uke mangler, saa en hoppet
    kjoering ikke oedelegger utfallet."""
    for i in range(4):
        uke = _uke_av(dato + dt.timedelta(days=7 * i))
        rader = _snapshot(lager, modell, uke)
        if not rader:
            continue
        for r in rader:
            if r.get("level") == "benchmark" and r.get("instrument") == ticker:
                k, val = _t(r.get("instrument_price")), r.get("currency")
                if not k:
                    continue
                if val == "NOK":
                    return k, uke
                rad = kurser.naermeste("AKRBP.OL", dato)   # bare for NOK-kursen
                upn = kurser.usd_per_nok(rad["uke"] if rad else uke)
                # referansen er i USD, saa USD per krone gir NOK-kursen
                return (k / upn, uke) if upn else (None, uke)
    return None, None


# ------------------------------------------------------------------ raavaren
def raavare_avkastning(tekst, segment, t0, t1):
    """Endring i raavarens realpris fra maaneden til t0 til maaneden til t1."""
    if not tekst:
        return None
    m0, m1 = f"{t0:%Y-%m}", f"{t1:%Y-%m}"
    v = {}
    for r in csv.DictReader(io.StringIO(tekst)):
        if r.get("segment") == segment and r.get("t") in (m0, m1):
            x = _t(r.get("real"))
            if x:
                v[r["t"]] = x
    if m0 in v and m1 in v:
        return v[m1] / v[m0] - 1.0
    return None


# ------------------------------------------------------------------ hovedlogikk
def utfall(lager, naa=None, note=print):
    """Regner alle modne utfall som ikke staar i filen fra foer."""
    idag = (naa or dt.datetime.now(OSLO)).date()
    hend = so.fra_csv(lager.les(so.HENDELSER)[0])
    innganger = [h for h in hend if h.get("event") in INNGANGER]
    if not innganger:
        note("   utfall: ingen innganger ennaa, ingenting aa regne")
        return []
    gamle = so.fra_csv(lager.les(so.UTFALL)[0])
    finnes = {(g.get("event_id"), g.get("horizon"), g.get("instrument")) for g in gamle}
    kurser = Kurser(lager.les(KURSER)[0])
    try:
        serier = lager.les(SERIER)[0]
    except Exception:
        serier = None

    nye = []
    for h in innganger:
        sd = _d(h.get("event_date"))
        if sd is None:
            continue
        modell, seg = h.get("model_version"), h.get("segment")
        klynge = h.get("macro_cluster_id") or ""
        snap = _snapshot(lager, modell, h.get("iso_week") or _uke_av(sd))
        univers = [r for r in (snap or [])
                   if r.get("level") == "instrument" and r.get("segment") == seg
                   and so.sann(r.get("instrument_eligible"))]
        for hor in so.HORISONTER:
            md = pluss_mnd(sd, hor)
            if md > idag:
                continue
            if (h["event_id"], str(hor), "") in finnes:
                continue
            basis = {"event_id": h["event_id"], "model_version": modell, "segment": seg,
                     "portfolio_id": klynge, "signal_date": sd.isoformat(),
                     "horizon": hor, "maturity_date": md.isoformat(),
                     "calculated_at": (naa or dt.datetime.now(OSLO)).strftime("%Y-%m-%d %H:%M:%S")}
            raa = raavare_avkastning(serier, seg, sd, md)

            if not univers:
                nye.append({**basis, "instrument": "", "commodity_return": _r(raa),
                            "outcome_status": "ingen_kjopbare"})
                continue

            pr, status_alle = [], []
            for r in univers:
                tk = r.get("instrument")
                if (h["event_id"], str(hor), tk) in finnes:
                    continue
                a, fall, st = kurser.avkastning(tk, sd, md)
                status_alle.append(st)
                if a is not None:
                    pr.append(a)
                nye.append({**basis, "instrument": tk, "commodity_return": _r(raa),
                            "instrument_return": _r(a), "max_drawdown": _r(fall),
                            "delisting": "true" if st == "avnotert" else "",
                            "outcome_status": st})

            port = sum(pr) / len(pr) if pr else None
            ref, _ = referanse(lager, modell, kurser, md, HOVEDREFERANSE)
            ref0, _ = referanse(lager, modell, kurser, sd, HOVEDREFERANSE)
            bm = (ref / ref0 - 1.0) if (ref and ref0) else None
            st = ("ok" if pr and all(x == "ok" for x in status_alle)
                  else ("mangler_kurs" if not pr else "delvis"))
            if bm is None and st == "ok":
                st = "mangler_referanse"
            nye.append({**basis, "instrument": "", "commodity_return": _r(raa),
                        "portfolio_return": _r(port), "benchmark_return": _r(bm),
                        "excess_return": _r(port - bm) if (port is not None and bm is not None) else None,
                        "outcome_status": st})
    return nye


def kjor(lager, note=print, naa=None):
    try:
        nye = utfall(lager, naa, note)
        if not nye:
            return
        so.legg_til_rader(lager, so.UTFALL, so.F_OUTCOME, nye)
        seg = [r for r in nye if not r.get("instrument")]
        note(f"   utfall {so.UTFALL}: {len(nye)} rader lagt til "
             f"({len(seg)} segmentrader, {len(nye) - len(seg)} papirrader)")
        for r in seg:
            note(f"      {r['segment']} {r['signal_date']} {r['horizon']} mnd: "
                 f"portefolje {r.get('portfolio_return')} referanse {r.get('benchmark_return')} "
                 f"mer {r.get('excess_return')} [{r['outcome_status']}]")
    except Exception as e:
        note(f"   utfall feilet: {type(e).__name__}: {str(e)[:100]}")


if __name__ == "__main__":
    import os
    rot = os.path.dirname(os.path.abspath(__file__))
    nye = utfall(so.LokalLager(rot, rot))
    print(f"{len(nye)} modne utfall aa skrive")
    for r in nye:
        print("  ", {k: v for k, v in r.items() if v not in (None, "")})
