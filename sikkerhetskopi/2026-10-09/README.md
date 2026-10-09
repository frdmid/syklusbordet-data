# Sikkerhetskopi 09.10.2026

Laget før en mulig flytting fra Claude Pro til Enterprise. Publiserte
artifacts og skyrutiner følger ikke med en slik flytting, og kildekoden til
dashbordet fantes til nå bare i selve artifacten. Repoet ellers (kode, data,
Shadow-OOS) ligger hos GitHub og påvirkes ikke.

## Innhold

| Fil | Hva |
|---|---|
| `dashbord_v61_publisert.html` | Dashbordet versjon 61 slik verten serverer det, med vertens omslag |
| `dashbord_v61_til_publisering.html` | Samme fil uten omslaget, klar til å publiseres som ny artifact |
| `database/segments/*.json` | Alle 25 dokumentene i samlingen `segments` |
| `database/marked/*.json` | `vix`, `dollar`, `endringer`, `helse`, `gass_b`, `laks_biomasse` |
| `rutine/onsdagsrutine_prompt.txt` | Hele teksten i onsdagsrutinen (trig_01HoJvyjwZRq5J4QNcXoFkr3) |
| `rutine/onsdagsrutine_meta.json` | Navn, tidspunkt (cron i UTC), modell, tillatelser og koblinger |
| `planlagte_oppgaver/*.md` | De lokale planlagte oppgavene i Claude-appen |
| `sha256.txt` | Sjekksum for hver fil |

## Gjenopprette dashbordet

1. Publiser `dashbord_v61_til_publisering.html` som ny artifact med
   kapabiliteten `db`. Den får en ny adresse; oppdater den i
   `notater/OVERLEVERING.md` og i rutineteksten.
2. Skriv dokumentene i `database/` til den nye artifactens database:
   samlingene `segments` og `marked`, dokument-id lik filnavnet uten `.json`.
   Alt i databasen kommer ellers fra filene i repoet, så neste onsdagsrutine
   fyller den også.
3. Kontroller at `<title>Syklusbordet</title>` og `:root` står øverst.

## Gjenopprette onsdagsrutinen

Lag en ny rutine med teksten i `rutine/onsdagsrutine_prompt.txt`, onsdag
09:00 UTC, med tilgang til artifact-databasen. Bytt adressen til dashbordet i
teksten hvis den er ny.

## Ikke med her

Egne skills i claude.ai (blant annet gull-konsulent, solsok-flysok,
flere-alternativer, planner-skill, kunde-research-agent) må Frode eksportere
selv. Koblinger (Notion, Google Drive, Strava og andre) må kobles til på nytt.
