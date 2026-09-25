# ---------------------------------------------------------------------------
# laks_innhent: laks som observasjonspanel, uten flagg
#
# Laksesonden (25.09.2026) viste at marginen mot produksjonskostnaden ikke
# sier noe om laksepapirene 24 maaneder fram (rho 0,108, p 0,353). Laks faar
# derfor ikke flagg. Frode vil likevel ha laks paa bordet som panel, for aa
# se prisen, marginen og papirene. Denne fila henter det som trengs, med
# noyaktig samme regnestykke som sonden, slik at tallene paa dashbordet er
# de samme som ble testet:
#
#   pris      SSB tabell 03024, fersk oppalen laks, kilopris per uke,
#             snittet per maaned (maanedsserie fra 2000)
#   valuta    Norges Bank USD/NOK maanedssnitt, reserve Yahoo NOK=X
#   sesong    faktor per kalendermaaned for aar Y, maalt bare paa data til og
#             med juni Y-1 mot et sentrert 2x12 snitt (se sesongfaktorer)
#   kostnad   Fiskeridirektoratets loennsomhetsundersoekelse, produksjons-
#             kostnad per kilo for hele landet. Aar Y regnes kjent fra
#             desember Y+1 og staar flatt til neste aar er kjent.
#   margin    sesongjustert kilopris i kroner delt paa kostnaden
#
# Den gamle kostnadsserien (1986 til 2008) er avsluttet og ligger bare som
# .xls, som krever en pakke den ukentlige innhentingen ikke har. Tallene under
# er fra sonden 25.09.2026, allerede skjoetet til den nye serien med faktoren
# 1,024 fra overlappen i 2008. De endres aldri. Den nye serien (fra 2008)
# hentes hver uke. Svarer ikke Fiskeridirektoratet, brukes forrige ukes
# kopi (laks_kost.json i repoet), og det sies fra.
# ---------------------------------------------------------------------------

import datetime as dt, io, json, re
import numpy as np
import pandas as pd
import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
SSB = "https://data.ssb.no/api/v0/no/table/03024"
FISKDIR = ("https://www.fiskeridir.no/Akvakultur/Tall-og-analyse/"
           "Loennsomhetsundersoekelse-for-laks-og-regnbueoerret")
SES_MIN_AAR, SES_VINDU = 5, 10
KOST_GAMMEL = {1986: 37.83, 1987: 35.28, 1988: 31.52, 1989: 30.20, 1990: 30.27, 1991: 31.66,
               1992: 28.87, 1993: 24.05, 1994: 20.86, 1995: 19.15, 1996: 17.32, 1997: 16.58,
               1998: 16.76, 1999: 16.42, 2000: 15.46, 2001: 15.27, 2002: 16.76, 2003: 16.41,
               2004: 15.52, 2005: 14.14, 2006: 15.09, 2007: 16.30}


def _post(url, js):
    r = requests.post(url, json=js, headers=UA, timeout=60)
    r.raise_for_status()
    return r


def hent_ukepris(get):
    """[(torsdag i uka, kr/kg)] for fersk oppalen laks."""
    meta = get(SSB).json()
    var = {v["code"]: v for v in meta["variables"]}
    tidkode = next(c for c, v in var.items() if v.get("time") or c.lower() == "tid")
    innh = next(c for c in var if c.lower().startswith("contents"))
    pris = [v for v, t in zip(var[innh]["values"], var[innh]["valueTexts"]) if "pris" in t.lower()]
    qry = [{"code": innh, "selection": {"filter": "item", "values": pris[:1]}}]
    for c, v in var.items():
        if c in (tidkode, innh):
            continue
        valg = [x for x, t in zip(v["values"], v["valueTexts"]) if "fersk" in t.lower()] or v["values"][:1]
        qry.append({"code": c, "selection": {"filter": "item", "values": valg[:1]}})
    js = _post(SSB, {"query": qry, "response": {"format": "json-stat2"}}).json()
    tider = list(js["dimension"][tidkode]["category"]["index"].keys())
    uke = []
    for tk, v in zip(tider, js["value"]):
        m = re.match(r"(\d{4})U(\d{2})", tk)
        if m and v is not None:
            try:
                uke.append((dt.date.fromisocalendar(int(m.group(1)), int(m.group(2)), 4), float(v)))
            except ValueError:
                pass
    s = pd.Series(dict(uke)).sort_index()
    if s.empty:
        raise ValueError("SSB ga ingen ukepriser")
    return s


