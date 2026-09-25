# ---------------------------------------------------------------------------
# sonde_kjor_kurve: hvor finnes terminkurven, gratis og fra Actions
#
# Kurveform er det tredje kontekstfeltet over grafen, og det eneste som ikke
# hentes. Foer det kan bygges maa tre ting vaere kjent, per raavare:
#   1. finnes dagens kurve, altsaa pris paa enkeltkontrakter flere maaneder ut
#   2. finnes kurven BAKOVER i tid, slik at dagens form kan leses mot egen
#      historikk som COT og BDI (en helning uten historikk er bare et tall)
#   3. hvor mange maaneder ut kurven rekker
#
# Tre kilder proeves:
#   A. Yahoo, enkeltkontrakter med maanedskode (CLZ26.NYM osv.). Gir dagens
#      kurve. Om utloepte kontrakter har historikk, avgjoer om kurven kan
#      bygges bakover.
#   B. EIA, NYMEX-kontrakt 1 til 4 for WTI og Henry Hub, daglig fra 1980- og
#      1990-tallet. Kort kurve, men lang historikk.
#   C. CME sine egne oppgjoerspriser. Proeves for aa vite, ventet stengt.
#
# Skriver ingenting til dashbordet. Lagrer det som ble funnet i
# sonder/kurve.json.
# ---------------------------------------------------------------------------

import io, json, os, subprocess, sys, time, datetime as dt
import numpy as np
import pandas as pd
import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
KODE = "FGHJKMNQUVXZ"
IDAG = dt.date.today()
UT = {}


def get(url, **kw):
    for i in range(3):
        try:
            r = requests.get(url, headers=kw.pop("headers", UA), timeout=kw.pop("timeout", 30), **kw)
            if r.status_code in (429, 502, 503):
                time.sleep(3 * (i + 1)); continue
            return r
        except requests.RequestException:
            if i == 2:
                raise
            time.sleep(2 * (i + 1))
    raise RuntimeError("ga opp")


def kontrakter(n=24):
    """Maanedskoder for de neste n maanedene, fra neste maaned."""
    ut, y, m = [], IDAG.year, IDAG.month
    for _ in range(n):
        m += 1
        if m > 12:
            m, y = 1, y + 1
        ut.append((y, m, f"{KODE[m - 1]}{y % 100:02d}"))
    return ut


def yahoo_siste(sym, rng_="5d"):
    r = get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range={rng_}&interval=1d")
    if r.status_code != 200:
        return None, r.status_code
    try:
        res = r.json()["chart"]["result"][0]
        c = [x for x in res["indicators"]["quote"][0]["close"] if x is not None]
        return (c[-1] if c else None), len(res.get("timestamp") or [])
    except Exception:
        return None, "tom"


# ======================================================== A. Yahoo
print("A. Yahoo, enkeltkontrakter\n")
ROTER = {
    "wti":      [("CL", "NYM")],
    "brent":    [("BZ", "NYM")],
    "henryhub": [("NG", "NYM")],
    "gold":     [("GC", "CMX")],
    "kobber":   [("HG", "CMX")],
    "kakao":    [("CC", "NYB")],
    "ttf":      [("TFM", "NYM"), ("TG", "NYM")],
    "uran":     [("UX", "CMX"), ("UX", "NYM")],
    "aluminium": [("ALI", "CMX")],
}
FRONT = {"wti": "CL=F", "brent": "BZ=F", "henryhub": "NG=F", "gold": "GC=F", "kobber": "HG=F",
         "kakao": "CC=F", "ttf": "TTF=F", "uran": "UX=F", "aluminium": "ALI=F"}
KUR = kontrakter(24)
for seg, roter in ROTER.items():
    front, _ = yahoo_siste(FRONT[seg])
    beste = None
    for rot, bors in roter:
        kurve = []
        for y, m, k in KUR:
            p, n = yahoo_siste(f"{rot}{k}.{bors}")
            if p:
                kurve.append((f"{y}-{m:02d}", round(float(p), 4)))
            time.sleep(0.15)
        if len(kurve) > (len(beste[1]) if beste else 0):
            beste = (f"{rot}.{bors}", kurve)
    if not beste or not beste[1]:
        print(f"   {seg:10} front {front}: ingen enkeltkontrakter svarte")
        UT[seg] = {"yahoo": None, "front": front}
        continue
    kv = beste[1]
    p0 = kv[0][1]
    def ut_til(mnd):
        k = [p for t, p in kv if (pd.Period(t, "M") - pd.Period(kv[0][0], "M")).n >= mnd]
        return k[0] if k else None
    p6, p12 = ut_til(6), ut_til(12)
    s6 = None if not p6 else round(100 * (p6 / p0 - 1), 2)
    s12 = None if not p12 else round(100 * (p12 / p0 - 1), 2)
    print(f"   {seg:10} {beste[0]:8} {len(kv):2} kontrakter {kv[0][0]}..{kv[-1][0]}  front {p0}  "
          f"6 mnd {s6 if s6 is not None else '-'} %  12 mnd {s12 if s12 is not None else '-'} %")
    UT[seg] = {"yahoo": {"rot": beste[0], "kurve": kv, "helning6": s6, "helning12": s12}, "front": front}

