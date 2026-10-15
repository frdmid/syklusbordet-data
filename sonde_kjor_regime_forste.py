# ---------------------------------------------------------------------------
# sonde_kjor_regime_forste: foerste regime.json for dashbordet (15.10.2026),
# slik at panelet har tall foer onsdagskjoeringen. Kjoerer samme beregning som
# kontekst_regime.py og legger resultatet i sonder/regime_forste.json.
# Engangskjoering; skriver ikke til dashbordet selv.
# ---------------------------------------------------------------------------

import json
import kontekst_regime as k

ut = k.beregn(open("serier/priser_mnd.csv", encoding="utf-8").read())
open("sonder/regime_forste.json", "w", encoding="utf-8").write(json.dumps(ut, ensure_ascii=False, indent=1) + "\n")
print(json.dumps({x: y for x, y in ut.items() if x != "serie"}, ensure_ascii=False, indent=1))
