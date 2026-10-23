---
name: syklusbordet-sjekk-2810
description: Kontrollerer hovedkjøring 08:48, reserve 09:56 og rutinen 10:15 og 13:15 onsdag 28.10.2026.
---

Kontroller ukekjøringen for Syklusbordet onsdag 28.10.2026, den første med ny arbeidsflyt. Svar på norsk, bruk bare norsk tid (Europe/Oslo, vintertid UTC+1), aldri UTC, og ingen tankestrek.

Arbeidsmappe: C:\Users\FrodeMidjo\kode\syklusbordet-data (repo frdmid/syklusbordet-data). Python startes med `py`. Git og `gh` finnes. Les først notater/LOGG.md (nyeste øverst) og notater/OVERLEVERING.md. Kjør `git pull --rebase origin main` først.

Sjekk disse fire, og regn om alle tidsstempler fra UTC til norsk tid:
1. Hovedkjøringen 08:48: `gh run list --workflow ukentlig.yml -L 5`. Det skal finnes en planlagt kjøring (event schedule) rundt 08:48 som er fullført med success, og jobbene kapitulasjon, priser og shipping skal ha kjørt (ikke hoppet over). index.json skal ha "oppdatert" fra 28.10. shadow/run_manifest.csv skal ha linjer for 2026-W44 med status ok for champion_v1_1 og de fem Challengerne (gass_rigger, laks_tilbud, olje_rigger, kull_ar95, bred_nedgang). Sjekk også at uran_futures_uke.csv har fått en rad for 2026-10-25 eller 2026-10-18 (Yahoo UX=F hadde ingen ny notering etter 15.10; mangler raden, si det).
2. Reserven 09:56: det skal finnes en planlagt kjøring rundt 09:56 der jobben «vakt» skrev «hopper over» og jobbene kapitulasjon, priser og shipping ble hoppet over (skipped). Bruk `gh run view <id>` og `gh run view <id> --log` for vakt-jobben.
3. Rutinen 10:15: bruk verktøyet RemoteTrigger, action list_runs med trigger_id trig_01HoJvyjwZRq5J4QNcXoFkr3, og get_run_log for kjøringen rundt 10:15. Den skal ha skrevet 25 segmenter og kontekstdokumentene (vix, dollar, endringer, helse, gass_b, laks_biomasse, regime, uran_kontrakt) og ført ukeloggen med klokkeslett i norsk tid.
4. Rutinen 13:15: samme verktøy. Den skal ha sett at ukens tall allerede var skrevet (marked/endringer med samme uke.ny_dato) og ikke skrevet noe, og ikke ført en ny oppføring i ukeloggen.

Gjør ingen endringer i rutiner, arbeidsflyter eller kode. Feiler noe, finn årsaken og beskriv den, men ikke start kjøringer på nytt uten at Frode ber om det. Før et kort innslag øverst i notater/LOGG.md (dato og klokkeslett fra PowerShell Get-Date, «Claude Code», hva som ble sjekket, resultat per punkt, hva Cowork må vite), commit med melding «Logg: sjekk av ukekjøringen 28.10» og linjen «Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>», og push til main.

Rapporter til slutt kort til Frode: ett avsnitt per punkt, ok eller ikke ok, med klokkeslett i norsk tid.