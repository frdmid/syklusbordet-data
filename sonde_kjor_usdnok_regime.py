# ---------------------------------------------------------------------------
# sonde_kjor_usdnok_regime: hvordan beveger USD/NOK seg i ulike makroregimer,
# og finnes det et tidlig varsel for posisjonering i USD mot NOK? (Frodes
# bestilling 03.11.2026; Frode maaler i NOK, og de fleste papirene paa bordet
# er i USD eller CAD)
#
# Utfall: endring i log USD/NOK fra maanedsslutt t til maanedsslutt t + h
#   (h 3, 6, 12). Positiv = dollaren styrker seg mot kronen = godt for en
#   NOK-investor med dollareksponering. Norges Bank daglig fra 1980.
# VARSLER i maaned t (punkt i tid, valgt foer kjoering), forventet retning:
#   W1 uro            VIX (maanedssnitt) i oeverste tredjedel        USD opp
#   W2 aksjefall      S&P 500 minst 10 % under 12 mnd toppen        USD opp
#   W3 oljefall       Brent 3 mnd endring i nederste tredjedel       USD opp
#   W4 bred nedgang   40 % eller faerre av raavarene i oppgang       USD opp
#   W5 dollartrend    DXY 3 mnd endring i oeverste tredjedel         USD opp
#   W6 egen trend     USD/NOK 3 mnd endring i oeverste tredjedel     USD opp
#   W7 dyr dollar     USD/NOK i oeverste tredjedel mot siste 10 aar  USD ned
#   W8 rentefordel    3 mnd T-bill (^IRX) minus styringsrenten i
#                     Norge i oeverste tredjedel                     USD opp
#   W9 samlet         minst 3 av W1 til W6 og W8                     USD opp
#   Tredjedeler mot det som var kjent da (minst 36 mnd).
# Data: Norges Bank (USD/NOK daglig, styringsrenten fra 1991), Yahoo (^VIX,
#   ^GSPC, DX-Y.NYB, ^IRX), serier/priser_mnd.csv (Brent, bredde).
#
# KRITERIER (satt foer kjoering, 03.11.2026). Et varsel holder paa horisont h
# hvis, paa 1993-01 til 2014-12 (kronen flyter fra desember 1992):
#   (a) snittet i varselmaanedene minus snittet i andre maaneder er minst
#       1,5 prosentpoeng per 3 mnd i forventet retning,
#   (b) p under 0,05 ensidig i forventet retning mot sirkulaert forskjoevet
#       varselserie (minst 24 mnd, 2000 trekk),
#   (c) samme fortegn i begge halvdelene,
#   (d) minst 5 episoder (ny etter 12 mnd uten varsel), og
#   (e) Benjamini-Hochberg paa 10 % over 9 varsler x 3 horisonter.
# Beskrivende: USD/NOK etter vekstregime og uro, og 2015 til 2026.
# Skriver ingenting til dashbordet. Utdata sonder/usdnok_regime.csv.
# ---------------------------------------------------------------------------

import io, time
import numpy as np
import pandas as pd
import requests

rng = np.random.default_rng(20261103)
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0 Safari/537.36"}
FRA, TIL = pd.Period("1993-01", "M"), pd.Period("2014-12", "M")
NYTT = (pd.Period("2015-01", "M"), pd.Period("2026-12", "M"))


def nb(sti):
    r = requests.get(f"https://data.norges-bank.no/api/data/{sti}?format=csv&startPeriod=1980&locale=en",
                     headers={"User-Agent": "Syklusbordet"}, timeout=120)
    d = pd.read_csv(io.StringIO(r.text), sep=";")
    s = pd.Series(pd.to_numeric(d.OBS_VALUE, errors="coerce").values, index=pd.to_datetime(d.TIME_PERIOD)).dropna()
    return s.sort_index()


def yahoo(sym):
    r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}",
                     params={"period1": 0, "period2": int(time.time()), "interval": "1d"}, headers=UA, timeout=60)
    res = r.json()["chart"]["result"][0]
    s = pd.Series(res["indicators"]["quote"][0]["close"], index=pd.to_datetime(res["timestamp"], unit="s")).dropna()
    time.sleep(0.3)
    return s


