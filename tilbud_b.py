# ---------------------------------------------------------------------------
# Syklusbordet: tilbudsskåren B, v5
#
# To feil i v2 stengte ute nettopp de selskapene som betyr mest:
#   1. Jeg leste bare facts["us-gaap"]. Utenlandske filere bruker
#      facts["ifrs-full"]. Cameco, Teck, Rio Tinto, BHP og Vale ble aldri
#      undersøkt, og meldingen "ingen passende begreper" var min feil.
#   2. Jeg krevde form == "10-K". De samme selskapene filer 40-F og 20-F.
#
# v3 leser begge taksonomier og alle tre skjemaer, og gjetter ingen
# begrepsnavn: den skanner det selskapet faktisk har og velger serien med
# flest årstall.
#
# B deles også i to, etter samme logikk som A1 og A2:
#   B1  persentil på forholdstallet. Relativ: investeres det mindre enn før.
#   B2  absolutt nivå mot 1,0. Under 1,0 krymper kapitalapparatet uansett
#       hva historikken sier.
#
# Aluminium i v2 viste hvorfor begge trengs: femten av atten år under 1,0,
# altså kronisk underinvestering, men B ble 11 fordi årets 1,02 er høyt
# mot sin egen elendige historikk. Persentilen alene skjulte nivået.
# ---------------------------------------------------------------------------

import base64, json, os, re, time
import numpy as np
import pandas as pd
import requests

try:
    from google.colab import userdata
    GITHUB_TOKEN = userdata.get("GITHUB_TOKEN")
except Exception:
    import os
    GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")   # GitHub Actions setter denne

REPO, BRANCH = "frdmid/syklusbordet-data", "main"
SEC_UA = {"User-Agent": "Syklusbordet frode@h-k.no"}
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}

KURV = {
    "uran":      ["CCJ", "UEC", "UUUU"],
    "kobber":    ["FCX", "SCCO"],
    "aluminium": ["AA", "CENX", "KALU"],
    "kull":      ["BTU", "HCC", "ARLP"],
    "gull":      ["NEM", "HL", "CDE", "GOLD"],
}
# Tatt ut etter v4, med begrunnelse per selskap:
#   RIO   Filteret forkastet paret med median 13,8 og falt gjennom til
#         DepreciationPropertyPlantAndEquipment, altsaa komponenten igjen.
#         Median 1,45 er naer sannheten, men ved uhell.
#   VALE  Kollapset til 2007-2012 med median 3,39. Vales faktiske ratio
#         ligger rundt 1,5-2. Bade gammel og feil skalert.
#   BHP   Diversifisert: ett capex-tall dekker jernmalm, kobber og kull.
#         Kan ikke tilordnes ett metall.
#   TECK  Samme problem, og var eneste selskap i sink.
# Jernmalm, nikkel og sink har dermed ingen B. Ingen boersnotert SEC-filer
# gir et rent tall for dem, og et B basert paa ett diversifisert selskap
# er verre enn ingen B.

SKJEMA = {"10-K", "20-F", "40-F"}
MIN_AAR = 6

