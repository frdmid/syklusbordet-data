# ---------------------------------------------------------------------------
# sonde_kjor_kali_platina: kan kalium og platina bli segmenter paa bordet?
#
# Bestilt av Frode 26.09.2026: "Test kali og platina opp mot instrumenter i
# sektoren." Sonden endrer ingenting paa bordet.
#
# Et segment trenger to ting for aa komme inn, samme krav som de andre:
#   1. En markedspris med nok historikk til at A kan regnes (minst 60 mnd
#      etter avkorting for forhandlet pris).
#   2. Minst ett papir som er kjoepbart paa IKZ og som faktisk folger prisen.
#      Kravene fra instrumenter.py: minst 72 maaneder i det faste vinduet fra
#      2016-01, og korrelasjon i maanedlige realendringer paa minst 0,30 baade
#      raatt (rf1, fast vindu) og etter at verdensindeksen er tatt ut (rp).
#
# Kalium ble tatt ut av bordet 22.09.2026 fordi prisen sto 71 % stille selv
# paa 2010-tallet. Papirene ble aldri maalt. Her maales de likevel, slik at
# svaret hviler paa tall og ikke bare paa at prisen er administrert.
#
# DEL 1  Stillstand i nominell pris per tiaar og per aar (Verdensbanken, Pink
#        Sheet). Samme regel som AVKORT i priser.py: over 40 % uendrede
#        maaneder er forhandlet pris, ikke en notering. Serien starter i
#        januar aaret etter siste aar over 40 %.
# DEL 2  A og detrendet A paa den avkortede serien, med bordets egen kode
#        (terskel_motor). Flaggmaaneder (A >= 80 og Ad >= 80), innslag og
#        realprisen 12 og 24 maaneder etter hvert innslag.
# DEL 3  sonde_ikz.py med IKZ_KUN=platina,kalium: hele IKZ-universet maales
#        mot de to prisene, med samme maaling som for resten av bordet.
# DEL 4  Vurdering mot kravene, og hva papirene gjorde etter hvert innslag
#        (realavkastning 12 og 24 mnd, og mot papirets eget snitt).
# ---------------------------------------------------------------------------

import io, json, os, re, subprocess, sys, time, warnings
import numpy as np
import pandas as pd
import requests
import terskel_motor as M

warnings.filterwarnings("ignore")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
MIRROR = "https://raw.githubusercontent.com/datasets/"
SERIER = [("platina", "Platinum"), ("kalium", "Potassium chloride")]
STILLE = 0.40          # samme grense som AVKORT i priser.py
MIN_HIST = 60          # samme som priser.py
NF_KRAV, R_KRAV = 72, 0.30
RES = {"kjort": time.strftime("%Y-%m-%d %H:%M:%S")}


def get(url, timeout=90):
    for i in range(3):
        try:
            r = requests.get(url, headers=UA, timeout=timeout)
            r.raise_for_status()
            return r
        except requests.RequestException:
            if i == 2:
                raise
            time.sleep(3 * (i + 1))


def pink_sheet():
    kand = []
    try:
        html = get("https://www.worldbank.org/en/research/commodity-markets", 40).text
        kand += [u if u.startswith("http") else "https://www.worldbank.org" + u
                 for u in re.findall(r'https?://[^"\']*?CMO[^"\']*?Monthly[^"\']*?\.xlsx', html)]
    except Exception:
        pass
    kand.append("https://thedocs.worldbank.org/en/doc/"
                "18675f1d1639c7a34d463f59263ba0a2-0050012025/related/"
                "CMO-Historical-Data-Monthly.xlsx")
    for u in dict.fromkeys(kand):
        try:
            raw = get(u).content
            for skip in (4, 5, 6):
                try:
                    df = pd.read_excel(io.BytesIO(raw), sheet_name="Monthly Prices", skiprows=skip)
                    df = df.rename(columns={df.columns[0]: "t"})
                    m = df[df["t"].astype(str).str.match(r"^\d{4}M\d{1,2}$", na=False)].copy()
                    if len(m) > 100:
                        m["t"] = pd.PeriodIndex(m["t"].astype(str).str.replace("M", "-", regex=False), freq="M")
                        return m.set_index("t").apply(pd.to_numeric, errors="coerce")
                except Exception:
                    pass
        except Exception:
            pass
    raise RuntimeError("Pink Sheet utilgjengelig")


