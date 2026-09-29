# ---------------------------------------------------------------------------
# c_manuell: overlevelsesporten C for selskaper som ikke rapporterer til SEC
#
# Innfoert 28.09.2026. Brent sto med port "ukjent" fordi ingen av papirene
# (Aker BP, DNO, IOGP-fondet) finnes hos SEC, mens Brent samtidig holdes etter
# det parallelle signalet til desember 2027. Salgsregelen "selg tidligere hvis
# porten stenger" hadde da ingenting aa stenge.
#
# Tallene leses for haand fra aarsrapportene (sonde_kjor_c_manuell,
# sonde_kjor_c_manuell2, sonde_kjor_c_manuell3) og ligger i c_manuell.json med
# kilde per selskap. Regnestykket er det samme som for SEC-selskapene i
# overlevelse_c.py:
#   C1 = siste kontanter / (brennrate per kvartal) der brennraten er det
#        verste driftsaaret i hele historikken minus siste aars renter.
#   aapen:  C1 >= 16 kvartaler (eller positiv drift etter renter) og netto
#           gjeld / egenkapital under 1,5, trang: 8 til 16, stengt: under 8.
#   netto gjeld over 3x egenkapital gjoer aapen til trang.
#
# Renter i driften (29.09.2026, samme regel som SEC-delen i overlevelse_c.py):
# under IFRS kan betalte renter foeres under drift eller finansiering. Ligger de
# under drift, er de allerede trukket i driftskontantstroemmen og skal ikke
# trekkes fra en gang til. Feltet "renter_i_drift" (true/false) med kilde i
# "renter_kilde" sier hvor selskapet foerer dem. "renter_i_drift_aar" kan
# overstyre for enkeltaar ({"2006": false}). Regelen avgjoeres for bunnaaret og
# for siste aar hver for seg. Mangler feltet, trekkes renten fra som foer, og
# utskriften sier at klassifiseringen ikke er lest.
#
# Produksjonsstart (Frodes beslutning 29.09.2026): aar foer produksjonsstart
# teller ikke. Et utviklingsselskap brenner penger fordi det bygger, ikke fordi
# raavaren er i en bunn, og det sier ingenting om hvordan selskapet taaler en
# syklisk bunn. Feltet "produksjon_fra" i c_manuell.json er det foerste hele
# regnskapsaaret med produksjon; tidligere driftsaar utelates, med kilde i
# feltet "produksjon_kilde". Aaret produksjonen startet midt i, teller ikke.
#
# Valuta: et forhold mellom to beloep maa ha samme valuta. Driftsaar i en annen
# valuta enn de siste balansetallene regnes om med Norges Banks aarssnitt for
# det aaret (snitt passer for en stroem over aaret). Mangler kursen for et
# aar, hoppes selskapet over. Ingen kurs gjettes.
# ---------------------------------------------------------------------------

import io, json, os
import pandas as pd
import requests

PORT_KVARTALER = 8
_NB = {}


def nok_per_enhet(valuta):
    """NOK per en enhet valuta, aarssnitt, fra Norges Bank."""
    if valuta == "NOK":
        return None
    if valuta not in _NB:
        t = requests.get(f"https://data.norges-bank.no/api/data/EXR/A.{valuta}.NOK.SP"
                         "?format=csv&startPeriod=1995&locale=en", timeout=40).text
        d = pd.read_csv(io.StringIO(t), sep=None, engine="python")
        tk = next(c for c in d.columns if "TIME" in c.upper())
        vk = next(c for c in d.columns if "OBS_VALUE" in c.upper())
        v = pd.to_numeric(d[vk].astype(str).str.replace(",", "."), errors="coerce")
        mk = next((c for c in d.columns if c.upper() == "UNIT_MULT"), None)
        if mk is not None:   # noen valutaer noteres per 100
            v = v / (10 ** pd.to_numeric(d[mk], errors="coerce").fillna(0))
        _NB[valuta] = pd.Series(v.values, index=d[tk].astype(str).str[:4].astype(int)).dropna()
    return _NB[valuta]


def omregn(belop, fra, til, aar, kurs=nok_per_enhet):
    """Beloep i valuta 'fra' til valuta 'til' med aarssnittet for 'aar'."""
    if fra == til:
        return belop
    nok = belop if fra == "NOK" else belop * float(kurs(fra)[aar])
    return nok if til == "NOK" else nok / float(kurs(til)[aar])


