# ---------------------------------------------------------------------------
# sonde_kjor_land: fondsregelen testet bakover paa Ken French sine landporteføljer
#
# Frodes beslutning 28.09.2026. Fondstesten i sonde_kjor_backtest stoppet der
# fondenes egne kurser starter (ENOR 2012, EWA 1996). Ken French har
# markedsporteføljer per land i dollar fra 1975. De gir fondsregelen for
# Norge og Australia de aarene fondene ikke fantes.
#
# REGELEN er den samme som paa dashbordet, med parene fra
# sonder/fondkart_forslag.json: minst to av fondets raavarer i et kvalifisert
# par har raa A >= 80, og minst en av dem staar i bunnsone. Til sammenligning:
# en av fondets raavarer i bunnsone. Innslag etter mer enn tolv maaneder uten.
#   Norge      brent+ttf, brent+aluminium, wti+ttf, wti+aluminium
#   Australia  kull+kobber
#   Brasil og andre land i kartet tas med hvis Ken French har en fil for dem.
#
# UTFALL som i de andre backtestene: 1, 2, 3, 6, 12 og 24 maaneder, mot
# landets eget snitt, mot det amerikanske markedet, episoder med hoeyst seks
# maaneder mellom, p fra 2000 tilfeldige episodedatoer.
#
# DET SOM AVGJOER, satt foer kjoering
#   Innslag FOER fondets egen kurshistorikk (Norge foer 2012-01, Australia foer
#   1996-03) er nye data. Regelen bestaar hvis de nye innslagene, samlet, har
#   S > 0 og flertall positive episoder ved 12 og 24 maaneder. Faa innslag
#   er ventet, og da er svaret beskrivende uansett.
#
# FORBEHOLD
#   Landporteføljen er hele boersen slik Ken French maaler den, ikke OBX eller
#   MSCI. Parene er maalt fra 2016 og brukt bakover. Avkastningen er i dollar,
#   ikke kroner.
# ---------------------------------------------------------------------------

import io, json, os, re, time, warnings, zipfile
import numpy as np
import pandas as pd
import requests
import terskel_motor as M

warnings.filterwarnings("ignore")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
HORISONTER = (1, 2, 3, 6, 12, 24)
KLYNGEGAP, PAUSE, TREKK = 6, M.PAUSE, 2000
rng = np.random.default_rng(20260928)
FRENCH = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/"
LAND = {"norge": ("Norway", "2012-01"), "australia": ("Australia", "1996-03"),
        "brasil": ("Brazil", "2000-07")}


def get(url, timeout=90):
    for i in range(3):
        try:
            r = requests.get(url, headers=UA, timeout=timeout)
            if r.status_code in (429, 502, 503):
                time.sleep(3 * (i + 1)); continue
            r.raise_for_status()
            return r
        except requests.RequestException:
            if i == 2:
                raise
            time.sleep(2 * (i + 1))
    raise RuntimeError(url)


def les_blokk(tekst, start=0):
    """Foerste datablokk fra linje start: overskriftslinje som begynner med
    komma, deretter rader med YYYYMM. Returnerer DataFrame i prosent."""
    i = start
    while not (tekst[i].strip().startswith(",") and len(tekst[i].split(",")) > 1):
        i += 1
    kol = [c.strip() for c in tekst[i].split(",")[1:]]
    rader = {}
    for l in tekst[i + 1:]:
        f = [x.strip() for x in l.split(",")]
        if not f[0].isdigit() or len(f[0]) != 6:
            break
        try:
            rader[pd.Period(f"{f[0][:4]}-{f[0][4:]}", "M")] = [float(x) for x in f[1:len(kol) + 1]]
        except ValueError:
            continue
    d = pd.DataFrame.from_dict(rader, orient="index", columns=kol).sort_index()
    return d.where(d > -99.0), i


def zip_tekst(url):
    z = zipfile.ZipFile(io.BytesIO(get(url).content))
    return z.read(z.namelist()[0]).decode("latin1").splitlines()


