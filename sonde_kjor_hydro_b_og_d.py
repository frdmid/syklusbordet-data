# ---------------------------------------------------------------------------
# sonde_kjor_hydro_b_og_d: hva fulgte for Norsk Hydro etter at testflagget
# «hoey tilbudsskaar og kapitulerte papirer» utloeste for aluminium
#
# Frodes bestilling 26.11.2026, etter at bordet varslet: «Aluminium:
# tilbudssiden krymper og aksjemarkedet har gitt opp papirene samtidig.
# Vurder om dette kan vaere et bra tidspunkt for aa kjoepe norsk hydro iht
# tekniske indikatorer og historikk.»
#
# ===========================================================================
# HVA DETTE ER, OG HVA DET IKKE ER
# ===========================================================================
# Dette er et BESKRIVENDE OPPSLAG for ETT papir, ikke en test av en ny regel.
# Det er viktig at forskjellen staar her, for sonden ble kjoert FOER denne
# fila ble skrevet: tallene kom av Frodes spoersmaal samme dag. Fila er en
# tro gjengivelse av det som ble regnet, slik at det kan kjoeres paa nytt, og
# ikke en forhaandsregistrering. Det som gjoer det forsvarlig er at
# INGENTING I REGELEN ER VALGT HER:
#   - flagget er testflagget b_og_d paa dashbordet, satt 29.09.2026 etter
#     sonde_kjor_b_signal, med terskler B2 over 50 og D for papirene 60 eller
#     mer, foer noe tilfelle hadde utloest,
#   - utloesningsaarene leses av sonder/b_signal.csv, som den sonden skrev,
#   - horisontene 12 og 24 maaneder er bordets vanlige,
#   - referansen er MSCI World i kroner, som resten av bordet bruker.
# Det eneste valget her er aa se paa Hydro alene i stedet for kurven, og det
# valget er Frodes spoersmaal.
#
# SONDEN AVGJOER INGENTING. Testflaggets eget kriterium staar urokket: det
# vurderes etter tre utloeste tilfeller, paa papirene likt vektet mot ACWI
# over tolv maaneder, og det kriteriet ble satt foer noe tilfelle. Ni
# historiske aar for ett papir er for lite til aa etablere noe, og 2020 alene
# baerer snittet. Tallene her skal leses som grunnlag for Frodes egen
# vurdering, ikke som et signal.
#
# MERK FORSKJELLEN PAA TO TALL SOM LETT BLANDES:
#   - «9 av 13 aar» i varselet er hvilket SEGMENT som slo de andre
#     segmentene, maalt paa papirkurven.
#   - Tallene her er hva HYDRO gjorde mot verdensindeksen. De to er ikke det
#     samme, og de peker ikke samme vei.
# ===========================================================================
#
# VALG SOM ER GJORT
#   - Inngang 30. april i utloesningsaaret, som i sonde_kjor_b_signal.
#   - Kursene er utbyttejusterte sluttkurser fra Yahoo, i kroner.
#   - MSCI World er IWDA.L regnet om til kroner med NOK=X.
#   - Det tekniske bildet er dagens: 50 og 200 dagers snitt, RSI 14,
#     fall fra femaarstopp og avstand til siste aars bunn og topp.
#   - Ingen nettkall utenom Yahoo. Sonden skriver ingenting til dashbordet,
#     databasen eller Shadow-OOS.
# ---------------------------------------------------------------------------

import os
import time
import warnings

import numpy as np
import pandas as pd
import requests

warnings.filterwarnings("ignore")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
PAPIR = "NHY.OL"
SEGMENT = "aluminium"
B2_MIN, D_MIN = 50, 60
ROT = os.path.dirname(os.path.abspath(__file__))


def get(url):
    for i in range(3):
        r = requests.get(url, headers=UA, timeout=45)
        if r.status_code in (429, 502, 503):
            time.sleep(4 * (i + 1))
            continue
        return r
    raise RuntimeError("Yahoo svarte ikke")


def yahoo(sym, interval="1mo"):
    r = get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}"
            f"?period1=0&period2={int(time.time())}&interval={interval}"
            f"&events=div%7Csplit&includeAdjustedClose=true").json()
    res = r["chart"]["result"][0]
    tz = (res.get("meta") or {}).get("exchangeTimezoneName") or "UTC"
    idx = pd.to_datetime(res["timestamp"], unit="s", utc=True).tz_convert(tz)
    adj = (res["indicators"].get("adjclose") or [{}])[0].get("adjclose")
    if not adj:
        adj = res["indicators"]["quote"][0]["close"]
    s = pd.Series(adj, index=idx).dropna()
    return s[s > 0]


def naken(s):
    """Yahoo gir tidssonebevisst indeks; sammenligningene under er naive."""
    s = s.copy()
    s.index = s.index.tz_localize(None)
    return s


print("=" * 78)
print("sonde_kjor_hydro_b_og_d: Norsk Hydro etter testflagget B2 og D")
print("BESKRIVENDE OPPSLAG. Avgjoer ingenting. Se toppen av fila.")
print("=" * 78)

# ------------------------------------------------------------- teknisk naa
dag = yahoo(PAPIR, "1d")
ma50, ma200 = dag.rolling(50).mean(), dag.rolling(200).mean()
sist = float(dag.iloc[-1])
d = dag.diff()
rsi = 100 - 100 / (1 + d.clip(lower=0).rolling(14).mean() / (-d.clip(upper=0)).rolling(14).mean())
topp5 = float(dag[dag.index >= dag.index[-1] - pd.Timedelta(days=5 * 365)].max())
bunn1 = float(dag[dag.index >= dag.index[-1] - pd.Timedelta(days=365)].min())
topp1 = float(dag[dag.index >= dag.index[-1] - pd.Timedelta(days=365)].max())