# Har utloepte kontrakter historikk? Avgjoer om kurven kan bygges bakover.
print("\n   Utloepte kontrakter (historikk bakover):")
for sym in ("CLZ20.NYM", "CLZ15.NYM", "CLZ10.NYM", "NGZ20.NYM", "GCZ20.CMX", "HGZ20.CMX", "CCZ20.NYB", "BZZ20.NYM"):
    r = get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range=max&interval=1d")
    try:
        res = r.json()["chart"]["result"][0]
        ts = res.get("timestamp") or []
        print(f"      {sym:10} HTTP {r.status_code}, {len(ts)} dager"
              + (f", {dt.date.fromtimestamp(ts[0])} til {dt.date.fromtimestamp(ts[-1])}" if ts else ""))
    except Exception:
        print(f"      {sym:10} HTTP {r.status_code}, ingen serie")
    time.sleep(0.3)


# ================================ D. tolvmaanedershelningen bakover i tid
# Frode 24.09: kurven 12 maaneder fram er nok, men den trenger persentil for
# aa vise hvor sterk strukturen er. Persentil krever historikk. Her proeves
# det aa bygge helningen bakover fra utloepte kontrakter: ved hver
# maanedsslutt velges naermeste kontrakt som front og kontrakten naermest 12
# maaneder senere som bak, og helningen er bak delt paa front minus 1.
print("\nD. Tolvmaanedershelning bakover, fra utloepte kontrakter\n")

def kontraktserie(sym):
    r = get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range=max&interval=1d")
    if r.status_code != 200:
        return None
    try:
        res = r.json()["chart"]["result"][0]
        ts, c = res.get("timestamp") or [], res["indicators"]["quote"][0]["close"]
        s = pd.Series(c, index=pd.to_datetime(ts, unit="s")).dropna()
        s = s[s > 0]
        return s.groupby(s.index.to_period("M")).last() if len(s) else None
    except Exception:
        return None

HIST = {}
for seg, info in UT.items():
    y = (info or {}).get("yahoo")
    if not y:
        continue
    rot, bors = y["rot"].split(".")
    serier = {}
    for aar in range(2016, IDAG.year + 3):
        for m in range(1, 13):
            s = kontraktserie(f"{rot}{KODE[m - 1]}{aar % 100:02d}.{bors}")
            if s is not None and len(s):
                serier[pd.Period(f"{aar}-{m:02d}", "M")] = s
            time.sleep(0.12)
    hel = {}
    for t in pd.period_range("2016-06", pd.Period(IDAG, "M"), freq="M"):
        tilgj = {d: s[t] for d, s in serier.items() if t in s.index and d > t}
        if len(tilgj) < 2:
            continue
        front = min(tilgj)
        bak = min(tilgj, key=lambda d: abs((d - front).n - 12))
        if abs((bak - front).n - 12) > 1:
            continue
        hel[t] = 100 * (tilgj[bak] / tilgj[front] - 1)
    hel = pd.Series(hel).sort_index()
    if len(hel) < 12:
        print(f"   {seg:10} {len(serier)} kontrakter med historikk, {len(hel)} maaneder med helning. For lite.")
        HIST[seg] = {"kontrakter": len(serier), "mnd": len(hel)}
        continue
    siste = hel.iloc[-1]
    p_alle = round(100 * float((hel <= siste).mean()), 1)
    tre = hel.iloc[-36:]
    p_tre = round(100 * float((tre <= siste).mean()), 1)
    print(f"   {seg:10} {len(serier):3} kontrakter, {len(hel):3} maaneder {hel.index[0]}..{hel.index[-1]}. "
          f"Siste {siste:+.2f} %, persentil {p_alle} (alle) / {p_tre} (3 aar). "
          f"Spenn {hel.min():+.1f} til {hel.max():+.1f} %. Hull: {len(pd.period_range(hel.index[0], hel.index[-1], freq='M')) - len(hel)} mnd")
    HIST[seg] = {"kontrakter": len(serier), "mnd": len(hel), "fra": str(hel.index[0]),
                 "siste": round(float(siste), 2), "pctl_alle": p_alle, "pctl_3aar": p_tre,
                 "serie": {str(k): round(float(v), 3) for k, v in hel.items()}}
