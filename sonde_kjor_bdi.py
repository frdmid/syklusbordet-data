# ---------------------------------------------------------------------------
# sonde_kjor_bdi: kan BDI leses fra Fearnleys-rapportene vi allerede henter
#
# bdi.json er en fast kopi som slutter i september 2026. Fra oktober blir
# BDI-raten i toerrlastpanelet staaende fast. Diagnosesonden (24.09.2026) fant
# linjen "Baltic Dry Index (BDI)" i alle de seks nyeste Fearnleys-rapportene,
# men leste ikke tallet. Denne sonden finner ut hvor tallet staar, og kontrollerer
# det mot bdi.json i maanedene der begge finnes. Den endrer ingenting.
#
# Krav for aa ta den i bruk (satt foer kjoering): minst 80 % av rapportene gir
# et tall, og maanedssnittet ligger innenfor 10 % av bdi.json i minst 90 % av
# de overlappende maanedene. Samme grenser som ved skjoetingen av bdi.json.
# ---------------------------------------------------------------------------

import io, json, re, time
import pandas as pd
import requests, pdfplumber
import logging
logging.getLogger("pdfminer").setLevel(logging.ERROR)

HSN = "https://www.hellenicshippingnews.com"
RAW = "https://raw.githubusercontent.com/frdmid/syklusbordet-data/main"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
TALL = re.compile(r"(?<![\d.,])(\d{1,2}[ ,]?\d{3}|\d{3,5})(?![\d])")


def katalog():
    ut = {}
    for side in range(1, 40):
        r = requests.get(f"{HSN}/wp-json/wp/v2/media?search=Fearnleys&per_page=100"
                         f"&page={side}&_fields=date,source_url", headers=UA, timeout=60)
        if r.status_code != 200:
            break
        d = r.json()
        if not d:
            break
        for m in d:
            u = m.get("source_url", "")
            if u.lower().endswith(".pdf"):
                ut[m.get("date", "")[:10]] = u
        if len(d) < 100:
            break
        time.sleep(0.3)
    return ut


def kandidater(L, i):
    """Tall paa linjen med etiketten og de seks neste, i rekkefoelge."""
    ut = []
    for j in range(i, min(i + 7, len(L))):
        tekst = re.sub(r"Baltic Dry Index|\(BDI\)|BDI", " ", L[j], flags=re.I)
        for m in TALL.finditer(tekst):
            v = float(m.group(1).replace(",", "").replace(" ", ""))
            if 150 <= v <= 25000:
                ut.append((j - i, v))
    return ut


print("1. Katalog")
kat = katalog()
datoer = sorted(kat)
print(f"   {len(kat)} rapporter, {datoer[0] if datoer else '-'} til {datoer[-1] if datoer else '-'}")
utvalg = sorted(set(datoer[-8:] + datoer[:-8][::6]))
print(f"   sjekker {len(utvalg)}: de 8 nyeste og hver sjette eldre\n")

b = requests.get(f"{RAW}/bdi.json?cb={int(time.time())}", timeout=30).json()
BDI = dict(zip(b["t"], b["nom"]))

print("2. Hvor tallet staar (de tre nyeste, linjene rundt etiketten)")
rader = []
for n, dato in enumerate(reversed(utvalg)):
    try:
        raw = requests.get(kat[dato], headers=UA, timeout=120).content
        with pdfplumber.open(io.BytesIO(raw)) as pdf:
            txt = "\n".join((s.extract_text() or "") for s in pdf.pages)
    except Exception as e:
        rader.append({"dato": dato, "feil": f"{type(e).__name__}"}); continue
    L = [x.strip() for x in txt.split("\n") if x.strip()]
    idx = [i for i, l in enumerate(L) if re.search(r"Baltic Dry Index|\bBDI\b", l, re.I)]
    if n < 3:
        print(f"\n   {dato}: {len(idx)} treff")
        for i in idx[:2]:
            for j in range(max(0, i - 2), min(len(L), i + 7)):
                print(f"      {'>' if j == i else ' '} {L[j][:110]}")
    k = kandidater(L, idx[0]) if idx else []
    rader.append({"dato": dato, "treff": len(idx), "kand": k[:6]})
    time.sleep(0.3)

print("\n3. Foerste tall etter etiketten mot bdi.json samme maaned")
print(f"   {'dato':10} {'foerste':>8} {'bdi.json':>9} {'forhold':>8}   kandidater (linje etter etiketten, tall)")
ok, naer, n_over = 0, 0, 0
for r in sorted(rader, key=lambda x: x["dato"]):
    if "feil" in r:
        print(f"   {r['dato']:10} feil: {r['feil']}"); continue
    f = r["kand"][0][1] if r["kand"] else None
    ref = BDI.get(r["dato"][:7])
    forh = f / ref if f and ref else None
    ok += f is not None
    if forh is not None:
        n_over += 1; naer += abs(forh - 1) <= 0.10
    print(f"   {r['dato']:10} {f if f else '-':>8} {ref if ref else '-':>9} "
          f"{('-' if forh is None else f'{forh:.3f}'):>8}   {r['kand']}")
print(f"\n   tall funnet i {ok} av {len(rader)} rapporter ({100 * ok / max(1, len(rader)):.0f} %)")
print(f"   innenfor 10 % av bdi.json: {naer} av {n_over} maaneder med begge "
      f"({100 * naer / max(1, n_over):.0f} %)")
print("   Merk: bdi.json er maanedssnitt, Fearnleys er ett tall per uke. Noe avvik er ventet.")
print(f"\n   Krav: minst 80 % tall og minst 90 % innenfor 10 %. "
      f"{'OPPFYLT' if ok / max(1, len(rader)) >= 0.8 and naer / max(1, n_over) >= 0.9 else 'IKKE OPPFYLT'} "
      "med foerste tall etter etiketten. Er det ikke oppfylt, viser linjene over hvor tallet faktisk staar.")
json.dump(rader, open("sonder/bdi_fearnleys.json", "w"), indent=1, default=str)
print("\nSend hele utskriften tilbake.")
