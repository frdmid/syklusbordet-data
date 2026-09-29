# ---------------------------------------------------------------------------
# sonde_kjor_rigg_slitasje: test B for rigger, med anslaatt slitasje for aar
# etter ny startbalanse
#
# Frodes bestilling 29.09.2026. Regel A (rigg_b.py) holder aar etter ny
# startbalanse utenfor, og da forsvinner Valaris og Diamond fra 2021 med sine
# reaktiveringer. B beholder investeringene, men bytter de kunstig lave
# avskrivningene med et anslag for slitasje.
#
# ANSLAGET, satt foer kjoering
#   avskrivning per rigg = snittet av de tre siste rene aarene foer
#   restruktureringen (avskrivninger delt paa antall rigger ved aarsslutt),
#   ganget med antall rigger i aaret. Riggtall fra XBRL-fila i aarsrapportene:
#     Valaris   val/esv:TotalNumberOfContractDrillingRigs per segment
#     Diamond   do:NumberOfOffshoreRigsOwned
#     Transocean rig:NumberOfMobileOffshoreDrillingUnits (til kontrollen)
#     Borr      borr:NumberOfJackUpRigsOwned (til kontrollen)
#   Mangler riggtall et aar, brukes selskapets siste kjente riggtall.
#
# KONTROLL, satt foer kjoering
#   Anslaget proeves paa aar der de faktiske avskrivningene er kjent og rene:
#   for hvert rent aar t regnes avskrivning per rigg i t-3 til t-1 ganger
#   riggtallet i t, og sammenlignes med faktiske avskrivninger i t. B
#   godkjennes bare hvis medianen av absolutt feil er hoeyst 20 % og
#   80-persentilen hoeyst 35 %. Ellers brukes regel A videre.
#
# UTSKRIFT: kontrollen, anslaget per restrukturert selskap og aar, og B2 per
# segment med regel A og med B side om side.
# ---------------------------------------------------------------------------

import re, time
import numpy as np
import pandas as pd
import rigg_b as R

TELLER = {
    "0000314808": ("Valaris", r":TotalNumberOfContractDrillingRigs$", True),
    "0000949039": ("Diamond Offshore", r":NumberOfOffshoreRigsOwned$", False),
    "0001451505": ("Transocean", r":NumberOfMobileOffshoreDrillingUnits$", False),
    "0001715497": ("Borr Drilling", r":NumberOfJackUpRigsOwned$", False),
}


def riggtall(cik, moenster, per_segment):
    """(klasse eller 'alle', aar) -> antall rigger ved aarsslutt. Nyeste rapport vinner."""
    ut = {}
    for dato, accn in R._aarsrapporter(cik):
        t = R._instans(cik, accn)
        time.sleep(0.15)
        if not t:
            continue
        ctx = {}
        for m in re.finditer(r"<(?:xbrli:)?context id=\"([^\"]+)\">(.*?)</(?:xbrli:)?context>", t, re.S):
            b = m.group(2)
            slutt = re.search(r"(?:instant|endDate)>([^<]+)<", b)
            dims = dict(re.findall(r"<xbrldi:explicitMember dimension=\"([^\"]+)\">([^<]+)<", b))
            if not slutt:
                continue
            if per_segment:
                seg = dims.get("us-gaap:StatementBusinessSegmentsAxis")
                andre = [d for d in dims if d not in ("us-gaap:StatementBusinessSegmentsAxis", "srt:ConsolidationItemsAxis")]
                k = next((kl for kl, mo in R.SEG_KLASSE if seg and re.search(mo, seg, re.I)), None)
                if k and not andre:
                    ctx[m.group(1)] = (k, slutt.group(1))
            elif not dims:
                ctx[m.group(1)] = ("alle", slutt.group(1))
        for m in re.finditer(r"<([A-Za-z0-9\-]+:[A-Za-z0-9_]+)\b[^>]*?contextRef=\"([^\"]+)\"[^>]*>([\d.]+)</\1>", t):
            if m.group(2) in ctx and re.search(moenster, m.group(1)):
                k, d = ctx[m.group(2)]
                if d[5:] in ("12-31", "12-30"):
                    ut[(k, int(d[:4]))] = float(m.group(3))
    return ut


print("1. RIGGTALL FRA AARSRAPPORTENE\n")
RIGG = {}
for cik, (navn, mo, ps) in TELLER.items():
    RIGG[cik] = riggtall(cik, mo, ps)
    print(f"   {navn:18s} " + ", ".join(f"{k} {a}: {v:.0f}" for (k, a), v in sorted(RIGG[cik].items(), key=lambda x: (x[0][0], x[0][1]))))

print("\n2. RAA DATA UTEN REGEL A\n")
lagret = dict(R.UTELAT_FRA)
R.UTELAT_FRA.clear()
REN_ALLE = R.rene(note=lambda *a: None)
SEG_ALLE = R.segmenter(note=lambda *a: None)
R.UTELAT_FRA.update(lagret)


def serie_for(cik, klasse):
    """Faktiske avskrivninger og capex per aar for et selskap (segment eller helt)."""
    if cik in REN_ALLE and REN_ALLE[cik]["seg"] == klasse:
        d = REN_ALLE[cik]
        return d["capex"].astype(float), d["dda"].astype(float)
    rader = {a: v for (k, c, a), v in SEG_ALLE.items() if c == cik and k == klasse}
    if not rader:
        return pd.Series(dtype=float), pd.Series(dtype=float)
    return (pd.Series({a: v["capex"] for a, v in rader.items()}).sort_index(),
            pd.Series({a: v["dda"] for a, v in rader.items()}).sort_index())


