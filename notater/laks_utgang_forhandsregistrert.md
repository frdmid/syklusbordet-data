# Forhåndsregistrert: to utganger for laksesignalet

Skrevet 25.11.2026, før noen ny episode har oppstått. Frodes bestilling etter
`sonde_kjor_laks_salg.py` samme dag. Dette dokumentet låser teksten; git-tiden
er tidsstempelet.

## Hvorfor dette ikke er en ny Challenger

Jeg forsøkte å registrere utgangen som `challenger_laks_adar_ut2_v1`, og stoppet
fordi **rammeverket ikke kan skille to utganger med samme inngang.** To ting i
`shadow_oos.py`, som er Championens maskineri og ikke skal røres:

1. En Challenger-modul kan bare sette `bottom_zone` i snapshotet. Utgangen
   finnes ikke som felt. Utfallene modnes på faste horisonter (3, 6, 12 og 24
   måneder) uansett hva spesifikasjonen sier om salg.
2. Selv om en Challenger leverer sin egen `ny_innslag`, blokkerer
   `finn_hendelser` en ny inngang når modellens egen skyggelogg har
   `bottom_zone_enter`, `_continue` eller `_active_at_start` siste 365 dager.
   En utgang som frigjør posisjonen tidligere kan altså ikke gi en ny inngang
   før det er gått tolv måneder likevel.

To Challengere med samme inngang ville derfor skrevet identiske snapshots,
identiske hendelser og identiske utfall. Det ville sett ut som to målinger og
vært én. Derfor står `challenger_laks_adar_v1` alene, og de to utgangene
sammenlignes i stedet på de SAMME registrerte inngangene.

Det koster ingenting i presisjon: begge utgangene er deterministiske funksjoner
av A-banen, og A-banen ligger i snapshotene uke for uke. Det eneste som må
være låst på forhånd er regelteksten, og det er det dette dokumentet gjør.

## De to utgangene

Begge gjelder episodene til `challenger_laks_adar_v1` (inngang: detrendet A
over 80 og rullende A over 85), begge har tak på 24 måneder, og begge selger
ved månedsslutt.

**U1, den registrerte.** Første måned der rå A er 50 eller lavere.
Står i spesifikasjonen til Challengeren og endres ikke.

**U2, alternativet som registreres her.** Første måned der rå A har vært 50
eller lavere **to måneder på rad**; det selges ved slutten av den andre
måneden.

Ingen andre utganger er forhåndsregistrert. Tallene 50 og to måneder skal ikke
flyttes etterpå. Vil noen ha en annen terskel, er det en ny registrering med
ny dato, og den gamle blir stående.

## Hvorfor U2 er med

Ikke fordi den ga høyest tall. Sonden 25.11.2026 målte tretten regler på fire
episoder, og kriteriet sa før måling at den beste av dem er støy. U2 er med
fordi den retter en feil vi kan peke på uten å se på avkastningen:

- April 2020: A faller til 49 i måned 2, U1 selger, og så går A opp igjen til
  76, 87 og 89. U1 selger på én støyete måned midt i episoden.
- Samme mønster i 2025: 42 i måned 5, deretter 55, 51 og 69.
- U2 ville holdt posisjonen fra april 2020 til april 2021 i stedet for til juni
  2020.

Til orientering, og det er ikke begrunnelsen: over de fire kjente episodene ga
U1 median 6 måneder og +16,9 prosentpoeng mot MSCI World, U2 median 10 måneder
og +19,8. Begge hadde tre av fire positive, og den svakeste episoden er 2025 i
begge.

## Slik regnes de når episodene modnes

For hver `hypothetical_entry` i `shadow_events.csv` med
`model_version = challenger_laks_adar_v1`:

1. Les `A_raw` for laks fra `shadow/snapshots/challenger_laks_adar_v1/<uke>.csv`
   for ukene etter inngangen. Det er månedstall, så én verdi per måned; bruk
   den siste uken i hver måned.
2. Finn utgangsmåneden for U1 og for U2 etter reglene over, med taket på 24
   måneder.
3. Regn avkastningen for den likt vektede kurven av laksepapirene på bordet,
   i kroner med utbytte reinvestert, fra inngangsmåneden til hver utgang, og
   meravkastningen mot MSCI World (IWDA.L) i kroner.

## Hva som avgjør, og når

Challengerens registrerte primærutfall er uendret: 12 måneders avkastning,
minst tre nye episoder, støttet hvis papirene slår MSCI World i minst to av
tre med positiv median. **Utgangene avgjør ingenting om signalet.** De er et
eget og mindre spørsmål: gitt at signalet holder, hvilken utgang tar mest av
oppgangen.

Sammenligningen av U1 og U2 er beskrivende til minst tre nye episoder har
modnet, og den skal rapporteres med begge tallene uansett hvilken som er best.
Blir U2 valgt senere, er det en ny Challenger med ny startdato, ikke en
retting av den som går.
