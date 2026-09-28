# LOGG

Felles logg for Cowork-økten og Claude Code-økten. Nyeste innslag øverst,
ett innslag per vesentlig endring. Hvert innslag har: dato og klokkeslett
(norsk tid), hvilken økt, hva som ble gjort, hvilke filer, og hva den andre
økten må vite. Detaljer kan ligge i egne notater i `notater/`, men hvert
notat skal ha en linje her. Automatiske commits fra GitHub Actions
("oppdatert ...", "sonderesultat ...") føres ikke.

---

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
