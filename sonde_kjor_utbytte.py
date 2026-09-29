# ---------------------------------------------------------------------------
# sonde_kjor_utbytte: maales alle papirene riktig med utbytte?
#
# Frodes bestilling 29.09.2026. To steder i repoet regner totalavkastning:
#   A  Backtestene og kapitulasjon D bruker Yahoo sin utbyttejusterte kurs
#      (adjclose), maanedlig eller daglig.
#   B  Flaggloggen (fra 29.09) logger siste kurs og summen av utbytte per uke
#      fra Yahoo sine utbyttehendelser, og regner (kurs slutt + utbytte) /
#      kurs start. Da maa utbyttebeloepet vaere i samme valuta og enhet som
#      kursen. Pence mot pund (London) og dollarutbytte paa papirer notert i
#      kroner er de kjente fellene.
#
# For hvert papir paa tavlen, ACWI og bransjefondene:
#   1  Enhet: for hver utbyttehendelse siste tre aar regnes utbyttet Yahoo
#      selv har lagt inn i adjclose, 1 - (adj/close dagen foer) /
#      (adj/close paa eksdagen), gange kursen dagen foer. Det skal vaere likt
#      det rapporterte beloepet. Forholdet viser enhetsfeil (100 = pence mot
#      pund) og valutafeil (rundt 10 = dollar mot kroner).
#   2  Ettaars totalavkastning paa tre maater: daglig adjclose, maanedlig
#      adjclose (det backtestene bruker), og kurs pluss rapporterte utbytter
#      (det flaggloggen gjoer). Avvik over ett prosentpoeng merkes.
#   3  Utbytteavkastning siste tolv maaneder, som rimelighetskontroll.
# ---------------------------------------------------------------------------

import time
import numpy as np
import pandas as pd
import requests
from instrumenter import INSTR

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
EKSTRA = ["ACWI", "XOP", "XME", "GDX", "EXV6.DE", "IOGP.L"]


def hent(tk, intervall, rekkevidde):
    for i in range(3):
        try:
            r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{tk}"
                             f"?range={rekkevidde}&interval={intervall}&events=div%7Csplit&includeAdjustedClose=true",
                             headers=UA, timeout=30)
            if r.status_code == 429:
                time.sleep(5); continue
            return r.json()["chart"]["result"][0]
        except Exception:
            time.sleep(2)
    return None


def serier(res):
    idx = pd.to_datetime(res["timestamp"], unit="s").normalize()
    q = res["indicators"]["quote"][0]["close"]
    a = ((res["indicators"].get("adjclose") or [{}])[0] or {}).get("adjclose")
    d = pd.DataFrame({"close": q, "adj": a if a else [np.nan] * len(q)}, index=idx).dropna(subset=["close"])
    d = d[~d.index.duplicated(keep="last")]
    div = pd.Series({pd.to_datetime(int(v["date"]), unit="s").normalize(): float(v["amount"])
                     for v in ((res.get("events") or {}).get("dividends") or {}).values()}, dtype=float).sort_index()
    if not len(div):
        div = pd.Series(dtype=float, index=pd.DatetimeIndex([]))
    return d, div, (res.get("meta") or {}).get("currency")


papirer = sorted({tk for rader in INSTR.values() for tk, *_ in rader} | set(EKSTRA))
print(f"{len(papirer)} papirer\n")
print(f"{'papir':10s} {'val':4s} {'utb 3 aar':>9s} {'enhet':>7s} {'yield 12m':>9s} "
      f"{'TR dag adj':>10s} {'TR mnd adj':>10s} {'TR kurs+utb':>11s}  merknad")
feil = []
for tk in papirer:
    r = hent(tk, "1d", "3y")
    if r is None:
        print(f"{tk:10s} ingen data"); feil.append((tk, "ingen data")); continue
    d, div, val = serier(r)
    merk = []
    # 1 enhet
    forhold = []
    for dag, beloep in div.items():
        foer = d.index[d.index < dag]
        paa = d.index[d.index >= dag]
        if not len(foer) or not len(paa) or d["adj"].isna().all():
            continue
        f0, f1 = foer[-1], paa[0]
        k0 = d.loc[f0, "adj"] / d.loc[f0, "close"]
        k1 = d.loc[f1, "adj"] / d.loc[f1, "close"]
        implisitt = (1 - k0 / k1) * d.loc[f0, "close"]
        if implisitt > 0 and beloep > 0:
            forhold.append(beloep / implisitt)
    enhet = float(np.median(forhold)) if forhold else np.nan
    if forhold and not (0.9 <= enhet <= 1.1):
        merk.append(f"utbytte i annen enhet eller valuta enn kursen (x{enhet:.2f})")
    # 2 ettaars totalavkastning
    slutt = d.index[-1]
    start = d.index[d.index <= slutt - pd.Timedelta(days=365)]
    tr_dag = tr_kurs = tr_mnd = np.nan
    if len(start):
        s0 = start[-1]
        if d["adj"].notna().all():
            tr_dag = 100 * (d.loc[slutt, "adj"] / d.loc[s0, "adj"] - 1)
        u = div[(div.index > s0) & (div.index <= slutt)].sum()
        tr_kurs = 100 * ((d.loc[slutt, "close"] + u) / d.loc[s0, "close"] - 1)
    rm = hent(tk, "1mo", "3y")
    if rm is not None:
        dm, _, _ = serier(rm)
        dm = dm[dm.index <= slutt]
        if len(dm) > 13 and dm["adj"].notna().all():
            tr_mnd = 100 * (dm["adj"].iloc[-1] / dm["adj"].iloc[-13] - 1)
    y12 = 100 * div[div.index > slutt - pd.Timedelta(days=365)].sum() / d.loc[slutt, "close"]
    if np.isfinite(tr_dag) and np.isfinite(tr_kurs) and abs(tr_dag - tr_kurs) > 1.0:
        merk.append(f"kurs+utbytte avviker {tr_kurs - tr_dag:+.1f} pp fra adjclose")
    if d["adj"].isna().all():
        merk.append("adjclose mangler")
    if y12 > 25:
        merk.append("urimelig hoey utbytteavkastning")
    if merk:
        feil.append((tk, "; ".join(merk)))
    fm = lambda x: "     -" if not np.isfinite(x) else f"{x:+7.1f}%"
    print(f"{tk:10s} {str(val):4s} {len(div):9d} {'-' if not np.isfinite(enhet) else f'{enhet:.2f}':>7s} "
          f"{y12:8.1f}% {fm(tr_dag):>10s} {fm(tr_mnd):>10s} {fm(tr_kurs):>11s}  {'; '.join(merk) or 'ok'}", flush=True)
    time.sleep(0.4)

print("\nTR mnd adj maaler til siste maanedsslutt, de andre til siste dag, saa de kan avvike litt av den grunn.")
print("\nOPPSUMMERING")
if feil:
    for tk, m in feil:
        print(f"   {tk:10s} {m}")
else:
    print("   Ingen avvik.")
