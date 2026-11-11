# ---------------------------------------------------------------------------
# kontekst_regime: regimepanelet paa dashbordet (Frodes bestilling 15.10.2026,
# steg 2 etter sonde_kjor_regime). Kontekst, ikke en skaar, ikke testet som
# signal, og ikke shadow-data.
#
# Skriver regime.json med fire felt og analoger:
#   VEKST      andel raavaresegmenter med hoeyere realpris enn for 12 mnd
#              siden (holdt i sonden), og kobber mot gull, endring 12 mnd.
#   SJOKK      To ledd fra 11.11.2026 (Frodes forslag, se
#              notater/2026-11-11_regime_sjokk_forslag.md):
#                nivaa   maanedssnitt av ^VIX      (fra 1990)
#                volvar  maanedssnitt av ^VVIX     (fra januar 2007)
#              ABSOLUTTE grenser, ikke persentil (Frodes poeng 11.11.2026:
#              for VIX er lang historikk ikke like viktig som for enkeltassets
#              og papirer, «vol er vol» - 20 er 20 i 1995 og i 2026, mens en
#              raavares realpris bare kan leses mot sin egen fordeling).
#              Det gir ogsaa 59 maaneder mer dekning: med persentil maatte
#              VVIX bygge opp 60 maaneder og startet foerst desember 2011, saa
#              finanskrisen og eurokrisen hadde ikke noe volvariasjonsledd.
#                nivaa:  20 forhoeyet, 30 hoey   (p63 og p91 fra 2007)
#                volvar: 105 forhoeyet, 120 hoey (p79 og p95 fra 2007)
#              Grensene er RUNDE TALL valgt fra fordelingen, ikke maalt mot
#              noe utfall. 20 og 30 er markedets egne konvensjonelle nivaaer.
#              Ordet settes av paret, med hysterese (inn med en gang, ut etter
#              UT_MND maaneder under): begge over den hoeye grensen gir sjokk,
#              begge over den lave gir forhoeyet, bare nivaa gir «spent nivaa»
#              (uroen er priset og stabil, som juni 2022), bare volvar gir
#              «urolig forventning» (markedet er usikkert paa usikkerheten,
#              ofte foer en bevegelse, som oktober 2018), ellers rolig. De to
#              enkeltleddene er med vilje ikke samme ord.
#              Symmetrisk varighetskrav ble forkastet: det leste tollsjokket
#              april 2025 og mars 2026 som rolig, fordi de var enkeltmaaneder.
#              Et sjokk maa registreres i maaneden det skjer; usikkerheten er
#              naar det slutter.
#              volvar er NULL foer 2007. Da settes ordet av nivaa alene og
#              merknaden sier at volvariasjonen er ukjent.
#              Den rullende tiaarspersentilen for hvert ledd (nivaa_pct,
#              volvar_pct) VISES som tilleggstall, men setter ikke ordet.
#              Papirkorrelasjonen (korr_papirer, rullende 13 uker) staar
#              fortsatt i feltet, men er TATT UT AV ORDET: max() over tre
#              ledd sto paa nesten hele tiden. Den er ikke maalt paa samme
#              maate ennaa.
#              Det gamle voksende VIX-maalet (vix_pct) staar igjen i feltet og
#              i serien for bakoverkompatibilitet, og brukes fortsatt i
#              analogavstanden (dims), slik at analoglisten ikke endrer seg.
#              INGEN av disse maalene er testet som signal: sonden
#              sonde_kjor_vvix_sjokk (11.11.2026) viste at verken VIX-nivaa,
#              VIX-spredning eller VVIX skiller utfallene etter bunnsonen.
#   BOOM       median A over raavarene. Fanger toppene (2008, 2022), ikke
#              bunnene, og vises bare som tegn paa at alt er dyrt.
#   LIKVIDITET Feds netto likviditet (WALCL minus WTREGEN minus RRPONTSYD),
#              endring 13 uker, reverse repo, og Fed, ECB og BoJ i USD,
#              endring 6 mnd. Beskrivende, for faa sykluser til aa teste.
#   SIDEN      vekst.nedgang_siden og sjokk.sjokk_siden: foerste maaned i
#              den pagaaende perioden med bred nedgang eller sjokk (15.10.2026),
#              til teksten om ventetid under panelet.
#   ANALOGER   naermeste tidligere maaneder over bredde, median A, VIX,
#              papirkorrelasjon, kreditt (BAA10Y) og rentekurve (T10Y2Y).
# Ordene i feltene bruker grensene fra sonden: 0,6 og 0,4 for bredde, nederste
# tiendedel siden 1990 for median A. Sjokkfeltet bruker grensene over (11.11.2026).
#
# Kalles hver uke fra shadow_challenger.kjor (etter Challengerne), som
# kontekst_laks. Ikke med i Championens frosne filer og ikke i noen
# Challengers kode. Onsdagsrutinen skriver fila til marked/regime.
# ---------------------------------------------------------------------------

