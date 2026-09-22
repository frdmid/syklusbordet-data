# ---------------------------------------------------------------------------
# Syklusbordet: sonde for C og D
#
# Dokumentet definerer dem slik:
#   C. Overlevelsesport. "Taaler selskapet ventetiden." Kontant-breakeven mot
#      dagens rate, likviditet i maaneder, netto gjeld mot verdijustert
#      egenkapital. Kvartalsvis. Under aatte kvartaler er aksjen en opsjon.
#      C gjelder SELSKAPET, ikke raavaren. Den porter instrumentet.
#   D. Kapitulasjon. "Har alle gitt opp." Fall fra 5-aarstopp, uker under
#      200-dagers, revisjonsbredde, sektorvekt i indeks, ETF-kapital. Ukentlig.
#      D gjelder SEGMENTET, maalt over aksjene i det.
#
# Av Ds fem ledd er to gratis og rett fram (fall fra topp, uker under 200d),
# ett mulig (ETF-kapital), og to bak betalingsmur (revisjonsbredde krever
# I/B/E/S, sektorvekt finnes ikke for shipping eller uran). Denne sonden
# maaler hva som faktisk svarer i stedet for aa anta.
#
# Skriver ingenting. Hvert kall er feilsikret for seg.
# ---------------------------------------------------------------------------

import io, json, re, time, warnings
import numpy as np, pandas as pd, requests
warnings.filterwarnings("ignore")

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
SEC_UA = {"User-Agent": "Syklusbordet frode@h-k.no"}
T = 25

