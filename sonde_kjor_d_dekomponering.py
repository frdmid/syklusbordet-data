# ---------------------------------------------------------------------------
# sonde_kjor_d_dekomponering: hvorfor varierer D saa mye mellom papirene i
# samme segment? (Frodes bestilling 12.10.2026). BESKRIVENDE, ingen kriterier,
# ingen beslutning om signal. Ingenting paa dashbordet endres.
#
# 1. Datakontroll. kapitulasjon_d.py henter kurser med range=max og
#    interval=1d. Yahoo svarer da IKKE med dagskurser, men med maaneds-,
#    kvartals- eller ukeskurser (dataGranularity 1mo, 3mo, 1wk). Da blir
#    "200-dagers snitt" et snitt over 200 maaneder (eller kvartaler), og for
#    papirer med kvartalskurser blir femaarstoppen en topp over 15 aar.
#    Sonden henter de samme papirene med period1/period2 (gir dagskurser) og
#    regner D paa nytt med de samme funksjonene (exp_pct og ledd, lest fra
#    kapitulasjon_d.py), og sammenligner med d_kapitulasjon.json.
#
# 2. Dekomponering. For hvert papir: endringen i log-kurs (lokal valuta,
#    utbyttejustert) de siste 24 maanedene deles i
#       raavare  = beta_r x endringen i segmentets realpris (priser_mnd.csv)
#       marked   = beta_m x endringen i verdensindeksen (ACWI, USD)
#       rest     = det som er igjen (selskap, valuta og alt annet)
#    Betaene er regnet paa maanedlige endringer de 60 maanedene foer
#    24-maanedersvinduet (ingen overlapp med det som forklares).
#    Andelen rest av summen av absoluttverdiene viser om papirets bevegelse er
#    selskapsspesifikk eller felles med raavaren.
# ---------------------------------------------------------------------------

import ast, json, time
import numpy as np
import pandas as pd
import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
t = ast.parse(open("kapitulasjon_d.py", encoding="utf-8").read())
ns = {"np": np, "pd": pd, "MIN_HIST": 60, "TOPPVINDU": 60, "FULLT_FALL": 30}
exec(compile(ast.Module(body=[n for n in t.body if isinstance(n, ast.FunctionDef) and n.name in ("exp_pct", "ledd")],
                        type_ignores=[]), "kapitulasjon_d", "exec"), ns)
exp_pct, ledd = ns["exp_pct"], ns["ledd"]


def yahoo(sym, maks=False):
    p = {"range": "max"} if maks else {"period1": 0, "period2": int(time.time())}
    r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}",
                     params={**p, "interval": "1d", "events": "div,split", "includeAdjustedClose": "true"},
                     headers=UA, timeout=60).json()["chart"]["result"][0]
    tz = (r.get("meta") or {}).get("exchangeTimezoneName") or "UTC"
    idx = pd.to_datetime(r["timestamp"], unit="s", utc=True).tz_convert(tz).normalize().tz_localize(None)
    adj = ((r["indicators"].get("adjclose") or [{}])[0] or {}).get("adjclose") or r["indicators"]["quote"][0]["close"]
    s = pd.Series(adj, index=idx, dtype=float).dropna()
    return s[~s.index.duplicated(keep="last")], (r.get("meta") or {}).get("dataGranularity")


def D_av(s):
    fall, u200 = ledd(s)
    d1, d2 = exp_pct(fall.values), exp_pct(-u200.values)
    d = np.nanmean(np.vstack([d1, d2]), axis=0) * np.clip(np.abs(fall.values) / 30, 0, 1)
    i = len(d) - 1
    while i >= 0 and np.isnan(d[i]):
        i -= 1
    return float(d[i]), float(fall.values[i])


GAMMEL = json.load(open("d_kapitulasjon.json", encoding="utf-8"))["papirer"]
pm = pd.read_csv("serier/priser_mnd.csv")
RAA = {s: pd.Series(np.log(g.real.astype(float).values), index=pd.PeriodIndex(g.t, freq="M"))
       for s, g in pm.groupby("segment")}
acwi, _ = yahoo("ACWI")
ACWI = np.log(acwi.resample("ME").last()); ACWI.index = ACWI.index.to_period("M")

print("1. DATAKONTROLL: HVA YAHOO SVARER MED range=max\n")
gran_teller, rader = {}, []
for tk, p in sorted(GAMMEL.items()):
    try:
        _, g_max = yahoo(tk, maks=True)
        s, _ = yahoo(tk)
    except Exception as e:
        print(f"   {tk:10s} feil {type(e).__name__}"); continue
    gran_teller[g_max] = gran_teller.get(g_max, 0) + 1
    Dny, fallny = D_av(s)
    m = np.log(s.resample("ME").last()); m.index = m.index.to_period("M")
    rad = {"tk": tk, "seg": (p.get("segmenter") or ["?"])[0], "g": g_max, "D_gml": p["D"], "D_ny": Dny,
           "fall_gml": p.get("fall_pst"), "fall_ny": fallny}
    seg = rad["seg"]
    if seg in RAA:
        df = pd.concat({"p": m.diff(), "r": RAA[seg].diff(), "w": ACWI.diff()}, axis=1).dropna()
        if len(df) >= 84:
            slutt = df.index[-1]
            est = df[(df.index > slutt - 84) & (df.index <= slutt - 24)]
            vin = df[df.index > slutt - 24]
            X = np.column_stack([np.ones(len(est)), est.r, est.w])
            b = np.linalg.lstsq(X, est.p.values, rcond=None)[0]
            tot = vin.p.sum(); raa = b[1] * vin.r.sum(); mkt = b[2] * vin.w.sum(); rest = tot - raa - mkt
            rad.update({"tot": tot, "raa": raa, "mkt": mkt, "rest": rest, "beta_r": b[1],
                        "rest_andel": abs(rest) / (abs(raa) + abs(mkt) + abs(rest))})
    rader.append(rad)
    time.sleep(0.25)
R = pd.DataFrame(rader)
print("   granularitet med range=max: " + ", ".join(f"{k} {v}" for k, v in gran_teller.items()))
R["endring"] = (R.D_ny - R.D_gml).abs()
print(f"   D med dagskurser mot dagens D: median endring {R.endring.median():.1f} poeng, over 20 poeng: {int((R.endring > 20).sum())}")
for _, x in R.sort_values("endring", ascending=False).head(15).iterrows():
    print(f"      {x.tk:10s} {x.seg:12s} ({x.g})  D {x.D_gml:5.1f} -> {x.D_ny:5.1f}   fall {x.fall_gml} -> {x.fall_ny:.1f} %")

print("\n\n2. DEKOMPONERING, SISTE 24 MND (log-%, dagskurser)\n")
for seg, g in R.dropna(subset=["tot"]).groupby("seg"):
    if len(g) < 2:
        continue
    print(f"   {seg}")
    for _, x in g.sort_values("D_ny", ascending=False).iterrows():
        print(f"      {x.tk:10s} D {x.D_ny:5.1f}  totalt {100 * x.tot:+6.1f}  = raavare {100 * x.raa:+6.1f} (beta {x.beta_r:+.2f})"
              f"  + marked {100 * x.mkt:+6.1f}  + rest {100 * x.rest:+6.1f}   rest-andel {100 * x.rest_andel:3.0f} %")
R.to_csv("sonder/d_dekomponering.csv", index=False)
print(f"\n   median rest-andel {100 * R.rest_andel.median():.0f} %; lagret sonder/d_dekomponering.csv")