import datetime as dt, io, json, time
import numpy as np
import pandas as pd
import requests

from instrumenter import INSTR

FIL = "regime.json"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
FONDER = ["XOP", "GDX", "COPX", "XME", "MOO", "IEZ", "OIH", "SPY"]
HENDELSER = {"1998-09": "LTCM og Russland", "2001-09": "11. september", "2002-07": "etter IT-boblen",
             "2008-06": "råvaretoppen 2008", "2008-10": "finanskrisen", "2011-08": "eurokrisen",
             "2015-08": "Kina og oljefallet", "2016-01": "råvarebunnen 2016", "2018-12": "renter og handelskrig",
             "2020-03": "covid", "2021-11": "gjenåpningen", "2022-03": "Ukraina", "2022-06": "inflasjonstoppen",
             "2025-04": "tollsjokket"}
MIN = 60
# Sjokkfeltet (11.11.2026). Runde tall valgt fra fordelingen av maanedssnittene
# paa den felles perioden fra 2007, ikke maalt mot noe utfall. VIX: 20 traff
# p63 og 30 traff p91. VVIX: 105 traff p79 og 120 traff p95.
NIVAA_GRENSER = (20, 30)        # maanedssnitt ^VIX: forhoeyet, hoey
VOLVAR_GRENSER = (105, 120)     # maanedssnitt ^VVIX: forhoeyet, hoey
UT_MND = 2                      # maaneder under grensen foer ordet gaar ned
MIN_DAGER = 15                  # hel maaned, som priser.py kaster paabegynt maaned
RULL_VINDU = 120                # tiaarsvindu for persentilen som vises


def _get(url, **kw):
    for i in range(4):
        try:
            r = requests.get(url, timeout=60, **kw)
            if r.status_code == 200:
                return r
        except requests.RequestException:
            pass
        time.sleep(3 * (i + 1))
    raise RuntimeError(f"ingen svar: {url[:60]}")


def _fred(sid):
    r = _get("https://fred.stlouisfed.org/graph/fredgraph.csv", params={"id": sid},
             headers={"User-Agent": "Syklusbordet frode@h-k.no"})
    d = pd.read_csv(io.StringIO(r.text)); d.columns = ["t", "v"]
    return pd.Series(pd.to_numeric(d.v, errors="coerce").values, index=pd.to_datetime(d.t)).dropna()


def _dag(sym):
    r = _get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}",
             params={"period1": 0, "period2": int(time.time()), "interval": "1d", "events": "div,split"}, headers=UA)
    res = r.json()["chart"]["result"][0]
    if (res.get("meta") or {}).get("dataGranularity") != "1d":
        raise ValueError("ikke dagskurser")
    adj = res["indicators"].get("adjclose", [{}])[0].get("adjclose") or res["indicators"]["quote"][0]["close"]
    s = pd.Series(adj, index=pd.to_datetime(res["timestamp"], unit="s")).dropna()
    time.sleep(0.3)
    return s[s > 0]


def _mnd(s, how="last"):
    m = s.resample("ME").last() if how == "last" else s.resample("ME").mean()
    m.index = m.index.to_period("M")
    return m