def mnd_slutt(s):
    m = s.resample("ME").last(); m.index = m.index.to_period("M"); return m


def mnd_snitt(s):
    m = s.resample("ME").mean(); m.index = m.index.to_period("M"); return m


def tredjedel(s, minn=36, vindu=None):
    v = s.values; ut = np.full(len(v), np.nan)
    for i in range(len(v)):
        h = v[: i + 1] if vindu is None else v[max(0, i + 1 - vindu): i + 1]
        h = h[np.isfinite(h)]
        if np.isfinite(v[i]) and len(h) >= minn:
            q = (h <= v[i]).mean()
            ut[i] = 0 if q <= 1 / 3 else (2 if q > 2 / 3 else 1)
    return pd.Series(ut, index=s.index)


# ------------------------------------------------------------------ data
usdnok = mnd_slutt(nb("EXR/B.USD.NOK.SP"))
lu = np.log(usdnok)
kpra = mnd_snitt(nb("IR/B.KPRA.SD.R"))
vix = mnd_snitt(yahoo("^VIX"))
spx = mnd_slutt(yahoo("^GSPC"))
dxy = mnd_slutt(yahoo("DX-Y.NYB"))
irx = mnd_snitt(yahoo("^IRX"))
p = pd.read_csv("serier/priser_mnd.csv"); p = p[~p.segment.str.startswith("ship_")]
real = p.pivot(index="t", columns="segment", values="real").astype(float).sort_index()
real.index = pd.PeriodIndex(real.index, freq="M")
brent = np.log(p[p.segment == "brent"].set_index("t").nom.astype(float)); brent.index = pd.PeriodIndex(brent.index, freq="M")
d12 = np.log(real) - np.log(real.shift(12)); n = d12.notna().sum(axis=1)
bredde = ((d12 > 0).sum(axis=1) / n)[n >= 5]

idx = lu.index
def paa(x):
    return x.reindex(idx)
W = pd.DataFrame(index=idx)
W["W1 uro"] = paa(tredjedel(vix)) == 2
W["W2 aksjefall"] = paa(spx / spx.rolling(12).max() - 1 <= -0.10)
W["W3 oljefall"] = paa(tredjedel((brent - brent.shift(3)).dropna())) == 0
W["W4 bred nedgang"] = paa(bredde <= 0.4)
W["W5 dollartrend"] = paa(tredjedel((np.log(dxy) - np.log(dxy.shift(3))).dropna())) == 2
W["W6 egen trend"] = paa(tredjedel((lu - lu.shift(3)).dropna())) == 2
W["W7 dyr dollar"] = paa(tredjedel(lu, minn=60, vindu=120)) == 2
W["W8 rentefordel"] = paa(tredjedel((irx - kpra).dropna())) == 2
gyld = pd.DataFrame({"W1": paa(tredjedel(vix)).notna(), "W3": paa(tredjedel((brent - brent.shift(3)).dropna())).notna(),
                     "W8": paa(tredjedel((irx - kpra).dropna())).notna()})
W = W.fillna(False).astype(bool)
W["W9 samlet"] = W[["W1 uro", "W2 aksjefall", "W3 oljefall", "W4 bred nedgang", "W5 dollartrend", "W6 egen trend",
                    "W8 rentefordel"]].sum(axis=1) >= 3
RETNING = {k: (-1 if k.startswith("W7") else 1) for k in W.columns}
KREVER = {"W1 uro": "W1", "W3 oljefall": "W3", "W8 rentefordel": "W8"}


def episoder(b):
    n, forr = 0, None
    for i in np.where(b)[0]:
        if forr is None or i - forr > 12:
            n += 1
        forr = i
    return n


