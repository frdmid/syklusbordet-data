# Uavhengig vurdering av modellen, 29.09.2026

Notat fra en egen Claude Code-økt som ikke har vært med på å lage modellen.
Ingen kode eller data er endret. Tallene under er lest fra `sonder/` eller
regnet direkte fra `sonder/backtest.json`, og det står hvilke.

## Kort konklusjon

Byggverket er ryddig, og det er gjort mye riktig: A og detrendet A er
punkt i tid, beslutningsregler er skrevet før kjøring, og notatene sier selv
at resultatene er tynne. Problemet er ikke slurv, men at bevisene er svakere
enn formuleringene. På data uten overlevelsesskjevhet (Ken French sine
bransjer) er flagget negativt mot eget snitt og mot markedet ved 12 måneder,
både før og etter 2011-09. Det positive på tavlens papirer faller til rundt
null uten episodene 2008-09 og 2020, og papirene er valgt i 2026 nettopp fordi
de fulgte råvaren. Flaggloggen framover er riktig tenkt, men vil i praksis ikke
kunne avgjøre noe på mange år, og den har noen hull som bør tettes nå, før
første innslag.

## 1. Metoden bak A, flagget, B, C og D

### A og bunnsonen

- **Ingen lekkasje i selve skåren.** `expanding_pct` og
  `expanding_pct_detrend` (`priser.py:145` og `:154`) bruker bare data til og
  med måned i. Deflatoren skalerer med siste KPI, men det endrer ikke
  rangeringen. De raske kopiene i `raavare_hist.py` er kontrollert mot
  originalene ved hver kjøring. Dette er godt gjort.
- **Men flagget live er ikke det samme som flagget i testene.** For seriene
  fra datasets-speilet (Brent, WTI, Henry Hub) lager `csv_series`
  (`priser.py:66`) månedsverdien av siste dagskurs, også for inneværende,
  uferdige måned. Flaggloggen for uke 39 har `siste_obs` 2026-09 for Brent,
  logget 25.09. Live kan flagget dermed slå inn og ut fra uke til uke på én
  dagskurs, mens backtestene måler ferdige måneder. Pink Sheet-seriene er
  månedssnitt, altså glattere og en halv måned forsinket. To ulike
  definisjoner av «måned» i samme regel.
- **Valgene rundt A er gjort med kunnskap om hele historikken.** Avkortingene i
  `AVKORT` (for eksempel jernmalm fra 2010) er faglig begrunnet, men valgt i
  2026. Ni segmenter ble tatt ut 22.09 fordi ingen papirer korrelerte over
  0,30 i 2016 til 2026. Regelen «rå og detrendet A ≥ 80» ble valgt på 2011 til
  2026 etter at rå A alene var prøvd. Hver for seg er dette forsvarlig. Samlet
  er det mange valg tatt på de samme 20 til 30 episodene, og det bør leses som
  en kilde til overtilpasning, ikke som lekkasje i streng forstand.
- **A og detrendet A er ikke to uavhengige bekreftelser.** De regnes av samme
  serie, og kravet om begge er i praksis en strengere terskel. Det er greit,
  men det bør ikke presenteres som to signaler.

### B, tilbudsskåren

- **Nevneren stiger i nedgangsår av seg selv.** `DDA_RANG` har som nest
  foretrukne begrep IFRS-begrepet for avskrivninger *inkludert nedskrivninger*
  (`tilbud_b.py:80`). Nedskrivninger kommer når prisene er lave, og da faller
  forholdstallet og B stiger, samtidig med A. Oppkjøp gjør det samme: de øker
  avskrivningene uten å komme med i capex. B måler da delvis det samme som A,
  ikke tilbudssiden.
- **Terskelen 1,0 er for lav som «vedlikehold».** Avskrivninger er på historisk
  kost. Med inflasjon må et selskap investere mer enn avskrivningene bare for å
  stå stille. B2 sier derfor «krymper» for sent.