def _pct_siste(s):
    v = s.dropna()
    return None if len(v) < MIN else round(float((v <= v.iloc[-1]).mean() * 100), 1)


def _pit(s):
    v = s.values; o = np.full(len(v), np.nan)
    for i in range(len(v)):
        if np.isfinite(v[i]):
            h = v[: i + 1]; h = h[np.isfinite(h)]
            if len(h) >= MIN:
                o[i] = (h <= v[i]).mean() * 100
    return pd.Series(o, index=s.index)


def _mnd_hel(s):
    """Maanedssnitt av en dagsserie, men bare hele maaneder (11.11.2026).

    En paabegynt maaned har faa handledager og kan ikke sammenlignes med hele
    maaneder. Samme regel som hel_maaned i priser.py, der en paabegynt maaned
    kastes slik at flagg ikke slaar inn og ut midt i en maaned."""
    g = s.groupby(s.index.to_period("M"))
    m = g.mean()[g.size() >= MIN_DAGER]
    return m.sort_index()


def _rull(s, w=RULL_VINDU, minn=MIN):
    """Persentil i et rullende vindu, som rolling_pct i priser.py (Ar).

    Vises som tilleggstall ved hvert sjokkledd, men setter ikke ordet: ordet
    bruker absolutte grenser (se toppen av fila)."""
    v = s.values
    ut = np.full(len(v), np.nan)
    for i in range(len(v)):
        lo = max(0, i - w + 1)
        if i - lo + 1 >= minn and np.isfinite(v[i]):
            y = v[lo: i + 1]
            y = y[np.isfinite(y)]
            if len(y) >= minn:
                ut[i] = (y <= v[i]).mean() * 100
    return pd.Series(ut, index=s.index)


def _hysterese(mask, ut_k=UT_MND):
    """Inn i tilstanden med en gang, ut etter ut_k maaneder paa rad under.

    Et symmetrisk varighetskrav leste tollsjokket (april 2025) og mars 2026 som
    rolig, fordi de var enkeltmaaneder. Et sjokk maa registreres i maaneden det
    skjer; usikkerheten er naar det slutter. NaN regnes som under grensen, men
    nullstiller ikke tilstanden med en gang."""
    ut, pa, under = [], False, 0
    for v in mask:
        if bool(v):
            pa, under = True, 0
        elif pa:
            under += 1
            if under >= ut_k:
                pa, under = False, 0
        ut.append(pa)
    return pd.Series(ut, index=mask.index)


def _sjokk_ord(nivaa_opp, volvar_opp, hoy_begge, volvar_kjent):
    """De fem ordene i sjokkfeltet. Rekkefoelgen er streng: sjokk foerst."""
    if hoy_begge:
        return "sjokk"
    if not volvar_kjent:
        return "spent nivå" if nivaa_opp else "rolig"
    if nivaa_opp and volvar_opp:
        return "forhøyet"
    if nivaa_opp:
        return "spent nivå"
    if volvar_opp:
        return "urolig forventning"
    return "rolig"


def _A_raa(v):
    o = np.full(len(v), np.nan)
    for i in range(59, len(v)):
        o[i] = (v[: i + 1] <= v[i]).mean()
    return (1 - o) * 100


def _r(x, n=2):
    return None if x is None or not np.isfinite(x) else round(float(x), n)


