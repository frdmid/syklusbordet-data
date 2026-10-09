# ---------------------------------------------------------------------------
# sonde_kjor_solv_signal: salgssignal for edelmetaller naar soelv tar igjen
# gull (Goehring & Rozencwajg, Q2 2026-brevet)
#
# Frodes bestilling 09.10.2026. G&R hevder at i hvert edelmetalloppsving
# siden 1971 har soelv foerst ligget etter gull og saa tatt det igjen i et
# kraftig rykk, og at det hver gang (1974, 1979, 2011, 2020, 2025/26) var
# riktig aa redusere begge metallene. Sonden proever om en enkel, mekanisk
# versjon av regelen holder.
#
# ALT UNDER ER SATT FOER KJOERING
#
# DATA     Verdensbankens Pink Sheet, maanedssnitt for gull og soelv i dollar,
#          signaler fra 1971-08 (gullvinduet stengt). Realavkastning med
#          amerikansk KPI (cpi_kopi.csv). Gullaksjer: Philadelphia Gold and
#          Silver Index (^XAU, fra 1984) og GDX (fra 2006), maanedsslutt fra
#          Yahoo. Aksjene vises, men avgjoer ikke.
#
# SIGNAL i maaned t naar alle tre holder:
#   1. Soelv har slaatt gull med minst 40 prosentpoeng over seks maaneder:
#      (S_t / S_t-6) / (G_t / G_t-6) - 1 >= 0,40.
#   2. Gull er i oppgang: G_t / G_t-24 >= 1,25.
#   3. Soelv laa etter foer rykket: forholdet gull/soelv i t-6 var over sitt
#      eget snitt de 60 maanedene fram til t-6.
#   Foerste maaned som oppfyller kravene er signalet. Nytt signal tidligst 24
#   maaneder senere.
#
# BASIS    Alle maaneder fra 1971-08 der krav 2 holder (gull i oppgang), uten
#          signal de tre foregaaende maanedene.
#
# AVGJOER  Signalet HOLDER bare hvis alle tre er oppfylt:
#   (a) Gjenkjenning: regelen finner minst 4 av G&Rs 5 episoder innen
#       4 maaneder fra 1974-02, 1979-12, 2011-04, 2020-08 og 2026-01.
#   (b) For alle signaler med hele 12 maaneder etterpaa (ogsaa de G&R ikke
#       nevner): median nominell gullavkastning over 12 maaneder ligger minst
#       10 prosentpoeng under basismaanedenes median, og minst to av tre
#       signaler har negativ gullavkastning over 12 maaneder.
#   (c) Plataa: (b) holder ogsaa med terskel 30 og 50 prosentpoeng i krav 1.
#   24 maaneder, realavkastning, soelv og aksjer vises, men avgjoer ikke.
#
# FORBEHOLD  Regelen er formet etter at G&Rs episoder var kjent, saa (a) er
#          en kontroll av at regelen maaler det de beskriver, ikke et bevis.
#          Det reelle beviset er (b) og (c), og der er antallet episoder lite.
#          Episoden 2026 har for kort tid etter seg til aa telle i (b).
# ---------------------------------------------------------------------------

import io, re
import numpy as np
import pandas as pd
import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
TERSKEL, OPP, VINDU, KARENS = 0.40, 1.25, 60, 24
GR = ["1974-02", "1979-12", "2011-04", "2020-08", "2026-01"]
START = pd.Period("1971-08", "M")


def pink_sheet():
    html = requests.get("https://www.worldbank.org/en/research/commodity-markets", headers=UA, timeout=30).text
    url = re.findall(r'https?://[^"\']*?CMO[^"\']*?Monthly[^"\']*?\.xlsx', html)[0]
    df = pd.read_excel(io.BytesIO(requests.get(url, headers=UA, timeout=90).content),
                       sheet_name="Monthly Prices", skiprows=4)
    df = df.rename(columns={df.columns[0]: "t"})
    df = df[df["t"].astype(str).str.match(r"^\d{4}M\d{1,2}$", na=False)].copy()
    df.index = pd.PeriodIndex(df["t"].str.replace("M", "-", regex=False), freq="M")
    return df[["Gold", "Silver"]].apply(pd.to_numeric, errors="coerce").dropna()