def analyse(navn, h, fra, til):
    y = (lu.shift(-h) - lu)
    m = (idx >= fra) & (idx <= til) & y.notna().values
    if navn in KREVER:
        m &= gyld[KREVER[navn]].values
    b, yy = W[navn].values[m], y.values[m]
    if b.sum() < 3 or (~b).sum() < 3:
        return None
    diff = yy[b].mean() - yy[~b].mean()
    r = RETNING[navn]
    null = []
    for _ in range(2000):
        s = np.roll(b, rng.integers(24, len(b) - 24))
        if s.sum() and (~s).sum():
            null.append(yy[s].mean() - yy[~s].mean())
    null = np.array(null)
    pv = (np.sum(r * null >= r * diff) + 1) / (len(null) + 1)
    mid = len(b) // 2; hv = []
    for sl in (slice(0, mid), slice(mid, None)):
        bb, ys = b[sl], yy[sl]
        hv.append(ys[bb].mean() - ys[~bb].mean() if bb.sum() and (~bb).sum() else np.nan)
    return dict(snitt=yy[b].mean(), andre=yy[~b].mean(), diff=diff, p=pv, h1=hv[0], h2=hv[1], n=int(b.sum()),
                ep=episoder(b), treff=float((np.sign(yy[b]) == r).mean()))


def pp(x):
    return "   -  " if x is None or not np.isfinite(x) else f"{100*x:+6.1f}"


print(f"USD/NOK {usdnok.index[0]} til {usdnok.index[-1]}, siste {usdnok.iloc[-1]:.3f}\n")
print("I DAG (siste maaned med data for alle):")
siste = idx[-1]
for k in W.columns:
    print(f"   {k:18} {'PAA' if W.loc[siste, k] else 'av'}")
print()

rader, tester = [], []
for h in (3, 6, 12):
    print(f"==================== h = {h} mnd (endring i log USD/NOK, positiv = sterkere dollar)")
    for navn in W.columns:
        for pn, (fra, til) in {"1993-2014": (FRA, TIL), "2015-2026": NYTT}.items():
            a = analyse(navn, h, fra, til)
            if a is None:
                print(f"   {navn:18} {pn} for faa maaneder"); continue
            rader.append({"varsel": navn, "h": h, "periode": pn, **a})
            print(f"   {navn:18} {pn}  varsel {pp(a['snitt'])} %  andre {pp(a['andre'])} %  forskjell {pp(a['diff'])} pp"
                  f"  p {a['p']:.3f}  halvdeler {pp(a['h1'])}/{pp(a['h2'])}  n {a['n']:3}  ep {a['ep']:2}  riktig retning {100*a['treff']:3.0f} %")
            if pn == "1993-2014":
                r = RETNING[navn]
                ok = (r * a["diff"] >= 0.015 * h / 3 and a["p"] < 0.05 and r * a["h1"] > 0 and r * a["h2"] > 0 and a["ep"] >= 5)
                tester.append({"test": f"{navn}, h {h}", "p": a["p"], "ok": ok})
    print()

T = pd.DataFrame(tester).sort_values("p").reset_index(drop=True); m = len(T)
g = max([i + 1 for i in range(m) if T.p[i] <= 0.10 * (i + 1) / m], default=0)
T["bh"] = [i < g for i in range(m)]
print("AVGJOERELSE (1993 til 2014)\n")
for _, t in T.sort_values("test").iterrows():
    print(f"   {t.test:24}: {'HOLDER' if (t.ok and t.bh) else 'holder ikke'} (krav a til d {'ja' if t.ok else 'nei'}, p {t.p:.3f}, BH {'ja' if t.bh else 'nei'})")

print("\nBESKRIVENDE: USD/NOK etter vekstregime og uro (snitt neste 3 og 12 mnd, prosent log, 1993 til 2026)")
reg = pd.Series(np.where(paa(bredde) >= 0.6, "bred oppgang", np.where(paa(bredde) <= 0.4, "bred nedgang", "noeytral")), index=idx)
reg[paa(bredde).isna()] = None
uro = W["W1 uro"].map({True: "uro", False: "rolig"})
for h in (3, 12):
    y = lu.shift(-h) - lu
    d = pd.DataFrame({"reg": reg, "uro": uro, "y": y})
    d = d[(d.index >= FRA) & d.y.notna() & d.reg.notna()]
    print(f"   h {h} mnd")
    for (a, b), gg in d.groupby(["reg", "uro"]):
        print(f"      {a:13} {b:6} n {len(gg):3}  snitt {pp(gg.y.mean())} %  median {pp(gg.y.median())} %  dollar opp i {100*(gg.y > 0).mean():3.0f} %")
pd.DataFrame(rader).to_csv("sonder/usdnok_regime.csv", index=False)
print("\nLagret sonder/usdnok_regime.csv")
