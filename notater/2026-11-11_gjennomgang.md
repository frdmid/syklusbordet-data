# Uavhengig gjennomgang av Syklusbordet, 11.11.2026

Skrevet av Claude Code (ny økt, uten forhistorie i prosjektet) på Frodes
bestilling. Grunnlag: Notion-siden «SB handover mappe» med sikkerhetskopien
2026-11-09, `CLAUDE.md`, `notater/LOGG.md`, `notater/OVERLEVERING.md`,
`notater/shadow_oos_plan.md`, backtestnotatet 28.09, koden (`priser.py`,
`shadow_oos.py`, `shadow_challenger.py`, `kontekst_handel.py`,
`instrumenter.py`, arbeidsflytene), dataene (`index.json`, `helse.json`,
`handel.json`, `shadow/`), dashbordet v77 og sondeutskriftene. Testene i
`test_shadow_oos.py` ble kjørt lokalt: 16 av 16 besto. Ingenting i repoet er
endret utover dette notatet og loggen.

## Helhetsvurdering

Prosjektet er uvanlig disiplinert for et enmannsprosjekt: kriterier skrives
før kjøring, Championen er frosset med hash av 16 kodefiler, shadow-loggen er
bare tillegg og kontrolleres med hashkjede og tester, evidensgradene på
dashbordet sier ærlig at ingen regel er «sterk», og overleveringen er
komplett nok til at en ny konto kan ta over. Metoden er stort sett sunn.

Svakhetene ligger tre steder: (1) Shadow-OOS vil trenge mange år før den
kan si noe, og det er ikke skrevet ned hva som skal til for at Championen
består eller forkastes; (2) driften hviler på en språkmodell som gjør
ETL-arbeid etter en tolv stegs prosaspesifikasjon, og på kildekode som bare
finnes i selve artifacten; (3) en del tekster er blitt så store at regelen
«les loggen først» ikke lenger kan følges bokstavelig.

## Hva som fungerer godt

- Punkt i tid overalt: A, Ad og Ar regnes bare på det som var kjent da.
  Avkortingen av administrerte prisserier (gull 1971, jernmalm 2010 osv.)
  er begrunnet og målt, ikke valgt.
- Bunnsonen (rå og detrendet A 80) ble testet på data uten
  overlevelsesskjevhet (Ken French-bransjer før 2011) og består ikke der.
  Det står i notatet og i evidensgraden. Få prosjekter tåler å skrive det.
- Shadow-OOS: registrering før data, egen startdato per Challenger,
  korreksjonslogg i stedet for retting, reproduserbarhetstest. Manifestet
  for W45 har Champion og seks Challengere ok.
- Papirene er valgt på målt korrelasjon etter at markedet er tatt ut, ikke
  på fortelling, og avgrenset til det som kan handles på IKZ.
- Deflatoren har fem ledd med kontroll mot BLS, og «hel måned»-regelen
  hindrer at flagg slår inn og ut midt i en måned.
- Overleveringen: prompts.txt i rekkefølge, sha256, databasedump, rutinens
  tekst og minnefilene. Det mangler lite.

## Svakheter og forslag

Forslagene er ordnet etter hvor mye de betyr. Der det finnes flere rimelige
veier, står alternativene, og det jeg ville valgt står først.

### 1. Shadow-OOS har for lite kraft, og Championen mangler en dom-regel

Papirporteføljen 2011 til 2026 har 13 innganger på 15 år, klumpet i 2015 og
2020. Med 24 måneders holdetid og Challengernes krav om tre modne
makroklynger kommer første dom realistisk rundt 2032. Challengerne har
`decision_rule` i config; Championen har det ikke.

- Skriv en evalueringsprotokoll for Championen nå, før første inngang: hvor
  mange episoder, hvilken horisont, hvilket krav mot OSEBX og MSCI World,
  og hva som skjer ved forkasting. Legg den i `notater/` og pek til den fra
  metadata i `config/champion_v1_1.json` sin etterfølger (config endres ikke).
- Aksepter åpent at den levende testen de første årene bekrefter
  rørsystemet, ikke kanten. Det som handles på, er in-sample-evidensen, og
  den er «middels». Dashbordet sier det alt; protokollen bør gjenta det.
- Vurder å forhåndsregistrere 6 og 12 måneder som foreløpige lesninger,
  slik at noe kan sies i 2028, uten at 24 måneder slutter å være primær.

