# ---------------------------------------------------------------------------
# sonde_kjor_uran: instrumenter for det nye uransegmentet, og en levende kilde
#
# Del 1. Hvilke papirer i IKZ-universet folger uran.
#   Tolv kandidater ble hentet i IKZ-sonden 22. september, men aldri maalt,
#   fordi det ikke fantes noen uranpris aa maale dem mot (FRED svarte ikke,
#   og kopien i repoet kom foerst 24. september). Naa finnes den. Sonden
#   kjorer sonde_ikz.py med IKZ_KUN=uran: samme maaling, samme krav og samme
#   faste vindu fra 2016 som for de andre segmentene, men bare mot uran og mot
#   hele kandidatuniverset. Resultatet skrives til sonder/ikz_uran.json, og
#   den fulle kjoringen i sonde_ikz.json roeres ikke.
#
#   Uten et maalt papir faar ikke segmentet noen instrumentliste, og da
#   hopper den planlagte kopieringen til dashbordet over det. Det er en sperre
#   med hensikt, saa denne sonden er det som slipper uran inn paa bordet.
#
# Del 2. Cameco som kilde. Runde 1 viste at IMF-serien i uran_reserve.csv
#   ligger rundt 19 % under markedet fra oktober 2021, og at Cameco svarer
#   med maanedsslutt spot fra 1988. Del 1 maaler naa mot Cameco-serien, og
#   del 2 viser aar for aar hvor godt den stemmer med IMF og futures.
# ---------------------------------------------------------------------------

import io, json, os, re, subprocess, sys, time
import pandas as pd
import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}

# ================================================================ del 1
print("DEL 1. IKZ-maaling mot uran\n", flush=True)
t0 = time.time()
p = subprocess.run([sys.executable, "sonde_ikz.py"], env=dict(os.environ, IKZ_KUN="uran"),
                   capture_output=True, text=True, timeout=3000)
print(p.stdout[-60000:])
if p.stderr.strip():
    print("[stderr]\n" + p.stderr[-4000:])
print(f"\n(del 1 brukte {time.time() - t0:.0f} s, kode {p.returncode})\n", flush=True)


# ================================================================ del 2
# Runde 1 (24.09) fant at Cameco svarer med maanedsslutt spot fra 1988, og at
# IMF-kopien har et brudd fra oktober 2021. Her sammenlignes Cameco aar for aar
# mot IMF (foer bruddet) og mot futures (etter), og serien lagres i sonder/
# slik at den kan leses uten ny kjoring.
print("\nDEL 2. Cameco mot IMF og futures, aar for aar\n")
from uran_kilde import cameco_spot, maaned, kontroll
RAW = "https://raw.githubusercontent.com/frdmid/syklusbordet-data/main/"
try:
    s = cameco_spot()
    imf = maaned(RAW + "uran_reserve.csv")
    fut = maaned(RAW + "uran_futures_uke.csv", snitt=True)
    ok, tekst = kontroll(s, imf, fut)
    print(f"   Cameco: {len(s)} mnd, {s.index[0]} til {s.index[-1]}, siste {s.iloc[-1]:.2f}")
    print(f"   Kontrollen: {'BESTAATT' if ok else 'IKKE BESTAATT'}. {tekst}\n")
    print("   aar    Cameco   IMF    futures   Cam/IMF-1   Cam/fut-1")
    for aar in range(1988, 2027):
        c = s[[p for p in s.index if p.year == aar]]
        if c.empty:
            continue
        i = imf.reindex(c.index).dropna(); f = fut.reindex(c.index).dropna()
        ci = ((c.reindex(i.index) / i - 1) * 100).median() if len(i) else None
        cf = ((c.reindex(f.index) / f - 1) * 100).median() if len(f) else None
        print(f"   {aar}  {c.mean():7.2f}  {i.mean() if len(i) else float('nan'):7.2f}  "
              f"{f.mean() if len(f) else float('nan'):7.2f}   "
              f"{'' if ci is None else f'{ci:+6.1f} %':>9}   {'' if cf is None else f'{cf:+6.1f} %':>9}")
    os.makedirs("sonder", exist_ok=True)
    with open("sonder/uran_cameco.csv", "w") as fh:
        fh.write("dato,spot\n" + "\n".join(f"{p}-01,{v}" for p, v in s.items()) + "\n")
    print("\n   lagret sonder/uran_cameco.csv")
except Exception as e:
    print(f"   FEIL {type(e).__name__}: {str(e)[:120]}")

print("\nSend hele utskriften tilbake.")