# Rangerte begreper, ikke "flest årstall vinner". Den regelen valgte
# DepreciationPropertyPlantAndEquipment for IFRS-filerne, som er EN komponent
# med lengre serie enn totalen. Rio Tinto fikk ratio 20,77 i stedet for ~2,1,
# altså ti ganger for høyt, fordi nevneren ble lest som en tidel.
CAPEX_RANG = [
    "PaymentsToAcquirePropertyPlantAndEquipment",
    "PaymentsToAcquireProductiveAssets",
    "PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities",
    "PurchaseOfPropertyPlantAndEquipment",
    "PurchaseOfIntangibleAssetsAndPropertyPlantAndEquipment",
    "AdditionsOtherThanThroughBusinessCombinationsPropertyPlantAndEquipment",
    "PropertyPlantAndEquipmentAdditions",
    "PaymentsToAcquireMiningAssets",
]
# Nedskrivninger skal ikke inn i nevneren (rettet 29.09.2026). Begrepet med
# "ImpairmentLoss" er avskrivninger PLUSS nedskrivninger, og nedskrivningene
# kommer nettopp i bunnaarene. Da blaases nevneren opp, forholdet faller og
# B ser ut som et tilbudskutt som ikke har skjedd. Det sto som nummer to og
# vant over de rene IFRS-begrepene. Naa er det nest siste utvei.
# B_DDA=gammel gir den gamle rekkefoelgen (for sonde_kjor_b_dda).
DDA_RANG = [
    "DepreciationDepletionAndAmortization",
    "DepreciationAndAmortisationExpense",
    "DepreciationAndAmortization",
    "DepreciationDepletionAndAmortizationExcludingAmortizationOfDeferredSalesCommissions",
    "DepreciationAmortisationAndImpairmentLossReversalOfImpairmentLossRecognisedInProfitOrLoss",
    "DepreciationPropertyPlantAndEquipment",   # komponent, siste utvei
]
if os.environ.get("B_DDA") == "gammel":
    DDA_RANG.insert(1, DDA_RANG.pop(4))
BEGREP = {}
# Plausibilitetsvindu. Et gruveselskap som investerer tjue ganger sine egne
# avskrivninger finnes ikke. Ligger medianen utenfor, er paret feil lest.
RATIO_MIN, RATIO_MAKS = 0.15, 6.0

def kandidater(facts, rang):
    """Alle serier selskapet har, i rangert rekkefølge."""
    ut = []
    for i, begrep in enumerate(rang):
        for takson in ("us-gaap", "ifrs-full"):
            d = facts.get(takson, {}).get(begrep)
            if not d:
                continue
            for enh, pkt in d.get("units", {}).items():
                if not (enh.startswith("USD") or enh in ("CAD", "AUD", "BRL", "GBP")):
                    continue
                aar = [p for p in pkt if p.get("form") in SKJEMA and p.get("fp") == "FY"]
                if len(aar) < MIN_AAR:
                    continue
                best = {}
                for p in aar:
                    k = p["end"][:4]
                    if k not in best or p.get("accn", "") > best[k].get("accn", ""):
                        best[k] = p
                sr = pd.Series({int(k): float(v["val"]) for k, v in best.items()}).sort_index()
                if len(sr) >= MIN_AAR:
                    ut.append((i, f"{takson}:{begrep}", enh, sr))
    return sorted(ut, key=lambda x: x[0])


def velg_par(facts):
    """Prøver kombinasjoner i rangert rekkefølge og tar første med
    plausibel median. Rang slår lengde, og plausibilitet slår begge."""
    cx = kandidater(facts, CAPEX_RANG)
    dd = kandidater(facts, DDA_RANG)
    forkastet = []
    for _, bc, ec, sc in cx:
        for _, bd, ed, sd in dd:
            fel = sc.index.intersection(sd.index)
            if len(fel) < MIN_AAR:
                continue
            r = (sc[fel] / sd[fel]).replace([np.inf, -np.inf], np.nan).dropna()
            if len(r) < MIN_AAR:
                continue
            med = float(r.median())
            if RATIO_MIN <= med <= RATIO_MAKS:
                return bc, bd, ec, sc[fel], sd[fel], r, forkastet
            forkastet.append((bc.split(":")[-1][:26], bd.split(":")[-1][:26], round(med, 1)))
    return None, None, None, None, None, None, forkastet


print("1. Tickerliste")
tick = requests.get("https://www.sec.gov/files/company_tickers.json",
                    headers=SEC_UA, timeout=60).json()
KART = {v["ticker"].upper(): str(v["cik_str"]).zfill(10) for v in tick.values()}
print(f"   {len(KART)} selskaper")