- **Ikke punkt i tid.** Siste innlevering vinner (`tilbud_b.py:107`), altså
  omarbeidede tall. Årstall kommer to til fire måneder etter årsslutt. Dette
  betyr ingenting for dashbordet i dag, men må håndteres hvis «flagg pluss B»
  skal testes bakover.
- Med 6 til 19 årlige punkter er B1 (persentil) svært ustabil. Det bør stå.

### C, overlevelsesporten

- **Renter trekkes fra to ganger for US GAAP-selskaper.** `kv()` trekker
  rentekostnaden fra driftskontantstrømmen (`overlevelse_c.py:213-215`). Under
  US GAAP er betalte renter allerede trukket fra i driftskontantstrømmen. Under
  IFRS kan de ligge under finansiering. Porten blir dermed strengere for
  amerikanske selskaper enn for andre, uten at det er meningen. Rentedekningen
  (`:221`) har samme problem.
- Dagens kontantbeholdning (`:198`) holdes mot verste års nominelle
  driftskontantstrøm i hele historikken. For et selskap som har vokst mye er
  det verste året lite i dagens kroner, og porten blir for åpen.
- Segmentets port er «åpen» hvis ett papir er åpent (`:272`), mens D bruker
  medianen. Begge valg kan forsvares, men de trekker i hver sin retning.
- Porten måles bare på selskaper som finnes i dag. At de overlevde forrige
  bunn er en del av grunnen til at de står på tavlen. C kan derfor ikke si noe
  om hvor ofte porten ville fanget en konkurs.

### D, kapitulasjon

- Metoden er ryddig: egen historikk, utbyttejustert kurs, dempet med
  fallets størrelse. Ingen lekkasje, fordi adjclose bare endrer forholdet
  mellom to datoer med utbyttene mellom dem.
- **D og A overlapper.** Papirene er valgt fordi de følger råvaren
  (korrelasjon over 0,30). Når råvaren har falt mye, har papirene også falt,
  og D stiger. Når dashbordet viser A høy, B høy og D høy, er det i stor grad
  ett fall målt tre ganger, ikke tre uavhengige tegn.
- Tidlige måneder der 200-dagers snitt mangler, telles som «ikke under»
  (`kapitulasjon_d.py:131-133`). Liten effekt.

### Valuta, inflasjon og utbytte

- Valutaomregningen i backtestene (`FX` i `sonde_kjor_backtest.py:74`) er
  riktig vei for alle valutaer, også pence. Utbytte er med via adjclose.
  Verdensindeksen er SPY før 2008, altså USA og ikke verden, som sonden selv
  sier.
- `tilbud_b.py:250-252` summerer SEC-selskapene i rapporteringsvaluta (Cameco
  i kanadiske dollar) sammen med dollar, mens de manuelt leste regnes om. Det
  påvirker bare vektingen, ikke forholdstallet per selskap.

## 2. Testene og konklusjonene

### Det som stemmer

Jeg har gått gjennom tallene i `notater/2026-09-28_backtest.md` og loggen mot
utskriftene. Nesten alle stemmer: 6 mnd S +12,6 % (7 av 11, p 0,094), 12 mnd
+15,7 % (6 av 11, p 0,135), bransjene før 2011 med 12 mnd S -5,7 % (4 av 16,
p 0,81), fondsregelen, landtesten og faktortallene.

### Det som ikke stemmer eller er overtolket

1. **«45 innslag, 11 episoder, alle etter 2008»** (notatet) er feil. Tre av de
   elleve episodene er før 2008: aluminium 1991-05, uran 1998-10 og 2000-04.
2. **«Resultatet fra 2011 til 2026 bæres i hovedsak av 2009 og 2020»**
   (loggen 28.09 18:19) er selvmotsigende, siden 2009 er før 2011. Papirtesten
   har ikke noe skille ved 2011; den går fra 1991.
