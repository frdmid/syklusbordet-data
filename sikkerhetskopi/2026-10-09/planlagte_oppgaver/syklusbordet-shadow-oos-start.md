---
name: syklusbordet-shadow-oos-start
description: Starter arbeidet med Shadow-OOS-oppsettet for Syklusbordet (fase 1) i repoet syklusbordet-data.
---

Du er Claude Code og skal jobbe med prosjektet Syklusbordet for Frode. Skriv alt på norsk, og bruk aldri tankestrek i tekst.

## Oppsett
- Repo: `C:\Users\FrodeMidjo\kode\syklusbordet-data` (klone av https://github.com/frdmid/syklusbordet-data). Jobb bare der, aldri i OneDrive-mappa `syklusbordet-data_GAMMEL_ikke_bruk`.
- Git ligger ikke i PATH. Bruk `C:\Users\FrodeMidjo\AppData\Local\GitHubDesktop\app-3.6.6\resources\app\git\cmd\git.exe` (finnes den ikke, se etter nyere `app-*`-mappe). Innlogging for push er satt opp.
- Start med `git pull origin main`.
- Les `CLAUDE.md`, deretter `notater/LOGG.md` (nyeste øverst) og `notater/OVERLEVERING.md`, og følg reglene der. Det betyr blant annet: Claude Code endrer ikke `c_manuell.*`, `b_manuell.*`, `CLAUDE.md` eller `.github/workflows/`. Nye steg i ukekjøringen kalles sist i et eksisterende skript (slik `helse.py` kalles fra `bygg_shipping.py`). Klokkeslett i loggen hentes fra systemet i norsk tid, og loggen føres i samme commit som endringen.

## Oppgaven
Frode vil bygge Shadow-OOS for Syklusbordet etter dokumentet
`C:\Users\FrodeMidjo\OneDrive - HK Reklamebyrå\Skrivebord\Shadow-OOS_oppsett_for_Syklusdashboard_MD-kode.docx`.
Les hele dokumentet. Teksten kan hentes ved å åpne docx-fila som zip og lese `word/document.xml`. Hovedregelen er at Champion fryses, og at shadow-dataene bare legges til (append-only). Fortiden regenereres aldri.

Gjør dette i rekkefølge:
1. **Kartlegg** hvordan dagens kode faktisk regner A, Ad, B, C, D, S, bunnsone, d95, trend, COT og kurve (`priser.py`, `kapitulasjon_d.py`, `tilbud_b.py`, `rigg_b.py`, `overlevelse_c.py`, `flagglogg.py`, `index.json`, `segments/`). Se også hva `flagglogg.py` allerede logger (episoder, 12-månedersregelen, `logg/hypotese_3mnd.csv`, `logg/regel_6040.csv`, `logg/dom.csv`), så du bygger videre på det som finnes og ikke lager en ny versjon av det samme.
2. **Skriv en plan** som notat, `notater/shadow_oos_plan.md`: hvordan dokumentets minimumsversjon (punkt 50 og fase 1 i punkt 51) passer inn i dette repoet. Hvilke filer og formater (repoet bruker JSON/CSV i git, ingen database), hvor i ukekjøringen snapshotet skrives, og hvordan append-only håndheves og testes (punkt 46). Ta med en liste over spørsmål som Frode må avgjøre.
3. **Bygg fase 1**, så langt det kan gjøres uten Frodes avgjørelser: `config/champion_v1_0.yaml` (eller JSON), modellregister, ukentlig `shadow_snapshot` per segment og instrument, `shadow_events`, `correction_log` og tom `shadow_outcomes`. Frys Champion-reglene slik koden er nå, med `code_commit` og `specification_hash`. Første ordinære ukekjøring etter 30.09.2026 er onsdag 07.10.2026 (`ukentlig.yml`, kl. 06:00 UTC). Den må skrive det første snapshotet, så alt må ligge på main før det. Dokumentet bruker 05.10 som eksempel. Bruk 07.10 og skriv det i notatet.
4. **Test lokalt** før push: kjør snapshotet mot dagens data, sjekk at en ny kjøring ikke endrer gamle rader, og at ukekjøringen ikke brytes.
5. **Push** til main, med logginnslag i samme commit. Ta nye forsøk ved nettverksfeil (vent 2, 4, 8 og 16 s). Oppdater `notater/OVERLEVERING.md` med de nye filene.

Dashbordet (artifact) skal IKKE endres i denne kjøringen. LIVE OOS-siden kommer senere, etter avtale med Frode.

Er noe uklart på en måte som påvirker hva som fryses, ta det mest konservative valget, skriv det i planen som et åpent spørsmål, og ikke gjett. Avslutt med et kort sammendrag til Frode: hva som er bygget, hva som er testet, hva som er pushet, og hvilke spørsmål han må avgjøre før 07.10.