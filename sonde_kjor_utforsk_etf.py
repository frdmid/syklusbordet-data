# ---------------------------------------------------------------------------
# sonde_kjor_utforsk_etf: eksplorativt soek etter fond som foelger to eller
# flere av bordets raavarer
#
# Frodes bestilling 26.09.2026: finne ETF-er vi ikke har tenkt paa, som
# paavirkes av to eller flere raavarer. Fondssonden (sonde_kjor_fond.py) har
# et kart satt paa forhaand. Denne leter i hele universet.
#
# UNIVERSET
#   Alle ETF-er paa Xetra fra Deutsche Boerses liste over handlbare
#   instrumenter. Alle ETF-er paa Xetra er UCITS, saa alle kan kjoepes paa
#   IKZ. ETC og ETN er egne instrumenttyper i lista og er ute. Ute ogsaa:
#   giret, short og invers (navnet), rentefond og valutasikrede andelsklasser
#   (dubletter av samme indeks). Faller lista bort, brukes en reserve fra
#   Deutsche Boerses ETF-statistikk.
#
# MAALINGEN (samme som ellers paa bordet)
#   Maanedlige realendringer i dollar fra 2016-01, bordets egne raavareserier
#   (raavare_hist), partiell korrelasjon rp etter verdensindeksen (IWDA.L).
#
# KRAV, SATT FOER KJOERING. Leting i tusenvis av par finner mye ved flaks,
# saa kravene er strengere enn i fondssonden:
#   1. minst 72 maaneder i vinduet
#   2. rp >= 0,20 over hele vinduet
#   3. Benjamini-Hochberg over alle par fond x raavare, q <= 0,05
#      (Fisher z paa partiell korrelasjon)
#   4. samme fortegn og rp >= 0,10 i BEGGE halvdeler av vinduet (2016-01 til
#      2021-03 og 2021-04 og ut). En sammenheng som bare finnes i den ene
#      halvdelen er ikke til aa stole paa.
#   5. et par av raavarer kvalifiserer naar samlet partiell korrelasjon er
#      >= 0,30 over hele vinduet og >= 0,20 i hver halvdel, og raavarene ikke
#      er samme faktor (korrelasjon under 0,70, saa Brent og WTI teller ikke)
#   Alt som bestaar er "funnet ved leting". Det gaar ikke inn i fondskartet
#   uten en oekonomisk begrunnelse og Frodes ja.
#
# TID
#   Henting av 1000 til 2000 kursserier tar tid. Sonden har et tidsbudsjett
#   (BUDSJETT_MIN) og lagrer kursene i sonder/etf_cache.json. Rekker den ikke
#   alle, maaler den det den har, skriver hvor mange som gjenstaar, og
#   fortsetter der den slapp ved neste kjoering. Filnavnet gjoer at den
#   kjoeres sist av sondene.
# ---------------------------------------------------------------------------

import io, json, math, os, re, time, warnings
import numpy as np
import pandas as pd
import requests

warnings.filterwarnings("ignore")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
FIKS, DELT, NF_KRAV = "2016-01", "2021-04", 72
RP_KRAV, RP_HALV, Q_KRAV, RJ_KRAV, RJ_HALV, SAMME_FAKTOR = 0.20, 0.10, 0.05, 0.30, 0.20, 0.70
BUDSJETT_MIN = float(os.environ.get("ETF_BUDSJETT_MIN", 30))
CACHE = "sonder/etf_cache.json"
KONTROLL = "IWDA.L"
SEKSTEN = ["brent", "wti", "henryhub", "ttf", "uran", "gold", "kobber", "nikkel", "aluminium",
           "sink", "bly", "tinn", "jernmalm", "kull", "kakao", "palmeolje"]
UT = re.compile(r"short|leverag|\b[2-5]x\b|daily|invers|bear|ultra|bond|treasury|govt|government|"
                r"corporate|aggregate|money market|overnight|\bestr\b|floating|duration|sukuk|t-bill|"
                r"inflation[- ]linked|hedged|\bhdg\b|covered|high yield|\bcredit\b|\bfrn\b|\btips\b", re.I)
FX = {"USD": None, "EUR": ("EURUSD=X", False), "GBP": ("GBPUSD=X", False), "GBp": ("GBPUSD=X", False),
      "CHF": ("CHF=X", True)}
T0 = time.time()


def get(url, timeout=60):
    for i in range(3):
        try:
            r = requests.get(url, headers=UA, timeout=timeout)
            if r.status_code in (429, 502, 503):
                time.sleep(4 * (i + 1)); continue
            r.raise_for_status()
            return r
        except requests.RequestException:
            if i == 2:
                raise
            time.sleep(2 * (i + 1))


