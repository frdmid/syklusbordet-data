# ---------------------------------------------------------------------------
# Syklusbordet: kapitulasjonsskaaren D
#
# Dokumentet: "Har alle gitt opp." Fall fra femaarstopp, uker under 200-dagers,
# revisjonsbredde, sektorvekt i indeks, ETF-forvaltningskapital. Ukentlig.
#
# Av de fem er to gratis og presise, ett finnes i en svakere form, og to er
# utenfor rekkevidde:
#   D1 fall fra femaarstopp        daglige kurser, eksakt
#   D2 andel uker under 200-dagers daglige kurser, eksakt
#   D3 temaets eget kursfall       naermeste frie erstatning for sektorvekt.
#                                  Det er IKKE forvaltningskapital: utstedernes
#                                  filer viser ingen kapitaltall i teksten.
#   revisjonsbredde                krever I/B/E/S, betalingsmur
#   sektorvekt i indeks            finnes ikke for shipping eller uran
#
# D maales mot selskapets EGEN historikk, ikke mot de andre selskapene i dag.
# En tverrsnittsrangering ville alltid hatt en toppdesil, ogsaa midt i en
# hoykonjunktur, og det er nettopp det som gjor en skaar ubrukelig.
#
# D maaler SELSKAPET. Etter at korrelasjonssonden viste median R2 paa 0,05
# mellom aksje og raavare, er det ikke en liten forskjell: A og B beskriver
# raavaren, C og D beskriver papiret du faktisk kjoper.
# ---------------------------------------------------------------------------

REPO, BRANCH = "frdmid/syklusbordet-data", "main"

import base64, json, os, time, warnings
warnings.filterwarnings('ignore', message='Mean of empty slice')
import numpy as np, pandas as pd, requests

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
MIN_HIST = 60        # maaneder foer persentilen regnes, som for A
TOPPVINDU = 60       # femaarstopp
FULLT_FALL = 30      # prosent fall som gir persentilen full vekt

# Persentilen alene er skalafri og har derfor ingen absolutt forankring. En
# aksje som aldri har falt mer enn fem prosent faar D naer 100 naar den er ned
# fem prosent, fordi det er det verste den har gjort. Paa syntetiske serier ga
# en jevn oppgang D=63 av ren stoy. Skaaren dempes derfor med hvor stort
# fallet faktisk er, med full vekt fra 30 prosent og nedover.

from instrumenter import INSTR

# Tema-ETF per segment. Bare der koblingen er forsvarlig. XME er bredt metall,
# XOP olje og gass, MOO jordbruk, BDRY torrlast, GDX gull, COPX kobber.
TEMA = {"kobber": "COPX", "gold": "GDX",
        "jernmalm": "XME", "nikkel": "XME", "sink": "XME", "bly": "XME",
        "tinn": "XME", "aluminium": "XME",
        "brent": "XOP", "wti": "XOP", "henryhub": "XOP", "ttf": "XOP",
        "urea": "MOO", "kalium": "MOO",
        "ship_capesize": "BDRY", "ship_kamsarmax": "BDRY",
        "ship_ultramax": "BDRY", "ship_handysize": "BDRY"}


UTBYTTEJUSTERT = {}   # ticker -> True hvis utbyttejustert kurs ble brukt


def dagskurs(sym):
    """Daglig kurs, utbyttejustert (Yahoo adjclose), fra 25.09.2026.

    Foer dette brukte D "close", som er justert for splitt, men ikke for
    utbytte. Et papir som betaler ut det meste av overskuddet faller da med
    hver utbetaling uten at noen har gitt opp, og D ble for hoey. Sonden
    sonde_kjor_dadj.py maalte forskjellen paa 60 papirer: median endring 0,
    men Leroey 94,7 til 41,3, Nestle 98,9 til 48,2, Champion Iron 99,2 til
    49,6, og kakao som segment 95,9 til 48,2. D skal maale om markedet har
    gitt opp, og da er totalavkastningen riktig maal. Byttet godkjent av Frode
    25.09.2026. Mangler adjclose, brukes close, og det logges."""
    r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}",
                     params={"range": "max", "interval": "1d", "events": "div,split"},
                     headers=UA, timeout=30)
    r.raise_for_status()
    res = r.json()["chart"]["result"][0]
    tz = (res.get("meta") or {}).get("exchangeTimezoneName") or "UTC"
    idx = pd.to_datetime(res["timestamp"], unit="s", utc=True).tz_convert(tz)
    idx = idx.normalize().tz_localize(None)
    adj = ((res["indicators"].get("adjclose") or [{}])[0] or {}).get("adjclose")
    UTBYTTEJUSTERT[sym] = bool(adj)
    s = pd.Series(adj if adj else res["indicators"]["quote"][0]["close"], index=idx, dtype=float).dropna()
    return s[~s.index.duplicated(keep="last")]


