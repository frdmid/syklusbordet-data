# ---------------------------------------------------------------------------
# sonde_kjor_laks: kan laks bli et segment paa bordet
#
# Metodikken er godkjent av Frode 24. september 2026 og staar i
# metodikkdokumentet under "Forslag til godkjenning: laks". Sonden endrer
# ingenting paa dashbordet. Den maaler kriteriene K1 til K5 og kjoerer
# terskeltesten for marginen, og lagrer maanedsserien i sonder/laks.csv.
#
# Valg som ikke sto eksplisitt i forslaget, og som er gjort her FOER maaling:
#   - Utfallet terskelvalget styres etter er avkastningen i den likt vektede
#     kurven av laksepapirer 24 maaneder etter, fordi det er papirene som
#     kjoepes. Endringen i sesongjustert realpris rapporteres ved siden av.
#   - Sesongfaktorene regnes paa log pris i kroner og brukes paa begge
#     seriene. Valuta har ikke sesong, saa faktorene er de samme.
#   - Kostnaden for aar Y regnes kjent fra desember aar Y+1, fordi
#     publiseringsmaaneden ikke staar i dataene. Rapporten kommer normalt
#     om hoesten, saa dette er paa den forsiktige siden.
#   - For 1,0, som staar ytterst i sin familie, kreves bare at naboen 1,1
#     gir positivt utfall i plataatesten.
#   - Valutakurs: Norges Bank sitt maanedssnitt USD/NOK for prisen, Yahoo
#     maanedsslutt for aksjene (samme som resten av bordet).
#
# To rettelser av det godkjente forslaget, begge funnet i proevekjoring paa
# simulerte data FOER sonden ble kjoert paa ekte data:
#   - Sesongfaktorene maales mot et sentrert 12-maaneders snitt fra data til og
#     med juni aaret foer, ikke mot aarssnittet. Aarssnittet tok med trenden og
#     lot sesong staa igjen. Se sesongfaktorer().
#   - Trinn 1 bruker blokkbootstrap av utfallet som null, ikke forskyvning av
#     marginserien. Forskyvningen ga 12 og 35 % falske funn der 5 % er riktig.
#     Ny null: 5,8 og 4,2 % paa 240 simuleringer. Se trinn1_kurv().
# ---------------------------------------------------------------------------

import ast, datetime as dt, io, json, math, os, re, time, warnings
import numpy as np
import pandas as pd
import requests

warnings.filterwarnings("ignore")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
MIRROR = "https://raw.githubusercontent.com/datasets/"
FIKS = pd.Period("2016-01", "M")
NF_MIN = 72
TERSKEL_R = 0.30
SES_MIN_AAR, SES_VINDU = 5, 10
PAUSE = 12
rng = np.random.default_rng(20260924)
RES = {"kriterier": {}}


def get(url, **kw):
    h = kw.pop("headers", UA)
    for i in range(3):
        try:
            r = requests.get(url, headers=h, timeout=kw.pop("timeout", 45), **kw)
            if r.status_code in (429, 502, 503):
                time.sleep(4 * (i + 1)); continue
            return r
        except requests.RequestException:
            if i == 2:
                raise
            time.sleep(2 * (i + 1))
    raise RuntimeError("ga opp")


def last_fra(fil, navn):
    t = ast.parse(open(fil, encoding="utf-8").read())
    kropp = [n for n in t.body if isinstance(n, ast.FunctionDef) and n.name in navn]
    ns = {"np": np, "MIN_HIST": 60}
    exec(compile(ast.Module(body=kropp, type_ignores=[]), fil, "exec"), ns)
    return ns

P = last_fra("priser.py", {"expanding_pct", "expanding_pct_detrend"})
expanding_pct, expanding_pct_detrend = P["expanding_pct"], P["expanding_pct_detrend"]


# ------------------------------------------- F- og t-fordeling uten scipy
def _betacf(a, b, x):
    qab, qap, qam = a + b, a + 1, a - 1
    c, d = 1.0, 1 - qab * x / qap
    d = 1 / (d if abs(d) > 1e-30 else 1e-30); h = d
    for m in range(1, 400):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1 + aa * d; d = 1 / (d if abs(d) > 1e-30 else 1e-30)
        c = 1 + aa / c; c = c if abs(c) > 1e-30 else 1e-30; h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1 + aa * d; d = 1 / (d if abs(d) > 1e-30 else 1e-30)
        c = 1 + aa / c; c = c if abs(c) > 1e-30 else 1e-30
        dl = d * c; h *= dl
        if abs(dl - 1) < 1e-12:
            break
    return h

def betainc(a, b, x):
    if x <= 0: return 0.0
    if x >= 1: return 1.0
    lb = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    bt = math.exp(a * math.log(x) + b * math.log(1 - x) - lb)
    return bt * _betacf(a, b, x) / a if x < (a + 1) / (a + b + 2) else 1 - bt * _betacf(b, a, 1 - x) / b

def f_sf(F, d1, d2):
    """P(F > F_obs)."""
    return betainc(d2 / 2, d1 / 2, d2 / (d2 + d1 * F))