### 2. Papirporteføljen på 31 % i året står øverst på dashbordet

Tallet er regnet med papirer valgt i 2026, og teksten sier det. Det ankrer
likevel. Alternativer:

- (anbefalt) Vis en parallell serie regnet på noe som fantes hele veien:
  Ken French-bransjene eller brede fond som EXV6 og IOGP, side om side med
  dagens papirer. Avstanden mellom de to er selve poenget.
- Vis bare avkastning mot MSCI World og OSEBX med skjevhetsvarselet først.
- Ta tallet ut og vis bare episodelisten.

### 3. Onsdagsrutinen er en språkmodell som gjør ETL

Prompten er tolv steg med valideringsregler, bevaringsregler og unntak. Den
feilet 30.09, Actions måtte startes for hånd 04.11, og hver uke koster en
Opus-kjøring. Den farligste feilmåten er at gamle tall skrives som ferske;
halve prompten finnes for å hindre akkurat det. Alternativer:

- (anbefalt) La dashbordet lese JSON-filene rett fra det offentlige repoet
  (raw.githubusercontent med cache-brekk, eller jsDelivr med commit-sha fra
  GitHub-API), og bruk databasen bare til `marked/alu_tilbud` (privat) og
  som reserve. Da er dashbordet ferskt i samme sekund som Actions er ferdig,
  SEED på 560 kB kan ut av fila, og rutinen krymper til ukeloggen eller
  forsvinner. Forutsetningen er at repoet forblir offentlig, eller at et
  lesetoken legges inn hvis det blir privat.
- Behold rutinen, men flytt validering, bevaring og rapport inn i et skript i
  repoet (`rutine_pakke.py`) som rutinen kjører. Prompten blir «kjør
  skriptet, skriv filene det godkjente, lim inn rapporten». Reglene blir
  testbare i stedet for prosa.
- La det stå. Da bør i det minste reservekjøringen torsdag (foreslått
  15.10, ikke bestilt) komme på plass.

### 4. Dashbordets kildekode finnes bare i artifacten

740 kB i én fil, der 560 kB er innbakt SEED og rundt 130 kB er kode. To
økter publiserer til samme adresse, og v54 mistet tittel og fargene.
Sikkerhetskopien 09.11 har fila, men det er en kopi, ikke kilden.

- Gjør repoet til kilden: `dashbord/index.html` (uten SEED, eller med SEED
  lagt inn av et lite byggeskript), publisering alltid fra den fila, og et
  kontrollskript som sjekker `<title>` og `:root` før publisering. Da er
  hver versjon diff-bar i git, og «les siste versjon først» blir
  `git pull`.

### 5. Reproduserbarhet: koden er frosset, bibliotekene er det ikke

`requirements.txt` har `pandas>=2.0` og `numpy>=1.24`. Championens hash låser
koden, men `polyfit`, `percentile` og `resample` kan endre oppførsel mellom
versjoner, og Actions installerer nyeste hver onsdag.

- Lås eksakte versjoner i `requirements.txt` (de som kjørte 14.10) og skriv
  versjonene inn i `run_manifest.csv`. En oppgradering blir da en synlig
  hendelse, ikke en stille endring. Dette er den billigste forbedringen på
  listen.

### 6. Sommertid i arbeidsflyten

`ukentlig.yml` er identisk med forslaget 21.10 og har tidene for vintertid.
Kommentaren sier at de må flyttes for hånd 28.03.2027. Siden
`vakt_ukentlig.py` alt hopper over når `index.json` er skrevet samme dag,
kan alle fire tidene stå inne (06:48, 07:48, 07:56 og 08:56 UTC). De
overflødige koster en vaktjobb på fem sekunder. Må gjøres av Frode eller
Cowork, siden Code ikke kan endre arbeidsflytene.

### 7. Loggen og ukeloggen er blitt for store til å leses først

`LOGG.md` er 176 kB med 156 innslag siden 28.09. Regelen «les den før du
begynner» kan ikke følges av en ny økt uten å bruke en stor del av
konteksten, så i praksis leses toppen. Ukeloggen i claude.ai nærmer seg
grensen på 60 000 tegn.