# ------------------------------------------------------------ universet
def xetra_liste():
    sider = ["https://www.xetra.com/xetra-en/instruments/instruments",
             "https://www.xetra.com/xetra-en/instruments/shares/list-of-tradable-shares",
             "https://www.xetra.com/xetra-en/instruments/etfs-etps/etf-etp-list",
             "https://www.xetra.com/xetra-de/instrumente/alle-handelbaren-instrumente"]
    lenker = []
    for s in sider:
        try:
            html = get(s, 40).text
            for u in re.findall(r'href="([^"]*allTradableInstruments[^"]*\.csv)"', html, re.I):
                lenker.append(u if u.startswith("http") else "https://www.xetra.com" + u)
        except Exception as e:
            print(f"   {s}: {type(e).__name__}")
    for u in dict.fromkeys(lenker):
        try:
            txt = get(u, 120).text
            linjer = txt.splitlines()
            h = next(i for i, l in enumerate(linjer[:20]) if "ISIN" in l and "Mnemonic" in l)
            df = pd.read_csv(io.StringIO("\n".join(linjer[h:])), sep=";", dtype=str)
            print(f"   Xetra-lista: {len(df)} instrumenter fra {u}")
            return df
        except Exception as e:
            print(f"   {u}: {type(e).__name__}: {str(e)[:60]}")
    return None


print("1. Universet\n")
df = xetra_liste()
UNIV = {}
if df is not None:
    kol = {c.lower(): c for c in df.columns}
    typ = next((kol[c] for c in kol if "instrument type" in c or c == "product type" or "instrumenttyp" in c), None)
    navn = next((kol[c] for c in kol if c in ("instrument", "instrument name", "name")), None)
    mn = kol.get("mnemonic")
    isin = kol.get("isin")
    if typ:
        print(f"   instrumenttyper: {dict(df[typ].value_counts().head(8))}")
        df = df[df[typ].astype(str).str.upper().str.strip().isin(["ETF", "ETFS", "EXCHANGE TRADED FUND"])]
    for _, r in df.iterrows():
        n = str(r.get(navn, "")) if navn else ""
        if not r.get(mn) or UT.search(n):
            continue
        UNIV[f"{str(r[mn]).strip()}.DE"] = {"navn": n.strip(), "isin": str(r.get(isin, "")).strip()}
if not UNIV:
    print("   Xetra-lista kom ikke inn. Reserve: fondene fra sonde_ikz.py og fondssonden.")
    for s, n in [("EXH1.DE", "iShares STOXX Europe 600 Oil & Gas"), ("EXV6.DE", "iShares STOXX Europe 600 Basic Resources"),
                 ("EXV7.DE", "iShares STOXX Europe 600 Chemicals"), ("EXH3.DE", "iShares STOXX Europe 600 Food & Beverage"),
                 ("EXH9.DE", "iShares STOXX Europe 600 Utilities"), ("EXXY.DE", "iShares Diversified Commodity Swap"),
                 ("XDBC.DE", "Xtrackers Optimum Yield Diversified Commodity Swap"), ("SXR2.DE", "iShares MSCI Canada")]:
        UNIV[s] = {"navn": n, "isin": ""}
print(f"   {len(UNIV)} ETF-er etter filtrering (giret, short, rente og valutasikret er ute)")

# ------------------------------------------------------------ kurser
_fx = {}


def yahoo(sym, justert=True):
    j = "&events=div%7Csplit&includeAdjustedClose=true" if justert else ""
    res = get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}"
              f"?period1=0&period2={int(time.time())}&interval=1mo{j}", 30).json()["chart"]["result"][0]
    meta = res.get("meta") or {}
    idx = pd.to_datetime(res["timestamp"], unit="s", utc=True).tz_convert(meta.get("exchangeTimezoneName") or "UTC")
    v = None
    if justert:
        try:
            v = res["indicators"]["adjclose"][0]["adjclose"]
        except Exception:
            v = None
    if v is None:
        v = res["indicators"]["quote"][0]["close"]
    s = pd.Series(v, index=idx).dropna()
    s = s[s > 0]
    s.index = s.index.to_period("M")
    s = s[~s.index.duplicated(keep="last")]
    val = meta.get("currency") or "USD"
    if val not in FX:
        raise ValueError(f"valuta {val}")
    if FX[val]:
        fs, inv = FX[val]
        if fs not in _fx:
            f = yahoo(fs, justert=False)
            _fx[fs] = (1.0 / f) if inv else f
        s = (s * _fx[fs].reindex(s.index).ffill()).dropna()
    if val == "GBp":
        s = s / 100.0
    return s


try:
    cache = json.load(open(CACHE, encoding="utf-8"))
except Exception:
    cache = {}