# ================================================================ K1: pris
print("K1. Prisserien fra SSB\n")
UKE = None
try:
    meta = get("https://data.ssb.no/api/v0/no/table/03024").json()
    print(f"   tabell 03024: {meta.get('title')}")
    var = {v["code"]: v for v in meta["variables"]}
    for c, v in var.items():
        print(f"      {c:14} {len(v['values']):5} verdier  "
              f"{', '.join(v['valueTexts'][:4])}{' ...' if len(v['values']) > 4 else ''}")
    tidkode = next(c for c, v in var.items() if v.get("time") or c.lower() == "tid")
    innh = next(c for c in var if c.lower().startswith("contents"))
    pris = [v for v, t in zip(var[innh]["values"], var[innh]["valueTexts"]) if "pris" in t.lower()]
    qry = [{"code": innh, "selection": {"filter": "item", "values": pris[:1]}}]
    for c, v in var.items():
        if c in (tidkode, innh):
            continue
        valg = [x for x, t in zip(v["values"], v["valueTexts"]) if "fersk" in t.lower()] or v["values"][:1]
        qry.append({"code": c, "selection": {"filter": "item", "values": valg[:1]}})
        print(f"   valgt {c}: {[t for x, t in zip(v['values'], v['valueTexts']) if x in valg[:1]]}")
    r = requests.post("https://data.ssb.no/api/v0/no/table/03024",
                      json={"query": qry, "response": {"format": "json-stat2"}}, headers=UA, timeout=60)
    js = r.json()
    tider = list(js["dimension"][tidkode]["category"]["index"].keys())
    verdi = js["value"]
    uke = []
    for tk, v in zip(tider, verdi):
        m = re.match(r"(\d{4})U(\d{2})", tk)
        if m and v is not None:
            y, w = int(m.group(1)), int(m.group(2))
            try:
                torsdag = dt.date.fromisocalendar(y, w, 4)
            except ValueError:
                continue
            uke.append((torsdag, float(v)))
    UKE = pd.Series(dict(uke)).sort_index()
    print(f"   {len(UKE)} uker, {UKE.index[0]} til {UKE.index[-1]}, siste {UKE.iloc[-1]:.2f} kr/kg")
except Exception as e:
    print(f"   FEIL {type(e).__name__}: {str(e)[:120]}")
    try:
        s = get("https://data.ssb.no/api/v0/no/table/?query=laks").json()
        print("   Tabeller med laks i SSB sitt API:")
        for x in s[:15]:
            print(f"      {x.get('id')}  {x.get('title')}")
    except Exception as e2:
        print(f"   sok feilet: {e2}")

if UKE is None or UKE.empty:
    RES["kriterier"]["K1"] = False
    print("\nK1 holder ikke. Ingen laks. Resten av sonden hoppes over.")
    os.makedirs("sonder", exist_ok=True)
    json.dump(RES, open("sonder/laks.json", "w"), ensure_ascii=False, indent=1, default=str)
    raise SystemExit(0)

NOK = UKE.groupby(pd.PeriodIndex(pd.to_datetime(UKE.index), freq="M")).mean()
NUKER = UKE.groupby(pd.PeriodIndex(pd.to_datetime(UKE.index), freq="M")).size()
k1 = NOK.index[0] <= pd.Period("2001-12", "M")
RES["kriterier"]["K1"] = bool(k1)
print(f"   maanedsserie {NOK.index[0]} til {NOK.index[-1]}. K1 (start senest 2001): {'HOLDER' if k1 else 'HOLDER IKKE'}")

# IMF som kontroll, hvis den svarer
print("\n   IMF-kontroll (PSALM)")
IMF = None
for url in ("https://api.imf.org/external/sdmx/2.1/data/IMF.RES,PCPS/W00.PSALM.USD.M",
            "https://api.imf.org/external/sdmx/2.1/data/IMF.RES,PCPS/W00.PSALM.USD.M?format=csv"):
    try:
        r = get(url, headers={**UA, "Accept": "application/vnd.sdmx.data+csv;version=1.0.0"})
        print(f"      HTTP {r.status_code} {len(r.content)} byte")
        if r.status_code == 200 and "OBS_VALUE" in r.text:
            d = pd.read_csv(io.StringIO(r.text))
            IMF = pd.Series(pd.to_numeric(d["OBS_VALUE"], errors="coerce").values,
                            index=pd.PeriodIndex(d["TIME_PERIOD"].astype(str).str.replace("M", "-"), freq="M")).dropna()
            break
    except Exception as e:
        print(f"      {type(e).__name__}")
if IMF is None or IMF.empty:
    print("      ingen data. Kontrollen kjoeres ikke, SSB staar alene.")


# ========================================================== valuta og KPI
print("\nValuta og deflator")
cpi = pd.read_csv(io.StringIO(get(MIRROR + "cpi-us/main/data/cpiai.csv").text)).iloc[:, :2]
cpi.columns = ["d", "v"]
cpi = pd.Series(cpi["v"].values, index=pd.PeriodIndex(pd.to_datetime(cpi["d"]), freq="M")).dropna()
cpi = cpi.reindex(pd.period_range(cpi.index[0], cpi.index[-1], freq="M")).ffill()
BASE = float(cpi.iloc[-1])
def realt(s):
    return s * BASE / cpi.reindex(s.index).fillna(BASE)

USDNOK = None
try:
    r = get("https://data.norges-bank.no/api/data/EXR/M.USD.NOK.SP?format=csv&startPeriod=1995&locale=en")
    d = pd.read_csv(io.StringIO(r.text), sep=None, engine="python")
    tk = next(c for c in d.columns if "TIME" in c.upper())
    vk = next(c for c in d.columns if "OBS_VALUE" in c.upper())
    USDNOK = pd.Series(pd.to_numeric(d[vk].astype(str).str.replace(",", "."), errors="coerce").values,
                       index=pd.PeriodIndex(d[tk].astype(str), freq="M")).dropna()
    print(f"   Norges Bank USD/NOK maanedssnitt: {USDNOK.index[0]} til {USDNOK.index[-1]}")
