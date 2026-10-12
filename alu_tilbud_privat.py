# ---------------------------------------------------------------------------
# alu_tilbud_privat: produksjonen av aluminium utenfor Kina til det private
# dashbordet (Frodes beslutning 12.10.2026). Kontekst, ikke skaar, ikke
# Shadow-OOS.
#
# IAIs vilkaar tillater bare personlig, ikke-kommersiell bruk og ingen
# videreformidling. Repoet er offentlig, saa verken IAI-fila eller tallene fra
# den skal inn i repoet. Denne fila inneholder bare koden.
#
# Bruk (manuelt, naar IAI har publisert en ny maaned, normalt rundt den 20.):
#   1. Frode laster ned CSV fra international-aluminium.org/statistics/
#      primary-aluminium-production (tabell, Month, fra 1999-01, knappen CSV)
#      og legger den i data_privat/.
#   2. py alu_tilbud_privat.py data_privat/<fila>.csv
#      skriver data_privat/alu_tilbud.json.
#   3. Fila skrives til dashbordets database, marked/alu_tilbud (ArtifactData).
# Samme definisjoner som sonde_kjor_aluminium_tilbud: utenfor Kina = sum av
# de rapporterte regionene unntatt China (Estimated) og Estimated Unreported.
# ---------------------------------------------------------------------------

import datetime as dt, json, sys
import numpy as np
import pandas as pd

REG = ["Africa", "North America", "South America", "Asia (ex China)", "Western & Central Europe",
       "Russia & Eastern Europe", "Europe (inc Russia)", "Oceania", "Gulf Cooperation Council"]
TAK = 45_000            # tusen tonn per aar, Kinas tak


def lag(fil):
    d = pd.read_csv(fil, sep=";")
    d["mnd"] = pd.PeriodIndex(pd.to_datetime(d["Period from"]), freq="M")
    d = d.set_index("mnd").sort_index()
    num = lambda c: pd.to_numeric(d[c].astype(str).str.replace("*", "", regex=False).str.strip(), errors="coerce")
    ute = sum(num(c).fillna(0) for c in REG)
    kina = num("China (Estimated)")
    u12, k12 = ute.rolling(12).sum(), kina.rolling(12).sum()
    v = (100 * np.log(u12 / u12.shift(12))).dropna()
    serie = [{"t": str(p), "dB": round(float(v[p]), 2), "tonn": round(float(u12[p]))} for p in v.index[-60:]]
    return {"id": "alu_tilbud", "laget": str(dt.date.today()), "mnd": str(v.index[-1]),
            "vekst_ute_12m": round(float(v.iloc[-1]), 2), "ute_12m_tusen_tonn": round(float(u12.iloc[-1])),
            "kina_12m_tusen_tonn": round(float(k12.iloc[-1])), "kina_av_tak_pst": round(100 * float(k12.iloc[-1]) / TAK, 1),
            "kilde": "International Aluminium Institute (IAI), primærproduksjon; personlig bruk",
            "serie": serie}


if __name__ == "__main__":
    d = lag(sys.argv[1])
    json.dump(d, open("data_privat/alu_tilbud.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(d["mnd"], d["vekst_ute_12m"], d["ute_12m_tusen_tonn"], d["kina_12m_tusen_tonn"], d["kina_av_tak_pst"], len(d["serie"]))