def hent_usdnok(get, reserve):
    try:
        t = get("https://data.norges-bank.no/api/data/EXR/M.USD.NOK.SP"
                "?format=csv&startPeriod=1995&locale=en").text
        d = pd.read_csv(io.StringIO(t), sep=None, engine="python")
        tk = next(c for c in d.columns if "TIME" in c.upper())
        vk = next(c for c in d.columns if "OBS_VALUE" in c.upper())
        s = pd.Series(pd.to_numeric(d[vk].astype(str).str.replace(",", "."), errors="coerce").values,
                      index=pd.PeriodIndex(d[tk].astype(str), freq="M")).dropna()
        return s, "Norges Bank, månedssnitt"
    except Exception:
        return reserve("NOK=X"), "Yahoo NOK=X, månedsslutt (reserve)"


def sesongfaktorer(ln):
    """Samme som sonde_kjor_laks.py. Faktor per kalendermaaned for aar Y, bare
    fra avvik mot et sentrert 2x12 snitt som kan regnes med data til og med
    desember Y-1, altsaa maaneder til og med juni Y-1."""
    ma = pd.Series(ln.values, index=ln.index).rolling(13, center=True).apply(
        lambda w: (0.5 * w[0] + w[1:12].sum() + 0.5 * w[12]) / 12, raw=True)
    dev = (ln - ma).dropna()
    fak = {}
    for y in sorted({p.year for p in ln.index}):
        sist = pd.Period(f"{y - 1}-06", "M")
        forst = pd.Period(f"{y - SES_VINDU}-01", "M")
        d = dev[(dev.index >= forst) & (dev.index <= sist)]
        per = d.groupby([p.month for p in d.index])
        if len(per) < 12 or per.size().min() < SES_MIN_AAR:
            continue
        f = per.mean()
        fak[y] = f - f.mean()
    ut = pd.Series([fak[p.year][p.month] if p.year in fak else np.nan for p in ln.index], index=ln.index)
    return ut, fak


def hent_kost_ny(get):
    """Ny serie for hele landet (fra 2008), {aar: kr/kg}."""
    import openpyxl  # noqa: F401  (xlsx)
    side = get(FISKDIR).text
    lenker = {(u if u.startswith("http") else "https://www.fiskeridir.no" + u)
              for u in re.findall(r'href="([^"]+\.xlsx[^"]*)"', side)}
    lenker = sorted(u for u in lenker if "kostnad-pr-kg" in u) or sorted(lenker)
    for u in lenker:
        ark = pd.read_excel(io.BytesIO(get(u, timeout=90).content), sheet_name=None, header=None)
        for navn, df in ark.items():
            if "hele landet" not in navn.lower():
                continue
            df = df.astype(object)
            aarrad = None
            for i in range(min(len(df), 40)):
                aar = [x for x in df.iloc[i].tolist() if isinstance(x, (int, float)) and not pd.isna(x)
                       and 1980 <= float(x) <= 2035 and float(x) == int(x)]
                if len(aar) >= 8:
                    aarrad = i; break
            if aarrad is None:
                continue
            kol = {j: int(x) for j, x in enumerate(df.iloc[aarrad].tolist())
                   if isinstance(x, (int, float)) and not pd.isna(x) and 1980 <= float(x) <= 2035}
            for i in range(len(df)):
                et = " ".join(str(x) for x in df.iloc[i].tolist()[:3] if isinstance(x, str)).lower()
                if "produksjonskost" in et and ("kg" in et or "kilo" in et):
                    v = {kol[j]: float(df.iat[i, j]) for j in kol
                         if isinstance(df.iat[i, j], (int, float)) and not pd.isna(df.iat[i, j]) and df.iat[i, j] > 0}
                    if len(v) >= 8 and min(v) <= 2008:
                        return v, u.split("/")[-1].split("?")[0]
    raise ValueError("fant ikke produksjonskostnad per kilo for hele landet")