except Exception as e:
    print(f"   Norges Bank feilet: {type(e).__name__} {str(e)[:60]}")


def yahoo(sym):
    r = get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}"
            f"?period1=0&period2={int(time.time())}&interval=1mo&events=div%7Csplit&includeAdjustedClose=true").json()
    res = r["chart"]["result"][0]
    tz = (res.get("meta") or {}).get("exchangeTimezoneName") or "UTC"
    idx = pd.to_datetime(res["timestamp"], unit="s", utc=True).tz_convert(tz).to_period("M")
    adj = (res["indicators"].get("adjclose") or [{}])[0].get("adjclose") or res["indicators"]["quote"][0]["close"]
    s = pd.Series(adj, index=idx).dropna()
    s = s[s > 0]
    return s[~s.index.duplicated(keep="last")], (res.get("meta") or {}).get("currency")

NOKX, _ = yahoo("NOK=X")        # NOK per USD, maanedsslutt
if USDNOK is None:
    USDNOK = NOKX
    print("   bruker Yahoo NOK=X som reserve")

USD = (NOK / USDNOK.reindex(NOK.index)).dropna()
if IMF is not None and not IMF.empty:
    f = USD.index.intersection(IMF.index)
    avv = ((USD[f] / IMF[f] - 1).abs() * 100)
    print(f"   SSB mot IMF: {len(f)} mnd, median avvik {avv.median():.1f} %, korr {USD[f].corr(IMF[f]):.4f}")
    RES["imf_kontroll"] = {"mnd": len(f), "median_avvik": round(float(avv.median()), 2)}
REAL = realt(USD)


# =========================================================== K2: sesong
print("\nK2. Sesongjustering")
LN = np.log(NOK)

def sesongfaktorer(ln):
    """Faktor per kalendermaaned for hvert aar Y, bare fra data til og med
    desember Y-1.

    Avviket maales mot et sentrert 2x12 glidende snitt (kjernen i X-11), men
    bare for maaneder der snittet kan regnes med data fram til desember Y-1,
    altsaa til og med juni Y-1. Da ser faktoren for aar Y aldri inn i aar Y.

    To enklere varianter ble forkastet i proevekjoring paa simulerte data med
    kjent sesong, fordi K2-testen fant sesong igjen etter justering:
      avvik fra aarssnittet     tok med trenden innenfor aaret, og lagde et
                                hopp hvert nyttaar (F steg fra 8 til 11)
      avvik fra aarets linje    linjen spiste en del av selve sesongen, som
                                ikke er symmetrisk innenfor et kalenderaar
    """
    v = ln.values
    ma = pd.Series(v, index=ln.index).rolling(13, center=True).apply(
        lambda w: (0.5 * w[0] + w[1:12].sum() + 0.5 * w[12]) / 12, raw=True)
    dev = (ln - ma).dropna()
    fak = {}
    for y in sorted({p.year for p in ln.index}):
        sist = pd.Period(f"{y - 1}-06", "M")
        forst = pd.Period(f"{y - SES_VINDU}-01", "M")
        d = dev[(dev.index >= forst) & (dev.index <= sist)]
        per = d.groupby([p.month for p in d.index])
        if len(per) < 12 or per.size().min() < SES_MIN_AAR:
            continue
        f = per.mean()
        fak[y] = f - f.mean()
    ut = pd.Series([fak[p.year][p.month] if p.year in fak else np.nan for p in ln.index], index=ln.index)
    return ut, fak

FAK, FAK_AAR = sesongfaktorer(LN)
JUST_NOK = (LN - FAK).dropna()
JUST_REAL = (np.log(REAL) - FAK.reindex(REAL.index)).dropna()
sisteaar = max(FAK_AAR)
print("   faktorer siste aar (log, i prosent):",
      ", ".join(f"{m}:{100 * v:+.1f}" for m, v in FAK_AAR[sisteaar].items()))
foerste = min(FAK_AAR)
print(f"   foerste faktoraar {foerste}. Amplitude {100 * (FAK_AAR[sisteaar].max() - FAK_AAR[sisteaar].min()):.1f} % "
      f"i {sisteaar}, {100 * (FAK_AAR[foerste].max() - FAK_AAR[foerste].min()):.1f} % i {foerste}")

def rest_sesong(serie):
    d = serie.diff().dropna()
    X = np.column_stack([np.ones(len(d))] + [[1.0 if p.month == m else 0.0 for p in d.index] for m in range(2, 13)])
    y = d.values
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    rss1 = float(((y - X @ b) ** 2).sum()); rss0 = float(((y - y.mean()) ** 2).sum())
    d1, d2 = 11, len(y) - 12
    F = ((rss0 - rss1) / d1) / (rss1 / d2)
    return F, f_sf(F, d1, d2), len(y)

F0, p0, n0 = rest_sesong(LN.loc[JUST_NOK.index])
F1, p1, n1 = rest_sesong(JUST_NOK)
print(f"   F-test for maanedseffekt i maanedsendringer: foer justering F={F0:.2f} p={p0:.4f}, "
      f"etter F={F1:.2f} p={p1:.4f} ({n1} mnd)")
k2 = p1 > 0.10
RES["kriterier"]["K2"] = bool(k2)
RES["sesong"] = {"F_foer": round(F0, 2), "p_foer": round(p0, 4), "F_etter": round(F1, 2), "p_etter": round(p1, 4)}
print(f"   K2 (p over 0,10 etter justering): {'HOLDER' if k2 else 'HOLDER IKKE'}")

