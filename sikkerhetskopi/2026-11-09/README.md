# Sikkerhetskopi 09.11.2026

Overleveringspakke for å fortsette Syklusbordet i en ny Claude-konto.
Publiserte artifacts, artifact-databasen, skyrutiner og lokale planlagte
oppgaver i Claude-appen følger ikke med en konto. Repoet (kode, data,
Shadow-OOS, sonder, notater) ligger hos GitHub og påvirkes ikke. Erstatter
kopien fra 23.10.2026 (som står urørt ved siden av).

Samme kopi, pluss det som ikke kan ligge i et offentlig repo (IAI-tallene for
aluminium), ligger i Notion: siden «SB handover mappe», mappen
«Sikkerhetskopi 2026-11-09». **Start med `prompts.txt`.**

## Innhold

| Fil | Hva |
|---|---|
| `prompts.txt` | Promptene, i rekkefølge, for å gjenskape alt i en ny Claude-konto |
| `dashbord_v77_publisert.html` | Dashbordet versjon 77 slik verten serverer det, med vertens omslag |
| `dashbord_v77_til_publisering.html` | Samme side uten omslaget, klar til å publiseres som ny artifact (med `db`) |
| `database/segments/*.json` | Alle 26 dokumentene i samlingen `segments` (18 råvarer, 7 skip, `miners`) |
| `database/marked/*.json` | `vix`, `dollar`, `endringer`, `helse`, `gass_b`, `laks_biomasse`, `regime`, `uran_kontrakt`, `handel` |
| `database/logg/flagg.json`, `database/meta/status.json` | Gammel flagglogg og statusdokument (brukes ikke av dashbordet, tas med for helhet) |
| `rutine/onsdagsrutine_prompt.txt` | Hele teksten i onsdagsrutinen (trig_01HoJvyjwZRq5J4QNcXoFkr3), versjon med steg 6l |
| `rutine/onsdagsrutine_meta.json` | Navn, tidsplan, modell, tillatelser og koblinger |
| `planlagte_oppgaver/*.md` | De lokale planlagte oppgavene (alle engangs og brukt; malen for en onsdagssjekk) |
| `minne/*.md` | Claude Codes minnefiler for prosjektet (norsk tid, varsling, Shadow-OOS) |
| `sha256.txt` | Sjekksum for hver fil |

**Ikke her (offentlig repo):** `marked/alu_tilbud` (produksjon av aluminium
utenfor Kina fra IAI, bare til personlig bruk) og `data_privat/`. De ligger
bare i Notion-kopien.

## Status 09.11.2026

- Dashbord versjon 77: handlingsliste med evidensgrad og papirportefølje
  øverst, regimeboks, paneler (med Gullgruver), korrelasjonsmatrise med
  USD/NOK, datahelse.
- Shadow-OOS: Champion v1.1 og seks Challengere (laks_tilbud, gass_rigger,
  olje_rigger, kull_ar95, bred_nedgang, gull_begge fra 04.11).
- GitHub Actions `ukentlig.yml` onsdag 08:48, reserve 09:56. Den planlagte
  kjøringen 04.11 gikk ikke og ble startet for hånd; sjekk at den går av seg
  selv.
- Uranprisen (ukeraden) hentes fra Sprott fra 04.11, Yahoo som reserve.

## Gjenopprette

Følg `prompts.txt`. Kort: (1) klon repoet og les deg opp, (2) publiser
dashbordet som ny artifact med `db` og skriv databasen inn (pluss
`alu_tilbud` fra Notion), (3) lag onsdagsrutinen på nytt med ny adresse,
(4) gjenskap prosjektet «Handelsalgoritme» med ukeloggen, (5) oppdater
Notion-siden og test en onsdag.

## Ikke med her

Egne skills i claude.ai må eksporteres separat. Koblinger (Notion, Google
Drive og andre) må kobles til på nytt. Prosjektdokumentene i claude.ai-
prosjektet «Handelsalgoritme» (blant annet `claude/syklusbordet-ukelogg.md`)
ligger bare i claude.ai og må eksporteres derfra. Andre skyrutiner på
kontoen (Skiferbarometeret, Bordet) hører til andre prosjekter.