def rigger(cik, klasse, aar):
    r = RIGG.get(cik, {})
    kl = klasse if TELLER[cik][2] else "alle"
    kjente = sorted(a for (k, a) in r if k == kl and a <= aar)
    return r[(kl, kjente[-1])] if kjente else np.nan


print("3. KONTROLL AV ANSLAGET PAA RENE AAR (satt foer kjoering)\n")
feil = []
for cik, (navn, _, _) in TELLER.items():
    for klasse in ("dyp", "grunt"):
        cx, dd = serie_for(cik, klasse)
        grense = R.UTELAT_FRA.get(navn, 9999)
        for t in dd.index:
            if t >= grense or not all((t - i) in dd.index for i in (1, 2, 3)):
                continue
            n_t = rigger(cik, klasse, t)
            per = [dd[t - i] / rigger(cik, klasse, t - i) for i in (1, 2, 3)]
            if np.isnan(n_t) or any(np.isnan(per)):
                continue
            est = np.mean(per) * n_t
            e = abs(est / dd[t] - 1)
            feil.append(e)
            print(f"   {navn:18s} {klasse:5s} {t}: faktisk {dd[t] / 1e6:7,.0f}  anslag {est / 1e6:7,.0f}  feil {100 * e:5.1f} %")
if feil:
    med, p80 = float(np.median(feil)), float(np.percentile(feil, 80))
    GODKJENT = med <= 0.20 and p80 <= 0.35
    print(f"\n   {len(feil)} aar: median feil {100 * med:.1f} % (krav 20), 80-persentil {100 * p80:.1f} % (krav 35) -> "
          f"{'GODKJENT' if GODKJENT else 'IKKE GODKJENT'}")
else:
    GODKJENT = False
    print("   ingen aar kunne kontrolleres -> IKKE GODKJENT")

print("\n4. ANSLAATT SLITASJE FOR AAR ETTER NY STARTBALANSE\n")
TILLEGG = {}   # (klasse, cik, aar) -> {"capex", "dda", "navn"}
for cik, (navn, _, _) in TELLER.items():
    grense = R.UTELAT_FRA.get(navn)
    if not grense:
        continue
    for klasse in ("dyp", "grunt"):
        cx, dd = serie_for(cik, klasse)
        foer = [a for a in (grense - 1, grense - 2, grense - 3) if a in dd.index]
        per = [dd[a] / rigger(cik, klasse, a) for a in foer if not np.isnan(rigger(cik, klasse, a))]
        if not per:
            continue
        pr = float(np.mean(per))
        for a in cx.index:
            if a < grense:
                continue
            n = rigger(cik, klasse, a)
            if np.isnan(n):
                continue
            TILLEGG[(klasse, cik, a)] = {"capex": cx[a], "dda": pr * n, "navn": navn + (" (segment)" if cik not in REN_ALLE else "")}
            print(f"   {navn:18s} {klasse:5s} {a}: capex {cx[a] / 1e6:6,.0f}  faktisk avskr {dd.get(a, np.nan) / 1e6:6,.0f}  "
                  f"anslaatt slitasje {pr * n / 1e6:6,.0f} ({n:.0f} rigger x {pr / 1e6:.1f})")

print("\n5. B2 PER SEGMENT: REGEL A MOT B\n")
ren_a = R.rene(note=lambda *a: None)
seg_a = R.segmenter(note=lambda *a: None)
RES_A = R.beregn(ren_a, seg_a)
seg_b = dict(seg_a)
for (k, cik, a), v in TILLEGG.items():
    if cik in ren_a or cik in REN_ALLE:
        # rent selskap (Diamond): legges inn som segmenttall for aaret
        seg_b[(k, cik, a)] = {"navn": v["navn"], "capex": v["capex"], "dda": v["dda"]}
    else:
        seg_b[(k, cik, a)] = {"navn": R.BLANDET.get(cik, v["navn"]), "capex": v["capex"], "dda": v["dda"]}
RES_B = R.beregn(ren_a, seg_b)
for k in ("grunt", "dyp"):
    a, b = RES_A[k], RES_B[k]
    print(f"   {k.upper()}")
    print(f"   {'aar':>5s} {'A forhold':>10s} {'A B2':>6s} {'A n':>4s} | {'B forhold':>10s} {'B B2':>6s} {'B n':>4s}")
    for aar in sorted(set(a.index) | set(b.index)):
        if aar < 2015:
            continue
        ra = a.loc[aar] if aar in a.index else None
        rb = b.loc[aar] if aar in b.index else None
        f = lambda r, c, fm: "-" if r is None or pd.isna(r[c]) else format(r[c], fm)
        print(f"   {aar:5d} {f(ra, 'forhold', '.2f'):>10s} {f(ra, 'B2', '.0f'):>6s} {f(ra, 'n', '.0f'):>4s} | "
              f"{f(rb, 'forhold', '.2f'):>10s} {f(rb, 'B2', '.0f'):>6s} {f(rb, 'n', '.0f'):>4s}")
    print()
print("   Konklusjon etter kriteriet satt foer kjoering: " +
      ("B kan tas i bruk." if GODKJENT else "B tas ikke i bruk; regel A gjelder."))
