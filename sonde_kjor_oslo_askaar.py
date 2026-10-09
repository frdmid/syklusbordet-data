# ---------------------------------------------------------------------------
# sonde_kjor_oslo_askaar: A og detrendet A (som tall) mot hele universet av
# aksjer paa Oslo Boers (Frodes bestilling 09.10.2026, i tillegg til
# flaggsonden sonde_kjor_oslo_univers). Horisonter 1 dag, 1, 3, 6, 12, 24 mnd.
#
# Hver maaned er en observasjon, saa skaarene gir langt flere datapunkter enn
# flaggene. Antall tester er likevel stort (rundt 300 aksjer x 18 segmenter x
# 2 skaarer x 6 horisonter). Alt under er satt FOER kjoering, og resultatet
# er IN_SAMPLE.
#
# DATA: som flaggsonden. A og Ad punkt-i-tid fra serier/priser_mnd.csv med
# funksjonene i priser.py. Skaaren for maaned t er kjent fra den 10. i maaned
# t+1 (inngang). Kurser fra Yahoo, univers fra Euronext (dagens noterte,
# overlevelsesskjevhet). Benchmark: likevektet snitt av universet.
#
# MAAL per aksje, segment, skaar og horisont: rangkorrelasjon (Spearman)
# mellom skaaren og meravkastningen fra inngang til inngang + h handelsdager.
# Ett punkt per maaned, minst 60 maaneder felles data. Positiv rho betyr at
# hoey skaar (lav pris) gir hoeyere avkastning etterpaa.
# p: to-sidig, sirkulaer blokkbootstrap av aksjens maanedlige meravkastning
#    (blokker paa 24 mnd, 300 trekk), og utfallet regnes paa nytt fra trekket;
#    skaaren staar fast (samme null som laksesonden, kalibrert der).
#    RETTET etter foerste kjoering 09.10.2026 (kriteriene uendret): med 300
#    trekk er minste p rundt 0,003, og FDR over rundt 7 700 tester per
#    horisont krever p rundt 0,00001, saa null funn var garantert. Naa regnes
#    p fra normalhalen til nullen: z = (rho - snitt i nullen) / sd i nullen.
#    Den talte p staar ved siden av (p_telt).
#    I tillegg: antall tester med |z| over 3 og 4 i ekte data mot placebo.
# FDR: Benjamini-Hochberg per horisont over alle tester, q = 0,10.
# ROBUST: i tillegg samme fortegn paa rho i foerste og andre halvdel av
#    aksjens periode.
# KONTROLL: antall robuste funn sammenlignes med det samme kjoert paa
#    skaarer forskjoevet 120 maaneder fram (samme form, feil tid), som placebo.
# Ingenting paa dashbordet endres.
# ---------------------------------------------------------------------------

import ast, io, json, math, time, warnings, glob
import numpy as np
import pandas as pd
import requests

warnings.filterwarnings("ignore")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
H = {"1d": 1, "1m": 21, "3m": 63, "6m": 126, "12m": 252, "24m": 504}
N_BOOT, BLOKK, Q, MIN_MND = 300, 24, 0.10, 60
rng = np.random.default_rng(20261010)


def last_fra(fil, navn):
    t = ast.parse(open(fil, encoding="utf-8").read())
    kropp = [n for n in t.body if isinstance(n, ast.FunctionDef) and n.name in navn]
    ns = {"np": np, "MIN_HIST": 60}
    exec(compile(ast.Module(body=kropp, type_ignores=[]), fil, "exec"), ns)
    return ns

P = last_fra("priser.py", {"expanding_pct", "expanding_pct_detrend"})

print("1. SKAARER\n")
pm = pd.read_csv("serier/priser_mnd.csv")
SK = {}
for seg, d in pm.groupby("segment"):
    d = d.sort_values("t")
    idx = pd.PeriodIndex(d["t"], freq="M")
    lr = np.log(d["real"].astype(float).values)
    SK[f"{seg}:A"] = pd.Series((1 - P["expanding_pct"](lr)) * 100, index=idx)
    SK[f"{seg}:Ad"] = pd.Series(P["expanding_pct_detrend"](lr), index=idx)
SK = pd.DataFrame(SK)
SK = SK[SK.index >= pd.Period("2000-01", "M")]
print(f"   {SK.shape[1]} skaarer, {SK.index[0]} til {SK.index[-1]}")

print("\n2. UNIVERS OG KURSER\n")
r = requests.post("https://live.euronext.com/en/pd_es/data/stocks/download?mics=XOSL%2CMERK%2CXOAS",
                  data={"args[initialLetter]": "", "args[fe_type]": "csv", "args[fe_decimal_separator]": ".",
                        "args[fe_date_format]": "d/m/Y"}, headers=UA, timeout=60)
