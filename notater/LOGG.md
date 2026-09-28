# Endringslogg for repoet

Alle endringer Claude gjør i repoet, nyeste øverst. Gjelder alle økter,
også cowork: den som endrer noe, skriver en linje her i samme commit.

Hver oppføring: dato, økt, hva som ble endret, hvorfor, og commit. Automatiske
commits fra GitHub Actions ("oppdatert ...", "sonderesultat ...") føres ikke.

---

## 28.09.2026, Claude Code (gren claude/brave-wright-cv54xv, slått inn i main)

- **Endringslogg opprettet** (denne fila) og `CLAUDE.md` med beskjed om å
  føre den. Frodes ønske.
- **Flaggloggen tester en tremånedershypotese framover** (`47128e1`).
  `flagglogg.py` skriver `logg/hypotese_3mnd.csv` hver uke: kjøp en måned
  etter bunnsone, selg tre måneder etter kjøpet, målt mot ACWI. ACWI logges
  nå som referanse i `logg/kurser_uke.csv` (segment "referanse").
  Kriterium for bekreftet står i koden og i notatet. Ingen endring i selve
  flagget eller dashbordet.
- **Notat om backtestene** (`2b78d91`, `1ee5287`):
  `notater/2026-09-28_backtest.md`. Funn, konklusjon og anbefalinger (ikke
  vedtatt).
- **Ny sonde `sonde_kjor_land.py`** (`808f096` til `7caa5e8`). Fondsregelen
  testet på Ken French sine landporteføljer for Norge og Australia fra 1975.
  Fem små commits for å finne filene hos French (landene ligger i
  `F-F_International_Countries.zip`, Australia heter `Austrlia.Dat`).
  Regel og kriterium uendret mellom kjøringene. Resultat: består ikke.
- **Ny sonde `sonde_kjor_backtest_lang.py`** (`5e445f4`). Bunnflagget testet
  bakover mot Ken French sine bransjeporteføljer fra 1926 og store gamle
  aksjer. Resultat: består ikke før 2011.
- **Ny sonde `sonde_kjor_backtest.py`** (`2656529`, `3a85325`, `3d40369`).
  Avkastning 1, 2, 3, 6 og 12 mnd etter bunnsone for papirene på tavlen og
  flerfaktorfondene. Andre commit gjorde nullfordelingen raskere, tredje
  rettet en feil i valutaomregningen som mistet 14 papirer i NOK, CAD og SEK.
  Commit-meldingen i `3a85325` sier at første kjøring sto over en halvtime.
  Det stemmer ikke: den ble avbrutt etter om lag seks minutter.
- **`sonder_ferdige.txt`**: lagt til `sonde_kjor_c_manuell3`,
  `sonde_kjor_backtest`, `sonde_kjor_backtest_lang` og `sonde_kjor_land`,
  så ad hoc-kjøringen ikke kjører dem på nytt.
