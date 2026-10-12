# ---------------------------------------------------------------------------
# repo_les: les en fil fra dette repoet slik at det virker baade naar repoet er
# offentlig og naar det er privat (forberedt 12.10.2026, Frodes bestilling;
# ligger paa grenen forbered-privat-repo til repoet eventuelt gjoeres privat).
#
# Foerst GitHub-API-et (contents, raa tekst) med GITHUB_TOKEN naar den finnes:
# ferskt (ingen mellomlagring) og virker for private repoer. Faller tilbake til
# raw.githubusercontent med cache-brekk, som i dag, og sender da nøkkelen med
# hvis den finnes (raw godtar den for private repoer).
# For et offentlig repo gir begge veiene samme innhold, saa tallene endres ikke.
# ---------------------------------------------------------------------------

import os, time
import requests

REPO, BRANCH = "frdmid/syklusbordet-data", "main"
_UA = {"User-Agent": "Syklusbordet"}


class Svar:
    """Minimal etterligning av requests.Response for kallstedene."""
    def __init__(self, status_code, text):
        self.status_code, self.text = status_code, text

    def json(self):
        import json
        return json.loads(self.text)

    def raise_for_status(self):
        if self.status_code != 200:
            raise requests.HTTPError(f"{self.status_code} for repofil")


def hent(sti, timeout=30):
    """Returnerer Svar med status_code og text for fila `sti` i repoet."""
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        try:
            r = requests.get(f"https://api.github.com/repos/{REPO}/contents/{sti}", params={"ref": BRANCH},
                             headers={**_UA, "Authorization": f"Bearer {token}",
                                      "Accept": "application/vnd.github.raw"}, timeout=timeout)
            if r.status_code in (200, 404):
                return Svar(r.status_code, r.content.decode("utf-8"))
        except requests.RequestException:
            pass
    h = dict(_UA, **({"Authorization": f"token {token}"} if token else {}))
    r = requests.get(f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/{sti}", params={"cb": int(time.time())},
                     headers=h, timeout=timeout)
    return Svar(r.status_code, r.content.decode("utf-8") if r.status_code == 200 else r.text)


def tekst(sti, timeout=30):
    """Teksten i fila, eller unntak hvis den ikke kan leses."""
    s = hent(sti, timeout)
    s.raise_for_status()
    return s.text
