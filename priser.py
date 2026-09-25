# ---------------------------------------------------------------------------
# Syklusbordet: ukentlig innhenting, v2.4
#
# Endret fra v1:
#  - FRED er ikke lenger i den kritiske stien. Deflatoren og olje/gass kommer
#    fra GitHub-speil som er verifisert nåbare. FRED er bare reservekilde.
#  - Ingen kall er uten feilsikring. Feiler en kilde, går resten videre.
#  - Korte tidsavbrudd, slik at en død vert koster 20 sekunder og ikke 60.
#  - Verdensbankens Pink Sheet finner lenken selv i stedet for å gjette URL.
#
# BELCO.OL, GOGL.OL og AGAS.OL er fjernet: de finnes ikke lenger.
# Golden Ocean gikk inn i CMB.TECH (CMBT).
#
# Kjøres av GitHub Actions ukentlig. Token kommer fra miljøet.
# ---------------------------------------------------------------------------

REPO = "frdmid/syklusbordet-data"
BRANCH = "main"
TIMEOUT = 20

import base64, io, json, re, time, warnings
import numpy as np
import pandas as pd
import requests

warnings.filterwarnings("ignore")
try:
    from google.colab import userdata
    GITHUB_TOKEN = userdata.get("GITHUB_TOKEN")
except Exception:
    import os
    GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")   # GitHub Actions setter denne

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0 Safari/537.36"}
MIN_HIST, CHART_MONTHS = 60, 180
MIRROR = "https://raw.githubusercontent.com/datasets/"
LOG, SEGMENTS = [], []


def note(kilde, ok, detalj=""):
    LOG.append({"kilde": kilde, "status": "OK" if ok else "FEIL", "detalj": detalj})
    print(("  ok    " if ok else "  FEIL  ") + kilde + ("   " + detalj if detalj else ""))


def get(url, **kw):
    r = requests.get(url, headers=UA, timeout=kw.pop("timeout", TIMEOUT), **kw)
    r.raise_for_status()
    return r


# ----------------------------------------------------------------- kildelesing

def csv_series(url, monthly=False):
    """To-kolonners CSV (dato, verdi) til månedsserie."""
    d = pd.read_csv(io.StringIO(get(url).text))
    d = d.iloc[:, :2]
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


def fred(series_id):
    """Reservekilde. Kort tidsavbrudd, får ikke lov til å henge."""
    return csv_series(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}")


def pink_sheet():
    """Finner gjeldende xlsx-lenke på CMO-siden i stedet for å gjette URL."""
    kandidater = []
    try:
        html = get("https://www.worldbank.org/en/research/commodity-markets",
                   timeout=30).text
        kandidater += [u if u.startswith("http") else "https://www.worldbank.org" + u
                       for u in re.findall(r'https?://[^"\']*?CMO[^"\']*?Monthly[^"\']*?\.xlsx', html)]
    except Exception as e:
        note("CMO-side (lenkesøk)", False, str(e)[:70])
    kandidater.append("https://thedocs.worldbank.org/en/doc/"
                      "18675f1d1639c7a34d463f59263ba0a2-0050012025/related/"
                      "CMO-Historical-Data-Monthly.xlsx")
    siste = None
    for u in dict.fromkeys(kandidater):
        try:
            raw = get(u, timeout=90).content
            for skip in (4, 5, 6):
                try:
                    df = pd.read_excel(io.BytesIO(raw), sheet_name="Monthly Prices",
                                       skiprows=skip)
                    df = df.rename(columns={df.columns[0]: "t"})
                    m = df[df["t"].astype(str).str.match(r"^\d{4}M\d{1,2}$", na=False)]
                    if len(m) > 100:
                        m = m.copy()
                        m["t"] = pd.PeriodIndex(
                            m["t"].astype(str).str.replace("M", "-", regex=False), freq="M")
                        note("Verdensbanken Pink Sheet", True,
                             f"{m.shape[1]} kolonner, {len(m)} måneder, skiprows={skip}")
                        return m.set_index("t").apply(pd.to_numeric, errors="coerce")
                except Exception as e:
                    siste = e
        except Exception as e:
            siste = e
    raise RuntimeError(f"ingen av {len(kandidater)} URL-er virket: {str(siste)[:70]}")


def yahoo_monthly(symbol):
    """Maanedskurs, tidsstemplet i borsens egen tidssone.

    Yahoo tidsstempler maanedsstolpen ved maanedens start i lokal tid. Leses
    den som UTC, faller 1. mars 00:00 CET paa 28. februar 23:00 UTC, og hele
    serien havner en maaned for tidlig. Feilen rammer alt utenfor amerikansk
    tid: Oslo, Stockholm, London og Sydney. Maalt paa vehicles.json ga den
    korrelasjon 0,58 mellom Aker BP og Brent ved ett maaneds forskyvning og
    -0,02 uten, altsaa et signal som saa ut som stoy.
    """
    res = get(f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
              f"?range=15y&interval=1mo").json()["chart"]["result"][0]
    tz = (res.get("meta") or {}).get("exchangeTimezoneName") or "UTC"
    idx = pd.to_datetime(res["timestamp"], unit="s", utc=True).tz_convert(tz)
    s = pd.Series(res["indicators"]["quote"][0]["close"], index=idx).dropna()
    s.index = s.index.to_period("M")
    return s[~s.index.duplicated(keep="last")]


def nve_magasin():
    d = pd.DataFrame(get("https://biapi.nve.no/magasinstatistikk/api/"
                         "Magasinstatistikk/HentOffentligData", timeout=60).json())
    d = d[d["omrType"] == "EL"]
    d["t"] = pd.PeriodIndex(pd.to_datetime(
        d["iso_aar"].astype(str) + "-" + d["iso_uke"].astype(str) + "-1",
        format="%G-%V-%u"), freq="M")
    return {f"NO{o}": g.groupby("t")["fyllingsgrad"].last() * 100
            for o, g in d.groupby("omrnr")}


# ---------------------------------------------------------------- signallogikk

def expanding_pct(x):
    v = np.asarray(x, dtype=float)
    out = np.full(len(v), np.nan)
    for i in range(len(v)):
        if i + 1 >= MIN_HIST:
            out[i] = (v[: i + 1] <= v[i]).sum() / (i + 1)
    return out