# kontroll: tolv maaneders glidende snitt
KONTROLL = np.log(REAL.rolling(12).mean()).dropna()


# ================================================= K4: kostnad og margin
print("\nK4. Produksjonskostnad fra Fiskeridirektoratet")
KOST = None
SIDER = ["https://www.fiskeridir.no/Akvakultur/Tall-og-analyse/Loennsomhetsundersoekelse-for-laks-og-regnbueoerret/Matfiskproduksjon-laks-og-regnbueoerret",
         "https://www.fiskeridir.no/Akvakultur/Tall-og-analyse/Loennsomhetsundersoekelse-for-laks-og-regnbueoerret",
         "https://www.fiskeridir.no/statistikk-tall-og-analyse/data-og-statistikk-om-akvakultur/loennsomhetsundersoekelse-for-laks-og-regnbueoerret"]
lenker = set()
for s in SIDER:
    try:
        r = get(s)
        print(f"   {s[-60:]:60} HTTP {r.status_code}")
        if r.status_code == 200:
            for m in re.finditer(r'href="([^"]+\.xlsx?[^"]*)"', r.text):
                u = m.group(1)
                lenker.add(u if u.startswith("http") else "https://www.fiskeridir.no" + u)
    except Exception as e:
        print(f"   {s[-60:]:60} {type(e).__name__}")
lenker.add("https://www.fiskeridir.no/Akvakultur/Tall-og-analyse/Loennsomhetsundersoekelse-for-laks-og-regnbueoerret/Matfiskproduksjon-laks-og-regnbueoerret/_/attachment/download/e6d800ae-84ad-42d4-b211-763e3e73e9ae:5d8fdff81f6c042b77c2e819ba9ff51c59503f1f/lon-mat14-flerefylker.xlsx")
print(f"   {len(lenker)} regnearklenker")

funn = []
for u in sorted(lenker):
    try:
        r = get(u, timeout=90)
        if r.status_code != 200:
            print(f"   HTTP {r.status_code} {u.split('/')[-1][:50]}"); continue
        ark = pd.read_excel(io.BytesIO(r.content), sheet_name=None, header=None)
        for navn, df in ark.items():
            df = df.astype(object)
            # aarsrad: en rad med minst 8 aarstall
            aarrad = None
            for i in range(min(len(df), 40)):
                aar = [x for x in df.iloc[i].tolist() if isinstance(x, (int, float)) and not pd.isna(x)
                       and 1980 <= float(x) <= 2035 and float(x) == int(x)]
                if len(aar) >= 8:
                    aarrad = i; break
            if aarrad is None:
                continue
            kol = {j: int(x) for j, x in enumerate(df.iloc[aarrad].tolist())
                   if isinstance(x, (int, float)) and not pd.isna(x) and 1980 <= float(x) <= 2035}
            for i in range(len(df)):
                etikett = " ".join(str(x) for x in df.iloc[i].tolist()[:3] if isinstance(x, str)).lower()
                if "produksjonskost" in etikett and ("kg" in etikett or "kilo" in etikett):
                    vals = {kol[j]: df.iat[i, j] for j in kol}
                    vals = {a: float(v) for a, v in vals.items() if isinstance(v, (int, float)) and not pd.isna(v) and v > 0}
                    if len(vals) >= 8:
                        funn.append((u.split("/")[-1], navn, etikett[:70], vals))
    except Exception as e:
        print(f"   {u.split('/')[-1][:50]}: {type(e).__name__} {str(e)[:50]}")
for fil, ark, et, v in funn:
    aar = sorted(v)
    print(f"   funnet: {fil[:40]} / {ark}: '{et}' {len(v)} aar {aar[0]}..{aar[-1]}, siste {v[aar[-1]]:.2f}")
# Kostnadsserien skjoetes av to deler for hele landet: den gamle (1986 til
# 2008) og den nye (fra 2008). Foerste kjoering 25.09.2026 valgte bare den
# lengste enkeltserien, som sluttet i 2008, og bar 2008-kostnaden flatt fram
# til 2026. Kostnaden var da 18 kr/kg mot rundt 60 i virkeligheten, marginen
# ble 4,5 i stedet for rundt 1,2, og hele terskeltesten var ugyldig.
# Naa: nyeste serie for hele landet, lenket til den eldste i overlappende aar.
# I tillegg kreves at serien er fersk (siste aar tidligst i fjor minus to).
if funn:
    hele = [f for f in funn if "hele landet" in f[1].lower()] or funn
    ny = max(hele, key=lambda x: (max(x[3]), len(x[3])))
    gml = min(hele, key=lambda x: (min(x[3]), -len(x[3])))
    nyv, gmlv = dict(ny[3]), dict(gml[3])
    felles = sorted(set(nyv) & set(gmlv))
    if gml is not ny and felles:
        faktor = float(np.mean([nyv[a] / gmlv[a] for a in felles]))
        k = {a: v * faktor for a, v in gmlv.items() if a < min(nyv)}
        k.update(nyv)
        print(f"   skjoetet: {gml[0][:30]} / {gml[1]} ({min(gmlv)}..{max(gmlv)}) og {ny[0][:30]} / {ny[1]} "
              f"({min(nyv)}..{max(nyv)}), overlapp {felles}, faktor {faktor:.3f}"
              + ("" if abs(faktor - 1) < 0.10 else "  OBS: definisjonene avviker mer enn 10 % i overlappen"))
        RES["kost_skjoet"] = {"gammel": [gml[0], gml[1]], "ny": [ny[0], ny[1]], "overlapp": felles, "faktor": faktor}
    else:
        k = nyv
        print(f"   ingen skjoeting mulig, bruker {ny[0][:30]} / {ny[1]}")
    KOST = pd.Series(k).sort_index()
    print("   kostnad per aar (kr/kg):", ", ".join(f"{a}:{v:.2f}" for a, v in KOST.items()))

