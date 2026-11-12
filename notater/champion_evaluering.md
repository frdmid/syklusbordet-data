# Evalueringsprotokoll for Champion v1.1

Skrevet 12.11.2026 av Claude Code på Frodes bestilling (steg 2 i
`notater/2026-11-11_gjennomgang.md`). Forhåndsregistrering: kriteriene under
er satt **før Championen har hatt en eneste inngang**. Per 12.11.2026 har
`shadow/shadow_events.csv` åtte rader, alle av typen `watch_*`, null
`hypothetical_entry` og null modningshendelser, og `shadow/shadow_outcomes.csv`
er tom. Klokken har altså ikke begynt å gå.

**Grensene i denne filen flyttes ikke etterpå.** Trengs en endring, skrives en
ny protokoll med egen dato, den gamle står, og begrunnelsen føres i
`notater/LOGG.md`. Det er samme regel som for sondene.

Protokollen kan ikke pekes til fra `config/champion_v1_1.json`, fordi den
filen aldri endres for hånd. Pekeren ligger i `notater/OVERLEVERING.md` og i
loggen.

## 1. Hva som evalueres

Champion v1.1 slik den er frosset i `config/champion_v1_1.json`: bunnsone når
A rå og A detrendet begge er 80 eller mer, inngang til kursen på signaldatoen,
holdt 24 måneder, porten C stengt gjør et papir ikke kjøpbart.

Ingenting annet evalueres her. Challengerne har sine egne kriterier i
`config/challengers/`. Det parallelle d95-signalet for Brent og WTI er
eksplisitt utenfor: det er Frodes valg, ikke testet, og logges for seg.

## 2. Hva som er en observasjon

**Én observasjon er én makroklynge**, ikke én episode og ikke ett papir.
Klyngeregelen er Championens egen: en inngang hører til siste klynge hvis den
kommer høyst 183 dager etter klyngens første inngang, på tvers av segmenter.

Dette er det viktigste valget i protokollen. Råvarene flagger sammen: i
papirporteføljens historikk ble elleve inngangsmåneder fra 2011 til 2023 bare
seks klynger, og 2020 alene ga tre segmenter. Teller man episoder eller
papirer som uavhengige observasjoner, får man et tall som ser sterkt ut og
ikke betyr noe. Prosjektets egne sonder teller hver makrohendelse én gang, og
protokollen gjør det samme.

Papirtallene rapporteres likevel, men som beskrivelse, aldri som
observasjoner i testen. Det skal stå i hver rapport.

## 3. Primærutfallet

For hver modnet klynge:

1. For hvert segment som flagget i klyngen: avkastning over 24 måneder fra
   signaldatoen, i NOK med utbytte, likt vektet over segmentets **kjøpbare**
   papirer på signaldatoen (`instrument_eligible`, altså på tavlen, ikke
   omvendt eksponering, og C ikke stengt).
2. Klyngens avkastning: likt vektet over segmentene i klyngen, altså ett
   segment er én vekt uansett hvor mange papirer det har.
3. Klyngens **meravkastning**: klyngens avkastning minus MSCI World
   (`IWDA.L`, i NOK) over nøyaktig det samme vinduet, fra den første
   signaldatoen i klyngen.

OSEBX (`OSEBX.OL`) regnes og rapporteres ved siden av, men avgjør ikke.
Begrunnelsen er pre-registrert her: papirene er globale (Toronto, London,
Oslo, Paris, New York), så MSCI World er den riktige hindringen, og OSEBX er
det Frode ellers kunne eid. Å velge den som ser best ut i ettertid er ikke
tillatt.

**To mål per klynge:** meravkastningen i prosentpoeng, og om den er positiv.

### Kanttilfeller, avgjort nå

- **Klynge uten kjøpbart papir** (`investable_signal` usann): det er et
  resultat, ikke manglende data. Klyngen telles i rapporten og i nevneren for
  «hvor ofte ga regelen noe handlbart», men den har ingen avkastning og
  inngår ikke i medianen eller fortegnstellingen. Antallet rapporteres alltid.
