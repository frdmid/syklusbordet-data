# LOGG

Felles logg for Cowork-økten og Claude Code-økten. Nyeste innslag øverst,
ett innslag per vesentlig endring. Hvert innslag har: dato og klokkeslett
(norsk tid), hvilken økt, hva som ble gjort, hvilke filer, og hva den andre
økten må vite. Detaljer kan ligge i egne notater i `notater/`, men hvert
notat skal ha en linje her. Automatiske commits fra GitHub Actions
("oppdatert ...", "sonderesultat ...") føres ikke.

---

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