def port_fra(kont, drift, gjeld, ek, rente, i_drift=lambda aar: False):
    """Samme regler som overlevelse_c.py. drift: pd.Series aar -> beloep.
    i_drift(aar) sier om betalte renter allerede er trukket i driften det aaret."""
    stress, naa, bunnaar = float(drift.min()), float(drift.iloc[-1]), int(drift.idxmin())
    siste = int(drift.index[-1])

    def kv(ocf, trukket):
        fri = ocf - (0.0 if trukket else (rente or 0.0))
        return None if fri >= 0 else round(kont / (-fri / 4), 1)
    kvartaler, kvartaler_naa = kv(stress, i_drift(bunnaar)), kv(naa, i_drift(siste))
    ngek = None if not ek or ek <= 0 or gjeld is None else round((gjeld - kont) / ek, 2)
    # Dekning = drift foer renter delt paa renter.
    dekning = None if not rente else round((stress + (rente if i_drift(bunnaar) else 0.0)) / rente, 1)
    if kvartaler is None:
        port, hvorfor = "aapen", f"positiv drift etter renter selv i {bunnaar}"
    elif kvartaler >= 16 and (ngek is None or ngek < 1.5):
        port, hvorfor = "aapen", f"{kvartaler} kvartaler"
    elif kvartaler >= PORT_KVARTALER:
        port, hvorfor = "trang", f"{kvartaler} kvartaler"
    else:
        port, hvorfor = "stengt", f"bare {kvartaler} kvartaler"
    if ngek is not None and ngek > 3 and port == "aapen":
        port, hvorfor = "trang", hvorfor + f", men netto gjeld {ngek}x egenkapital"
    return {"port": port, "hvorfor": hvorfor, "kvartaler": kvartaler, "kvartaler_naa": kvartaler_naa,
            "bunnaar": bunnaar, "netto_gjeld_ek": ngek, "rentedekning": dekning,
            "renter_i_drift_bunnaar": i_drift(bunnaar), "renter_i_drift_siste": i_drift(siste),
            "stress": stress, "naa": naa}


def maal(aksjer, sti="c_manuell.json", kurs=nok_per_enhet):
    """Returnerer {ticker: selskapspost} for papirene i c_manuell.json som
    ogsaa staar paa tavlen. aksjer er AKSJER fra overlevelse_c.py."""
    if not os.path.exists(sti):
        print("   c_manuell.json finnes ikke")
        return {}
    man = json.load(open(sti, encoding="utf-8"))
    ut = {}
    for tk, d in man.items():
        if tk.startswith("_"):
            continue
        if tk not in aksjer:
            print(f"   {tk:12s} staar ikke paa tavlen, hoppes over")
            continue
        s = d["siste"]
        val = s["valuta"]
        try:
            drift = pd.Series({int(a): omregn(v["drift"], v["valuta"], val, int(a), kurs)
                               for a, v in d["drift"].items() if v.get("drift") is not None}).sort_index()
        except Exception as e:
            print(f"   {tk:12s} valutakurs mangler: {type(e).__name__} {str(e)[:60]}, hoppes over")
            continue
        pf = d.get("produksjon_fra")
        if pf is not None:
            utelatt = [int(a) for a in drift.index if a < int(pf)]
            drift = drift[drift.index >= int(pf)]
            if utelatt:
                print(f"   {tk:12s} aar foer produksjonsstart utelatt: {utelatt}")
        if len(drift) < 4 or s["aar"] not in drift.index:
            print(f"   {tk:12s} for faa driftsaar ({len(drift)}) eller siste aar mangler, hoppes over")
            continue
        rid, unntak = d.get("renter_i_drift"), {int(a): bool(v) for a, v in (d.get("renter_i_drift_aar") or {}).items()}
        if rid is None:
            print(f"   {tk:12s} renter_i_drift mangler: klassifiseringen er ikke lest, renten trekkes fra som foer")
        i_drift = lambda aar, rid=rid, unntak=unntak: unntak.get(int(aar), bool(rid))
        r = port_fra(s["kontanter"], drift, s.get("gjeld"), s.get("egenkapital"), s.get("rente"), i_drift)
        ut[tk] = {"ticker": tk, "navn": aksjer[tk]["navn"], "bors": aksjer[tk]["bors"],
                  "segmenter": aksjer[tk]["segmenter"], "port": r["port"], "hvorfor": r["hvorfor"],
                  "kvartaler": r["kvartaler"], "kvartaler_naa": r["kvartaler_naa"],
                  "bunnaar": r["bunnaar"], "aar_historikk": len(drift),
                  "netto_gjeld_ek": r["netto_gjeld_ek"], "rentedekning": r["rentedekning"],
                  "kontanter_m": round(s["kontanter"], 1), "verste_drift_m": round(r["stress"], 1),
                  "drift_naa_m": round(r["naa"], 1), "rente_m": s.get("rente"), "valuta": val,
                  "aar": [int(drift.index[0]), int(drift.index[-1])],
                  "produksjon_fra": pf,
                  "renter_i_drift": rid, "renter_i_drift_bunnaar": r["renter_i_drift_bunnaar"],
                  "renter_i_drift_siste": r["renter_i_drift_siste"],
                  "kilde": "manuelt lest aarsrapport: " + d.get("kilde", "")}
        print(f"   {tk:12s} {r['port']:7s} {r['hvorfor'][:38]:40s} bunnaar {r['bunnaar']} av "
              f"{len(drift)} aar, netto gjeld/EK {str(r['netto_gjeld_ek']):>6}, "
              f"renter i drift {'ja' if r['renter_i_drift_bunnaar'] else 'nei'}  (manuelt)")
    return ut
