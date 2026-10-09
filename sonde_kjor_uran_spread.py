# ---------------------------------------------------------------------------
# sonde_kjor_uran_spread: spotpris mot langsiktig kontraktspris for uran som
# signal for uranaksjene (G&R, Q2 2026-brevet)
#
# Frodes bestilling 09.10.2026: test foer det blir et felt paa dashbordet.
# G&Rs paastand: rundt 90 % av uranet handles paa kontrakt mellom gruver og
# kraftselskaper, mens spot (10 %) styres mer av fond. Naar spot ligger klart
# under kontraktsprisen, har spekulantene gitt opp, og sterke oppganger har
# fulgt. Naar spot ligger over, er de ivrige, og fall har fulgt.
#
# ALT UNDER ER SATT FOER KJOERING
#
# DATA     Cameco, maanedsslutt for spot og langsiktig kontraktspris (snitt av
#          UxC og TradeTech), kontraktspris fra 1996-03. Aksjen er Cameco
#          (CCJ, fra 1996-04), utbyttejustert, i dollar. Markedet er SPY.
#          URA (fra 2010) og URNM (fra 2019) vises, men avgjoer ikke.
# MAAL     spread_t = spot_t / kontrakt_t - 1.
# UTFALL   Meravkastning for CCJ over SPY de neste 12 maanedene fra
#          maanedsslutt t. Spot 12 maaneder fram vises, men avgjoer ikke.
#
# AVGJOER  Feltet regnes som STOETTET bare hvis alle tre holder:
#   (a) Rangkorrelasjon (Spearman) mellom spread og CCJs meravkastning 12
#       mnd fram er negativ. Fordi maanedene overlapper, regnes den paa ikke-
#       overlappende utvalg: ett for hver av de 12 startmaanedene (hver 12.
#       maaned). Holder hvis medianen av de 12 er -0,20 eller lavere og minst
#       9 av 12 er negative.
#   (b) Grupper: median meravkastning 12 mnd etter maaneder med spread paa
#       -10 % eller lavere er minst 15 prosentpoeng hoeyere enn etter
#       maaneder med spread paa 0 eller hoeyere.
#   (c) Plataa og periode: (b) holder ogsaa med terskel -5 % og -15 %, og
#       ogsaa naar bare maaneder fra 2010 regnes med (etter at fond og
#       finansielle aktoerer ble store i uran).
#   Holder ikke (a) til (c), kan feltet likevel staa som kontekst, merket
#   ikke testet med hell, som VIX og dollaren. Det er Frodes valg.
#
# FORBEHOLD  Kontraktsprisen er en indikator som oppdateres sjeldnere enn
#          spot; lange perioder med uendret kontraktspris gir spread som
#          bare foelger spot. Cameco er ett selskap. Paastanden er kjent fra
#          G&R, og deres eksempler (2025 og 2026) ligger i dataene.
# ---------------------------------------------------------------------------

import io
import numpy as np
import pandas as pd
import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}


def cameco():
    html = requests.get("https://www.cameco.com/invest/markets/uranium-price", headers=UA, timeout=40).text
    for t in pd.read_html(io.StringIO(html)):
        k = [c for c in t.columns if "long" in str(c).lower()]
        s = [c for c in t.columns if "spot" in str(c).lower()]
        if k and s and len(t) > 300:
            idx = pd.PeriodIndex(pd.to_datetime(t.iloc[:, 0].astype(str).str.replace("/", "-")), freq="M")
            df = pd.DataFrame({"spot": pd.to_numeric(t[s[0]], errors="coerce").values,
                               "kontrakt": pd.to_numeric(t[k[0]], errors="coerce").values}, index=idx)
            return df[~df.index.duplicated(keep="last")].dropna()
    raise ValueError("fant ikke tabellen")


def yahoo_mnd(sym):
    r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}",
                     params={"range": "max", "interval": "1d", "events": "div,split"},
                     headers=UA, timeout=60).json()["chart"]["result"][0]
    adj = ((r["indicators"].get("adjclose") or [{}])[0] or {}).get("adjclose") or r["indicators"]["quote"][0]["close"]
    s = pd.Series(adj, index=pd.to_datetime(r["timestamp"], unit="s"), dtype=float).dropna()
    m = s.resample("ME").last().dropna()
    m.index = m.index.to_period("M")
    return m


u = cameco()
px = {s: yahoo_mnd(s) for s in ("CCJ", "SPY", "URA", "URNM")}
u["spread"] = u["spot"] / u["kontrakt"] - 1