# ===================================================================== data
print("0. Raavarene fra bordets egen kode\n")
from raavare_hist import hent
REAL, _NOM, cpi = hent()
KART = json.load(open("sonder/fondkart_forslag.json", encoding="utf-8"))
BUNN, SONE = {}, {}
for sid, lr in REAL.items():
    lr = lr.dropna()
    full = pd.period_range(lr.index[0], lr.index[-1], freq="M")
    lr = lr.reindex(full).interpolate()
    s = M.Segment(sid, lr.values, np.array([p.ordinal for p in lr.index]))
    ok = np.isfinite(s.A) & np.isfinite(s.Ad)
    BUNN[sid] = pd.Series(ok & (s.A >= 80) & (s.Ad >= 80), index=lr.index)
    SONE[sid] = pd.Series(ok & (s.A >= 80), index=lr.index)

print("\n1. Ken French: landporteføljene (F-F_International_Countries.zip)\n")
# Alle landene ligger i én zip, en fil per land. Formatet er ikke det samme
# som i bransjefilene, saa lesingen er generell: foerste linje som starter med
# YYYYMM er data, linjen over er overskriften. Markedskolonnen heter "Mkt" hvis
# den finnes, ellers brukes foerste kolonne, og det skrives ut hva som ble valgt.
z = zipfile.ZipFile(io.BytesIO(get(FRENCH + "ftp/F-F_International_Countries.zip").content))
navn = z.namelist()
print(f"   {len(navn)} filer i zip: {', '.join(navn[:40])}")


def les_land(tekst):
    rader, kol = {}, None
    for i, l in enumerate(tekst):
        f = [x for x in re.split(r"[,\s]+", l.strip()) if x]
        if f and re.fullmatch(r"\d{6}", f[0]):
            if kol is None:
                j = i - 1
                while j >= 0 and not tekst[j].strip():
                    j -= 1
                kol = [x for x in re.split(r",|\s{2,}|\t", tekst[j].strip()) if x.strip()]
            elif rader and pd.Period(f"{f[0][:4]}-{f[0][4:]}", "M") <= max(rader):
                break      # neste blokk begynner (for eksempel aarlige tall eller likevektet)
            try:
                rader[pd.Period(f"{f[0][:4]}-{f[0][4:]}", "M")] = [float(x) for x in f[1:]]
            except ValueError:
                continue
    if not rader:
        return None, None
    n = min(len(v) for v in rader.values())
    d = pd.DataFrame({p: v[:n] for p, v in rader.items()}).T.sort_index()
    kol = [k.strip() for k in (kol or [])]
    if len(kol) >= n:
        d.columns = kol[-n:] if len(kol) > n else kol
    return d.where(d > -99.0), kol


KURS, KILDE = {}, {}
for fid, (land, _) in LAND.items():
    if fid not in KART:
        continue
    treff = [x for x in navn if land.lower() in x.lower()]
    if not treff:
        print(f"   {land}: ingen fil"); continue
    tekst = z.read(treff[0]).decode("latin1").splitlines()
    print(f"   {land}: {treff[0]}")
    print("      foerste linjer: " + " | ".join(x.strip()[:80] for x in tekst[:8] if x.strip()))
    d, kol = les_land(tekst)
    if d is None:
        print("      fant ingen datarader"); continue
    k = next((c for c in d.columns if str(c).lower() in ("mkt", "market")), d.columns[0])
    print(f"      overskrift: {kol}")
    print(f"      kolonner: {list(d.columns)}, {len(d)} mnd fra {d.index[0]} til {d.index[-1]}")
    print(f"      BRUKT: kolonne {k}. Snitt {d[k].mean():.2f} % per mnd, std {d[k].std():.2f}")
    KURS[fid] = np.log1p(d[k].dropna() / 100.0).cumsum()
    KILDE[fid] = f"{treff[0]}, kolonne {k}"

fak = zip_tekst(FRENCH + "ftp/F-F_Research_Data_Factors_CSV.zip")
F, _ = les_blokk(fak)
MARKED = np.log1p((F["Mkt-RF"] + F["RF"]) / 100.0).cumsum()
if not KURS:
    raise SystemExit("Fant ingen landportefølje. Filnavnene over viser hva zip-fila inneholder.")


