# ---------------------------------------------------------------------------
# sonde_kjor_dadj: gir ujustert kurs feil kapitulasjonsskaar D?
#
# kapitulasjon_d.py bruker Yahoo sin "close", som er justert for splitt, men
# ikke for utbytte og andre kapitalutdelinger. For et papir som deler ut det
# meste av overskuddet, som 2020 Bulkers (maanedlig utbytte), faller kursen
# med hver utbetaling uten at noen har gitt opp. 25.09.2026 sto 2020 Bulkers
# med fall -95,9 % fra femaarstopp og D 95,4, og trakk capesize opp.
#
# Sonden regner D paa to maater for alle papirene og temafondene: som i dag
# (close) og utbyttejustert (adjclose), med noyaktig samme regnestykke som
# kapitulasjon_d.py (kopiert under, ikke importert, fordi den filen henter og
# skriver naar den lastes). Den endrer ingenting.
#
# Forhaandsregel: sonden er beskrivende. Bytte til adjclose er en retting av
# maalingen, ikke en ny regel, men den flytter D for alle papirer med utbytte,
# og legges derfor fram for Frode med tallene foer den tas i bruk.
# ---------------------------------------------------------------------------

import time
import numpy as np, pandas as pd, requests

from instrumenter import INSTR

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
MIN_HIST, TOPPVINDU, FULLT_FALL = 60, 60, 30
TEMA = {"kobber": "COPX", "gold": "GDX",
        "jernmalm": "XME", "nikkel": "XME", "sink": "XME", "bly": "XME",
        "tinn": "XME", "aluminium": "XME",
        "brent": "XOP", "wti": "XOP", "henryhub": "XOP", "ttf": "XOP",
        "urea": "MOO", "kalium": "MOO",
        "ship_capesize": "BDRY", "ship_kamsarmax": "BDRY",
        "ship_ultramax": "BDRY", "ship_handysize": "BDRY"}


def to_kurser(sym):
    r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}",
                     params={"range": "max", "interval": "1d", "events": "div,split"},
                     headers=UA, timeout=30)
    r.raise_for_status()
    res = r.json()["chart"]["result"][0]
    tz = (res.get("meta") or {}).get("exchangeTimezoneName") or "UTC"
    idx = pd.to_datetime(res["timestamp"], unit="s", utc=True).tz_convert(tz)
    idx = idx.normalize().tz_localize(None)
    c = pd.Series(res["indicators"]["quote"][0]["close"], index=idx)
    adj = (res["indicators"].get("adjclose") or [{}])[0].get("adjclose")
    a = pd.Series(adj, index=idx) if adj else None
    n_utb = len((res.get("events") or {}).get("dividends") or {})
    rens = lambda s: s.dropna()[~s.dropna().index.duplicated(keep="last")]
    return rens(c), (rens(a) if a is not None else None), n_utb


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


def ledd(daglig):
    m = daglig.resample("ME").last().dropna()
    m.index = m.index.to_period("M")
    topp = m.rolling(TOPPVINDU, min_periods=12).max()
    fall = (m / topp - 1) * 100
    ma = daglig.rolling(200, min_periods=120).mean()
    uke = (daglig < ma).resample("W").last().dropna().astype(float)
    and52 = uke.rolling(52, min_periods=26).mean() * 100
    a = and52.resample("ME").last()
    a.index = a.index.to_period("M")
    return fall, a.reindex(fall.index)


def dskaar(daglig):
    fall, u200 = ledd(daglig)
    d = np.nanmean(np.vstack([exp_pct(fall.values), exp_pct(-u200.values)]), axis=0)
    d = d * np.clip(np.abs(fall.values) / FULLT_FALL, 0, 1)
    if (~np.isnan(d)).sum() < 12:
        return None, None
    i = len(d) - 1
    while i >= 0 and np.isnan(d[i]):
        i -= 1
    return round(float(d[i]), 1), round(float(fall.values[i]), 1)


print("1. Papirer: D med ujustert kurs (i dag) og utbyttejustert")
print(f"   {'ticker':12s} {'utb':>4} {'fall':>7} {'D':>6} | {'fall adj':>8} {'D adj':>6} {'endring':>8}")
PAP, TYP = {}, {}
for sid, rader in INSTR.items():
    for tk, bors, navn, typ, kom in rader:
        TYP[tk] = typ
        PAP.setdefault(tk, set()).add(sid)
alle = sorted(PAP) + sorted(set(TEMA.values()))
RES, mangler = {}, []
for tk in alle:
    try:
        c, a, nu = to_kurser(tk)
        d0, f0 = dskaar(c)
        if a is None:
            mangler.append(tk); d1, f1 = None, None
        else:
            d1, f1 = dskaar(a)
        RES[tk] = (d0, f0, d1, f1, nu)
        if d0 is not None:
            e = "" if d1 is None else f"{d1 - d0:+8.1f}"
            print(f"   {tk:12s} {nu:4d} {f0:6.1f}% {d0:6.1f} | "
                  + (f"{f1:7.1f}% {d1:6.1f} {e}" if d1 is not None else "   adjclose mangler"))
    except Exception as ex:
        print(f"   {tk:12s} FEIL {type(ex).__name__} {str(ex)[:50]}")
    time.sleep(0.2)

ok = [v for v in RES.values() if v[0] is not None and v[2] is not None]
diff = np.array([v[2] - v[0] for v in ok])
print(f"\n   {len(ok)} papirer med begge. Endring i D: median {np.median(diff):+.1f}, "
      f"|endring| over 10: {int((np.abs(diff) > 10).sum())}, over 25: {int((np.abs(diff) > 25).sum())}")
if mangler:
    print(f"   adjclose mangler for: {', '.join(mangler)}")

print("\n2. Segmentene: D i dag og utbyttejustert (median av papirene, 2:1 mot temafondet)")
for sid in INSTR:
    egne = [tk for tk in PAP if sid in PAP[tk] and not str(TYP[tk]).lower().startswith("etc")
            and tk in RES and RES[tk][0] is not None]
    t = TEMA.get(sid)
    ut = []
    for k in (0, 2):
        vals = [RES[tk][k] for tk in egne if RES[tk][k] is not None]
        td = RES.get(t, (None,) * 5)[k] if t else None
        if not vals:
            ut.append(td); continue
        med = float(np.median(vals))
        ut.append(round(med if td is None else (med * 2 + td) / 3, 1))
    if ut[0] is not None or ut[1] is not None:
        e = "" if None in ut else f"{ut[1] - ut[0]:+6.1f}"
        print(f"   {sid:16s} {str(ut[0]):>6} -> {str(ut[1]):>6} {e}  (n={len(egne)})")