print("\n2. Capex og avskrivninger, begge taksonomier")
hentet, sett = {}, {}
for metall, tickere in KURV.items():
    for tk in tickere:
        if tk in sett:
            hentet.setdefault(metall, {})[tk] = sett[tk]
            continue
        cik = KART.get(tk)
        if not cik:
            print(f"   {tk:6s} ikke i tickerlisten")
            continue
        try:
            cf = requests.get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json",
                              headers=SEC_UA, timeout=120).json()
        except Exception as e:
            print(f"   {tk:6s} FEIL {type(e).__name__}")
            continue
        f = cf.get("facts", {})
        bc, bd, enh, capex, dda, r, forkastet = velg_par(f)
        if r is None:
            print(f"   {tk:6s} ingen plausibelt par. Forkastet: {forkastet[:3]}")
            continue
        if forkastet:
            print(f"   {tk:6s} forkastet {len(forkastet)} par med urimelig median: "
                  f"{forkastet[:2]}")
        fel = r.index
        sett[tk] = {"ratio": r, "capex": capex[fel], "dda": dda[fel]}
        BEGREP[tk] = {"metall": metall, "teller": bc, "nevner": bd,
                      "ratio": {int(a): round(float(v), 3) for a, v in r.items()}}
        hentet.setdefault(metall, {})[tk] = sett[tk]
        print(f"   {tk:6s} {len(r):>2} år {r.index.min()}-{r.index.max()}  "
              f"siste {r.iloc[-1]:5.2f}  median {r.median():5.2f}  {enh:3s}")
        print(f"          teller  {bc.split(':')[-1][:58]}")
        print(f"          nevner  {bd.split(':')[-1][:58]}")
        print(f"          serie   " + " ".join(f"{a}:{v:.2f}" for a, v in
              list(r.items())[-8:]))
        time.sleep(0.5)

# ---------------------------------------------------------------------------
# 2b. Manuelt leste aarsrapporter (b_manuell.json), fra 26.09.2026
#
# For metaller der ingen SEC-filer gir et rent tall. Foerst jernmalm (Frodes
# beslutning 26.09.2026): Fortescue, Kumba, Champion og Vales jernmalmsegment.
# Tallene er lest av for haand fra aarsrapportene (sonde_kjor_b_jernmalm.py
# skriver ut sidene), med kilde og side per tall i filen. Formatet:
#   {"jernmalm": {"FMG": {"valuta": "USD", "regnskapsaar": "juni",
#                          "aar": {"2015": {"capex": 1.0, "dda": 1.0,
#                                           "kilde": "AR 2015 s. 80"}}}}}
# Tallene er i millioner i selskapets valuta. De regnes om til dollar med
# aarssnittet av valutakursen for aaret regnskapsaaret slutter, slik at summen
# over kurven blir verdivektet som for SEC-selskapene. Forholdstallet for hvert
# selskap er uavhengig av valuta, saa omregningen paavirker bare vektingen.
# Regnskapsaaret merkes med aaret det slutter, samme regel som SEC-delen.
# ---------------------------------------------------------------------------
FX_AAR = {}


def fx_aarssnitt(valuta):
    """Dollar per enhet valuta, snitt per kalenderaar, fra Yahoo."""
    if valuta == "USD":
        return None
    if valuta not in FX_AAR:
        sym = {"ZAR": "ZAR=X", "CAD": "CAD=X", "AUD": "AUDUSD=X", "BRL": "BRL=X"}[valuta]
        r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}"
                         f"?period1=0&period2={int(time.time())}&interval=1mo", headers=UA, timeout=30).json()
        r = r["chart"]["result"][0]
        s = pd.Series(r["indicators"]["quote"][0]["close"],
                      index=pd.to_datetime(r["timestamp"], unit="s")).dropna()
        s = s.groupby(s.index.year).mean()
        FX_AAR[valuta] = s if sym.startswith("AUD") else 1.0 / s
    return FX_AAR[valuta]


