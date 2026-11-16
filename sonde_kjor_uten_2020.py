# ---------------------------------------------------------------------------
# sonde_kjor_uten_2020: hvor mye av det prosjektet tror paa, er egentlig 2020?
# (Frodes bestilling 16.11.2026, etter sonde_kjor_vvix_regime samme dag.)
#
# BAKGRUNN. Fire ganger har prosjektet funnet at et maal virker, og at hele
# virkningen ligger i den ene vendingen i 2020: papirene i bunnsonen
# (backtesten 28.09.2026, «baaret av 2008/09 og 2020»), hoey VIX etter 2015
# (sonden 03.11.2026, «mest 2020»), holdetidene (03.11.2026, «uten 2020 laa
# papirene under world paa 3 til 12 mnd») og VVIX (16.11.2026, der forskjellen
# gikk fra +75 til -2 prosentpoeng uten 2020). Denne sonden gjor samme
# sjekk systematisk paa det som FAKTISK baerer vekt i dag.
#
# HVA EN SLIK SJEKK KAN OG IKKE KAN. Den kan vise at en paastand er skjoer.
# Den kan IKKE etablere noe: aa ta ut et aar i ettertid er ikke en ny test, og
# et maal som holder uten 2020 er ikke dermed bekreftet. Sonden har altsaa
# bare ett legitimt utfall per paastand: skjoer eller ikke skjoer.
#
# KRITERIUM (satt foer kjoering 16.11.2026). En paastand kalles
# 2020-AVHENGIG hvis, naar signalmaanedene i kalenderaaret 2020 tas ut,
# forskjellen enten
#   (a) skifter fortegn, eller
#   (b) krymper til under halvparten av sin opprinnelige stoerrelse.
# Ellers kalles den ikke 2020-avhengig. Grensen flyttes ikke etter kjoering.
#
# HVA SOM TESTES. De tre paastandene som har evidensgrad «middels» i
# handel.json, altsaa de eneste som baerer vekt, pluss papirportefoeljen som
# staar oeverst paa dashbordet:
#   1. Championens bunnsone paa raavarens egen realpris. Merk at det
#      avgjoerende vinduet i evidensteksten er 1965 til 2014, som ikke
#      inneholder 2020; det kontrolleres her, og hele perioden vises ved siden.
#   2. challenger_bred_nedgang_v1: bunnsone i bred nedgang (40 % eller faerre
#      raavarer i oppgang) mot bunnsone ellers. Nivaaene her kan avvike fra
#      regimesonden 15.10.2026, som regnet paa makroklynger; det som betyr noe
#      er forskjellen med og uten 2020 INNENFOR denne sonden.
#   3. challenger_gull_begge_v1: maanedene der S1 og S2 staar samtidig, maalt
#      paa gruvefondene over 6 maaneder mot MSCI World, som Challengeren selv
#      gjoer. Signalhistorikken leses av miners.json.
#   4. Papirportefoeljen i handel.json: de 13 posisjonene mot MSCI World, med
#      og uten de fire fra 2020. Tallene leses som de staar, ingen ny
#      simulering.
#
# Utfall for 1 og 2 er endring i log realpris for raavaren, for 3 og 4 er det
# papirenes avkastning, slik de respektive paastandene selv er formulert.
# Skriver ingenting til dashbordet og ingenting til shadow.
# Utdata sonder/uten_2020.csv.
# ---------------------------------------------------------------------------

import json
import time

import numpy as np
import pandas as pd
import requests

rng = np.random.default_rng(20261116)
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
MIN_HIST = 60
HORISONTER = (3, 6, 9, 12, 24)
AAR_UT = 2020
TIL = pd.Period("2014-12", "M")
BRED = 0.40


def expanding_pct(v):
    out = np.full(len(v), np.nan)
    for i in range(MIN_HIST - 1, len(v)):
        out[i] = (v[: i + 1] <= v[i]).sum() / (i + 1)
    return (1 - out) * 100


def expanding_pct_detrend(v):
    out = np.full(len(v), np.nan)
    for i in range(MIN_HIST - 1, len(v)):
        y = v[: i + 1]; t = np.arange(i + 1)
        b, a = np.polyfit(t, y, 1); r = y - (a + b * t)
        out[i] = (r <= r[i]).sum() / len(r)
    return (1 - out) * 100


def pp(x):
    return "   -  " if x is None or not np.isfinite(x) else f"{100 * x:+6.1f}"


def dom(med, uten):
    """Kriteriet i toppen: fortegnsskifte eller mindre enn halvparten."""
    if med is None or uten is None or not np.isfinite(med) or not np.isfinite(uten):
        return "kan ikke avgjoeres"
    if abs(med) < 1e-9:
        return "ingen forskjell aa krympe"
    if np.sign(uten) != np.sign(med):
        return "2020-AVHENGIG (fortegnsskifte)"
    if abs(uten) < abs(med) / 2:
        return f"2020-AVHENGIG (krympet til {100 * abs(uten) / abs(med):.0f} %)"
    return f"ikke 2020-avhengig (beholder {100 * abs(uten) / abs(med):.0f} %)"