- **C stenger etter inngang:** primærutfallet er de 24 månedene uansett.
  `C_forced_exit` logges og rapporteres for seg, som Championens
  spesifikasjon sier.
- **Et papir slutter å handles** (avnotering, oppkjøp, slik GOGL ble CMBT):
  avkastningen regnes til siste kurs som finnes, posisjonen regnes som
  avsluttet der, og det føres i rapporten. Papiret erstattes ikke.
- **Uke merket `code_changed` eller `data_stale`** i snapshotet som ga
  inngangen: klyngen telles, men merkes i rapporten. Er flertallet av
  klyngene merket, er testen ikke gyldig, og det skal stå tydelig.
- **Klynge som ennå ikke har modnet:** utelates helt. Ingen delvise
  avkastninger i primærutfallet.

## 4. Hva ulike antall klynger kan avgjøre

Dette avsnittet er grunnen til at protokollen er bygget som den er. Med en
ensidig fortegnstest over klynger:

| Krav | Falsk godkjenning hvis regelen er verdiløs | Treffer en god regel (vinner 70 %) |
|---|---|---|
| minst 2 av 3 | 50,0 % | 78 % |
| minst 4 av 5 | 18,8 % | 53 % |
| minst 5 av 6 | 10,9 % | 42 % |
| minst 6 av 7 | 6,2 % | 33 % |

**To av tre kan ikke brukes som bestått-krav:** en verdiløs regel klarer det
annenhver gang. Og selv ved seks klynger ville en virkelig god regel feile
kravet oftere enn den klarer det.

Historisk takt: seks klynger på 11,2 år, altså én per 1,9 år, og klyngene
kommer i rykk (2015, 2020). Med 24 måneders modning betyr det grovt tre modne
klynger rundt åtte år etter første inngang, fem rundt elleve og seks rundt
tretten. Første inngang har ikke kommet ennå.

**Konklusjonen av dette:** en levende test som skal bekrefte regelen er flere
tiår unna. Det den kan gjøre tidligere, er å **forkaste** den. Protokollen er
derfor i hovedsak et falsifiseringsinstrument, og bestått-kravet står for
ordens skyld.

## 5. Avgjørelsesreglene

### 5a. Varsel (gjennomgang, ikke forkasting)

Etter **tre** modne klynger: er medianen av meravkastningene negativ, skriver
Claude Code et varsel i loggen og i prosjektchatten, og Frode leser tallene.
Dette forkaster ingenting. En god regel (vinner 70 % av klyngene) utløser
varselet i 22 % av tilfellene, så det skal leses som «se på dette», ikke som
en dom.

### 5b. Forkastet

Etter **fem** modne klynger, hvis **begge** holder:

- medianen av meravkastningene er negativ, og
- høyst én av fem klynger slo MSCI World.

En god regel treffer dette i bare 3,1 % av tilfellene, en verdiløs i 18,8 %
og en dårlig (vinner 30 %) i 52,8 %. Det er den beste balansen som er mulig
med fem observasjoner.

**Hva som skjer da:** Championen blir kontekst på bordet, på linje med trend
og COT, og slutter å være det Frode handler på. Bunnsonen vises videre, men
med evidensgrad svak og en setning om at den levende testen forkastet den.
Den beste Challengeren som selv har bestått sitt eget kriterium, vurderes som
Champion v2.0 fra en ny dato. Finnes ingen slik Challenger, står bordet uten
en modell, og det er et gyldig utfall.

### 5c. Bestått

Etter **seks** modne klynger, hvis **begge** holder:

- minst fem av seks klynger slo MSCI World, og
- medianen av meravkastningene er minst 10 prosentpoeng over 24 måneder.

Selv da er formuleringen «forenlig med at regelen virker», ikke «bevist». Med
seks observasjoner er falsk godkjenning 10,9 %, og det skal stå i rapporten
hver gang.

### 5d. Alt annet

Ikke avgjort. Loggingen fortsetter. **Ikke forkastet er ikke det samme som
bekreftet**, og statusen fram til noe av det over slår inn, er den som står på
dashbordet i dag: in-sample-evidens, evidensgrad middels.

## 6. Maskinerikontrollen, som kan gjøres tidlig

