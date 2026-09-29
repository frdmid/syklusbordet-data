# ---------------------------------------------------------------------------
# sonde_kjor_c_spleis: C foer og etter at begrepene skjoetes sammen
#
# Frodes bestilling 29.09.2026: finn oppdaterte tall for Vale og Frontline.
# Begge har byttet fra US GAAP til IFRS (Vale 2012, Frontline 2022), og C
# satt fast i de gamle begrepene. Sonden kjoerer overlevelse_c.py med
# SPLEIS=0 (gammel regel) og SPLEIS=1 (ny), uten aa publisere, og viser for
# ALLE SEC-selskaper aar, bunnaar, kontanter, verste drift, drift naa,
# kvartaler og port, foer og etter.
# ---------------------------------------------------------------------------

import json, os, subprocess, sys, tempfile

ut = {}
for navn, verdi in (("foer", "0"), ("etter", "1")):
    fil = os.path.join(tempfile.gettempdir(), f"c_spleis_{navn}.json")
    p = subprocess.run([sys.executable, "overlevelse_c.py"], capture_output=True, text=True, timeout=3000,
                       env={**os.environ, "GITHUB_TOKEN": "", "SPLEIS": verdi, "C_UT": fil})
    if p.returncode != 0 or not os.path.exists(fil):
        sys.exit(f"overlevelse_c.py feilet ({navn}):\n{p.stdout[-3000:]}\n{p.stderr[-3000:]}")
    ut[navn] = json.load(open(fil, encoding="utf-8"))["selskaper"]
    if navn == "etter":
        print("Utskrift med ny regel, del 2:\n" + p.stdout[p.stdout.find("2. Regnskapstall"):p.stdout.find("2b.")])

F, E = ut["foer"], ut["etter"]
FELT = ["aar", "bunnaar", "kontanter_musd", "verste_drift_musd", "drift_naa_musd", "kvartaler",
        "kvartaler_naa", "netto_gjeld_ek", "rentedekning", "port"]
endret = []
for tk in sorted(set(F) | set(E)):
    f, e = F.get(tk, {}), E.get(tk, {})
    if str(e.get("kilde", f.get("kilde", ""))).startswith("manuelt"):
        continue
    diff = [k for k in FELT if f.get(k) != e.get(k)]
    if not diff:
        continue
    endret.append(tk)
    print(f"\n{tk} ({e.get('navn', f.get('navn'))})")
    for k in FELT:
        print(f"   {k:18s} {str(f.get(k)):>16s} -> {e.get(k)}{'   *' if k in diff else ''}")
    for ledd in sorted(set(f.get("begreper", {})) | set(e.get("begreper", {}))):
        a, b = f.get("begreper", {}).get(ledd), e.get("begreper", {}).get(ledd)
        if a != b:
            print(f"   begrep {ledd:10s} {a} -> {b}")
print(f"\nENDRET: {', '.join(endret) or 'ingen'}")
print("PORT ENDRET: " + (", ".join(f"{t} {F.get(t, {}).get('port')} -> {E.get(t, {}).get('port')}"
                                   for t in endret if F.get(t, {}).get("port") != E.get(t, {}).get("port")) or "ingen"))
gamle = [f"{t} (siste aar {v['aar'][-1]})" for t, v in E.items() if v.get("aar") and v["aar"][-1] < 2024]
print("Fortsatt siste aar foer 2024: " + (", ".join(gamle) or "ingen"))
json.dump(ut, open("sonder/c_spleis.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
