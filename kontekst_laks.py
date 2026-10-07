# ---------------------------------------------------------------------------
# kontekst_laks: staaende biomasse for laks i Norge til dashbordet
# (Frodes bestilling 07.10.2026). Kontekst, ikke en skaar, og ikke shadow-data.
#
# Skriver laks_biomasse.json: endringen i staaende biomasse (snitt av tre
# maaneder mot de samme tre maanedene aaret foer, i prosent), som i
# challenger_laks_tilbud_v1 og sonde_kjor_biomasse, og de siste 60 maanedene
# til kurven i laks-panelet. Kilde: Fiskeridirektoratets biomassestatistikk.
#
# Kalles hver uke fra shadow_challenger.kjor (etter Challengerne). Ikke med i
# Championens frosne filer og ikke i noen Challengers kode, saa endringer her
# endrer ingen modell. Onsdagsrutinen skriver fila til marked/laks_biomasse.
# ---------------------------------------------------------------------------

import datetime as dt, io, json, time
import pandas as pd
import requests

URL = "https://register.fiskeridir.no/biomassestatistikk/BIOSTAT-LAKS-FLK/biostat-total-flk.csv"
FIL = "laks_biomasse.json"


def hent():
    for i in range(4):
        try:
            r = requests.get(URL, headers={"User-Agent": "Syklusbordet"}, timeout=120)
            if r.status_code == 200:
                break
        except requests.RequestException:
            pass
        time.sleep(2 ** (i + 1))
    else:
        raise RuntimeError("Fiskeridirektoratet svarer ikke")
    d = pd.read_csv(io.StringIO(r.content.decode("utf-8-sig", errors="replace")), sep=";")
    d = d[d["ARTSID"].str.upper() == "LAKS"]
    d["BIOMASSE_KG"] = pd.to_numeric(d["BIOMASSE_KG"].astype(str).str.replace(",", "."), errors="coerce")
    d["mnd"] = pd.PeriodIndex(pd.to_datetime(dict(year=d["ÅR"], month=d["MÅNED_KODE"], day=1)), freq="M")
    b = d.groupby("mnd")["BIOMASSE_KG"].sum().sort_index()
    return b.reindex(pd.period_range(b.index[0], b.index[-1], freq="M"))


def lag(b, idag=None):
    b3 = b.rolling(3).mean()
    db = (100 * (b3 / b3.shift(12) - 1)).dropna()
    serie = [{"t": str(p), "dB": round(float(db[p]), 2), "tonn": round(float(b[p]) / 1000)} for p in db.index[-60:]]
    return {"id": "laks_biomasse", "laget": str(idag or dt.date.today()), "mnd": str(db.index[-1]),
            "dB": round(float(db.iloc[-1]), 2), "tonn": round(float(b.iloc[-1]) / 1000),
            "kilde": "Fiskeridirektoratet, biomassestatistikk (laks, hele landet)", "serie": serie}


def kjor(lager, note=print):
    try:
        tekst = json.dumps(lag(hent()), ensure_ascii=False, indent=1) + "\n"
        t, sha = lager.les(FIL)
        if t is None:
            lager.opprett(FIL, tekst)
        elif t != tekst:
            lager.erstatt(FIL, tekst, sha)
        note(f"   kontekst {FIL}: skrevet")
    except Exception as e:
        note(f"   kontekst {FIL} feilet: {type(e).__name__}: {str(e)[:80]}")


if __name__ == "__main__":
    d = lag(hent())
    open(FIL, "w", encoding="utf-8", newline="\n").write(json.dumps(d, ensure_ascii=False, indent=1) + "\n")
    print(FIL, d["mnd"], d["dB"], d["tonn"], len(d["serie"]))