def yahoo_mnd(sym):
    r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}",
                     params={"range": "max", "interval": "1d"}, headers=UA, timeout=60).json()["chart"]["result"][0]
    adj = ((r["indicators"].get("adjclose") or [{}])[0] or {}).get("adjclose") or r["indicators"]["quote"][0]["close"]
    s = pd.Series(adj, index=pd.to_datetime(r["timestamp"], unit="s"), dtype=float).dropna()
    m = s.resample("ME").last().dropna()
    m.index = m.index.to_period("M")
    return m


def signaler(G, S, terskel):
    rel6 = (S / S.shift(6)) / (G / G.shift(6)) - 1
    opp = G / G.shift(24) >= OPP
    R = G / S
    etter = R.shift(6) > R.rolling(VINDU).mean().shift(6)
    kand = (rel6 >= terskel) & opp & etter
    ut, siste = [], None
    for t in kand.index[kand.values]:
        if t < START:
            continue
        if siste is None or (t - siste).n >= KARENS:
            ut.append(t)
            siste = t
    return ut, opp


def fram(x, t, h):
    return x[t + h] / x[t] - 1 if (t in x.index and t + h in x.index) else np.nan


ps = pink_sheet()
G, S = ps["Gold"], ps["Silver"]
kpi = pd.read_csv("cpi_kopi.csv")
kpi.index = pd.PeriodIndex(kpi.iloc[:, 0], freq="M")
kpi = kpi.iloc[:, 1].astype(float).reindex(G.index).ffill()
Greal = G / kpi
aksjer = {}
for sym in ("^XAU", "GDX"):
    try:
        aksjer[sym] = yahoo_mnd(sym)
    except Exception as e:
        print(f"   {sym} ikke hentet ({type(e).__name__})")
print(f"Data: gull og soelv {G.index[0]} til {G.index[-1]}; " +
      ", ".join(f"{k} fra {v.index[0]}" for k, v in aksjer.items()))


def rapport(terskel, vis=True):
    sig, opp = signaler(G, S, terskel)
    rader = []
    for t in sig:
        r = {"t": str(t), "G/S": round(G[t] / S[t], 1),
             "gull12": fram(G, t, 12), "gull24": fram(G, t, 24),
             "gullreal12": fram(Greal, t, 12), "solv12": fram(S, t, 12)}
        for k, v in aksjer.items():
            r[k + "12"] = fram(v, t, 12)
        rader.append(r)
    df = pd.DataFrame(rader)
    nylig = set()
    for t in sig:
        nylig |= {t + i for i in range(1, 4)}
    basis = [t for t in G.index if t >= START and bool(opp.get(t, False)) and t not in nylig and t not in sig]
    b12 = pd.Series([fram(G, t, 12) for t in basis]).dropna()
    full = df[df["gull12"].notna()] if len(df) else df
    med_sig = float(full["gull12"].median()) if len(full) else np.nan
    neg = int((full["gull12"] < 0).sum()) if len(full) else 0
    b_ok = len(full) > 0 and (med_sig <= b12.median() - 0.10) and neg * 3 >= 2 * len(full)
    treff = [g for g in GR if any(abs((pd.Period(g, "M") - s).n) <= 4 for s in sig)]
    if vis:
        print(f"\n--- terskel {int(terskel * 100)} pp: {len(sig)} signaler")
        if len(df):
            vis_df = df.copy()
            for c in vis_df.columns:
                if c not in ("t", "G/S"):
                    vis_df[c] = (100 * vis_df[c]).round(0)
            print(vis_df.to_string(index=False))
        print(f"   G&R-episoder funnet: {len(treff)} av 5 ({', '.join(treff)})")
        print(f"   gull 12 mnd: median etter signal {100 * med_sig:+.0f} % ({len(full)} signaler med 12 mnd etter, "
              f"{neg} negative); basis {len(b12)} mnd, median {100 * b12.median():+.0f} %")
        print(f"   (b) {'holder' if b_ok else 'holder ikke'}")
    return len(treff), b_ok


print("\n1. HOVEDREGELEN")
treff, b40 = rapport(TERSKEL)
print("\n2. PLATAA")
_, b30 = rapport(0.30)
_, b50 = rapport(0.50)
a_ok = treff >= 4
print("\n3. AVGJOERELSE (kriterier satt foer kjoering)")
print(f"   (a) gjenkjenning {treff} av 5: {'ok' if a_ok else 'ikke ok'}")
print(f"   (b) terskel 40: {'ok' if b40 else 'ikke ok'}")
print(f"   (c) plataa 30 og 50: {'ok' if (b30 and b50) else 'ikke ok'}")
print(f"   -> {'HOLDER' if (a_ok and b40 and b30 and b50) else 'HOLDER IKKE'}")
