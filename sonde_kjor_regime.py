# ---------------------------------------------------------------------------
# sonde_kjor_regime: kjenner maalene for regime igjen de store makrohendelsene?
# (Frodes bestilling 15.10.2026, steg 1 av regimepanelet)
#
# Fire dimensjoner, alle maanedlige og punkt i tid (persentil mot det som var
# kjent da, minst 60 mnd):
#   SJOKK     absorpsjon: andelen av variasjonen i ukeavkastningen til
#             papirene og fondene paa bordet som forklares av foerste
#             hovedkomponent, rullende 13 uker (minst 15 papirer). Snittet av
#             parvise korrelasjoner vises ved siden av, og korrelasjonen
#             mellom raavarene (maanedsendring i realpris, rullende 12 mnd).
#             VIX (Yahoo) og Baa mot tiaarig rente (FRED BAA10Y) som kontroll.
#   VEKST     bredde: andel raavaresegmenter med hoeyere realpris enn for
#             12 mnd siden. Kobber mot gull, endring 12 mnd. Rentekurven
#             10 mot 2 aar (FRED T10Y2Y).
#   BILLIG    median A (raa) over raavarene, andel i bunnsonen (A og Ad 80),
#             spredning (kvartilavstand i A).
#   LIKVIDITET (Frodes tillegg 15.10.2026, beskrivende): Feds netto
#             likviditet = balansen (WALCL) minus statskassens konto (WTREGEN)
#             minus reverse repo (RRPONTSYD), nivaa og endring 13 uker; og
#             sentralbankbalansene i USD (Fed, ECB, BoJ), endring 6 mnd.
#             Fra 2002 og 2003; reverse repo er naer null foer 2021 og igjen
#             fra 2025.
# Analog: dagens verdier sammenlignes med alle tidligere maaneder (standardisert
# avstand over absorpsjon, bredde, median A, VIX, kreditt og rentekurve), og de
# naermeste vises. Likviditet er ikke med i analogen (for kort historikk).
#
# KRITERIER (satt foer kjoering, 15.10.2026)
#   SJOKK holder hvis absorpsjonen (punkt-i-tid-persentil) er 95 eller mer
#     innen en maaned fra 2008-10, 2011-08 og 2020-03 (alle tre), OG hoeyst
#     halvparten av maanedene paa 95 eller mer ligger mer enn tre maaneder fra
#     listen over kjente stressperioder under.
#   VEKST holder hvis bredden i snitt er over 0,6 i 2003-01..2008-06 og
#     2021-01..2022-06, og under 0,4 i 2001-06..2002-06, 2008-11..2009-06,
#     2015-01..2016-03 og 2020-03..2020-08.
#   BILLIG holder hvis median A er i oeverste tiendedel (av maanedene fra
#     1990) innen tre maaneder fra 2009-02, 2016-01 og 2020-04, og i nederste
#     tiendedel innen tre maaneder fra 2008-06 og 2022-06.
#   LIKVIDITET har intet kriterium (for faa sykluser).
# Holder ikke en dimensjon, er den ikke verdt et felt i panelet.
# Skriver ingenting til dashbordet. Utdata sonder/regime.csv.
# ---------------------------------------------------------------------------

import io, os, time
import numpy as np
import pandas as pd
import requests

from instrumenter import INSTR

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
FONDER = ["XOP", "GDX", "COPX", "XME", "MOO", "IEZ", "OIH", "SPY"]
STRESS = ["1997-10", "1998-08", "1998-09", "1998-10", "2001-09", "2002-07", "2002-08", "2002-09", "2002-10",
          "2008-09", "2008-10", "2008-11", "2008-12", "2009-01", "2009-02", "2009-03", "2010-05",
          "2011-08", "2011-09", "2011-10", "2015-08", "2016-01", "2016-02", "2018-02", "2018-10",
          "2018-11", "2018-12", "2020-02", "2020-03", "2020-04", "2022-02", "2022-03", "2022-06",
          "2022-09", "2022-10", "2023-03", "2025-04"]
