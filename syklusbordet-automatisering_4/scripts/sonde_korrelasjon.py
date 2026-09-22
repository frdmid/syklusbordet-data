# ---------------------------------------------------------------------------
# Syklusbordet: uttrykker instrumentene faktisk raavaren
#
# Instrumentlaget hviler paa en uproevd antakelse: at de 93 papirene beveger
# seg med segmentet sitt. Denne maaler det.
#
# Paa de ni parene der det fantes data fra for, var svaret ujevnt. Aker BP mot
# Brent gir korrelasjon 0,58 og forklarer 34 % av variasjonen. Yara mot urea
# gir 0,16 og forklarer 3 %. Det siste er verdt aa vite for det staar som
# instrument i bordet.
#
# NB paa tidssone. Yahoo tidsstempler maanedsstolpen ved maanedens start i
# borsens lokale tid. Leses den som UTC, havner hele serien en maaned for
# tidlig for alt utenfor amerikansk tid, og korrelasjonen kollapser fra 0,58
# til -0,02. Det var en reell feil i innhentingen fram til i dag.
#
# Skriver ingenting.
# ---------------------------------------------------------------------------

REPO, BRANCH = "frdmid/syklusbordet-data", "main"
RAW = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}"

import json, time, warnings
import numpy as np, pandas as pd, requests
warnings.filterwarnings("ignore")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}

from instrumenter import INSTR


def maanedskurs(sym):
    r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}",
                     params={"range": "15y", "interval": "1mo"}, headers=UA, timeout=25)
    r.raise_for_status()
    res = r.json()["chart"]["result"][0]
    tz = (res.get("meta") or {}).get("exchangeTimezoneName") or "UTC"
    idx = pd.to_datetime(res["timestamp"], unit="s", utc=True).tz_convert(tz)
    s = pd.Series(res["indicators"]["quote"][0]["close"], index=idx).dropna()
    s.index = s.index.to_period("M")
    return s[~s.index.duplicated(keep="last")], tz


print("1. Henter raavareseriene fra repoet")
idx = requests.get(f"{RAW}/index.json?cb={int(time.time())}",
                   headers={**UA, "Cache-Control": "no-cache"}, timeout=30).json()
SEG = {}
for sid in idx["segmenter"] + [f"ship_{x}" for x in
        ("vlcc","suezmax","aframax","kamsarmax","ultramax","capesize","handysize")]:
    try:
        d = requests.get(f"{RAW}/segments/{sid}.json?cb={int(time.time())}",
                         headers={**UA, "Cache-Control": "no-cache"}, timeout=30).json()
        s = pd.Series({pd.Period(r["t"], "M"): r["nom"] for r in d["series"]}).sort_index()
        A = pd.Series({pd.Period(r["t"], "M"): r.get("A") for r in d["series"]}).sort_index()
        SEG[sid] = (s, A)
    except Exception as e:
        print(f"   {sid}: {type(e).__name__}")
print(f"   {len(SEG)} segmenter")

print("\n2. Henter kurser for instrumentene")
PAR = [(tk, sid, b) for sid, rader in INSTR.items() for tk, b, *_ in rader if sid in SEG]
KURS, tzer = {}, {}
for tk in sorted({t for t, _, _ in PAR}):
    try:
        KURS[tk], tzer[tk] = maanedskurs(tk)
    except Exception as e:
        print(f"   {tk:14s} FEIL {type(e).__name__} {str(e)[:40]}")
    time.sleep(0.25)
print(f"   {len(KURS)} av {len({t for t,_,_ in PAR})} instrumenter")

print("\n3. Samsvar mellom instrument og segment")
print("   R2 er andelen av instrumentets bevegelse som raavaren forklarer.")
print("   beta opp og ned viser om papiret tar oppsiden eller bare nedsiden.")
print("   forsk. er hvilken forskyvning som gir hoyest korrelasjon. Alt annet")
print("   enn 0 betyr at noe er feil justert, eller at prisen er et snitt.\n")
print(f"   {'instrument':12s} {'segment':16s} {'bors':>10} {'n':>4} {'korr':>6} {'R2':>5} "
      f"{'beta':>6} {'opp':>6} {'ned':>6} {'vol i/r':>8} {'forsk.':>7}")
ut = []
for tk, sid, bors in sorted(PAR, key=lambda x: (x[1], x[0])):
    if tk not in KURS:
        continue
    nom, A = SEG[sid]
    x = np.log(nom).diff(); y = np.log(KURS[tk]).diff()
    felles = x.index.intersection(y.index)
    x, y = x.reindex(felles), y.reindex(felles)
    m = x.notna() & y.notna() & np.isfinite(x) & np.isfinite(y)
    if m.sum() < 36:
        print(f"   {tk:12s} {sid:16s} {bors:>10} {int(m.sum()):>4}   for kort")
        continue
    xx, yy = x[m], y[m]
    r = float(np.corrcoef(xx, yy)[0, 1]); b = float(np.polyfit(xx, yy, 1)[0])
    bo = float(np.polyfit(xx[xx > 0], yy[xx > 0], 1)[0]) if (xx > 0).sum() > 20 else np.nan
    bn = float(np.polyfit(xx[xx < 0], yy[xx < 0], 1)[0]) if (xx < 0).sum() > 20 else np.nan
    lag = {}
    for k in (-1, 0, 1, 2):
        yk = y.shift(k); mk = x.notna() & yk.notna() & np.isfinite(x) & np.isfinite(yk)
        lag[k] = float(np.corrcoef(x[mk], yk[mk])[0, 1]) if mk.sum() > 30 else -9
    best = max(lag, key=lag.get)
    sone = (A.reindex(felles) >= 80).fillna(False)
    ri = (float(np.corrcoef(xx[sone[m]], yy[sone[m]])[0, 1])
          if (sone & m).sum() > 24 else np.nan)
    ut.append(dict(tk=tk, seg=sid, bors=bors, n=int(m.sum()), r=r, b=b, bo=bo, bn=bn,
                   vol=float(yy.std() / xx.std()), lag=best, r_sone=ri))
    print(f"   {tk:12s} {sid:16s} {bors:>10} {int(m.sum()):>4} {r:6.2f} {r*r:5.2f} "
          f"{b:6.2f} {bo:6.2f} {bn:6.2f} {yy.std()/xx.std():8.2f} {best:+7d}")