# Aksjene i modellen, hentet rett fra instrumentlisten. De 13 ETC-ene er
# holdt utenfor med vilje: en ETC foelger raavaren, saa kursfallet er
# allerede A og ikke kapitulasjon.
AKSJER = {
 "2020.OL": {"bors": "Oslo", "navn": "2020 Bulkers", "segmenter": ["ship_capesize"]},
 "AA": {"bors": "NYSE", "navn": "Alcoa", "segmenter": ["aluminium"]},
 "ADM": {"bors": "NYSE", "navn": "Archer-Daniels-Midland", "segmenter": ["palmeolje", "kokosolje"]},
 "AEM": {"bors": "NYSE", "navn": "Agnico Eagle Mines", "segmenter": ["gold"]},
 "AFM.V": {"bors": "TSX Venture", "navn": "Alphamin Resources", "segmenter": ["tinn"]},
 "AKRBP.OL": {"bors": "Oslo", "navn": "Aker BP", "segmenter": ["brent"]},
 "ANTO.L": {"bors": "London", "navn": "Antofagasta", "segmenter": ["kobber"]},
 "AR": {"bors": "NYSE", "navn": "Antero Resources", "segmenter": ["henryhub"]},
 "AUSS.OL": {"bors": "Oslo", "navn": "Austevoll Seafood", "segmenter": ["fiskemel"]},
 "BARN.SW": {"bors": "Zürich", "navn": "Barry Callebaut", "segmenter": ["kakao"]},
 "BG": {"bors": "NYSE", "navn": "Bunge Global", "segmenter": ["kokosolje"]},
 "BOL.ST": {"bors": "Stockholm", "navn": "Boliden", "segmenter": ["sink", "bly"]},
 "BTU": {"bors": "NYSE", "navn": "Peabody Energy", "segmenter": ["kull"]},
 "CF": {"bors": "NYSE", "navn": "CF Industries", "segmenter": ["urea"]},
 "CNA.L": {"bors": "London", "navn": "Centrica", "segmenter": ["ttf"]},
 "DHT": {"bors": "NYSE", "navn": "DHT Holdings", "segmenter": ["ship_vlcc"]},
 "DVN": {"bors": "NYSE", "navn": "Devon Energy", "segmenter": ["wti"]},
 "EQNR.OL": {"bors": "Oslo", "navn": "Equinor", "segmenter": ["ttf"]},
 "EQT": {"bors": "NYSE", "navn": "EQT Corporation", "segmenter": ["henryhub"]},
 "FANG": {"bors": "Nasdaq", "navn": "Diamondback Energy", "segmenter": ["wti"]},
 "FCX": {"bors": "NYSE", "navn": "Freeport-McMoRan", "segmenter": ["kobber"]},
 "FRO.OL": {"bors": "Oslo", "navn": "Frontline", "segmenter": ["ship_vlcc", "ship_suezmax"]},
 "FXPO.L": {"bors": "London", "navn": "Ferrexpo", "segmenter": ["jernmalm"]},
 "GLEN.L": {"bors": "London", "navn": "Glencore", "segmenter": ["nikkel", "tinn"]},
 "GNK": {"bors": "NYSE", "navn": "Genco Shipping", "segmenter": ["ship_kamsarmax", "ship_ultramax", "ship_handysize"]},
 "GT": {"bors": "Nasdaq", "navn": "Goodyear", "segmenter": ["gummi_rss3", "gummi_tsr20"]},
 "HAFNI.OL": {"bors": "Oslo", "navn": "Hafnia", "segmenter": ["ship_aframax"]},
 "HAL.SI": {"bors": "Singapore", "navn": "Halcyon Agri", "segmenter": ["gummi_rss3", "gummi_tsr20"]},
 "HCC": {"bors": "NYSE", "navn": "Warrior Met Coal", "segmenter": ["kull"]},
 "HSHP.OL": {"bors": "Oslo", "navn": "Himalaya Shipping", "segmenter": ["ship_capesize"]},
 "HSY": {"bors": "NYSE", "navn": "Hershey", "segmenter": ["kakao"]},
 "JDEP.AS": {"bors": "Amsterdam", "navn": "JDE Peet's", "segmenter": ["kaffe_arabica"]},
 "MICP.PA": {"bors": "Paris", "navn": "Michelin", "segmenter": ["gummi_rss3", "gummi_tsr20"]},
 "MOS": {"bors": "NYSE", "navn": "Mosaic", "segmenter": ["kalium"]},
 "MOWI.OL": {"bors": "Oslo", "navn": "Mowi", "segmenter": ["fiskemel"]},
 "MPE.L": {"bors": "London", "navn": "M.P. Evans Group", "segmenter": ["palmeolje", "kokosolje", "te"]},
 "NAT": {"bors": "NYSE", "navn": "Nordic American Tankers", "segmenter": ["ship_suezmax"]},
 "NEM": {"bors": "NYSE", "navn": "Newmont", "segmenter": ["gold"]},
 "NESN.SW": {"bors": "Zürich", "navn": "Nestlé", "segmenter": ["kaffe_robusta"]},
 "NEXA": {"bors": "NYSE", "navn": "Nexa Resources", "segmenter": ["sink"]},
 "NHY.OL": {"bors": "Oslo", "navn": "Norsk Hydro", "segmenter": ["aluminium"]},
 "NTR": {"bors": "NYSE", "navn": "Nutrien", "segmenter": ["urea", "kalium"]},
 "OET.OL": {"bors": "Oslo", "navn": "Okeanis Eco Tankers", "segmenter": ["ship_vlcc", "ship_suezmax"]},
 "PANL": {"bors": "Nasdaq", "navn": "Pangaea Logistics", "segmenter": ["ship_kamsarmax", "ship_ultramax", "ship_handysize"]},
 "RE.L": {"bors": "London", "navn": "REA Holdings", "segmenter": ["palmeolje"]},
 "RIO.L": {"bors": "London", "navn": "Rio Tinto", "segmenter": ["jernmalm"]},
 "SALM.OL": {"bors": "Oslo", "navn": "SalMar", "segmenter": ["fiskemel"]},
 "SBLK": {"bors": "Nasdaq", "navn": "Star Bulk Carriers", "segmenter": ["ship_kamsarmax", "ship_ultramax", "ship_capesize"]},
 "SBUX": {"bors": "Nasdaq", "navn": "Starbucks", "segmenter": ["kaffe_arabica", "kaffe_robusta"]},
 "SHEL.L": {"bors": "London", "navn": "Shell", "segmenter": ["ttf"]},
 "TATACONSUM.NS": {"bors": "Mumbai", "navn": "Tata Consumer", "segmenter": ["te"]},
 "TECK-B.TO": {"bors": "Toronto", "navn": "Teck Resources", "segmenter": ["bly"]},
 "TGA.L": {"bors": "London", "navn": "Thungela Resources", "segmenter": ["kull"]},
 "TMIP.L": {"bors": "London", "navn": "Taylor Maritime", "segmenter": ["ship_handysize"]},
 "TNK": {"bors": "NYSE", "navn": "Teekay Tankers", "segmenter": ["ship_aframax"]},
 "TRMD-A.CO": {"bors": "København", "navn": "TORM", "segmenter": ["ship_aframax"]},
 "UNA.AS": {"bors": "Amsterdam", "navn": "Unilever", "segmenter": ["te"]},
 "VALE": {"bors": "NYSE", "navn": "Vale", "segmenter": ["nikkel", "jernmalm"]},
 "VAR.OL": {"bors": "Oslo", "navn": "Vår Energi", "segmenter": ["brent"]},
 "YAR.OL": {"bors": "Oslo", "navn": "Yara International", "segmenter": ["urea", "kalium"]},
}

