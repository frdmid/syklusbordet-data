# ---------------------------------------------------------------------------
# Syklusbordet: eksplorativ instrumentsonde for IKZ-universet
#
# Formaal: finne hvilke instrumenter en norsk privatperson med IKZ-konto paa
# Nordnet faktisk kan kjope, og som samvarierer sterkest med raavarene i
# modellen.
#
# Hva som er ute:
#   ETC og ETN. De er gjeldspapirer, ikke fond, og gaar ikke paa IKZ. Det
#   rammer nettopp de 13 papirene som maalte best i forrige runde (CRUD 0,95,
#   BRNT 0,90). Erstatningene maa maales, ikke antas.
#   ETF-er med amerikansk domisil (COPX, GDX, XME, XOP, MOO, URA, BDRY). PRIIPs
#   krever nokkelinformasjon paa EOS-format, som amerikanske utstedere ikke
#   lager. De brukes fortsatt internt som temaproxy i D, men kan ikke kjopes.
#
# Hva som er inne:
#   UCITS-ETF-er notert paa Xetra, London, Amsterdam eller SIX.
#   Enkeltaksjer paa Oslo, Stockholm, Kobenhavn, Helsinki, London, Xetra,
#   Amsterdam, Paris, SIX, USA og Toronto.
#
# Maalingen: se README-blokken nederst i filen.
#
# Kjores manuelt fra Actions-fanen. Skriver sonde_ikz.json og sonde_ikz.md.
# ---------------------------------------------------------------------------

REPO = "frdmid/syklusbordet-data"
BRANCH = "main"
TIMEOUT = 25

import base64, io, json, os, re, time, warnings
import numpy as np
import pandas as pd
import requests

warnings.filterwarnings("ignore")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
MIRROR = "https://raw.githubusercontent.com/datasets/"

MIN_N        = 60     # minste felles maanedstall for at et par rapporteres
NOK_N        = 96     # minste felles maanedstall for at et par kan brukes
HORISONT     = 12     # primaer holdehorisont, maaneder
HORISONT_2   = 24     # robusthetssjekk
BOOT         = 1000   # blokkbootstrap-trekninger
P_GULV       = 0.15   # under denne korrelasjonen er p-verdien uinteressant
BLOKK        = 24     # blokklengde, maaneder
BUNNVINDU    = 18     # halv bredde paa vinduet som daterer en bunn
FIKS         = "2016-01"   # fast sammenligningsvindu, se README nederst

LOGG = []
def note(k, ok, d=""):
    LOGG.append({"kilde": k, "status": "OK" if ok else "FEIL", "detalj": d})
    print(("  ok    " if ok else "  FEIL  ") + k + ("   " + d if d else ""))


def get(url, **kw):
    for forsok in range(3):
        try:
            r = requests.get(url, headers=UA, timeout=kw.pop("timeout", TIMEOUT), **kw)
            if r.status_code in (429, 502, 503):
                time.sleep(3 * (forsok + 1)); continue
            r.raise_for_status()
            return r
        except requests.RequestException:
            if forsok == 2:
                raise
            time.sleep(2 * (forsok + 1))
    raise RuntimeError("ga opp")


# =========================================================== 1. raavareserier
# Samme kilder, samme avkortinger som priser.py. Dette er bevisst duplisert og
# ikke lest fra segments/: de publiserte seriene er kuttet til 180 maaneder for
# grafens skyld, og sonden trenger hele historikken.

def csv_series(url, monthly=False):
    d = pd.read_csv(io.StringIO(get(url).text)).iloc[:, :2]
    d.columns = ["Date", "Value"]
    d["Value"] = pd.to_numeric(d["Value"], errors="coerce")
    d = d.dropna()
    if monthly:
        d["Date"] = pd.PeriodIndex(d["Date"].astype(str), freq="M")
        return d.set_index("Date")["Value"].sort_index()
    d["Date"] = pd.to_datetime(d["Date"])
    s = d.set_index("Date")["Value"].resample("ME").last().dropna()
    s.index = s.index.to_period("M")
    return s


def pink_sheet():
    kand = []
    try:
        html = get("https://www.worldbank.org/en/research/commodity-markets", timeout=40).text
        kand += [u if u.startswith("http") else "https://www.worldbank.org" + u
                 for u in re.findall(r'https?://[^"\']*?CMO[^"\']*?Monthly[^"\']*?\.xlsx', html)]
    except Exception:
        pass
    kand.append("https://thedocs.worldbank.org/en/doc/"
                "18675f1d1639c7a34d463f59263ba0a2-0050012025/related/"
                "CMO-Historical-Data-Monthly.xlsx")
    for u in dict.fromkeys(kand):
        try:
            raw = get(u, timeout=90).content
            for skip in (4, 5, 6):
                try:
                    df = pd.read_excel(io.BytesIO(raw), sheet_name="Monthly Prices", skiprows=skip)
                    df = df.rename(columns={df.columns[0]: "t"})
                    m = df[df["t"].astype(str).str.match(r"^\d{4}M\d{1,2}$", na=False)]
                    if len(m) > 100:
                        m = m.copy()
                        m["t"] = pd.PeriodIndex(
                            m["t"].astype(str).str.replace("M", "-", regex=False), freq="M")
                        return m.set_index("t").apply(pd.to_numeric, errors="coerce")
                except Exception:
                    pass
        except Exception:
            pass
    raise RuntimeError("Pink Sheet utilgjengelig")


AVKORT = {"gold": "1971-08", "aluminium": "1980-01", "nikkel": "1980-01",
          "te": "1980-01", "kakao": "1980-01", "urea": "2000-01",
          "ttf": "2000-01", "kull": "2000-01", "jernmalm": "2010-01"}
UTEN_A = set()

SPEIL = [("brent", "oil-prices/main/data/brent-daily.csv", False),
         ("wti", "oil-prices/main/data/wti-daily.csv", False),
         ("henryhub", "natural-gas/main/data/daily.csv", False),
         ("gold", "gold-prices/main/data/monthly.csv", True)]

PINK = [("kobber", "Copper"), ("nikkel", "Nickel"), ("aluminium", "Aluminum"),
        ("sink", "Zinc"), ("bly", "Lead"), ("tinn", "Tin"),
        ("jernmalm", "Iron ore"), ("kull", "Coal, Australian"),
        ("ttf", "Natural gas, Europe"), ("urea", "Urea"),
        ("fiskemel", "Fish meal"),
        ("kakao", "Cocoa"), ("kaffe_arabica", "Coffee, Arabica"),
        ("kaffe_robusta", "Coffee, Robusta"), ("palmeolje", "Palm oil"),
        ("gummi_rss3", "Rubber, RSS3"), ("gummi_tsr20", "Rubber, TSR20"),
        ("kokosolje", "Coconut oil"), ("te", "Tea, avg 3 auctions")]

print("1. Deflator og raavarepriser")
cpi = csv_series(MIRROR + "cpi-us/main/data/cpiai.csv")
note("deflator", True, f"siste {cpi.index[-1]}")

def deflater(nom):
    nom = nom.dropna().sort_index()
    return (nom * (cpi.dropna().iloc[-1] / cpi.reindex(nom.index).ffill())).dropna()

RAAVARE = {}
for sid, sti, mnd in SPEIL:
    try:
        s = csv_series(MIRROR + sti, monthly=mnd)
        if sid in AVKORT:
            s = s.loc[AVKORT[sid]:]
        RAAVARE[sid] = deflater(s)
    except Exception as e:
        note(f"speil {sid}", False, str(e)[:60])
