# Tillegg til sikkerhetskopien, 12.11.2026

Dette er IKKE en full sikkerhetskopi. Det er de filene som er endret siden
`sikkerhetskopi/2026-11-09/`, slik at en gjenoppretting gir dagens tilstand.
Alt som ikke ligger her, hentes fra kopien 09.11, som står urørt.

**Start med `prompts.txt` i denne mappen.** Den er kopien fra 09.11 med
stiene rettet.

## Hva som er endret

| Fil | Hvorfor |
|---|---|
| `dashbord_v78_publisert.html` | Dashbordet versjon 78 slik verten serverer det, med vertens omslag |
| `dashbord_v78_til_publisering.html` | Samme side uten omslaget, klar til å publiseres som ny artifact (med `db`) |
| `rutine/onsdagsrutine_prompt.txt` | Onsdagsrutinens tekst endret 11.11.2026: punkt 6i krever `nivaa_grenser` og `volvar_grenser`, og rapportlinjen for regime viser de to leddene |
| `prompts.txt` | Peker til v78 og til rutineteksten her |
| `sha256.txt` | Sjekksum for hver fil i denne mappen |

## Hva som fortsatt hentes fra 09.11

Databasen (`database/`), minnefilene (`minne/`), de planlagte oppgavene
(`planlagte_oppgaver/`) og rutinens innstillinger
(`rutine/onsdagsrutine_meta.json`). De er uendret. I Notion gjelder det også
`marked/alu_tilbud` (IAI) og `data_privat/`, som aldri ligger i repoet.

Databasens `marked/regime` har fortsatt forrige feltstruktur. Det er riktig:
dashbordet v78 viser den gamle cellen når de nye feltene mangler, og første
onsdagskjøring etter gjenopprettingen skriver den nye strukturen.

## Endret siden 09.11.2026

- **Dashbord v78** (11.11): uro-feltet i regimeboksen delt i to, nivå
  (månedssnitt VIX) og volvariasjon (månedssnitt VVIX), mot absolutte grenser
  20 og 30 for nivå og 105 og 120 for volvariasjon. Fem ord: rolig, spent
  nivå, urolig forventning, forhøyet og sjokk, med hysterese (opp straks, ned
  etter to måneder under). Papirkorrelasjonen står utenfor ordet.
  Grensene er valgt, ikke målt. Se `notater/2026-11-11_regime_sjokk_forslag.md`.
- **`kontekst_regime.py`** skriver de nye feltene fra første
  onsdagskjøring etter 11.11.2026.
- **Onsdagsrutinen** endret 11.11, se tabellen over.
- **Sonde `sonde_kjor_vvix_sjokk`** (11.11): ingen av målene (VIX-nivå,
  spredningen i VIX, VVIX) skiller utfallene etter bunnsonen. Sjokkfeltet er
  derfor fortsatt kontekst, ikke et signal.
- **Tidssonefeil funnet 11.11:** `TZ=Europe/Oslo date` i Git Bash på Frodes
  maskin svarer GMT +0000, altså UTC, og ga logginnslag en time bak. Bruk
  Python med `zoneinfo`. Står i `notater/OVERLEVERING.md` under Fallgruver.
- **`test_no_future_data`** rettet 12.11: datoen utledes fra dataene i stedet
  for å pinne 2026-10-07. Hele suiten består, 16 av 16.
- **Gjennomgang 11.11** med forslag: `notater/2026-11-11_gjennomgang.md` og
  promptene som gjør dem, `notater/2026-11-11_prompt_forbedringer.md`. Ingen
  av de fem prioriterte stegene er kjørt.

## Status 12.11.2026

- Dashbord versjon 78. Shadow-OOS: Champion v1.1 og seks Challengere.
- `ukentlig.yml` onsdag 08:48, reserve 09:56. Kjøringen 11.11 gikk av seg selv.
- Onsdagsrutinen gikk 11.11 (10:15 og 13:19). Neste 18.11 kl. 10:15.