ALLE = sorted(AKSJER)


def prov(navn, fn, pause=0.25):
    try:
        r = fn()
        print(f"   OK    {navn:22s} {r}")
        time.sleep(pause); return r
    except Exception as e:
        print(f"   feil  {navn:22s} {type(e).__name__} {str(e)[:60]}")
        time.sleep(pause); return None


# ===================================================== 1. kurser for D-leddene

print("=" * 78)
print("1. KURSHISTORIKK. D trenger fem aar for fall-fra-topp og 200-dagers")
print("=" * 78)

def yahoo(sym, rng="10y", iv="1d"):
    j = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}",
                     params={"range": rng, "interval": iv}, headers=UA, timeout=T)
    j.raise_for_status(); res = j.json()["chart"]["result"][0]
    s = pd.Series(res["indicators"]["quote"][0]["close"],
                  index=pd.to_datetime(res["timestamp"], unit="s")).dropna()
    return s[~s.index.duplicated(keep="last")]

KURS, mangler = {}, []
print(f"\n{'ticker':14s} {'n':>6} {'fra':>12} {'til':>12} {'aar':>5}  {'fall fra 5-aarstopp':>20}  {'% uker <200d':>13}")
for tk in ALLE:
    try:
        s = yahoo(tk)
        if len(s) < 260:
            raise ValueError(f"bare {len(s)} dager")
        KURS[tk] = s
        aar = (s.index[-1] - s.index[0]).days / 365.25
        topp5 = s[s.index >= s.index[-1] - pd.Timedelta(days=1826)].max()
        fall = 100 * (s.iloc[-1] / topp5 - 1)
        ma = s.rolling(200).mean()
        uke = (s < ma).resample("W").last().dropna()
        u200 = 100 * uke[uke.index >= uke.index[-1] - pd.Timedelta(days=1826)].mean()
        print(f"{tk:14s} {len(s):>6} {str(s.index[0].date()):>12} {str(s.index[-1].date()):>12} "
              f"{aar:>5.1f}  {fall:>19.1f} %  {u200:>12.0f} %")
    except Exception as e:
        mangler.append(tk)
        print(f"{tk:14s} {'FEIL':>6}  {type(e).__name__} {str(e)[:48]}")
    time.sleep(0.2)

print(f"\n   {len(KURS)} av {len(ALLE)} med brukbar kurshistorikk")
if mangler:
    print(f"   mangler: {', '.join(mangler)}")
    print("\n   Proever stooq for dem som feilet:")
    SUFF = {".OL": ".no", ".ST": ".se", ".CO": ".dk", ".L": ".uk", ".TO": ".ca",
            ".V": ".ca", ".SW": ".ch", ".AS": ".nl", ".PA": ".fr", ".SI": ".sg", ".NS": ".in"}
    for tk in mangler:
        base = re.sub(r"\.[A-Z]+$", "", tk).lower().replace("-", "")
        suff = next((v for k, v in SUFF.items() if tk.endswith(k)), ".us")
        def g(b=base, s=suff):
            t = requests.get(f"https://stooq.com/q/d/l/?s={b}{s}&i=d", headers=UA, timeout=T).text
            if not t.startswith("Date"): return f"ikke CSV: {t[:40]!r}"
            d = pd.read_csv(io.StringIO(t))
            return f"{len(d)} rader, {d.iloc[0,0]} til {d.iloc[-1,0]}"
        prov(f"stooq {base}{suff}", g)


# ============================================== 2. ETF-kapital som kapitulasjon