def expanding_pct_detrend(x, minn=60):
    """Persentil paa residualet etter at trenden er trukket ut, punkt-i-tid.
    Ved hver dato tilpasses trenden bare paa det som var kjent da.
    Retter feilen der en serie med fallende realpris faar stigende
    persentil av seg selv: Henry Hub laa over 80 i 66 % av tiden fordi
    realprisen falt 2,8 % i aaret, ikke fordi noe syklisk skjedde."""
    v = np.asarray(x, dtype=float)
    out = np.full(len(v), np.nan)
    for i in range(minn - 1, len(v)):
        y = v[: i + 1]
        t = np.arange(i + 1)
        b, a = np.polyfit(t, y, 1)
        r = y - (a + b * t)
        out[i] = (r <= r[i]).sum() / len(r)
    return (1 - out) * 100


def rolling_pct(x, w=120, minn=60):
    """Persentil i et rullende ti-aars vindu i stedet for hele historikken.
    Lar fordelingen folge regimet i stedet for aa slepe med seg 1960-tallet."""
    v = np.asarray(x, dtype=float)
    out = np.full(len(v), np.nan)
    for i in range(len(v)):
        lo = max(0, i - w + 1)
        if i - lo + 1 >= minn:
            y = v[lo : i + 1]
            out[i] = (y <= v[i]).sum() / len(y)
    return (1 - out) * 100


def trend_per_aar(x):
    v = np.asarray(x, dtype=float)
    if len(v) < 24:
        return None
    b, _ = np.polyfit(np.arange(len(v)), v, 1)
    return round(float(100 * (np.exp(b * 12) - 1)), 2)


def expanding_bands(x, qs=(10, 25, 50, 75, 90)):
    v = np.asarray(x, dtype=float)
    res = {q: np.full(len(v), np.nan) for q in qs}
    for i in range(len(v)):
        if i + 1 >= MIN_HIST:
            for q in qs:
                res[q][i] = np.percentile(v[: i + 1], q)
    return res


D95_SEGMENTER, D95_NIVAA = {"brent"}, 95


def build_segment(seg_id, name, group, unit, nom, cpi, note_txt, source, url):
    nom = nom.dropna().sort_index()
    real = (nom * (cpi.dropna().iloc[-1] / cpi.reindex(nom.index).ffill())).dropna()
    nom = nom.reindex(real.index)
    lr = np.log(real.values)
    A  = (1 - expanding_pct(lr)) * 100      # raa: mot hele egen historikk
    Ad = expanding_pct_detrend(lr)          # detrendet: mot trenden
    Ar = rolling_pct(lr)                    # rullende: mot siste ti aar
    bands = expanding_bands(real.values)

    idx = real.index
    keep = idx[-CHART_MONTHS:] if len(idx) > CHART_MONTHS else idx
    pos = {p: i for i, p in enumerate(idx)}

    # Bunnsone krever at BADE raa og detrendet A er over 80.
    #
    # Fram til nu gikk flagget paa raa A alene, med de to andre som
    # kvalitetsmerke. Det holdt ikke. Testet paa 24 segmenter 2011-2026, der
    # hver makrohendelse telles en gang og ikke en gang per segment:
    #
    #   raa A >= 80          4 klynger, klyngemedian +8 % over 24 mnd,  p = 0,27
    #   raa og detrendet     7 klynger, klyngemedian +37 %, 7 av 7,     p = 0,014
    #
    # Raa A alene lot seg ikke skille fra tilfeldige kjopsdatoer. Den stod
    # dessuten flagget 72 % av alle maaneder for aluminium og 66 % for Henry
    # Hub, altsaa en tilstand og ikke et signal.
    #
    # Den rullende skaaren er ute av flagget. I alle 120 maanedene der de to
    # andre laa over 80, laa den ogsaa over 80. Den avgjorde aldri noe.
    #
    # Oppsikt: raa over 80 mens detrendet ikke er. Lavt mot egen historie, men
    # forklart av trenden. Holdes synlig, men er ikke et flagg.
    if seg_id in UTEN_A:
        A = np.full(len(A), np.nan); Ad = np.full(len(Ad), np.nan)
        Ar = np.full(len(Ar), np.nan)
        for q in bands: bands[q][:] = np.nan
    over = lambda v, i: (not np.isnan(v[i])) and v[i] >= 80
    flagg = np.array([over(A, i) and over(Ad, i) for i in range(len(A))])
    oppsikt = np.array([over(A, i) and not flagg[i] for i in range(len(A))])
    # Parallelt signal, innfoert etter Frodes beslutning 25.09.2026: detrendet
    # A paa 95 eller mer, uavhengig av raa A. Bare for Brent. IKKE testet som
    # regel: ideen kom etter aa ha sett episoden fra desember 2025, og Brent
    # alene har fem innslag siden 1987 (1993-10, 1998-02, 2015-01, 2020-02,
    # 2025-12). Det vises og logges separat fra bunnsonen, slik at det kan
    # vurderes framover uten aa blandes med den testede regelen.
    if seg_id in D95_SEGMENTER:
        d95 = np.array([(not np.isnan(Ad[i])) and Ad[i] >= D95_NIVAA for i in range(len(Ad))])
    else:
        d95 = np.zeros(len(Ad), dtype=bool)
    enig = flagg
    miz = 0
    for i in range(len(idx) - 1, -1, -1):
        if enig[i]:
            miz += 1
        else:
            break

    rows = []
    for p in keep:
        i = pos[p]
        g = lambda q: None if np.isnan(bands[q][i]) else round(float(bands[q][i]), 4)
        rows.append({"t": str(p), "nom": round(float(nom[p]), 4),
                     "real": round(float(real[p]), 4),
                     "p10": g(10), "p25": g(25), "p50": g(50), "p75": g(75), "p90": g(90),
                     "A": None if np.isnan(A[i]) else round(float(A[i]), 1),
                     "Ad": None if np.isnan(Ad[i]) else round(float(Ad[i]), 1),
                     "Ar": None if np.isnan(Ar[i]) else round(float(Ar[i]), 1),
                     "flagg": bool(flagg[i]), "oppsikt": bool(oppsikt[i]),
                     **({"flagg_d95": bool(d95[i])} if seg_id in D95_SEGMENTER else {})})

    last, li = keep[-1], pos[keep[-1]]
    return {"id": seg_id, "name": name, "group": group, "unit": unit, "status": "live",
            "note": note_txt, "source": source, "source_url": url,
            "hist_start": str(idx[0]), "last_obs": str(last),
            "last_nom": round(float(nom[last]), 4), "last_real": round(float(real[last]), 4),
            "trend_pst_aar": trend_per_aar(lr),
            "scores": {"A": None if np.isnan(A[li]) else round(float(A[li]), 1),
                       "Ad": None if np.isnan(Ad[li]) else round(float(Ad[li]), 1),
                       "Ar": None if np.isnan(Ar[li]) else round(float(Ar[li]), 1),
                       "flagg": bool(flagg[li]),
                       "oppsikt": bool(oppsikt[li]),
                       **({"flagg_d95": bool(d95[li]),
                           "d95_regel": f"detrendet A >= {D95_NIVAA}, parallelt signal, ikke testet"}
                          if seg_id in D95_SEGMENTER else {}),
                       "A2": None, "B": None, "D": None, "S": None,
                       "gate": "ukjent", "months_in_zone": miz},
            "series": rows}