HENDELSER = {"1998-09": "LTCM og Russland", "2001-09": "11. september", "2002-07": "etter IT-boblen",
             "2008-10": "finanskrisen", "2011-08": "eurokrisen og USAs kredittvurdering",
             "2015-08": "Kina og oljefallet", "2016-01": "raavarebunnen", "2018-12": "renteoppgang og handelskrig",
             "2020-03": "covid", "2022-06": "inflasjon og renteoppgang", "2022-03": "Ukraina",
             "2008-06": "raavaretoppen", "2022-05": "raavaretoppen etter Ukraina", "2025-04": "tollsjokket"}
MIN = 60


def get(url, **kw):
    for i in range(4):
        try:
            r = requests.get(url, timeout=60, **kw)
            if r.status_code == 200:
                return r
        except requests.RequestException:
            pass
        time.sleep(3 * (i + 1))
    raise RuntimeError(f"ingen svar: {url[:70]}")


def fred(sid):
    if os.environ.get("UTEN_FRED"):          # lokal proeve; FRED svarer fra Actions
        raise RuntimeError("FRED hoppet over")
    r = get("https://fred.stlouisfed.org/graph/fredgraph.csv", params={"id": sid},
            headers={"User-Agent": "Syklusbordet frode@h-k.no"})
    d = pd.read_csv(io.StringIO(r.text))
    d.columns = ["t", "v"]
    s = pd.Series(pd.to_numeric(d.v, errors="coerce").values, index=pd.to_datetime(d.t)).dropna()
    return s


def dag(sym):
    r = get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}",
            params={"period1": 0, "period2": int(time.time()), "interval": "1d", "events": "div,split"}, headers=UA)
    res = r.json()["chart"]["result"][0]
    if (res.get("meta") or {}).get("dataGranularity") != "1d":
        raise ValueError("ikke dagskurser")
    adj = res["indicators"].get("adjclose", [{}])[0].get("adjclose") or res["indicators"]["quote"][0]["close"]
    s = pd.Series(adj, index=pd.to_datetime(res["timestamp"], unit="s")).dropna()
    time.sleep(0.3)
    return s[s > 0]


def pit(s, minn=MIN):
    """Punkt-i-tid-persentil 0..100 (hoey = hoeyt mot egen historikk)."""
    v = s.values; o = np.full(len(v), np.nan)
    for i in range(len(v)):
        if np.isfinite(v[i]):
            h = v[: i + 1]; h = h[np.isfinite(h)]
            if len(h) >= minn:
                o[i] = (h <= v[i]).mean() * 100
    return pd.Series(o, index=s.index)


def A_raa(v):
    o = np.full(len(v), np.nan)
    for i in range(59, len(v)):
        o[i] = (v[: i + 1] <= v[i]).mean()
    return (1 - o) * 100


def A_det(v):
    o = np.full(len(v), np.nan)
    for i in range(59, len(v)):
        y = v[: i + 1]; t = np.arange(i + 1)
        b, a = np.polyfit(t, y, 1); r = y - (a + b * t)
        o[i] = (r <= r[i]).mean()
    return (1 - o) * 100


def naer(idx, maaneder, k):
    m = [pd.Period(x, "M") for x in maaneder]
    return pd.Series([any(abs((t - x).n) <= k for x in m) for t in idx], index=idx)


# ------------------------------------------------------------------ raavarer
p = pd.read_csv("serier/priser_mnd.csv")
p = p[~p.segment.str.startswith("ship_")]
real = p.pivot(index="t", columns="segment", values="real").astype(float)
real.index = pd.PeriodIndex(real.index, freq="M")
real = real.sort_index()
A, Ad = {}, {}
for s in real:
    x = real[s].dropna(); lv = np.log(x.values)
    A[s] = pd.Series(A_raa(lv), index=x.index); Ad[s] = pd.Series(A_det(lv), index=x.index)
