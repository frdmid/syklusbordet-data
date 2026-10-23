# Sikkerhetskopi 23.10.2026

Laget før arbeidsgiverens planlagte overgang til Claude Enterprise, slik at
alt kan gjenskapes hvis noe forsvinner. Publiserte artifacts, artifact-
databasen, skyrutiner og lokale planlagte oppgaver i Claude-appen følger
ikke nødvendigvis med en slik overgang. Repoet (kode, data, Shadow-OOS,
notater) ligger hos GitHub og påvirkes ikke. Erstatter kopien fra 09.10.2026
(som står urørt ved siden av).

Samme kopi, pluss det som ikke kan ligge i et offentlig repo (IAI-tallene for
aluminium), ligger i Notion: siden «Syklusbordet: prosjektbeskrivelse og
sikkerhetskopi», mappen «Sikkerhetskopi 2026-10-23».

## Innhold

| Fil | Hva |
|---|---|
| `dashbord_v67_publisert.html` | Dashbordet versjon 67 slik verten serverer det, med vertens omslag |
| `dashbord_v67_til_publisering.html` | Samme fil uten omslaget, klar til å publiseres som ny artifact |
| `database/segments/*.json` | Alle 25 dokumentene i samlingen `segments` |
| `database/marked/*.json` | `vix`, `dollar`, `endringer`, `helse`, `gass_b`, `laks_biomasse`, `regime`, `uran_kontrakt` |
| `database/logg/flagg.json`, `database/meta/status.json` | Den gamle flaggloggen og statusdokumentet (fra rutinen som er slettet; brukes ikke av dashbordet) |
| `rutine/onsdagsrutine_prompt.txt` | Hele teksten i onsdagsrutinen (trig_01HoJvyjwZRq5J4QNcXoFkr3) |
| `rutine/onsdagsrutine_meta.json` | Navn, tidsplan, modell, tillatelser og koblinger |
| `planlagte_oppgaver/*.md` | De lokale planlagte oppgavene i Claude-appen (to brukte, sjekken 28.10 aktiv) |
| `prompts.txt` | Promptene, i rekkefølge, for å gjenskape alt i en ny Claude-konto |
| `minne/*.md` | Claude Codes minnefiler for prosjektet (regler som norsk tid og varsling) |
| `sha256.txt` | Sjekksum for hver fil |

**Ikke her (offentlig repo):** `marked/alu_tilbud` (produksjon av aluminium
utenfor Kina fra IAI, bare til personlig bruk) og `data_privat/`. De ligger
bare i Notion-kopien.

## Gjenopprette dashbordet

1. Publiser `dashbord_v67_til_publisering.html` som ny artifact med
   kapabiliteten `db`. Den får en ny adresse; oppdater den i
   `notater/OVERLEVERING.md`, i rutineteksten og på Notion-siden.
2. Skriv dokumentene i `database/` til den nye artifactens database:
   samlingene `segments`, `marked`, `logg` og `meta`, dokument-id lik
   filnavnet uten `.json` (ArtifactData «set» med file_path, eller «batch»).
   Legg også inn `marked/alu_tilbud` fra Notion-kopien. Alt annet fyller
   onsdagsrutinen på nytt fra repoet.
3. Kontroller at `<title>Syklusbordet</title>` og `:root{ --ground:#f4f4f1`
   står øverst.

## Gjenopprette onsdagsrutinen

Lag en ny rutine med teksten i `rutine/onsdagsrutine_prompt.txt` og
tidsplanen `CRON_TZ=Europe/Oslo 15 10,13 * * 3` (onsdag 10:15 og 13:15 norsk
tid), med tilgang til artifact-databasen og prosjektet «Handelsalgoritme»
(ukeloggen). Bytt adressen til dashbordet i teksten hvis den er ny.
Innhentingen i GitHub (`ukentlig.yml`, 08:48 og reserve 09:56) påvirkes ikke.

## Gjenopprette de lokale oppgavene

Bare `syklusbordet-sjekk-2810` er aktiv (engangssjekk 28.10.2026). Den kan
lages på nytt fra fila i `planlagte_oppgaver/` hvis den ikke har kjørt.

## Ikke med her

Egne skills i claude.ai må eksporteres separat. Koblinger (Notion, Google
Drive og andre) må kobles til på nytt. Prosjektdokumentene i claude.ai-
prosjektet «Handelsalgoritme» (blant annet `claude/syklusbordet-ukelogg.md`)
ligger i claude.ai og bør eksporteres fra prosjektet. Andre skyrutiner på
kontoen (Skiferbarometeret, Bordet) hører til andre prosjekter.
