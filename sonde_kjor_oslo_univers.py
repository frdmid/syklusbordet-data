# ---------------------------------------------------------------------------
# sonde_kjor_oslo_univers: flaggene i modellen mot hele universet av aksjer
# paa Oslo Boers (Frodes bestilling 09.10.2026). Finnes sammenhenger vi ikke
# har funnet? Horisonter: 1 dag, 1, 3, 6, 12 og 24 maaneder.
#
# Dette er datagraving med svaert mange tester (rundt 300 aksjer x 12 signaler
# x 6 horisonter). Uten kontroll gir det hundrevis av falske funn. Alt under
# er satt FOER kjoering. Resultatene er IN_SAMPLE: et funn er en hypotese som
# maa registreres og maales framover, ikke et bevis.
#
# UNIVERS: alle aksjer paa Euronext-listen for Oslo (Oslo Boers, Euronext
# Expand og Euronext Growth) per 09.10.2026, kurser fra Yahoo (TICKER.OL,
# utbyttejustert, daglig fra 2000). Bare dagens noterte selskaper:
# konkurser og avnoteringer mangler (overlevelsesskjevhet, trekker opp).
# Daglige endringer over 80 % i log regnes som datafeil og settes til mangler.
#
# FLAGG (punkt-i-tid, samme funksjoner som priser.py, fra serier/priser_mnd.csv):
#   bunnsone   raa A >= 80 og detrendet A >= 80 (Championens regel)
#   d95        detrendet A >= 95, bare Brent og WTI (det parallelle signalet)
#   Ny episode: foerste flaggmaaned etter minst 12 maaneder uten flagg.
#   Inngang: foerste handelsdag fra og med den 10. i maaneden etter
#   flaggmaaneden (da er maanedstallene publisert). Episoder fra 2001.
#
# MAAL: meravkastning (log) fra inngang til inngang + h handelsdager, mot et
# likevektet snitt av alle aksjene i universet samme dager. h = 1, 21, 63,
# 126, 252, 504.
#
# TEST per aksje, signal og horisont (minst 3 episoder med data):
#   p     to-sidig, mot 1000 trekk av like mange tilfeldige inngangsdatoer for
#         samme aksje (samme horisont).
#         RETTET etter foerste kjoering 09.10.2026 (kriteriene uendret): talt p
#         har minste verdi rundt 0,001, og FDR over rundt 600 tester per
#         horisont krever rundt 0,0002, saa null funn var garantert. Naa:
#         z = (snitt - snitt i trekkene) / sd i trekkene, p fra normalhalen.
#   FDR   Benjamini-Hochberg per horisont over alle tester, q = 0,10.
#   ROBUST  funnet holder bare hvis det ogsaa (a) har samme fortegn i minst
#         75 % av episodene og (b) beholder fortegnet naar hver episode tas ut
#         en og en.
#   PLACEBO  hele kjoeringen gjentas 10 ganger med tilfeldige flaggdatoer
#         (samme antall episoder per signal). Antall robuste funn i placebo er
#         det tilfeldighet alene gir.
# BESLUTNING: et funn regnes bare som kandidat hvis det overlever FDR og
# robusthet, og antall robuste funn paa horisonten er klart over placebo
# (mer enn snittet pluss to standardavvik). Kandidater maales videre som
# instrument (r og rm, som IKZ-maalingen) eller registreres som Challenger.
# Ingenting paa dashbordet endres.
# ---------------------------------------------------------------------------

import ast, io, json, math, time, warnings
import numpy as np
import pandas as pd
import requests

warnings.filterwarnings("ignore")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
H = {"1d": 1, "1m": 21, "3m": 63, "6m": 126, "12m": 252, "24m": 504}
N_PERM, N_PLACEBO, Q, MIN_EP, PAUSE = 1000, 10, 0.10, 3, 12
rng = np.random.default_rng(20261009)


def last_fra(fil, navn):
    t = ast.parse(open(fil, encoding="utf-8").read())
    kropp = [n for n in t.body if isinstance(n, ast.FunctionDef) and n.name in navn]
    ns = {"np": np, "MIN_HIST": 60}
    exec(compile(ast.Module(body=kropp, type_ignores=[]), fil, "exec"), ns)
    return ns

P = last_fra("priser.py", {"expanding_pct", "expanding_pct_detrend"})