rader = []
print("sonde_kjor_uten_2020")
print("Kriteriet staar i toppen av fila og er satt foer kjoering.\n")

# ------------------------------------------------------------------ grunnlaget
p = pd.read_csv("serier/priser_mnd.csv")
p = p[~p.segment.str.startswith("ship_")]
real = p.pivot(index="t", columns="segment", values="real").astype(float).sort_index()
real.index = pd.PeriodIndex(real.index, freq="M")
lr = np.log(real)
A = pd.DataFrame(np.nan, index=lr.index, columns=lr.columns)
Ad = A.copy()
for c in lr.columns:
    s = lr[c].dropna()
    A.loc[s.index, c] = expanding_pct(s.values)
    Ad.loc[s.index, c] = expanding_pct_detrend(s.values)
SIG = ((A >= 80) & (Ad >= 80)).values
d12 = lr - lr.shift(12)
bredde = (d12 > 0).sum(axis=1) / d12.notna().sum(axis=1)
ute = np.array([d.year == AAR_UT for d in lr.index])
print(f"{lr.shape[1]} raavarer, {lr.index[0]} til {lr.index[-1]}")
print(f"signalmaaneder i alt {int(SIG.sum())}, derav i {AAR_UT}: "
      f"{int(SIG[ute].sum())}\n")


def snitt(mask, h, fra, til, drop2020=False):
    Y = (lr.shift(-h) - lr).values
    rad = (lr.index >= fra) & (lr.index <= til)
    if drop2020:
        rad = rad & ~ute
    m = mask[rad] & np.isfinite(Y[rad])
    return (Y[rad][m].mean(), int(m.sum())) if m.sum() else (np.nan, 0)


# ---------------------------------------------- 1. Championens bunnsone
print("==================== 1. Championens bunnsone, raavarens realpris")
print("   Evidensteksten bruker 1965 til 2014, som ikke inneholder 2020.")
for navn, (fra, til) in {"1965-2014 (avgjorende)": (lr.index[0], TIL),
                         "hele 1965-2026": (lr.index[0], lr.index[-1])}.items():
    print(f"\n   {navn}")
    for h in HORISONTER:
        m_sig, n1 = snitt(SIG, h, fra, til)
        m_ikke, n2 = snitt(~SIG, h, fra, til)
        u_sig, n3 = snitt(SIG, h, fra, til, True)
        u_ikke, n4 = snitt(~SIG, h, fra, til, True)
        med = m_sig - m_ikke if np.isfinite(m_sig) and np.isfinite(m_ikke) else None
        uten = u_sig - u_ikke if np.isfinite(u_sig) and np.isfinite(u_ikke) else None
        rader.append({"del": "1 bunnsone", "periode": navn, "h": h,
                      "med_2020": med, "uten_2020": uten, "n_med": n1, "n_uten": n3})
        print(f"      h {h:2}  signal {pp(m_sig)} % mot ellers {pp(m_ikke)} %"
              f"  forskjell {pp(med)} pp  |  uten 2020 {pp(uten)} pp   {dom(med, uten)}")

# ---------------------------------------------- 2. bred nedgang
print("\n==================== 2. challenger_bred_nedgang_v1")
print(f"   Bunnsone naar {BRED:.0%} eller faerre raavarer er i oppgang, mot bunnsone ellers.")
b = (bredde <= BRED).values
SIG_B = SIG & b[:, None]
SIG_IB = SIG & ~b[:, None]
fra = pd.Period("1995-01", "M")
for h in HORISONTER:
    m_b, n1 = snitt(SIG_B, h, fra, lr.index[-1])
    m_i, n2 = snitt(SIG_IB, h, fra, lr.index[-1])
    u_b, n3 = snitt(SIG_B, h, fra, lr.index[-1], True)
    u_i, n4 = snitt(SIG_IB, h, fra, lr.index[-1], True)
    med = m_b - m_i if np.isfinite(m_b) and np.isfinite(m_i) else None
    uten = u_b - u_i if np.isfinite(u_b) and np.isfinite(u_i) else None
    rader.append({"del": "2 bred nedgang", "periode": "1995-2026", "h": h,
                  "med_2020": med, "uten_2020": uten, "n_med": n1, "n_uten": n3})
    print(f"   h {h:2}  i bred nedgang {pp(m_b)} % (n {n1:3}) mot ellers {pp(m_i)} % (n {n2:3})"
          f"  forskjell {pp(med)} pp  |  uten 2020 {pp(uten)} pp (n {n3:3})   {dom(med, uten)}")

# ---------------------------------------------- 3. gullgruver BEGGE
print("\n==================== 3. challenger_gull_begge_v1, gruvefondene 6 mnd mot MSCI World")