def exp_pct(v, minn=MIN_HIST):
    """Punkt-i-tid persentil mot egen historikk. Returnerer HOY naar verdien er
    LAV, som for prisnivaaskaaren A. Kalleren maa derfor sende inn stoerrelser
    der lav verdi betyr kapitulert: fallet selv (mer negativt = verre) og
    MINUS andelen uker under 200-dagers.

    Foerste versjon sendte inn -fall og +andel, altsaa begge snudd feil vei, og
    ga D naer null paa bunnen av et 69 prosents fall. Feilen ble fanget av en
    syntetisk serie med et krasj i seg."""
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
    """D1 og D2 som maanedsserier, begge snudd slik at hoy verdi = kapitulert."""
    m = daglig.resample("ME").last().dropna()
    m.index = m.index.to_period("M")
    # D1: fall fra rullende femaarstopp. Mer negativt = mer kapitulert.
    topp = m.rolling(TOPPVINDU, min_periods=12).max()
    fall = (m / topp - 1) * 100
    # D2: andel av siste 52 uker under 200-dagers snitt.
    ma = daglig.rolling(200, min_periods=120).mean()
    uke = (daglig < ma).resample("W").last().dropna().astype(float)
    and52 = uke.rolling(52, min_periods=26).mean() * 100
    a = and52.resample("ME").last()
    a.index = a.index.to_period("M")
    return fall, a.reindex(fall.index)


print("1. Henter kurser")
AKSJER = {}
for sid, rader in INSTR.items():
    for tk, bors, navn, typ, kom in rader:
        AKSJER.setdefault(tk, {"navn": navn, "bors": bors, "typ": typ,
                               "segmenter": []})["segmenter"].append(sid)
alle = sorted(AKSJER) + sorted(set(TEMA.values()))
KURS = {}
for tk in alle:
    try:
        KURS[tk] = dagskurs(tk)
    except Exception as e:
        print(f"   {tk:12s} FEIL {type(e).__name__} {str(e)[:40]}")
    time.sleep(0.2)
print(f"   {len(KURS)} av {len(alle)} hentet, utbyttejustert: "
      f"{sum(UTBYTTEJUSTERT.get(t, False) for t in KURS)}"
      + (f", uten adjclose: {', '.join(t for t in KURS if not UTBYTTEJUSTERT.get(t))}"
         if any(not UTBYTTEJUSTERT.get(t) for t in KURS) else ""))

print("\n2. D per papir")
D = {}
print(f"   {'ticker':12s} {'fra':>8} {'mnd':>5} {'fall':>8} {'u<200d':>8} "
      f"{'D1':>6} {'D2':>6} {'D':>6}")
for tk in sorted(AKSJER):
    if tk not in KURS:
        continue
    try:
        fall, u200 = ledd(KURS[tk])
        d1, d2 = exp_pct(fall.values), exp_pct(-u200.values)
        d = np.nanmean(np.vstack([d1, d2]), axis=0)
        demp = np.clip(np.abs(fall.values) / FULLT_FALL, 0, 1)
        d = d * demp
        gyldig = ~np.isnan(d)
        if gyldig.sum() < 12:
            print(f"   {tk:12s} for kort historikk ({int(gyldig.sum())} mnd med skaar)")
            continue
        i = len(d) - 1
        while i >= 0 and np.isnan(d[i]):
            i -= 1
        D[tk] = {"ticker": tk, **{k: AKSJER[tk][k] for k in ("navn", "bors", "typ", "segmenter")},
                 "D": round(float(d[i]), 1),
                 "D1": None if np.isnan(d1[i]) else round(float(d1[i]), 1),
                 "demping": round(float(demp[i]), 2),
                 "D2": None if np.isnan(d2[i]) else round(float(d2[i]), 1),
                 "fall_pst": round(float(fall.values[i]), 1),
                 "uker_under_200d_pst": None if np.isnan(u200.values[i]) else round(float(u200.values[i]), 0),
                 "hist_start": str(fall.index[0]), "mnd_med_skaar": int(gyldig.sum()),
                 "serie": [{"t": str(p), "D": None if np.isnan(x) else round(float(x), 1)}
                           for p, x in list(zip(fall.index, d))[-180:]]}
        print(f"   {tk:12s} {str(fall.index[0]):>8} {len(fall):>5} "
              f"{fall.values[i]:7.1f}% {u200.values[i]:7.0f}% "
              f"{d1[i]:6.1f} {d2[i]:6.1f} {d[i]:6.1f}")
    except Exception as e:
        print(f"   {tk:12s} FEIL {type(e).__name__} {str(e)[:50]}")