def mer(sym, h=12):
    a, b = px[sym], px["SPY"]
    return (a.shift(-h) / a - 1) - (b.shift(-h) / b - 1)


d = u.copy()
for s in ("CCJ", "URA", "URNM"):
    d[s] = mer(s).reindex(d.index)
d["spot12"] = (u["spot"].shift(-12) / u["spot"] - 1)
d = d[d.index >= pd.Period("1996-04", "M")]
print(f"Data: {d.index[0]} til {d.index[-1]}, {len(d)} mnd; CCJ med 12 mnd etter: {d['CCJ'].notna().sum()}")
print(f"Spread i dag ({d.index[-1]}): {100 * d['spread'].iloc[-1]:+.1f} %  (spot {d['spot'].iloc[-1]}, kontrakt {d['kontrakt'].iloc[-1]})")
print(f"Fordeling av spread: 10-pst {100 * d['spread'].quantile(.1):+.0f} %, median {100 * d['spread'].median():+.0f} %, "
      f"90-pst {100 * d['spread'].quantile(.9):+.0f} %")

print("\n1. RANGKORRELASJON PAA IKKE-OVERLAPPENDE UTVALG (a)")
x = d.dropna(subset=["CCJ"])
rho = []
for o in range(12):
    sub = x.iloc[o::12]
    rho.append(sub["spread"].rank().corr(sub["CCJ"].rank()))
rho = np.array(rho)
print("   " + " ".join(f"{r:+.2f}" for r in rho))
a_ok = np.median(rho) <= -0.20 and (rho < 0).sum() >= 9
print(f"   median {np.median(rho):+.2f}, negative {(rho < 0).sum()} av 12 -> {'ok' if a_ok else 'ikke ok'}")


def grupper(df, terskel, navn, vis=True):
    lav = df[df["spread"] <= terskel]
    hoy = df[df["spread"] >= 0]
    ml, mh = lav["CCJ"].median(), hoy["CCJ"].median()
    ok = len(lav) >= 6 and len(hoy) >= 6 and (ml - mh) >= 0.15
    if vis:
        print(f"   {navn:22s} terskel {int(terskel * 100):+d} %: lav {len(lav):3d} mnd median {100 * ml:+5.0f} % | "
              f"spread>=0 {len(hoy):3d} mnd median {100 * mh:+5.0f} % | diff {100 * (ml - mh):+5.0f} pp "
              f"(spot 12 mnd: {100 * lav['spot12'].median():+.0f} % mot {100 * hoy['spot12'].median():+.0f} %) "
              f"-> {'ok' if ok else 'ikke ok'}")
    return ok


print("\n2. GRUPPER, CCJ OVER SPY 12 MND (b)")
b_ok = grupper(x, -0.10, "hele perioden")
print("\n3. PLATAA OG PERIODE (c)")
c1 = grupper(x, -0.05, "hele perioden")
c2 = grupper(x, -0.15, "hele perioden")
x10 = x[x.index >= pd.Period("2010-01", "M")]
c3 = grupper(x10, -0.10, "fra 2010")
c_ok = c1 and c2 and c3

print("\n4. TIL OPPLYSNING: URA OG URNM (avgjoer ikke)")
for s in ("URA", "URNM"):
    y = d.dropna(subset=[s])
    lav, hoy = y[y["spread"] <= -0.10][s], y[y["spread"] >= 0][s]
    print(f"   {s}: spread <= -10 %: {len(lav)} mnd median {100 * lav.median():+.0f} %; "
          f"spread >= 0: {len(hoy)} mnd median {100 * hoy.median():+.0f} %")

print("\n5. EPISODER: maaneder med spread <= -10 % etter minst 12 mnd uten")
siste = None
for t, r in d.iterrows():
    if r["spread"] <= -0.10 and (siste is None or (t - siste).n > 12):
        ccj = "" if pd.isna(r["CCJ"]) else f"{100 * r['CCJ']:+.0f} %"
        print(f"   {t}: spread {100 * r['spread']:+.0f} %, CCJ over SPY 12 mnd {ccj}")
    if r["spread"] <= -0.10:
        siste = t

print("\n6. AVGJOERELSE (kriterier satt foer kjoering)")
print(f"   (a) {'ok' if a_ok else 'ikke ok'}, (b) {'ok' if b_ok else 'ikke ok'}, (c) {'ok' if c_ok else 'ikke ok'}")
print(f"   -> {'STOETTET' if (a_ok and b_ok and c_ok) else 'IKKE STOETTET'}")