Denne er ikke en del av dommen, men den er det eneste som kan kontrolleres
innen rimelig tid, og den har en reell feilmåte.

Ved **første** modne klynge skal Claude Code:

1. regne avkastningen på nytt fra snapshotet og inndatafilen for signaluken,
   uavhengig av utfallsmodulen, og kontrollere at de to er like,
2. kontrollere at papirene som ble brukt er de som sto i snapshotet på
   signaldatoen, ikke dagens papirer på tavlen,
3. kontrollere at valutaomregningen bruker kursene i snapshotet,
4. kontrollere at referansene er hentet for samme vindu, og
5. føre resultatet i loggen.

Avviker de to beregningene, er det en implementasjonsfeil, og den håndteres
som D-feilen 12.10.2026: korreksjonslogg, og ny Championversjon hvis dataene
er feil.

## 7. Sekundære lesninger

3, 6 og 12 måneder regnes og rapporteres, og **avgjør ingenting**. De står
der fordi de kan vise at noe er galt tidlig, og fordi prosjektet alt har
funnet at korte holdetider er dårligere enn 24 måneder.

Papirnivå, segmentnivå og d95 rapporteres beskrivende, med den faste
setningen om at de ikke er uavhengige observasjoner.

## 8. Hvem gjør hva

- **Claude Code** regner tallene fra `shadow/shadow_outcomes.csv` og
  snapshotene, skriver dem i `notater/LOGG.md` og sier fra i den aktive
  prosjektchatten når en av terskelene i avsnitt 5 er nådd. Den avgjør ikke.
- **Frode** avgjør, i prosjektchatten, og avgjørelsen føres i loggen med dato.
- **Onsdagsrutinen skal ikke vise shadow-status** (Frodes regel 05.10.2026).
  Varsel går i prosjektchatten.

## 9. Det som mangler for å kunne kjøre dette

`shadow/shadow_outcomes.csv` er tom. Fase 2 av Shadow-OOS, som regner
utfallene, er ikke bygget. Protokollen kan altså ikke utføres ennå, men den er
skrevet nå fordi den må være satt før første inngang, og første inngang kan
komme når som helst: jernmalm mangler 9,2 poeng og Henry Hub 24,5 til
bunnsonen per 11.11.2026.

**Forslag til modulen**, ikke bygget: `shadow_utfall.py` i roten, kalt fra
`shadow_challenger.kjor` etter Challengerne, som leser snapshotene og
`logg/kurser_uke.csv`, regner avkastning per papir, segment og klynge ved 3,
6, 12 og 24 måneder, og legger rader til `shadow/shadow_outcomes.csv` med
`so.legg_til_rader`, altså bare tillegg. Den må **ikke** ligge blant
Championens 16 hashede filer, slik at den kan rettes uten å gjøre Championen
ugyldig. Den bør ha egne tester i `test_shadow_oos.py`, minst: at en
avkastning regnes fra snapshotets kurser og ikke fra dagens, at en klynge
uten kjøpbart papir gir en rad uten avkastning, og at en modning ikke skrives
to ganger.

## 10. Kjente begrensninger

- **Få observasjoner.** Hele avsnitt 4. Dette er den bindende begrensningen,
  og ingen statistisk finesse løser den.
- **Papirene er valgt i 2026** på data fra 2016 til 2026. Framover er det
  ikke en skjevhet, siden utvalget er frosset i snapshotet, men papirene kan
  være tilpasset en periode som ikke gjentar seg.
- **Universet kan krympe.** Papirer forsvinner (BELCO, GOGL, AGAS er alt
  borte). Blir et segment uten kjøpbare papirer, gir det klynger uten
  avkastning, og det rapporteres.
- **En klynge er ikke én beslutning.** Frode kjøper ikke nødvendigvis alle
  segmentene i en klynge, og bordet foreslår ingen størrelser. Protokollen
  måler regelen, ikke porteføljen.
- **MSCI World er ikke risikojustert.** Protokollen sammenligner rå
  avkastning. Papirene er mer volatile enn verdensindeksen, så et positivt
  resultat er ikke uten videre en god byttehandel. Det skal stå i rapporten.