def legg_til(seg_id, navn, gruppe, enhet, serie, cpi, kilde, url, merknad=None):
    try:
        SEGMENTS.append(build_segment(
            seg_id, navn, gruppe, enhet, serie, cpi,
            merknad or "Prisnivåskåren A er beregnet. B, C og D venter på kilder.",
            kilde, url))
        sc = SEGMENTS[-1]["scores"]
        note(f"segment {seg_id}", True,
             f"A={sc['A']} detr={sc['Ad']} rull={sc['Ar']} "
             f"{'BUNNSONE' if sc['flagg'] else ('oppsikt' if sc['oppsikt'] else '')}"
             f"  siste {SEGMENTS[-1]['last_obs']}")
    except Exception as e:
        note(f"segment {seg_id}", False, f"{type(e).__name__}: {str(e)[:70]}")


# ----------------------------------------------------------------- publisering

def push(path, text):
    api = f"https://api.github.com/repos/{REPO}/contents/{path}"
    h = {"Authorization": f"Bearer {GITHUB_TOKEN}",
         "Accept": "application/vnd.github+json"}
    sha = None
    try:
        g = requests.get(api, headers=h, params={"ref": BRANCH}, timeout=30)
        if g.status_code == 200:
            sha = g.json().get("sha")
    except Exception:
        pass
    body = {"message": f"oppdatert {path}",
            "content": base64.b64encode(text.encode("utf-8")).decode(),
            "branch": BRANCH}
    if sha:
        body["sha"] = sha
    requests.put(api, headers=h, json=body, timeout=60).raise_for_status()


# --------------------------------------------------------------------- kjøring

print("1. Deflator")
# Reservekjede, innfoert 25.09.2026. KPI-speilet var eneste deflator, og faller
# det bort, stopper alt. Alle leddene er samme serie: amerikansk KPI for alle
# varer, ikke sesongjustert (BLS CUUR0000SA0). Den revideres ikke, saa det
# trengs ingen versjonshaandtering, bare et flagg naar tallet er gammelt.
# Realprisen regnes som nom * KPI(siste) / KPI(t), som ikke avhenger av
# basisaaret, saa OECD sin indeks (2015 = 100) gir samme realpris.
#   1 GitHub-speilet (datasets/cpi-us)
#   2 BLS flatfil (krever en User-Agent som sier hvem som spoer)
#   3 OECD SDMX
#   4 FRED
#   5 forrige ukes kopi i repoet (cpi_kopi.csv), merket som gammel
# Naar speilet virker, hentes BLS ogsaa som kontroll av de siste 24 maanedene.
BLS_UA = {"User-Agent": "Syklusbordet frode@h-k.no"}   # samme form som SEC_UA i overlevelse_c.py

def bls_cpi():
    t = requests.get("https://download.bls.gov/pub/time.series/cu/cu.data.1.AllItems",
                     headers=BLS_UA, timeout=40)
    t.raise_for_status()
    rader = {}
    for linje in t.text.splitlines()[1:]:
        f = [x.strip() for x in linje.split("\t")]
        if len(f) >= 4 and f[0] == "CUUR0000SA0" and f[2].startswith("M") and f[2] != "M13":
            rader[pd.Period(f"{f[1]}-{f[2][1:]}", "M")] = float(f[3])
    if len(rader) < 600:
        raise ValueError(f"bare {len(rader)} maaneder")
    return pd.Series(rader).sort_index()

def oecd_cpi():
    url = ("https://sdmx.oecd.org/public/rest/data/OECD.SDD.TPS,DSD_PRICES@DF_PRICES_ALL,1.0/"
           "USA.M.N.CPI.IX._T.N._Z?startPeriod=1950-01&format=csvfilewithlabels")
    d = pd.read_csv(io.StringIO(get(url, timeout=60).text))
    s = pd.Series(pd.to_numeric(d["OBS_VALUE"], errors="coerce").values,
                  index=pd.PeriodIndex(d["TIME_PERIOD"].astype(str), freq="M")).dropna().sort_index()
    if len(s) < 600:
        raise ValueError(f"bare {len(s)} maaneder")
    return s

def kopi_cpi():
    t = requests.get(f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/cpi_kopi.csv",
                     params={"cb": int(time.time())}, headers=UA, timeout=30)
    t.raise_for_status()
    d = pd.read_csv(io.StringIO(t.text))
    return pd.Series(d["kpi"].values, index=pd.PeriodIndex(d["mnd"].astype(str), freq="M"))

cpi, cpi_kilde = None, None
for navn, fn in [("GitHub-speil cpi-us", lambda: csv_series(MIRROR + "cpi-us/main/data/cpiai.csv")),
                 ("BLS flatfil CUUR0000SA0", bls_cpi),
                 ("OECD SDMX KPI USA", oecd_cpi),
                 ("FRED CPIAUCSL", lambda: fred("CPIAUCSL")),
                 ("forrige ukes kopi (cpi_kopi.csv)", kopi_cpi)]:
    try:
        cpi = fn()
        cpi_kilde = navn
        note(navn, True, f"siste {cpi.index[-1]}")
        break
    except Exception as e:
        note(navn, False, f"{type(e).__name__}: {str(e)[:70]}")
if cpi is None:
    raise SystemExit("Ingen deflator tilgjengelig. Alt annet er meningsløst uten. "
                     "Send loggen over til Claude.")
alder = (pd.Period(pd.Timestamp.now(), freq="M") - cpi.index[-1]).n
note("deflator, alder", alder <= 3 and not cpi_kilde.startswith("forrige"),
     f"{cpi_kilde}, siste {cpi.index[-1]}, {alder} mnd gammel"
     + (". GAMMEL: realprisene regnes mot en KPI som ikke er oppdatert" if alder > 3 else ""))