try:
    ps = pink_sheet()
    norm = lambda x: re.sub(r"[^a-z0-9]", "", str(x).lower())
    kol = {norm(c): c for c in ps.columns}
    for sid, nokkel in PINK:
        eksakt = [v for k, v in kol.items() if k == norm(nokkel)]
        delvis = [v for k, v in kol.items() if norm(nokkel) in k]
        traff = eksakt or delvis
        if not traff:
            note(f"Pink Sheet {sid}", False, f"ingen kolonne som ligner '{nokkel}'")
            continue
        s = ps[traff[0]].dropna()
        if sid in AVKORT:
            s = s.loc[AVKORT[sid]:]
        RAAVARE[sid] = deflater(s)
except Exception as e:
    note("Pink Sheet", False, str(e)[:80])

# Uran. Ikke i Pink Sheet. IMF sin serie via FRED, med en kopi i repoet som
# reserve dersom FRED ikke svarer fra Actions-maskinen.
# Stillstandstesten: 15 % paa 90-tallet, 4 % paa 2000-tallet, 0 % etter. Godt
# under terskelen paa rundt 40 % som utloste avkorting for de ni andre, saa
# serien brukes hel fra 1992.
for navn, url, mnd in [
        ("FRED PURANUSDM", "https://fred.stlouisfed.org/graph/fredgraph.csv?id=PURANUSDM", False),
        ("repokopi uran", f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/uran_reserve.csv", True)]:
    try:
        RAAVARE["uran"] = deflater(csv_series(url, monthly=mnd))
        note(f"uran ({navn})", True, f"{len(RAAVARE['uran'])} mnd fra {RAAVARE['uran'].index[0]}")
        break
    except Exception as e:
        note(f"uran ({navn})", False, str(e)[:60])

for sid in UTEN_A:
    RAAVARE.pop(sid, None)     # administrert pris, ikke et marked

# IKZ_KUN=<segment> maaler bare mot den ene raavaren, men mot HELE
# kandidatuniverset, slik at et papir som ikke var ventet aa folge den ogsaa
# kan dukke opp. Brukes naar et nytt segment kommer til, som uran 24.09.2026,
# uten aa skrive over forrige fulle kjoring i sonde_ikz.json.
KUN = os.environ.get("IKZ_KUN", "").strip()
if KUN:
    RAAVARE = {k: v for k, v in RAAVARE.items() if k == KUN}
    if not RAAVARE:
        raise SystemExit(f"IKZ_KUN={KUN}: raavaren kom ikke inn, se loggen over")
    print(f"   IKZ_KUN={KUN}: maaler bare mot denne")
note("raavareserier", True, f"{len(RAAVARE)} segment, "
     f"korteste {min(len(v) for v in RAAVARE.values())} mnd")


# ========================================================= 2. kandidatunivers
# segmenter = hvilke raavarer papiret er ventet aa folge. Alt annet maales
# ogsaa, men merkes som eksplorativt og faar strengere krav.
# b = bors. "" = USA, T = tvilsom tilgang paa Nordnet, maa verifiseres.

E = lambda t, n, segs, b="", alt=None: {"t": t, "navn": n, "segmenter": segs,
                                        "type": "aksje", "b": b, "alt": alt or []}
F = lambda t, n, segs, isin=None, alt=None: {"t": t, "navn": n, "segmenter": segs,
                                             "type": "ETF", "isin": isin, "b": "",
                                             "alt": alt or []}

KANDIDATER = [
    # ---- UCITS-ETF, sektor Europa. Eldst i universet, fra 2006 og 2007.
    F("EXH1.DE", "iShares STOXX Europe 600 Oil & Gas", ["brent", "wti", "ttf", "henryhub"], "DE000A0H08M3"),
    F("EXV6.DE", "iShares STOXX Europe 600 Basic Resources", ["kobber", "nikkel", "aluminium", "sink", "bly", "jernmalm", "kull"], "DE000A0F5UK5"),
    F("EXV7.DE", "iShares STOXX Europe 600 Chemicals", ["urea", "ttf"], "DE000A0Q4R36"),
    F("EXH3.DE", "iShares STOXX Europe 600 Food & Beverage", ["kakao", "kaffe_arabica", "te"], "DE000A0H08B4"),
    F("EXH9.DE", "iShares STOXX Europe 600 Utilities", ["ttf"], "DE000A0Q4R02"),
    # ---- UCITS-ETF, global sektor
    F("IOGP.L", "iShares Oil & Gas Exploration & Production", ["brent", "wti", "henryhub"], "IE00B6R51Z18"),
    F("WNRG.L", "SPDR MSCI World Energy", ["brent", "wti"], "IE00BYTRRB94"),
    F("XDW0.DE", "Xtrackers MSCI World Energy", ["brent", "wti"], "IE00BM67HL84"),
    F("IESU.L", "iShares S&P 500 Energy Sector", ["wti", "henryhub"], "IE00B42NKQ00"),
    F("MNCG.L", "iShares MSCI Global Metals & Mining Producers", ["kobber", "jernmalm", "nikkel", "sink"], "IE00B6R52036"),
    F("GDIG.L", "VanEck Global Mining", ["kobber", "jernmalm", "nikkel", "aluminium"], "IE00BDFBTQ78"),
    F("ISAG.L", "iShares Agribusiness", ["palmeolje"], "IE00B6R52143"),
    # ---- UCITS-ETF, gull og gruve
    F("GDX.L", "VanEck Gold Miners UCITS", ["gold"], "IE00BQQP9F84"),
    F("GJGB.L", "VanEck Junior Gold Miners UCITS", ["gold"], "IE00BQQP9G91"),
    F("SPGP.L", "iShares Gold Producers", ["gold"], None),
    F("IAUP.L", "iShares Gold Producers (USD acc)", ["gold"], None),
    # ---- UCITS-ETF, nyere nisjer. Ventet for korte, tas med for aa se n.
    F("COPX.L", "Global X Copper Miners UCITS", ["kobber"], "IE000M7V94E1"),
    F("COPM.L", "iShares Copper and Metals Mining UCITS", ["kobber"], "IE000RSSEWJ1"),
    F("URNU.L", "Global X Uranium UCITS", ["uran"], "IE000NDWFGA5"),
    F("U3O8.L", "Sprott Uranium Miners UCITS", ["uran"], "IE0005YK6564"),
    # ---- UCITS-ETF, bredt raavarebytte. Fond, ikke ETC, og dermed lovlige.
    F("EXXY.DE", "iShares Diversified Commodity Swap", ["kobber", "brent", "aluminium"], "DE000A0H0728"),
    F("XDBC.DE", "Xtrackers Optimum Yield Diversified Commodity Swap", ["kobber", "brent"], "LU0292106167"),
    F("CMFP.L", "L&G Longer Dated All Commodities", ["kobber", "brent"], "IE00B4WPHX27"),
    F("CMOD.L", "Invesco Bloomberg Commodity", ["kobber", "brent"], "IE00BD6FTQ80"),
    # ---- kontroll: verdensindeks. Brukes til partiell korrelasjon.
    F("IWDA.L", "iShares Core MSCI World", [], "IE00B4L5Y983"),

    # ---- olje og gass, Norden og Europa
    E("EQNR.OL", "Equinor", ["brent", "ttf"]), E("AKRBP.OL", "Aker BP", ["brent"]),
    E("VAR.OL", "Vår Energi", ["brent"]), E("DNO.OL", "DNO", ["brent"]),
    E("SUBC.OL", "Subsea 7", ["brent"]), E("TGS.OL", "TGS", ["brent"]),
    E("BORR.OL", "Borr Drilling", ["brent"]), E("SDRL", "Seadrill", ["brent"], alt=["SDRL.OL"]),
    E("SHEL.L", "Shell", ["brent", "ttf"]), E("BP.L", "BP", ["brent", "ttf"]),
    E("TTE.PA", "TotalEnergies", ["brent", "ttf"]), E("NESTE.HE", "Neste", ["brent", "palmeolje"]),
    E("CNA.L", "Centrica", ["ttf"]), E("ENGI.PA", "Engie", ["ttf"]),
    E("RWE.DE", "RWE", ["ttf", "kull"]), E("EOAN.DE", "E.ON", ["ttf"]),
    E("FORTUM.HE", "Fortum", ["ttf"]), E("ORSTED.CO", "Ørsted", ["ttf"]),
    # ---- olje og gass, Nord-Amerika
    E("XOM", "ExxonMobil", ["brent", "wti"]), E("CVX", "Chevron", ["brent", "wti"]),
    E("COP", "ConocoPhillips", ["wti"]), E("FANG", "Diamondback Energy", ["wti"]),
    E("DVN", "Devon Energy", ["wti"]), E("EOG", "EOG Resources", ["wti"]),
    E("OXY", "Occidental", ["wti"]), E("APA", "APA Corp", ["wti"]),
    E("CTRA", "Coterra Energy", ["wti", "henryhub"], alt=["COG", "CXO"]), E("EQT", "EQT Corporation", ["henryhub"]),
    E("AR", "Antero Resources", ["henryhub"]), E("RRC", "Range Resources", ["henryhub"]),
    E("CNX", "CNX Resources", ["henryhub"]), E("EXE", "Expand Energy", ["henryhub"]),
    E("GPOR", "Gulfport Energy", ["henryhub"]), E("LNG", "Cheniere Energy", ["henryhub", "ttf"]),
    E("SLB", "SLB", ["brent"]), E("HAL", "Halliburton", ["wti"]), E("BKR", "Baker Hughes", ["brent"]),
    E("CNQ.TO", "Canadian Natural", ["wti"]), E("SU.TO", "Suncor", ["wti"]),
    E("CVE.TO", "Cenovus", ["wti"]), E("TOU.TO", "Tourmaline Oil", ["henryhub"]),
    E("ARX.TO", "ARC Resources", ["henryhub"]), E("BIR.TO", "Birchcliff Energy", ["henryhub"]),
    E("PEY.TO", "Peyto", ["henryhub"]), E("WCP.TO", "Whitecap Resources", ["wti"]),
    E("VET.TO", "Vermilion Energy", ["wti", "ttf"]), E("MEG.TO", "MEG Energy", ["wti"]),

    # ---- gull
    E("NEM", "Newmont", ["gold"]), E("AEM", "Agnico Eagle", ["gold"]),
    E("B", "Barrick Mining", ["gold"]), E("GFI", "Gold Fields", ["gold"]),
    E("AU", "AngloGold Ashanti", ["gold"]), E("KGC", "Kinross Gold", ["gold"]),
    E("HMY", "Harmony Gold", ["gold"]), E("FNV", "Franco-Nevada", ["gold"]),
    E("WPM", "Wheaton Precious Metals", ["gold"]), E("RGLD", "Royal Gold", ["gold"]),
    E("PAAS", "Pan American Silver", ["gold"]), E("SSRM", "SSR Mining", ["gold"]),
    E("IAG", "IAMGOLD", ["gold"]), E("BTG", "B2Gold", ["gold"]),
    E("NGD", "New Gold", ["gold"], alt=["NGD.TO"]), E("EDV.TO", "Endeavour Mining", ["gold"]),
    E("K.TO", "Kinross (Toronto)", ["gold"]), E("ELD.TO", "Eldorado Gold", ["gold"]),
    E("EQX.TO", "Equinox Gold", ["gold"]), E("LUG.TO", "Lundin Gold", ["gold"]),
    E("FRES.L", "Fresnillo", ["gold"]), E("HOC.L", "Hochschild Mining", ["gold"]),

    # ---- kobber og basismetall
    E("ANTO.L", "Antofagasta", ["kobber"]), E("GLEN.L", "Glencore", ["kobber", "nikkel", "sink", "kull", "tinn"]),
    E("RIO.L", "Rio Tinto", ["jernmalm", "aluminium", "kobber"]),
    E("AAL.L", "Anglo American", ["kobber", "jernmalm"]), E("BHP.L", "BHP Group", ["jernmalm", "kobber"]),
    E("FCX", "Freeport-McMoRan", ["kobber"]), E("SCCO", "Southern Copper", ["kobber"]),
    E("TECK-B.TO", "Teck Resources", ["kobber", "sink", "kull"]),
    E("FM.TO", "First Quantum", ["kobber"]), E("HBM.TO", "Hudbay Minerals", ["kobber", "sink"]),
    E("LUN.TO", "Lundin Mining", ["kobber", "sink"]), E("IVN.TO", "Ivanhoe Mines", ["kobber"]),
    E("ERO.TO", "Ero Copper", ["kobber"]), E("CS.TO", "Capstone Copper", ["kobber"]),
    E("NEXA", "Nexa Resources", ["sink", "bly"]), E("BOL.ST", "Boliden", ["sink", "kobber", "bly"]),
    E("NDA.DE", "Aurubis", ["kobber"]), E("ATYM.L", "Atalaya Mining", ["kobber"]),
    E("CAML.L", "Central Asia Metals", ["kobber", "sink"]),

    # ---- aluminium, nikkel, jernmalm, staal
    E("NHY.OL", "Norsk Hydro", ["aluminium"]), E("AA", "Alcoa", ["aluminium"]),
    E("CENX", "Century Aluminum", ["aluminium"]), E("KALU", "Kaiser Aluminum", ["aluminium"]),
    E("CSTM", "Constellium", ["aluminium"]),
    E("VALE", "Vale", ["jernmalm", "nikkel"]), E("ERA.PA", "Eramet", ["nikkel"]),
    E("OUT1V.HE", "Outokumpu", ["nikkel"]), E("SBSW", "Sibanye-Stillwater", ["nikkel", "gold"]),
    E("FXPO.L", "Ferrexpo", ["jernmalm"]), E("MT.AS", "ArcelorMittal", ["jernmalm", "kull"]),
    E("SSAB-B.ST", "SSAB", ["jernmalm", "kull"]), E("STLD", "Steel Dynamics", ["jernmalm"], alt=["X"]),
    E("NUE", "Nucor", ["jernmalm"]), E("CLF", "Cleveland-Cliffs", ["jernmalm"]),
    E("CIA.TO", "Champion Iron", ["jernmalm"]), E("LIF.TO", "Labrador Iron Ore", ["jernmalm"]),

    # ---- kull
    E("TGA.L", "Thungela Resources", ["kull"]), E("BTU", "Peabody Energy", ["kull"]),
    E("HCC", "Warrior Met Coal", ["kull"]), E("AMR", "Alpha Metallurgical", ["kull"]),
    E("CNR", "Core Natural Resources", ["kull"], alt=["CEIX", "ARCH"]), E("ARLP", "Alliance Resource", ["kull"]),
    E("NC", "NACCO Industries", ["kull"]),

    # ---- gjodsel
    E("YAR.OL", "Yara International", ["ttf"]),
    E("CF", "CF Industries", ["urea", "henryhub"]), E("NTR", "Nutrien", []),
    E("MOS", "Mosaic", []), E("ICL", "ICL Group", []),
    E("SDF.DE", "K+S", []), E("OCI.AS", "OCI NV", ["urea"]),
    E("IPI", "Intrepid Potash", []), E("LXU", "LSB Industries", ["urea"]),

    # ---- fiskemel og sjomat
    E("AUSS.OL", "Austevoll Seafood", ["fiskemel"]), E("MOWI.OL", "Mowi", ["fiskemel"]),
    E("SALM.OL", "SalMar", ["fiskemel"]), E("LSG.OL", "Lerøy Seafood", ["fiskemel"]),
    E("GSF.OL", "Grieg Seafood", ["fiskemel"]), E("BAKKA.OL", "Bakkafrost", ["fiskemel"]),
    E("BAKKA.CO", "Bakkafrost (Kobenhavn)", ["fiskemel"], alt=["NRS.OL"]),

    # ---- kakao, kaffe, te
    E("BARN.SW", "Barry Callebaut", ["kakao"]), E("NESN.SW", "Nestlé", ["kakao", "kaffe_arabica", "kaffe_robusta"]),
    E("LISN.SW", "Lindt & Sprüngli", ["kakao"]), E("MDLZ", "Mondelez", ["kakao"]),
    E("HSY", "Hershey", ["kakao"]), E("TR", "Tootsie Roll", ["kakao"]),
    E("CLA-B.ST", "Cloetta", ["kakao"]), E("ORK.OL", "Orkla", ["kakao", "kaffe_arabica"]),
    E("SBUX", "Starbucks", ["kaffe_arabica"]), E("JDEP.AS", "JDE Peet's", ["kaffe_arabica", "kaffe_robusta", "te"], alt=["JDEP.F"]),
    E("KDP", "Keurig Dr Pepper", ["kaffe_arabica"]),
    E("UNA.AS", "Unilever", ["te", "palmeolje"]), E("ULVR.L", "Unilever (London)", ["te", "palmeolje"]),

    # ---- palmeolje, vegetabilsk olje, kokos
    E("MPE.L", "M.P. Evans Group", ["palmeolje"]), E("RE.L", "REA Holdings", ["palmeolje"]),
    E("AAK.ST", "AAK AB", ["palmeolje", "kokosolje"]), E("ADM", "Archer-Daniels-Midland", ["palmeolje", "kokosolje"]),
    E("BG", "Bunge Global", ["palmeolje", "kokosolje"]), E("CRDA.L", "Croda International", ["kokosolje"]),

    # ---- gummi
    E("ML.PA", "Michelin", ["gummi_rss3", "gummi_tsr20"], alt=["MICP.PA"]),
    E("CON.DE", "Continental", ["gummi_rss3", "gummi_tsr20"]),
    E("GT", "Goodyear", ["gummi_rss3", "gummi_tsr20"]),
    E("TYRES.HE", "Nokian Renkaat", ["gummi_rss3", "gummi_tsr20"]),
    E("TREL-B.ST", "Trelleborg", ["gummi_tsr20"]),

    # ---- uran. Nytt segment. B er allerede maalt for uran i b_capex.json og
    #      har ligget ubrukt fordi segmentet ikke fantes.
    E("CCJ", "Cameco", ["uran"]), E("CCO.TO", "Cameco (Toronto)", ["uran"]),
    E("KAP.L", "Kazatomprom GDR", ["uran"]), E("NXE", "NexGen Energy", ["uran"]),
    E("UEC", "Uranium Energy", ["uran"]), E("DNN", "Denison Mines", ["uran"]),
    E("UUUU", "Energy Fuels", ["uran"]), E("URG", "Ur-Energy", ["uran"]),
    E("PDN.AX", "Paladin Energy", ["uran"], "T"),
    E("U-UN.TO", "Sprott Physical Uranium Trust", ["uran"], "T", alt=["U-U.TO", "SRUUF"]),
    E("BWXT", "BWX Technologies", ["uran"]), E("LEU", "Centrus Energy", ["uran"]),

    # ---- forbrukersiden. Papirer der raavaren er en kostnad og ikke en
    #      inntekt. Ventet negativt fortegn: dyr raavare klemmer marginen,
    #      fallende raavare utvider den. Kjeden er lengre enn paa
    #      produsentsiden (raavare faller, innkjopspris faller med
    #      etterslep, margin utvider seg, kursen folger etter), saa forvent
    #      lavere R2 og et tregere signal.
    E("IAG.L", "IAG (British Airways)", ["brent"]),
    E("LHA.DE", "Lufthansa", ["brent"]), E("AF.PA", "Air France-KLM", ["brent"]),
    E("RYAAY", "Ryanair", ["brent"]), E("NAS.OL", "Norwegian Air Shuttle", ["brent"]),
    E("CCL", "Carnival", ["brent"], alt=["CCL.L", "CUK"]), E("RCL", "Royal Caribbean", ["brent"]),
    E("DSV.CO", "DSV", ["brent"]), E("KNIN.SW", "Kuehne+Nagel", ["brent"]),
    E("DHL.DE", "DHL Group", ["brent"]), E("MAERSK-B.CO", "A.P. Moller-Maersk", ["brent"]),
    E("BAS.DE", "BASF", ["ttf", "urea"]), E("1COV.DE", "Covestro", ["ttf"], alt=["COV.DE"]),
    E("AI.PA", "Air Liquide", ["ttf"]), E("LIN", "Linde", ["ttf"]),
    E("HEI.DE", "Heidelberg Materials", ["ttf", "kull"]),
    E("HOLN.SW", "Holcim", ["ttf", "kull"]), E("SGO.PA", "Saint-Gobain", ["ttf"]),
    E("VOW3.DE", "Volkswagen", ["aluminium", "jernmalm"]),
    E("BMW.DE", "BMW", ["aluminium", "jernmalm"]),
    E("MBG.DE", "Mercedes-Benz", ["aluminium"]), E("RNO.PA", "Renault", ["aluminium"]),
    E("ABBN.SW", "ABB", ["kobber"]), E("SU.PA", "Schneider Electric", ["kobber"]),
    E("LR.PA", "Legrand", ["kobber"]), E("NEX.PA", "Nexans", ["kobber", "aluminium"]),
    E("NKT.CO", "NKT", ["kobber", "aluminium"]),
    E("ENR.DE", "Siemens Energy", ["kobber", "aluminium"]),
    E("ALFA.ST", "Alfa Laval", ["jernmalm"]), E("SAND.ST", "Sandvik", ["jernmalm"]),
    E("VOLV-B.ST", "Volvo", ["jernmalm", "aluminium"]),
    E("ATCO-A.ST", "Atlas Copco", ["kobber"]),
    E("BALL", "Ball Corporation", ["aluminium"]), E("CCK", "Crown Holdings", ["aluminium"]),
    E("AMCR", "Amcor", ["aluminium"]),

    # ---- tvilsom tilgang, tas med for aa se om de i det hele tatt er verdt en
    #      forespørsel til Nordnet
    E("AFM.V", "Alphamin Resources", ["tinn"], "T"),
    E("SIP.BR", "Sipef", ["palmeolje"], "T"),
    E("LOTB.BR", "Lotus Bakeries", ["kakao"], "T"),
]

# Hvilke par som er ventet NEGATIVE. Raavaren er en kostnad for papiret, ikke
# en inntekt. Uten dette kartet leses et negativt fortegn som en feil, og det
# er det ikke: et sterkt negativt par er like handlbart som et positivt, bare
# fra motsatt ende av syklusen.
#
# To rettinger av det som laa inne fra for:
#   Yara mot TTF. Gass er 70 til 80 prosent av kostnaden i ammoniakk. Yara er
#   ventet positiv mot urea og NEGATIV mot gass. Sto som positiv i begge.
#   Oppdrettsselskapene mot fiskemel. Fiskemel er for, altsaa kostnad. Bare
#   Austevoll er delvis produsent gjennom Pelagia, og staar derfor som blandet.
FORBRUKER = {
    "YAR.OL": {"ttf"}, "CF": {"henryhub"}, "LXU": {"henryhub"},
    "MOWI.OL": {"fiskemel"}, "SALM.OL": {"fiskemel"}, "LSG.OL": {"fiskemel"},
    "GSF.OL": {"fiskemel"}, "BAKKA.OL": {"fiskemel"}, "NRS.OL": {"fiskemel"},
    "NESTE.HE": {"palmeolje"},
    "BARN.SW": {"kakao"}, "NESN.SW": {"kakao", "kaffe_arabica", "kaffe_robusta"},
    "LISN.SW": {"kakao"}, "MDLZ": {"kakao"}, "HSY": {"kakao"}, "TR": {"kakao"},
    "CLA-B.ST": {"kakao"}, "ORK.OL": {"kakao", "kaffe_arabica"},
    "SBUX": {"kaffe_arabica"}, "KDP": {"kaffe_arabica"},
    "JDEP.AS": {"kaffe_arabica", "kaffe_robusta", "te"},
    "UNA.AS": {"te", "palmeolje"}, "ULVR.L": {"te", "palmeolje"},
    "AAK.ST": {"palmeolje", "kokosolje"}, "CRDA.L": {"kokosolje"},
    "MICP.PA": {"gummi_rss3", "gummi_tsr20"}, "CON.DE": {"gummi_rss3", "gummi_tsr20"},
    "GT": {"gummi_rss3", "gummi_tsr20"}, "TYRES.HE": {"gummi_rss3", "gummi_tsr20"},
    "TREL-B.ST": {"gummi_tsr20"},
    "IAG.L": {"brent"}, "LHA.DE": {"brent"}, "AF.PA": {"brent"}, "RYAAY": {"brent"},
    "NAS.OL": {"brent"}, "CCL.L": {"brent"}, "RCL": {"brent"}, "DSV.CO": {"brent"},
    "KNIN.SW": {"brent"}, "DHL.DE": {"brent"}, "MAERSK-B.CO": {"brent"},
    "BAS.DE": {"ttf", "urea"}, "1COV.DE": {"ttf"}, "AI.PA": {"ttf"}, "LIN": {"ttf"},
    "HEI.DE": {"ttf", "kull"}, "HOLN.SW": {"ttf", "kull"}, "SGO.PA": {"ttf"},
    "VOW3.DE": {"aluminium", "jernmalm"}, "BMW.DE": {"aluminium", "jernmalm"},
    "MBG.DE": {"aluminium"}, "RNO.PA": {"aluminium"},
    "ABBN.SW": {"kobber"}, "SU.PA": {"kobber"}, "LR.PA": {"kobber"},
    "NEX.PA": {"kobber", "aluminium"}, "NKT.CO": {"kobber", "aluminium"},
    "ENR.DE": {"kobber", "aluminium"}, "ALFA.ST": {"jernmalm"}, "SAND.ST": {"jernmalm"},
    "VOLV-B.ST": {"jernmalm", "aluminium"}, "ATCO-A.ST": {"kobber"},
    "BALL": {"aluminium"}, "CCK": {"aluminium"}, "AMCR": {"aluminium"},
    "MT.AS": {"jernmalm"}, "SSAB-B.ST": {"jernmalm"}, "X": {"jernmalm"},
    "NUE": {"jernmalm"}, "CLF": {"jernmalm"},   # staalverk: malm er innsats
    "NDA.DE": {"kobber"},                        # Aurubis smelter, tjener paa margin
    "AUSS.OL": set(),                            # blandet, eier Pelagia
}
BLANDET = {"AUSS.OL": {"fiskemel"}, "NHY.OL": {"aluminium"}, "GLEN.L": {"kull"}}

KONTROLL = "IWDA.L"
print(f"\n2. Kandidatunivers: {len(KANDIDATER)} papirer")


# ============================================================== 3. kursinnhenting

FX = {"USD": None, "EUR": ("EURUSD=X", False), "GBP": ("GBPUSD=X", False),
      "GBp": ("GBPUSD=X", False), "NOK": ("NOK=X", True), "SEK": ("SEK=X", True),
      "DKK": ("DKK=X", True), "CHF": ("CHF=X", True), "CAD": ("CAD=X", True),
      "ILS": ("ILS=X", True), "AUD": ("AUDUSD=X", False)}
_fx_cache = {}

def fx_serie(sym, invert):
    if sym not in _fx_cache:
        s = yahoo_maaned(sym, justert=False)
        _fx_cache[sym] = (1.0 / s) if invert else s
    return _fx_cache[sym]


def yahoo_maaned(symbol, justert=True):
    """Maanedsserie, tidsstemplet i borsens egen tidssone.

    Tidssonen er ikke pynt. Yahoo setter maanedsstolpen til maanedens forste
    dag i lokal tid. Leses den som UTC havner alt utenfor amerikansk tid en
    maaned for tidlig, og Aker BP mot Brent leste -0,02 i stedet for 0,58.
    """
    j = "&events=div%7Csplit&includeAdjustedClose=true" if justert else ""
    res = get(f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
              f"?period1=0&period2={int(time.time())}&interval=1mo{j}").json()
    res = res["chart"]["result"][0]
    meta = res.get("meta") or {}
    tz = meta.get("exchangeTimezoneName") or "UTC"
    idx = pd.to_datetime(res["timestamp"], unit="s", utc=True).tz_convert(tz)
    v = None
    if justert:
        try:
            v = res["indicators"]["adjclose"][0]["adjclose"]
        except Exception:
            v = None
    if v is None:
        v = res["indicators"]["quote"][0]["close"]
    s = pd.Series(v, index=idx).dropna()
    s = s[s > 0]        # en nullkurs gir log(0) = -inf, som dropna ikke fjerner
    s.index = s.index.to_period("M")
    s = s[~s.index.duplicated(keep="last")]
    s.attrs["valuta"] = meta.get("currency") or "USD"
    return s


TILLATT = ("", ".OL", ".ST", ".CO", ".HE", ".L", ".DE", ".AS", ".PA", ".SW", ".TO")

def finn_via_isin(isin):
    r = get(f"https://query2.finance.yahoo.com/v1/finance/search?q={isin}"
            f"&quotesCount=25&newsCount=0").json()
    ut = []
    for q in r.get("quotes", []):
        sym = q.get("symbol", "")
        if not sym:
            continue
        suff = "." + sym.split(".")[-1] if "." in sym else ""
        if suff in TILLATT:
            ut.append(sym)
    return ut


print("\n3. Kurser")
KURS, META = {}, {}
for k in KANDIDATER:
    sym, s = k["t"], None
    for forsok in [k["t"]] + list(k.get("alt") or []):
        try:
            s = yahoo_maaned(forsok)
            if len(s) < 24:
                s = None
            else:
                sym = forsok
                break
        except Exception:
            s = None
    if s is None and k.get("isin"):
        for alt in finn_via_isin(k["isin"]):
            try:
                s2 = yahoo_maaned(alt)
                if len(s2) >= 24 and (s is None or len(s2) > len(s)):
                    s, sym = s2, alt
            except Exception:
                pass
            time.sleep(0.3)
    if s is None:
        note(f"kurs {k['t']}", False, "ingen serie")
        continue
    val = s.attrs.get("valuta", "USD")
    if val not in FX:
        note(f"kurs {k['t']}", False, f"ukjent valuta {val}")
        continue
    if FX[val]:
        try:
            r = fx_serie(*FX[val]).reindex(s.index).ffill()
            s = (s * r).dropna()      # maaneder foer valutakursen finnes faller ut
        except Exception as e:
            note(f"valuta {k['t']}", False, f"{val}: {str(e)[:40]}")
            continue
    if val == "GBp":
        s = s / 100.0
    s = deflater(s)                    # realavkastning, samme deflator som raavaren
    KURS[k["t"]] = s
    META[k["t"]] = {**{x: k[x] for x in ("navn", "segmenter", "type", "b")},
                    "symbol": sym, "valuta": val,
                    "fra": str(s.index[0]), "n": len(s)}
    time.sleep(0.25)
note("kurser", True, f"{len(KURS)} av {len(KANDIDATER)} hentet")


# ================================================================= 4. maaling

def logendring(s, h):
    x = np.log(s.astype(float))
    d = (x - x.shift(h))
    return d[np.isfinite(d)]


def blokkbootstrap(x, y, b=BOOT, L=BLOKK):
    """Nullfordeling for korrelasjon naar begge serier er autokorrelerte.

    Overlappende 12-maanedersendringer deler elleve av tolv observasjoner med
    naboen. En vanlig t-test paa dem er meningsloes. Her flyttes y i sirkulaere
    blokker paa L maaneder, slik at nullhypotesen beholder y sin egen
    autokorrelasjon og bare river opp koblingen til x.
    """
    n = len(x)
    if n < 3 * L:
        return None
    r0 = float(np.corrcoef(x, y)[0, 1])
    IX = _boot_ix(n, L, b)
    Y = y[IX]                                   # b x n
    xc = x - x.mean()
    Yc = Y - Y.mean(axis=1, keepdims=True)
    r = (Yc @ xc) / np.sqrt((Yc ** 2).sum(axis=1) * (xc ** 2).sum())
    return (int((np.abs(r) >= abs(r0)).sum()) + 1) / (b + 1)


_ix_cache = {}
def _boot_ix(n, L, b):
    if (n, L, b) not in _ix_cache:
        nb = int(np.ceil(n / L))
        rng = np.random.default_rng(20260922)
        start = rng.integers(0, n, (b, nb))
        blokk = (start[:, :, None] + np.arange(L)[None, None, :]) % n
        _ix_cache[(n, L, b)] = blokk.reshape(b, -1)[:, :n]
    return _ix_cache[(n, L, b)]


def vendepunkt(real, topp=False):
    """Maaneder som er laveste (eller hoyeste) realpris i +/- BUNNVINDU mnd."""
    v = real.values
    ut = []
    for i in range(BUNNVINDU, len(v) - BUNNVINDU):
        vindu = v[i - BUNNVINDU: i + BUNNVINDU + 1]
        if v[i] == (vindu.max() if topp else vindu.min()):
            ut.append(i)
    # slaa sammen naboer som tilhorer samme bunn
    grupper, siste = [], -99
    for i in ut:
        if i - siste > BUNNVINDU:
            grupper.append(i)
        siste = i
    return [real.index[i] for i in grupper]


bunner = lambda real: vendepunkt(real, topp=False)
topper = lambda real: vendepunkt(real, topp=True)


_le = {}
def le(tick, h):
    if (tick, h) not in _le:
        _le[(tick, h)] = logendring(KURS[tick], h)
    return _le[(tick, h)]

kontroll = KURS.get(KONTROLL)
resultat = []
print("\n4. Maaling")
for sid, real in sorted(RAAVARE.items()):
    r1_c = logendring(real, 1)
    r12_c = logendring(real, HORISONT)
    r24_c = logendring(real, HORISONT_2)
    bnr, tpp = bunner(real), topper(real)
    for tick, kurs in KURS.items():
        if tick == KONTROLL:
            continue
        m = META[tick]
        a_priori = sid in m["segmenter"]
        vent = ("f" if sid in FORBRUKER.get(tick, set())
                else ("b" if sid in BLANDET.get(tick, set()) else "p"))
        i1 = r1_c.index.intersection(le(tick, 1).index)
        if len(i1) < MIN_N:
            continue
        x1 = r1_c.reindex(i1).values
        y1 = le(tick, 1).reindex(i1).values
        r1 = float(np.corrcoef(x1, y1)[0, 1])
        beta1 = float(np.polyfit(x1, y1, 1)[0])

        i12 = r12_c.index.intersection(le(tick, HORISONT).index)
        r12 = beta12 = p12 = None
        if len(i12) >= MIN_N:
            x = r12_c.reindex(i12).values
            y = le(tick, HORISONT).reindex(i12).values
            r12 = float(np.corrcoef(x, y)[0, 1])
            beta12 = float(np.polyfit(x, y, 1)[0])
            p12 = blokkbootstrap(x, y) if abs(r12) >= P_GULV else None

        # Fast vindu. Full felles historikk gir hvert par sin egen periode, og
        # da maaler man like mye naar papiret ble notert som hvordan det folger
        # raavaren. Det faste vinduet er det som rangerer.
        rf1 = rf12 = None
        nf = 0
        i1f = i1[i1 >= pd.Period(FIKS, "M")]
        if len(i1f) >= 48:
            nf = len(i1f)
            rf1 = float(np.corrcoef(r1_c.reindex(i1f).values,
                                    le(tick, 1).reindex(i1f).values)[0, 1])
            i12f = i12[i12 >= pd.Period(FIKS, "M")] if len(i12) else i12
            if len(i12f) >= 48:
                rf12 = float(np.corrcoef(r12_c.reindex(i12f).values,
                                         le(tick, HORISONT).reindex(i12f).values)[0, 1])

        i24 = r24_c.index.intersection(le(tick, HORISONT_2).index)
        r24 = None
        if len(i24) >= MIN_N:
            r24 = float(np.corrcoef(r24_c.reindex(i24).values,
                                    le(tick, HORISONT_2).reindex(i24).values)[0, 1])

        # partiell korrelasjon mot verdensindeksen: hva raavaren tilfoyer
        # utover at aksjer generelt steg
        rp = None
        if kontroll is not None:
            w = logendring(kontroll, 1).reindex(i1)
            ok = w.notna().values
            if ok.sum() >= MIN_N:
                xw = float(np.corrcoef(x1[ok], w.values[ok])[0, 1])
                yw = float(np.corrcoef(y1[ok], w.values[ok])[0, 1])
                rxy = float(np.corrcoef(x1[ok], y1[ok])[0, 1])
                d = np.sqrt((1 - xw ** 2) * (1 - yw ** 2))
                rp = float((rxy - xw * yw) / d) if d > 1e-9 else None

        # asymmetri: folger papiret raavaren opp like godt som ned
        opp = x1 > 0
        b_opp = float(np.polyfit(x1[opp], y1[opp], 1)[0]) if opp.sum() >= 24 else None
        b_ned = float(np.polyfit(x1[~opp], y1[~opp], 1)[0]) if (~opp).sum() >= 24 else None

        # Fangstgrad fra daterte vendepunkt. Maales fra begge ender.
        # Et papir med negativt fortegn skal ikke maales fra raavarens bunn:
        # der er det forbrukeren har det vondest. Toppen er inngangen.
        def fangst(punkter):
            par = []
            for b in punkter:
                if b not in kurs.index:
                    continue
                bt = b + HORISONT
                if bt not in real.index or bt not in kurs.index:
                    continue
                par.append((str(b), round(float(np.log(real[bt] / real[b])), 3),
                            round(float(np.log(kurs[bt] / kurs[b])), 3)))
            if len(par) < 2:
                return None, par
            sc = sum(x[1] for x in par)
            return (round(sum(x[2] for x in par) / sc, 2) if abs(sc) > 0.05 else None), par
        fang, par = fangst(bnr)
        fang_t, par_t = fangst(tpp)

        resultat.append({
            "segment": sid, "ticker": tick, "symbol": m["symbol"], "navn": m["navn"],
            "type": m["type"], "bors": m["b"], "a_priori": a_priori,
            "vent": vent,
            "n1": int(len(i1)), "n12": int(len(i12)), "fra": m["fra"],
            "r1": round(r1, 3), "beta1": round(beta1, 2),
            "r12": None if r12 is None else round(r12, 3),
            "beta12": None if beta12 is None else round(beta12, 2),
            "p12": None if p12 is None else round(p12, 4),
            "r24": None if r24 is None else round(r24, 3),
            "nf": int(nf),
            "rf1": None if rf1 is None else round(rf1, 3),
            "rf12": None if rf12 is None else round(rf12, 3),
            "r_partiell": None if rp is None else round(rp, 3),
            "beta_opp": None if b_opp is None else round(b_opp, 2),
            "beta_ned": None if b_ned is None else round(b_ned, 2),
            "fangst": fang, "bunner": par,
            "fangst_topp": fang_t, "topper": par_t,
            "som_ventet": None if not a_priori or vent == "b" else
                          bool((r1 > 0) == (vent == "p"))})
    print(f"   {sid:16} {sum(1 for r in resultat if r['segment']==sid):4} par")

# Benjamini-Hochberg over de eksplorative parene. De a priori-ventede parene
# holdes utenfor: de er ikke funnet ved leting.
eks = [r for r in resultat if not r["a_priori"] and r["p12"] is not None]
eks.sort(key=lambda r: r["p12"])
m_ = len(eks)
for i, r in enumerate(eks, 1):
    r["q12"] = round(min(1.0, r["p12"] * m_ / i), 4)
for r in resultat:
    r.setdefault("q12", None)

note("par maalt", True, f"{len(resultat)} totalt, {sum(1 for r in resultat if r['a_priori'])} a priori")


# ============================================================== 5. publisering

def push(path, text):
    api = f"https://api.github.com/repos/{REPO}/contents/{path}"
    h = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}
    sha = None
    try:
        g = requests.get(api, headers=h, params={"ref": BRANCH}, timeout=30)
        if g.status_code == 200:
            sha = g.json().get("sha")
    except Exception:
        pass
    body = {"message": f"sonde ikz {path}", "branch": BRANCH,
            "content": base64.b64encode(text.encode("utf-8")).decode()}
    if sha:
        body["sha"] = sha
    requests.put(api, headers=h, json=body, timeout=60).raise_for_status()


NF_TRYGG = 72     # maaneder i det faste vinduet for at rangeringen er til aa stole paa

def sorter(r):
    """Rangerer paa tallverdi, men legger korte serier bakerst.

    Et par maalt paa fem aar kan naa hoye korrelasjoner ved flaks alene, og
    uten dette skillet fyller nynoterte papirer toppen av hver liste.
    """
    for k in ("rf12", "rf1", "r12", "r1"):
        if r.get(k) is not None:
            return (0 if r.get("nf", 0) >= NF_TRYGG else 1, -abs(r[k]))
    return (2, 0.0)

L = ["# Sonde: instrumenter i IKZ-universet", "",
     f"Kjort {time.strftime('%Y-%m-%d %H:%M')} UTC. "
     f"{len(KURS)} papirer hentet av {len(KANDIDATER)} forsokt. "
     f"{len(resultat)} par maalt mot {len(RAAVARE)} raavarer.", "",
     "Kolonner: r1 = korrelasjon i manedlige realendringer. r12 = samme over "
     "overlappende 12-manedersendringer, p fra blokkbootstrap. rp = partiell "
     "korrelasjon i r1 etter at verdensindeksen er tatt ut. beta12 = hvor mye "
     "papiret beveger seg per enhet ravare over 12 maneder. opp/ned = beta maalt "
     "bare i maneder der ravaren steg, mot bare der den falt. fangstB og fangstT "
     "= papirets samlede 12-manedersavkastning fra daterte bunner og fra daterte "
     "topper, delt pa ravarens. "
     "vent = hvilket fortegn papiret var ventet a ha: p = produsent, ravaren er "
     "inntekt, ventet positiv. f = forbruker, ravaren er kostnad, ventet negativ. "
     "b = blandet. ok = fortegnet kom ut som ventet. "
     f"rf1 og rf12 er de samme maalt i det faste vinduet fra {FIKS}, som er "
     "det eneste som er sammenlignbart pa tvers av papirer med ulik alder. "
     f"nf = antall maneder i det faste vinduet; par med nf under {NF_TRYGG} er "
     "sortert bakerst fordi en kort serie nar hoye tall ved flaks alene. "
     "ap = papiret var ventet a folge "
     "denne ravaren; tomt felt betyr at treffet er funnet ved leting.", ""]
for sid in sorted(RAAVARE):
    rad = [r for r in resultat if r["segment"] == sid]
    if not rad:
        continue
    rad.sort(key=sorter)
    nb, nt = len(bunner(RAAVARE[sid])), len(topper(RAAVARE[sid]))
    L += [f"## {sid}   ({nb} daterte bunner, {nt} daterte topper)", ""]
    hode = ("| papir | navn | type | n | nf | rf1 | rf12 | r1 | r12 | p12 | q12 | "
            "rp | beta12 | opp | ned | fangstB | fangstT | vent | ok | ap |")
    strek = "|" + "---|" * 20
    # To tabeller: papirer som folger raavaren, og papirer som gaar motsatt.
    # Et sterkt negativt par er handlbart fra motsatt ende av syklusen, saa det
    # skal ikke druknes nederst i en felles liste sortert paa tallverdi.
    def nivaa(r):
        for k in ("rf12", "rf1", "r12", "r1"):
            if r.get(k) is not None:
                return r[k]
        return 0.0
    for tittel, utvalg in (("Folger raavaren", [r for r in rad if nivaa(r) > 0]),
                           ("Gaar motsatt", [r for r in rad if nivaa(r) < 0])):
        if not utvalg:
            continue
        L += [f"### {tittel}", "", hode, strek]
        for r in utvalg[:10]:
            g = lambda k: "" if r.get(k) is None else r[k]
            L.append(f"| {r['symbol']} | {r['navn'][:26]} | {r['type']} | {r['n1']} | "
                     f"{r['nf']} | {g('rf1')} | {g('rf12')} | {r['r1']} | {g('r12')} | "
                     f"{g('p12')} | {g('q12')} | {g('r_partiell')} | {g('beta12')} | "
                     f"{g('beta_opp')} | {g('beta_ned')} | {g('fangst')} | "
                     f"{g('fangst_topp')} | {r['vent']} | "
                     f"{'' if r['som_ventet'] is None else ('ja' if r['som_ventet'] else 'NEI')} | "
                     f"{'x' if r['a_priori'] else ''} |")
        L.append("")
ap = [r for r in resultat if r["som_ventet"] is not None]
feil = [r for r in ap if not r["som_ventet"]]
L += ["## Fortegn mot forventning", "",
      f"{len(feil)} av {len(ap)} par med forhandsantatt retning fikk motsatt "
      "fortegn av det antagelsen tilsa. Et feil fortegn er ikke et daarlig "
      "papir: det betyr at antagelsen om hvem som tjener og hvem som betaler "
      "var feil, og det er i seg selv verdt a vite.", ""]
if feil:
    feil.sort(key=sorter)
    L += ["| segment | papir | vent | r1 | rf1 | rf12 |", "|" + "---|" * 6]
    for r in feil[:30]:
        g = lambda k: "" if r.get(k) is None else r[k]
        L.append(f"| {r['segment']} | {r['symbol']} | {r['vent']} | {r['r1']} | "
                 f"{g('rf1')} | {g('rf12')} |")
    L.append("")

L += ["## Papirer som ikke lot seg hente", ""]
L += [f"- {l['kilde']}: {l['detalj']}" for l in LOGG if l["status"] == "FEIL"] or ["- ingen"]

if KUN:
    # Skrives til sonder/, som arbeidsflyten legger i repoet etter kjoringen.
    # Den fulle kjoringen i sonde_ikz.json roeres ikke.
    os.makedirs("sonder", exist_ok=True)
    with open(f"sonder/ikz_{KUN}.json", "w", encoding="utf-8") as f:
        json.dump({"kjort": time.strftime("%Y-%m-%d %H:%M:%S"), "kun": KUN, "logg": LOGG,
                   "meta": META, "par": resultat}, f, ensure_ascii=False, indent=1)
    print("\n".join(L))
    print(f"\n   skrevet sonder/ikz_{KUN}.json ({len(resultat)} par)")
    raise SystemExit(0)

try:
    push("sonde_ikz.json", json.dumps(
        {"kjort": time.strftime("%Y-%m-%d %H:%M:%S"), "logg": LOGG,
         "meta": META, "par": resultat}, ensure_ascii=False, indent=1))
    push("sonde_ikz.md", "\n".join(L))
    print(f"\n   publisert sonde_ikz.json og sonde_ikz.md ({len(resultat)} par)")
except Exception as e:
    print(f"\n   FEIL ved publisering: {e}")
    print("\n".join(L[:200]))


# ---------------------------------------------------------------------------
# README: hvorfor maalingen ser slik ut
#
# Maaleintervall: maanedlig.
#   Raavareseriene fra Pink Sheet er maanedlige, saa hoyere opplosning finnes
#   ikke paa den ene siden av paret. Dagsdata ble dessuten testet tidligere:
#   alle 15 par hadde toppunkt paa lag null, det vil si ingen ledetid aa hente,
#   og tidssonefeilen som dagsdata skjulte kostet en hel maaneds forskyvning.
#
# Horisont: 1, 12 og 24 maaneder.
#   Ett maaned maaler samvariasjon i normal drift. Det er tallet som ga median
#   0,17 i forrige runde og som gjor instrumentlaget til modellens svakeste del.
#   Tolv maaneder er horisonten en taalmodig bunnkjoper faktisk holder, og er
#   derfor det som avgjor om et papir er brukbart. Tjuefire er robusthetssjekk.
#   Overlappende tolvmaanedersendringer deler elleve av tolv observasjoner med
#   naboen, saa p-verdien kommer fra blokkbootstrap og ikke fra en t-test.
#
# Periode: full felles historikk, pluss et fast vindu fra 2016-01.
#   Ingen fast startdato for hovedmaalingen, fordi universet spriker fra 2006
#   (EXH1, EXV6) til 2023 (COPX UCITS). En fast start ville enten kaste ut de
#   unge eller maale dem paa en stump uten aa si fra. Derfor rapporteres n for
#   hvert par, med 60 maaneder som gulv for aa bli vist og 96 for aa kunne
#   brukes. Det faste vinduet fra 2016 er det som rangerer: det er den lengste
#   perioden de fleste papirene dekker, og det inneholder bunnen i 2016,
#   krasjet i 2020 og boomen i 2021 og 2022. Et par maalt bare fra 2019 har
#   aldri sett en bunn, og korrelasjonen er da maalt i en eneste oppgangsfase.
#
# Valuta: alt regnes om til dollar for maaling.
#   Raavaren er i dollar. Et papir notert i kroner baerer da USDNOK som felles
#   faktor, og siden kronen svekkes naar raavarer faller, demper det den maalte
#   sammenhengen kunstig. Maalingen skal vise raavarefolsomhet, ikke
#   valutaeffekt. Valutaeffekten for en norsk investor er reell, men den hoerer
#   hjemme i posisjonsbeslutningen og ikke i instrumentvalget.
#
# Realpriser: begge sider deflateres med samme amerikanske KPI.
#   Over en maaned er det likegyldig. Over tolv og tjuefire maaneder er det
#   ikke, i hvert fall ikke gjennom 2021 til 2023.
#
# Totalavkastning: justert sluttkurs, altsaa med utbytte.
#   Gruve- og oljeselskaper betaler ut mye i toppen av syklusen. Uten utbytte
#   undervurderes fangstgraden systematisk for nettopp de papirene som er
#   aktuelle.
#
# Partiell korrelasjon mot verdensindeksen.
#   Forrige runde viste at Yara fikk 0,02 i R2 utover at aksjer generelt steg,
#   mot 0,07 til 0,20 for de ovrige. Et papir som bare folger markedet er
#   ubrukelig som raavareeksponering, uansett hvor hoy raakorrelasjonen er.
#
# Opp- og nedbeta.
#   Et papir som folger raavaren ned uten aa folge den opp er verre enn
#   ingenting. Asymmetrien fanges ved aa regne stigningstallet separat i
#   maaneder der raavaren steg og der den falt.
#
# Fangstgrad fra daterte bunner.
#   Bunnene dateres i realprisen selv, som laveste maaned i et vindu paa pluss
#   minus atten maaneder, og uavhengig av modellens flagg. Flagget gir bare sju
#   klynger paa hele panelet, altsaa for faa hendelser per segment. Fangstgrad
#   er papirets samlede tolvmaanedersavkastning fra disse bunnene delt paa
#   raavarens. Faa observasjoner, saa tallet er beskrivende og ikke en test.
#
# Negativt fortegn.
#   Et sterkt negativt par er like handlbart som et positivt, bare fra motsatt
#   ende av syklusen. Papiret er da en forbruker: raavaren er kostnad og ikke
#   inntekt. Dyr raavare klemmer marginen, fallende raavare utvider den. Derfor
#   maales fangstgraden fra daterte topper i tillegg til daterte bunner, og
#   derfor rangeres tabellene paa tallverdi og ikke paa fortegn, med produsenter
#   og forbrukere i hver sin tabell.
#
#   Tre forbehold som er reelle og ikke formaliteter. For det forste er kjeden
#   lengre: raavaren faller, innkjopsprisen folger med etterslep fordi
#   kontraktene loper, marginen utvider seg, og forst da beveger kursen seg.
#   Forvent lavere R2 og et tregere signal enn paa produsentsiden. For det andre
#   avhenger gevinsten av om selskapet faar beholde besparelsen eller maa gi den
#   videre i pris, og det er en bransjestruktur og ikke en raavarepris. For det
#   tredje har forbrukerne hoyere markedsbeta enn produsentene, saa den
#   partielle korrelasjonen mot verdensindeksen er viktigere her: et papir som
#   bare folger markedet er ubrukelig uansett fortegn.
#
#   Modellen flagger i dag bare bunner, altsaa A hoy. Speilbildet, A lav og
#   raavaren dyr, er inngangen for forbrukersiden. Det er en egen hypotese som
#   ikke er testet, og den skal testes for den bygges inn.
#
# Multippel testing.
#   Rundt 4000 par maales. Det hoyeste tallet i en slik bunke er hoyt av seg
#   selv. Par som var ventet paa forhaand merkes a priori og vurderes direkte.
#   Resten er funnet ved leting og faar Benjamini-Hochberg-justert q-verdi. Et
#   uventet treff uten q under 0,1 er stoy til det motsatte er vist.
# ---------------------------------------------------------------------------
