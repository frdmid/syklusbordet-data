# ---------------------------------------------------------------------------
# vakt_ukentlig: avgjoer om en planlagt ukekjoering skal gaa (21.10.2026,
# Frodes bestilling etter at GitHub hoppet over kjoeringen 21.10).
#
# ukentlig.yml har to planlagte tider onsdag: hovedkjoering 08:48 og
# reservekjoering 09:56 norsk tid. Reserven skal bare gjoere noe hvis
# hovedkjoeringen ikke kom. Regelen:
#   - startet for haand (workflow_dispatch): kjoer alltid
#   - planlagt: kjoer bare hvis index.json IKKE allerede er skrevet i dag
#     (norsk dato). Da blir det aldri to kjoeringer av Shadow-OOS samme dag.
# Skriver kjor=true eller kjor=false til GITHUB_OUTPUT, og en linje til loggen.
# Feiler lesingen av index.json, kjoeres det (bedre en kjoering for mye enn
# en uke uten tall; Shadow-OOS skriver uansett bare en gang per uke).
# ---------------------------------------------------------------------------

import datetime as dt
import json
import os
from zoneinfo import ZoneInfo

OSLO = ZoneInfo("Europe/Oslo")


def avgjor(hendelse, oppdatert_utc, naa_utc):
    """oppdatert_utc: 'YYYY-MM-DD HH:MM:SS' fra index.json (UTC), eller None."""
    if hendelse != "schedule":
        return True, "startet for haand"
    if not oppdatert_utc:
        return True, "fant ikke index.json"
    t = dt.datetime.fromisoformat(oppdatert_utc).replace(tzinfo=dt.timezone.utc).astimezone(OSLO)
    idag = naa_utc.astimezone(OSLO).date()
    if t.date() == idag:
        return False, f"index.json er allerede skrevet i dag kl. {t:%H:%M} norsk tid"
    return True, f"index.json er fra {t:%d.%m.%Y %H:%M} norsk tid"


if __name__ == "__main__":
    try:
        oppd = json.load(open("index.json", encoding="utf-8")).get("oppdatert")
    except Exception:
        oppd = None
    kjor, grunn = avgjor(os.environ.get("GITHUB_EVENT_NAME", ""), oppd, dt.datetime.now(dt.timezone.utc))
    print(f"vakt: {'kjoerer' if kjor else 'hopper over'} ({grunn})")
    ut = os.environ.get("GITHUB_OUTPUT")
    if ut:
        with open(ut, "a", encoding="utf-8") as f:
            f.write(f"kjor={'true' if kjor else 'false'}\n")