if cpi_kilde.startswith("GitHub"):
    try:
        kontroll = bls_cpi()
        f = cpi.index.intersection(kontroll.index)[-24:]
        avvik = float((cpi[f] / kontroll[f] - 1).abs().max() * 100)
        note("deflator, kontroll mot BLS", avvik < 0.05, f"{len(f)} mnd, stoerste avvik {avvik:.3f} %")
    except Exception as e:
        note("deflator, kontroll mot BLS", False, f"BLS svarte ikke: {type(e).__name__}: {str(e)[:50]}")

print("\n2. Energi og gull fra GitHub-speil")
MIRRORS = [
    ("brent", "Råolje (Brent)", "Energi", "USD/fat", "oil-prices/main/data/brent-daily.csv", False),
    ("wti", "Råolje (WTI)", "Energi", "USD/fat", "oil-prices/main/data/wti-daily.csv", False),
    ("henryhub", "Naturgass US (Henry Hub)", "Energi", "USD/MMBtu", "natural-gas/main/data/daily.csv", False),
    ("gold", "Gull", "Metall", "USD/unse", "gold-prices/main/data/monthly.csv", True),
]
# Noen serier starter foer prisen var en markedspris. Gull hadde forsvart kurs
# fram til gullvinduet ble lukket 15. august 1971, og staar uendret i ni av ti
# maaneder foer 1968. Med den perioden inne opptar den de billigste persentilene
# permanent: 206 av 206 flaggmaaneder laa foer 1971, og bunnen i 1999 til 2001
# leste A=53. Avkortet leser den 97.
# Maalt paa andelen maaneder der den NOMINELLE prisen staar helt stille, per
# tiaar. Over ca. 40 % betyr forhandlet kontraktspris eller forsvart kurs, ikke
# en notering. Tallene i parentes er den maalte andelen i tiaaret foer starten.
AVKORT = {
    "gold":      "1971-08",   # 66 % paa 60-tallet, konvertibel dollar til aug 1971
    "aluminium": "1980-01",   # 91 % / 24 %, LME-kontrakt fra 1978
    "nikkel":    "1980-01",   # 81 % / 80 %, LME-kontrakt fra 1979
    "te":        "1980-01",   # 91 % paa 60-tallet
    "kakao":     "1980-01",   # 55 % paa 70-tallet, den internasjonale kakaoavtalen
    "urea":      "2000-01",   # 95/66/41/31 %, kontraktspris til rundt 2000
    "ttf":       "2000-01",   # 95/92/93/26 %, oljeindeksert kontrakt
    "kull":      "2000-01",   # 89/77/57 %, aarlige kontraktspriser
    "jernmalm":  "2010-01",   # 93/94/93/92/57 %, forhandlet referansepris til 2010
}

# Mekanisme for serier som er for administrerte til at A betyr noe, men som
# likevel skal staa synlig med pris og graf. Settet er tomt naa. Kalium sto her
# fram til 2026-09-22: den sto 71 % stille selv paa 2010-tallet, bare
# 2020-tallet var en markedspris, og seks aar er ikke en fordeling. Da den
# heller ikke hadde et maalt instrument i IKZ-universet, ble hele segmentet
# tatt ut i stedet for aa staa som en pris uten skaar og uten papir.
UTEN_A = set()

M = ("Serien er avkortet fordi prisen foer dette var forhandlet eller fastsatt "
     "og ikke satt i et marked. En fast pris opptar de billigste persentilene "
     "permanent, og da kan ingenting etterpaa lese billig.")
AVKORT_MERKNAD = {
    "gold": ("Serien starter i august 1971, da gullvinduet ble lukket. Før det "
             "var dollaren konvertibel til en forsvart kurs, og prisen står "
             "uendret i ni av ti måneder. Det er ikke en markedspris."),
    "aluminium": M + " Aluminium fikk LME-kontrakt i 1978.",
    "nikkel":    M + " Nikkel fikk LME-kontrakt i 1979.",
    "te":        M + " Te sto 91 % stille på 1960-tallet.",
    "kakao":     M + " Den internasjonale kakaoavtalen styrte prisen på 1970-tallet.",
    "urea":      M + " Urea var kontraktspris fram til rundt 2000.",
    "ttf":       M + " Europeisk gass var oljeindeksert kontrakt fram til 1990-tallet.",
    "kull":      M + " Australsk kull hadde årlige kontraktspriser.",
    "jernmalm":  M + " Jernmalm hadde årlig forhandlet referansepris fram til 2010.",
}

for sid, navn, grp, enhet, sti, mnd in MIRRORS:
    try:
        serie = csv_series(MIRROR + sti, monthly=mnd)
        if sid in AVKORT:
            foer = len(serie)
            serie = serie.loc[AVKORT[sid]:]
            assert len(serie) >= MIN_HIST, f"{sid}: bare {len(serie)} mnd igjen etter avkorting"
            note(f"avkorting {sid}", True,
                 f"{foer} -> {len(serie)} mnd, starter {AVKORT[sid]}")
        legg_til(sid, navn, grp, enhet, serie, cpi,
                 "EIA/LBMA via datasets-speil", MIRROR + sti,
                 merknad=AVKORT_MERKNAD.get(sid))
    except Exception as e:
        note(f"speil {sid}", False, f"{type(e).__name__}: {str(e)[:70]}")

print("\n2b. Uran")
# Kilden er Camecos maanedsslutt spot fra 1988, kontrollert mot to uavhengige
# kopier hver uke. IMF-serien i uran_reserve.csv har et brudd fra oktober 2021
# og ligger rundt 19 % for lavt etter det, saa den brukes bare som kontroll.
# Se uran_kilde.py for tallene.
#
# Ingen avkorting. Stillstandstesten ga 15 % paa 1990-tallet, 4 % paa
# 2000-tallet og 0 % etter, godt under terskelen paa rundt 40 % som utloste
# avkorting for de ni seriene i AVKORT.
URAN_MERKNAD = (
    "Spotpris i USD per pund U3O8, månedsslutt, snittet av UxC og TradeTech slik "
    "Cameco publiserer det, historikk fra 1988. Det meste av uranet selges på "
    "langsiktige kontrakter, så spot er et tynt marked som forsterker syklusen i "
    "begge retninger.")