UT["_historikk"] = HIST

# Rente, for aa skille contango som bare er finansiering fra reell overflod
irx, _ = yahoo_siste("^IRX")
print(f"\n   13 ukers statspapir (^IRX): {irx}")
UT["_rente"] = irx


# ======================================================== B. EIA
print("\nB. EIA, NYMEX kontrakt 1 til 4\n")
try:
    import xlrd  # noqa
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "xlrd"], check=False)
EIA = {"wti": ("pet", "RCLC"), "henryhub": ("ng", "RNGC")}
for seg, (omr, kode) in EIA.items():
    ser = {}
    for i in (1, 2, 3, 4):
        u = f"https://www.eia.gov/dnav/{omr}/hist_xls/{kode}{i}d.xls"
        try:
            r = get(u, timeout=60)
            if r.status_code != 200:
                print(f"   {seg:10} kontrakt {i}: HTTP {r.status_code}"); continue
            ark = pd.read_excel(io.BytesIO(r.content), sheet_name=None, header=None)
            data = next((df for navn, df in ark.items() if "data" in str(navn).lower()), list(ark.values())[-1])
            df = data.dropna()
            df = df[pd.to_datetime(df.iloc[:, 0], errors="coerce").notna()]
            s = pd.Series(pd.to_numeric(df.iloc[:, 1], errors="coerce").values,
                          index=pd.to_datetime(df.iloc[:, 0])).dropna()
            ser[i] = s
            print(f"   {seg:10} kontrakt {i}: {len(s)} dager, {s.index[0].date()} til {s.index[-1].date()}, siste {s.iloc[-1]}")
        except Exception as e:
            print(f"   {seg:10} kontrakt {i}: {type(e).__name__} {str(e)[:60]}")
        time.sleep(0.5)
    if 1 in ser and 4 in ser:
        d = pd.concat([ser[1], ser[4]], axis=1).dropna()
        d = d[(d.iloc[:, 0] > 0) & (d.iloc[:, 1] > 0)]
        m = d.resample("ME").last()
        hel = 100 * (m.iloc[:, 1] / m.iloc[:, 0] - 1)
        hel = hel.dropna()
        pctl = round(100 * float((hel <= hel.iloc[-1]).mean()), 1)
        tre = hel.iloc[-36:]
        pctl3 = round(100 * float((tre <= tre.iloc[-1]).mean()), 1)
        print(f"      helning kontrakt 1 til 4, maanedsslutt: {len(hel)} mnd fra {hel.index[0].date()}. "
              f"Siste {hel.iloc[-1]:+.2f} %, persentil {pctl} mot hele historikken, {pctl3} mot tre aar. "
              f"Andel maaneder i backwardation: {100 * (hel < 0).mean():.0f} %")
        UT.setdefault(seg, {})["eia"] = {"mnd": len(hel), "fra": str(hel.index[0].date()),
                                         "siste": round(float(hel.iloc[-1]), 2), "pctl_alle": pctl, "pctl_3aar": pctl3}


# ======================================================== C. CME
print("\nC. CME oppgjoerspriser")
for u in ("https://www.cme.com/CmeWS/mvc/Settlements/Futures/Settlements/425/FUT",
          "https://www.cmegroup.com/CmeWS/mvc/Settlements/Futures/Settlements/425/FUT"):
    try:
        r = get(u, headers={**UA, "Accept": "application/json"})
        print(f"   {u[8:50]:42} HTTP {r.status_code} {len(r.content)} byte")
    except Exception as e:
        print(f"   {u[8:50]:42} {type(e).__name__}")


os.makedirs("sonder", exist_ok=True)
json.dump(UT, open("sonder/kurve.json", "w"), ensure_ascii=False, indent=1, default=str)
print("\nLagret sonder/kurve.json")
print("\nHva som avgjoer videre: raavarer der del D gir minst tre aar med helning kan")
print("faa persentil straks. Ellers bygges historikken framover, uke for uke, og")
print("persentilen kommer naar den er lang nok. EIA gir kort kurve med lang")
print("historikk for WTI og Henry Hub, som kontroll.")
print("\nSend hele utskriften tilbake.")
