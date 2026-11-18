# ---------------------------------------------------------------------------
# dashbord/kontroller: sjekker dashbord/index.html FOER publisering
# (Frodes bestilling 12.11.2026, steg 3 i notater/2026-11-11_gjennomgang.md).
#
#   py -X utf8 dashbord/kontroller.py
#
# Coworks versjon 54 mistet <title> og :root og ble fargelos i lys modus, og
# vertens omslag kom med to ganger. Kontrollene under fanger begge, og i
# tillegg at lastelogikken og sperren mot IAI-data staar.
#
# Avslutter med kode 1 hvis noe feiler, saa den kan brukes som port.
# ---------------------------------------------------------------------------

import os
import sys

ROT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIL = os.path.join(ROT, "dashbord", "index.html")
GRENSE = 16 * 1024 * 1024          # artifactens grense


def kontroller(t, storrelse):
    """Returnerer (feil, advarsler) som lister med tekst."""
    feil, adv = [], []

    if not t.startswith("<title>Syklusbordet</title>"):
        feil.append("filen begynner ikke med <title>Syklusbordet</title>. Vertens omslag "
                    "skal vaere fjernet, og tittelen staa foerst.")
    if "--ground:#f4f4f1" not in t[:4000]:
        feil.append(":root med --ground:#f4f4f1 staar ikke oeverst. Uten den blir lys "
                    "modus fargelos (det skjedde i versjon 54).")
    if "<!doctype" in t.lower():
        feil.append("filen inneholder <!doctype>. Verten legger paa omslaget selv, saa "
                    "da kommer det to ganger.")
    if storrelse > GRENSE:
        feil.append(f"filen er {storrelse} byte, over grensen {GRENSE}.")

    # lastelogikken. Siden leser databasen, som onsdagsrutinen fyller, med de
    # innbakte dataene som siste utvei. Forsoeket paa aa lese
    # dashbord/data.json fra repoet (12.11 til 18.11.2026) er tatt ut: begge
    # veier ble stanset av sandkassens CSP i den publiserte siden. Koden ligger
    # i commit ff22032.
    if 'id="datakilde"' not in t:
        feil.append('feltet id="datakilde" mangler: siden kan ikke vise hvilken kilde '
                    "som ble brukt.")
    if t.count("LASTER_VERSJON") < 3:
        feil.append("LASTER_VERSJON brukes ikke: linjen over Datahelse sier ikke hvilken "
                    "lastelogikk som kjoerer, og en gammel side i cache avsloerer seg "
                    "ikke selv.")
    if 'x.id !== "alu_tilbud"' not in t or "alu_tilbud" not in t:
        feil.append("haandteringen av alu_tilbud mangler: IAI-tallene skal alltid komme "
                    "fra databasen.")
    # Henter siden fra et eksternt nettsted igjen, er det enten en bevisst
    # endring etter en ny maaling, eller en gammel vane som kom tilbake. Den
    # skal ikke stoppe publiseringen, men den skal sees.
    if "fetch(" in t:
        adv.append("filen henter fra nettet (fetch). Sandkassen stanset baade "
                   "raw.githubusercontent og jsDelivr 18.11.2026. Maal i den "
                   "PUBLISERTE siden foer du stoler paa det, og send aldri headere: "
                   "de utloeser CORS-preflight.")
    # reserven
    for navn in ("const SEED", "ENDR_SEED", "HELSE_SEED"):
        if navn not in t:
            feil.append(f"{navn} mangler: siden har ingen siste utvei naar verken repoet "
                        "eller databasen svarer.")
    if "window.claude?.use?.(\"db\")" not in t:
        feil.append("databasen leses ikke lenger: reserven er borte.")

    # mindre ting
    #
    # Em dash er tankestrek og skal ikke finnes. En dash (U+2013) staar med vilje
    # i fmt() som plassholder for et tall som mangler, saa den telles ikke.
    # Begge tegnene staar som kode og ikke som tegn, slik at denne fila selv
    # ikke faller for sin egen kontroll.
    if chr(0x2014) in t:          # em dash som kode, saa fila selv er ren
        adv.append("filen inneholder tankestrek (em dash); prosjektet skriver uten.")
    # <title> finnes ogsaa inne i <svg> for tilgjengelighet. Bare dokumenttittelen
    # skal vaere unik.
    if t.count("<title>Syklusbordet</title>") != 1:
        adv.append(f"{t.count('<title>Syklusbordet</title>')} forekomster av "
                   "<title>Syklusbordet</title>, ventet 1.")
    return feil, adv


def main():
    if not os.path.exists(FIL):
        print(f"FEIL: fant ikke {FIL}")
        return 1
    t = open(FIL, encoding="utf-8").read()
    feil, adv = kontroller(t, os.path.getsize(FIL))
    print(f"Kontrollerer {os.path.relpath(FIL, ROT)} ({os.path.getsize(FIL)} byte, {len(t)} tegn)\n")
    for a in adv:
        print(f"  advarsel: {a}")
    for f in feil:
        print(f"  FEIL: {f}")
    if feil:
        print(f"\n{len(feil)} feil. Publiser IKKE.")
        return 1
    print(f"\nAlt i orden{', ' + str(len(adv)) + ' advarsel(er)' if adv else ''}. "
          "Filen kan publiseres som den er, uten omslag.")
    print("\nHUSK: kilden er dashbord/index.html i repoet, ikke artifacten.")
    print("Publiserer du fra den gamle artifacten, overskrives arbeidet i mappen.")
    print("Kjoerte du `git pull` foer du endret?")
    return 0


if __name__ == "__main__":
    sys.exit(main())