def yahoo_mnd(sym):
    for f in range(4):
        try:
            r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}",
                             params={"period1": 0, "period2": int(time.time()),
                                     "interval": "1mo"}, headers=UA, timeout=60)
            res = r.json()["chart"]["result"][0]
            adj = (res["indicators"].get("adjclose", [{}])[0].get("adjclose")
                   or res["indicators"]["quote"][0]["close"])
            idx = pd.to_datetime(res["timestamp"], unit="s").to_period("M")
            s = pd.Series(adj, index=idx).dropna()
            s = s[s > 0]
            time.sleep(0.3)
            return s[~s.index.duplicated(keep="last")]
        except Exception:
            if f == 3:
                return None
            time.sleep(2 ** (f + 1))


try:
    mn = json.load(open("miners.json", encoding="utf-8"))
    ser = pd.DataFrame(mn["series"]).set_index("t")
    ser.index = pd.PeriodIndex(ser.index, freq="M")
    begge = ser["sig1"].astype(bool) & ser["sig2"].astype(bool)
    fond = [i["ticker"] for i in mn["instrumenter"] if i.get("handlbar")]
    kurs = {t: k for t in fond if (k := yahoo_mnd(t)) is not None}
    world = yahoo_mnd("IWDA.L")
    print(f"   BEGGE staar i {int(begge.sum())} av {len(begge)} maaneder "
          f"({begge.index[0]} til {begge.index[-1]})")
    print(f"   fond med kurs: {', '.join(sorted(kurs))}"
          + (f"   (world: {'ok' if world is not None else 'MANGLER'})"))
    if world is None or not kurs:
        raise RuntimeError("mangler kurser")
    h = 6
    for merke, drop in (("med 2020", False), ("uten 2020", True)):
        mer = []
        for t in begge.index[begge.values]:
            if drop and t.year == AAR_UT:
                continue
            t1 = t + h
            if t1 > min(world.index[-1], max(k.index[-1] for k in kurs.values())):
                continue
            w = world.get(t), world.get(t1)
            if not all(w):
                continue
            fa = [k.get(t1) / k.get(t) - 1 for k in kurs.values()
                  if k.get(t) and k.get(t1)]
            if fa:
                mer.append(float(np.mean(fa)) - (w[1] / w[0] - 1))
        if merke == "med 2020":
            med_n, med_v = len(mer), (float(np.median(mer)) if mer else None)
        else:
            uten_n, uten_v = len(mer), (float(np.median(mer)) if mer else None)
        print(f"   {merke:10} {len(mer):3} signalmaaneder, median meravkastning "
              f"{pp(np.median(mer)) if mer else '   -  '} pp")
    rader.append({"del": "3 gull BEGGE", "periode": f"{begge.index[0]}-{begge.index[-1]}",
                  "h": 6, "med_2020": med_v, "uten_2020": uten_v,
                  "n_med": med_n, "n_uten": uten_n})
    print(f"   {dom(med_v, uten_v)}")
except Exception as e:
    print(f"   kunne ikke regnes: {type(e).__name__}: {str(e)[:90]}")

# ---------------------------------------------- 4. papirportefoljen
print("\n==================== 4. Papirportefoeljen i handel.json, 13 posisjoner")
try:
    pos = [q for q in json.load(open("handel.json", encoding="utf-8"))
           ["portefolje"]["posisjoner"] if q["variant"] == "alle"]
    mer = [(q["inngang"], q["segment"], q["avk"] - q["world"])
           for q in pos if q.get("world") is not None]
    alle = [m[2] for m in mer]
    u20 = [m[2] for m in mer if not m[0].startswith("2020")]
    print(f"   alle {len(alle)} posisjoner: median meravkastning {np.median(alle):+7.1f} pp, "
          f"snitt {np.mean(alle):+7.1f} pp, slo world i {sum(x > 0 for x in alle)} av {len(alle)}")
    print(f"   uten 2020 ({len(u20)}):       median {np.median(u20):+7.1f} pp, "
          f"snitt {np.mean(u20):+7.1f} pp, slo world i {sum(x > 0 for x in u20)} av {len(u20)}")
    rader.append({"del": "4 papirportefolje", "periode": "2011-2023", "h": 24,
                  "med_2020": float(np.median(alle)) / 100,
                  "uten_2020": float(np.median(u20)) / 100,
                  "n_med": len(alle), "n_uten": len(u20)})
    print(f"   median: {dom(np.median(alle), np.median(u20))}")
    print(f"   snitt:  {dom(np.mean(alle), np.mean(u20))}")
    print("   de fire fra 2020, i prosentpoeng over world:")
    for d, seg, m in sorted(mer, key=lambda x: -x[2])[:5]:
        print(f"      {d}  {seg:10} {m:+8.1f} pp{'   <- 2020' if d.startswith('2020') else ''}")
except Exception as e:
    print(f"   kunne ikke regnes: {type(e).__name__}: {str(e)[:80]}")

pd.DataFrame(rader).to_csv("sonder/uten_2020.csv", index=False)
print("\nLagret sonder/uten_2020.csv")