# ------------------------------------------------------------------ flagg
print("1. FLAGG (punkt-i-tid fra serier/priser_mnd.csv)\n")
pm = pd.read_csv("serier/priser_mnd.csv")
SIGNAL = {}
for seg, d in pm.groupby("segment"):
    d = d.sort_values("t")
    idx = pd.PeriodIndex(d["t"], freq="M")
    lr = np.log(d["real"].astype(float).values)
    A = (1 - P["expanding_pct"](lr)) * 100
    Ad = P["expanding_pct_detrend"](lr)
    over = lambda v, t: (~np.isnan(v)) & (v >= t)
    regler = {"bunnsone": over(A, 80) & over(Ad, 80)}
    if seg in ("brent", "wti"):
        regler["d95"] = over(Ad, 95)
    for navn, f in regler.items():
        ep, siste = [], None
        for p, v in zip(idx, f):
            if v and (siste is None or (p - siste).n > PAUSE):
                ep.append(p)
            if v:
                siste = p
        ep = [p for p in ep if p >= pd.Period("2001-01", "M")]
        if ep:
            SIGNAL[f"{seg}:{navn}"] = ep
for k, v in SIGNAL.items():
    print(f"   {k:22s} {len(v)} episoder: {', '.join(str(p) for p in v)}")


# ------------------------------------------------------------------ univers
print("\n\n2. UNIVERS OG KURSER\n")
r = requests.post("https://live.euronext.com/en/pd_es/data/stocks/download?mics=XOSL%2CMERK%2CXOAS",
                  data={"args[initialLetter]": "", "args[fe_type]": "csv", "args[fe_decimal_separator]": ".",
                        "args[fe_date_format]": "d/m/Y"}, headers=UA, timeout=60)
liste = pd.read_csv(io.StringIO(r.content.decode("utf-8-sig")), sep=";", skiprows=[1, 2, 3])
liste = liste[liste["Currency"].isin(["NOK", "USD", "EUR"]) & liste["Symbol"].notna()]
print(f"   Euronext-listen: {len(liste)} papirer ({', '.join(f'{m} {n}' for m, n in liste['Market'].value_counts().items())})")


def yahoo(sym):
    for i in range(3):
        try:
            j = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?period1=946684800"
                             f"&period2={int(time.time())}&interval=1d&events=div%7Csplit&includeAdjustedClose=true",
                             headers=UA, timeout=30).json()
            res = (j.get("chart") or {}).get("result")
            if not res:
                return None
            res = res[0]
            if "timestamp" not in res:
                return None
            adj = (res["indicators"].get("adjclose") or [{}])[0].get("adjclose") or res["indicators"]["quote"][0]["close"]
            s = pd.Series(adj, index=pd.to_datetime(res["timestamp"], unit="s").normalize()).dropna()
            s = s[s > 0]
            return s[~s.index.duplicated(keep="last")]
        except Exception:
            time.sleep(2 * (i + 1))
    return None

KURS, MARKED, NAVN = {}, {}, {}
for _, rad in liste.iterrows():
    sym = str(rad["Symbol"]).strip()
    s = yahoo(sym.replace(" ", "-") + ".OL")
    if s is not None and len(s) >= 504:
        KURS[sym], MARKED[sym], NAVN[sym] = s, rad["Market"], rad["Name"]
    time.sleep(0.25)
print(f"   med minst to aars kurser hos Yahoo: {len(KURS)}")

LP = np.log(pd.DataFrame(KURS).sort_index())
dag = LP.diff()
LP = LP.mask(dag.abs() > np.log(1.8))          # datafeil
LP = LP.ffill(limit=5)
R = LP.diff()
R = R.where(R.abs() <= np.log(1.8))
kalender = R.index[R.notna().sum(axis=1) >= 20]
R = R.loc[kalender]
LP = LP.loc[kalender]
BENCH = R.mean(axis=1, skipna=True).cumsum()
print(f"   handelsdager med minst 20 aksjer: {kalender[0].date()} til {kalender[-1].date()}")

# fremoverrettet meravkastning per horisont: AR[h] (dager x aksjer)
AR = {}
for k, h in H.items():
    fw = LP.shift(-h) - LP
    AR[k] = fw.sub(BENCH.shift(-h) - BENCH, axis=0)


def inngang(p):
    d = pd.Timestamp((p + 1).start_time) + pd.Timedelta(days=9)
    i = kalender.searchsorted(d)
    return i if i < len(kalender) else None