- Rull måneden ut: `notater/logg/2026-10.md` for eldre innslag, `LOGG.md`
  beholder inneværende måned pluss en kort «Status nå»-blokk øverst (20
  linjer) som erstatter behovet for å lese historikken. Samme for
  ukeloggen.
- La Actions skrive ukerapporten deterministisk til `logg/uke/<uke>.md` fra
  de samme filene. Da ligger den eneste delen av prosjektet som i dag bare
  finnes i claude.ai, også i GitHub.

### 8. Git-historikken

81 commits 04.11 og 89 commits 28.10, én per fil gjennom contents-API.
Historikken blir støy, og hver push er et eget kappløp. Et felles
`github_push.py` som samler alle filene fra ett skript i én commit
(trees-API), eller én `git commit` i runneren til slutt, gir en lesbar
historikk. Ikke viktig, men billig.

### 9. Tester finnes bare for shadow

Persentilfunksjonene, flagg og oppsikt, hel måned-regelen, Challengernes
`snapshot` og porteføljeavspillingen i `kontekst_handel.py` har ingen
tester. Championens hash hindrer uønsket endring, men ikke en feil som alt
ligger der (D-feilen 12.10 var av det slaget).

- Gullprøver på en syntetisk serie med kjente svar for A, Ad, Ar, flagg og
  oppsikt, og en avspilling av `kontekst_handel` fra lagrede kurser. Kjøres
  lokalt og i sondeflyten.

### 10. Offentlig repo og Fearnleys

`arkiv/fearnleys/` har 46 PDF-er (13 MB) av Fearnleys ukerapporter, offentlig
tilgjengelig. Rapportene er gratis, men videreformidling er noe annet enn
nedlasting. Sjekk vilkårene; flytt eventuelt arkivet til `data_privat/` og
la bare de uttrukne tallene ligge åpent. Merk at punkt 3 (dashbordet leser
repoet direkte) forutsetter at repoet er offentlig, så de to henger sammen.

### 11. Metodiske merknader til A

- Detrendet A tilpasser én rett linje på hele det voksende vinduet. For
  serier med brudd (jernmalm fra 2010, kull fra 2000) er trenden skjør, og
  etter en lang oppgang sier Ad «billig» mot en trend som er dratt opp.
  Forslag til sonde, ikke endring av Champion: følsomhet for trendvindu
  (voksende mot rullende 20 år) på bransjedataene før 2011.
- Amerikansk KPI deflaterer alt, også laks (omregnet til USD) og TTF.
  Konsistent, men en kroneinvestor får «real» i dollar. Bør stå i
  metodeteksten på dashbordet.
- Uranraden i `uran_futures_uke.csv` byttet fra futures til Sprott-spot
  04.11. Bruddet er loggført; det bør også stå som en kolonne i fila
  (`kilde`), så en senere sonde ikke blander de to.

### 12. Evidensgradene kan bære tallstørrelse

Hver grad bør vise antall episoder og testperiode ved siden av ordet
(«middels, 15 klynger, 1995 til 2024»). Det er den informasjonen leseren
trenger for å vekte graden, og den finnes alt i sondeutskriftene.

### 13. Overleveringen er god, men uprøvd

- Gjør en gjenopprettingsøvelse: kjør prompt 1 og 2 mot en ny, midlertidig
  artifact fra sikkerhetskopien. Det er det eneste som beviser at kopien
  virker, og det koster en time.
- Rutinen bruker `project_read` og `project_write` mot claude.ai-prosjektet.
  Prompts.txt bør si hva som gjøres hvis den nye kontoen ikke har det
  verktøyet (punkt 7 over løser det).
- Små ting: `README.md` er 19 byte. (Rettet 12.11.2026: påstanden om at
  `.gitignore` hadde slukt `__pycache__/` var feil. Den kom av at to filer ble
  lest sammenslått i samme kommando. `.gitignore` er i orden.)

## Prioritert, hvis bare fem ting gjøres

1. Lås bibliotekversjoner og før dem i manifestet (punkt 5).
2. Skriv evalueringsprotokollen for Championen (punkt 1).
3. La dashbordet lese repoet direkte, og gjør repoet til kilde for
   dashbordkoden (punkt 3 og 4).
4. Alle fire cron-tidene inn i `ukentlig.yml` (punkt 6).
5. Rull loggen og la Actions skrive ukerapporten til repoet (punkt 7).