3. **«Modellen hviler på 2011 til 2026»** (utskriften fra
   `sonde_kjor_backtest_lang`) er for velvillig. Bransjene *fra* 2011-09, altså
   inne i perioden regelen ble valgt på, gir også 12 mnd S -3,7 % (3 av 6) og
   -9,4 % mot markedet. Etter faktorene er det -6,1 % (FF5+M). Selv i
   utvalgsperioden er det bare tavlens papirer som gir et positivt tall.
4. **Hvor mye 2008-09 og 2020 bærer.** Regnet fra `innslag_papirer` i
   `sonder/backtest.json` (medianen per segment, ikke per papir, og
   totalavkastning, ikke mot eget snitt, så dette er en tilnærming): S etter
   12 måneder er +25 % med alle elleve episoder, +14 % uten 2020, +14 % uten
   2008-11, og **+2 % uten begge**. Det er lavere enn et vanlig aksjeår.
   «Bæres av 2009 og 2020» er altså ikke en nyanse; uten dem er det ingenting.
5. **Faktorsonden.** Regelen satt før kjøring (FF5+M under en tredel av rå S)
   krever ikke at noe er signifikant, og ble oppfylt med p 0,13 og 6 av 11.
   Loggen sier dette selv. Men den riktige lesingen er strengere: de eneste
   dataene uten overlevelsesskjevhet (bransjene) er negative etter faktorene
   i alle horisonter og begge perioder, og forskjellen mot papirene forklares
   best av utvalget. Sonden summerer dessuten enkle månedsavkastninger
   (`pct_change` og `sum_fram`), ikke log. Etter et flagg er volatiliteten
   høy, og da blir en sum av enkle avkastninger skjevt høy. Det trekker papirene
   opp mer enn snittet de sammenlignes med.
6. **«Flagget er ikke tilbakevist»** (notatet) undertolker. Testen som ble
   skrevet som avgjørende før kjøring, feilet. Det riktige er: flagget har
   ikke vist verdi for aksjer på data uten overlevelsesskjevhet.
7. **Dobbelttelling i papirtesten.** `HEND` i `sonde_kjor_backtest.py:357`
   tar med et papir én gang per segment. I 2020-03 flagget både Brent og WTI,
   og IOGP.L telles to ganger i episoden. GLEN.L (fire segmenter) og EXV6.DE
   (tre) kan få samme effekt. Bransjesonden tar høyde for dette, faktorsonden
   også (den bruker en mengde), men papirtesten gjør det ikke.

### Det som er riktig satt opp

- Episoder som enhet, null der hele episoden flyttes, kontroll med inngang T+1,
  skillet ved 2016 og 2011, og bransjene som hovedtest er gode valg.
- Terskel-, timing- og salgssonden er kalibrert på simulerte data før bruk.
  Det er uvanlig grundig.

### Mange forsøk på samme data

Summen av sondene er mange horisonter (1 til 24 mnd), to inngangstider,
åtte terskler, fem inngangsregler, fem salgsregler, fondsregel, land og faktor,
på de samme 11 til 27 episodene. Hypotesen om kjøp etter én måned og salg
etter tre er én celle blant flere titalls. Notatet sier at den er funnet i
dataene, og det er riktig. Den står i tillegg i motsetning til to regler som
ble vedtatt tidligere: timingsonden sa «kjøp ved flagget» (T0) og salgssonden
sa «hold 24 måneder» (S0, «gjelder fra nå»). Det bør stå tydelig hvilken regel
som gjelder hvis det kjøpes for ekte penger.

## 3. Flaggloggen og hypotesen framover

Ideen er riktig: logg før utfallet er kjent, i git, med kriterium skrevet ned
på forhånd. Men slik den står nå, kan den neppe avgjøre noe, og den har hull.