print("\n" + "=" * 78)
print("2. TEMA-ETF-ER. Kapital som forlater temaet er Ds tredje brukbare ledd")
print("=" * 78)
print("   Testes paa to maater: kurs fra Yahoo (alltid), og utstederens egen")
print("   daglige fil med forvaltningskapital (varierer).")

ETF = {"uran": "URA", "kobber": "COPX", "gull": "GDX", "metall bredt": "XME",
       "torrlast": "BDRY", "oljeservice": "OIH", "olje og gass": "XOP",
       "litium": "LIT", "stal": "SLX", "jordbruk": "MOO"}
print()
for seg, sym in ETF.items():
    def g(s=sym):
        k = yahoo(s, rng="max")
        topp = k[k.index >= k.index[-1] - pd.Timedelta(days=1826)].max()
        return (f"{len(k)} dager fra {k.index[0].date()}, "
                f"fall fra 5-aarstopp {100*(k.iloc[-1]/topp-1):.0f} %")
    prov(f"{seg} ({sym})", g)

print("\n   Utstedernes egne filer med forvaltningskapital:")
UTSTEDER = {
 "Global X URA": "https://globalxetfs.com/funds/ura/?download_full_holdings=true",
 "Global X COPX": "https://globalxetfs.com/funds/copx/?download_full_holdings=true",
 "VanEck GDX": "https://www.vaneck.com/us/en/investments/gold-miners-etf-gdx/holdings/",
 "SSGA XME": "https://www.ssga.com/us/en/intermediary/library-content/products/"
             "fund-data/etfs/us/holdings-daily-us-en-xme.xlsx",
 "Breakwave BDRY": "https://etfmanagers.com/funds/bdry/",
}
for navn, u in UTSTEDER.items():
    def g(u=u):
        r = requests.get(u, headers=UA, timeout=T, allow_redirects=True)
        t = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", r.text[:400000]))
        m = re.search(r"(net assets|aum|fund assets|total net)[^.]{0,80}?"
                      r"([$€]?\s?[\d][\d,.]{5,})", t, re.I)
        return (f"{r.status_code}, {len(r.content):,} b"
                + (f", fant: {m.group(0)[:70]!r}" if m else ", ingen kapitaltall i teksten"))
    prov(navn, g, pause=0.6)


# ============================================ 3. SEC XBRL for C, selvoppdagende

print("\n" + "=" * 78)
print("3. C FRA REGNSKAPET. Hvilke selskaper har SEC-tall, og hva heter feltene")
print("=" * 78)
print("   Ingen begreper gjettes. Skriptet scanner hva hvert selskap faktisk")
print("   bruker, i baade us-gaap og ifrs-full, og rapporterer antall aarstall.")

LEDD = {
 "kontanter": r"^(CashAndCashEquivalents|CashCashEquivalentsRestricted|Cash$)",
 "gjeld":     r"^(LongTermDebt|DebtCurrent|DebtLongtermAndShorttermCombined|Borrowings|"
              r"LongtermBorrowings|ShorttermBorrowings)",
 "drift_kontantstrom": r"(NetCashProvidedByUsedInOperatingActivities$|"
              r"CashFlowsFromUsedInOperatingActivities$)",
 "egenkapital": r"^(StockholdersEquity$|Equity$|EquityAttributableToOwnersOfParent$)",
 "rente":     r"(InterestExpense|InterestPaid|FinanceCosts)",
 "driftskostnad": r"(OperatingExpenses$|CostsAndExpenses$|OperatingCosts)",
}
FORMER = {"10-K", "20-F", "40-F", "10-Q", "6-K"}

try:
    tick = requests.get("https://www.sec.gov/files/company_tickers.json",
                        headers=SEC_UA, timeout=45).json()
    KART = {v["ticker"].upper(): str(v["cik_str"]).zfill(10) for v in tick.values()}
    print(f"\n   SECs tickerliste: {len(KART)} selskaper")
except Exception as e:
    KART = {}
    print(f"\n   FEIL paa tickerlisten: {type(e).__name__} {str(e)[:50]}")

def secnavn(tk):
    """Norske og europeiske tickere maa strippes for borssuffiks."""
    for k in (tk, re.sub(r"\.[A-Z]+$", "", tk), re.sub(r"-[A-Z]$", "", re.sub(r"\.[A-Z]+$", "", tk))):
        if k.upper() in KART: return k.upper()
    return None

