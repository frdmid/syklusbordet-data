# ---------------------------------------------------------------------------
# sonde_kjor_b_haleregel: tilbudsskaaren B foer og etter haleregelen
#
# Frodes beslutning 29.09.2026 (bestilt fra Cowork-oekten): det siste aaret i
# B-serien telles foerst naar minst tre fjerdedeler av kurvens selskaper har
# tall. Denne sonden kjoerer tilbud_b.py to ganger, med og uten regelen
# (HALEREGEL=1 og 0), uten aa publisere noe (GITHUB_TOKEN tomt), og viser
# forskjellen per metall i siste aar, forhold, B1 og B2. Alle andre tall skal
# vaere like, og det kontrolleres.
# ---------------------------------------------------------------------------

import json, os, subprocess, sys, tempfile

ut = {}
for navn, verdi in (("foer", "0"), ("etter", "1")):
    fil = os.path.join(tempfile.gettempdir(), f"b_{navn}.json")
    env = {**os.environ, "GITHUB_TOKEN": "", "HALEREGEL": verdi, "B_UT": fil}
    p = subprocess.run([sys.executable, "tilbud_b.py"], env=env, capture_output=True, text=True, timeout=3000)
    if p.returncode != 0 or not os.path.exists(fil):
        print(f"tilbud_b.py feilet ({navn}):\n{p.stdout[-3000:]}\n{p.stderr[-3000:]}")
        sys.exit(1)
    ut[navn] = json.load(open(fil, encoding="utf-8"))
    if navn == "etter":
        print("Utskrift fra tilbud_b.py med regelen, del 2b og 3:\n")
        t = p.stdout
        print(t[t.find("2b. Manuelt"):t.find("4. Sprott")])

F, E = ut["foer"], ut["etter"]
print("\nKUTT PER METALL")
for m in sorted(set(F["kutt"]) | set(E["kutt"])):
    k = E["kutt"].get(m, {})
    print(f"   {m:10s} halvregel {k.get('halvregel')}  haleregel {k.get('haleregel')}  "
          f"(krav {k.get('krav_hale')} selskaper; per aar siste fem: "
          f"{dict(list(k.get('selskaper_per_aar', {}).items())[-5:])})")

print("\nFORSKJELL I SISTE AAR")
print(f"   {'metall':10s} {'siste aar':>14s} {'forhold':>16s} {'B1':>14s} {'B2':>14s}")
avvik = []
for m in sorted(set(F["metaller"]) | set(E["metaller"])):
    f, e = F["metaller"].get(m), E["metaller"].get(m)
    if not f or not e:
        print(f"   {m:10s} finnes bare {'foer' if f else 'etter'}"); continue
    rad = lambda k: f"{f[k]} -> {e[k]}" if f[k] != e[k] else f"{e[k]}"
    print(f"   {m:10s} {str(f['aar'][-1]) + ' -> ' + str(e['aar'][-1]) if f['aar'][-1] != e['aar'][-1] else str(e['aar'][-1]):>14s} "
          f"{rad('ratio_siste'):>16s} {rad('B1_siste'):>14s} {rad('B2_siste'):>14s}")
    # Kontroll: aarene som er med i begge skal ha identiske tall
    n = len(e["aar"])
    for k in ("aar", "ratio", "B1", "B2"):
        if f[k][:n] != e[k]:
            avvik.append(f"{m}/{k}")
print("\nKONTROLL: " + ("alle aar som staar igjen har samme forhold, B1 og B2 som foer"
                       if not avvik else "AVVIK utover de kuttede aarene: " + ", ".join(avvik)))
json.dump({"foer": F, "etter": E, "avvik": avvik}, open("sonder/b_haleregel.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("\nlagret sonder/b_haleregel.json")
