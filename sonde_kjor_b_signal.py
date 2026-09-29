# ---------------------------------------------------------------------------
# sonde_kjor_b_signal: er hoey tilbudsskaar B2, eller hoey kapitulasjon D, et
# kjoepssignal for papirene?
#
# Frodes bestilling 29.09.2026. Samlet test over alle B-seriene bordet har:
# seks metaller (b_capex.json) og tre riggsegmenter (b_rigg.json). Rigger
# alene gir omtrent en episode per segment. D testes i samme oppsett, baade
# for papirene i segmentet og for fondet.
#
# ALT UNDER ER SATT FOER KJOERING
#
# INNGANG  B2 for aar t er kjent naar aarsrapportene er ute. Inngang ved
#          slutten av april aar t+1. D leses samme maaned, punkt i tid.
# UTFALL   Avkastning 12 og 24 maaneder etter inngang, i dollar, utbytte
#          justert (Yahoo adjclose), minus verdensindeksen (ACWI, SPY foer
#          ACWI fantes). Segmentets utfall = median av papirene som har kurs.
# PAPIRER  Metallene: papirene paa tavlen (instrumenter.py), ikke de omvendte.
#          Rigger: land HP, NBR, PTEN, PD.TO; grunt BORR, SHLF.OL; dyp RIG.
#          Fond: temafondet fra kapitulasjon_d.TEMA der det finnes (COPX, GDX,
#          XME), OIH for riggsegmentene.
# D        Som i kapitulasjon_d.py: snittet av persentilen for fall fra
#          femaarstopp og for andel uker under 200-dagers snitt, dempet naar
#          fallet er under 30 %. Segmentets D = median av papirenes D.
# GRUPPER  Hoey B2: over 50. Hoey D: 60 eller mer (dashbordets "langt nede").
# SAMMENLIGNING  For hvert inngangsaar: median av utfallet i hoey gruppe minus
#          median i lav gruppe, naar begge har minst ett segment.
# AVGJOER  Et signal HOLDER hvis, paa 12 maaneder: (a) differansen er positiv
#          i flertallet av aarene, (b) snittet av differansene er positivt,
#          og (c) begge holder ogsaa uten inngangsaarene 2020 og 2021.
#          24 maaneder vises, men avgjoer ikke.
# FORBEHOLD  B-kurvene er dagens selskaper (overlevere), og papirene paa
#          tavlen er valgt i dag. Store raavarebunner (2015-16, 2020) treffer
#          alle segmentene samtidig, saa det reelle antallet episoder er lite.
# ---------------------------------------------------------------------------

import json, time, warnings
import numpy as np
import pandas as pd
import requests
from instrumenter import INSTR

warnings.filterwarnings("ignore")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
TOPPVINDU, FULLT_FALL, MIN_HIST = 60, 30, 60
METALL = {"uran": "uran", "kobber": "kobber", "aluminium": "aluminium", "kull": "kull",
          "gull": "gold", "jernmalm": "jernmalm"}
FOND = {"kobber": "COPX", "gull": "GDX", "aluminium": "XME",
        "rigg_land": "OIH", "rigg_grunt": "OIH", "rigg_dyp": "OIH"}
RIGG_PAPIRER = {"rigg_land": ["HP", "NBR", "PTEN", "PD.TO"], "rigg_grunt": ["BORR", "SHLF.OL"], "rigg_dyp": ["RIG"]}
FX = {"NOK": ("NOK=X", True), "CAD": ("CAD=X", True), "GBP": ("GBPUSD=X", False), "GBp": ("GBPUSD=X", False),
      "EUR": ("EURUSD=X", False), "AUD": ("AUDUSD=X", False), "SEK": ("SEK=X", True), "CHF": ("CHF=X", True),
      "ZAR": ("ZAR=X", True), "DKK": ("DKK=X", True)}
_fx = {}


