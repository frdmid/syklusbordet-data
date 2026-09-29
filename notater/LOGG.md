# LOGG

Felles logg for Cowork-økten og Claude Code-økten. Nyeste innslag øverst,
ett innslag per vesentlig endring. Hvert innslag har: dato og klokkeslett
(norsk tid), hvilken økt, hva som ble gjort, hvilke filer, og hva den andre
økten må vite. Detaljer kan ligge i egne notater i `notater/`, men hvert
notat skal ha en linje her. Automatiske commits fra GitHub Actions
("oppdatert ...", "sonderesultat ...") føres ikke.

---

### 29.09.2026 12:05, Claude Code
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