print(f"\n2. Kurser (budsjett {BUDSJETT_MIN:.0f} min, {len(cache)} i lageret fra foer)\n")
ferdig = True
nye = 0
for sym in [KONTROLL] + sorted(UNIV):
    if sym in cache:
        continue
    if time.time() - T0 > BUDSJETT_MIN * 60:
        ferdig = False
        break
    try:
        s = yahoo(sym)
        cache[sym] = {"fra": str(s.index[0]), "v": [round(float(x), 6) for x in s.values]}
    except Exception as e:
        cache[sym] = {"feil": type(e).__name__}
    nye += 1
    time.sleep(0.25)
    if nye % 100 == 0:
        print(f"   {nye} hentet ({time.time() - T0:.0f} s)", flush=True)
        json.dump(cache, open(CACHE, "w"))
os.makedirs("sonder", exist_ok=True)
json.dump(cache, open(CACHE, "w"))
igjen = sum(1 for s in UNIV if s not in cache)
print(f"   {nye} nye denne gangen, {igjen} gjenstaar" + ("" if ferdig else ". Kjoer sonden igjen for resten."))


def serie(sym):
    c = cache.get(sym)
    if not c or "v" not in c:
        return None
    return pd.Series(c["v"], index=pd.period_range(c["fra"], periods=len(c["v"]), freq="M"))


# ------------------------------------------------------------ maaling
print("\n3. Maaling\n")
from raavare_hist import hent
REAL, _NOM, cpi = hent()
if not isinstance(cpi.index, pd.PeriodIndex):
    cpi.index = pd.DatetimeIndex(cpi.index).to_period("M")
defl = lambda s: (s * (cpi.dropna().iloc[-1] / cpi.reindex(s.index).ffill())).dropna()
X = {sid: REAL[sid].dropna().diff().dropna() for sid in SEKSTEN if sid in REAL}
w_s = serie(KONTROLL)
if w_s is None:
    raise SystemExit("Verdensindeksen (IWDA.L) mangler, kan ikke regne partiell korrelasjon.")
W = np.log(defl(w_s)).diff().dropna()


def rest(y, w_):
    A = np.column_stack([np.ones(len(w_)), w_])
    return y - A @ np.linalg.lstsq(A, y, rcond=None)[0]


def rp_paa(i, y, x):
    ww = W.reindex(i).values
    return float(np.corrcoef(rest(y.reindex(i).values, ww), rest(x.reindex(i).values, ww))[0, 1])


def rj_paa(i, y, x1, x2):
    ww = W.reindex(i).values
    yr = rest(y.reindex(i).values, ww)
    A = np.column_stack([np.ones(len(i)), rest(x1.reindex(i).values, ww), rest(x2.reindex(i).values, ww)])
    fit = A @ np.linalg.lstsq(A, yr, rcond=None)[0]
    return float(np.sqrt(max(0.0, 1 - ((yr - fit) ** 2).sum() / ((yr - yr.mean()) ** 2).sum())))


P1, P2 = pd.Period(FIKS, "M"), pd.Period(DELT, "M")
PAR = []          # ett element per fond x raavare
FOND = {}
for sym, info in UNIV.items():
    s = serie(sym)
    if s is None:
        continue
    y = np.log(defl(s)).diff().dropna()
    i0 = y.index.intersection(W.index)
    i0 = i0[i0 >= P1]
    if len(i0) < NF_KRAV:
        continue
    FOND[sym] = {"y": y, "i": i0, **info}
    for sid, x in X.items():
        i = i0.intersection(x.index)
        if len(i) < NF_KRAV:
            continue
        r = rp_paa(i, y, x)
        n = len(i)
        z = math.atanh(max(-0.999999, min(0.999999, r))) * math.sqrt(n - 4)
        p = math.erfc(abs(z) / math.sqrt(2))
        a, b = i[i < P2], i[i >= P2]
        PAR.append({"etf": sym, "raavare": sid, "n": n, "rp": r, "p": p,
                    "rp_1": rp_paa(a, y, x) if len(a) >= 30 else None,
                    "rp_2": rp_paa(b, y, x) if len(b) >= 30 else None})
print(f"   {len(FOND)} fond med minst {NF_KRAV} maaneder, {len(PAR)} par fond x raavare")

# Benjamini-Hochberg over alle par
PAR.sort(key=lambda r: r["p"])
m = len(PAR)
q_min = 1.0
for k in range(m - 1, -1, -1):
    q_min = min(q_min, PAR[k]["p"] * m / (k + 1))
    PAR[k]["q"] = q_min


def holder(r):
    if abs(r["rp"]) < RP_KRAV or r["q"] > Q_KRAV or r["rp_1"] is None or r["rp_2"] is None:
        return False
    sg = 1 if r["rp"] > 0 else -1
    return r["rp_1"] * sg >= RP_HALV and r["rp_2"] * sg >= RP_HALV