D = pd.DataFrame(ut)
if not D.empty:
    print(f"\n4. Sammendrag over {len(D)} par")
    print(f"   median korrelasjon {D.r.median():.2f}, median R2 {(D.r**2).median():.2f}")
    print(f"   {int((D.r < 0.3).sum())} par under 0,30 i korrelasjon. De uttrykker i praksis")
    print(f"   noe annet enn segmentet sitt:")
    for _, q in D[D.r < 0.3].sort_values("r").iterrows():
        print(f"      {q.tk:12s} {q.seg:16s} korr {q.r:5.2f}  R2 {q.r**2:.2f}")
    print(f"\n   {int((D.bn > D.bo).sum())} par tar mer av nedsiden enn av oppsiden:")
    for _, q in D[D.bn > D.bo].sort_values("bo").head(12).iterrows():
        print(f"      {q.tk:12s} {q.seg:16s} opp {q.bo:5.2f}  ned {q.bn:5.2f}")
    d = D[D.lag != 0]
    if len(d):
        print(f"\n   {len(d)} par har hoyest korrelasjon ved en forskyvning:")
        for _, q in d.iterrows():
            print(f"      {q.tk:12s} {q.seg:16s} forskyvning {q.lag:+d}")
    print("\n   Beste og verste:")
    for _, q in D.nlargest(5, "r").iterrows():
        print(f"      {q.tk:12s} {q.seg:16s} korr {q.r:5.2f}  beta {q.b:5.2f}")
    print("      ...")
    for _, q in D.nsmallest(5, "r").iterrows():
        print(f"      {q.tk:12s} {q.seg:16s} korr {q.r:5.2f}  beta {q.b:5.2f}")

# ------------------------------------------------- 5. leder aksjen raavaren

print("\n5. Ledetid, maalt paa dagsdata")
print("   Maanedsdata kan ikke svare paa dette: leder aksjen med to til seks uker,")
print("   ser det ut som samtidighet i en maanedsserie. Her korreleres daglige")
print("   endringer ved forskyvninger fra -20 til +20 borsdager. Negativ topp")
print("   betyr at aksjen beveger seg FOR raavaren.\n")

def dagskurs(sym, aar=10):
    r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}",
                     params={"range": f"{aar}y", "interval": "1d"}, headers=UA, timeout=25)
    r.raise_for_status()
    res = r.json()["chart"]["result"][0]
    tz = (res.get("meta") or {}).get("exchangeTimezoneName") or "UTC"
    idx = pd.to_datetime(res["timestamp"], unit="s", utc=True).tz_convert(tz).normalize().tz_localize(None)
    s = pd.Series(res["indicators"]["quote"][0]["close"], index=idx).dropna()
    return s[~s.index.duplicated(keep="last")]

# Raavarer med daglig notering. Pink Sheet er maanedlig og kan ikke brukes her.
DAGLIG = {"brent": "BZ=F", "wti": "CL=F", "henryhub": "NG=F", "gold": "GC=F",
          "kobber": "HG=F"}
print(f"   {'instrument':12s} {'segment':10s} {'n':>5} {'r ved 0':>8} {'beste lag':>10} "
      f"{'r der':>7}  {'tolkning':>22}")
for sid, futt in DAGLIG.items():
    try:
        rv = dagskurs(futt)
    except Exception as e:
        print(f"   raavare {sid} ({futt}): {type(e).__name__} {str(e)[:40]}")
        continue
    x = np.log(rv).diff()
    for tk, s_, b in [(t, s2, b2) for t, s2, b2 in PAR if s2 == sid]:
        try:
            y = np.log(dagskurs(tk)).diff()
        except Exception:
            continue
        felles = x.index.intersection(y.index)
        if len(felles) < 500:
            continue
        xx, yy = x.reindex(felles), y.reindex(felles)
        rr = {}
        for k in range(-20, 21):
            yk = yy.shift(k)
            m = xx.notna() & yk.notna() & np.isfinite(xx) & np.isfinite(yk)
            if m.sum() > 200:
                rr[k] = float(np.corrcoef(xx[m], yk[m])[0, 1])
        if not rr:
            continue
        best = max(rr, key=rr.get)
        tolk = ("samtidig" if best == 0 else
                (f"aksjen leder {-best} dager" if best < 0 else
                 f"aksjen folger {best} dager etter"))
        print(f"   {tk:12s} {sid:10s} {len(felles):>5} {rr.get(0, float('nan')):8.2f} "
              f"{best:+10d} {rr[best]:7.2f}  {tolk:>22}")
        time.sleep(0.25)


print("\n" + "=" * 78)
print("Et instrument med korrelasjon under 0,30 uttrykker ikke segmentet.")
print("Et med hoyere beta ned enn opp gir deg nedsiden uten oppsiden.")
