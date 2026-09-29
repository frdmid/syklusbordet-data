# ---------------------------------------------------------------------------
# sonde_kjor_b_dda: tilbudsskaaren B foer og etter at nedskrivninger ble tatt
# ut av nevneren
#
# Frodes beslutning 29.09.2026, etter den uavhengige gjennomgangen. Begrepet
# "avskrivninger og nedskrivninger" sto som nummer to i DDA_RANG og vant over
# de rene avskrivningsbegrepene for IFRS-filere. Sonden kjoerer tilbud_b.py to
# ganger, B_DDA=gammel og ny rekkefoelge, uten aa publisere (GITHUB_TOKEN
# tomt), og viser (1) hvilke selskaper som fikk ny nevner og (2) siste aar,
# forhold, B1 og B2 per metall, foer og etter.
# ---------------------------------------------------------------------------

import json, os, subprocess, sys, tempfile

ut = {}
for navn, verdi in (("foer", "gammel"), ("etter", "ny")):
    fil = os.path.join(tempfile.gettempdir(), f"bdda_{navn}.json")
    env = {**os.environ, "GITHUB_TOKEN": "", "B_DDA": verdi, "B_UT": fil}
    p = subprocess.run([sys.executable, "tilbud_b.py"], env=env, capture_output=True, text=True, timeout=3000)
    if p.returncode != 0 or not os.path.exists(fil):
        print(f"tilbud_b.py feilet ({navn}):\n{p.stdout[-3000:]}\n{p.stderr[-3000:]}")
        sys.exit(1)
    ut[navn] = json.load(open(fil, encoding="utf-8"))

F, E = ut["foer"], ut["etter"]
print("1. SELSKAPER MED NY NEVNER")
n = 0
for tk in sorted(set(F["begreper"]) | set(E["begreper"])):
    f, e = F["begreper"].get(tk, {}), E["begreper"].get(tk, {})
    if f.get("nevner") == e.get("nevner") and f.get("teller") == e.get("teller"):
        continue
    n += 1
    print(f"   {tk:6s} ({e.get('metall', f.get('metall'))})")
    print(f"      foer:  {str(f.get('teller')).split(':')[-1][:40]} / {str(f.get('nevner')).split(':')[-1][:70]}")
    print(f"      etter: {str(e.get('teller')).split(':')[-1][:40]} / {str(e.get('nevner')).split(':')[-1][:70]}")
    aar = sorted(set(f.get("ratio", {})) | set(e.get("ratio", {})))[-8:]
    print("      forhold per aar: " + "  ".join(
        f"{a}: {f.get('ratio', {}).get(str(a), f.get('ratio', {}).get(a))} -> {e.get('ratio', {}).get(str(a), e.get('ratio', {}).get(a))}"
        for a in aar))
print(f"   {n} selskaper endret" if n else "   ingen selskaper endret")

print("\n2. PER METALL, SISTE AAR")
print(f"   {'metall':10s} {'siste aar':>14s} {'forhold':>16s} {'B1':>14s} {'B2':>14s}")
for m in sorted(set(F["metaller"]) | set(E["metaller"])):
    f, e = F["metaller"].get(m), E["metaller"].get(m)
    if not f or not e:
        print(f"   {m:10s} finnes bare {'foer' if f else 'etter'}"); continue
    rad = lambda k: f"{f[k]} -> {e[k]}" if f[k] != e[k] else f"{e[k]}"
    sa = f"{f['aar'][-1]} -> {e['aar'][-1]}" if f['aar'][-1] != e['aar'][-1] else str(e['aar'][-1])
    print(f"   {m:10s} {sa:>14s} {rad('ratio_siste'):>16s} {rad('B1_siste'):>14s} {rad('B2_siste'):>14s}")
json.dump(ut, open("sonder/b_dda.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("\nlagret sonder/b_dda.json")