def beregn(priser_csv, note=print):
    # raavarer
    p = pd.read_csv(io.StringIO(priser_csv))
    p = p[~p.segment.str.startswith("ship_")]
    real = p.pivot(index="t", columns="segment", values="real").astype(float)
    real.index = pd.PeriodIndex(real.index, freq="M"); real = real.sort_index()
    A = pd.DataFrame({s: pd.Series(_A_raa(np.log(real[s].dropna().values)), index=real[s].dropna().index)
                      for s in real}).reindex(real.index)
    M = pd.DataFrame(index=real.index)
    M["median_A"] = A.median(axis=1)
    d12 = np.log(real) - np.log(real.shift(12))
    M["bredde"] = (d12 > 0).sum(axis=1) / d12.notna().sum(axis=1)
    kg = np.log(real.kobber / real.gold)
    M["kobber_gull_12m"] = 100 * (kg - kg.shift(12))
    M = M[M.index >= pd.Period("1965-01", "M")]

    # papirer
    syms = sorted({x[0] for v in INSTR.values() for x in v} | set(FONDER))
    uke = {}
    for s in syms:
        try:
            uke[s] = _dag(s).resample("W-FRI").last()
        except Exception:
            pass
    R = np.log(pd.DataFrame(uke)).diff()
    R = R[R.index >= "1990-01-01"]
    pk = []
    for i in range(len(R)):
        w = R.iloc[max(0, i - 12): i + 1].dropna(axis=1, thresh=13).dropna()
        w = w.loc[:, (w.std() > 1e-8) & ((w != 0).sum() >= 8)]
        if i < 12 or w.shape[1] < 15 or len(w) < 13:
            pk.append(np.nan); continue
        c = np.corrcoef(w.values.T); n = c.shape[0]
        pk.append((c.sum() - n) / (n * (n - 1)))
    U = pd.Series(pk, index=R.index)
    M["korr_papirer"] = _mnd(U)
    # Sjokkfeltets to ledd (11.11.2026). Hele maaneder, absolutte grenser.
    M["vix"] = _mnd_hel(_dag("^VIX"))
    try:
        M["vvix"] = _mnd_hel(_dag("^VVIX"))
    except Exception as e:
        note(f"   regime: VVIX mangler ({type(e).__name__}: {str(e)[:60]})")
        M["vvix"] = np.nan
    for sid, navn in (("BAA10Y", "kreditt"), ("T10Y2Y", "rentekurve")):
        try:
            M[navn] = _mnd(_fred(sid), "mean")
        except Exception as e:
            note(f"   regime: {sid} mangler ({type(e).__name__})")
    M = M.sort_index()
    M["vix_pct"] = _pit(M.vix); M["korr_pct"] = _pit(M.korr_papirer)
    # Rullende tiaarspersentil per ledd. Vises, setter ikke ordet.
    M["nivaa_pct"] = _rull(M.vix)
    M["volvar_pct"] = _rull(M.vvix) if M.vvix.notna().any() else np.nan
    # Ordet, maaned for maaned, med hysterese over hele historikken.
    M["nivaa_opp"] = _hysterese(M.vix >= NIVAA_GRENSER[0])
    M["volvar_opp"] = _hysterese(M.vvix >= VOLVAR_GRENSER[0])
    M["sjokk_hoy"] = _hysterese((M.vix >= NIVAA_GRENSER[1]) & (M.vvix >= VOLVAR_GRENSER[1]))
    M["sjokk_ord"] = [_sjokk_ord(M.nivaa_opp.iat[i], M.volvar_opp.iat[i],
                                 M.sjokk_hoy.iat[i], bool(np.isfinite(M.vvix.iat[i])))
                      for i in range(len(M))]
    if "kreditt" in M:
        M["kreditt_pct"] = _pit(M.kreditt)

    # likviditet
    lik = None
    try:
        walcl, tga, rrp = _fred("WALCL") / 1000, _fred("WTREGEN") / 1000, _fred("RRPONTSYD")
        uk = pd.concat([walcl.resample("W-WED").last(), tga.resample("W-WED").last(),
                        rrp.resample("W-WED").last()], axis=1).ffill().dropna(subset=[0, 1])
        uk.columns = ["fed", "tga", "rrp"]; uk["rrp"] = uk.rrp.fillna(0)
        uk["netto"] = uk.fed - uk.tga - uk.rrp
        n13 = 100 * (np.log(uk.netto) - np.log(uk.netto.shift(13)))
        ecb, eur, boj, jpy = _fred("ECBASSETSW"), _fred("DEXUSEU"), _fred("JPNASSETS"), _fred("DEXJPUS")
        g = pd.DataFrame({"fed": _mnd(walcl), "ecb": _mnd(ecb) / 1000 * _mnd(eur, "mean"),
                          "boj": _mnd(boj) / 10 / _mnd(jpy, "mean")}).dropna()
        g["sum"] = g.sum(axis=1); g6 = 100 * (np.log(g["sum"]) - np.log(g["sum"].shift(6)))
        nm = _mnd(uk.netto); n13m = _mnd(n13)
        lik = {"dato": str(uk.index[-1].date()), "fed_netto_mrd": _r(uk.netto.iloc[-1], 0),
               "fed_netto_13u_pst": _r(n13.iloc[-1], 1), "rrp_mrd": _r(uk.rrp.iloc[-1], 0),
               "rrp_topp_mrd": _r(uk.rrp.max(), 0), "rrp_topp_dato": str(uk.rrp.idxmax().date()),
               "tga_mrd": _r(uk.tga.iloc[-1], 0), "fed_balanse_mrd": _r(uk.fed.iloc[-1], 0),
               "sb_mnd": str(g.index[-1]), "sb_sum_mrd": _r(g["sum"].iloc[-1], 0), "sb_6m_pst": _r(g6.iloc[-1], 1),
               "serie": [{"t": str(t), "netto": _r(nm[t], 0), "n13": _r(n13m.get(t), 1)}
                         for t in nm.index[-60:]]}
    except Exception as e:
        note(f"   regime: likviditet mangler ({type(e).__name__}: {str(e)[:60]})")

    # siste maaned der alle hovedmaalene finnes
    siste = M.dropna(subset=["bredde", "median_A", "vix_pct", "korr_pct"]).index[-1]
    r = M.loc[siste]
    fra90 = M.index >= pd.Period("1990-01", "M")
    q10 = float(M.median_A[fra90].quantile(0.1))
    vekst = "bred oppgang" if r.bredde >= 0.6 else ("bred nedgang" if r.bredde <= 0.4 else "blandet")
    sjokk = M.sjokk_ord.loc[siste]
    boom = "alt dyrt" if r.median_A <= q10 else "nei"

    def start_av(maske):
        """Foerste maaned i den sammenhengende perioden som slutter i siste maaned, eller None."""
        m = maske.loc[:siste].dropna()
        if not len(m) or not m.iloc[-1]:
            return None
        i = len(m) - 1
        while i > 0 and m.iloc[i - 1]:
            i -= 1
        return str(m.index[i])
    nedgang_siden = start_av(M.bredde <= 0.4)
    # Foerste maaned i den paagaaende perioden der ordet ikke er rolig.
    sjokk_siden = start_av(M.sjokk_ord != "rolig")

    dims = [k for k in ("bredde", "median_A", "vix_pct", "korr_pct", "kreditt_pct", "rentekurve") if k in M]
    X = M[dims].dropna()
    Z = (X - X.mean()) / X.std()
    dist = np.sqrt(((Z - Z.loc[siste]) ** 2).sum(axis=1)) if siste in Z.index else pd.Series(dtype=float)
    dist = dist[dist.index <= siste - 24].sort_values()
    analoger, vist = [], []
    for t, d in dist.items():
        if any(abs((t - v).n) < 6 for v in vist):
            continue
        vist.append(t)
        nh = min(HENDELSER, key=lambda h: abs((pd.Period(h, "M") - t).n))
        analoger.append({"t": str(t), "avstand": _r(d, 2),
                         "naer": HENDELSER[nh] if abs((pd.Period(nh, "M") - t).n) <= 6 else None})
        if len(analoger) == 5:
            break

    serie = [{"t": str(t), "bredde": _r(M.bredde.get(t), 2), "median_A": _r(M.median_A.get(t), 1),
              "vix_pct": _r(M.vix_pct.get(t), 0), "korr_pct": _r(M.korr_pct.get(t), 0),
              "nivaa": _r(M.vix.get(t), 2), "volvar": _r(M.vvix.get(t), 2),
              "nivaa_pct": _r(M.nivaa_pct.get(t), 0), "volvar_pct": _r(M.volvar_pct.get(t), 0),
              "ord": M.sjokk_ord.get(t)}
             for t in M.index[M.index <= siste][-60:]]
    return {"id": "regime", "laget": str(dt.date.today()), "mnd": str(siste),
            "vekst": {"ord": vekst, "bredde": _r(r.bredde, 2), "kobber_gull_12m": _r(r.kobber_gull_12m, 1),
                      "nedgang_siden": nedgang_siden},
            "sjokk": {"ord": sjokk,
                      # de to leddene som setter ordet
                      "nivaa": _r(r.vix, 2), "nivaa_pct": _r(r.get("nivaa_pct"), 0),
                      "nivaa_grenser": list(NIVAA_GRENSER),
                      "volvar": _r(r.get("vvix"), 2), "volvar_pct": _r(r.get("volvar_pct"), 0),
                      "volvar_grenser": list(VOLVAR_GRENSER),
                      "volvar_kjent": bool(np.isfinite(r.get("vvix", np.nan))),
                      "ut_mnd": UT_MND,
                      # vises, men utenfor ordet
                      "korr_papirer": _r(r.korr_papirer, 2), "korr_pct": _r(r.korr_pct, 0),
                      # det gamle voksende maalet, for bakoverkompatibilitet
                      "vix": _r(r.vix, 1), "vix_pct": _r(r.vix_pct, 0),
                      "sjokk_siden": sjokk_siden,
                      "merknad": "Nivå er månedssnittet av VIX, volvariasjon månedssnittet av VVIX, "
                                 f"begge mot absolutte grenser ({NIVAA_GRENSER[0]} og {NIVAA_GRENSER[1]} "
                                 f"for nivå, {VOLVAR_GRENSER[0]} og {VOLVAR_GRENSER[1]} for volvariasjon). "
                                 f"Ordet går opp med én gang og ned etter {UT_MND} måneder under. "
                                 "Persentilene er rullende ti år og vises bare. Papirkorrelasjonen står "
                                 "utenfor ordet. Grensene er valgt, ikke målt: sonden sonde_kjor_vvix_sjokk "
                                 "viste at ingen av målene skiller utfallene etter bunnsonen. Kontekst, "
                                 "ikke et signal."
                                 + ("" if bool(np.isfinite(r.get("vvix", np.nan)))
                                    else " VVIX finnes først fra januar 2007, så volvariasjonen er ukjent "
                                         "denne måneden og ordet er satt av nivået alene.")},
            "boom": {"ord": boom, "median_A": _r(r.median_A, 1), "grense": _r(q10, 1)},
            "kreditt": _r(r.get("kreditt"), 2), "kreditt_pct": _r(r.get("kreditt_pct"), 0),
            "rentekurve": _r(r.get("rentekurve"), 2), "likviditet": lik, "analoger": analoger,
            "analog_dim": dims, "serie": serie,
            "kilder": "Råvarer: priser_mnd.csv. Papirer, VIX og VVIX: Yahoo. Kreditt, rentekurve og likviditet: FRED "
                      "(BAA10Y, T10Y2Y, WALCL, WTREGEN, RRPONTSYD, ECBASSETSW, JPNASSETS, DEXUSEU, DEXJPUS)."}


def kjor(lager, note=print):
    try:
        priser = lager.les("serier/priser_mnd.csv")[0]
        tekst = json.dumps(beregn(priser, note), ensure_ascii=False, indent=1) + "\n"
        t, sha = lager.les(FIL)
        if t is None:
            lager.opprett(FIL, tekst)
        elif t != tekst:
            lager.erstatt(FIL, tekst, sha)
        note(f"   kontekst {FIL}: skrevet")
    except Exception as e:
        note(f"   kontekst {FIL} feilet: {type(e).__name__}: {str(e)[:80]}")


if __name__ == "__main__":
    import os
    rot = os.path.dirname(os.path.abspath(__file__))
    ut = beregn(open(os.path.join(rot, "serier/priser_mnd.csv"), encoding="utf-8").read())
    print(json.dumps({k: v for k, v in ut.items() if k not in ("serie",)}, ensure_ascii=False, indent=1)[:3000])
