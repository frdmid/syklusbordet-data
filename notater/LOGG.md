# LOGG

Felles logg for Cowork-økten og Claude Code-økten. Nyeste innslag øverst,
ett innslag per vesentlig endring. Hvert innslag har: dato og klokkeslett
(norsk tid), hvilken økt, hva som ble gjort, hvilke filer, og hva den andre
økten må vite. Detaljer kan ligge i egne notater i `notater/`, men hvert
notat skal ha en linje her. Automatiske commits fra GitHub Actions
("oppdatert ...", "sonderesultat ...") føres ikke.

---

### 05.10.2026 17:10, Claude Code
**Hva:** `code_commit` for Champion v1.0 er nå
6e5ff9756b3675b1853d0ff845f8d6bb8f2af788, ført inn i config og register.
Kodefilene der er kontrollert mot hashene i config. `specification_hash` er
uendret (9e2cef1f...).
**Filer:** `config/champion_v1_0.json`, `shadow/model_registry.csv`, loggen.
**Den andre økten må vite:** Ingenting nytt.

### 05.10.2026 17:08, Claude Code
**Hva:** To referanser for Champion v1.0 (Frodes ønske): OSEBX og MSCI
World, rapportert side om side uten at én er fasit. MSCI World måles med
iShares Core MSCI World UCITS (`IWDA.L`, akkumulerende i USD, så utbyttet
ligger i kursen); Yahoos MSCI World-indeks er bare en prisindeks. Begge
hentes hver uke og står i snapshotet med dollarkurs. Avkastning måles i NOK.
Champion fryst på nytt (`specification_hash` 9e2cef1f...), fortsatt fra
07.10.2026. 16 tester besto; ekte kjøring ga OSEBX 2067,06 NOK og IWDA
146,97 USD.
**Filer:** `shadow_oos.py`, `test_shadow_oos.py`, `config/champion_v1_0.json`,
`shadow/model_registry.csv`, `notater/shadow_oos_plan.md`,
`notater/OVERLEVERING.md`, loggen.
**Den andre økten må vite:** `code_commit` føres inn i neste commit.

### 05.10.2026 17:07, Claude Code
**Hva:** Challengere som egne grener i Shadow-OOS (Frodes beslutning), lagt
inn før start så Champion aldri må endres for en ny Challenger:
1. Kroksted `shadow_oos.kjor_challengere`: kaller `shadow_challenger.py`
   etter at Champion er skrevet. Feil der rammer ikke Champion.
2. Ny `shadow_challenger.py` (ikke frosset): registrering med hypotese,
   endrede og uendrede variabler, primært utfall, retning, beslutningsregel
   og startdato (en onsdag frem i tid), og ukentlig kjøring med egne
   snapshots, egne hendelser i den felles loggen, egen manifestlinje og
   egen hashkjede. Regler skrives i `challengers/<id>.py`.
3. Hendelser og kontroll i `shadow_oos.py` er gjort modellnøytrale.
4. `priser.py` skriver hele månedsserien (nominell og real) per
   råvaresegment til `serier/priser_mnd.csv` hver uke, til Challengere som
   regner A på nytt. Ingen tall på bordet er endret; kjørt lokalt uten
   feil (18 serier, 303 kB, siste verdi lik segmentfilene).
Champion fryst på nytt (`specification_hash` 88942503...), fortsatt fra
07.10.2026. Testene utvidet til 16, alle besto. Også ført: S logges
separat når og hvis den blir aktiv, og onsdagsrutinen skal ikke vise
shadow-status (Frodes beslutninger).
**Filer:** `shadow_challenger.py` (ny), `shadow_oos.py`, `priser.py`,
`test_shadow_oos.py`, `config/champion_v1_0.json`,
`shadow/model_registry.csv`, `notater/shadow_oos_plan.md`,
`notater/OVERLEVERING.md`, loggen.
**Den andre økten må vite:** En ny regel skal skrives som Challenger, ikke
inn i den levende koden. `code_commit` føres inn i neste commit.

### 05.10.2026 16:57, Claude Code
**Hva:** `code_commit` for Champion v1.0 er nå
2bd2f8c2c188c45575102096248fde343ea94090 (commiten med Frodes avgjørelser),
ført inn i config og register. Kodefilene der er kontrollert mot hashene i
config. `specification_hash` er uendret (633c2216...).
**Filer:** `config/champion_v1_0.json`, `shadow/model_registry.csv`, loggen.
**Den andre økten må vite:** Ingenting nytt.

### 05.10.2026 16:56, Claude Code
**Hva:** Frodes avgjørelser om Shadow-OOS lagt inn før start, og Champion v1.0
frosset på nytt (ny `specification_hash` 633c2216..., `effective_from` fortsatt
07.10.2026):
1. Det frosne er godkjent.
2. Første kjøring etter onsdagsoppdateringen teller: uken går fra onsdag til
   tirsdag, og er `index.json` ikke oppdatert siden onsdag, skrives ingenting
   (`venter_paa_onsdagsoppdatering`).
3. Endret regelkode gir en Challenger med egen startdato; Champion endres
   aldri.
4. C stengt er ikke kjøpbar, C ukjent er kjøpbar (trang og fond regnet som
   kjøpbare). `investable_signal` regnes nå: minst ett kjøpbart papir. Sju
   papirer er utelukket med dagens tall.
5. Makroklynger regnes fra klyngens første inngang (183 dager).
6. Referanseindeksen er OSEBX, hentet hver uke og lagret i snapshotet; måles
   i NOK med utbytte.
7. 26 måneder er nok: 36 måneder er tatt ut.
Testene utvidet til 14, alle besto. En kjøring mot ekte data med ekte
OSEBX-kurs ga 104 rader.
**Filer:** `shadow_oos.py`, `test_shadow_oos.py`, `config/champion_v1_0.json`,
`shadow/model_registry.csv`, `notater/shadow_oos_plan.md`,
`notater/OVERLEVERING.md`, loggen.
**Den andre økten må vite:** `code_commit` føres inn i neste commit. Trang og
fond som kjøpbare, og måling i NOK, er Claude Codes lesing; Frode må si fra
før 07.10 kl. 06:00 UTC hvis det er feil.

### 05.10.2026 16:48, Claude Code
**Hva:** `code_commit` for Champion v1.0 ført inn i `config/champion_v1_0.json`
og `shadow/model_registry.csv`: 0800ece179d8e74ccb3250abeb8289221a657c9c, der
de 16 kodefilene ligger slik de er hashet (kontrollert mot git-arkivet).
`specification_hash` er uendret (03a41a16...), siden commiten står utenfor
det som hashes.
**Filer:** `config/champion_v1_0.json`, `shadow/model_registry.csv`, loggen.
**Den andre økten må vite:** Ingenting nytt.

### 05.10.2026 16:46, Claude Code
**Hva:** Shadow-OOS fase 1 (Frodes bestilling, planlagt kjøring), etter
dokumentet «Shadow-OOS-oppsett for Syklusdashboard». Champion v1.0 (A-modellen
slik koden er i dag) er frosset med `effective_from` 07.10.2026, første
ordinære ukekjøring etter 30.09 (dokumentet bruker 05.10 som eksempel). Ny
modul `shadow_oos.py`, kalt sist i `bygg_shipping.py`, skriver hver uke ett
snapshot per segment og papir (`shadow/snapshots/champion_v1_0/<uke>.csv`),
inndata med git-blob-sha, hendelser, og en manifestlinje med hash og
hashkjede. Alt er bare tillegg: snapshotet opprettes én gang per ISO-uke og
endres aldri, og hver kjøring kontrollerer de gamle mot hashene. Config har
reglene og sha256 for de 16 kodefilene; endret kode merkes `code_changed`.
S regnes ikke i dagens kode og står som NULL, sterk kandidat finnes ikke.
12-månedersregelen og episodene gjenbrukes fra `flagglogg.py`, og
flaggloggen er ikke endret. `shadow_outcomes.csv` og `correction_log.csv` er
tomme. Testet lokalt mot dagens data (ti tester, alle besto): første snapshot
103 rader og to hendelser (oppsikt ved start for Henry Hub og jernmalm).
Dashbordet er ikke endret. Plan, filformat og Frodes spørsmål i
`notater/shadow_oos_plan.md`.
**Filer:** `shadow_oos.py` (ny), `test_shadow_oos.py` (ny),
`config/champion_v1_0.json` (ny), `shadow/` (ny: `model_registry.csv`,
`shadow_outcomes.csv`, `correction_log.csv`), `bygg_shipping.py`,
`notater/shadow_oos_plan.md` (ny), `notater/OVERLEVERING.md`.
**Den andre økten må vite:** Rør aldri filene i `shadow/` eller config for
hånd; feil føres i `correction_log.csv`. Endringer i `c_manuell.py` og de
andre 15 kodefilene i config synes nå som `code_changed` i shadow; skriv i
loggen hva som ble endret og hvorfor. `code_commit` føres inn i registeret i
neste commit. Frode må svare på spørsmål 1 til 3 i planen før 07.10 kl. 06:00
UTC.

### 02.10.2026 09:19, Claude Code
**Hva:** Frodes arbeidskopi av repoet er flyttet ut av OneDrive (Frodes
beslutning). Ny klone fra GitHub i `C:\Users\FrodeMidjo\kode\syklusbordet-data`.
Den gamle kopien under `OneDrive ... \Skrivebord\Syklusbordet_linket` var lik
main og hadde ingen filer som ikke lå i repoet. Den skal ikke brukes mer, og
døpes om så ingen skriver dit ved et uhell. Grunnen er at OneDrive
synkroniserer `.git` og kan legge tilbake eldre filer, slik det trolig skjedde
med loggen 01.10. Fallgruven i `OVERLEVERING.md` er oppdatert.
**Filer:** `notater/OVERLEVERING.md`, loggen.
**Den andre økten må vite:** Bruker Cowork en lokal mappe, skal den være den
nye, ikke OneDrive-mappa. GitHub er fasit som før.

### 02.10.2026 09:09, Cowork
**Hva:** Ny linje sist i `CLAUDE.md`: «Les også `notater/OVERLEVERING.md`.»
(Frodes bestilling, slik Claude Codes innslag 09:03 ba om.) Innslaget
01.10 kl. 12:58 under var skrevet lokalt, men ikke pushet før Claude Codes
innslag kom på main. Det er lagt inn igjen her, på sin plass etter tid.
**Filer:** `CLAUDE.md`, loggen.
**Den andre økten må vite:** Ingenting nytt utover linjen i `CLAUDE.md`.

### 02.10.2026 09:03, Claude Code
**Hva:** Nytt notat `notater/OVERLEVERING.md` (Frodes bestilling), slik at en
ny Code-økt kan ta over prosjektet: hva skårene er, hvem som eier hva, hvordan
uken og kvartalet går, dashbordets adresse og database, rutinen, viktige
filer, fallgruver (blant annet OneDrive og toppen av dashbordet) og åpne
punkter. Kontrollert at innslagene fra 30.09 kl. 13:29 og 13:32 står i loggen
igjen, og at OneDrive-feilen 01.10 bare rammet loggen, ikke koden.
**Filer:** `notater/OVERLEVERING.md` (ny).
**Den andre økten må vite:** Frode eller Cowork bør legge én linje i
`CLAUDE.md`: «Les også `notater/OVERLEVERING.md`.» Claude Code kan ikke endre
den fila. Hold notatet oppdatert når noe i det endrer seg.