A = pd.DataFrame(A).reindex(real.index); Ad = pd.DataFrame(Ad).reindex(real.index)
M = pd.DataFrame(index=real.index)
M["median_A"] = A.median(axis=1)
M["andel_bunn"] = ((A >= 80) & (Ad >= 80)).sum(axis=1) / A.notna().sum(axis=1)
M["spredning_A"] = A.quantile(0.75, axis=1) - A.quantile(0.25, axis=1)
d12 = np.log(real) - np.log(real.shift(12))
M["bredde"] = (d12 > 0).sum(axis=1) / d12.notna().sum(axis=1)
M["kobber_gull_12m"] = 100 * (np.log(real.kobber / real.gold) - np.log(real.kobber / real.gold).shift(12))
dm = np.log(real).diff()


def snittkorr(df):
    c = df.dropna(axis=1).corr().values
    n = c.shape[0]
    return np.nan if n < 5 else (c.sum() - n) / (n * (n - 1))


M["korr_raavarer"] = [snittkorr(dm.iloc[max(0, i - 11): i + 1]) if i >= 11 else np.nan for i in range(len(dm))]
M = M[M.index >= pd.Period("1965-01", "M")]
print(f"Raavarer: {real.shape[1]} segmenter, {M.index[0]} til {M.index[-1]}")

# ------------------------------------------------------------------ papirer
syms = sorted({x[0] for v in INSTR.values() for x in v} | set(FONDER))
uke = {}
for s in syms:
    try:
        uke[s] = dag(s).resample("W-FRI").last()
    except Exception as e:
        print(f"   {s}: {type(e).__name__}")
R = np.log(pd.DataFrame(uke)).diff()
R = R[R.index >= "1990-01-01"]
print(f"Papirer og fond: {R.shape[1]} med kurs, uker {R.index[0].date()} til {R.index[-1].date()}")
absorp, pkorr, npap = [], [], []
for i in range(len(R)):
    w = R.iloc[max(0, i - 12): i + 1].dropna(axis=1, thresh=13)
    w = w.dropna()
    w = w.loc[:, (w.std() > 1e-8) & ((w != 0).sum() >= 8)]   # kurser som staar stille
    if i < 12 or w.shape[1] < 15 or len(w) < 13:
        absorp.append(np.nan); pkorr.append(np.nan); npap.append(w.shape[1]); continue
    c = np.corrcoef(w.values.T)
    ev = np.linalg.eigvalsh(c)
    absorp.append(ev[-1] / ev.sum()); n = c.shape[0]
    pkorr.append((c.sum() - n) / (n * (n - 1))); npap.append(n)
U = pd.DataFrame({"absorpsjon": absorp, "korr_papirer": pkorr, "n_papirer": npap}, index=R.index)
Um = U.resample("ME").last(); Um.index = Um.index.to_period("M")
M = M.join(Um, how="outer")

# ------------------------------------------------------------------ marked og FRED
def mnd(s, how="last"):
    m = s.resample("ME").last() if how == "last" else s.resample("ME").mean()
    m.index = m.index.to_period("M")
    return m


try:
    M["vix"] = mnd(dag("^VIX"), "mean")
except Exception as e:
    print(f"   VIX: {type(e).__name__}")
for sid, navn in (("BAA10Y", "kreditt"), ("T10Y2Y", "rentekurve")):
    try:
        M[navn] = mnd(fred(sid), "mean")
    except Exception as e:
        print(f"   {sid}: {type(e).__name__}: {str(e)[:60]}")
lik_ok = True
try:
    walcl, tga, rrp = fred("WALCL") / 1000, fred("WTREGEN") / 1000, fred("RRPONTSYD")
    print(f"   enheter, siste (mrd USD): Fed-balanse {walcl.iloc[-1]:.0f}, statskassen {tga.iloc[-1]:.0f}, "
          f"reverse repo {rrp.iloc[-1]:.0f}")
    uk = pd.concat([walcl.resample("W-WED").last(), tga.resample("W-WED").last(),
                    rrp.resample("W-WED").last().fillna(0)], axis=1).ffill().dropna(subset=[0, 1])
    uk.columns = ["fed", "tga", "rrp"]
    uk["netto"] = uk.fed - uk.tga - uk.rrp.fillna(0)
    uk["netto_13u"] = 100 * (np.log(uk.netto) - np.log(uk.netto.shift(13)))
    M["fed_netto_mrd"] = mnd(uk.netto); M["fed_netto_13u_pst"] = mnd(uk.netto_13u)
    M["rrp_mrd"] = mnd(uk.rrp)
    ecb, eur = fred("ECBASSETSW"), fred("DEXUSEU")
    boj, jpy = fred("JPNASSETS"), fred("DEXJPUS")
    glob = pd.DataFrame({"fed": mnd(walcl), "ecb": mnd(ecb) / 1000 * mnd(eur, "mean"),
                         "boj": mnd(boj) / 10 / mnd(jpy, "mean")}).dropna()
    glob["sum"] = glob.sum(axis=1)
    print(f"   sentralbanker siste (mrd USD): Fed {glob.fed.iloc[-1]:.0f}, ECB {glob.ecb.iloc[-1]:.0f}, "
          f"BoJ {glob.boj.iloc[-1]:.0f}")
    M["sb_sum_mrd"] = glob["sum"]
    M["sb_6m_pst"] = 100 * (np.log(glob["sum"]) - np.log(glob["sum"].shift(6)))