try:
    from uran_kilde import hent_uran, CAMECO
    serie, kilde = hent_uran(f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/", note)
    if serie is None:
        note("uran", False, kilde + ". Segmentet er utelatt denne uken")
    else:
        legg_til("uran", "Uran", "Energi", "USD/lb", serie, cpi,
                 "Cameco (UxC og TradeTech), månedsslutt", CAMECO, merknad=URAN_MERKNAD)
        if GITHUB_TOKEN:
            try:
                push("uran_cameco.csv", "dato,spot\n" + "\n".join(
                    f"{p}-01,{v}" for p, v in serie.items()) + "\n")
            except Exception as e:
                note("push uran_cameco.csv", False, str(e)[:60])
        alder = (pd.Period(pd.Timestamp.now(), freq="M") - serie.index[-1]).n
        if alder > 2:
            note("uran, alder", False, f"siste obs {serie.index[-1]}, {alder} mnd gammel")
except Exception as e:
    note("uran", False, f"{type(e).__name__}: {str(e)[:70]}")

print("\n2c. Laks")
# Observasjonspanel uten flagg. Se laks_innhent.py for kilder og regnestykke,
# som er det samme som i laksesonden 25.09.2026. Marginen mot produksjons-
# kostnaden ga ingen informasjon om papirene (rho 0,108, p 0,353), saa laks
# har ikke bunnsone og ikke oppsikt, bare tallene.
LAKS = None
LAKS_MERKNAD = (
    "Observasjon, ikke flagg. Eksportpris for fersk oppalen laks fra SSB, uke for uke, "
    "snittet per måned og sesongjustert, omregnet til dollar. Sesongen er stor (rundt 27 % "
    "fra topp til bunn), så rå pris ville gitt falske bunner hver høst. Marginen er "
    "sesongjustert kilopris i kroner delt på Fiskeridirektoratets produksjonskostnad per kilo. "
    "Laksesonden fant at verken marginen eller prisnivået sa noe om papirene 24 måneder fram.")
try:
    import laks_innhent
    def _les_raw(sti):
        r = requests.get(f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/{sti}",
                         params={"cb": int(time.time())}, headers=UA, timeout=30)
        return r.text if r.status_code == 200 else None
    LAKS = laks_innhent.hent(get, yahoo_monthly, les=_les_raw, note=note)
    legg_til("laks", "Laks (sesongjustert)", "Sjømat", "USD/kg", LAKS["usd_just"], cpi,
             "SSB tabell 03024, Norges Bank, Fiskeridirektoratet",
             "https://www.ssb.no/statbank/table/03024", merknad=LAKS_MERKNAD)
    if SEGMENTS and SEGMENTS[-1]["id"] == "laks":
        laks_innhent.berik(SEGMENTS[-1], LAKS, expanding_pct)
        lk = SEGMENTS[-1]["laks"]
        note("laks", True, f"margin {lk['margin']} (A {lk['A_margin']}), kostnad {lk['kost_siste_aar']} "
                           f"{lk['kost_siste']} kr/kg{'' if lk['kost_fersk'] else ' GAMMEL'}, uke {lk['uke']} "
                           f"{lk['uke_nok_kg']} kr/kg")
        if GITHUB_TOKEN and not str(LAKS["kost_kilde"]).startswith("forrige"):
            try:
                push("laks_kost.json", json.dumps({"hentet": str(pd.Timestamp.utcnow())[:10],
                     "kilde": LAKS["kost_kilde"], "ny": {str(a): v for a, v in LAKS["kost_ny"].items()}}))
            except Exception as e:
                note("push laks_kost.json", False, str(e)[:60])
except Exception as e:
    note("laks", False, f"{type(e).__name__}: {str(e)[:70]}")

print("\n3. Metall, innsatsfaktorer og flerårige fra Pink Sheet")
FLERAARIG_MERKNAD = (
    "Flerårig vekst. Tre til sju år fra planting til full bæring, så tilbudet "
    "reagerer over år og ikke over en sesong. Realprisen har likevel en "
    "produktivitetstrend nedover, så persentilen overdriver hvor billig den er."
)

# Ni segmenter er tatt ut 2026-09-22: urea, fiskemel, kaffe arabica, kaffe
# robusta, gummi RSS3, gummi TSR20, kokosolje, te og kalium. De aatte forste
# fordi ingen av dem hadde et instrument i IKZ-universet med maanedskorrelasjon
# over 0,30 mot sin egen raavare. Oppdretterne laa paa 0,07 mot fiskemel og
# Nutrien paa 0,05 mot urea. Kalium i tillegg fordi prisen er administrert i
# hele historikken og segmentet derfor aldri fikk noen prisnivaaskaar.
# Et segment uten et papir som folger det er en pris paa en skjerm, ikke en
# beslutning. Seriene finnes fortsatt i Pink Sheet og kan hentes inn igjen ved
# aa legge linjen tilbake.
PINK = [
    ("kobber", "Kobber", "Metall", "USD/tonn", "Copper"),
    ("nikkel", "Nikkel", "Metall", "USD/tonn", "Nickel"),
    ("aluminium", "Aluminium", "Metall", "USD/tonn", "Aluminum"),
    ("sink", "Sink", "Metall", "USD/tonn", "Zinc"),
    ("bly", "Bly", "Metall", "USD/tonn", "Lead"),
    ("tinn", "Tinn", "Metall", "USD/tonn", "Tin"),
    ("jernmalm", "Jernmalm 62% Fe", "Metall", "USD/tonn", "Iron ore"),
    ("kull", "Termisk kull (Australia)", "Metall", "USD/tonn", "Coal, Australian"),
    ("ttf", "Naturgass Europa", "Energi", "USD/mmbtu", "Natural gas, Europe"),
    # Tremasse er tatt ut: Verdensbanken har fjernet woodpulp fra Pink Sheet.
    # Flerårige vekster. Tre til sju år fra planting til full bæring, så
    # tilbudssiden er et kapitalapparat og ikke en årlig såing.
    ("kakao", "Kakao", "Flerårige", "USD/kg", "Cocoa"),
    ("palmeolje", "Palmeolje", "Flerårige", "USD/tonn", "Palm oil"),
]
try:
    ps = pink_sheet()
    norm = lambda x: re.sub(r"[^a-z0-9]", "", str(x).lower())
    kol = {norm(c): c for c in ps.columns}
    print("   kolonner i arket:", ", ".join(sorted(str(c).strip() for c in ps.columns)))
    for sid, navn, grp, enhet, nokkel in PINK:
        # Eksakt treff først. Ren delstrengmatching er rekkefølgeavhengig:
        # "Tin" ligger inni "Platinum", og hva som blir valgt avhenger av
        # kolonnerekkefølgen i arket. Det skal ikke avgjøre hva vi måler.
        eksakt = [v for k, v in kol.items() if k == norm(nokkel)]
        delvis = [v for k, v in kol.items() if norm(nokkel) in k]
        treff = eksakt or delvis
        if not treff:
            note(f"Pink Sheet {navn}", False, f"ingen kolonne som ligner '{nokkel}'")
            continue
        if not eksakt and len(delvis) > 1:
            note(f"Pink Sheet {navn}", False,
                 f"tvetydig: '{nokkel}' passer på {delvis}, valgte '{delvis[0]}'")
        serie = ps[treff[0]].dropna()
        if sid in AVKORT:
            foer = len(serie)
            serie = serie.loc[AVKORT[sid]:]
            assert len(serie) >= MIN_HIST, f"{sid}: bare {len(serie)} mnd etter avkorting"
            note(f"avkorting {sid}", True,
                 f"{foer} -> {len(serie)} mnd, starter {AVKORT[sid]}")
        legg_til(sid, navn, grp, enhet, serie, cpi,
                 f"Verdensbanken Pink Sheet: {treff[0]}",
                 "https://www.worldbank.org/en/research/commodity-markets",
                 merknad=AVKORT_MERKNAD.get(sid,
                         FLERAARIG_MERKNAD if grp == "Flerårige" else None))
except Exception as e:
    note("Verdensbanken Pink Sheet", False, f"{type(e).__name__}: {str(e)[:90]}")

print("\n4. Magasinfylling (egen indikator, ikke pris)")
indicators = {}
try:
    for omr, s in nve_magasin().items():
        indicators[f"magasin_{omr.lower()}"] = {
            "navn": f"Magasinfylling {omr}", "enhet": "prosent",
            "kilde": "NVE magasinstatistikk",
            "t": [str(p) for p in s.index[-CHART_MONTHS:]],
            "v": [round(float(v), 2) for v in s.values[-CHART_MONTHS:]]}
    note("NVE magasinstatistikk", True, f"{len(indicators)} prisområder")
except Exception as e:
    note("NVE magasinstatistikk", False, f"{type(e).__name__}: {str(e)[:70]}")

print("\n5. Vehikkellaget (aksjekurser)")
VEHICLES = {"brent": ["AKRBP.OL", "VAR.OL", "DNO.OL"], "kobber": ["FCX"],
            "aluminium": ["NHY.OL"], "urea": ["YAR.OL"],
            "laks": ["MOWI.OL", "SALM.OL", "LSG.OL"],
            "vlcc": ["FRO.OL", "DHT", "INSW"],
            "torrlast": ["SBLK", "HSHP.OL", "CMBT", "2020.OL"],
            "floater": ["RIG", "VAL", "NE"], "nikkel": ["IGO.AX", "NIC.AX"],
            "vlgc": ["BWLPG.OL"], "ttf": ["EQNR.OL"]}
vehicle_px, dode = {}, []
for seg, syms in VEHICLES.items():
    for sym in syms:
        try:
            ser = yahoo_monthly(sym)
            vehicle_px[sym] = {"seg": seg, "t": [str(p) for p in ser.index],
                               "px": [round(float(v), 4) for v in ser.values]}
            time.sleep(0.3)
        except Exception as e:
            dode.append(sym)
if dode:
    note("Yahoo, symbol uten treff", False, ", ".join(dode))
note("Yahoo totalt", len(vehicle_px) > 0, f"{len(vehicle_px)} av "
     f"{sum(len(v) for v in VEHICLES.values())} symbol, "
     f"{len(set(v['seg'] for v in vehicle_px.values()))} segment dekket")


# --------------------------------------------- berik segmentene for dashbordet
# Repofilene skal vaere komplette, slik at den planlagte oppgaven som skriver
# til dashbordets database bare kopierer og ikke maa flette. Hver gang noe maa
# flettes manuelt, er det et sted en feil kan gjemme seg.

print("\n6. Beriker segmentene: instrumenter, etterspoersel, tilbudsskaar")

try:
    from instrumenter import INSTR
    n = 0
    for s in SEGMENTS:
        rader = INSTR.get(s["id"])
        if not rader:
            continue
        s["instrumenter"] = [
            {"ticker": tk, "bors": bors, "navn": navn, "type": typ,
             "kommentar": kom.lstrip("-").strip(),
             "omvendt": kom.strip().startswith("-"),
             "handlbar": bors in {"Oslo", "Stockholm", "København", "Helsinki",
                                  "London", "Xetra", "Amsterdam", "Paris",
                                  "Zurich", "NYSE", "Nasdaq", "Toronto"}}
            for tk, bors, navn, typ, kom in rader]
        n += 1
    note("instrumenter", True, f"{n} av {len(SEGMENTS)} segment fikk instrumentliste")
except Exception as e:
    note("instrumenter", False, f"{type(e).__name__}: {str(e)[:70]}")

try:
    o = pd.read_csv("https://raw.githubusercontent.com/owid/energy-data/master/"
                    "owid-energy-data.csv", low_memory=False)
    w = o[o.country == "World"].set_index("year")
    def vekst(x, k):
        y = np.log(x.iloc[-k:].values)
        return None if len(y) < k else round(float(
            100 * (np.exp(np.polyfit(np.arange(len(y)), y, 1)[0]) - 1)), 2)
    # Femaarsvinduet er utelatt: 2020 gjor det til en maaling av gjeninnhentingen.
    BAERER = {"oil_consumption": ("Olje", ["brent", "wti"]),
              "gas_consumption": ("Gass", ["henryhub", "ttf"]),
              "coal_consumption": ("Kull", ["kull"]),
              "nuclear_consumption": ("Kjernekraft", ["uran"])}
    kart = {}
    for kol, (navn, segs) in BAERER.items():
        x = w[kol].dropna()
        e = {"baerer": navn, "vekst10": vekst(x, 10), "vekst20": vekst(x, 20),
             "vekst30": vekst(x, 30), "siste_aar": int(x.index[-1]),
             "topp_aar": int(x.idxmax()),
             "under_topp_pst": round(float(100 * (x.iloc[-1] / x.max() - 1)), 1),
             "kilde": "Our World in Data, Energy dataset"}
        for sid in segs:
            kart[sid] = e
    n = 0
    for s in SEGMENTS:
        if s["id"] in kart:
            s["ettersp"] = kart[s["id"]]; n += 1
    note("OWID etterspoersel", True,
         f"{n} segment, siste aar {kart['brent']['siste_aar']}")
except Exception as e:
    note("OWID etterspoersel", False, f"{type(e).__name__}: {str(e)[:70]}")

try:
    kap = get(f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/d_kapitulasjon.json"
              f"?cb={int(time.time())}").json()
    segd = kap.get("segmenter", {})
    papir = kap.get("papirer", {})
    n = 0
    for s in SEGMENTS:
        g = segd.get(s["id"])
        if not g or g.get("D") is None:
            continue
        s["scores"]["D"] = g["D"]
        s["d_detalj"] = {k: g.get(k) for k in ("D_aksjer", "tema", "tema_D", "spredning", "n")}
        for i in s.get("instrumenter", []):
            d = papir.get(i["ticker"])
            if d:
                i["D"] = d["D"]
                i["fall_pst"] = d["fall_pst"]
        n += 1
    note("kapitulasjon D", True, f"{n} segment")
except Exception as e:
    note("kapitulasjon D", False, f"{type(e).__name__}: {str(e)[:70]}")

try:
    c = get(f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/c_overlevelse.json"
            f"?cb={int(time.time())}").json()
    segporter = c.get("segmenter", {})
    selskap = c.get("selskaper", {})
    n = 0
    # Porten regnes ut paa nytt av de instrumentene som staar paa bordet NAA,
    # ikke av det c_overlevelse.json en gang maalte.
    #
    # Dette er ikke pirk. 22. september ble instrumentlisten byttet ut etter
    # sonden, mens C stammet fra forrige kvartalskjoring. Ni av femten
    # segmenter viste da en port som beskrev selskaper som ikke lenger sto
    # oppfoert: gull leste "aapen" av Agnico og Newmont mens bordet viste tre
    # gruve-ETF-er. En port som beskriver noen andre er verre enn ingen port.
    stale = 0
    for s in SEGMENTS:
        g = segporter.get(s["id"]) or {}
        maalt = {i["ticker"]: i for i in g.get("instrumenter", [])}
        egne = [maalt[i["ticker"]] for i in s.get("instrumenter", [])
                if i["ticker"] in maalt]
        if not egne:
            # Skill mellom "vi mangler tall" og "det finnes ingen tall aa ha".
            # Gull har tre UCITS-fond som instrumenter, og et fond har ingen
            # balanse. Porten der er ikke ukjent, den er uaktuell, og "ukjent"
            # antyder feilaktig at den kan fylles en dag.
            maalbare = [i for i in s.get("instrumenter", [])
                        if not str(i.get("type", "")).lower().startswith(("etf", "etc", "etn", "fond"))]
            # Et segment uten noen instrumenter (uran, til sonden har maalt dem)
            # er ukjent, ikke uaktuell: det er ikke fond, det er ingenting ennaa.
            gate = "ukjent" if (maalbare or not s.get("instrumenter")) else "uaktuell"
            if g.get("gate") not in (None, "ukjent"):
                stale += 1
        elif any(x["port"] == "aapen" for x in egne): gate = "aapen"
        elif any(x["port"] == "trang" for x in egne): gate = "trang"
        else:                                         gate = "stengt"
        s["scores"]["gate"] = gate
        s["gate_detalj"] = {"aapne": sum(1 for x in egne if x["port"] == "aapen"),
                            "malte": len(egne)}
        for i in s.get("instrumenter", []):
            d = maalt.get(i["ticker"])
            if d:
                i["port"] = d["port"]
                i["kvartaler"] = d.get("kvartaler")
                sk = selskap.get(i["ticker"], {})
                i["bunnaar"] = sk.get("bunnaar")
                i["aar_historikk"] = sk.get("aar_historikk")
            else:
                for k in ("port", "kvartaler", "bunnaar", "aar_historikk"):
                    i.pop(k, None)
        n += 1
    aapne = sum(1 for s in SEGMENTS if s["scores"]["gate"] == "aapen")
    note("overlevelsesport C", True, f"{n} segment, {aapne} aapne"
         + (f", {stale} mistet porten fordi C ikke er kjort for dagens papirer"
            if stale else ""))
except Exception as e:
    note("overlevelsesport C", False, f"{type(e).__name__}: {str(e)[:70]}")

try:
    b = get(f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/b_capex.json"
            f"?cb={int(time.time())}").json()
    # b_capex.json bruker metallnavn, segmentene bruker id. De er ikke alltid
    # de samme: gull heter "gold" som segment. Uten denne oversettelsen ville
    # gull mistet tilbudsskaaren sin stille.
    ID = {"gull": "gold"}
    kart = {ID.get(k, k): v for k, v in b.get("metaller", {}).items()}
    uten = [k for k in kart if k not in {x["id"] for x in SEGMENTS}]
    if uten:
        note("tilbudsskaar B", False,
             f"maalt for {', '.join(uten)}, men de finnes ikke som segment")
    n = 0
    for s in SEGMENTS:
        d = kart.get(s["id"])
        if not d:
            continue
        s["scores"]["B1"] = d.get("B1_siste")
        s["scores"]["B2"] = d.get("B2_siste")
        s["scores"]["B"] = d.get("B2_siste")
        n += 1
    note("tilbudsskaar B", True, f"{n} segment fra b_capex.json")
except Exception as e:
    note("tilbudsskaar B", False, f"{type(e).__name__}: {str(e)[:70]}")

# Kontekstfeltene over grafen. Se signaler.py for hvorfor de ligger her.
try:
    from signaler import trend, cot_for_segmenter
    n = 0
    for s in SEGMENTS:
        t = trend(s["series"])
        if t:
            s["trend"] = t; n += 1
    note("trendbekreftelse", True, f"{n} segment")
    cot = cot_for_segmenter(note)
    for s in SEGMENTS:
        if s["id"] in cot:
            s["cot"] = cot[s["id"]]
    note("COT totalt", len(cot) > 0, f"{len(cot)} av 6 kontrakter")
except Exception as e:
    note("signaler", False, f"{type(e).__name__}: {str(e)[:70]}")

# Terminkurven tolv maaneder fram, med historikk som bygges uke for uke.
# Se kurve_innhent.py. Historikken leses via API-et (ikke en mellomlagret
# kopi), og skrives bare naar innhentingen har tilgang til repoet.
try:
    import kurve_innhent
    def _les_api(sti):
        if not GITHUB_TOKEN:
            return None
        r = requests.get(f"https://api.github.com/repos/{REPO}/contents/{sti}",
                         params={"ref": BRANCH}, timeout=30,
                         headers={"Authorization": f"Bearer {GITHUB_TOKEN}",
                                  "Accept": "application/vnd.github.raw"})
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.text
    kurve_innhent.oppdater(SEGMENTS, _les_api,
                           (lambda sti, tekst: push(sti, tekst)) if GITHUB_TOKEN else (lambda sti, tekst: None),
                           note)
except Exception as e:
    note("kurveform", False, f"{type(e).__name__}: {str(e)[:70]}")

# VIX, uroen i det amerikanske aksjemarkedet. Ett felt oeverst paa bordet,
# felles for alle segmenter, som kontekst. Ikke testet som signal.
# Persentilen er dagens siste dagskurs mot alle maanedsslutter siden 1990,
# og mot siste ti aar. Skrives til marked.json, som onsdagsoppgaven kopierer
# til dashbordets database (samlingen "marked", dokument "vix").
MARKED = None
try:
    r = get(f"https://query1.finance.yahoo.com/v8/finance/chart/%5EVIX?period1=0"
            f"&period2={int(time.time())}&interval=1mo", timeout=40).json()["chart"]["result"][0]
    idx = pd.to_datetime(r["timestamp"], unit="s", utc=True).tz_convert("America/New_York").to_period("M")
    mnd = pd.Series(r["indicators"]["quote"][0]["close"], index=idx).dropna()
    mnd = mnd[~mnd.index.duplicated(keep="last")]
    d = get("https://query1.finance.yahoo.com/v8/finance/chart/%5EVIX?range=10d&interval=1d",
            timeout=30).json()["chart"]["result"][0]
    par = [(t, v) for t, v in zip(d["timestamp"], d["indicators"]["quote"][0]["close"]) if v is not None]
    t_siste, v_siste = par[-1]
    dato = pd.Timestamp(t_siste, unit="s", tz="UTC").tz_convert("America/New_York").strftime("%Y-%m-%d")
    hist = mnd[mnd.index < pd.Period(dato[:7], "M")]          # hele maaneder foer i dag
    ti = hist[hist.index >= hist.index[-1] - 119]
    pct = lambda s, x: round(float(100 * (s <= x).mean()), 1)
    MARKED = {"id": "vix", "navn": "VIX", "t": dato, "verdi": round(float(v_siste), 2),
              "pctl_alle": pct(hist, v_siste), "pctl_10aar": pct(ti, v_siste),
              "fra": str(hist.index[0]), "median": round(float(hist.median()), 2),
              "maks": round(float(hist.max()), 2), "maks_t": str(hist.idxmax()),
              "serie": [[str(p), round(float(v), 2)] for p, v in mnd.iloc[-180:].items()],
              "kilde": "Cboe VIX via Yahoo (^VIX)", "merknad": "Kontekst, ikke testet som signal."}
    note("VIX", True, f"{MARKED['verdi']} per {dato}, persentil {MARKED['pctl_alle']} "
                      f"(fra {MARKED['fra']}) / {MARKED['pctl_10aar']} (10 aar)")
except Exception as e:
    note("VIX", False, f"{type(e).__name__}: {str(e)[:70]}")

print("\n" + "=" * 70)
print(f"{len(SEGMENTS)} segment bygget, {len(indicators)} indikatorer, "
      f"{len(vehicle_px)} kursserier")
fl = [s["id"] for s in SEGMENTS if s["scores"].get("flagg")]
op = [s["id"] for s in SEGMENTS if s["scores"].get("oppsikt")]
print(f"Bunnsone (raa og detrendet over 80): {', '.join(fl) or 'ingen'}")
print(f"Under oppsikt (bare raa over 80):    {', '.join(op) or 'ingen'}")

if GITHUB_TOKEN and SEGMENTS:
    feil = 0
    for s in SEGMENTS:
        try:
            push(f"segments/{s['id']}.json", json.dumps(s, ensure_ascii=False))
        except Exception as e:
            feil += 1
            note(f"push {s['id']}", False, str(e)[:70])
    if cpi_kilde and not cpi_kilde.startswith("forrige"):
        try:
            push("cpi_kopi.csv", "mnd,kpi\n" + "\n".join(f"{p},{v}" for p, v in cpi.items()) + "\n")
        except Exception as e:
            note("push cpi_kopi.csv", False, str(e)[:60])
    if MARKED:
        try:
            push("marked.json", json.dumps(MARKED, ensure_ascii=False))
        except Exception as e:
            note("push marked.json", False, str(e)[:70])
    for navn, obj in [("indicators.json", indicators), ("vehicles.json", vehicle_px)]:
        try:
            push(navn, json.dumps(obj, ensure_ascii=False))
        except Exception as e:
            note(f"push {navn}", False, str(e)[:70])
    # Loggen over flagg og tenkte handler framover. Se flagglogg.py.
    # Leses via API-et og ikke raw.githubusercontent, som kan servere en
    # mellomlagret eldre kopi, og da ville forrige ukes linjer blitt skrevet
    # over. Svarer API-et med noe annet enn 200 eller 404, skrives ingenting.
    try:
        import flagglogg
        def _les_logg(sti):
            r = requests.get(f"https://api.github.com/repos/{REPO}/contents/{sti}",
                             params={"ref": BRANCH}, timeout=30,
                             headers={"Authorization": f"Bearer {GITHUB_TOKEN}",
                                      "Accept": "application/vnd.github.raw"})
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r.text
        flagglogg.oppdater(SEGMENTS, _les_logg, push, note)
    except Exception as e:
        note("flagglogg", False, f"{type(e).__name__}: {str(e)[:70]}")
    try:
        push("index.json", json.dumps(
            {"oppdatert": str(pd.Timestamp.utcnow())[:19],
             "segmenter": [s["id"] for s in SEGMENTS], "logg": LOG},
            ensure_ascii=False, indent=1))
        print(f"Publisert til https://github.com/{REPO}"
              + (f" ({feil} segment feilet)" if feil else ""))
    except Exception as e:
        print(f"index.json feilet: {str(e)[:90]}")
elif not GITHUB_TOKEN:
    print("\nGITHUB_TOKEN mangler, så ingenting ble publisert.\n"
          "Nøkkelikonet i venstre marg: legg inn hemmeligheten GITHUB_TOKEN\n"
          "(classic PAT med scope repo) og skru på tilgang for denne notatboken.")

print("\nDEKNINGSTABELL (send denne til Claude)")
print(pd.DataFrame(LOG).to_string(index=False))