def kjor(signal, n_perm=N_PERM, rng=rng):
    """Returnerer DataFrame med en rad per aksje, signal og horisont."""
    rader = []
    for sig, ep in signal.items():
        idx_e = [i for i in (inngang(p) for p in ep) if i is not None]
        for k in H:
            M = AR[k].values
            for j, sym in enumerate(AR[k].columns):
                col = M[:, j]
                v = np.array([col[i] for i in idx_e])
                ok = ~np.isnan(v)
                n = int(ok.sum())
                if n < MIN_EP:
                    continue
                v = v[ok]
                gyldig = np.flatnonzero(~np.isnan(col))
                trekk = col[gyldig[rng.integers(0, len(gyldig), size=(n_perm, n))]].mean(axis=1)
                mu, sd = trekk.mean(), trekk.std()
                obs = v.mean()
                if not sd > 0:
                    continue
                z = (obs - mu) / sd
                p = math.erfc(abs(z) / math.sqrt(2))
                andel = float(np.mean(np.sign(v) == np.sign(obs)))
                loo = all(np.sign(np.delete(v, i).mean()) == np.sign(obs) for i in range(n)) if n > 1 else False
                rader.append({"signal": sig, "aksje": sym, "h": k, "n": n, "snitt": obs, "snitt_null": mu,
                              "z": z, "p": p, "andel_samme": andel, "loo": loo})
    df = pd.DataFrame(rader)
    if df.empty:
        return df
    df["q"] = np.nan
    for k in H:
        m = df["h"] == k
        ps = df.loc[m, "p"].values
        o = np.argsort(ps)
        qs = ps[o] * len(ps) / (np.arange(len(ps)) + 1)
        qs = np.minimum.accumulate(qs[::-1])[::-1]
        q = np.empty_like(qs); q[o] = np.minimum(qs, 1)
        df.loc[m, "q"] = q
    df["robust"] = (df["q"] <= Q) & (df["andel_samme"] >= 0.75) & df["loo"]
    return df


print("\n\n3. TESTENE\n")
RES = kjor(SIGNAL)
print(f"   tester: {len(RES)} ({', '.join(f'{k} {int((RES.h == k).sum())}' for k in H)})")
print(f"   p under 0,05: {int((RES.p < 0.05).sum())} (ventet ved tilfeldighet rundt {int(0.05 * len(RES))})")
print(f"   FDR q <= {Q}: {int((RES.q <= Q).sum())}, robuste: {int(RES.robust.sum())}, "
      f"|z|>3: {int((RES.z.abs() > 3).sum())} (ventet ved normalfordeling rundt {0.0027 * len(RES):.0f})")

print("\n\n4. PLACEBO: tilfeldige flaggdatoer, samme antall episoder per signal\n")
mnd = pd.period_range("2001-01", str(kalender[-1].to_period("M") - 1), freq="M")
plac = {k: [] for k in H}
for b in range(N_PLACEBO):
    sig_p = {s: sorted(rng.choice(mnd, size=len(ep), replace=False)) for s, ep in SIGNAL.items()}
    d = kjor(sig_p, n_perm=300, rng=np.random.default_rng(b))
    for k in H:
        plac[k].append(int(d[(d.h == k)].robust.sum()) if not d.empty else 0)
    print(f"   runde {b + 1}: robuste per horisont " + ", ".join(f"{k} {plac[k][-1]}" for k in H))

print("\n\n5. RESULTAT PER HORISONT\n")
INSTR = {}
import glob
for f in glob.glob("segments/*.json"):
    s = json.load(open(f, encoding="utf-8"))
    for i in s.get("instrumenter") or []:
        INSTR.setdefault(str(i.get("ticker", "")).replace(".OL", ""), set()).add(s["id"])
for k in H:
    d = RES[RES.h == k]
    rob = d[d.robust].sort_values("p")
    pm_, ps_ = np.mean(plac[k]), np.std(plac[k])
    over_pl = len(rob) > pm_ + 2 * ps_
    print(f"   {k}: {len(d)} tester, robuste {len(rob)}, placebo {pm_:.1f} +/- {ps_:.1f} -> "
          f"{'OVER placebo' if over_pl else 'ikke over placebo'}")
    for _, x in rob.head(15).iterrows():
        seg = x.signal.split(":")[0]
        pa = "paa bordet" if seg in INSTR.get(x.aksje, set()) else ""
        print(f"      {x.aksje:8s} {str(NAVN.get(x.aksje, ''))[:26]:26s} {x.signal:20s} n {x.n}  "
              f"merav. {100 * (np.exp(x.snitt) - 1):+6.1f} % (tilfeldig {100 * (np.exp(x.snitt_null) - 1):+5.1f} %)  "
              f"p {x.p:.3f} q {x.q:.3f} {pa}")
    print()

RES["navn"] = RES.aksje.map(NAVN)
RES["marked"] = RES.aksje.map(MARKED)
RES.to_csv("sonder/oslo_univers.csv", index=False)
print("   Alle tester lagret i sonder/oslo_univers.csv")
