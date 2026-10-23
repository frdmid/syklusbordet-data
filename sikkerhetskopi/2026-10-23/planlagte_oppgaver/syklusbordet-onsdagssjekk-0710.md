---
name: syklusbordet-onsdagssjekk-0710
description: Kontrollerer at ukekjøringen 07.10 oppdaterte dashbordet og skrev første Shadow-OOS-snapshot.
---

Du er Claude Code og skal kontrollere prosjektet Syklusbordet for Frode etter ukekjøringen onsdag 07.10.2026. Skriv på norsk, og bruk aldri tankestrek i tekst. Opprett aldri kontoer og meld deg aldri på noen tjeneste.

## Oppsett
- Repo: `C:\Users\FrodeMidjo\kode\syklusbordet-data`. Git: `C:\Users\FrodeMidjo\AppData\Local\GitHubDesktop\app-3.6.6\resources\app\git\cmd\git.exe` (finnes den ikke, se etter nyere `app-*`). Kjør `git pull origin main` først.
- Les `CLAUDE.md`, toppen av `notater/LOGG.md`, `notater/OVERLEVERING.md` og `notater/shadow_oos_plan.md`.
- Dashbordet: https://claude.ai/artifact/5fSPzKWdZhhV1vWB6DNZbF. Databasen leses med ArtifactData, samlingene `segments` og `marked` (dokumentene `vix`, `dollar`, `endringer`, `helse`).

## Dette er en KONTROLL. Endre ingenting.
Ikke rediger filer, ikke push, ikke skriv til databasen, ikke publiser dashbordet, og ikke kjør arbeidsflyter eller rutiner på nytt. Finner du feil, beskriv dem og foreslå hva som bør gjøres. Frode avgjør.

## Sjekk
1. **GitHub Actions `ukentlig.yml`** (skal ha startet 06:00 UTC): finnes det commits fra i dag med «oppdatert ...»? Er `index.json`, `segments/*.json`, `helse.json` og `endringer.json` oppdatert i dag? Feil i loggen i `index.json`?
2. **Shadow-OOS, første snapshot** (Champion v1.0, `effective_from` 2026-10-07): finnes det rader med i dag som dato i `shadow/`, med manifestlinje, hendelser og en hashkjede som starter riktig? Kjør `test_shadow_oos.py` lokalt og rapporter resultatet. Stemmer `specification_hash` og `code_commit` i `config/champion_v1_0.json` fortsatt med registeret, og er de frosne kodefilene uendret mot hashene? Hvor mange rader, og hvilke segmenter er i bunnsone eller watch?
3. **Fearnleys-arkivet**: ligger rapporter i `arkiv/fearnleys/` (første gang var ventet rundt 18 MB, 41 rapporter)?
4. **Onsdagsrutinen `trig_01HoJvyjwZRq5J4QNcXoFkr3`** (rundt 09:16 UTC): har databasen fått dagens tall? Sammenlign `updatedAt` og innhold i `marked/endringer`, `marked/helse` og et par `segments`-dokumenter mot filene i repoet. Spesielt: viser `marked/endringer` kvartalet fra 2026-10-01 (ikke 2026-09-29), og har `segments/nikkel` og `segments/tinn` fått port C åpen etter Coworks Glencore-regel 01.10?
5. **Datahelse**: er noen rader gule eller røde i `helse.json`?

## Svar
Avslutt med et kort sammendrag til Frode: hva som er i orden, hva som ikke er det, og hva du foreslår. Hvis ukekjøringen eller rutinen ikke har gått ennå, si det tydelig og når det bør sjekkes igjen.