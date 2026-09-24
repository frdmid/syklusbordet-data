# ---------------------------------------------------------------------------
# Fast oppstarter for sondene. Denne filen endres aldri.
#
# Arbeidsflytfiler er beskyttet mot fjernskriving, saa hver gang en ny sonde
# trengte et eget steg maatte Frode legge inn en ny yml manuelt. Losningen var
# et fritt steg som kjorer sonde_ad_hoc.py. Men da ble ALLE sonder hetende det
# samme, og utskriften havnet alltid i sonder/ad_hoc.txt.
#
# Det gikk galt to ganger 24. september: gammel utskrift laa igjen under samme
# navn, saa den saa ut som et ferskt svar. Forste gang tolket jeg sonde 1 sine
# tall som sonde 2 sine. Andre gang leste jeg sonde 3 som om den var sonde 4.
#
# Derfor denne: oppstarteren finner alle filer som heter sonde_kjor_*.py,
# kjorer hver av dem i egen prosess, og legger utskriften i sonder/<navn>.txt
# med navn, tidspunkt og commit oeverst. Da kan gammel utskrift aldri leses som
# ny, og en ny sonde krever bare en ny fil.
#
# Slik legges en sonde til:  skriv sonde_kjor_<hva_den_maaler>.py
# Slik leses svaret:         sonder/sonde_kjor_<hva_den_maaler>.txt
# ---------------------------------------------------------------------------

import glob, os, subprocess, sys, time

SONDER = sorted(glob.glob("sonde_kjor_*.py"))
os.makedirs("sonder", exist_ok=True)

if not SONDER:
    print("Ingen filer som heter sonde_kjor_*.py i repoet. Ingenting aa kjore.")
    print("En sonde legges til ved aa skrive en slik fil. Arbeidsflyten")
    print("trenger ingen endring.")
    sys.exit(0)

try:
    sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                         capture_output=True, text=True, timeout=20).stdout.strip() or "ukjent"
except Exception:
    sha = "ukjent"

print(f"Oppstarter: {len(SONDER)} sonde(r) funnet\n")
resultat = []
for sti in SONDER:
    navn = os.path.splitext(os.path.basename(sti))[0]
    ut = f"sonder/{navn}.txt"
    start = time.time()
    print(f"=== {navn} ===", flush=True)
    try:
        p = subprocess.run([sys.executable, sti], capture_output=True, text=True, timeout=3600)
        tekst = (p.stdout or "") + (("\n[stderr]\n" + p.stderr) if p.stderr.strip() else "")
        kode = p.returncode
    except subprocess.TimeoutExpired:
        tekst, kode = "AVBRUTT: sonden brukte mer enn en time.", 124
    except Exception as e:
        tekst, kode = f"AVBRUTT: {type(e).__name__}: {e}", 1
    brukt = time.time() - start

    # Hodet er det som gjor at gammel utskrift ikke kan leses som ny.
    hode = (f"sonde:   {navn}\n"
            f"kjort:   {time.strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
            f"commit:  {sha}\n"
            f"status:  {'OK' if kode == 0 else f'FEIL, avslutningskode {kode}'}\n"
            f"brukte:  {brukt:.0f} sekunder\n"
            + "-" * 62 + "\n")
    with open(ut, "w", encoding="utf-8") as f:
        f.write(hode + tekst)
    print(tekst)
    print(f"--- skrevet til {ut} ({brukt:.0f} s, kode {kode})\n", flush=True)
    resultat.append((navn, kode, brukt))

print("\nOPPSUMMERING")
for navn, kode, brukt in resultat:
    print(f"   {'OK  ' if kode == 0 else 'FEIL'}  {navn:40} {brukt:5.0f} s  -> sonder/{navn}.txt")