### 01.10.2026 12:58, Cowork
**Hva:** Dashbordet versjon 56 og 57. Versjon 56 la inn en egen
korrelasjonsmatrise for detrendet A under standardmatrisen. Frode valgte
etter en gjennomgang å beholde bare standardmatrisen, og versjon 57 tar den
detrendede ut igjen. Grunnen: for de fleste par skiller de to matrisene seg
mindre enn usikkerheten med 36 måneder (rundt ±0,10). Kobber/nikkel er 0,66
for A og 0,65 for detrendet A. Der de skiller seg, som Brent/TTF med 0,57
mot 0,40, skyldes det hvor bratt skåren reagerer der prisen ligger i
fordelingen, ikke en annen sammenheng i markedet. Realprisen gir 0,52.
Begge versjonene er bygget uten sidens omslag. Toppen er kontrollert etter
publisering: `<title>` og `:root` står der.
**Filer:** ingen i repoet (dashbordet ligger som artifact).
**Den andre økten må vite:** `renderKorr(segs, felt, elId)` og
`korrSerie(s, felt)` tar fortsatt et felt, men kallet bruker bare "A".
Seksjonen `korr-d` finnes ikke lenger.

### 01.10.2026 12:34, Cowork
**Hva:** Ny regel i C (Frodes beslutning): år før en fusjon som endret
selskapet vesentlig, teller ikke. Nytt felt `selskap_fra` i
`c_manuell.json` er det første hele regnskapsåret i dagens form, med kilde i
`selskap_kilde`. Feltet brukes bare der det er satt per selskap, på samme
måte som `produksjon_fra`. Første gang: Glencore fra 2014 (Xstrata kjøpt
2. mai 2013). 2008 til 2013 utelates. Prøvekjørt: GLEN.L går fra stengt
(3,9 kvartaler, 2009) til åpen (positiv drift etter renter selv i 2020,
12 år, netto gjeld/EK 0,68). De andre tolv gir samme resultat som før.
Ved neste kvartalskjøring går nikkel fra stengt til åpen (Glencore åpen,
Eramet stengt), og tinn fra stengt til åpen. Sink får 2 av 2 åpne og kull
3 av 3.
Loggen: Frodes commit «Update LOGG.md» 01.10 kl. 12:29 la en eldre versjon
av loggen på main. Claude Codes innslag 30.09 kl. 13:29 og 13:32 og Coworks
innslag 01.10 kl. 12:27 forsvant. De er lagt inn igjen her, uendret.
Sannsynlig årsak er at repoet ligger i en OneDrive-mappe, og at OneDrive
skrev tilbake en eldre kopi av filen.
**Filer:** `c_manuell.json`, `c_manuell.py`, loggen.
**Den andre økten må vite:** Kjør «Kvartalsvis tilbudsskaar» etter push.
Sjekk at innslagene dine fra 30.09 står i loggen.

### 01.10.2026 12:27, Cowork
**Hva:** Laget 30.09, pushet 01.10 før loggen var ført. C for seks
selskaper uten SEC-tall (punkt 1.1 fra vurderingen av Groks forslag), lagt
inn i `c_manuell.json`. Prøvekjørt med Norges Banks kurser. De sju som alt lå inne, gir samme resultat som før.
- GLEN.L: stengt, 3,9 kvartaler. Verste år er 2009 (−3 010 MUSD, prospektet
  fra 2011), og tallet skyldes økt arbeidskapital i handelen. Netto gjeld/EK
  er 0,68. Glencore er med i nikkel, sink, tinn og kull.
- CS.TO: åpen, 16,6 kvartaler, verste år 2015 etter renter. 2011 til 2014
  mangler.
- ATYM.L: åpen, positiv drift. `produksjon_fra` er 2017 (kommersiell
  produksjon fra 1. februar 2016). 2010 til 2012 mangler, men gjelder årene
  før produksjonsstart.
- ERA.PA: stengt, 7,3 kvartaler. Verste år er 2025 (−313 MEUR).
- MPE.L: åpen, positiv drift. 2006 til 2009 er på omarbeidet grunnlag.
- RE.L: stengt, 2,9 kvartaler. Verste år er 2018 (−25,9 MUSD).
Alle seks har regnskapsår til 31. desember. Renter i driften: Glencore,
Atalaya, Eramet, M.P. Evans og REA. For Capstone ligger rentene under
finansiering i 2015 og 2025 og i driften i 2008 (`renter_i_drift_aar`).
Segmentporten ved neste kvartalskjøring:
- kobber går fra ukjent til åpen (CS.TO, ATYM.L).
- nikkel går fra ukjent til stengt (ERA.PA, GLEN.L).
- tinn går fra ukjent til stengt (bare GLEN.L).
- palmeolje går fra ukjent til åpen (MPE.L åpen, RE.L stengt).
- sink og kull er fortsatt åpne.
Rettelse i `c_manuell.py`: `port_fra` velger nå verste år etter at renten
er trukket fra, der renten ikke alt ligger i driften. Med lik
renteklassifisering alle år blir valget det samme som før. Bare Capstone
har unntak per år. Uten rettelsen ville 2008 blitt valgt, og porten ville
vist positiv drift, selv om 2015 etter renter er svakere.
Om dashbordet versjon 54: toppen av filen var skadet da jeg publiserte (se
Claude Codes innslag 13:32). Jeg bygger
videre på 55 og sjekker `<title>` og `:root` etter hver publisering.
**Filer:** `c_manuell.json`, `c_manuell.py`, loggen.
**Den andre økten må vite:** Kjør «Kvartalsvis tilbudsskaar» etter push.
Glencore stengt hviler på 2009 alene. Uten 2008 til 2010 blir verste år
2011 (−343), og porten blir åpen med 34 kvartaler. Frode avgjør om årene
før Xstrata-fusjonen skal telle. Til han har avgjort det, gjelder hele
historikken.

### 30.09.2026 13:32, Claude Code
**Hva:** Dashbordet versjon 55 er helsesjekken lagt oppå Coworks versjon 54
(korrelasjonsmatrisen som SVG, publisert 11.26 UTC, ikke ført i loggen ennå).
Versjon 54 var skadet i toppen: linjene med `<title>`, fontlenkene, `<style>`
og fargetokenene for lys modus (`:root`) var borte, og sidens omslag lå der to
ganger. I lys modus hadde siden derfor ingen tittel, ingen farger og ingen
bakgrunn. Linjene er satt inn igjen fra versjon 53. Resten av versjon 54 er
uendret, og matrisen har allerede egen rulling, så rettelsen for `#korr` i
innslaget under er ikke tatt med.
Onsdagsrutinen feilet i dag kl. 11.18 etter 6 sekunder uten å skrive noe. Den
har fått steg 6e (helse.json til marked/helse) og et punkt om datahelse i
rapporten, og er kjørt på nytt for hånd. `marked/helse` er skrevet én gang for
hånd (versjon 1).
**Filer:** ingen i repoet utover loggen; dashbordet, databasen og rutinen.
**Cowork må vite:** Bygg videre på versjon 55. Kontroller at `<title>` og
`:root` står øverst etter en publisering.

### 30.09.2026 13:29, Claude Code
**Hva:** Helsesjekk på dashbordet (Frodes bestilling etter vurderingen av
Groks forslag), dashbordet versjon 55 (se innslaget over).
1. Ny `helse.py` lager `helse.json` sist i ukekjøringen (kalles fra
   `bygg_shipping.py` etter endringer). Én rad per serie: siste observasjon,
   frekvens, forventet etterslep (dager fra periodens slutt til tallet er på
   bordet, onsdagsinnhentingen regnet med) og periodens slutt. Status regnes
   på dashbordet mot dagens dato: grønn til forventet dato pluss 3 dager, gul
   til pluss 7, rød over det. Da blir alt gult og rødt også hvis selve
   innhentingen stopper. Etterslepene står i toppen av `helse.py` (Pink Sheet
   14, speilene 10, FRED 24, KPI-speilet 45, COT 9, Fearnleys 7, daglige kurser
   2, kvartalsvis 5, OWID 300 og laksekostnad 350). FEIL i loggen i
   `index.json` blir røde rader.
2. `c_manuell.json` og `b_manuell.json` leses, ikke endres: én rad per selskap,
   rød når siste regnskapsår sluttet for mer enn 15 måneder siden.
   Regnskapsårets slutt fra feltet `regnskapsaar` (B) eller «31. <måned>» i
   `kilde` (C, gir mars for CIA.TO), ellers desember.
3. Kort varsel helt øverst bare når noe er gult eller rødt, hele tabellen
   nederst (Datahelse) med kolonnen Automatisk/Manuell. I dag er alle 58 rader
   grønne, så varselet vises ikke.
4. «24 av 43 aksjer» i forklaringen og varselboksen regnes nå fra
   instrumentene i databasen (aksjer med port åpen eller stengt): 30 av 54 i
   dag. Teksten nevner også at noen selskaper er lest for hånd.
5. `shipping.py` arkiverer hver Fearnleys-rapport den laster ned som PDF i
   `arkiv/fearnleys/<dato>.pdf` (rundt 450 kB). Rapporter som allerede er lest,
   arkiveres ikke bakover, men de 41 som ikke kunne leses lastes ned på nytt
   hver uke og blir derfor arkivert ved neste kjøring (rundt 18 MB én gang).
   Ingen andre råfiler arkiveres.
Også: korrelasjonstabellen fra versjon 53 gjorde hele siden bredere enn
skjermen (1395 px på 1200). `#korr` har fått overflow-x:auto.
**Filer:** `helse.py` (ny), `helse.json` (ny), `bygg_shipping.py`,
`shipping.py`; dashbordet.
**Cowork må vite:** Onsdagsrutinen skriver `helse.json` til databasen
(samlingen marked, dokumentet helse). Når du fører inn et nytt regnskapsår i
`c_manuell.json` eller `b_manuell.json`, går raden grønn neste onsdag. Et nytt
selskap i C med annet regnskapsår enn desember bør ha «31. <måned>» i `kilde`.

### 30.09.2026 10:36, Cowork
**Hva:** Dashbordet versjon 53: korrelasjonsmatrise mellom A-skårene nederst
(Frodes bestilling). Korrelasjon mellom månedlige endringer i A over de siste
36 månedene, parvis på felles måneder, minst 24 par. Farge fra mørk rød (−1)
til mørk grønn (+1), lite tall og pil for endringen mot matrisen en måned
tidligere. Segmenter med bare kvartalsdata regnes på kvartalsendringer over
tolv kvartaler og merkes k (ingen i dag). Skipssegmentene har ingen A og er
utenfor. Kontekst, ikke testet. Bygget på versjon 52.
**Filer:** ingen i repoet (dashbordet ligger som artifact).
**Den andre økten må vite:** Funksjonene heter renderKorr, korrSerie, korrPar
og kalles sist i render(). Kontrollert mot uavhengig utregning (Brent/WTI 0,94,
Brent/TTF 0,57, HH/kobber 0,21).

