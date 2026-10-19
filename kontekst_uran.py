# ---------------------------------------------------------------------------
# kontekst_uran: holder kontrollserien for uranfutures levende (19.10.2026,
# Frodes bestilling).
#
# uran_futures_uke.csv ble lastet opp for haand 24.09.2026 (UxC-futures,
# nest naermeste kontrakt, ukentlig fra 2007) og ble aldri oppdatert; siste
# notering var 2026-09-20. Fila brukes av uran_kilde.py til aa kontrollere
# Camecos spotpris fra 2022, og av helse.py som en ukentlig kilde.
#
# Dette skriptet legger til en rad i uken: siste notering av naermeste
# UxC-kontrakt hos Yahoo (UX=F, CME). Yahoo gir bare dagens notering, ikke
# historikk, saa hullet fra 2026-09-27 til 2026-10-11 fylles ikke. Datoen er
# soendagen som starter uken noteringen er fra, som i den opprinnelige fila.
# Finnes soendagen fra foer, erstattes verdien. NB: fra 2026-10 er det
# naermeste kontrakt, ikke nest naermeste; forskjellen er liten, og
# kontrollen bruker median over maaneder.
#
# I tillegg (19.10.2026) skrives uran_kontrakt.json: spot og langsiktig
# kontraktspris fra Camecos side, forskjellen (spot / kontrakt - 1) med
# persentil mot egen historikk fra 1996, og de siste 60 maanedene til
# dashbordet (marked/uran_kontrakt). Kontekst, ikke en skaar:
# sonde_kjor_uran_spread fant at forskjellen ikke var et signal.
#
# Kalles hver uke fra shadow_challenger.kjor (som kontekst_laks og
# kontekst_regime). Fila er data, ikke kode, saa Championens hash (der
# uran_kilde.py er med) endres ikke. En feil her rammer ingenting annet.
# ---------------------------------------------------------------------------

import datetime as dt
import json
import time
import requests

FIL = "uran_futures_uke.csv"
SYM = "UX=F"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}


def siste_notering():
    for i in range(4):
        try:
            r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{SYM}",
                             params={"range": "5d", "interval": "1d"}, headers=UA, timeout=40)
            m = r.json()["chart"]["result"][0]["meta"]
            pris, tid = m.get("regularMarketPrice"), m.get("regularMarketTime")
            if pris and tid and 10 < float(pris) < 500:
                return float(pris), dt.datetime.fromtimestamp(int(tid), dt.timezone.utc).date()
        except Exception:
            pass
        time.sleep(2 ** (i + 1))
    raise RuntimeError(f"Yahoo ga ingen notering for {SYM}")


def oppdater(tekst, pris, dato):
    """Ren funksjon: returnerer ny filtekst med raden for uken til dato."""
    sondag = dato - dt.timedelta(days=(dato.weekday() + 1) % 7)
    linjer = tekst.strip().splitlines()
    hode, rader = linjer[0], linjer[1:]
    ny = f"{sondag.isoformat()},{round(pris, 2)}"
    if rader and rader[-1].split(",")[0] == sondag.isoformat():
        rader[-1] = ny
    elif rader and rader[-1].split(",")[0] > sondag.isoformat():
        return tekst          # aldri skriv bakover i tid
    else:
        rader.append(ny)
    return "\n".join([hode] + rader) + "\n"


CAMECO = "https://www.cameco.com/invest/markets/uranium-price"
KFIL = "uran_kontrakt.json"


def kontrakt(html=None, idag=None):
    """Spot og langsiktig kontraktspris fra Camecos tabell (maanedsslutt).
    Kontekst, ikke en skaar: sonde_kjor_uran_spread (09.10.2026) fant at
    forskjellen ikke varslet Cameco mot SPY over 12 mnd."""
    import io
    import pandas as pd
    if html is None:
        r = requests.get(CAMECO, headers=UA, timeout=60)
        r.raise_for_status()
        html = r.text
    for t in pd.read_html(io.StringIO(html)):
        ks = [c for c in t.columns if "spot" in str(c).lower()]
        kl = [c for c in t.columns if "long" in str(c).lower()]
        if not ks or not kl:
            continue
        d = pd.to_datetime(t.iloc[:, 0].astype(str), errors="coerce")
        df = pd.DataFrame({"spot": pd.to_numeric(t[ks[0]], errors="coerce").values,
                           "kontrakt": pd.to_numeric(t[kl[0]], errors="coerce").values}, index=d)
        df = df[df.index.notna()].dropna()
        if len(df) < 120:
            continue
        df.index = df.index.to_period("M")
        df = df[~df.index.duplicated(keep="last")].sort_index()
        df["spread"] = 100 * (df.spot / df.kontrakt - 1)
        s = df.spread
        siste = df.index[-1]
        k12 = df.kontrakt.get(siste - 12)
        return {"id": "uran_kontrakt", "laget": str(idag or dt.date.today()), "mnd": str(siste),
                "spot": round(float(df.spot.iloc[-1]), 2), "kontrakt": round(float(df.kontrakt.iloc[-1]), 2),
                "spread_pst": round(float(s.iloc[-1]), 1),
                "spread_pctl": round(float((s <= s.iloc[-1]).mean() * 100), 0),
                "spread_median": round(float(s.median()), 1),
                "kontrakt_12m_pst": None if k12 is None else round(float(100 * (df.kontrakt.iloc[-1] / k12 - 1)), 1),
                "fra": str(df.index[0]),
                "kilde": "Cameco (UxC og TradeTech), månedsslutt; spot og langsiktig kontraktspris, USD/lb U3O8",
                "serie": [{"t": str(p), "spot": round(float(r.spot), 2), "kontrakt": round(float(r.kontrakt), 2)}
                          for p, r in df.iloc[-60:].iterrows()]}
    raise ValueError("fant ingen tabell med spot og langsiktig pris")


def kjor(lager, note=print):
    try:
        tekst = json.dumps(kontrakt(), ensure_ascii=False, indent=1) + "\n"
        t, sha = lager.les(KFIL)
        if t is None:
            lager.opprett(KFIL, tekst)
        elif t != tekst:
            lager.erstatt(KFIL, tekst, sha)
        note(f"   kontekst {KFIL}: skrevet")
    except Exception as e:
        note(f"   kontekst {KFIL} feilet: {type(e).__name__}: {str(e)[:80]}")
    try:
        pris, dato = siste_notering()
        if (dt.date.today() - dato).days > 10:
            raise RuntimeError(f"notering fra {dato} er for gammel")
        t, sha = lager.les(FIL)
        if t is None:
            raise RuntimeError(f"{FIL} finnes ikke")
        ny = oppdater(t, pris, dato)
        if ny != t:
            lager.erstatt(FIL, ny, sha)
        note(f"   kontekst {FIL}: {dato} {pris}")
    except Exception as e:
        note(f"   kontekst {FIL} feilet: {type(e).__name__}: {str(e)[:80]}")


if __name__ == "__main__":
    p, d = siste_notering()
    print(p, d)
    print(oppdater(open(FIL, encoding="utf-8").read(), p, d).strip().splitlines()[-3:])