# ================================================================ regnestykket
def fram_p(lk, h):
    ut = {}
    for t, v in lk.items():
        if t + h in lk.index:
            ut[t] = lk[t + h] - v
    return pd.Series(ut, dtype=float)


FWD = {h: {k: fram_p(v, h) for k, v in KURS.items()} for h in HORISONTER}
SNITT = {h: {k: float(f.mean()) for k, f in FWD[h].items()} for h in HORISONTER}
FWD_M = {h: fram_p(MARKED, h) for h in HORISONTER}


def innslag(fl):
    ut, siste = [], None
    for t in fl.index[fl.values]:
        if siste is None or t.ordinal - siste.ordinal > PAUSE:
            ut.append(t)
        siste = t
    return ut


def flagg(fid, kun_en=False):
    par = [tuple(p["par"]) for p in KART[fid]["par"]]
    sids = sorted({s for p in par for s in p})
    idx = None
    for s in sids:
        idx = BUNN[s].index if idx is None else idx.union(BUNN[s].index)
    b = {s: BUNN[s].reindex(idx).fillna(False) for s in sids}
    z = {s: SONE[s].reindex(idx).fillna(False) for s in sids}
    if kun_en:
        return pd.concat([b[s] for s in sids], axis=1).any(axis=1)
    ut = pd.Series(False, index=idx)
    for a, c in par:
        ut |= z[a] & z[c] & (b[a] | b[c])
    return ut


def klynger(datoer):
    o = np.array([d.ordinal for d in datoer])
    rek = np.argsort(o, kind="stable")
    kl = np.zeros(len(o), int)
    c, sist = 0, None
    for i in rek:
        if sist is not None and o[i] - sist > KLYNGEGAP:
            c += 1
        kl[i] = c; sist = o[i]
    return kl


def S_av(v, kl):
    v = np.asarray(v, float)
    ok = np.isfinite(v)
    if not ok.any():
        return np.nan, 0, 0
    med = np.array([np.median(v[ok & (kl == c)]) for c in np.unique(kl[ok])])
    return float(med.mean()), int((med > 0).sum()), len(med)


def utfall(hend, h):
    rader = []
    for t, fid in hend:
        f = FWD[h][fid]
        if t not in f.index:
            continue
        r = float(f[t])
        m = float(FWD_M[h][t]) if t in FWD_M[h].index else np.nan
        rader.append({"t": t, "fid": fid, "abs": r, "mer": r - SNITT[h][fid], "marked": r - m})
    return rader


def null_S(rader, h):
    kl = klynger([r["t"] for r in rader])
    ep = {}
    for r, c in zip(rader, kl):
        ep.setdefault(c, []).append(r["fid"])
    d = {k: {p: float(x) - SNITT[h][k] for p, x in FWD[h][k].items()} for k in KURS}
    alle = sorted({p for v in d.values() for p in v})
    kand = []
    for fids in ep.values():
        med = []
        for m in alle:
            v = [d[f][m] for f in fids if m in d[f]]
            if v and len(v) * 2 >= len(fids):
                med.append(float(np.median(v)))
        if med:
            kand.append(np.array(med))
    if not kand:
        return np.array([])
    return np.column_stack([k[rng.integers(len(k), size=TREKK)] for k in kand]).mean(axis=1)


pst = lambda v: "     -  " if v is None or not np.isfinite(v) else f"{100 * (np.exp(v) - 1):+7.1f} %"