def dag(sym, valutakurs=False):
    r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}",
                     params={"range": "max", "interval": "1d", "events": "div,split"}, headers=UA, timeout=40)
    res = r.json()["chart"]["result"][0]
    idx = pd.to_datetime(res["timestamp"], unit="s").normalize()
    adj = ((res["indicators"].get("adjclose") or [{}])[0] or {}).get("adjclose")
    s = pd.Series(adj if adj else res["indicators"]["quote"][0]["close"], index=idx, dtype=float).dropna()
    s = s[(s > 0) & ~s.index.duplicated(keep="last")]
    if valutakurs:
        return s
    val = (res.get("meta") or {}).get("currency") or "USD"
    if val != "USD":
        fs, inv = FX[val]
        if fs not in _fx:
            f = dag(fs, valutakurs=True)
            _fx[fs] = (1.0 / f) if inv else f
        s = (s * _fx[fs].reindex(s.index).ffill()).dropna()
        if val == "GBp":
            s = s / 100
    return s


def exp_pct(v, minn=MIN_HIST):
    v = np.asarray(v, float)
    out = np.full(len(v), np.nan)
    for i in range(len(v)):
        if i + 1 >= minn and not np.isnan(v[i]):
            h = v[: i + 1]
            h = h[~np.isnan(h)]
            if len(h) >= minn:
                out[i] = (1 - (h <= v[i]).sum() / len(h)) * 100
    return out


def d_serie(daglig):
    """D per maaned, punkt i tid, som i kapitulasjon_d.py."""
    m = daglig.resample("ME").last().dropna()
    m.index = m.index.to_period("M")
    topp = m.rolling(TOPPVINDU, min_periods=12).max()
    fall = (m / topp - 1) * 100
    ma = daglig.rolling(200, min_periods=120).mean()
    uke = (daglig < ma).resample("W").last().dropna().astype(float)
    and52 = uke.rolling(52, min_periods=26).mean() * 100
    a = and52.resample("ME").last(); a.index = a.index.to_period("M")
    a = a.reindex(fall.index)
    d = np.nanmean(np.vstack([exp_pct(fall.values), exp_pct(-a.values)]), axis=0)
    d = d * np.clip(np.abs(fall.values) / FULLT_FALL, 0, 1)
    return pd.Series(d, index=fall.index)


def mnd(daglig):
    m = daglig.resample("ME").last().dropna()
    m.index = m.index.to_period("M")
    return m


print("1. B2 PER SEGMENT OG AAR\n")
B = {}
bc = json.load(open("b_capex.json", encoding="utf-8"))["metaller"]
for m, sid in METALL.items():
    if m in bc:
        B[m] = {int(a): b for a, b in zip(bc[m]["aar"], bc[m]["B2"]) if b is not None}
br = json.load(open("b_rigg.json", encoding="utf-8"))["segmenter"]
for k in ("land", "grunt", "dyp"):
    B["rigg_" + k] = {int(a): b for a, b in zip(br[k]["aar"], br[k]["B2"]) if b is not None}
for s, v in B.items():
    print(f"   {s:12s} " + " ".join(f"{a}:{b:.0f}" for a, b in sorted(v.items())))

print("\n2. KURSER\n")
PAPIRER = {m: [tk for tk, b, n, typ, kom in INSTR.get(sid, []) if not kom.strip().startswith("-")]
           for m, sid in METALL.items()}
PAPIRER.update(RIGG_PAPIRER)
alle = sorted({t for v in PAPIRER.values() for t in v} | set(FOND.values()) | {"ACWI", "SPY"})
DAG = {}
for tk in alle:
    try:
        DAG[tk] = dag(tk)
    except Exception as e:
        print(f"   {tk:10s} ingen kurs ({type(e).__name__})")
    time.sleep(0.25)
MND = {tk: mnd(s) for tk, s in DAG.items()}
DS = {}
for tk, s in DAG.items():
    try:
        DS[tk] = d_serie(s)
    except Exception:
        pass
for s, v in PAPIRER.items():
    print(f"   {s:12s} " + ", ".join(f"{t} ({MND[t].index[0]})" if t in MND else f"{t} (mangler)" for t in v)
          + (f"  | fond {FOND[s]}" if s in FOND else ""))