def hent(get, reserve_valuta, les=None, note=print):
    """Returnerer dict med serien til build_segment (sesongjustert nominell
    USD/kg per maaned) og alt panelet trenger. les(sti) -> tekst eller None
    (forrige ukes kostnadskopi)."""
    uke = hent_ukepris(get)
    pi = pd.PeriodIndex(pd.to_datetime(uke.index), freq="M")
    nok = uke.groupby(pi).mean()
    uker = uke.groupby(pi).size()
    usdnok, valkilde = hent_usdnok(get, reserve_valuta)

    ln = np.log(nok)
    fak, fak_aar = sesongfaktorer(ln)
    just_nok = (ln - fak).dropna()
    usd = (nok / usdnok.reindex(nok.index)).dropna()
    usd_just = (usd * np.exp(-fak.reindex(usd.index))).dropna()

    kost_kilde, kost_ny = None, None
    try:
        kost_ny, fil = hent_kost_ny(get)
        kost_kilde = f"Fiskeridirektoratet, {fil}"
    except Exception as e:
        tekst = les("laks_kost.json") if les else None
        if tekst:
            k = json.loads(tekst)
            kost_ny = {int(a): v for a, v in k["ny"].items()}
            kost_kilde = f"forrige ukes kopi ({k.get('hentet')}), Fiskeridirektoratet svarte ikke"
            note("laks kostnad", False, f"{type(e).__name__}: {str(e)[:50]}. Bruker kopien")
        else:
            raise
    if abs(kost_ny.get(2008, 0) / 18.61 - 1) > 0.02:
        note("laks kostnad", False, f"2008 i ny serie er {kost_ny.get(2008)}, ikke 18,61 som ved skjoetingen")
    kost = dict(KOST_GAMMEL)
    kost.update(kost_ny)
    kost = pd.Series(kost).sort_index()
    kjent = pd.Series({pd.Period(f"{int(a) + 1}-12", "M"): float(v) for a, v in kost.items()}).sort_index()
    ks = kjent.reindex(pd.period_range(kjent.index[0], just_nok.index[-1], freq="M")).ffill()
    margin = (np.exp(just_nok) / ks.reindex(just_nok.index)).dropna()
    siste_kostaar = int(kost.index[-1])
    fersk = siste_kostaar >= dt.date.today().year - 3

    return {"usd_just": usd_just, "nok": nok, "uker": uker, "fak": fak, "fak_aar": fak_aar,
            "just_nok": just_nok, "margin": margin, "kost": kost, "kost_ny": kost_ny,
            "kost_kilde": kost_kilde, "kost_fersk": fersk, "valuta": valkilde,
            "siste_uke": (str(uke.index[-1]), float(uke.iloc[-1]))}


def berik(seg, L, expanding_pct):
    """Legger margin og laksefelt paa segmentet fra build_segment, og tar bort
    flagget. Laks er observasjon: bunnregelen er ikke testet gyldig for laks,
    og marginen ga ingen informasjon om papirene."""
    m = L["margin"]
    am = pd.Series((1 - expanding_pct(np.log(m.values))) * 100, index=m.index)
    for r in seg["series"]:
        p = pd.Period(r["t"], "M")
        r["flagg"], r["oppsikt"] = False, False
        r["margin"] = None if p not in m.index else round(float(m[p]), 3)
        r["Am"] = None if p not in am.index or np.isnan(am[p]) else round(float(am[p]), 1)
    sc = seg["scores"]
    sc["flagg"], sc["oppsikt"], sc["months_in_zone"] = False, False, 0
    sc["observasjon"] = True
    sc["margin"] = round(float(m.iloc[-1]), 3)
    sc["A_margin"] = None if np.isnan(am.iloc[-1]) else round(float(am.iloc[-1]), 1)
    fa = L["fak_aar"][max(L["fak_aar"])]
    uke_dato, uke_pris = L["siste_uke"]
    seg["laks"] = {
        "margin": sc["margin"], "A_margin": sc["A_margin"], "margin_mnd": str(m.index[-1]),
        "margin_min": round(float(m.min()), 2), "margin_min_t": str(m.idxmin()),
        "margin_maks": round(float(m.max()), 2), "margin_maks_t": str(m.idxmax()),
        "margin_fra": str(m.index[0]),
        "kost_siste_aar": int(L["kost"].index[-1]), "kost_siste": round(float(L["kost"].iloc[-1]), 2),
        "kost_fersk": bool(L["kost_fersk"]), "kost_kilde": L["kost_kilde"],
        "uke": uke_dato, "uke_nok_kg": round(uke_pris, 2),
        "mnd_nok_kg": round(float(L["nok"].iloc[-1]), 2), "mnd_uker": int(L["uker"].iloc[-1]),
        "sesong_mnd": str(L["nok"].index[-1]),
        "sesong_pst": round(float(100 * (np.exp(fa[L["nok"].index[-1].month]) - 1)), 1),
        "sesong_amplitude_pst": round(float(100 * (fa.max() - fa.min())), 1),
        "valuta": L["valuta"],
        "test": "Margin mot papirene 24 mnd fram: rho 0,108, p 0,353 (sonden 25.09.2026). Ikke flagg.",
    }
    return seg
