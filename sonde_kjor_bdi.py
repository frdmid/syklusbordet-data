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
#
# Andre kjoering (25.09.2026). Foerste kjoering fant tallet i 91 % av
# rapportene, men sammenlignet ett ukestall med bdi.json sitt maanedssnitt, og
# ikke maanedssnittet av ukene slik kravet sier. BDI beveger seg for mye innad
# i en maaned til at det holder (samme funn som ved skjoetingen av bdi.json:
# 50 av 162 maaneder over 10 % som maanedsslutt). Naa leses alle rapportene,
# ukene snittes per maaned, og bare maaneder med minst to uker sammenlignes.
# Tolkingen er ogsaa strammet: rapportens eget aarstall uten $ og uten
# tusenskille tas ikke som BDI. Det slo feil i ett tilfelle (2026-08-12, der
# 2026 ble lest i stedet for 2939). Andre tall i samme stoerrelse, som BDI 2014
# i juli 2019, er ekte og beholdes.
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
TALL = re.compile(r"(\$?)(?<![\d.,])(\d{1,2}[ ,]\d{3}|\d{3,5})(?![\d])")


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


def kandidater(L, i, aar=None):
    """Tall paa linjen med etiketten og de seks neste, i rekkefoelge."""
    ut = []
    for j in range(i, min(i + 7, len(L))):
        tekst = re.sub(r"Baltic Dry Index|\(BDI\)|BDI", " ", L[j], flags=re.I)
        for m in TALL.finditer(tekst):
            raa = m.group(2)
            v = float(raa.replace(",", "").replace(" ", ""))
            aarstall = aar is not None and v == aar and not m.group(1) and not re.search(r"[ ,]", raa)
            if 150 <= v <= 25000 and not aarstall:
                ut.append((j - i, v))
    return ut


print("1. Katalog")
kat = katalog()
datoer = sorted(kat)
print(f"   {len(kat)} rapporter, {datoer[0] if datoer else '-'} til {datoer[-1] if datoer else '-'}")
utvalg = datoer
print(f"   leser alle {len(utvalg)}\n")

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
    k = kandidater(L, idx[0], int(dato[:4])) if idx else []
    rader.append({"dato": dato, "treff": len(idx), "kand": k[:6]})
    time.sleep(0.3)

print("\n3. Maanedssnitt av ukene mot bdi.json")
funnet = [r for r in rader if r.get("kand")]
print(f"   tall funnet i {len(funnet)} av {len(rader)} rapporter ({100 * len(funnet) / max(1, len(rader)):.0f} %)")
mangler = [r["dato"] for r in rader if not r.get("kand")]
print(f"   uten tall: {', '.join(mangler[:30])}{' ...' if len(mangler) > 30 else ''}")
uker = pd.Series({pd.Timestamp(r["dato"]): r["kand"][0][1] for r in funnet}).sort_index()
mnd = uker.groupby(uker.index.to_period("M")).agg(["mean", "count"])
sam = [(str(p), row["mean"], int(row["count"]), BDI.get(str(p))) for p, row in mnd.iterrows()]
sam = [x for x in sam if x[3] and x[2] >= 2]
av = [abs(x[1] / x[3] - 1) for x in sam]
naer = sum(1 for a in av if a <= 0.10)
print(f"   {len(sam)} maaneder med minst to uker og bdi.json: {naer} innenfor 10 % ({100 * naer / max(1, len(sam)):.0f} %), "
      f"median avvik {100 * float(pd.Series(av).median()) if av else float('nan'):.1f} %")
print("   stoerste avvik:")
for p, m, n, ref in sorted(sam, key=lambda x: -abs(x[1] / x[3] - 1))[:10]:
    print(f"      {p}  Fearnleys {m:7.0f} ({n} uker)  bdi.json {ref:7.0f}  {100 * (m / ref - 1):+6.1f} %")
ok1 = len(funnet) / max(1, len(rader)) >= 0.8
ok2 = naer / max(1, len(sam)) >= 0.9
print(f"\n   Krav: tall i minst 80 % ({'ja' if ok1 else 'nei'}), minst 90 % av maanedene innenfor 10 % ({'ja' if ok2 else 'nei'}). "
      f"{'OPPFYLT, Fearnleys kan forlenge bdi.json' if ok1 and ok2 else 'IKKE OPPFYLT'}")
print(f"   Siste uker: " + ", ".join(f"{d.date()}: {v:.0f}" for d, v in uker.iloc[-6:].items()))
json.dump(rader, open("sonder/bdi_fearnleys.json", "w"), indent=1, default=str)
print("\nSend hele utskriften tilbake.")