k4 = False
if KOST is not None and len(KOST) >= 15:
    endr = (KOST / KOST.shift(1) - 1).dropna() * 100
    brudd = endr[endr.abs() > 30]
    print(f"   aarsendringer over 30 %: {', '.join(f'{a}: {v:+.0f} %' for a, v in brudd.items()) or 'ingen'}")
    fersk = int(KOST.index[-1]) >= pd.Timestamp.now().year - 3
    print(f"   siste kostnadsaar {int(KOST.index[-1])}: {'fersk' if fersk else 'FOR GAMMEL, marginen kan ikke brukes'}")
    k4 = brudd.empty and fersk
    RES["kost"] = {"aar": [int(a) for a in KOST.index], "brudd": {int(a): round(float(v), 1) for a, v in brudd.items()}}
else:
    print("   ingen brukbar kostnadsserie med minst 15 aar")
RES["kriterier"]["K4"] = bool(k4)
print(f"   K4 (kostnadsserie uten uforklart brudd): {'HOLDER' if k4 else 'HOLDER IKKE, eller maa forklares manuelt'}")

MARGIN = None
if KOST is not None and len(KOST) >= 10:
    # aar Y kjent fra desember Y+1, flatt fram til neste
    kjent = {}
    for a, v in KOST.items():
        kjent[pd.Period(f"{int(a) + 1}-12", "M")] = float(v)
    ks = pd.Series(kjent).sort_index()
    ks = ks.reindex(pd.period_range(ks.index[0], JUST_NOK.index[-1], freq="M")).ffill()
    MARGIN = (np.exp(JUST_NOK) / ks.reindex(JUST_NOK.index)).dropna()
    print(f"   margin {MARGIN.index[0]} til {MARGIN.index[-1]}, siste {MARGIN.iloc[-1]:.2f}, "
          f"min {MARGIN.min():.2f} ({MARGIN.idxmin()}), maks {MARGIN.max():.2f}")


# ======================================================== A-skaarene
LR = JUST_REAL
A_raa = pd.Series((1 - expanding_pct(LR.values)) * 100, index=LR.index)
A_det = pd.Series(expanding_pct_detrend(LR.values), index=LR.index)
A_mar = None
if MARGIN is not None:
    A_mar = pd.Series((1 - expanding_pct(np.log(MARGIN.values))) * 100, index=MARGIN.index)
print(f"\nA siste maaned {LR.index[-1]}: raa {A_raa.iloc[-1]:.1f}, detrendet {A_det.iloc[-1]:.1f}"
      + (f", margin-A {A_mar.iloc[-1]:.1f}, margin {MARGIN.iloc[-1]:.2f}" if A_mar is not None else ""))
print(f"Andel maaneder med raa A minst 80: {100 * (A_raa >= 80).mean():.0f} %, detrendet: {100 * (A_det >= 80).mean():.0f} %")


# ======================================================= K3: papirene
print("\nK3. Papirene")
PAPIR = {"MOWI.OL": "Mowi", "SALM.OL": "SalMar", "LSG.OL": "Leroy", "GSF.OL": "Grieg",
         "BAKKA.OL": "Bakkafrost", "MAS.OL": "Masoval", "AUSS.OL": "Austevoll (blandet)"}
KURS_USD, KURS_NOK = {}, {}
for tk in PAPIR:
    try:
        s, val = yahoo(tk)
        if val not in ("NOK", None):
            print(f"   {tk}: valuta {val}, hoppet over"); continue
        KURS_NOK[tk] = s
        KURS_USD[tk] = realt((s / NOKX.reindex(s.index)).dropna())
    except Exception as e:
        print(f"   {tk}: {type(e).__name__}")
    time.sleep(0.3)
VERDEN, _ = yahoo("IWDA.L")
VERDEN = realt(VERDEN)

def maal(ks, pris, verden, utelat=()):
    x = np.log(pris).diff(); y = np.log(ks).diff(); w = np.log(verden).diff()
    d = pd.concat([x, y, w], axis=1, keys=["x", "y", "w"]).dropna()
    d = d[(d.index >= FIKS) & (~d.index.isin([pd.Period(u, "M") for u in utelat]))]
    if len(d) < 24:
        return None
    r = float(np.corrcoef(d.x, d.y)[0, 1])
    rx = d.x - np.polyval(np.polyfit(d.w, d.x, 1), d.w)
    ry = d.y - np.polyval(np.polyfit(d.w, d.y, 1), d.w)
    rm = float(np.corrcoef(rx, ry)[0, 1])
    return {"nf": len(d), "r": round(r, 3), "rm": round(rm, 3)}