### 30.09.2026 08:11, Claude Code
**Hva:** Dashbordet versjon 52. Underteksten under overskriften Test-flagg er fjernet.
**Filer:** ingen i repoet (dashbordet ligger som artifact).
**Cowork må vite:** Ingenting.

### 30.09.2026 08:11, Claude Code
**Hva:** Dashbordet versjon 51. I test-flagg-seksjonen er teksten under
«Når det vurderes» gjort om til en utfellbar lenke, på samme måte som
«Bakgrunn». Vurderingskriteriet er ikke endret.
**Filer:** ingen i repoet (dashbordet ligger som artifact).
**Cowork må vite:** Ingenting.

### 30.09.2026 08:10, Claude Code
**Hva:** Onsdagsrutinen (trig_01HoJvyjwZRq5J4QNcXoFkr3) er oppdatert. Første
forsøk feilet, så innslaget kl. 08:03 var for tidlig ute med at prompten var
oppdatert. Det er rettet nå. Nytt steg 6d skriver `endringer.json` til dashbordets
database (marked/endringer). Steg 5 beskytter også `rigg_b`, og rapporten har
et eget punkt for ukens endringer. Den planlagte ukekjøringen (06:00 UTC) var
ikke startet kl. 08:10, fordi GitHub ofte forsinker planlagte kjøringer.
**Filer:** ingen i repoet (bare rutinen).
**Cowork må vite:** Ikke rør `endringer.json` eller `logg/endringer_snap.json`
for hånd. Bildene flyttes automatisk.

### 30.09.2026 08:03, Claude Code
**Hva:** Endringsboks for dashbordet (Frodes bestilling). Ny modul
`endringer.py`: hver ukekjøring lagrer et bilde av nøkkeltallene
(`logg/endringer_snap.json`) og sammenligner med forrige ISO-ukes bilde; de
ti største endringene og alle skifter (bunnsone, oppsikt, d95, port, trend)
skrives til `endringer.json`. Kvartalskjøringen gjør det samme for C (kvartaler,
netto gjeld/EK, port), B per metall og rigg-B. Priser og nivåer rangeres
etter prosent, skårer etter poeng, forholdstall etter endring ganger 100.
Kalles sist i `bygg_shipping.py` (uke) og sist i `overlevelse_c.py`
(kvartal, ikke når en sonde kjører den). Første bilder er laget fra
git-historikken: uke fra 28.09 11.23 UTC (eldste lagrede kjøring), kvartal
fra 28.09 11.48 UTC mot 29.09 13.43 UTC.
**Filer:** `endringer.py` (ny), `bygg_shipping.py`, `overlevelse_c.py`,
`endringer.json` (ny), `logg/endringer_snap.json` (ny).
**Den andre økten må vite:** Onsdagsjobben må skrive `endringer.json` til
databasen (samlingen marked, dokumentet endringer); prompten er oppdatert.

### 29.09.2026 21:49, Claude Code
**Hva:** Nytt test-flagg på dashbordet (Frodes beslutning): «Høy tilbudsskår
og kapitulerte papirer». Utløses når B2 er over 50 og D for papirene alene
(`d_detalj.D_aksjer`, uten fondet) er 60 eller mer. Gjelder aluminium, gull,
jernmalm, kobber, kull, uran og oljeservice (høyeste B2 blant
riggsegmentene). Kriterium satt før noe tilfelle: vurderes etter tre
tilfeller; støttet hvis papirene slår ACWI over tolv måneder i minst to av
tre. Ingen segmenter utløser nå (høyest D for papirene: aluminium 45).
Flaggloggen logger nå også `D_pap` og `B2_rigg` hver uke, så flagget kan
etterprøves.
**Filer:** `flagglogg.py`; dashbordet.
**Den andre økten må vite:** `logg/flagg_uke.csv` får to nye kolonner fra
onsdag.

### 29.09.2026 21:45, Claude Code
**Hva:** Test av B2 og kapitulasjon D som kjøpssignal (Frodes bestilling),
`sonde_kjor_b_signal.py`, regler og kriterium satt i fila før kjøring. Ni
segmenter (seks metaller, tre riggsegmenter), inngang i april året etter B,
avkastning mot verdensindeksen, høy gruppe mot lav per inngangsår.
Resultat på 12 mnd (avgjør), med sjansen for minst like mange positive år ved
myntkast:
- B2 over 50: positiv 8 av 14 år, snitt +3,1 pp; uten 2020-21 7 av 12,
  +10,5 pp. Holder etter kriteriet, men svakt (myntkast 0,40).
- D papirene 60+: 11 av 16, +22,1 pp; uten 2020-21 9 av 14, +11,7 pp. Holder
  (myntkast 0,11). På 24 mnd snur det: 7 av 15, uten 2020-21 -8,0 pp.
- D fondet 60+: 4 av 12. Holder ikke.
- B2 over 50 og D papirene 60+: 9 av 13, +24,6 pp; uten 2020-21 7 av 11,
  +19,5 pp. Holder (myntkast 0,13).
Forbehold: 2012 til 2016 er høy B2 bare aluminium, og fra 2020 er lav B2
bare kobber og jernmalm. B-kurvene og papirene er dagens overlevere.
SHLF.OL (Shelf Drilling) fantes ikke på Yahoo.
**Filer:** `sonde_kjor_b_signal.py` (ny), `sonder/sonde_kjor_b_signal.txt`,
`sonder/b_signal.csv`, `sonder_ferdige.txt`.
**Den andre økten må vite:** Ingenting på dashbordet er endret.

### 29.09.2026 16:59, Claude Code
**Hva:** Dashbordet publisert som versjon 48 (tekst om anslått slitasje), og
oljeservice i databasen oppdatert med B for rigger etter regel B (versjon 4).
**Filer:** Ingen i repoet; dashbordet og databasen.
**Den andre økten må vite:** Ingenting.

### 29.09.2026 16:58, Claude Code
**Hva:** Test B (anslått slitasje) besto kriteriet satt før kjøring og er tatt
i bruk i `rigg_b.py` (Frodes beslutning: gjør A, test B). Kontrollen på 33
rene år: median feil 17,1 % (krav 20), 80-persentil 28,6 % (krav 35); med
bare rapporterte riggtall 16,7 og 25,0 på 25 år. Regel A ligger i bunn: år
etter ny startbalanse tas ut; for Valaris og Diamond fra 2021 legges
investeringene inn igjen med anslått slitasje (avskrivning per rigg de tre
siste rene årene ganger riggtall ved årsslutt, fra XBRL). Pacific Drilling
fra 2018 er holdt utenfor (ingen riggtall).
Tall 2025, bare A mot A pluss B: grunt vann B2 100 til 80 (forhold 0,60 til
1,04; Borr og Valaris), dypt vann B2 100 til 100 (0,19 til 0,31; Transocean
og Valaris). Land uendret (81,7). Valaris' anslåtte slitasje 2025: flytere
214 mill. mot faktisk avskrivning 60, jackups 121 mot 59.
`b_rigg.json` skrevet lokalt (GitHub-tilkoblingen var nede i Actions);
kvartalskjøringen lager den på nytt. Utskriften av sonden er lagret i
`sonder/sonde_kjor_rigg_slitasje.txt`.
**Filer:** `rigg_b.py`, `b_rigg.json`, `sonder/sonde_kjor_rigg_slitasje.txt`,
`sonder_ferdige.txt`.
**Den andre økten må vite:** Dashbordteksten er oppdatert.

### 29.09.2026 16:51, Claude Code
**Hva:** Regel A for B for rigger (Frodes beslutning): alle år etter ny
startbalanse holdes utenfor, ikke bare Valaris. `UTELAT_FRA` i `rigg_b.py`:
Valaris 2021, Diamond 2021, Pacific Drilling 2018, Hercules 2015, Paragon
2017. Kilde: SECs fulltekstsøk etter "fresh start accounting" i
årsrapportene og XBRL-begrepene FreshStart*; Transocean, Borr, Rowan, Ocean
Rig og landselskapene hadde ingen treff. Tallene kjøres og føres når test B
er ferdig. Ny sonde `sonde_kjor_rigg_slitasje.py` (test B): beholder
investeringene og bytter avskrivningene etter ny startbalanse med anslått
slitasje (avskrivning per rigg før restruktureringen ganger riggtall).
Kriteriet for å ta B i bruk står i fila, satt før kjøring.
**Filer:** `rigg_b.py`, `sonde_kjor_rigg_slitasje.py` (ny).
**Den andre økten må vite:** Ingenting er publisert ennå.

### 29.09.2026 15:44, Claude Code
**Hva:** Kvartalsvis innhenting kjørt; `b_rigg.json` har nå grunt vann B2 100
(Borr) og dypt vann B2 100 (Transocean), land 81,7. Dashbordet er publisert
som versjon 47 med ny tekst om Valaris, og oljeservice i databasen er
oppdatert med de nye tallene (versjon 3). `segments/oljeservice.json` i
repoet får dem ved den ukentlige kjøringen onsdag.
**Filer:** Ingen i repoet; dashbordet og databasen.
**Den andre økten må vite:** Ingenting.

### 29.09.2026 15:41, Claude Code
**Hva:** Valaris tatt ut av B for rigger fra 2021 (Frodes beslutning,
`UTELAT_FRA` i `rigg_b.py`). Riggene ble skrevet ned ved konkursen, så
avskrivningene er kunstig lave (flytere 2025: 60 mill. i avskrivninger på 1,2
mrd. i bokført verdi). Før og etter, 2025: grunt vann B2 35 til 100 (forhold
1,36 til 0,60, nå bare Borr), dypt vann B2 86 til 100 (0,37 til 0,19, nå bare
Transocean). Land og årene før 2021 er uendret. Teksten på dashbordet er
oppdatert.
**Filer:** `rigg_b.py`.
**Den andre økten må vite:** Offshore hviler nå på ett selskap per segment.

### 29.09.2026 15:21, Claude Code
**Hva:** Kvartalsvis og ukentlig innhenting kjørt. `b_rigg.json` skrevet av
Actions (land B2 81,7, grunt 35,3, dyp 85,5; to selskaper hver i 2025).
`segments/oljeservice.json` har feltet `rigg_b`. Dashbordet er publisert som
versjon 46 med linjen «Tilbud B, rigger», og oljeservice er skrevet til
databasen (versjon 2).
**Filer:** Ingen i repoet; dashbordet og databasen.
**Den andre økten må vite:** Ingenting.