kval = {}
for r in PAR:
    if holder(r):
        kval.setdefault(r["etf"], []).append(r)
print(f"   {sum(len(v) for v in kval.values())} par bestaar kravene 1 til 4, fordelt paa {len(kval)} fond")

FUNN = []
for sym, rader in kval.items():
    pos = [r for r in rader if r["rp"] > 0]
    if len(pos) < 2:
        continue
    f = FOND[sym]
    par = []
    for a_ in range(len(pos)):
        for b_ in range(a_ + 1, len(pos)):
            s1, s2 = pos[a_]["raavare"], pos[b_]["raavare"]
            i = f["i"].intersection(X[s1].index).intersection(X[s2].index)
            rr = float(np.corrcoef(X[s1].reindex(i).values, X[s2].reindex(i).values)[0, 1])
            if rr > SAMME_FAKTOR:
                continue
            rj = rj_paa(i, f["y"], X[s1], X[s2])
            a, b = i[i < P2], i[i >= P2]
            rj1 = rj_paa(a, f["y"], X[s1], X[s2]) if len(a) >= 30 else 0
            rj2 = rj_paa(b, f["y"], X[s1], X[s2]) if len(b) >= 30 else 0
            if rj >= RJ_KRAV and rj1 >= RJ_HALV and rj2 >= RJ_HALV:
                par.append({"par": [s1, s2], "r_samlet": round(rj, 3), "halvdeler": [round(rj1, 3), round(rj2, 3)]})
    if par:
        FUNN.append({"etf": sym, "navn": f["navn"], "isin": f["isin"], "nf": len(f["i"]),
                     "raavarer": {r["raavare"]: {"rp": round(r["rp"], 3), "q": round(r["q"], 4),
                                                 "halvdeler": [round(r["rp_1"], 3), round(r["rp_2"], 3)]} for r in pos},
                     "par": sorted(par, key=lambda p: -p["r_samlet"])})

# dubletter: fond som foelger samme indeks (maanedsendringer korrelerer over 0,98)
FUNN.sort(key=lambda f: -f["par"][0]["r_samlet"])
grupper = []
for f in FUNN:
    y = FOND[f["etf"]]["y"]
    for g in grupper:
        y0 = FOND[g[0]["etf"]]["y"]
        i = y.index.intersection(y0.index)
        if len(i) >= 36 and np.corrcoef(y.reindex(i), y0.reindex(i))[0, 1] > 0.98:
            g.append(f); break
    else:
        grupper.append([f])

print(f"\n4. Fond som foelger minst to raavarer (funnet ved leting), {len(grupper)} grupper\n")
KJENT = {"EXH1.DE", "EXV6.DE", "EXXY.DE", "XDBC.DE", "SXR2.DE"}
for g in grupper:
    f = g[0]
    dub = f"  (+ {len(g) - 1} dubletter: {', '.join(x['etf'] for x in g[1:4])}{'...' if len(g) > 4 else ''})" if len(g) > 1 else ""
    print(f"   {f['etf']:10} {f['navn'][:60]}  nf {f['nf']}{'  [allerede i fondssonden]' if f['etf'] in KJENT else ''}{dub}")
    for sid, r in sorted(f["raavarer"].items(), key=lambda x: -x[1]["rp"]):
        print(f"      {sid:10} rp {r['rp']:+.2f}  (halvdeler {r['halvdeler'][0]:+.2f} / {r['halvdeler'][1]:+.2f})  q {r['q']:.4f}")
    for p in f["par"][:4]:
        print(f"      par {p['par'][0]}+{p['par'][1]}: samlet {p['r_samlet']:.2f}  (halvdeler {p['halvdeler'][0]:.2f} / {p['halvdeler'][1]:.2f})")
    print()

neg = sorted([r for rr in kval.values() for r in rr if r["rp"] < 0], key=lambda r: r["rp"])[:15]
if neg:
    print("   Sterkeste NEGATIVE sammenhenger (raavaren er en kostnad for fondet), bare til orientering:")
    for r in neg:
        print(f"      {r['etf']:10} {UNIV[r['etf']]['navn'][:50]:50} {r['raavare']:10} rp {r['rp']:+.2f}")

json.dump({"kjort": time.strftime("%Y-%m-%d %H:%M:%S"), "ferdig": ferdig, "gjenstaar": igjen,
           "univers": len(UNIV), "maalt": len(FOND), "par_testet": len(PAR),
           "funn": FUNN, "grupper": [[x["etf"] for x in g] for g in grupper]},
          open("sonder/utforsk_etf.json", "w"), ensure_ascii=False, indent=1)
print(f"\nLagret sonder/utforsk_etf.json. {'Alle fond er maalt.' if ferdig else f'{igjen} fond gjenstaar: kjoer sonden igjen.'}")