PRIS_USD = np.exp(JUST_REAL)
PRIS_NOK = np.exp(JUST_NOK)
VERDEN_NOK = VERDEN * NOKX.reindex(VERDEN.index)
bestaar = []
print(f"   {'papir':10} {'navn':22} {'nf':>4} {'r':>6} {'rm':>6}  | uten sep/okt 2022 | kroner mot kroner | status")
RES["papirer"] = {}
for tk, navn in PAPIR.items():
    if tk not in KURS_USD:
        continue
    a = maal(KURS_USD[tk], PRIS_USD, VERDEN)
    b = maal(KURS_USD[tk], PRIS_USD, VERDEN, utelat=("2022-09", "2022-10"))
    c = maal(KURS_NOK[tk], PRIS_NOK, VERDEN_NOK)
    if not a:
        print(f"   {tk:10} {navn:22} for kort serie"); continue
    ok = a["nf"] >= NF_MIN and a["r"] >= TERSKEL_R and a["rm"] >= TERSKEL_R and "blandet" not in navn
    snur = b and ((b["r"] >= TERSKEL_R and b["rm"] >= TERSKEL_R) != (a["r"] >= TERSKEL_R and a["rm"] >= TERSKEL_R))
    if ok:
        bestaar.append(tk)
    RES["papirer"][tk] = {"alle": a, "uten_2022": b, "nok": c, "bestaar": ok}
    print(f"   {tk:10} {navn:22} {a['nf']:4} {a['r']:6.3f} {a['rm']:6.3f}  | "
          f"{b['r'] if b else '-':>6} {b['rm'] if b else '-':>6}   | {c['r'] if c else '-':>6} {c['rm'] if c else '-':>6}    | "
          f"{'BESTAAR' if ok else 'nei'}{'  (resultatet snur uten 2022)' if snur else ''}")
k3 = len(bestaar) > 0
RES["kriterier"]["K3"] = bool(k3)
print(f"   K3 (minst ett papir): {'HOLDER' if k3 else 'HOLDER IKKE'}. Bestaar: {', '.join(bestaar) or 'ingen'}")


# ========================================== terskeltesten for marginen
print("\nTerskeltesten for marginen")
# kurv: likt vektet snitt av maanedlige log-avkastninger i dollar, reelt
kurv_ret = pd.concat({tk: np.log(s).diff() for tk, s in KURS_USD.items()
                      if "blandet" not in PAPIR[tk]}, axis=1).mean(axis=1, skipna=True)
KURV = kurv_ret.dropna().cumsum()
def fram(logserie, h):
    return logserie.shift(-h) - logserie
UTF = {"kurv24": fram(KURV, 24), "kurv12": fram(KURV, 12),
       "pris24": fram(JUST_REAL, 24), "pris12": fram(JUST_REAL, 12)}
PRIMAER = "kurv24"

def signal_serier():
    s = {}
    if A_mar is not None:
        for t in (60, 70, 75, 80, 85, 90, 95):
            s[f"pct{t}"] = A_mar >= t
        for t in (1.0, 1.1, 1.2, 1.3):
            s[f"abs{t}"] = MARGIN < t
    return s
SIG = signal_serier()

def innslag(sig, til=None):
    ut, siste = [], None
    for t, v in sig.items():
        if til is not None and t > til:
            break
        if v and (siste is None or (t - siste).n > PAUSE):
            ut.append(t)
        if v:
            siste = t
    return ut

def median_utfall(inn, utf):
    v = [utf.get(t) for t in inn]
    v = [x for x in v if x is not None and np.isfinite(x)]
    return (float(np.median(v)), len(v)) if v else (np.nan, 0)

# Trinn 1: informasjon uten terskel.
#
# Foerste utkast forskjoev marginserien sirkulaert mot utfallet. Det ble
# kalibrert paa simulerte serier uten sammenheng foer bruk, og ga p under 0,05
# i 12 % av tilfellene mot en uavhengig kurv og 35 % mot prisens egen framtid.
# Forkastet. Marginpersentilen er ikke stasjonaer, og da holder ikke en
# forskyvning som null.
#
# Nullen naa lager kunstige utfallsserier i stedet og lar marginen staa:
#   kurv: maanedsavkastningene trekkes i blokker paa 24 maaneder (sirkulaer
#         blokkbootstrap), og 24-maanedersutfallet regnes paa nytt.
#   pris: maanedsendringene i den sesongjusterte prisen trekkes paa samme maate,
#         en ny prisbane bygges, og BADE marginen, persentilen og utfallet
#         regnes paa nytt fra den. Da faar nullen noyaktig den samme
#         selvreferansen som den ekte testen, og skjevheten kanselleres.
#   Prisutfallet i trinn 1 er i kroner, samme valuta som marginen.
BLOKK, TREKK1 = 24, 500

def rangkorr(a, b):
    d = pd.concat([a, b], axis=1).dropna()
    if len(d) < 36:
        return np.nan, len(d)
    return float(d.iloc[:, 0].rank().corr(d.iloc[:, 1].rank())), len(d)

def blokktrekk(x, n, L=BLOKK):
    x = np.asarray(x); m = len(x); ut = []
    while len(ut) < n:
        st = rng.integers(m)
        ut.extend(x[(st + np.arange(L)) % m])
    return np.array(ut[:n])

def fram_arr(logbane, h=24):
    f = np.full(len(logbane), np.nan)
    f[:-h] = logbane[h:] - logbane[:-h]
    return f

def trinn1_kurv(amar, kurvret, h=24):
    r = kurvret.dropna()
    obs, n = rangkorr(amar, pd.Series(fram_arr(r.cumsum().values, h), index=r.index))
    if not np.isfinite(obs):
        return None
    null = []
    for _ in range(TREKK1):
        rr = blokktrekk(r.values, len(r))
        null.append(rangkorr(amar, pd.Series(fram_arr(np.cumsum(rr), h), index=r.index))[0])
    null = np.array([x for x in null if np.isfinite(x)])
    return {"rho": round(obs, 3), "n": n, "p": round(float(((null >= obs).sum() + 1) / (len(null) + 1)), 3)}

def amar_fra(lnpris, kost):
    """kost: log kostnad som serie paa samme indeks (kjent-fra-regelen er allerede brukt)."""
    m = lnpris - kost
    return pd.Series((1 - expanding_pct(m.values)) * 100, index=m.index)