print(f"\nTEKNISK BILDE {dag.index[-1].date()}")
print(f"   kurs, utbyttejustert        {sist:8.2f}")
print(f"   50 dagers snitt             {float(ma50.iloc[-1]):8.2f}   avvik {100*(sist/float(ma50.iloc[-1])-1):+6.1f} %")
print(f"   200 dagers snitt            {float(ma200.iloc[-1]):8.2f}   avvik {100*(sist/float(ma200.iloc[-1])-1):+6.1f} %")
print(f"   50 over 200                 {'ja' if float(ma50.iloc[-1]) > float(ma200.iloc[-1]) else 'nei':>8}")
print(f"   RSI 14 dager                {float(rsi.iloc[-1]):8.1f}")
print(f"   fall fra femaarstopp        {100*(sist/topp5-1):+8.1f} %")
print(f"   over siste aars bunn        {100*(sist/bunn1-1):+8.1f} %")
print(f"   under siste aars topp       {100*(sist/topp1-1):+8.1f} %")

mnd = naken(yahoo(PAPIR, "1mo").resample("ME").last())
for n, navn in ((12, "12 mnd"), (24, "24 mnd"), (60, "5 aar")):
    if len(mnd) > n:
        print(f"   avkastning {navn:7}          {100*(float(mnd.iloc[-1])/float(mnd.iloc[-1-n])-1):+8.1f} %")

# --------------------------------------------------------------- historikk
b = pd.read_csv(os.path.join(ROT, "sonder", "b_signal.csv"))
al = b[b.seg == SEGMENT]
ut = al[(al.B2 > B2_MIN) & (al.D_pap >= D_MIN)]
print(f"\nUTLOESTE AAR FOR {SEGMENT.upper()} (B2 over {B2_MIN} og D for papirene {D_MIN}+): {len(ut)}")
print("   " + ", ".join(str(int(x)) for x in ut.inngang))

verden = naken((yahoo("IWDA.L", "1mo").resample("ME").last()
                * yahoo("NOK=X", "1mo").resample("ME").last().reindex(
                    yahoo("IWDA.L", "1mo").resample("ME").last().index)).dropna())


def avk(s, t0, n):
    idx = s.index[s.index <= t0]
    if not len(idx):
        return None
    i = s.index.get_loc(idx[-1])
    return None if i + n >= len(s) else float(s.iloc[i + n] / s.iloc[i] - 1) * 100


print(f"\nHYDRO ETTER HVER UTLOESNING (inngang 30. april)")
print(f"   {'aar':5} {'B2':>5} {'D_pap':>6} {'12 mnd':>9} {'mot world':>10} {'24 mnd':>9} {'mot world':>10}")
r12, r24, m12, m24, rader = [], [], [], [], []
for _, row in ut.iterrows():
    t0 = pd.Timestamp(int(row.inngang), 4, 30)
    a12, a24 = avk(mnd, t0, 12), avk(mnd, t0, 24)
    w12, w24 = avk(verden, t0, 12), avk(verden, t0, 24)
    e12 = None if (a12 is None or w12 is None) else a12 - w12
    e24 = None if (a24 is None or w24 is None) else a24 - w24
    print(f"   {int(row.inngang):5} {row.B2:5.0f} {row.D_pap:6.1f} "
          f"{('%+9.1f' % a12) if a12 is not None else '        -'} "
          f"{('%+10.1f' % e12) if e12 is not None else '         -'} "
          f"{('%+9.1f' % a24) if a24 is not None else '        -'} "
          f"{('%+10.1f' % e24) if e24 is not None else '         -'}")
    rader.append({"aar": int(row.inngang), "B2": float(row.B2), "D_pap": float(row.D_pap),
                  "a12": a12, "mer12": e12, "a24": a24, "mer24": e24})
    for lst, v in ((r12, a12), (r24, a24), (m12, e12), (m24, e24)):
        if v is not None:
            lst.append(v)

print()
for navn, lst in (("12 mnd, avkastning", r12), ("12 mnd, mot world", m12),
                  ("24 mnd, avkastning", r24), ("24 mnd, mot world", m24)):
    if lst:
        print(f"   {navn:22} n {len(lst):2}  median {np.median(lst):+7.1f}  "
              f"positive {sum(1 for x in lst if x > 0)} av {len(lst)}")

print("\nGRUNNLINJEN: alle aar i samme periode, uansett utloesning")
alle = []
for aar in range(2012, 2025):
    v, w = avk(mnd, pd.Timestamp(aar, 4, 30), 12), avk(verden, pd.Timestamp(aar, 4, 30), 12)
    if v is not None and w is not None:
        alle.append(v - w)
print(f"   12 mnd mot world: n {len(alle)}, median {np.median(alle):+.1f} pp, "
      f"positive {sum(1 for x in alle if x > 0)} av {len(alle)}")

print("\nLES DETTE SAMMEN MED TALLENE:")
print("   Utloesningsaarene er litt mindre daarlige enn grunnlinjen, men")
print("   medianen mot verdensindeksen er fortsatt negativ, og 2020 baerer")
print("   snittet alene. Ni aar for ett papir etablerer ingenting.")
print("   Testflaggets eget kriterium staar urokket: tre utloeste tilfeller,")
print("   papirene likt vektet mot ACWI over tolv maaneder.")
