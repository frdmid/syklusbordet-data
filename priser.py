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
                     "flagg": bool(flagg[i]), "oppsikt": bool(oppsikt[i])})

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
cpi = None
for navn, fn in [("GitHub-speil cpi-us", lambda: csv_series(MIRROR + "cpi-us/main/data/cpiai.csv")),
                 ("FRED CPIAUCSL", lambda: fred("CPIAUCSL"))]:
    try:
        cpi = fn()
        note(navn, True, f"siste {cpi.index[-1]}")
        break
    except Exception as e:
        note(navn, False, f"{type(e).__name__}: {str(e)[:70]}")
if cpi is None:
    raise SystemExit("Ingen deflator tilgjengelig. Alt annet er meningsløst uten. "
                     "Send loggen over til Claude.")

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

# Kalium er et eget tilfelle. Den staar 71 % stille selv paa 2010-tallet, og
# bare 2020-tallet er en markedspris. Seks aar er ikke en fordeling, saa A
# beregnes ikke i det hele tatt. Segmentet staar synlig med pris og graf.
UTEN_A = {"kalium"}

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
    "kalium":    ("Prisnivåskåren er ikke beregnet. Kalium var kontraktspris i hele "
                  "historikken og står 71 % stille selv på 2010-tallet. Bare 2020-tallet "
                  "er en markedspris, og seks år er ikke nok til en fordeling."),
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

print("\n3. Metall, innsatsfaktorer og flerårige fra Pink Sheet")
FLERAARIG_MERKNAD = (
    "Flerårig vekst. Tre til sju år fra planting til full bæring, så tilbudet "
    "reagerer over år og ikke over en sesong. Realprisen har likevel en "
    "produktivitetstrend nedover, så persentilen overdriver hvor billig den er."
)

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
    ("urea", "Urea", "Nordisk", "USD/tonn", "Urea"),
    ("kalium", "Kalium", "Nordisk", "USD/tonn", "Potassium chloride"),
    ("fiskemel", "Fiskemel", "Nordisk", "USD/tonn", "Fish meal"),
    # Tremasse er tatt ut: Verdensbanken har fjernet woodpulp fra Pink Sheet.
    # Flerårige vekster. Tre til sju år fra planting til full bæring, så
    # tilbudssiden er et kapitalapparat og ikke en årlig såing.
    ("kakao", "Kakao", "Flerårige", "USD/kg", "Cocoa"),
    ("kaffe_arabica", "Kaffe arabica", "Flerårige", "USD/kg", "Coffee, Arabica"),
    ("kaffe_robusta", "Kaffe robusta", "Flerårige", "USD/kg", "Coffee, Robusta"),
    ("palmeolje", "Palmeolje", "Flerårige", "USD/tonn", "Palm oil"),
    ("gummi_rss3", "Gummi (RSS3)", "Flerårige", "USD/kg", "Rubber, RSS3"),
    ("gummi_tsr20", "Gummi (TSR20)", "Flerårige", "USD/kg", "Rubber, TSR20"),
    ("kokosolje", "Kokosolje", "Flerårige", "USD/tonn", "Coconut oil"),
    ("te", "Te", "Flerårige", "USD/kg", "Tea, avg 3 auctions"),
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
             "handlbar": bors in {"Oslo", "Stockholm", "København", "London",
                                  "NYSE", "Nasdaq", "Toronto", "TSX Venture"}}
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
    for s in SEGMENTS:
        g = segporter.get(s["id"])
        if not g:
            continue
        s["scores"]["gate"] = g["gate"]
        s["gate_detalj"] = {"aapne": g["aapne"], "malte": g["malte"]}
        # port per instrument, slik at raden viser hvem som baerer den
        port = {i["ticker"]: i for i in g.get("instrumenter", [])}
        for i in s.get("instrumenter", []):
            d = port.get(i["ticker"])
            if d:
                i["port"] = d["port"]
                i["kvartaler"] = d.get("kvartaler")
                sk = selskap.get(i["ticker"], {})
                i["bunnaar"] = sk.get("bunnaar")
                i["aar_historikk"] = sk.get("aar_historikk")
        n += 1
    note("overlevelsesport C", True,
         f"{n} segment, {sum(1 for x in segporter.values() if x['gate']=='aapen')} aapne")
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
    for navn, obj in [("indicators.json", indicators), ("vehicles.json", vehicle_px)]:
        try:
            push(navn, json.dumps(obj, ensure_ascii=False))
        except Exception as e:
            note(f"push {navn}", False, str(e)[:70])
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