def trinn1_pris(lnpris, lnkost, h=24):
    d = pd.concat([lnpris, lnkost], axis=1).dropna()
    lp, lk = d.iloc[:, 0], d.iloc[:, 1]
    obs, n = rangkorr(amar_fra(lp, lk), pd.Series(fram_arr(lp.values, h), index=lp.index))
    if not np.isfinite(obs):
        return None
    dl = lp.diff().dropna().values
    null = []
    for _ in range(TREKK1):
        bane = lp.iloc[0] + np.concatenate([[0], np.cumsum(blokktrekk(dl, len(lp) - 1))])
        bane = pd.Series(bane, index=lp.index)
        null.append(rangkorr(amar_fra(bane, lk), pd.Series(fram_arr(bane.values, h), index=lp.index))[0])
    null = np.array([x for x in null if np.isfinite(x)])
    return {"rho": round(obs, 3), "n": n, "p": round(float(((null >= obs).sum() + 1) / (len(null) + 1)), 3)}

# Kalibrering foer bruk: tilfeldig pris, jevn kostnad, uavhengig kurv.
def kalibrer(ant=200, n=300):
    tk, tp = 0, 0
    idx = pd.period_range("2000-01", periods=n, freq="M")
    for i in range(ant):
        lp = pd.Series(np.cumsum(rng.normal(0.003, 0.07, n)), index=idx)
        lk = pd.Series(np.linspace(0, 0.004 * n, n), index=idx)
        kurv = pd.Series(rng.normal(0.005, 0.08, n), index=idx)
        a = trinn1_kurv(amar_fra(lp, lk), kurv)
        b = trinn1_pris(lp, lk)
        tk += bool(a and a["p"] < 0.05); tp += bool(b and b["p"] < 0.05)
    return tk / ant, tp / ant

if A_mar is None:
    print("   ingen margin, terskeltesten hoppes over")
    RES["terskel"] = None