### 29.09.2026 15:13, Claude Code
**Hva:** B for rigger er i drift (Frodes beslutning), som informasjon i
oljeservicepanelet. Ny modul `rigg_b.py` regner investeringer delt på
avskrivninger for land, grunt vann (jackups) og dypt vann (flytere) hver for
seg: rene selskaper fra SECs samlede data pluss segmenttall fra årsrapportene
til Valaris, Seadrill og Rowan. Nytt fra sondene: Diamond (2007 til 2023)
og Ocean Rig (2014 til 2017) er med etter at begrepene
CostOfServicesDepreciation, CostOfGoodsAndServicesSoldDepreciation og
PaymentsForProceedsFromProductiveAssets ble lagt til. Patterson-UTI er holdt
utenfor, fordi selskapet fører avskrivninger og nedskrivninger samlet.
Lokalt: land B2 82 (forhold 0,90 i 2025, 2 selskaper), grunt 35 (1,36, 2),
dyp 86 (0,37, 2). Kjøres kvartalsvis fra slutten av `tilbud_b.py` (hoppes
over når en sonde kjører den) og skriver `b_rigg.json`. `priser.py` legger
tallene i `oljeservice.rigg_b`. Dashbordet viser en linje «Tilbud B,
rigger» i panelet og et avsnitt i forklaringen.
**Filer:** `rigg_b.py` (ny), `tilbud_b.py`, `priser.py`; `b_rigg.json` skrives
av Actions.
**Den andre økten må vite:** B for rigger står ikke i `scores.B` og ikke i
oversikten. `tilbud_b.py` tar nå rundt ett minutt lenger.

