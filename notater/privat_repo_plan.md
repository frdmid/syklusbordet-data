# Plan: gjøre repoet privat

Forberedt 12.10.2026 av Claude Code (Frodes bestilling). Ligger bare på
grenen `forbered-privat-repo` til Frode bestemmer seg. Main er uendret, så
ingenting endres i drift før grenen slås inn.

## Hvorfor det trengs endringer

Flere skript leser repoets egne filer fra `raw.githubusercontent.com` uten
innlogging. I et privat repo svarer den adressen 404, og ukekjøringen ville
fått hull (KPI-kopien, uran, laksekostnad, B for rigger, D, C, B, shipping,
manuell B).

## Det som er forberedt på grenen

- Ny `repo_les.py`: leser en repofil via GitHub-API-et med `GITHUB_TOKEN` når
  den finnes (ferskt, virker for private repoer), ellers fra
  raw.githubusercontent som i dag (med nøkkelen sendt med hvis den finnes).
- `priser.py` (7 steder), `uran_kilde.py`, `shipping.py` og `tilbud_b.py`
  leser repofiler gjennom `repo_les`.
- Testet 12.10.2026 mot det offentlige repoet: alle ti filene gir nøyaktig
  samme innhold som i dag, uranserien er lik, og ukjent fil gir 404.
  API-veien med raa tekst gir samme innhold som raw.

Allerede klare for privat repo (bruker API med nøkkel): `shadow_oos.py`,
`shadow_challenger.py`, `kapitulasjon_d.py`, `overlevelse_c.py`,
`endringer.py`, `helse.py`, `kontekst_laks.py` og skrivingen i alle skript.

## Ikke rettet (sonder, kjøres sjelden)

`sonde_ikz.py`, `sonde_korrelasjon.py`, `sonde_kjor_bdi.py`,
`sonde_kjor_uran.py` og `sonde_kjor_fearnleys_mal.py` leser fra raw uten
nøkkel. Rett dem til `repo_les` hvis de skal kjøres igjen etter at repoet er
privat. Den gamle mappa `syklusbordet-automatisering_4/` er ikke i bruk.

## Rekkefølge når Frode vil gjøre repoet privat

1. Slå inn grenen i main (Claude Code), helst rett etter en onsdagskjøring.
2. Shadow-OOS: `priser.py`, `uran_kilde.py`, `shipping.py` og `tilbud_b.py` er
   frosne kodefiler i Champion v1.0. Endringen merkes `code_changed` i
   snapshotene fra uken etter. Det er en endring i hvordan filer leses, ikke
   i noen regel, og tallene er de samme. Før en linje i
   `shadow/correction_log.csv` og i loggen som sier det. Ny Challenger trengs
   ikke. NB: `repo_les.py` er ikke blant de frosne filene.
3. Kjør «Ukentlig» for hånd i Actions og kontroller at loggen i `index.json`
   ikke har nye FEIL.
4. Frode gjør repoet privat i GitHub (Settings, General, Danger Zone, Change
   visibility).
5. Onsdagsrutinen (trig_01HoJvyjwZRq5J4QNcXoFkr3) henter fra raw uten
   innlogging og vil feile. Frode kobler GitHub til rutinen i claude.ai (eller
   gir den tilgang på annen måte), og teksten endres til å hente via
   GitHub-tilkoblingen. Det må gjøres samme dag som repoet blir privat.
6. Cowork: sjekk at Cowork-økten fortsatt har tilgang til repoet.
7. Følg med på Actions-minutter: private repoer har 2 000 minutter i måneden
   på gratisplanen.