def tabell(tittel, hend):
    print(f"\n   {tittel}")
    print("   h    innsl ep | abs: median treff | mot eget snitt: median |   S      ep+    p    | mot USA: median   S     ep+")
    ut = {}
    for h in HORISONTER:
        r = utfall(hend, h)
        if not r:
            print(f"   {h:2d}   ingen"); ut[h] = None; continue
        kl = klynger([x["t"] for x in r])
        a = np.array([x["abs"] for x in r]); m = np.array([x["mer"] for x in r]); w = np.array([x["marked"] for x in r])
        S, pos, n = S_av(m, kl); Sw, posw, _ = S_av(w, kl)
        nu = null_S(r, h)
        p = float(((nu >= S).sum() + 1) / (len(nu) + 1)) if len(nu) and np.isfinite(S) else np.nan
        ut[h] = {"innslag": len(r), "episoder": n, "abs_median": float(np.median(a)), "S": S, "S_pos": pos, "p": p,
                 "mer_median": float(np.median(m)), "S_usa": Sw, "S_usa_pos": posw}
        print(f"   {h:2d}   {len(r):4d} {n:3d} | {pst(np.median(a))} {100 * np.mean(a > 0):4.0f} % | {pst(np.median(m))}      | "
              f"{pst(S)} {pos:2d}/{n:<2d} {'  -  ' if not np.isfinite(p) else format(p, '.3f')} | "
              f"{pst(np.nanmedian(w))} {pst(Sw)} {posw:2d}", flush=True)
    return ut


print("\n2. Innslag")
H = {"regelen": [], "en": []}
for fid in KURS:
    for navn, kun in (("regelen", False), ("en", True)):
        for t in innslag(flagg(fid, kun)):
            H[navn].append((t, fid))
    print(f"   {fid:10} regelen: {' '.join(str(t) for t, f in H['regelen'] if f == fid) or '-'}")
    print(f"   {'':10} en i bunnsone: {' '.join(str(t) for t, f in H['en'] if f == fid) or '-'}")

nye = lambda hend: [(t, f) for t, f in hend if t < pd.Period(LAND[f][1], "M")]
print("\n\n3. Resultat")
RES = {"regelen_alle": tabell("Fondsregelen, alle innslag", H["regelen"]),
       "regelen_nye": tabell("Fondsregelen, bare innslag foer fondets egen historikk (AVGJOER)", nye(H["regelen"])),
       "en_alle": tabell("Sammenligning: en i bunnsone, alle innslag", H["en"]),
       "en_nye": tabell("Sammenligning: en i bunnsone, foer fondets egen historikk", nye(H["en"]))}

print("\n   Hvert innslag etter regelen (abs, dollar):")
print("      land       innslag " + "".join(f"{h:>8d} mnd" for h in HORISONTER))
LISTE = []
for t, fid in sorted(H["regelen"], key=lambda x: (x[1], x[0])):
    v = {h: (float(FWD[h][fid][t]) if t in FWD[h][fid].index else np.nan) for h in HORISONTER}
    LISTE.append({"land": fid, "t": str(t), **{f"h{h}": v[h] for h in HORISONTER}})
    print(f"      {fid:10} {str(t):8}" + "".join(f"{pst(v[h]):>12}" for h in HORISONTER)
          + ("   (nytt)" if t < pd.Period(LAND[fid][1], "M") else ""))

print("\n\n4. Beslutning etter regelen satt foer kjoering")
ny = RES["regelen_nye"]
ok = {h: bool(ny.get(h) and np.isfinite(ny[h]["S"]) and ny[h]["S"] > 0 and ny[h]["S_pos"] * 2 > ny[h]["episoder"])
      for h in (12, 24)}
for h in (12, 24):
    o = ny.get(h)
    print(f"   {h} mnd: " + ("ingen innslag" if not o else
          f"S {pst(o['S'])}, {o['S_pos']} av {o['episoder']} episoder positive, p {o['p']:.3f}")
          + f"  ->  {'bestaar' if ok[h] else 'bestaar ikke'}")
print("   " + ("Fondsregelen holder paa landdata foer fondene fantes." if all(ok.values())
             else "Fondsregelen holder ikke paa landdata foer fondene fantes."))


def rens(x):
    if isinstance(x, dict):
        return {str(k): rens(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [rens(v) for v in x]
    if isinstance(x, (float, np.floating)):
        return None if not np.isfinite(x) else round(float(x), 5)
    if isinstance(x, (np.integer, np.bool_)):
        return x.item()
    return x


os.makedirs("sonder", exist_ok=True)
json.dump(rens({"kjort": time.strftime("%Y-%m-%d %H:%M:%S"), "kilder": KILDE, "resultat": RES,
                "innslag": LISTE, "bestaar": ok}),
          open("sonder/land.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("\n   lagret sonder/land.json")
