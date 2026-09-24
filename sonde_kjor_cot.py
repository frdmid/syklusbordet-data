# ---------------------------------------------------------------------------
# sonde_kjor_cot: svarer CFTC fra Actions, og gir feltene riktige tall
#
# COT-feltet paa dashbordet ble til 24. september skrevet rett inn i
# databasen av en egen oekt, utenfor repoet, og manglet persentil. Naa regnes
# det av signaler.py inne i den ukentlige kjoringen, med persentil mot tre aar
# og mot hele historikken. Foer det kan stoles paa maa tre ting vises:
#
#   1. at publicreporting.cftc.gov svarer fra en Actions-maskin. FRED gjor det
#      ikke, saa det kan ikke antas.
#   2. at feltnavnene er de signaler.py leter etter. Sonden skriver ut alle
#      feltene i en rad, og tallene for gull skal stemme med det som staar
#      paa dashbordet i dag for rapporten 2026-09-08: forvaltere netto
#      134 972 kontrakter, 32,82 % av aapen balanse 411 227.
#   3. om andre raavarer paa bordet har en CFTC-kontrakt vi ikke bruker:
#      uran, aluminium, nikkel, sink, bly, tinn, jernmalm, kull, palmeolje,
#      europeisk gass og frakt.
# ---------------------------------------------------------------------------

import json, time
import requests
from signaler import DATASETT, KONTRAKTER, hent_kontrakt, cot_fra_rader

UA = {"User-Agent": "Syklusbordet frode@h-k.no"}


def note(k, ok, d=""):
    print(("   ok    " if ok else "   FEIL  ") + k + ("   " + d if d else ""), flush=True)


# ===================================================================== 1 og 2
print("1. Svarer CFTC, og hvilke felt har en rad\n")
try:
    rader = hent_kontrakt(KONTRAKTER["gold"])
    note("gull", True, f"{len(rader)} uker, {rader[0].get('report_date_as_yyyy_mm_dd','?')[:10]} "
         f"til {rader[-1].get('report_date_as_yyyy_mm_dd','?')[:10]}")
    print("\n   feltene i en rad:")
    for k in sorted(rader[-1]):
        if any(x in k for x in ("open_interest_all", "m_money", "prod_merc", "report_date",
                                "market_and", "contract_market_code")):
            print(f"      {k:40} {rader[-1][k]}")
    print("\n   kontroll mot dashbordet, rapporten 2026-09-08:")
    r = next((x for x in rader if str(x.get("report_date_as_yyyy_mm_dd", ""))[:10] == "2026-09-08"), None)
    if r:
        c = cot_fra_rader([x for x in rader
                           if str(x.get("report_date_as_yyyy_mm_dd", ""))[:10] <= "2026-09-08"], "088691")
        print(f"      oi {c['oi']} (skal vaere 411227), mm_net {c['mm_net']} (134972), "
              f"mm_pct {c['mm_pct']} (32.82), prod_pct {c['prod_pct']} (-7.53)")
    else:
        print("      fant ikke rapporten 2026-09-08")
except Exception as e:
    note("gull", False, f"{type(e).__name__}: {str(e)[:120]}")

print("\n\n2. Alle seks, slik den ukentlige kjoringen vil regne dem\n")
for sid, kode in KONTRAKTER.items():
    try:
        c = cot_fra_rader(hent_kontrakt(kode), kode)
        note(sid, True, f"{c['dato']}  {c['kontrakt'][:38]:38} forvaltere {c['mm_pct']:+6.1f} % "
             f"pctl {c['mm_pctl_3aar']:5} (3 aar) {c['mm_pctl_alle']:5} (fra {c['fra_aar']})   "
             f"produsent {c['prod_pct']:+6.1f} % pctl {c['prod_pctl_3aar']:5}")
    except Exception as e:
        note(sid, False, f"{type(e).__name__}: {str(e)[:90]}")
    time.sleep(1.5)


# ========================================================================= 3
print("\n\n3. Finnes det kontrakter for resten av bordet\n")
SOK = ["URANIUM", "ALUMINUM", "ALUMINIUM", "NICKEL", "ZINC", "LEAD", "TIN ",
       "IRON ORE", "COAL", "PALM", "TTF", "DUTCH", "FREIGHT", "COCOA"]
for ord_ in SOK:
    try:
        p = {"$select": "cftc_contract_market_code,market_and_exchange_names,"
                        "max(report_date_as_yyyy_mm_dd) as siste,count(*) as uker",
             "$where": f"upper(market_and_exchange_names) like '%{ord_}%'",
             "$group": "cftc_contract_market_code,market_and_exchange_names",
             "$order": "siste DESC", "$limit": "8"}
        r = requests.get(DATASETT, params=p, headers=UA, timeout=60)
        if r.status_code != 200:
            print(f"   {ord_:10} HTTP {r.status_code} {r.text[:80]}")
            continue
        j = r.json()
        if not j:
            print(f"   {ord_:10} ingen")
        for x in j:
            print(f"   {ord_:10} {x.get('cftc_contract_market_code'):8} "
                  f"{str(x.get('market_and_exchange_names'))[:58]:58} "
                  f"siste {str(x.get('siste'))[:10]}  {x.get('uker')} uker")
    except Exception as e:
        print(f"   {ord_:10} {type(e).__name__}: {str(e)[:80]}")
    time.sleep(1.5)

print("\nEn kontrakt er brukbar hvis den fortsatt rapporteres (siste i september")
print("2026) og har flere hundre uker. Aapen balanse maa sjekkes foer den tas inn:")
print("en kontrakt med noen faa tusen kontrakter sier lite om posisjonering.")
print("\nSend hele utskriften tilbake.")