else:
    kal_a, kal_b = kalibrer()
    print(f"   kalibrering paa {200} simuleringer uten sammenheng, andel p under 0,05: "
          f"kurv {100 * kal_a:.1f} %, prisens egen framtid {100 * kal_b:.1f} %")
    RES["kalibrering"] = {"kurv": kal_a, "egen_pris": kal_b}
    LNK = np.log(ks.reindex(JUST_NOK.index))
    t1 = {"kurv24": trinn1_kurv(A_mar, kurv_ret, 24), "kurv12": trinn1_kurv(A_mar, kurv_ret, 12),
          "pris24_nok": trinn1_pris(JUST_NOK, LNK, 24), "pris12_nok": trinn1_pris(JUST_NOK, LNK, 12)}
    for k, v in t1.items():
        print(f"   trinn 1, {k}: rho {v['rho'] if v else '-'}, p {v['p'] if v else '-'}, n {v['n'] if v else '-'}")
    info = t1[PRIMAER] is not None and t1[PRIMAER]["p"] <= 0.10
    RES["trinn1"] = t1
    print(f"   trinn 1 paa primaerutfallet ({PRIMAER}): {'informasjon' if info else 'ingen informasjon, laks faar ikke flagg'}"
          + ("" if kal_a <= 0.075 else "  OBS: testen var for liberal i kalibreringen, resultatet kan ikke brukes"))

    # Trinn 3 foerst, paa hele utvalget: kurve over tersklene
    print("\n   Hele utvalget (beskrivende og plataatest)")
    print(f"   {'terskel':8} {'andel mnd':>9} {'episoder':>8} | {'kurv 24':>8} {'kurv 12':>8} {'pris 24':>8} {'pris 12':>8}")
    kurve = {}
    for nv, s in SIG.items():
        inn = innslag(s)
        rad = {k: median_utfall(inn, UTF[k]) for k in UTF}
        kurve[nv] = {"andel": float(s.mean()), "episoder": len(inn), **{k: rad[k][0] for k in rad},
                     "n_prim": rad[PRIMAER][1], "datoer": [str(t) for t in inn]}
        f = lambda v: "-" if not np.isfinite(v) else f"{100 * (np.exp(v) - 1):+7.1f}%"
        print(f"   {nv:8} {100 * s.mean():8.0f}% {len(inn):8} | {f(rad['kurv24'][0])} {f(rad['kurv12'][0])} "
              f"{f(rad['pris24'][0])} {f(rad['pris12'][0])}   {', '.join(str(t) for t in inn)}")
    RES["kurve"] = kurve
    FAM = {"pct": ["pct60", "pct70", "pct75", "pct80", "pct85", "pct90", "pct95"],
           "abs": ["abs1.0", "abs1.1", "abs1.2", "abs1.3"]}
    def plataa(nv):
        fam = FAM["pct"] if nv.startswith("pct") else FAM["abs"]
        i = fam.index(nv)
        nab = [fam[j] for j in (i - 1, i + 1) if 0 <= j < len(fam)]
        return all(np.isfinite(kurve[x][PRIMAER]) and kurve[x][PRIMAER] > 0 for x in nab + [nv])

    # Trinn 2: terskel valgt uten fasit, aar for aar fra 2012
    print("\n   Trinn 2: terskel valgt hvert aarsskifte med data kjent da")
    utenfor, valg, valg_pct = {"valgt": [], "pct80": [], "abs1.0": [], "valgt+det": []}, {}, {}
    for aar in range(2012, LR.index[-1].year + 1):
        slutt = pd.Period(f"{aar - 1}-12", "M")
        kjent_til = slutt - 24          # utfallet maa vaere ferdig
        best, bestv, bestp, bestpv = None, -np.inf, None, -np.inf
        for nv, s in SIG.items():
            inn = [t for t in innslag(s, til=kjent_til)]
            v, n = median_utfall(inn, UTF[PRIMAER].loc[:kjent_til + 24])
            if n >= 3 and np.isfinite(v) and v > bestv:
                best, bestv = nv, v
            if nv.startswith("pct") and n >= 3 and np.isfinite(v) and v > bestpv:
                bestp, bestpv = nv, v
        valg[aar] = best
        valg_pct[aar] = bestp
        for nv_key, sig in (("valgt", SIG.get(best)), ("pct80", SIG["pct80"]), ("abs1.0", SIG["abs1.0"]),
                            ("valgt+det", None if best is None else (SIG[best] & (A_det.reindex(SIG[best].index) >= 80)))):
            if sig is None:
                continue
            aarets = sig[(sig.index >= pd.Period(f"{aar}-01", "M")) & (sig.index <= pd.Period(f"{aar}-12", "M"))]
            for t in innslag(sig):
                if t in aarets.index and aarets.get(t):
                    utenfor[nv_key].append(t)
    print("   valgt terskel per aar:", ", ".join(f"{a}:{v}" for a, v in valg.items()))
    print("   beste persentilterskel per aar:", ", ".join(f"{a}:{v}" for a, v in valg_pct.items()))
    RES["valg_per_aar"] = valg; RES["valg_pct_per_aar"] = valg_pct
    res2 = {}
    for k, inn in utenfor.items():
        inn = sorted(set(inn))
        v, n = median_utfall(inn, UTF[PRIMAER])
        v2, n2 = median_utfall(inn, UTF["pris24"])
        res2[k] = {"innslag": [str(t) for t in inn], "kurv24": v, "n": n, "pris24": v2}
        f = lambda v: "-" if not np.isfinite(v) else f"{100 * (np.exp(v) - 1):+.1f} %"
        print(f"   {k:10} {len(inn):3} innslag utenfor utvalget, {n} med fasit: kurv 24 mnd {f(v)}, pris 24 mnd {f(v2)}"
              f"   {', '.join(str(t) for t in inn)}")
    RES["trinn2"] = res2

    # Valget, etter regelen som er bestemt
    print("\n   Valget")
    endelig = None
    if not info:
        print("   Trinn 1 viste ingen informasjon. Laks faar ikke flagg.")
    elif kurve["abs1.0"]["episoder"] >= 3 and plataa("abs1.0"):
        endelig = "abs1.0"
        print("   Nullpunktet 1,0 har minst tre episoder og bestaar plataatesten. Det brukes.")
    else:
        siste = valg_pct.get(max(valg_pct)) if valg_pct else None
        if siste and plataa(siste):
            endelig = siste
            print(f"   Nullpunktet holder ikke. Beste persentilterskel i trinn 2 siste aar er {siste}, "
                  "som bestaar plataatesten. Den brukes.")
        else:
            print(f"   Nullpunktet holder ikke, og beste persentilterskel siste aar ({siste}) bestaar ikke "
                  "plataatesten. Laks faar ikke flagg.")
    if endelig:
        med_det = res2["valgt+det"]["kurv24"] > res2["valgt"]["kurv24"] if np.isfinite(res2["valgt+det"]["kurv24"]) else False
        print(f"   Detrendet A som andre ledd: {'beholdes, den forbedret utfallet i trinn 2' if med_det else 'tas ut, den forbedret ikke utfallet i trinn 2'}")
        regel = SIG[endelig] & (A_det.reindex(SIG[endelig].index) >= 80) if med_det else SIG[endelig]
        andel = float(regel.mean())
        k5 = andel <= 0.25
        print(f"   K5: flagget staar {100 * andel:.0f} % av maanedene. {'Under' if k5 else 'Over'} grensen paa 25 %.")
        for t in innslag(regel):
            v = UTF["pris24"].get(t); k = UTF["kurv24"].get(t)
            f = lambda v: "-" if v is None or not np.isfinite(v) else f"{100 * (np.exp(v) - 1):+.1f} %"
            print(f"      episode {t}: pris 24 mnd {f(v)}, kurv 24 mnd {f(k)}")
        RES["kriterier"]["K5_andel"] = round(andel, 3)
        RES["valg"] = {"terskel": endelig, "med_detrendet": bool(med_det)}
        print(f"   Flagget staar naa: {'JA' if bool(regel.iloc[-1]) else 'nei'} ({regel.index[-1]})")


# ============================================================== lagring
os.makedirs("sonder", exist_ok=True)
ut = pd.DataFrame({"nok_kg": NOK, "uker": NUKER, "usd_real": REAL, "sesongfaktor": FAK,
                   "just_nok_log": JUST_NOK, "just_real_log": JUST_REAL,
                   "margin": MARGIN if MARGIN is not None else np.nan,
                   "A_raa": A_raa, "A_detrendet": A_det,
                   "A_margin": A_mar if A_mar is not None else np.nan})
ut.index = ut.index.astype(str)
ut.to_csv("sonder/laks.csv", float_format="%.5f")
json.dump(RES, open("sonder/laks.json", "w"), ensure_ascii=False, indent=1, default=str)
print("\nOppsummering av kriteriene:", ", ".join(f"{k}: {v}" for k, v in RES["kriterier"].items()))
print("Lagret sonder/laks.csv og sonder/laks.json")
print("\nSend hele utskriften tilbake.")