**Den kommer til å ta lang tid.** Historisk har bunnsonen gitt rundt 27
episoder på 60 år over alle råvarene, og 11 episoder på tavlens papirer fra
1991. Det er omtrent én episode annethvert år. Fem ferdige episoder tar
sannsynligvis åtte til ti år. Ingen segmenter står i bunnsonen nå.

**Kriteriene skiller dårlig.** Hvis flagget ikke har noen verdi, er hver
episode omtrent et myntkast mot ACWI. Da er sjansen for «bekreftet» ved fire av
fem rundt 19 %. Test-flagget «Bunnsone og høy tilbudsskår» (to av tre slår
ACWI) blir bekreftet i 50 % av tilfellene av ren tilfeldighet, og uran har hatt
to bunnsone-episoder siden 1988.

**Hull som bør tettes før første innslag:**

1. *Innslag defineres ikke som i testene.* Backtestene krever tolv måneder uten
   flagg før et nytt innslag. `hypotese_3mnd` tar med hver `tenkt_kjoep`
   (`flagglogg.py:214-236`), og hver `bunnsone_start` lager nye
   (`:318-340`). Sammen med at oljeflagget regnes på uferdig måned, kan ett
   fall gi flere innslag.
2. *Papirer som tas av tavlen forsvinner fra testen.* Kurser logges bare for
   papirene som står på tavlen den uken (`flagglogg.py:272-277`). Tas et papir
   ut etter et tenkt kjøp, slik 2020.OL ble 29.09, logges det ikke lenger, og
   posisjonen blir stående som «aapen» for alltid. Det er overlevelsesskjevhet
   bygd inn i den eneste testen som skulle være fri for den.
3. *Samme papir i flere segmenter* gir flere rader i samme episode (IOGP.L for
   Brent og WTI, GLEN.L for fire metaller).
4. *Ingen fast avslutning.* «Minst fem episoder … ellers forkastet» sier ikke
   om man vurderer nøyaktig ved fem, eller venter på flere når det står tre av
   fem. Det åpner for å vente til det ser bra ut.
5. *Dommen regnes ikke i koden.* Filen gir rader per papir, men ikke
   episoder, median per episode eller konklusjon. Det skal gjøres for hånd, og
   da finnes det valg.
6. *WTI og d95.* WTI har tom `d95` i uke 39 fordi den ble lagt til 28.09.
   `flagglogg.py:312` leser tom verdi fra forrige uke som «ikke i sonen», så
   første gang WTI når 95 blir det logget som et rent innslag selv om loggen
   ikke fulgte WTI før.

**Det som mangler i loggen:** prisen selv (nominell og real) og måneden den
gjelder, slik at revisjoner i Pink Sheet kan oppdages; hvilken versjon av
koden og instrumentlisten som ga flagget (commit), selv om git-historikken
delvis dekker det; og en kontrollgruppe: de samme papirene i uker uten flagg,
eller alle tavlens papirer likt vektet, slik at man ser om flagget slår
råvareaksjer generelt og ikke bare ACWI.

## 4. De tre viktigste svakhetene

### Bør rettes

**1. Bevisgrunnlaget er svakere enn språket.** Den eneste positive støtten
kommer fra papirer valgt i 2026 for at de fulgte råvaren, og den forsvinner
uten 2008-09 og 2020. Bransjene uten overlevelsesskjevhet er negative også i
utvalgsperioden. *Det jeg ville gjort:* skrive i notatet og på dashbordet at
flagget ikke har vist verdi for aksjer, rette de tre formuleringene over, og
bruke flagget som en liste over hvor det er verdt å lese, ikke som en
kjøpsregel. Hold posisjonene små, slik notatet selv anbefaler.

