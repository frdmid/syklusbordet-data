# ---------------------------------------------------------------------------
# sonde_kjor_c_rente: overlevelsesporten C foer og etter rentefiksen
#
# Frodes beslutning 29.09.2026, etter den uavhengige gjennomgangen: C trakk
# renter fra driftskontantstroemmen ogsaa for US GAAP-filere, der renten
# allerede er trukket. Denne sonden kjoerer overlevelse_c.py to ganger,
# RENTEFIX=0 (gammel regel) og RENTEFIX=1 (ny), uten aa publisere noe
# (GITHUB_TOKEN tomt), og viser port, kvartaler, kvartaler naa og
# rentedekning per selskap, foer og etter.
# ---------------------------------------------------------------------------

import json, os, subprocess, sys, tempfile

ut = {}
for navn, verdi in (("foer", "0"), ("etter", "1")):
    fil = os.path.join(tempfile.gettempdir(), f"c_{navn}.json")
    env = {**os.environ, "GITHUB_TOKEN": "", "RENTEFIX": verdi, "C_UT": fil}
    p = subprocess.run([sys.executable, "overlevelse_c.py"], env=env, capture_output=True, text=True, timeout=3000)
    if p.returncode != 0 or not os.path.exists(fil):
        print(f"overlevelse_c.py feilet ({navn}):\n{p.stdout[-3000:]}\n{p.stderr[-3000:]}")
        sys.exit(1)
    ut[navn] = json.load(open(fil, encoding="utf-8"))["selskaper"]

F, E = ut["foer"], ut["etter"]
print(f"{'papir':10s} {'grunn':26s} {'port':>17s} {'kvartaler':>15s} {'kv naa':>15s} {'dekning':>13s}  rente musd")
endret = []
for tk in sorted(set(F) | set(E)):
    f, e = F.get(tk, {}), E.get(tk, {})
    fx = lambda k: f"{f.get(k)} -> {e.get(k)}" if f.get(k) != e.get(k) else f"{e.get(k)}"
    print(f"{tk:10s} {str(e.get('rentegrunn', e.get('kilde', 'manuell')))[:26]:26s} {fx('port'):>17s} "
          f"{fx('kvartaler'):>15s} {fx('kvartaler_naa'):>15s} {fx('rentedekning'):>13s}  "
          f"{e.get('rente_musd', e.get('rente_m'))}")
    if f.get("port") != e.get("port"):
        endret.append(f"{tk} {f.get('port')} -> {e.get('port')}")
print("\nPORT ENDRET: " + (", ".join(endret) if endret else "ingen"))
print("Manuelt leste selskaper (c_manuell) regnes likt foer og etter; fiksen gjelder bare SEC-tallene.")
json.dump(ut, open("sonder/c_rente.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("lagret sonder/c_rente.json")