liste = pd.read_csv(io.StringIO(r.content.decode("utf-8-sig")), sep=";", skiprows=[1, 2, 3])
liste = liste[liste["Currency"].isin(["NOK", "USD", "EUR"]) & liste["Symbol"].notna()]


def yahoo(sym):
    for i in range(3):
        try:
            j = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?period1=946684800"
                             f"&period2={int(time.time())}&interval=1d&events=div%7Csplit&includeAdjustedClose=true",
                             headers=UA, timeout=30).json()
            res = (j.get("chart") or {}).get("result")
            if not res or "timestamp" not in res[0]:
                return None
            res = res[0]
            adj = (res["indicators"].get("adjclose") or [{}])[0].get("adjclose") or res["indicators"]["quote"][0]["close"]
            s = pd.Series(adj, index=pd.to_datetime(res["timestamp"], unit="s").normalize()).dropna()
            s = s[s > 0]
            return s[~s.index.duplicated(keep="last")]
        except Exception:
            time.sleep(2 * (i + 1))
    return None

KURS, NAVN = {}, {}
for _, rad in liste.iterrows():
    sym = str(rad["Symbol"]).strip()
    s = yahoo(sym.replace(" ", "-") + ".OL")
    if s is not None and len(s) >= 504:
        KURS[sym], NAVN[sym] = s, rad["Name"]
    time.sleep(0.25)
print(f"   aksjer med minst to aars kurser: {len(KURS)}")

LP = np.log(pd.DataFrame(KURS).sort_index())
LP = LP.mask(LP.diff().abs() > np.log(1.8)).ffill(limit=5)
R = LP.diff()
R = R.where(R.abs() <= np.log(1.8))
kal = R.index[R.notna().sum(axis=1) >= 20]
R, LP = R.loc[kal], LP.loc[kal]
BENCH = R.mean(axis=1, skipna=True).cumsum()

# inngangsdag per skaarmaaned
mnd = SK.index
inn = []
for p in mnd:
    i = kal.searchsorted(pd.Timestamp((p + 1).start_time) + pd.Timedelta(days=9))
    inn.append(i if i < len(kal) else -1)
inn = np.array(inn)
ok_m = inn >= 0
mnd, inn, SKv = mnd[ok_m], inn[ok_m], SK.values[ok_m]

# meravkastning (log) per aksje fra inngang i maaned m til inngang i m+1 (for bootstrap),
# og fremover per horisont
EX = LP.sub(BENCH, axis=0).values                     # dager x aksjer
def fram(i, h):
    j = np.minimum(i + h, len(kal) - 1)
    out = EX[j] - EX[i]
    out[(i + h) >= len(kal)] = np.nan
    return out
FW = {k: fram(inn, h) for k, h in H.items()}           # maaneder x aksjer
MND_R = np.vstack([EX[inn[1:]] - EX[inn[:-1]], np.full(EX.shape[1], np.nan)])   # maanedlig meravkastning


def rang(a):
    return pd.DataFrame(a).rank().values


def spearman_mat(S, Y):
    """S: maaneder x skaarer, y: maaneder (en aksje). Rho per skaar paa felles ikke-NaN."""
    out = np.full(S.shape[1], np.nan); n = np.zeros(S.shape[1], int)
    for c in range(S.shape[1]):
        m = ~np.isnan(S[:, c]) & ~np.isnan(Y)
        n[c] = m.sum()
        if n[c] >= MIN_MND:
            out[c] = pd.Series(S[m, c]).rank().corr(pd.Series(Y[m]).rank())
    return out, n


def zrank(M):
    """Rangerer hver kolonne (NaN beholdes), standardiserer, NaN -> 0."""
    Rk = pd.DataFrame(M).rank().values
    mu, sd = np.nanmean(Rk, axis=0), np.nanstd(Rk, axis=0)
    Z = (Rk - mu) / np.where(sd > 0, sd, np.nan)
    return np.nan_to_num(Z), (~np.isnan(Rk)).sum(axis=0)


