# Prompter for forbedringene fra gjennomgangen 11.11.2026

To prompter: én til Claude Code (det meste) og én til Cowork (filene Cowork
eier). Bakgrunnen står i `notater/2026-11-11_gjennomgang.md`. Lim inn
teksten mellom strekene. Kjør Code-prompten først; Cowork-prompten kan gå
når som helst.

Tre ting bør Frode avgjøre før Code-prompten kjøres, ellers bruker Code
forslagene som står i prompten:

1. Championens evalueringsprotokoll: antall episoder, horisont og krav
   (forslag i steg 2).
2. Om dashbordet skal lese repoet direkte (steg 3). Da må repoet forbli
   offentlig.
3. Om onsdagsrutinen skal fortsette som reserve etter steg 3 (forslaget er
   ja, uendret, til to onsdager har vist at direktelesingen virker).

======================================================================
PROMPT TIL CLAUDE CODE
----------------------------------------------------------------------
Les CLAUDE.md, toppen av notater/LOGG.md, notater/OVERLEVERING.md og hele
notater/2026-11-11_gjennomgang.md. Gjør stegene under i rekkefølge, ett
steg per commit, med logginnslag i notater/LOGG.md i samme commit (norsk
tid fra `TZ=Europe/Oslo date`, nyeste øverst, ingen tankestrek). Push etter
hvert steg. Python startes med `py -X utf8`.

Regler som gjelder hele veien:
- Rør ikke de 16 kodefilene som er hashet i config/champion_v1_1.json
  (priser.py, signaler.py, instrumenter.py, uran_kilde.py, laks_innhent.py,
  kurve_innhent.py, flagglogg.py, kapitulasjon_d.py, overlevelse_c.py,
  c_manuell.py, tilbud_b.py, rigg_b.py, shipping.py, bygg_shipping.py,
  helse.py, shadow_oos.py). Alt nytt som skal kjøres ukentlig, kalles fra
  shadow_challenger.kjor etter kontekst_handel, slik kontekst-modulene gjør.
- Rør ikke config/, shadow/, c_manuell.*, b_manuell.*, CLAUDE.md eller
  .github/workflows/. Trengs en endring der, skriv en instruks til Cowork i
  loggen.
- Ingen nye kontoer, nøkler eller tjenester.
- Si fra i chatten og stopp hvis et steg krever en avgjørelse som ikke står
  her.

STEG 1. Lås bibliotekversjoner og logg miljøet.
Finn hvilke versjoner av pandas, numpy, requests, openpyxl, pdfplumber og
lxml som kjørte i den siste vellykkede kjøringen av «Ukentlig innhenting»
(`gh run list --workflow ukentlig.yml`, så `gh run view <id> --log` og
linjene «Successfully installed»). Skriv dem som eksakte versjoner
(`pandas==2.x.y`) i requirements.txt. Lag miljo_logg.py som hver uke legger
en rad i shadow/miljo.csv: iso-uke, dato, python-versjon og versjonene av
de seks pakkene. Bare tillegg, overskrift første gang. Kall den fra
shadow_challenger.kjor, sist, i samme try/except-mønster som
kontekst-modulene. Kjør den lokalt én gang for å kontrollere at fila får
riktig form, og slett den lokale testraden før commit (fila skal først
skrives av Actions). Før i OVERLEVERING under Viktige filer.

STEG 2. Evalueringsprotokoll for Championen.
Skriv notater/champion_evaluering.md, datert, med kriterier som er satt
før første inngang. Bruk disse verdiene hvis Frode ikke har gitt andre:
- Primær: 24 måneders avkastning i NOK for de kjøpbare papirene, likt
  vektet, fra hypothetical_entry, mot MSCI World (IWDA.L) og OSEBX side om
  side.
- Ingen dom før minst tre makroklynger har modnet på 24 måneder.
- Består: medianen over klyngene er positiv, og papirene slår MSCI World i
  minst to av tre klynger (eller samme andel ved flere).
- Forkastes: ellers. Da blir Championen kontekst, og den beste Challengeren
  som selv har bestått sitt eget krav, vurderes som Champion v2.0 fra en ny
  dato.