print("\n2b. Manuelt leste aarsrapporter")
try:
    rm = requests.get(f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/b_manuell.json"
                      f"?cb={int(time.time())}", timeout=30)
    MAN = rm.json() if rm.status_code == 200 else {}
    if not MAN:
        print("   b_manuell.json finnes ikke ennaa")
    for metall, selskaper in MAN.items():
        if metall.startswith("_"):
            continue
        for tk, d in selskaper.items():
            aar = {int(k): v for k, v in d["aar"].items()
                   if v.get("capex") is not None and v.get("dda") not in (None, 0)}
            if len(aar) < MIN_AAR:
                print(f"   {metall}/{tk}: bare {len(aar)} aar, trenger {MIN_AAR}")
                continue
            fx = fx_aarssnitt(d["valuta"])
            capex = pd.Series({k: float(v["capex"]) for k, v in aar.items()}).sort_index()
            dda = pd.Series({k: float(v["dda"]) for k, v in aar.items()}).sort_index()
            if fx is not None:
                f_ = fx.reindex(capex.index)
                if f_.isna().any():
                    print(f"   {metall}/{tk}: mangler valutakurs for {list(f_[f_.isna()].index)}, de aarene utelates")
                capex, dda = (capex * f_).dropna(), (dda * f_).dropna()
            r = (capex / dda).replace([np.inf, -np.inf], np.nan).dropna()
            if not (RATIO_MIN <= float(r.median()) <= RATIO_MAKS):
                print(f"   {metall}/{tk}: median {r.median():.2f} utenfor {RATIO_MIN}-{RATIO_MAKS}, ikke brukt")
                continue
            hentet.setdefault(metall, {})[tk] = {"ratio": r, "capex": capex[r.index], "dda": dda[r.index]}
            print(f"   {metall}/{tk:8s} {len(r):>2} aar {r.index.min()}-{r.index.max()}  siste {r.iloc[-1]:5.2f}  "
                  f"median {r.median():5.2f}  {d['valuta']}  (manuelt lest)")
except Exception as e:
    print(f"   FEIL {type(e).__name__}: {str(e)[:80]}")