def kjor(SKm, label):
    """Spearman i matriseform. For hver aksje og horisont: maanedene der utfallet
    finnes (V). Skaarene rangeres innen V; nullen er sirkulaer blokkbootstrap
    av utfallet selv innen V (blokker paa 24 mnd, 300 trekk). Ved overlappende
    utfall (3 til 24 mnd) beholder blokkene det meste av overlappet."""
    rader = []
    for j, sym in enumerate(KURS):
        for k in H:
            y = FW[k][:, j]
            V = np.flatnonzero(~np.isnan(y))
            if len(V) < MIN_MND:
                continue
            S = SKm[V]
            gyld = (~np.isnan(S)).sum(axis=0) >= MIN_MND
            if not gyld.any():
                continue
            Zs, ns = zrank(np.where(gyld, S, np.nan))
            Zy, _ = zrank(y[V][:, None]); Zy = Zy[:, 0]
            mask = ~np.isnan(S)
            rho = (Zs * Zy[:, None]).sum(axis=0) / np.maximum(ns, 1)
            # bootstrap av utfallet
            n = len(V)
            st = rng.integers(0, n, size=(N_BOOT, n // BLOKK + 2))
            idx = ((st[:, :, None] + np.arange(BLOKK)) % n).reshape(N_BOOT, -1)[:, :n]
            Yb = y[V][idx]
            Zb = (pd.DataFrame(Yb.T).rank().values - (n + 1) / 2) / np.sqrt((n * n - 1) / 12)
            null = (Zb.T @ Zs) / np.maximum(ns, 1)                      # N_BOOT x skaarer
            halv = n // 2
            r = []
            for del_ in (slice(0, halv), slice(halv, n)):
                Zs_h, ns_h = zrank(np.where(gyld, S[del_], np.nan))
                Zy_h, _ = zrank(y[V][del_][:, None])
                r.append((Zs_h * Zy_h[:, 0][:, None]).sum(axis=0) / np.maximum(ns_h, 1))
            mu, sd = null.mean(axis=0), null.std(axis=0)
            for c, sk in enumerate(SK.columns):
                if not gyld[c] or not sd[c] > 0:
                    continue
                z = (rho[c] - mu[c]) / sd[c]
                p = math.erfc(abs(z) / math.sqrt(2))
                rader.append({"skaar": sk, "aksje": sym, "h": k, "n": int(ns[c]), "rho": rho[c], "z": z, "p": p,
                              "p_telt": (np.sum(np.abs(null[:, c] - mu[c]) >= abs(rho[c] - mu[c])) + 1) / (N_BOOT + 1),
                              "rho_1": r[0][c], "rho_2": r[1][c]})
    df = pd.DataFrame(rader)
    df["q"] = np.nan
    for k in H:
        m = df.h == k
        ps = df.loc[m, "p"].values; o = np.argsort(ps)
        qs = ps[o] * len(ps) / (np.arange(len(ps)) + 1)
        qs = np.minimum.accumulate(qs[::-1])[::-1]
        q = np.empty_like(qs); q[o] = np.minimum(qs, 1)
        df.loc[m, "q"] = q
    df["robust"] = (df.q <= Q) & (np.sign(df.rho_1) == np.sign(df.rho)) & (np.sign(df.rho_2) == np.sign(df.rho))
    print(f"   {label}: {len(df)} tester, p<0,05 {int((df.p < 0.05).sum())}, |z|>3 {int((df.z.abs() > 3).sum())}, "
          f"|z|>4 {int((df.z.abs() > 4).sum())}, q<=0,10 {int((df.q <= Q).sum())}, robuste {int(df.robust.sum())}")
    return df

print("\n3. TESTENE\n")
RES = kjor(SKv, "ekte skaarer")
PLA = kjor(np.roll(SKv, 120, axis=0), "placebo (skaarer forskjoevet 120 mnd)")

INSTR = {}
for f in glob.glob("segments/*.json"):
    s = json.load(open(f, encoding="utf-8"))
    for i in s.get("instrumenter") or []:
        INSTR.setdefault(str(i.get("ticker", "")).replace(".OL", ""), set()).add(s["id"])

print("\n4. RESULTAT PER HORISONT\n")
for k in H:
    d = RES[RES.h == k]; pl = PLA[PLA.h == k]
    rob = d[d.robust].sort_values("p")
    print(f"   {k}: robuste {len(rob)} (positive {int((rob.rho > 0).sum())}), placebo {int(pl.robust.sum())};  "
          f"|z|>3 ekte {int((d.z.abs() > 3).sum())} av {len(d)}, placebo {int((pl.z.abs() > 3).sum())} av {len(pl)}")
    for _, x in rob.head(15).iterrows():
        seg = x.skaar.split(":")[0]
        pa = "paa bordet" if seg in INSTR.get(x.aksje, set()) else ""
        print(f"      {x.aksje:8s} {str(NAVN.get(x.aksje, ''))[:24]:24s} {x.skaar:16s} rho {x.rho:+.2f} "
              f"(halvdeler {x.rho_1:+.2f}/{x.rho_2:+.2f}) n {x.n} p {x.p:.3f} q {x.q:.3f} {pa}")
    print()
RES["navn"] = RES.aksje.map(NAVN)
RES.to_csv("sonder/oslo_askaar.csv", index=False)
print("   Alle tester lagret i sonder/oslo_askaar.csv")