print(f"\n   {'ticker':14s} {'i SEC':>7}  " + "".join(f"{k[:11]:>13s}" for k in LEDD))
funn, utenfor = {}, []
for tk in ALLE:
    nk = secnavn(tk)
    if not nk:
        utenfor.append(tk); print(f"   {tk:14s} {'nei':>7}")
        continue
    try:
        cf = requests.get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{KART[nk]}.json",
                          headers=SEC_UA, timeout=90).json()
    except Exception as e:
        print(f"   {tk:14s} {'FEIL':>7}  {type(e).__name__} {str(e)[:40]}")
        continue
    fakta = {}
    for tak in ("us-gaap", "ifrs-full"):
        fakta.update({k: v for k, v in cf.get("facts", {}).get(tak, {}).items()})
    rad, valg = [], {}
    for ledd, mons in LEDD.items():
        best = None
        for begrep, d in fakta.items():
            if not re.search(mons, begrep, re.I): continue
            for enh, pkt in d.get("units", {}).items():
                if enh != "USD" and not enh.startswith("USD"): continue
                aar = {p["end"][:4] for p in pkt if p.get("form") in FORMER}
                if best is None or len(aar) > best[0]: best = (len(aar), begrep)
        rad.append(f"{best[0]:>13}" if best else f"{'-':>13}")
        if best: valg[ledd] = best[1]
    funn[tk] = valg
    print(f"   {tk:14s} {'ja':>7}  " + "".join(rad))

n_full = sum(1 for v in funn.values() if len(v) >= 4)
print(f"\n   {len(funn)} av {len(ALLE)} finnes hos SEC, {n_full} har minst fire "
      f"av seks ledd. {len(utenfor)} staar utenfor: {', '.join(utenfor)}")
print("\n   Begrepene som ble valgt, for de fem forste:")
for tk, v in list(funn.items())[:5]:
    print(f"      {tk}")
    for ledd, b in v.items(): print(f"         {ledd:20s} {b[:60]}")


# ===================================== 4. nordiske selskaper, som ikke filer SEC

print("\n" + "=" * 78)
print("4. DE NORDISKE. 13 Oslo, 1 Stockholm, 1 København filer ikke hos SEC")
print("=" * 78)
print("   15 av 60 aksjer. Uten dem er C blind paa nettopp de")
print("   instrumentene du helst vil eie.")

NORD = ['2020.OL', 'AKRBP.OL', 'AUSS.OL', 'BOL.ST', 'EQNR.OL', 'FRO.OL']
def yq(sym, mod):
    r = requests.get(f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{sym}",
                     params={"modules": mod}, headers=UA, timeout=T)
    d = r.json().get("quoteSummary", {}).get("result")
    if not d: return f"{r.status_code}, tomt svar: {r.text[:70]!r}"
    k = d[0].get(mod, {})
    if isinstance(k, dict) and k.get("balanceSheetStatements"):
        rader = k["balanceSheetStatements"]
        return f"{len(rader)} perioder, felt: {sorted(rader[0].keys())[:6]}"
    return f"{r.status_code}, noekler: {sorted(k)[:8] if isinstance(k, dict) else type(k).__name__}"

print()
for s in NORD:
    for mod in ("balanceSheetHistory", "financialData", "defaultKeyStatistics"):
        prov(f"{s} / {mod}", lambda s=s, m=mod: yq(s, m), pause=0.4)

print("\n   Andre veier til nordiske regnskapstall:")
ANDRE = {
 "Euronext Oslo instrument": "https://live.euronext.com/en/product/equities/NO0010096985-XOSL",
 "Oslo Bors nyhetsweb": "https://newsweb.oslobors.no/",
 "Equinor IR XBRL": "https://www.equinor.com/investors",
 "Frontline IR": "https://www.frontline.bm/financial-information/",
 "Borsdata API (krever nokkel)": "https://apiservice.borsdata.se/v1/instruments",
}
for navn, u in ANDRE.items():
    def g(u=u):
        r = requests.get(u, headers=UA, timeout=T)
        return f"{r.status_code}, {len(r.content):,} b"
    prov(navn, g, pause=0.5)

print("\n" + "=" * 78)
print("1 avgjor om D kan bygges og for hvor mange. 3 avgjor det samme for C.")
print("4 avgjor om C i det hele tatt kan dekke de norske instrumentene.")
print("Send hele utskriften tilbake.")