### 29.09.2026 15:01, Claude Code
**Hva:** `sonde_kjor_rigg_segment.py` kjørt lokalt og rettet. Segmenttall
funnet for Valaris/Ensco (flytere og jackups 2009 til 2025, unntatt 2021, som
er delt i to perioder av konkursen), Seadrill (2011 til 2021) og Rowan (2014
til 2018). Noble, Transocean, Atwood, Pride og Vantage rapporterer ett
segment. Kontrollen besto for begge: forhold 2011 til 2014 rundt 2,8, og
2016 til 2021 0,41 (dyp) og 0,49 (grunt). Siste B2: dyp 84, grunt 35 (Borrs
nybygg og Valaris' reaktiveringer). Rettet: Rowan ble talt to ganger i 2014
til 2018; nå brukes segmenttallene når de finnes. Tidligere retting: bredere
begreper for avskrivninger (Ensco brukte CostOfGoodsAndServicesSoldDepreciation)
og riktig XBRL-fil for eldre rapporter. Sonden legges på main og kjøres i
Actions for utskrift i `sonder/`.
**Filer:** `sonde_kjor_rigg_segment.py`.
**Den andre økten må vite:** Ingenting er bygget på dashbordet.

### 29.09.2026 14:56, Claude Code
**Hva:** Ny sonde `sonde_kjor_rigg_segment.py` (Frodes bestilling): henter
segmenttall (flytere og jackups) fra XBRL-filene til årsrapportene for de
blandede riggselskapene og legger dem sammen med de rene selskapene fra
`sonde_kjor_rigg_b`. Klassifisering og kontroll står i fila, satt før
kjøring. Ligger foreløpig bare på arbeidsgrenen; kjøres lokalt nå.
**Filer:** `sonde_kjor_rigg_segment.py` (ny).
**Den andre økten må vite:** Ingenting er bygget på dashbordet.

### 29.09.2026 14:52, Claude Code
**Hva:** Ny sonde `sonde_kjor_rigg_b.py` (Frodes bestilling): B for rigger som
capex delt på avskrivninger fra SEC, delt i land, grunt vann (jackups) og
dypt vann (flytere). Bare rene selskaper teller; blandede vises for seg.
Konkursrammede er med (CIK fra SECs liste over bransjekode 1381). Kjørt lokalt:
- Dypt vann følger kjent historie på investeringene: forhold 1,64 i 2011 til
  2014 og 0,49 i 2016 til 2021. Nedskrivningene besto ikke kontrollen, fordi
  Transoceans nedskrivninger i XBRL blander inn goodwill. De kan ikke brukes.
- Siste B2: land 82, grunt 100, dyp 100 (2025).
- Dekningen er tynn: etter 2019 er dypt vann bare Transocean og grunt vann
  bare Borr. Patterson-UTI, Diamond og Ocean Rig mangler standardbegreper for
  avskrivninger eller capex.
- De blandede selskapene (Valaris, Noble, Seadrill) er nå flertallet
  offshore, og Valaris viser forhold over 2 i 2022 til 2024 fordi
  avskrivningene falt etter konkursen (ny startbalanse). Det svekker
  forholdet som mål rett etter en restrukturering.
To feil i sonden rettet før tallene over, og skrevet i fila: goodwill ut av
nedskrivningene, og år før riggene var i drift utelatt (Pacific Drilling
2009 til 2011 hadde forhold over 500).
**Filer:** `sonde_kjor_rigg_b.py` (ny).
**Den andre økten må vite:** Ingenting er bygget på dashbordet.

### 29.09.2026 14:40, Cowork
**Hva:** Etterført innslag for to Cowork-endringer som ble pushet uten innslag
i dag (den siste er commit 4ea249b):
1. Fire papirer lagt i C fra årsrapporter etter navnekontrollen: Champion Iron
   (CIA.TO), Labrador Iron Ore Royalty (LIF.TO), Air Liquide (AI.PA) og
   Heidelberg Materials (HEI.DE). Produksjonsstart (Frodes beslutning): feltet
   `produksjon_fra`; `c_manuell.py` utelater driftsår før det. Champion fra
   FY2019 (Bloom Lake satt i drift igjen i februar 2018); uten regelen ville
   porten vært stengt (6,0 kvartaler fra FY2018).
2. Renteregelen i `c_manuell.py`, samme regel som SEC-delen: feltet
   `renter_i_drift` med `renter_kilde` (og `renter_i_drift_aar` for unntak),
   avgjort for bunnåret og siste år hver for seg. Mangler feltet, trekkes
   renten fra som før, og utskriften sier det. Vale lagt inn med Claude Codes
   tall fra 20-F (brukes foran SEC via `MANUELL_FORAN`).
**Filer:** `c_manuell.json`, `c_manuell.py` (begge pushet tidligere),
`notater/LOGG.md`.
**Den andre økten må vite:** Klassifisering lest av Cowork: DNO drift også i
bunnåret 2015 (Interest paid −31,6 i driftsdelen, årsrapport 2015 s. 20),
Heidelberg drift (Business Figures 2025), Champion drift (driften starter med
årsresultatet, ingen rentelinje under finansiering). Aker BP og Air Liquide
finansiering, LIF ingen renter, Vale drift. Bunnåret for Aker BP (2006), Air
Liquide og Heidelberg (2005) er ikke sjekket; portene er åpne uansett. Vales
2009 og 2011 er kontrollert mot SECs tall, resten er Claude Codes lesing.
Resultatet står i innslaget 14:16. Cowork fører heretter innslag i samme
commit som endringen.

### 29.09.2026 14:32, Claude Code
**Hva:** Oljeservice er i drift. Kvartalsvis og ukentlig innhenting kjørt:
`segments/oljeservice.json` har A 46,8, detrendet 98,8, D 21,5 (papirene 3,8
til 75,5, IEZ 20,8), C åpen (SLB og BKR åpne, HAL stengt), aktivitet 105,3
(persentil 37,7). Segmentet står i `index.json` (18 segmenter). Dokumentet er
skrevet rett inn i dashbordets database (samlingen segments, versjon 1), så
det vises før onsdagsjobben. Dashbordet er publisert som versjon 45: tittelen
på merket «Observasjon» hentes fra `scores.observasjon_grunn` (laks-teksten
står som reserve), raten skriver «av aktiviteten» for volumindekser, og
forklaringen har et avsnitt om oljeservice.
**Filer:** Ingen i repoet; dashbordet og databasen.
**Den andre økten må vite:** Onsdagsjobben vil skrive oljeservice til
databasen sammen med de andre, uten endringer i jobben.

### 29.09.2026 14:25, Claude Code
**Hva:** Nytt segment `oljeservice` (Frodes beslutning), observasjon uten
flagg, bygget i `priser.py` etter samme mønster som laks:
- Verdi: BLS produsentpris for boring av olje- og gassbrønner
  (PCU213111213111, fra 1985) via FRED, deflatert som resten. A 46,8,
  detrendet 98,8, rullende 78,3. Flagg og oppsikt er alltid av
  (`scores.observasjon`, med grunn i `scores.observasjon_grunn`).
- Rate: industriproduksjon for boring (IPN213111N, fra 1972): 105,3 i august,
  persentil 38, +9,2 % på tolv måneder.
- Papirer: OIH, XES, SLB, HAL, BKR, SUBC.OL, TGS.OL. Riggselskapene er
  utenfor (nye noteringer etter konkurs).
- D mot IEZ (`kapitulasjon_d.TEMA`). Lokalt: segment 21,5, papirene 4 til 76.
- C: `GJELD_STRENG = {"oljeservice": 1.5}` i `overlevelse_c.py`: netto
  gjeld over 1,5 ganger egenkapitalen stenger porten for selskaper i
  segmentet. Lokalt: SLB og BKR åpne, HAL stengt (5,2 kvartaler, bunnår
  2016). Subsea 7 og TGS er ikke hos SEC; TGS ble ellers koblet til et
  argentinsk gasselskap, men navnekontrollen stoppet det.
- FRED svarer ikke på nettleser-agent, så `fred_mnd` bruker en vanlig.
**Filer:** `priser.py`, `instrumenter.py`, `kapitulasjon_d.py`,
`overlevelse_c.py`.
**Den andre økten må vite:** Segmentet havner i `index.json`, så
onsdagsjobben skriver det til dashbordet. Det logges også i flaggloggen, men
får aldri tenkte kjøp. Subsea 7 og TGS kan legges i `c_manuell.json` hvis C
skal måles for dem. Dashbordet får en forklaring og riktig tekst for
observasjon og for aktivitet som rate.

### 29.09.2026 14:16, Claude Code
**Hva:** Kvartalsvis innhenting kjørt etter Coworks commit 4ea249b
(renteregel i `c_manuell.py`, feltet `renter_i_drift` for alle manuelt leste
selskaper, og Vale i `c_manuell.json`; ikke ført i loggen av Cowork). Porten
før (11.12 UTC) og etter (12.16 UTC):
- DNO: trang til åpen. 10,1 til 24,5 kvartaler, rentedekning -0,7 til 0,3.
  Betalte renter ligger i driften, så de ble tidligere trukket to ganger.
- Brent: åpen 1 av 2 til åpen 2 av 2 (Aker BP og DNO).
- Vale: åpen, uendret. Nå manuelle tall: drift 2007 til 2025, bunnår 2016 til
  2015, netto gjeld/EK 0,16 til 0,30 (gjelden er nå langsiktige lån 2025 i
  stedet for SEC-tallet fra 2022), rentedekning 5,9 til 5,5.
- Champion Iron og Heidelberg: port uendret (åpen), rentedekning +1,0.
- Aker BP, Air Liquide og Labrador: uendret (renter under finansiering eller
  ingen renter).
**Filer:** Ingen endret av Claude Code; `c_overlevelse.json` skrevet av Actions.
**Den andre økten må vite:** Dashbordet får portene etter onsdagskjøringen.

### 29.09.2026 14:01, Claude Code
**Hva:** Ny sonde `sonde_kjor_oljeservice.py` (Frodes bestilling): grunnlag
for et oljeservicesegment bygget som shippingsegmentene. Bygger ingenting.
Sjekker prisserie og indikator (FRED: produsentpris for boring og for
støttetjenester fra 1985, industriproduksjon for boring fra 1972; Baker Hughes
svarer 403), 25 papirer på Yahoo, driftskontantstrøm hos SEC for C, og
beskrivende avkastning mot SPY etter Brent-flagg, flagg i produsentprisen og
en aktivitetsbunn definert før kjøring. Kjørt lokalt først; hovedfunn i
svaret til Frode og i `sonder/sonde_kjor_oljeservice.txt` når Actions har
kjørt.
**Filer:** `sonde_kjor_oljeservice.py` (ny).
**Den andre økten må vite:** Ingen segmenter eller tall på dashbordet er
endret.

### 29.09.2026 13:14, Claude Code
**Hva:** Manuelle tall kan nå erstatte SEC-tallene i C for utvalgte papirer
(Frodes beslutning). Ny mengde `MANUELL_FORAN = {"VALE"}` i
`overlevelse_c.py`. Har `c_manuell.json` en post for et slikt papir, og den gir
en måling, brukes den i stedet for SEC-tallene, og utskriften viser porten
fra begge. Uten post står SEC som før. Ingen tall endres før Cowork har lagt
inn Vale.
**Filer:** `overlevelse_c.py`.
**Den andre økten må vite:** Cowork bes legge inn "VALE" i `c_manuell.json` i
samme format som de andre: driftskontantstrøm per år i USD (helst hele
historikken, minst 2022 til 2025, som mangler hos SEC), og siste år med
kontanter, langsiktig gjeld, egenkapital og betalte renter, med kilde. NB:
Vale fører betalte renter under drift (IFRS-begrepet
InterestPaidClassifiedAsOperatingActivities finnes hos SEC til 2022).
`c_manuell.py` trekker renten fra driften en gang til, så for Vale bør
renten enten føres som null eller regelen i `c_manuell.py` justeres; ellers
telles den dobbelt. `c_manuell.py` og `c_manuell.json` er ikke rørt av
Claude Code.

### 29.09.2026 13:11, Claude Code
**Hva:** Tallene fra `sonde_kjor_c_spleis` (før og etter skjøting av begreper
i C) og `sonde_kjor_vale`. Ingen porter endret.
Frontline: tall til 2025 (før 2021). Kontanter 113 til 251 mill. USD, drift
siste år 63 til 682, netto gjeld/EK 1,22 til 0,99, bunnår fortsatt 2013.
Åpen før og etter.
Vale: drift til 2021 (før 2011), bunnår 2009 til 2016, verste drift 7 136
til 6 401 mill. USD, kontanter 5 832 til 7 372 (nå fra 2025), netto
gjeld/EK 0,07 til 0,16. Åpen før og etter. Driften for 2022 til 2025 finnes
ikke i SECs standardbegreper: Vale merker driftskontantstrømmen med et eget
begrep, som SECs datasett ikke tar med. Standardbegrepet som går til 2025
(drift før renter og skatt) er ikke brukt, fordi det måler noe annet.
Andre selskaper, samme port før og etter: PANL får drift fra 2013 (bunnår
2016, verste drift 19 mot 21), Hershey får nyere kontanter (588 til 926), og
rentedekning eller netto gjeld/EK endres litt for AA, ARLP, CENX, EQT, GNK,
NAT, TORM og UUUU fordi siste rente- eller balansetall nå er fra et nyere år.
Skjøtingen er tatt inn på main.
**Filer:** `overlevelse_c.py` (fra forrige innslag), `sonder_ferdige.txt`,
`sonde_kjor_vale.py` (ny).
**Den andre økten må vite:** `c_manuell.py` måler bare papirer som mangler
SEC-tall, så Vale kan ikke leses manuelt uten en endring der.

### 29.09.2026 13:08, Claude Code
**Hva:** Retting av utdaterte tall i C for selskaper som har byttet
regnskapsstandard (Frodes bestilling: oppdaterte tall for Vale og Frontline).
C valgte første begrep med minst fire år. Vale gikk fra US GAAP til IFRS i
2012 og Frontline i 2022, så C regnet på kontanter og drift fra 2011 og 2021.
Nå skjøtes begrepene: det første i rangeringen bestemmer valutaen, og de
neste fyller inn år som mangler (`aarsserie_spleis`). Renteregelen avgjøres
per år ut fra hvilket begrep året er lest fra, for bunnåret og for siste år
hver for seg. `SPLEIS=0` gir gammel regel. Ny sonde `sonde_kjor_c_spleis.py`
viser før og etter for alle SEC-selskaper; tallene føres i neste innslag.
Endringen går ikke til main før tallene er sett.
**Filer:** `overlevelse_c.py`, `sonde_kjor_c_spleis.py` (ny).
**Den andre økten må vite:** Skjøtingen kan også endre andre selskaper, der
hull i ett begrep fylles fra et annet. Sonden viser hvilke.

### 29.09.2026 12:56, Claude Code
**Hva:** Produksjonsstart i SEC-delen av C (Frodes beslutning, samme regel som
Coworks `c_manuell.py`). `sonde_kjor_c_produksjon` listet alle SEC-selskaper
med bunnår og omsetning det året og siste år. Sju kandidater:
- HSHP.OL: bunnår 2022, omsetning 0 mot 132 mill. USD i 2025. Reell kandidat.
- ARLP (bunnår 2008), EQT (2007), HSY (2008), NAT (2013), PANL (2020) og TNK
  (2021): flagget bare fordi omsetningsbegrepet mangler for bunnåret hos
  SEC. Alle var i drift da (driften var positiv i bunnåret for ARLP, EQT, HSY
  og PANL; NAT og TNK hadde omsetning i årene rundt). Ingen endring.
Ingen andre selskaper hadde omsetning under ti prosent av siste år i bunnåret.
Lagt inn: HSHP.OL fra 2024. Kilde: 20-F for 2023 (lenke i
`PRODUKSJON_FRA` i `overlevelse_c.py`), "the first six vessels being
delivered during the year ended December 31, 2023, and commencing operations
shortly after". Driften startet i 2023, så første hele år er 2024.
Utelatt: 2022 og 2023.
Port før og etter: Himalaya går fra trang (89,6 kvartaler, men netto gjeld
3,92 ganger egenkapitalen) til ikke målt, fordi bare 2024 og 2025 står
igjen, og C krever minst fire år (samme som i `c_manuell.py`). Capesize går
fra åpen 1 av 2 til åpen 1 av 1 (bare SBLK). Ingen andre selskaper endres.
**Filer:** `overlevelse_c.py`, `sonder_ferdige.txt`.
**Den andre økten må vite:** Himalaya havner i listen `utenfor_sec` i
`c_overlevelse.json` selv om den finnes hos SEC; grunnen står i utskriften.
Sonden fant også data som har sluttet å oppdateres hos SEC: Vale (drift
2007 til 2011), Frontline (til 2021) og omsetningen for Century (til 2018).
C for Vale og Frontline bygger altså på gamle år. Det er ikke rettet.
`c_manuell.json` og `c_manuell.py` er ikke rørt.

### 29.09.2026 12:52, Claude Code
**Hva:** (1) Kvartalsvis innhenting kjørt på nytt etter Coworks commit 7799ea5
(nye selskaper i `c_manuell.json` og regelen om produksjonsstart i
`c_manuell.py`, ikke ført i loggen). Jernmalm er igjen 3/3 åpne (Vale,
Champion Iron, Labrador Iron Ore) og TTF 3/3 åpne (Equinor, Air Liquide,
Heidelberg), nå med riktige selskaper lest manuelt. Champion Iron regnes fra
2019 (produksjon_fra). (2) Mekanismen for produksjonsstart i SEC-delen er lagt
inn i `overlevelse_c.py`: tabellen `PRODUKSJON_FRA` (ticker: første hele år,
kilde), foreløpig tom, så ingen tall endres. År før utelates og skrives ut.
Blir det færre enn fire driftsår igjen, måles selskapet ikke (som i
`c_manuell.py`). `PRODFIX=0` slår regelen av. Ny sonde
`sonde_kjor_c_produksjon.py` finner kandidatene (omsetning i bunnåret under
ti prosent av siste år) og henter setninger om produksjonsstart fra
årsrapportene hos SEC som kilde.
**Filer:** `overlevelse_c.py`, `sonde_kjor_c_produksjon.py` (ny).
**Den andre økten må vite:** `c_manuell.json` og `c_manuell.py` er ikke rørt.
Tabellen fylles først når sonden har vist kilder.

### 29.09.2026 12:27, Claude Code
**Hva:** Rettet klokkeslettene i de sju innslagene fra Claude Code i dag
mellom 12.02 og 12.24. De var ført med anslåtte tider (12.05 til 14.05) i
stedet for faktisk norsk tid. Nå følger de tidspunktene på commitene.
Innholdet er ikke endret.
**Filer:** `notater/LOGG.md`.
**Den andre økten må vite:** Rekkefølgen er uendret.

### 29.09.2026 12:24, Claude Code
**Hva:** Kvartalsvis innhenting kjørt manuelt (Frodes beslutning), slik at
rettelsene i C gjelder nå og ikke først i januar. Endringer i porten per
segment: aluminium trang til åpen (AA åpen), bly trang til åpen (Nexa),
suezmax trang til åpen (Frontline), VLCC 1/2 til 2/2 åpne, capesize uendret
åpen (Himalaya stengt til trang). Jernmalm måles nå bare på Vale (1/1, åpen),
fordi Champion Iron og Labrador Iron Ore var feil selskap. TTF måles bare på
Equinor (1/1, åpen), fordi Air Liquide og Heidelberg var feil selskap. B er
uendret: 2025 for alle seks metaller, samme forhold, B1 og B2 som før.
2020.OL og CMBT er ute av C.
**Filer:** Ingen endret av økten; `c_overlevelse.json` og `b_capex.json`
skrevet av Actions.
**Den andre økten må vite:** Dashbordet får de nye portene etter den ukentlige
kjøringen onsdag 07.00 UTC. Jernmalm og TTF hviler nå på ett selskap hver i C.
Air Liquide, Heidelberg, Champion Iron og Labrador Iron Ore kan legges i
`c_manuell.json` hvis de skal måles.

### 29.09.2026 12:16, Claude Code
**Hva:** Ukentlig innhenting kjørt manuelt igjen for å kontrollere flaggloggen
og hel måned for olje før onsdag. Alt virket: `logg/regel_6040.csv` og
`logg/dom.csv` er skrevet (begge "venter", ingen innslag ennå). Brent, WTI og
Henry Hub har nå siste observasjon 2026-08, ikke den uferdige september. A for
Brent gikk fra 18,0 til 32,6 og for WTI fra 24,9 til 30,7 av den grunn; ingen
flagg endret, ingen nye hendelser. WTI sitt tomme d95-felt fra 25.09 ga ikke
et falskt innslag.
**Filer:** Ingen endret av økten; data skrevet av Actions.
**Den andre økten må vite:** Oljesegmentene vil fra nå henge en måned etter
når innhentingen skjer før månedsslutt. Det er meningen.

### 29.09.2026 12:10, Claude Code
**Hva:** Tallene fra sondene for C, B og punkt 5.
C (`sonder/sonde_kjor_c_rente.txt`), før og etter rentefiksen og
navnekontrollen: fire porter endret. AA trang til åpen (13,6 til 20,5
kvartaler), Frontline trang til åpen (positiv drift etter renter), Nexa trang
til åpen, Himalaya Shipping stengt til trang. BTU, CENX, GNK, NAT, SBLK og TNK
fikk flere kvartaler uten portendring. AI.PA, HEI.DE, LIF.TO og CIA.TO er
borte fra SEC-delen (feil selskap før). Rentedekningen stiger med 1,0 for alle
der renten nå regnes som del av driften.
B (`sonder/sonde_kjor_b_dda.txt`): ingen selskaper byttet nevner. Begrepet
med nedskrivninger ble ikke valgt for noe SEC-selskap, så B er uendret
(aluminium 1,021, gull 1,189, jernmalm 1,593, kobber 1,87, kull 0,986, uran
1,181). Rettelsen er et vern, ikke en endring i dagens tall.
Punkt 5 (`sonder/sonde_kjor_regel_foer2011.txt`), bransjene før 2011-09, 22
innslag, 16 episoder, mot det amerikanske markedet:
H3 (kjøp T+1, selg T+4): S -1,6 %, 9 av 16 positive, p 0,73. **Består ikke.**
60/40 på 24 mnd: S -3,7 %, 9 av 16 positive, p 0,82. **Består ikke.**
Også fra 2011-09 er bransjene negative (H3 S -1,6 %, 2 av 6). Norge før 2012:
to innslag, H3 +3,7 % og +1,3 %, 60/40 24 mnd +2,8 % og -14,9 %.
**Filer:** `sonder_ferdige.txt`, `notater/2026-09-28_backtest.md` (nytt
tillegg).
**Den andre økten må vite:** Den korte hypotesen har ikke støtte utenfor
tavlens papirer. Det positive 3-månedersresultatet på papirene (+8,4 % mot
eget snitt ved T+1) finnes ikke i bransjeporteføljene, verken før eller etter
2011. Loggen framover står uendret som test, men forventningen bør være lav.

### 29.09.2026 12:08, Claude Code
**Hva:** (1) C: navnekontroll når børssuffikset strippes før oppslag hos SEC.
Fire papirer var koblet til feil selskap siden C ble laget: Air Liquide
(AI.PA) ble lest som C3.ai, Heidelberg Materials (HEI.DE) som HEICO, Labrador
Iron Ore Royalty (LIF.TO) som Life360 og Champion Iron (CIA.TO) som Citizens
Inc. Nå må navnet hos SEC dele et ord med navnet på tavlen. De fire får
"ukjent" fra SEC-delen, med mindre `c_manuell.json` har dem. Funnet i
sonden for rentefiksen; ført her etter commit 5c381fa, som manglet innslag.
(2) Ny sonde `sonde_kjor_regel_foer2011.py` (punkt 5): hypotesen T+1/3 mnd
og regel 60/40 testet på Ken French-bransjer (og landene Norge og Australia)
før 2011-09. Regler, mål og beslutningskriterium står i hodet av fila og er
skrevet før kjøring.
**Filer:** `overlevelse_c.py`, `sonde_kjor_regel_foer2011.py` (ny),
`sonder_ferdige.txt` (b_dda ferdig).
**Den andre økten må vite:** Porten for segmentene med AI.PA, HEI.DE, LIF.TO
og CIA.TO kan endre seg ved neste kvartalsvise kjøring. Tallene har vært feil
til nå.

### 29.09.2026 12:06, Claude Code
**Hva:** Hullene i flaggloggen fra den uavhengige gjennomgangen er tettet, og
Frodes praktiske salgsregel 60/40 er lagt inn som egen regel. Alt er skrevet
ned før noe utfall finnes.
1. Pause: tenkte kjøp logges bare ved et nytt innslag (første bunnsonemåned
   etter mer enn tolv uten flagg), sjekket mot segmentets månedsserie og
   `flagg_uke.csv`. En ny start innen tolv måneder logges som
   `bunnsone_start` med merknad, uten tenkte kjøp.
2. Papirene fryses ved innslaget: papirer med tenkt kjøp siste 26 måneder
   logges videre selv om de tas av tavlen.
3. Episoder (høyst 183 dager mellom flaggdatoer, på tvers av segmenter), og
   hvert papir telles én gang per episode.
4. Dommen regnes i koden og skrives til `logg/dom.csv`: de fem første ferdige
   episodene, bekreftet ved minst fire av fem positive, forkastet så snart to
   er negative. "Eller 80 % hvis flere" er tatt ut. Sjansen for "bekreftet"
   ved null effekt er rundt 19 %.
5. Tomt d95-felt forrige uke leses som ukjent, ikke nei (WTI).
6. Regel 60/40: kjøp som hypotesen (T+1), selg 60 % etter 3 måneder, 40 %
   måles ved 12 og 24 måneder. Mål: 0,6 x (papir minus ACWI, 3 mnd) + 0,4 x
   (papir minus ACWI, 12 eller 24 mnd). Dom på 24 mnd. `logg/regel_6040.csv`.
7. Oljeflagget på hele måneder: `priser.py` kaster siste måned for
   dagsseriene (Brent, WTI, Henry Hub) hvis den ikke er ferdig. Siste
   observasjon for disse vil derfor ofte være forrige måned.
**Filer:** `flagglogg.py`, `priser.py`; nye loggfiler `logg/regel_6040.csv` og
`logg/dom.csv` (skrives onsdag); `logg/hypotese_3mnd.csv` får kolonnen episode.
**Den andre økten må vite:** A, flagg og persentiler for Brent, WTI og Henry
Hub kan flytte seg litt fordi den uferdige måneden ikke lenger telles med.
Testet lokalt med oppdiktede kurser (pause, dobbeltpapir, dom); første ekte
kjøring er onsdag.

### 29.09.2026 12:03, Claude Code
**Hva:** Rettet to feil fra den uavhengige gjennomgangen, med sonder som
viser tallene før og etter. Tallene føres i et eget innslag når sondene har
kjørt.
C: renter ble trukket fra driftskontantstrømmen også for US GAAP-filere, der
de allerede er trukket (dobbelttelling). Nå trekkes renter bare når driften
er lest fra IFRS og selskapet ikke oppgir betalte renter under drift.
Rentedekningen regnes nå på drift før renter. Nye felt per selskap:
`renter_i_drift`, `rentegrunn`. `RENTEFIX=0` gir gammel regel.
B: begrepet "avskrivninger og nedskrivninger" sto som nummer to i nevneren
og vant over rene avskrivninger for IFRS-filere. Nedskrivninger kommer i
bunnårene og trekker B ned. Nå er det nest siste utvei. `B_DDA=gammel` gir
gammel rekkefølge.
**Filer:** `overlevelse_c.py`, `tilbud_b.py`, `sonde_kjor_c_rente.py` (ny),
`sonde_kjor_b_dda.py` (ny).
**Den andre økten må vite:** `b_manuell.json` og `c_manuell.json` er ikke
rørt. `c_manuell.py` trekker fortsatt renter fra driften for de manuelt
leste selskapene. Det er riktig bare hvis årsrapporten fører betalte renter
under finansiering. Fører den dem under drift (vanlig i IFRS, IAS 7 tillater
begge), telles renten to ganger der også. Cowork bør sjekke det per selskap.

### 29.09.2026 12:02, Claude Code
**Hva:** Rettet tre formuleringer i backtestnotatet etter den uavhengige
gjennomgangen. Ingen tall endret. "Alle etter 2008" var feil (episodene 1991,
1998 og 2000 er med). "Båret av 2009 og 2020" er nå "2008/09 og 2020".
"Flagget er ikke tilbakevist" er erstattet med at flagget ikke har vist verdi
for aksjer på data uten overlevelsesskjevhet. Innslaget 28.09 kl. 18.19 under
sa "resultatet fra 2011 til 2026 bæres av 2009 og 2020"; det henger ikke
sammen og skal leses som: papirresultatet (episoder 1991 til 2023) bæres av
2008/09 og 2020.
**Filer:** `notater/2026-09-28_backtest.md` (ny seksjon "Rettelser 29.09.2026").
**Den andre økten må vite:** Bruk den nye konklusjonen hvis flagget omtales i
dashbordet eller notater.

### 29.09.2026 11:41, Claude Code
**Hva:** Ukentlig innhenting kjørt manuelt 29.09 og kontrollert. Alt nytt fra
28. og 29.09 virker: utbytte og dollarkurs i `logg/kurser_uke.csv`, B og Ar i
`logg/flagg_uke.csv`, `logg/hypotese_3mnd.csv` opprettet (tom), COT for
palmeolje (7 av 7 kontrakter), `B_forhold` og `B_aar` i segmentene,
2020.OL ute av D, CMBT på tavlen for capesize og utenfor D og C.
**Filer:** Ingen endret av denne økten; data skrevet av Actions.
**Den andre økten må vite:** Retting av innslaget om CMBT kl. 11.24: CMBT
logges ikke i flaggloggen, fordi flaggloggen hopper over skipssegmentene.
`c_overlevelse.json` har fortsatt 2020.OL til den kvartalsvise kjøringen,
men capesize-porten regnes bare av papirene på tavlen, så det påvirker ikke
noe. D for capesize hviler nå på ett papir (SBLK, D 6,7) pluss BDRY, fordi
HSHP.OL ikke har D-tall. Denne ukens linjer blir erstattet av onsdagens kjøring.

### 29.09.2026 11:34, Claude Code
**Hva:** COT for palmeolje lagt inn (Frodes valg), og to forsøk på SGX sin
COT for jernmalm. Palmeolje: CFTC-kontrakt 037021, CME «USD Malaysian Crude
Palm Oil Calendar», ukentlig fra september 2021; sonden ga et fullstendig felt.
SGX: rapporten lastes av en app som henter filer via et GraphQL-grensesnitt
med en skjult versjonsnøkkel; ingen fil eller adresse lot seg finne. Gitt opp.
**Filer:** `signaler.py` (`KONTRAKTER["palmeolje"]`), `priser.py` (teller
kontraktene i stedet for fast 6), `sonde_kjor_cot_palme_sgx.py` og
`sonde_kjor_sgx_cot.py` (nye), `sonder_ferdige.txt`. Dashbordet versjon 44:
forklaringsteksten om COT sier nå sju segmenter og hvorfor resten mangler.
**Den andre økten må vite:** Palmeolje får COT-feltet fra onsdagens kjøring.
Dashbordet trenger ingen annen endring; COT-feltet tegnes for alle segmenter
som har det. Bygg videre på versjon 44.

### 29.09.2026 11:29, Claude Code
**Hva:** Sonde for posisjonstall (COT) til segmentene som mangler det. Bygger
ingenting.
**Filer:** `sonde_kjor_cotr.py` (ny), `sonder/sonde_kjor_cotr.txt`,
`sonder_ferdige.txt`.
**Den andre økten må vite:** CFTC har palmeolje (CME «USD Malaysian Crude
Palm Oil Calendar», ukentlig fra mai 2022 til nå), nok til treårspersentil.
Aluminium hos COMEX stoppet i juni 2026, og resten av CFTC-kontraktene for
jernmalm, kull og TTF er nedlagt. Ingen CFTC-tall for nikkel, sink, bly,
tinn eller uran. LME COTR svarer 403 (Cloudflare) fra GitHub Actions, så det
kan ikke hentes automatisk derfra. ICE Futures Europe sine COT-filer
(COTHist) har bare Brent, gasolje, kakao og lignende, ikke kull eller TTF.
SGX sin COT-side for jernmalm er en JavaScript-app uten direkte filer.

### 29.09.2026 11:24, Claude Code
**Hva:** CMB.TECH (CMBT, NYSE) tatt inn på tavlen for capesize, merket «ny
sammensetning, ikke målt» (Frodes beslutning, alternativ 1). Holdes utenfor
kapitulasjon D og overlevelsesporten C, fordi kurshistorikken hos Yahoo er
Euronav (tankskip) og begge måles mot papirets egen historikk.
**Filer:** `instrumenter.py` (ny linje under capesize, og ny ordbok
`UTEN_HISTORIKK`), `kapitulasjon_d.py` og `overlevelse_c.py` (hopper over
papirer i `UTEN_HISTORIKK`).
**Den andre økten må vite:** `UTEN_HISTORIKK` i `instrumenter.py` er stedet
for papirer der historikken tilhører et annet selskap. De vises på tavlen og
logges i flaggloggen, men teller ikke i D eller C. Capesize har nå HSHP.OL,
SBLK og CMBT; D og C for segmentet regnes av HSHP.OL og SBLK. Endringen
slår inn på dashbordet etter onsdagens kjøring. CMBT sto fra før bare i
`VEHICLES["torrlast"]` i `priser.py`, som referanse.

### 29.09.2026 11:18, Claude Code
**Hva:** 2020 Bulkers (2020.OL) tatt ut av tavlen for capesize og av
vehikkellaget (Frodes beslutning). Kursen hos Yahoo falt 97 % i april 2026
uten at adjclose fanget det, og det ga falsk kapitulasjon (D 95).
**Filer:** `instrumenter.py` (linjen fjernet, begrunnelse i kommentar),
`priser.py` (`VEHICLES["torrlast"]`). Arkivkopiene i
`syklusbordet-automatisering_4/` og gamle sonder er ikke rørt.
**Den andre økten må vite:** Capesize står nå med HSHP.OL og SBLK. D for
papiret og for capesize, porten C og dashbordet oppdateres ved neste ukentlige
kjøring (onsdag), fordi `kapitulasjon_d.py`, `bygg_shipping.py` og
`flagglogg.py` leser instrumentlisten. Til da viser dashbordet fortsatt
2020.OL. Kan tas inn igjen når kursdataene er rettet.

### 29.09.2026 11:01, Claude Code
**Hva:** Kontroll av utbytte for alle papirene (Frodes bestilling), og retting
av utbyttet i flaggloggen. Ny sonde `sonde_kjor_utbytte.py` sammenlignet
Yahoo sitt rapporterte utbytte med det Yahoo selv har justert kursen for, og
ettårs totalavkastning på tre måter, for 60 papirer.
**Filer:** `flagglogg.py` (`siste_kurs`), `sonde_kjor_utbytte.py` (ny),
`sonder/sonde_kjor_utbytte.txt`, `sonder_ferdige.txt`.
**Den andre økten må vite:**
1. Yahoo sitt rapporterte utbyttebeløp er i feil valuta eller enhet for ni
   papirer: i dollar for FRO.OL, HAFNI.OL, HSHP.OL, OET.OL, 2020.OL og
   TRMD-A.CO (kursen er i kroner), og i pund for GLEN.L, ATYM.L, MPE.L og
   TMIP.L (kursen er i pence). Flaggloggen brukte beløpet direkte fra
   29.09 og ville overvurdert utbyttet 7 til 100 ganger. Rettet før noe utbytte
   var logget: utbyttet regnes nå av justeringen i adjclose, i kursens egen
   valuta og enhet. Testet mot et konstruert tilfelle (1 USD blir 10 NOK).
2. Backtestene og kapitulasjon D bruker adjclose, og den er riktig for alle
   papirene unntatt 2020.OL. Små avvik (1 til 8 prosentpoeng over ett år for
   papirer med høyt utbytte, som NAT, DHT, AKRBP og EQNR) skyldes at adjclose
   reinvesterer utbyttet, ikke feil.
3. 2020.OL (2020 Bulkers) har et kursfall på 97 % i april 2026 som ikke er
   fanget av adjclose (ettårs totalavkastning minus 95 % justert, +10 % med kurs
   og utbytte). Trolig en stor utdeling som Yahoo ikke har justert for. D for
   papiret (95) og dermed D for capesize er sannsynligvis falsk. Ikke rettet;
   venter på Frodes beslutning.
4. Akkumulerende fond (IOGP.L, GDX.L, GJGB.L, SPGP.L, EXV6.DE) har ingen
   utbytter, som ventet.

### 29.09.2026 10:54, Claude Code
**Hva:** Kriterium for når test-flagget «Bunnsone og høy tilbudsskår» vurderes,
skrevet ned før noe tilfelle (Frodes beslutning). Vurderes etter tre utløste
tilfeller. Et tilfelle er første utløste måned etter mer enn tolv måneder uten,
og tilfeller i ulike segmenter med høyst seks måneder mellom telles som ett.
Støttet hvis tavlens papirer for segmentet, likt vektet, slår ACWI over tolv
måneder fra utløsningen i minst to av tre tilfeller, i dollar med utbytte på
kursene i flaggloggen. Ellers forkastet. Kriteriet skal ikke flyttes.
**Filer:** Dashbordet (artifact Syklusbordet, versjon 43, feltet `kriterium`
i `TESTFLAGG`, vist under regelen). Ingen filer i repoet.
**Den andre økten må vite:** Dette innslaget er den bindende teksten for
kriteriet. Dashbordet viser den samme. Bygg videre på versjon 43.

### 29.09.2026 10:52, Claude Code
**Hva:** Grensen i test-flagget «Bunnsone og høy tilbudsskår» satt til B2 60
(Frodes valg), ned fra 50 som Claude Code hadde valgt.
**Filer:** Dashbordet (artifact Syklusbordet, versjon 42). Ingen filer i repoet.
**Den andre økten må vite:** Grensen er konstanten `TEST_B2` rett over
`TESTFLAGG`. Bygg videre på versjon 42.

### 29.09.2026 10:49, Claude Code
**Hva:** Ny seksjon «Test-flagg» på dashbordet, rett under flerfaktorfond
(Frodes beslutning). Første test-flagg: bunnsone og høy tilbudsskår, for uran
og aluminium. Utløses når segmentet står i bunnsone (rå og detrendet A 80 eller
mer) og B2 er 50 eller mer. Da vises et varsel i klartekst; ellers en linje per
segment som sier hva som mangler. Ikke testet, og påvirker ikke bunnsonen.
**Filer:** Dashbordet (artifact Syklusbordet, versjon 41). Ingen filer i repoet.
**Den andre økten må vite:** Test-flaggene er en liste `TESTFLAGG` i
dashbordets script, rett før `renderNaa`, og tegnes av `renderTest`, som
kalles etter `renderFond`. Nye test-flagg legges til som nye elementer i
listen (navn, segmenter, regel, bakgrunn, utlost, varsel, rolig). Seksjonen er
`<section id="testflagg">` under `#fond`. Grensen B2 50 er valgt av Claude
Code; si fra hvis Frode vil ha en annen. Flaggloggen logger allerede
bunnsone og B per uke, så et utløst test-flagg kan etterprøves der.
Bygg videre på versjon 41.

### 29.09.2026 10:38, Claude Code
**Hva:** Kapitulasjon D og overlevelsesporten C i klartekst på dashbordet,
samme grep som for B. Hvert panel får linjene «Kapitulasjon D:» og
«Overlevelse C:», og oversikten får en kort merkelapp under D-måleren.
D: 80 og over «gitt opp», 60 til 79 «langt nede», 30 til 59 «noe nede»,
under 30 «ikke gitt opp». Teksten sier i tillegg om papirene spriker (30
poeng eller mer mellom laveste og høyeste D), om grunnlaget er tynt (ett
eller to papirer), og om alle papirene er omvendte. C forklarer porten og
lister hvert målt papir med port og kvartaler, og hvilke som ikke er målt.
**Filer:** Dashbordet (artifact Syklusbordet, versjon 40). Ingen filer i repoet.
**Den andre økten må vite:** Nye funksjoner `dNivaa`, `dKort`, `dKlartekst`
og `cKlartekst` ligger rett etter B-funksjonene, før `dTekst`. To nye linjer
i panelhodet etter B-linjen, og D-cellen i oversikten har fått `.b-kort`.
Bygg videre på versjon 40.

### 29.09.2026 10:34, Claude Code
**Hva:** Tilbud B i klartekst på dashbordet (Frodes ønske). Hvert panel med B
får en linje «Tilbud B:» som forklarer situasjonen nå, og oversikten får en
kort merkelapp under B2-måleren (for eksempel «krymper, øker nå»). Teksten
regnes i dashbordet av B2 (nivå), B1 (retning) og forholdstallet, så den
følger med når B oppdateres. Grenser: B2 ≥ 75 krymper tydelig, ≥ 50 krymper,
≥ 25 vedlikehold, ellers ingen knapphet. B1 ≥ 70 kutter videre, under 30 øker
nå. Teksten sier alltid «Ikke testet som signal».
**Filer:** Dashbordet (artifact Syklusbordet, versjon 39, bygd på versjon 38
fra Cowork), `priser.py` (sender `B_forhold` og `B_aar` i `scores`).
**Den andre økten må vite:** Dashbordet er endret på tre steder: CSS-klassene
`.b-tekst` og `.b-kort`, funksjonene `bNivaa`, `bRetning`, `bKort` og
`bTekst` rett før `dTekst`, og én linje i panelhodet og B2-cellen i
oversikten. Bygg videre på versjon 39, ellers forsvinner endringen.
Forholdstallet i teksten vises først når `priser.py` har kjørt på onsdag;
til da står teksten uten det.

### 29.09.2026 10:22, Claude Code
**Hva:** Haleregel for tilbudsskåren B (Frodes beslutning 29.09, bestilt fra
Cowork). I tillegg til halvregelen, og bare for slutten av serien: siste år
telles først når minst tre fjerdedeler (rundet opp) av kurvens aktive selskaper
har tall. Aktive = selskaper med tall i minst ett av de tre siste årene i
serien (Frodes valg av alternativ 1). År kuttes bakfra til kravet er oppfylt.
Kuttene logges per metall som for halvregelen.
**Filer:** `tilbud_b.py` (del 3), `sonde_kjor_b_haleregel.py` (ny),
`sonder/sonde_kjor_b_haleregel.txt`, `sonder/b_haleregel.json`,
`sonder_ferdige.txt`. `b_manuell.json` og `c_manuell.json` er ikke rørt.
**Den andre økten må vite:** Før og etter, siste år per metall:
jernmalm 2026 -> 2025, forhold 1,154 -> 1,593, B1 66,7 -> 50,0, B2 0,0 -> 0,0
(haleregelen kutter 2026, der bare FMG og CIA har tall). Aluminium (2025,
1,021, B1 5,9, B2 63,0), gull (2025, 1,189, 33,3, 32,0), kobber (2025, 1,87,
36,8, 0,0), kull (2025, 0,986, 38,9, 48,6) og uran (2025, 1,181, 0,0, 73,0)
er uendret. Alle år som står igjen har samme tall som før. Regelen slik den
først var formulert (krav av alle selskaper) ville kuttet 2023 til 2025 for
kull fordi HCC sluttet å rapportere i 2022 (B2 48,6 -> 91,9); derfor
aktive selskaper. HALEREGEL=0 og HALEKRAV=alle i miljøet gir de gamle
variantene, bare for sammenligning.

### 29.09.2026 10:09, Claude Code
**Hva:** Faktorsonden kjørt. Avkastningen etter bunnflagget justert for marked,
størrelse, verdi, lønnsomhet, investering, momentum og (bransjene) langsiktig
reversering.
**Filer:** `sonder/sonde_kjor_faktor.txt`, `sonder/faktor.json`,
`sonder_ferdige.txt` (lagt til `sonde_kjor_faktor`).
**Den andre økten må vite:** Papirene på tavlen: 12 mnd S +27,1 % rå,
+15,7 % etter faktorene (6 av 11 episoder, p 0,13). Etter regelen satt før
kjøring har flagget «noe eget». Det som forklares, er nesten bare markedet
(bidrag +17 prosentpoeng); verdi, momentum og reversering forklarer nesten
ingenting. Bransjeporteføljene er negative etter faktorene både før og etter
2011 (12 mnd minus 8,5 % før 2011). At papirene er positive mens bransjene ikke er
det, peker mot utvalget av papirer (valgt 2026, overlevere) og ikke mot flagget.
Ikke signifikant i noen av settene.

### 29.09.2026 10:04, Claude Code
**Hva:** Flaggloggen utvidet (Frodes punkt 2). Kursloggen får utbytte per uke og
valutakurs til dollar. Ukeloggen får B, B1, B2 og Ar per segment. Hypotesen om
kjøp etter én måned og salg etter tre måles nå i dollar med utbytte, mot ACWI
på samme måte. Ny sonde for faktorjustering (punkt 3) lagt inn og kjørt.
**Filer:** `flagglogg.py`, `sonde_kjor_faktor.py` (ny). Fra neste onsdag får
`logg/kurser_uke.csv` kolonnene `utbytte` og `usd_per_enhet`, og
`logg/flagg_uke.csv` kolonnene `Ar`, `B`, `B1`, `B2`. `logg/hypotese_3mnd.csv`
får `utbytte` og `grunnlag`.
**Den andre økten må vite:** Målet for hypotesen er endret før noe utfall fantes
(ingen rene innslag ennå). Kriteriet for bekreftet er uendret. Eldre kursrader
mangler utbytte og valuta, og da faller målingen tilbake til egen valuta uten
utbytte; kolonnen `grunnlag` sier hva som ble brukt. `siste_kurs` i
`flagglogg.py` returnerer nå en dict, ikke en tuppel. Leser noe annet
`kurser_uke.csv` eller `flagg_uke.csv` på kolonneposisjon, må det sjekkes.
Resultatet av faktorsonden føres i et eget innslag.

### 29.09.2026 10:00, Cowork
**Hva:** Fortescue lagt inn i tilbudsskåren B for jernmalm, lest fra
`sonder/sonde_kjor_b_fmg.txt` (årsrapportene FY2012 til FY2026).
**Filer:** `b_manuell.json` (FMG lagt til), `sonder_ferdige.txt` (lagt til
`sonde_kjor_b_fmg`), `notater/LOGG.md`.
**Den andre økten må vite:** Kvartalsvis kjøring 29.09 kl. 09:52 bekreftet B for
jernmalm uten Fortescue: ratio 1,875 (2025), B1 20, B2 0, og DNO trang (10,1
kvartaler). Med Fortescue (prøvekjørt) går serien 2012 til 2026 med fire selskaper.
Fortescue er konsernet: Payments for PP&E (Fortescue pluss joint operations)
mot Depreciation and amortisation, alle år kontrollert i to rapporter unntatt
FY2012 og FY2026. Fortescue Energy er med fra FY2021 (under ti prosent). FY2008 til
FY2011 mangler (ingen lesbar tekst i PDF-ene). NB: 2026 står med bare Fortescue og
Champion (regnskapsår som slutter i 2026) og trekker siste ratio ned til 1,16,
mot 1,60 for 2025 med alle fire. Regelen om at regnskapsåret merkes med året det
slutter er uendret; en endring er Frodes valg.

### 29.09.2026 09:50, Cowork
**Hva:** (arbeidet ble gjort 28.09, pushet 29.09) Tilbudsskåren B for jernmalm fra årsrapporter, og DNO i
overlevelsesporten C. Fortescue-sonde for B.
**Filer:** `b_manuell.json` (ny: Kumba 2007 til 2025, Vales jernmalmsegment
2016 til 2025, Champion FY2021 til FY2026), `c_manuell.json` (DNO lagt til),
`sonde_kjor_b_fmg.py` (ny), `notater/2026-09-28_cowork_c_og_b.md`, `notater/LOGG.md`.
**Den andre økten må vite:** Prøvekjørt B for jernmalm: ratio 1,88,
femårssnitt 1,85, B1 20, B2 0, altså ingen tilbudsknapphet. Serien blir
2016 til 2025 til Fortescue er inne, fordi tynne år kuttes. DNO prøvekjørt til
trang (10,1 kvartaler, verste år 2015); 2008 og 2009 mangler. Tallene er lest
via nettverktøy og kontrollert mot to rapporter der det gikk. Kan brukes i
testen «flagget kombinert med B» når Fortescue er inne.

### 28.09.2026 13:30, Cowork
**Hva:** Overlevelsesporten C for papirer uten SEC-tall. Aker BP målt til åpen
(23,0 kvartaler, verste år 2006), så Brent-porten er åpen.
**Filer:** `c_manuell.py` (ny), `c_manuell.json` (ny), `overlevelse_c.py`
(leser c_manuell), `sonde_kjor_c_manuell3.py` (ny), `sonder_ferdige.txt`
(lagt til `sonde_kjor_fond_norge`).
**Den andre økten må vite:** NewsWeb-vedlegg hentes med
`https://api3.oslo.oslobors.no/v1/newsreader/attachment?messageId=..&attachmentId=..`.
Driftsår i annen valuta regnes om med Norges Banks årssnitt.

### 28.09.2026 12:30, Cowork
**Hva:** WTI lagt til i det parallelle signalet detrendet A ≥ 95 (Frodes
valg, ikke testet). Dashbord versjon 38: kortere fondsboks (de fem fondene
nærmest flagg, med par og begrunnelse), Norge (Nordnet/KLP, målt på ENOR) i
fondskartet.
**Filer:** `priser.py` (D95_SEGMENTER), dashbordet (artifact, ikke i repoet).
**Den andre økten må vite:** WTI holdes etter regelen fra desember 2025 til
desember 2027, som Brent. Brent og WTI har 34 felles måneder over 95, så det
er i praksis samme signal. Differansen Henry Hub mot TTF ble undersøkt og gir
ikke et eget signal; ikke innført.

### 28.09.2026 23:30, Claude Code
**Hva:** Felles logg og `CLAUDE.md` opprettet, formatert etter malen fra Cowork-økten.
**Filer:** `notater/LOGG.md`, `CLAUDE.md`
**Den andre økten må vite:** `CLAUDE.md` ber alle økter lese denne loggen før
de starter og føre sine endringer her i samme commit.

### 28.09.2026 18:19, Claude Code
**Hva:** Notat om backtestene, og hypotesen om kjøp én måned etter bunnsone og
salg tre måneder etter kjøpet lagt inn i flaggloggen som test framover.
**Filer:** `notater/2026-09-28_backtest.md`, `flagglogg.py`,
`logg/hypotese_3mnd.csv` (ny, skrives hver onsdag), `logg/kurser_uke.csv`
(ACWI logges nå som referanse, segment "referanse").
**Den andre økten må vite:** Bunnflagget holdt ikke utenfor perioden det ble
valgt på (Ken French-bransjer før 2011 og landporteføljer for Norge).
Resultatet fra 2011 til 2026 bæres i hovedsak av 2009 og 2020. Hypotesen er
funnet i de samme dataene og er ikke bekreftet. Kriteriet for bekreftet står i
`flagglogg.py` og i notatet og skal ikke flyttes. Flagget og dashbordet er
ikke endret.

### 28.09.2026 15:18 til 18:11, Claude Code
**Hva:** Tre nye sonder: backtest 1 til 12 mnd på tavlens papirer og
flerfaktorfond, test bakover mot Ken French-bransjer fra 1926, og fondsregelen
på Ken French sine landporteføljer fra 1975.
**Filer:** `sonde_kjor_backtest.py`, `sonde_kjor_backtest_lang.py`,
`sonde_kjor_land.py`, resultater i `sonder/sonde_kjor_backtest*.txt`,
`sonder/sonde_kjor_land.txt` og tilhørende `.json`, `sonder_ferdige.txt`
(lagt til `sonde_kjor_c_manuell3`, `sonde_kjor_backtest`,
`sonde_kjor_backtest_lang`, `sonde_kjor_land`).
**Den andre økten må vite:** Første backtest mistet 14 papirer i NOK, CAD og
SEK på grunn av en valutafeil, rettet før tallene i notatet. Commit-meldingen i
`3a85325` sier at første kjøring sto over en halvtime, det stemmer ikke (om
lag seks minutter). Landdataene hos French ligger i
`F-F_International_Countries.zip`, Australia heter `Austrlia.Dat`.