print("\n3. Temaets eget kursfall")
TEMA_D = {}
for sym in sorted(set(TEMA.values())):
    if sym not in KURS:
        continue
    try:
        fall, u200 = ledd(KURS[sym])
        d = np.nanmean(np.vstack([exp_pct(fall.values), exp_pct(-u200.values)]), axis=0)
        d = d * np.clip(np.abs(fall.values) / FULLT_FALL, 0, 1)
        i = len(d) - 1
        while i >= 0 and np.isnan(d[i]):
            i -= 1
        if i >= 0:
            TEMA_D[sym] = {"D": round(float(d[i]), 1), "fall_pst": round(float(fall.values[i]), 1)}
            print(f"   {sym:6s} D={TEMA_D[sym]['D']:5.1f}  fall {TEMA_D[sym]['fall_pst']:6.1f} %")
    except Exception as e:
        print(f"   {sym:6s} FEIL {type(e).__name__}")

print("\n4. D per segment")
SEG = {}
for sid in INSTR:
    egne = [v for v in D.values() if sid in v["segmenter"] and not v["typ"].lower().startswith("etc")]
    t = TEMA.get(sid)
    td = TEMA_D.get(t, {}).get("D") if t else None
    if not egne:
        SEG[sid] = {"D": td, "n": 0, "tema": t, "tema_D": td, "papirer": []}
        continue
    # Medianen, ikke hoyeste. Dokumentet spor om ALLE har gitt opp, ikke om én har.
    med = float(np.median([v["D"] for v in egne]))
    samlet = med if td is None else round((med * 2 + td) / 3, 1)
    SEG[sid] = {"D": round(samlet, 1), "D_aksjer": round(med, 1), "n": len(egne),
                "tema": t, "tema_D": td,
                "spredning": [round(min(v["D"] for v in egne), 1),
                              round(max(v["D"] for v in egne), 1)],
                "papirer": [{"ticker": v["ticker"], "D": v["D"], "fall_pst": v["fall_pst"]}
                            for v in sorted(egne, key=lambda x: -x["D"])]}
for sid, v in sorted(SEG.items(), key=lambda x: -(x[1]["D"] or -1)):
    if v["n"]:
        print(f"   {sid:16s} D={v['D']:5.1f}  aksjer {v['D_aksjer']:5.1f} "
              f"(spenn {v['spredning'][0]:.0f}-{v['spredning'][1]:.0f}, n={v['n']})"
              + (f"  tema {v['tema']} {v['tema_D']:.0f}" if v["tema_D"] is not None else ""))

if GITHUB_TOKEN and D:
    api = f"https://api.github.com/repos/{REPO}/contents/d_kapitulasjon.json"
    h = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}
    sha = None
    g = requests.get(api, headers=h, params={"ref": BRANCH}, timeout=30)
    if g.status_code == 200:
        sha = g.json().get("sha")
    body = {"message": "kapitulasjon D", "branch": BRANCH,
            "content": base64.b64encode(json.dumps(
                {"oppdatert": str(pd.Timestamp.utcnow())[:19],
                 "papirer": D, "segmenter": SEG, "tema": TEMA_D,
                 "kurs": "utbyttejustert (Yahoo adjclose) fra 25.09.2026",
                 "uten_utbyttejustering": sorted(t for t in KURS if not UTBYTTEJUSTERT.get(t)),
                 "merknad": ("Kursen er utbyttejustert. D1 er fall fra rullende femaarstopp, D2 andelen av siste 52 "
                             "uker under 200-dagers snitt. Begge er persentiler mot papirets "
                             "EGEN historikk, punkt-i-tid, slik A er. Segmentets D er "
                             "medianen av aksjene, siden spoersmaalet er om alle har gitt opp "
                             "og ikke om én har, vektet to tredeler mot temaets eget kursfall "
                             "der en ETF passer. Revisjonsbredde og sektorvekt mangler: "
                             "betalingsmur og finnes ikke for disse segmentene. "
                             "Temaleddet er kursfall, IKKE forvaltningskapital. Skaaren dempes "
                             "med hvor stort fallet faktisk er, med full vekt fra "
                             "30 prosent: en persentil alene er skalafri og ville "
                             "gitt hoy D til et fall paa fem prosent.")},
                ensure_ascii=False).encode()).decode()}
    if sha:
        body["sha"] = sha
    requests.put(api, headers=h, json=body, timeout=60).raise_for_status()
    print(f"\n   publisert d_kapitulasjon.json ({len(D)} papirer, "
          f"{sum(1 for v in SEG.values() if v['n'])} segmenter)")
elif not GITHUB_TOKEN:
    print("\n   GITHUB_TOKEN mangler, ingenting publisert")