def cpi_serie():
    d = pd.read_csv(io.StringIO(get(MIRROR + "cpi-us/main/data/cpiai.csv").text)).iloc[:, :2]
    d.columns = ["Date", "Value"]
    d["Value"] = pd.to_numeric(d["Value"], errors="coerce")
    d = d.dropna()
    d["Date"] = pd.to_datetime(d["Date"])
    s = d.set_index("Date")["Value"].resample("ME").last().dropna()
    s.index = s.index.to_period("M")
    return s


pst = lambda v: "-" if v is None or not np.isfinite(v) else f"{100 * (np.exp(v) - 1):+6.1f} %"

# =============================================================== del 1
print("DEL 1. Stillstand i nominell pris (Verdensbanken, Pink Sheet)\n")
ps = pink_sheet()
norm = lambda x: re.sub(r"[^a-z0-9]", "", str(x).lower())
kol = {norm(c): c for c in ps.columns}
cpi = cpi_serie()
NOM, START = {}, {}
for sid, navn in SERIER:
    eksakt = [v for k, v in kol.items() if k == norm(navn)]
    delvis = [v for k, v in kol.items() if k.startswith(norm(navn))]
    traff = eksakt or delvis
    if not traff:
        print(f"   {sid}: fant ingen kolonne for '{navn}'. Kolonner som ligner: "
              f"{[c for c in ps.columns if norm(navn)[:5] in norm(c)]}")
        continue
    s = ps[traff[0]].dropna()
    s = s[s > 0]
    NOM[sid] = s
    stille = (s.diff() == 0).astype(float).iloc[1:]
    print(f"   {sid} (kolonne '{traff[0]}'): {s.index[0]} til {s.index[-1]}, {len(s)} mnd, siste {s.iloc[-1]:.2f}")
    tiaar = stille.groupby(stille.index.year // 10 * 10).mean()
    print("      uendret per tiaar: " + "  ".join(f"{a}-t {100 * v:.0f} %" for a, v in tiaar.items()))
    aar = stille.groupby(stille.index.year).mean()
    over = [a for a, v in aar.items() if v > STILLE]
    if over:
        vis = over if len(over) <= 12 else over[:3] + ["..."] + over[-6:]
        print(f"      aar over 40 % ({len(over)} av {len(aar)}): "
              + ", ".join(a if a == "..." else f"{a} ({100 * aar[a]:.0f} %)" for a in vis))
    else:
        print("      aar over 40 %: ingen")
    start = pd.Period(f"{max(over) + 1}-01", "M") if over else s.index[0]
    START[sid] = start
    n_etter = int((s.index >= start).sum())
    print(f"      start etter regelen: {start}, {n_etter} mnd etter avkorting"
          + ("" if n_etter >= MIN_HIST else f"  (UNDER {MIN_HIST}: A kan ikke regnes)"))
    RES[sid] = {"kolonne": str(traff[0]), "fra": str(s.index[0]), "til": str(s.index[-1]),
                "stille_tiaar": {int(a): round(float(v), 3) for a, v in tiaar.items()},
                "aar_over_40": over, "start": str(start), "n_etter": n_etter}
    print()

# =============================================================== del 2
print("DEL 2. A og detrendet A paa den avkortede serien\n")
SEG = {}
for sid, s in NOM.items():
    s = s[s.index >= START[sid]]
    if len(s) < MIN_HIST:
        print(f"   {sid}: {len(s)} mnd, for kort til A\n")
        RES[sid]["A_mulig"] = False
        continue
    real = (s * (cpi.iloc[-1] / cpi.reindex(s.index).ffill())).dropna()
    lr = np.log(real)
    full = pd.period_range(lr.index[0], lr.index[-1], freq="M")
    lr = lr.reindex(full).interpolate()
    seg = M.Segment(sid, lr.values, np.array([p.ordinal for p in lr.index]))
    SEG[sid] = (seg, lr)
    fl = np.isfinite(seg.A) & np.isfinite(seg.Ad) & (seg.A >= 80) & (seg.Ad >= 80)
    RES[sid]["A_mulig"] = True
    RES[sid]["A_naa"] = round(float(seg.A[-1]), 1)
    RES[sid]["Ad_naa"] = round(float(seg.Ad[-1]), 1)
    RES[sid]["andel_flagg"] = round(float(fl[np.isfinite(seg.A)].mean()), 3)
    print(f"   {sid}: {lr.index[0]} til {lr.index[-1]}. Naa A {seg.A[-1]:.1f}, detrendet A {seg.Ad[-1]:.1f}. "
          f"Flagget i {100 * RES[sid]['andel_flagg']:.1f} % av maanedene med skaar.")
    RES[sid]["innslag"] = []
    f12, f24 = M.fram(seg.lr, 12), M.fram(seg.lr, 24)
    for i in M.innslag(fl):
        t = str(lr.index[i])
        RES[sid]["innslag"].append({"t": t, "A": round(float(seg.A[i]), 1), "Ad": round(float(seg.Ad[i]), 1),
                                    "r12": None if not np.isfinite(f12[i]) else float(f12[i]),
                                    "r24": None if not np.isfinite(f24[i]) else float(f24[i])})
        print(f"      innslag {t}  A {seg.A[i]:5.1f}  Ad {seg.Ad[i]:5.1f}   realpris 12 mnd {pst(f12[i])}, 24 mnd {pst(f24[i])}")
    ok = np.isfinite(f12) & np.isfinite(seg.A)
    print(f"      snitt alle maaneder med skaar: 12 mnd {pst(f12[ok].mean())}, "
          f"24 mnd {pst(f24[np.isfinite(f24) & np.isfinite(seg.A)].mean())}\n")

# =============================================================== del 3
print("DEL 3. IKZ-universet maalt mot platina og kalium (sonde_ikz.py)\n", flush=True)
avk = ",".join(f"{k}:{v}" for k, v in START.items())
t0 = time.time()
p = subprocess.run([sys.executable, "sonde_ikz.py"],
                   env=dict(os.environ, IKZ_KUN="platina,kalium", IKZ_AVKORT=avk),
                   capture_output=True, text=True, timeout=3000)
print(p.stdout[-50000:])
if p.stderr.strip():
    print("[stderr]\n" + p.stderr[-4000:])
print(f"\n(del 3 brukte {time.time() - t0:.0f} s, kode {p.returncode})\n", flush=True)

# =============================================================== del 4
print("DEL 4. Vurdering mot kravene og utfall etter innslag\n")
try:
    ikz = json.load(open("sonder/ikz_platina_kalium.json", encoding="utf-8"))
    kurs = json.load(open("sonder/ikz_kurs_platina_kalium.json", encoding="utf-8"))
except Exception as e:
    ikz, kurs = {"par": []}, {}
    print(f"   fant ikke resultatet fra del 3: {type(e).__name__}")
g = lambda r, k: "-" if r.get(k) is None else f"{r[k]:.2f}"
RES["vurdering"] = {}
for sid, _ in SERIER:
    par = [r for r in ikz["par"] if r["segment"] == sid]
    ap = sorted([r for r in par if r["a_priori"]], key=lambda r: -(r.get("rf1") or -9))
    print(f"   {sid.upper()}: ventede papirer (krav nf >= {NF_KRAV}, rf1 >= {R_KRAV}, rp >= {R_KRAV})")
    print(f"      {'papir':9} {'navn':34} {'bors':4} {'nf':>4} {'rf1':>6} {'r1':>6} {'rp':>6} {'b12':>6} {'fangst':>7}  bestaar")
    best = []
    for r in ap:
        ok = (r.get("nf", 0) >= NF_KRAV and (r.get("rf1") or 0) >= R_KRAV and (r.get("r_partiell") or 0) >= R_KRAV)
        if ok:
            best.append(r["ticker"])
        print(f"      {r['ticker']:9} {r['navn'][:34]:34} {r['bors'] or 'ok':4} {r['nf']:4d} {g(r,'rf1'):>6} "
              f"{g(r,'r1'):>6} {g(r,'r_partiell'):>6} {g(r,'beta12'):>6} {g(r,'fangst'):>7}  {'JA' if ok else 'nei'}")
    mangler = [m for m in ("SBSW", "SLP.L", "THS.L", "ELR.TO", "IMPUY", "ANGPY", "JMAT.L") if sid == "platina"
               and m not in {r["ticker"] for r in ap}] + \
              [m for m in ("NTR", "MOS", "ICL", "SDF.DE", "IPI") if sid == "kalium" and m not in {r["ticker"] for r in ap}]
    if mangler:
        print(f"      ikke maalt (ingen kurs eller for kort): {', '.join(mangler)}")
    eks = sorted([r for r in par if not r["a_priori"] and r.get("nf", 0) >= NF_KRAV and r.get("rf1") is not None],
                 key=lambda r: -abs(r["rf1"]))[:6]
    print("      sterkeste uventede (funnet ved leting, strengere krav):")
    for r in eks:
        print(f"         {r['ticker']:9} {r['navn'][:34]:34} rf1 {g(r,'rf1')}  rp {g(r,'r_partiell')}  q12 {g(r,'q12')}")
    RES["vurdering"][sid] = {"bestaar": best,
                             "a_priori": [{k: r.get(k) for k in ("ticker", "navn", "bors", "nf", "rf1", "r1",
                                                                  "r_partiell", "beta12", "fangst")} for r in ap]}

    # utfall for papirene etter hvert innslag
    if sid in SEG and kurs:
        seg, lr = SEG[sid]
        print("      papirene etter innslag, realavkastning (og mot papirets eget snitt):")
        for t, v in kurs.items():
            if t not in {r["ticker"] for r in ap}:
                continue
            k = pd.Series(v)
            k.index = pd.PeriodIndex(k.index, freq="M")
            lk = np.log(k.sort_index())
            f12 = (lk.shift(-12) - lk).dropna(); f24 = (lk.shift(-24) - lk).dropna()
            linje = []
            for inn in RES[sid].get("innslag", []):
                pr = pd.Period(inn["t"], "M")
                if pr not in lk.index:
                    continue
                a = f12.get(pr); b = f24.get(pr)
                linje.append(f"{inn['t']}: 12m {pst(a)}"
                             + ("" if a is None else f" ({pst(a - f12.mean())})")
                             + f", 24m {pst(b)}")
            print(f"         {t:9} " + ("; ".join(linje) if linje else "ingen innslag i papirets historikk"))
    print()

print("SAMLET")
for sid, _ in SERIER:
    r = RES.get(sid, {})
    print(f"   {sid}: prisen {'kan' if r.get('A_mulig') else 'kan IKKE'} gi A "
          f"(start {r.get('start')}, {r.get('n_etter')} mnd"
          f"{', under ti aar: for kort til en fordeling' if (r.get('n_etter') or 0) < 120 else ''}). "
          f"Papirer som bestaar: {', '.join(RES['vurdering'].get(sid, {}).get('bestaar', [])) or 'ingen'}.")

os.makedirs("sonder", exist_ok=True)
json.dump(RES, open("sonder/kali_platina.json", "w"), ensure_ascii=False, indent=1, default=str)
print("\nLagret sonder/kali_platina.json")