verden = MND["SPY"].copy()
if "ACWI" in MND:
    fra = MND["ACWI"].index[0]
    verden = pd.concat([verden[verden.index < fra] / verden[fra] * MND["ACWI"][fra], MND["ACWI"]])


def mer(tk, t0, h):
    m = MND.get(tk)
    if m is None or t0 not in m.index or t0 + h not in m.index or t0 not in verden.index or t0 + h not in verden.index:
        return np.nan
    return (m[t0 + h] / m[t0]) - (verden[t0 + h] / verden[t0])


print("\n3. RADER: segment og inngangsaar\n")
RAD = []
for s, bser in B.items():
    for aar, b2 in sorted(bser.items()):
        t0 = pd.Period(f"{aar + 1}-04", "M")
        pap = [t for t in PAPIRER[s] if t in MND]
        r = {"seg": s, "inngang": aar + 1, "B2": b2}
        for h in (12, 24):
            v = [mer(t, t0, h) for t in pap]
            v = [x for x in v if np.isfinite(x)]
            r[f"u{h}"] = float(np.median(v)) if v else np.nan
        dv = [float(DS[t].get(t0, np.nan)) for t in pap if t in DS]
        dv = [x for x in dv if np.isfinite(x)]
        r["D_pap"] = float(np.median(dv)) if dv else np.nan
        f = FOND.get(s)
        r["D_fond"] = float(DS[f].get(t0, np.nan)) if f in DS else np.nan
        RAD.append(r)
df = pd.DataFrame(RAD)
pd.set_option("display.width", 200)
print(df.round(3).to_string(index=False))


def test(navn, hoey):
    print(f"\n   {navn}")
    ut = {}
    for h in (12, 24):
        rader = []
        for inn, g in df.groupby("inngang"):
            g = g[np.isfinite(g[f"u{h}"])]
            hm, lm = g[hoey(g)], g[~hoey(g)]
            if len(hm) and len(lm):
                rader.append((inn, float(hm[f"u{h}"].median() - lm[f"u{h}"].median()), len(hm), len(lm)))
        if not rader:
            print(f"      {h} mnd: ingen aar med begge grupper"); continue
        d = pd.DataFrame(rader, columns=["inngang", "diff", "n_hoey", "n_lav"]).set_index("inngang")
        uten = d.drop([2020, 2021], errors="ignore")
        ok = lambda x: len(x) and (x["diff"] > 0).sum() * 2 > len(x) and x["diff"].mean() > 0
        print(f"      {h} mnd: " + "  ".join(f"{i}:{100 * r['diff']:+.0f}({int(r['n_hoey'])}/{int(r['n_lav'])})" for i, r in d.iterrows()))
        print(f"         positive {int((d['diff'] > 0).sum())} av {len(d)}, snitt {100 * d['diff'].mean():+.1f} pp; "
              f"uten 2020-21: {int((uten['diff'] > 0).sum())} av {len(uten)}, snitt {100 * uten['diff'].mean():+.1f} pp")
        ut[h] = bool(ok(d) and ok(uten))
    dom = ut.get(12, False)
    print(f"      -> {'HOLDER' if dom else 'HOLDER IKKE'} (avgjoeres paa 12 mnd)")
    return dom


print("\n\n4. TESTENE (satt foer kjoering)")
R = {"B2 over 50": test("B2 over 50 mot resten", lambda g: g["B2"] > 50),
     "D papirer 60+": test("D papirene 60 eller mer mot resten", lambda g: g["D_pap"] >= 60),
     "D fond 60+": test("D fondet 60 eller mer mot resten", lambda g: g["D_fond"] >= 60),
     "B2 og D papirer": test("B2 over 50 OG D papirene 60 eller mer mot resten",
                             lambda g: (g["B2"] > 50) & (g["D_pap"] >= 60))}
print("\n\n5. OPPSUMMERING: " + ", ".join(f"{k}: {'holder' if v else 'holder ikke'}" for k, v in R.items()))
df.to_csv("sonder/b_signal.csv", index=False)
