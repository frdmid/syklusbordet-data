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
# Kalles hver uke fra shadow_challenger.kjor (som kontekst_laks og
# kontekst_regime). Fila er data, ikke kode, saa Championens hash (der
# uran_kilde.py er med) endres ikke. En feil her rammer ingenting annet.
# ---------------------------------------------------------------------------

import datetime as dt
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


def kjor(lager, note=print):
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