except Exception as e:
    lik_ok = False
    print(f"   likviditet: {type(e).__name__}: {str(e)[:80]}")

M = M.sort_index()
for k in ("absorpsjon", "korr_papirer", "korr_raavarer", "vix", "kreditt"):
    if k in M:
        M[f"{k}_pct"] = pit(M[k])
M["median_A_dec"] = np.nan
fra90 = M.index >= pd.Period("1990-01", "M")
q10, q90 = M.median_A[fra90].quantile([0.1, 0.9])

# ------------------------------------------------------------------ kriteriene
print("\n1. SJOKK (absorpsjon, punkt-i-tid-persentil)\n")
for t in ("2008-10", "2011-08", "2020-03"):
    w = M.loc[pd.Period(t, "M") - 1: pd.Period(t, "M") + 1]
    print(f"   {t} ({HENDELSER.get(t, '')}): absorpsjon {w.absorpsjon.max():.2f}, persentil maks "
          f"{w.absorpsjon_pct.max():.0f}; snittkorr papirer {w.korr_papirer.max():.2f}; VIX-persentil "
          f"{w.vix_pct.max() if 'vix_pct' in w else float('nan'):.0f}")
treff = all(M.loc[pd.Period(t, "M") - 1: pd.Period(t, "M") + 1].absorpsjon_pct.max() >= 95
            for t in ("2008-10", "2011-08", "2020-03"))
topp = M[M.absorpsjon_pct >= 95]
ute = ~naer(topp.index, STRESS, 3)
print(f"   maaneder paa 95 eller mer: {len(topp)}, utenfor kjent stress: {int(ute.sum())} "
      f"({', '.join(str(t) for t in topp.index[ute.values])})")
sjokk_ok = treff and ute.mean() <= 0.5
print(f"   -> SJOKK {'HOLDER' if sjokk_ok else 'HOLDER IKKE'}")
for k in ("korr_papirer", "korr_raavarer", "vix"):
    if f"{k}_pct" in M:
        t3 = [M.loc[pd.Period(t, 'M') - 1: pd.Period(t, 'M') + 1][f"{k}_pct"].max() for t in ("2008-10", "2011-08", "2020-03")]
        tp = M[M[f"{k}_pct"] >= 95]; u = (~naer(tp.index, STRESS, 3)).mean() if len(tp) else np.nan
        print(f"   kontroll {k:14}: persentil 2008/2011/2020 {t3[0]:.0f}/{t3[1]:.0f}/{t3[2]:.0f}, "
              f"{len(tp)} mnd paa 95+, andel utenfor stress {u:.0%}")

print("\n2. VEKST (bredde: andel raavarer opp over 12 mnd)\n")
vok = True
for a, b, op in (("2003-01", "2008-06", ">"), ("2021-01", "2022-06", ">"), ("2001-06", "2002-06", "<"),
                 ("2008-11", "2009-06", "<"), ("2015-01", "2016-03", "<"), ("2020-03", "2020-08", "<")):
    v = M.bredde.loc[pd.Period(a, "M"): pd.Period(b, "M")].mean()
    ok = v > 0.6 if op == ">" else v < 0.4
    vok &= ok
    print(f"   {a}..{b}: {v:.2f} (krav {op} {'0,6' if op == '>' else '0,4'}) {'ok' if ok else 'NEI'}")