- Foreløpige lesninger ved 6 og 12 måneder rapporteres i loggen når de
  foreligger, men avgjør ingenting.
- Hvem avgjør: Frode, i den aktive prosjektchatten, etter at Code har
  regnet tallene fra shadow/shadow_outcomes.csv.
Skriv også at utfallene i shadow_outcomes.csv (fase 2) må regnes av en
modul som ikke er hashet; foreslå navn og plassering, men bygg den ikke nå.
Pek til notatet fra OVERLEVERING (Shadow-OOS) og fra handel.json sin
evidens-tekst for bunnsone (kontekst_handel.py, EVIDENS, én setning).

STEG 3. Dashbordet leser repoet direkte, og repoet blir kilde for koden.
a) Les siste versjon av artifacten https://claude.ai/artifact/5fSPzKWdZhhV1vWB6DNZbF
   med Artifact read. Ta bort vertens omslag. Lagre den som
   dashbord/index.html i repoet. Det er fra nå kilden; publisering skjer
   alltid fra den fila.
b) Lag dashbord/bygg.py som fra segments/*.json, index.json, marked.json,
   dollar.json, endringer.json, helse.json, gass_b.json, laks_biomasse.json,
   regime.json, uran_kontrakt.json, miners.json og handel.json setter sammen
   én fil dashbord/data.json med samme struktur som databasen (samlingene
   segments og marked, dokument-id som i dag, uten alu_tilbud). Skriptet
   bruker de samme kravene som onsdagsrutinens punkt 3, 6b til 6l
   (sikkerhetskopi/2026-11-09/rutine/onsdagsrutine_prompt.txt): en fil
   som ikke består, tas ikke med, og grunnen skrives i data.json under
   «avvist». Kall bygg.py fra shadow_challenger.kjor etter kontekst_handel,
   og la den pushe dashbord/data.json slik kontekst-modulene pusher.
c) Endre dashbord/index.html: ved innlasting hentes først
   https://raw.githubusercontent.com/frdmid/syklusbordet-data/main/dashbord/data.json
   med cache-brekk (`?cb=` pluss tidsstempel) og `Cache-Control: no-cache`.
   Svarer den og har «laget» nyere enn databasens endringer.uke.ny_dato,
   brukes den; marked/alu_tilbud leses alltid fra databasen. Svarer den
   ikke, brukes databasen som i dag, og SEED som siste utvei. Vis kilden
   («repo 11.11.2026 09:12», «database» eller «innbakt») i datahelse-
   boksen. Ta SEED ut av fila og legg den i dashbord/seed.json, som
   bygg_publiser.py (under) baker inn ved publisering, så fila i repoet er
   kode uten data.
d) Lag dashbord/bygg_publiser.py: leser index.html og seed.json, lager
   dashbord/publiser.html, og kontrollerer at fila begynner med
   `<title>Syklusbordet</title>`, at `:root{ --ground:#f4f4f1` finnes, og
   at det ikke finnes to `<!doctype`. Feiler kontrollen, publiseres
   ingenting.
e) Test lokalt: `py -m http.server` i dashbord/, åpne publiser.html i
   nettleserpanelet, ingen feil i konsollen, scrollWidth lik bredden ved
   390 px, og at handlingslisten, regimeboksen, panelene og
   korrelasjonsmatrisen viser tall både med data.json og uten (blokker
   raw.githubusercontent i testen).
f) Publiser til samme adresse. Kontroller etter publisering som i
   OVERLEVERING. Oppdater OVERLEVERING: kilden er dashbord/index.html, SEED
   ligger i seed.json, data.json er hovedkilde, databasen er reserve,
   onsdagsrutinen er uendret inntil videre.
g) Skriv i loggen hva Cowork må vite: les ikke lenger artifacten som kilde,
   endre dashbord/index.html i repoet og publiser med bygg_publiser.py.

STEG 4. Ukerapport fra Actions til repoet.
Lag ukerapport.py som skriver logg/uke/<iso-uke>.md med samme innhold som
onsdagsrutinens punkt 7 (tabellen med segment, A, Ad, Ar, B2, D og siste
observasjon, bunnsone og oppsikt, d95, D-dekning, COT, laks, VIX, dollar,
gass_b, biomasse, regime, uran, gullgruver, handlingslisten, jernmalm,
deflator, flagglogg, kurveform, og det som feilet), regnet fra filene i
repoet, komma som desimaltegn, norsk tid, ingen tankestrek. Kall den fra
shadow_challenger.kjor etter bygg.py. Kjør den lokalt mot dagens filer og
legg resultatet ved som logg/uke/2026-W45.md (merket «regnet lokalt
11.11»). Før i OVERLEVERING.

STEG 5. Rull loggen.
Flytt innslagene i notater/LOGG.md fra september og oktober 2026 til
notater/logg/2026-09.md og notater/logg/2026-10.md, ord for ord, i samme
rekkefølge, med samme overskrift og innledning som LOGG.md. LOGG.md
beholder innledningen, en ny blokk «Status nå» (høyst 20 linjer: dashbord-
versjon, modeller i Shadow-OOS, neste planlagte hendelser, åpne
avgjørelser, hvor eldre innslag ligger) og innslagene fra november. Legg
til en regel i innledningen: ved månedsskifte flyttes forrige måned ut, og
«Status nå» oppdateres. Oppdater OVERLEVERING der den peker til loggen.
Skriv i loggen at CLAUDE.md bør si det samme (Cowork endrer CLAUDE.md).

STEG 6. Små ting i samme commit.
- uran_futures_uke.csv: legg til kolonnen «kilde» (futures eller sprott)
  bakover etter det loggen 04.11 sier, og la kontekst_uran.py skrive den.
- README.md: ti linjer om hva repoet er, og pek til notater/OVERLEVERING.md.
- .gitignore: egen linje for `__pycache__/`.
- kontekst_handel.py: legg «episoder» og «periode» inn i hver
  EVIDENS-oppføring (tall fra sondeutskriftene), og vis dem i dashbordets
  evidenstekst («middels, 15 klynger, 1995 til 2024»). Publiser på nytt
  via bygg_publiser.py.

Til slutt: kjør `py -X utf8 test_shadow_oos.py` og bekreft 16 av 16 i
loggen. Avslutt med en kort oppsummering i chatten av hva som er gjort,
hva som venter på Cowork, og hva Frode må avgjøre.
----------------------------------------------------------------------

======================================================================
PROMPT TIL COWORK
----------------------------------------------------------------------
Les notater/2026-11-11_gjennomgang.md (punkt 6, 7 og 10) og de nyeste
innslagene i notater/LOGG.md. Gjør dette, med logginnslag i samme commit:

1. .github/workflows/ukentlig.yml: legg inn alle fire cron-tidene, så
   fila virker både ved vintertid og sommertid uten å flyttes for hånd:
     - cron: "48 6 * * 3"
     - cron: "48 7 * * 3"
     - cron: "56 7 * * 3"
     - cron: "56 8 * * 3"
   vakt_ukentlig.py hopper over når index.json alt er skrevet samme dag, så
   de overflødige kjøringene stopper etter vaktjobben. Oppdater kommentaren
   i fila og notater/ukentlig_forslag.yml til det samme.
2. CLAUDE.md: endre «Les notater/LOGG.md før du begynner» til at man leser
   blokken «Status nå» og inneværende måned i LOGG.md, og at eldre innslag
   ligger i notater/logg/. Vent med dette til Claude Code har gjort steg 5
   i sin prompt (det står i loggen når det er gjort).
3. arkiv/fearnleys/: sjekk Fearnleys sine vilkår for videreformidling av
   ukerapportene. Hvis vilkårene ikke tillater det, flytt mappen til
   data_privat/ (ignorert av git), fjern den fra git-historikken bare hvis
   Frode ber om det, og la shipping.py sitt arkivkall peke til den nye
   stien (shipping.py er hashet i Champion, så en endring der skal
   merkes som code_changed og føres i loggen; gjør det ikke uten Frodes ja).
----------------------------------------------------------------------