print("\n3. B1 relativt og B2 absolutt")
ut, KUTT = {}, {}
for metall, d in hentet.items():
    cx = pd.DataFrame({k: v["capex"] for k, v in d.items()})
    dd = pd.DataFrame({k: v["dda"] for k, v in d.items()})
    s = (cx.sum(axis=1) / dd.sum(axis=1)).replace([np.inf, -np.inf], np.nan).dropna()
    # Haleårsregelen i v4 var for hard. Den kuttet 2023, 2024 og 2025 fra
    # kull fordi HCC sluttet å rapportere i 2022, altså nettopp de årene du
    # trenger, for å berge en symmetri. Nå kuttes et år bare hvis under
    # halvparten av kurven er igjen. Endringer ellers logges, ikke slettes.
    ant = cx.notna().sum(axis=1).reindex(s.index)
    maks = int(cx.notna().sum(axis=1).max())
    tynne = [int(a) for a in s.index if ant[a] * 2 < maks]
    if tynne:
        print(f"      kuttet {len(tynne)} år med under halve kurven: {tynne}")
        s = s[~s.index.isin(tynne)]
        ant = ant[~ant.index.isin(tynne)]
    # Haleregelen, Frodes beslutning 29.09.2026, i tillegg til halvregelen og
    # bare for slutten av serien: det siste aaret telles foerst naar minst tre
    # fjerdedeler av kurvens aktive selskaper (rundet opp) har tall for det. Aar kuttes
    # bakfra til det siste oppfyller kravet. Aar midt i serien foelger fortsatt
    # halvregelen. Bakgrunn: selskaper med avvikende regnskapsaar (FMG og CIA i
    # jernmalm, som slutter i juni og mars) gir et nytt aar lenge foer resten,
    # og da ble siste forhold et snitt av to selskaper i stedet for fire.
    # HALEREGEL=0 i miljoeet slaar den av, bare for sammenligning.
    # Kravet regnes av de AKTIVE selskapene i kurven: de som har tall i minst
    # ett av de tre siste aarene i serien (Frodes valg 29.09.2026). Ellers ville
    # et selskap som har sluttet aa rapportere (HCC i kull fra 2022) kutte
    # 2023 til 2025, samme feil som v4-regelen. HALEKRAV=alle gir kravet av
    # alle selskaper i kurven, bare for sammenligning.
    siste3 = [a for a in cx.index if a > s.index[-1] - 3] if len(s) else []
    aktive = [c for c in cx.columns if cx.loc[siste3, c].notna().any()] if siste3 else list(cx.columns)
    grunnlag = aktive if os.environ.get("HALEKRAV", "aktive") != "alle" else list(cx.columns)
    krav = -(-3 * len(grunnlag) // 4)
    hale = []
    if os.environ.get("HALEREGEL", "1") != "0":
        while len(s) and ant[s.index[-1]] < krav:
            hale.append(int(s.index[-1]))
            s, ant = s.iloc[:-1], ant.iloc[:-1]
    if hale:
        print(f"      kuttet {len(hale)} år i halen med under {krav} av {len(grunnlag)} selskaper: {sorted(hale)}")
    KUTT[metall] = {"halvregel": tynne, "haleregel": sorted(hale), "krav_hale": krav, "grunnlag_hale": sorted(grunnlag),
                    "selskaper_per_aar": {str(int(a)): int(n) for a, n in cx.notna().sum(axis=1).items()}}
    if len(s) < MIN_AAR:
        continue
    kurv = {int(a): sorted(cx.columns[cx.loc[a].notna()]) for a in cx.index if a in s.index}
    aa = sorted(kurv)
    bytte = [a for i, a in enumerate(aa) if i and kurv[a] != kurv[aa[i-1]]]

    v = s.values
    pct = np.array([np.nan if i + 1 < MIN_AAR else (v[:i+1] <= v[i]).sum()/(i+1)
                    for i in range(len(v))])
    B1 = (1 - pct) * 100
    # B2: hvor langt under 1,0 har snittet av siste fem ar ligget.
    # 0,60 gir 100, 1,00 gir 50, 1,40 og over gir 0.
    sn5 = s.rolling(5, min_periods=3).mean()
    B2 = np.clip((1.4 - sn5.values) / 0.8 * 100, 0, 100)
    ut[metall] = {"metall": metall, "aar": [int(a) for a in s.index],
        "ratio": [round(float(x), 3) for x in s.values],
        "B1": [None if np.isnan(b) else round(float(b), 1) for b in B1],
        "B2": [None if np.isnan(b) else round(float(b), 1) for b in B2],
        "B1_siste": None if np.isnan(B1[-1]) else round(float(B1[-1]), 1),
        "B2_siste": None if np.isnan(B2[-1]) else round(float(B2[-1]), 1),
        "ratio_siste": round(float(s.iloc[-1]), 3),
        "snitt_5aar": None if np.isnan(sn5.iloc[-1]) else round(float(sn5.iloc[-1]), 3),
        "aar_under_1": int((s < 1.0).sum()), "aar_totalt": len(s),
        "selskaper": sorted(cx.columns), "kurv_per_aar": {str(k): v for k, v in kurv.items()},
        "aar_med_kurvbytte": bytte,
        "merknad": ("Capex delt paa avskrivninger, verdivektet over "
            f"{len(cx.columns)} selskaper ({', '.join(sorted(cx.columns))}). "
            "B1 er persentil, altsaa investeres det mindre enn for. B2 er "
            "nivaa mot 1,0 over fem aar, altsaa krymper kapitalapparatet i "
            "absolutt forstand. Arlig frekvens og faa observasjoner. Bare "
            "borsnoterte selskaper (SEC, og for jernmalm manuelt leste "
            "aarsrapporter), saa kinesisk og statlig kapasitet mangler.")}
    print(f"\n   {metall:10s} {len(cx.columns)} selskaper, {len(s)} år"
          + (f"   kurvbytte {bytte}" if bytte else ""))
    print(f"      ratio {s.iloc[-1]:.2f}  5-års snitt {ut[metall]['snitt_5aar']}  "
          f"B1={ut[metall]['B1_siste']}  B2={ut[metall]['B2_siste']}  "
          f"{ut[metall]['aar_under_1']}/{len(s)} år under 1,0")
    print("      " + "  ".join(f"{a}:{r:.2f}" for a, r in list(s.items())[-8:]))


print("\n\n4. Sprott, til kapitulasjonsskåren D")
# SPUT-premien mot NAV er dokumentets D-input for uran, ikke B. Kurs finnes
# hos Yahoo, NAV maa komme fra Sprott. Dette er en sondering, ikke en bygging.
for navn, u in [
    ("Yahoo SRUUF", "https://query1.finance.yahoo.com/v8/finance/chart/SRUUF?range=5y&interval=1wk"),
    ("Yahoo U-UN.TO", "https://query1.finance.yahoo.com/v8/finance/chart/U-UN.TO?range=5y&interval=1wk"),
    ("Sprott uranfond", "https://sprott.com/investment-strategies/physical-commodity-funds/uranium/"),
    ("Sprott NAV-API", "https://sprott.com/api/fund/nav/SRUUF"),
    ("Sprott investering", "https://sprott.com/investment-strategies/"),
]:
    try:
        r = requests.get(u, headers=UA, timeout=40)
        print(f"   {r.status_code}  {len(r.content):>9,} b  {navn}")
        if r.status_code == 200 and "sprott.com" in u:
            t = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", r.text))
            for m in re.finditer(r"(NAV|net asset value|premium|discount)[^.]{0,90}", t, re.I):
                print(f"        {m.group(0)[:110]}")
                break
        if r.status_code == 200 and "yahoo" in u:
            j = r.json()["chart"]["result"][0]
            print(f"        {len(j['timestamp'])} ukepunkter, siste "
                  f"{j['indicators']['quote'][0]['close'][-1]}")
    except Exception as e:
        print(f"   {type(e).__name__:>18s}  {navn}   {str(e)[:40]}")
    time.sleep(0.6)


if os.environ.get("B_UT"):
    with open(os.environ["B_UT"], "w", encoding="utf-8") as f:
        json.dump({"metaller": ut, "kutt": KUTT, "begreper": BEGREP}, f, ensure_ascii=False)

if GITHUB_TOKEN and ut:
    api = f"https://api.github.com/repos/{REPO}/contents/b_capex.json"
    h = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}
    sha = None
    g = requests.get(api, headers=h, params={"ref": BRANCH}, timeout=30)
    if g.status_code == 200:
        sha = g.json().get("sha")
    body = {"message": "b_capex v3", "branch": BRANCH,
            "content": base64.b64encode(json.dumps(
                {"oppdatert": str(pd.Timestamp.utcnow())[:19], "metaller": ut},
                ensure_ascii=False).encode()).decode()}
    if sha:
        body["sha"] = sha
    requests.put(api, headers=h, json=body, timeout=60).raise_for_status()
    print(f"\n   publisert {len(ut)} metaller")

print("\n" + "=" * 72)
print("Hoy B1 og hoy B2 samtidig er den ekte tilstanden: det investeres lite,")
print("og det har det gjort lenge nok til at kapasitet faktisk forsvinner.")


# B for rigger (29.09.2026): land, grunt og dypt vann, se rigg_b.py. Kjoeres
# her fordi arbeidsflyten for kvartalet allerede kjoerer denne fila. Hoppes
# over naar tilbud_b.py kjoeres av en sonde (B_UT satt). Feiler den, paavirkes
# ikke B for metallene.
if not os.environ.get("B_UT"):
    try:
        import rigg_b
        rigg_b.kjor()
    except Exception as e:
        print(f"\nRigg B feilet: {type(e).__name__}: {str(e)[:100]}")