print(f"   -> VEKST {'HOLDER' if vok else 'HOLDER IKKE'}")

print(f"\n3. BILLIG (median A; oeverste tiendedel fra 1990 >= {q90:.1f}, nederste <= {q10:.1f})\n")
bok = True
for t, hoy in (("2009-02", True), ("2016-01", True), ("2020-04", True), ("2008-06", False), ("2022-06", False)):
    w = M.median_A.loc[pd.Period(t, "M") - 3: pd.Period(t, "M") + 3]
    ok = (w.max() >= q90) if hoy else (w.min() <= q10)
    bok &= ok
    print(f"   {t} ({HENDELSER.get(t, '')}): {'maks' if hoy else 'min'} {w.max() if hoy else w.min():.1f} {'ok' if ok else 'NEI'}")
print(f"   -> BILLIG {'HOLDER' if bok else 'HOLDER IKKE'}")

print("\n4. LIKVIDITET (beskrivende)\n")
if lik_ok:
    for t in ("2008-12", "2011-06", "2014-10", "2018-12", "2019-09", "2020-06", "2021-12", "2022-12", "2023-12",
              "2024-12", str(M.dropna(subset=["fed_netto_mrd"]).index[-1])):
        hit = M[M.index.astype(str) == t]
        r = hit.iloc[0] if len(hit) and pd.notna(hit.iloc[0].get("fed_netto_mrd")) else None
        if r is not None:
            print(f"   {t}: Fed netto {r.fed_netto_mrd:7.0f} mrd (13 uker {r.fed_netto_13u_pst:+5.1f} %), reverse repo "
                  f"{r.rrp_mrd:6.0f}, sentralbanker {r.sb_sum_mrd:7.0f} mrd (6 mnd {r.sb_6m_pst:+5.1f} %)")

print("\n5. I DAG OG ANALOGER\n")
siste = M.dropna(subset=["absorpsjon", "bredde", "median_A"]).index[-1]
r = M.loc[siste]
print(f"   {siste}: absorpsjon {r.absorpsjon:.2f} (persentil {r.absorpsjon_pct:.0f}), snittkorr papirer "
      f"{r.korr_papirer:.2f}, VIX-persentil {r.get('vix_pct', np.nan):.0f}, kreditt {r.get('kreditt', np.nan):.2f}, "
      f"rentekurve {r.get('rentekurve', np.nan):.2f}")
print(f"   bredde {r.bredde:.2f}, kobber mot gull 12 mnd {r.kobber_gull_12m:+.1f} %, median A {r.median_A:.1f}, "
      f"andel i bunnsonen {r.andel_bunn:.2f}, spredning {r.spredning_A:.1f}")
dims = [k for k in ("absorpsjon_pct", "bredde", "median_A", "vix_pct", "kreditt_pct", "rentekurve") if k in M]
X = M[dims].dropna()
Z = (X - X.mean()) / X.std()
dist = np.sqrt(((Z - Z.loc[siste]) ** 2).sum(axis=1))
dist = dist[dist.index <= siste - 24].sort_values()
print(f"   naermeste maaneder (over {', '.join(dims)}), minst 24 mnd tilbake:")
vist = []
for t, d in dist.items():
    if any(abs((t - v).n) < 6 for v in vist):
        continue
    vist.append(t)
    nh = min(HENDELSER, key=lambda h: abs((pd.Period(h, "M") - t).n))
    avst = abs((pd.Period(nh, "M") - t).n)
    print(f"      {t}  avstand {d:.2f}" + (f"  (naer {HENDELSER[nh]}, {nh})" if avst <= 6 else ""))
    if len(vist) == 8:
        break

print(f"\n6. OPPSUMMERING: sjokk {'holder' if sjokk_ok else 'holder ikke'}, vekst {'holder' if vok else 'holder ikke'}, "
      f"billig {'holder' if bok else 'holder ikke'}, likviditet beskrivende")
M.reset_index(names="t").to_csv("sonder/regime.csv", index=False)
print("Lagret sonder/regime.csv")
