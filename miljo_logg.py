# ---------------------------------------------------------------------------
# miljo_logg: hvilke biblioteksversjoner som faktisk kjorte, uke for uke
# (Frodes bestilling 12.11.2026, steg 1 i notater/2026-11-11_gjennomgang.md).
#
# HVORFOR. Championen er frosset med sha256 av 16 kodefiler, men miljoet koden
# kjorer paa er ikke frosset. requirements.txt krevde bare "pandas>=2.0", og
# 11.11.2026 viste kjoeringen i Actions pandas 3.1.1: flyten har altsaa alt
# krysset en majorversjon uten at noen vet naar. Persentilene, polyfit og
# resample kan endre oppforsel over en slik grense.
#
# HVA DEN GJOER IKKE. Den pinner ingenting. En eksakt pinne i
# requirements.txt ville gjort stille avvik til HARD FEIL: mangler et hjul for
# runnerens Python, stopper hele onsdagen, og arbeidsflyten har ingen
# reserveinstallasjon (den eies av Cowork og kan ikke endres herfra). I stedet
# har requirements.txt oevre grenser ved neste majorversjon, og denne modulen
# registrerer hva som faktisk kjorte og sier fra naar det avviker fra
# config/miljo_kjent.json. Vil Frode ha eksakte pinner, maa Cowork foerst
# legge inn et reservesteg i ukentlig.yml; det staar i notatet.
#
# ROBUSTHET. Skriver til logg/miljo.csv, IKKE til shadow/: den mappen er
# modellens frosne register med hashkjede og manifest, og en fil utenfor
# manifestet hoerer ikke hjemme der. Bare tillegg (so.legg_til_rader), og en
# kjoering som alt har skrevet sin rad gjor ingenting.
# Raden er en per uke OG PLATTFORM, ikke bare per uke: ellers ville en lokal
# kjoering paa Frodes maskin bruke opp ukens plass og hindre Actions fra aa
# skrive den raden som gjelder for dataene. Samtidig blir det synlig at de to
# miljoene er ulike (12.11.2026: pandas 3.1.1 i Actions, 3.0.6 lokalt).
# Alt er pakket i try/except: en feil her skal aldri stoppe noe annet.
#
# Kalles fra shadow_challenger.kjor, sist, som kontekstmodulene.
# ---------------------------------------------------------------------------

import datetime as dt
import json
import platform
import sys
from zoneinfo import ZoneInfo

import shadow_oos as so

FIL = "logg/miljo.csv"
KJENT = "config/miljo_kjent.json"
PAKKER = ("pandas", "numpy", "requests", "openpyxl", "pdfplumber", "lxml")
F_MILJO = ["uke", "dato", "plattform", "python", *PAKKER, "avvik"]
OSLO = ZoneInfo("Europe/Oslo")


def versjoner():
    """Versjonene slik de er installert naa. Leser metadata, ikke pakkene selv,
    saa en pakke som ikke kan importeres likevel blir registrert."""
    from importlib.metadata import PackageNotFoundError, version
    ut = {"python": ".".join(str(x) for x in sys.version_info[:3]),
          "plattform": platform.system().lower()}
    for p in PAKKER:
        try:
            ut[p] = version(p)
        except PackageNotFoundError:
            ut[p] = "mangler"
        except Exception:
            ut[p] = "ukjent"
    return ut


def avvik_mot_kjent(naa_, kjent):
    """Liste med 'pakke: kjent -> naa' for det som ikke stemmer.

    Bare felt som staar i kjent sammenlignes, saa en ny pakke i loggen gir
    ikke avvik foer den er foert inn i config/miljo_kjent.json."""
    ut = []
    for k in ["python", *PAKKER]:
        v = (kjent or {}).get(k)
        if v and naa_.get(k) and v != naa_[k]:
            ut.append(f"{k}: {v} -> {naa_[k]}")
    return ut


def les_kjent(lager, note=print):
    try:
        t = lager.les(KJENT)[0]
        return json.loads(t)["versjoner"] if t else None
    except Exception as e:
        note(f"   miljo: kunne ikke lese {KJENT} ({type(e).__name__})")
        return None


def kjor(lager, note=print, naa=None):
    try:
        naa_dt = naa or dt.datetime.now(OSLO)
        uke = so.periodenokkel(naa_dt.date())
        v = versjoner()
        gamle = so.fra_csv(lager.les(FIL)[0])
        if any(r.get("uke") == uke and r.get("plattform") == v["plattform"] for r in gamle):
            note(f"   miljo {FIL}: {uke} paa {v['plattform']} staar alt, skriver ikke")
            return
        kjent = les_kjent(lager, note)
        avvik = avvik_mot_kjent(v, kjent)
        rad = {"uke": uke, "dato": naa_dt.strftime("%Y-%m-%d %H:%M"),
               "plattform": v["plattform"], "python": v["python"],
               **{p: v[p] for p in PAKKER},
               "avvik": "; ".join(avvik)}
        so.legg_til_rader(lager, FIL, F_MILJO, [rad])
        if avvik:
            note(f"   miljo {FIL}: {uke} skrevet. AVVIK mot {KJENT}: " + "; ".join(avvik))
        else:
            note(f"   miljo {FIL}: {uke} skrevet, ingen avvik mot {KJENT}")
    except Exception as e:
        note(f"   miljo {FIL} feilet: {type(e).__name__}: {str(e)[:80]}")


if __name__ == "__main__":
    v = versjoner()
    print("installert naa:")
    for k in ["plattform", "python", *PAKKER]:
        print(f"   {k:12} {v[k]}")
    try:
        kjent = json.load(open(KJENT, encoding="utf-8"))["versjoner"]
    except Exception as e:
        print(f"\nfant ikke {KJENT} ({type(e).__name__})")
    else:
        a = avvik_mot_kjent(v, kjent)
        print("\navvik mot " + KJENT + ": " + ("; ".join(a) if a else "ingen"))