**2. Testen framover har hull og for lav styrke.** *Det jeg ville gjort, før
første innslag:* samme innslagsdefinisjon som i testene (ferdige måneder og
tolv måneders pause); fryse papirlisten per innslag og fortsette å logge
kursen til posisjonen er lukket, også om papiret tas av tavlen; ett papir én
gang per episode; dommen regnet i koden; et fast vurderingspunkt (for
eksempel de første seks episodene eller en fast dato), med sjansen for falsk
bekreftelse oppgitt. Og viktigst: **test hypotesen nå på data den ikke er
funnet i.** Den ble funnet på tavlens papirer. Bransjene før 2011 og
landporteføljene er ute av utvalget for den, og inngang T+1 med salg etter tre
måneder kan regnes der i dag. Det tar en sonde, ikke ti år.

**3. Rentefeilen i C** (`overlevelse_c.py:213-215`). Liten jobb, og den gjør
porten systematisk strengere for amerikanske selskaper.

### Forbehold som bør stå, men ikke nødvendigvis rettes

- B stiger mekanisk i nedgangsår (nedskrivninger og oppkjøp i nevneren), og
  terskelen 1,0 ligger under reelt vedlikehold. B, C og D er ikke testet og
  ikke punkt i tid. A, B og D overlapper, så tre høye skårer er ikke tre
  bekreftelser.
- Oljeflagget live bygger på uferdig måned. Enten bruk siste ferdige måned,
  eller skriv det tydelig og bruk samme definisjon i testene.
- Mange forsøk på de samme få episodene. Hver ny sonde på de samme dataene gjør
  neste funn mindre verdt.

## 5. Kodefeil og mindre funn

| Fil og linje | Hva | Alvor |
|---|---|---|
| `overlevelse_c.py:213-215`, `:221` | Renter trukket fra driftskontantstrøm som (US GAAP) allerede er etter renter | Bør rettes |
| `flagglogg.py:272-277` | Bare tavlens papirer logges; tenkte kjøp i papirer som tas ut blir aldri avsluttet | Bør rettes |
| `flagglogg.py:214-236`, `:318-340` | Ingen tolv måneders pause som i testene; papir i flere segmenter gir flere rader | Bør rettes |
| `flagglogg.py:312` | Tom forrige verdi leses som «ikke i sonen» (WTI og d95) | Liten |
| `priser.py:66` med `:206` | Uferdig måned brukes for Brent, WTI og Henry Hub | Bør avklares |
| `sonde_kjor_backtest.py:357` | Papir telles én gang per segment i samme episode (IOGP.L i 2020-03) | Liten, men skjevt oppover |
| `tilbud_b.py:101-108` | Ingen varighetskontroll for strømsposter, slik C har (`overlevelse_c.py:107-109`). Risiko for at et kvartalstall tas for et årstall. Ikke verifisert mot data | Bør sjekkes |
| `tilbud_b.py:121-131` | `velg_par` krever ikke samme valuta for capex og avskrivninger | Liten, plausibilitetsvinduet fanger det meste |
| `tilbud_b.py:80` | Avskrivninger inkludert nedskrivninger | Metodisk |
| `tilbud_b.py:250-252` | SEC-selskaper summeres i ulik valuta | Liten |
| `sonde_kjor_faktor.py`, `R[tk]` og `sum_fram` | Enkle avkastninger summert i stedet for log | Forbehold |
| `kapitulasjon_d.py:131-133` | Måneder uten 200-dagers snitt telles som «ikke under» | Liten |
| `flagglogg.py:22` | Sier at salgsregelen ikke er vedtatt; salgssonden vedtok S0 (24 mnd) | Kommentar |
| `notater/2026-09-28_backtest.md` | «alle etter 2008» er feil | Rett teksten |

## Hva de andre øktene bør gjøre først

1. Rette formuleringene i notatet og loggen (punkt 2 over), uten å endre tall.
2. Tette hullene i flaggloggen før noe segment går inn i bunnsonen.
3. Kjøre hypotesen (T+1, salg etter tre måneder) på bransjene og landene før
   2011, med regelen skrevet ned før kjøring.
4. Rette rentefeilen i C.

Ingen av dette krever at flaggregelen endres, og jeg anbefaler ikke å endre
den etter denne vurderingen.
