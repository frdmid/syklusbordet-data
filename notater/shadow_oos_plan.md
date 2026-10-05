# Shadow-OOS: plan og fase 1

Skrevet 05.10.2026 av Claude Code (planlagt kjøring, Frodes bestilling), etter
dokumentet «Shadow-OOS-oppsett for Syklusdashboard». Gjelder minimumsversjonen
(punkt 50) og fase 1 i punkt 51. Dashbordet er ikke endret. LIVE OOS-siden
kommer senere, etter avtale med Frode.

## Startdato

Dokumentet bruker 05.10.2026 som eksempel. Første ordinære ukekjøring etter
30.09.2026 er **onsdag 07.10.2026** (`ukentlig.yml`, 06:00 UTC). Den skriver det
første snapshotet. `effective_from` er derfor 07.10.2026. Koden skriver
ingenting før den datoen, heller ikke ved en kjøring for hånd.

## 1. Kartlegging: hva dagens kode faktisk gjør

| Element | Hvor | Hva som fryses |
|---|---|---|
| A rå | `priser.build_segment`, `scores.A` | Persentil av log realpris mot hele egen historikk, punkt i tid, minst 60 mnd |
| A detrendet | samme, `scores.Ad` | Samme mot egen trend |
| A rullende | samme, `scores.Ar` | Ti års vindu. Vises, men inngår ikke i flagget |
| A anker | `bygg_shipping.py`, `scores.A2` | Paritet mot kostnadsanker, bare skipssegmentene |
| Bunnsone | `scores.flagg` | A ≥ 80 og Ad ≥ 80. Laks og oljeservice har aldri flagg (observasjon). Skipssegmentene har ingen A |
| Oppsikt (watch) | `scores.oppsikt` | A ≥ 80 og ikke bunnsone |
| d95 | `scores.flagg_d95` | Brent og WTI, Ad ≥ 95, separat og ikke testet |
| B | `scores.B` | B2 siste år fra `b_capex.json` (`tilbud_b.py`), bare metallene som har B. Rigger (`rigg_b.py`) er kontekst i oljeservice |
| C | `scores.gate` | `overlevelse_c.py` og `c_manuell.py`: kvartaler kontantene holder i verste år, under 8 stengt. Segmentet er åpent hvis minst ett målt papir på tavlen er åpent (`priser.py`), fond gir «uaktuell» |
| D | `scores.D` | `kapitulasjon_d.py`: median av papirenes D, vektet mot temaets kursfall |
| S | `scores.S` | **Regnes ikke.** Feltet er alltid tomt i dagens kode |
| Sterk kandidat | ingen | **Finnes ikke** i dagens kode |
| Trend | `signaler.trend` | Kontekst |
| COT | `signaler.cot_for_segmenter` | Kontekst, sju kontrakter |
| Kurve | `kurve_innhent`, `signaler.kurveform` | Kontekst, seks segmenter |

Det som alt finnes i `flagglogg.py`, og som shadow bygger videre på i stedet
for å lage på nytt:

- 12-månedersregelen for nytt innslag (`ny_innslag`, `PAUSE_MND = 12`). Shadow
  kaller den samme funksjonen, og sjekker i tillegg sin egen hendelseslogg.
- Episoder med høyst 183 dager mellom innslag (`KLYNGE_DAGER`). Shadow bruker
  samme regel for makroklynger.
- `logg/kurser_uke.csv`: ukens kurs, valuta, utbytte og dollarkurs per papir,
  pluss ACWI. Shadow leser ukens kurser derfra og henter ikke kurser selv.
- `logg/hendelser.csv`, `hypotese_3mnd.csv`, `regel_6040.csv`, `dom.csv`: den
  korte hypotesen og 60/40-regelen. De står uendret. Shadow er en egen,
  bredere logg for Champion, ikke en erstatning.

Forskjellen fra flaggloggen: flaggloggen erstatter ukens linjer hvis
innhentingen går to ganger samme uke, og regner hypotesefilene på nytt hver
uke. Shadow skriver ukens snapshot én gang og rører det aldri igjen.

## 2. Hvordan minimumsversjonen passer inn

Repoet bruker JSON og CSV i git, ingen database. Tabellene i dokumentet blir
filer:

| Dokumentet | Fil | Skrives |
|---|---|---|
| `champion_v1_0.yaml` | `config/champion_v1_0.json` | Én gang, før start (JSON fordi PyYAML ikke er med i `requirements.txt`) |
| `model_registry` | `shadow/model_registry.csv` | Én linje per modell |
| `shadow_snapshot` | `shadow/snapshots/champion_v1_0/<ISO-uke>.csv` | Én fil per uke, opprettes og endres aldri |
| rådata-manifest (28) | `shadow/inndata/champion_v1_0/<ISO-uke>.json` | Git-blob-sha for hver inndatafil og hash for hver kodefil |
| `shadow_events` | `shadow/shadow_events.csv` | Bare tillegg |
| `shadow_outcomes` | `shadow/shadow_outcomes.csv` | Tom med overskrift i fase 1 |
| `correction_log` | `shadow/correction_log.csv` | Bare tillegg, for hånd ved feil |
| `run_manifest` (29) | `shadow/run_manifest.csv` | Én linje per kjøring |

Koden ligger i `shadow_oos.py`, testene i `test_shadow_oos.py`.

**Én rad i snapshotet** er dato × segment × papir × modell. Hvert segment har én
segmentrad (`level=segment`, tomt `instrument`) og én rad per papir på tavlen
(`level=instrument`). Feltnavnene følger dokumentet (4.1 til 4.5), slik at
koblingen er direkte. NULL er tom celle, aldri 0. Sannhetsverdier er
`true`/`false`. Første snapshot mot dagens data: 103 rader (18 råvaresegmenter,
7 skipssegmenter, 78 papirrader), rundt 45 kB per uke.

Felter som ikke finnes i dagens kode, står som NULL: `S`, `strong_candidate`,
`inventory`, `supply_metric`, `shares_outstanding`, `market_cap`,
`publication_date`. `available_from` er snapshotdatoen: vi vet bare at tallet
var tilgjengelig da vi leste det.

**Hendelser:** `watch_*`, `bottom_zone_enter/continue/exit`, `d95_enter/exit`,
`C_open/C_tight/C_closed/C_unknown/C_not_applicable` når segmentets port endres,
`hypothetical_entry` ved ny episode, `hypothetical_entry_d95` for d95,
`*_reentry_no_new_episode` når regelen sier nei, `C_forced_exit` per papir når C
stenger etter inngang (innen 24 mnd), og `3m/6m/12m/24m/36m_maturity`.
Tilstander som står allerede ved første snapshot, får `*_active_at_start` og er
ikke en ny episode (samme regel som flaggloggen). Ved inngang lagres
`macro_cluster_id`, `commodity_signal=true` og antall papirer per C-tilstand.
`investable_signal` er NULL til Frode har avgjort spørsmål 1 under.

## 3. Hvor i ukekjøringen

Sist i `bygg_shipping.py`, etter `endringer` og `helse`, som det siste steget i
`ukentlig.yml`. Da er segmentene, skipssegmentene, flaggloggen (med ukens
kurser) og helse.json skrevet. Kallet er pakket i try/except, så en feil i
shadow stopper ikke noe annet. Arbeidsflyten er ikke endret.

Rekkefølgen i én kjøring:

1. Les config. Før 07.10.2026: skriv ingenting.
2. Kontroller integriteten (under). Avvik skrives i manifestet, men stopper
   ikke ukens snapshot: klokken skal gå, avviket skal synes.
3. Sammenlign kodefilene med hashene i config. Endret kode merkes i
   `code_changed` i snapshotet og manifestet.
4. Finnes ukens snapshot fra før: skriv en manifestlinje
   `hoppet_over_uke_finnes` og stopp. Første kjøring i ISO-uken vinner.
5. Ellers: les inndata, skriv inndatafilen og snapshotet (bare opprett).
6. Regn hendelsene fra det lagrede snapshotet og forrige snapshot, og legg dem
   til.
7. Skriv manifestlinjen med hash av snapshotet, inndatafilen og
   hendelsesloggen, og en hashkjede.

Avbrytes en kjøring etter at snapshotet er skrevet, regner neste kjøring samme
uke hendelsene fra det lagrede snapshotet (`ok_gjenopptatt`), uten å regne
snapshotet på nytt.

## 4. Slik håndheves og testes append-only (punkt 46)

Håndheves i koden:

- Snapshot og inndatafil skrives med `opprett`, som feiler hvis filen finnes
  (GitHub-API svarer 422 uten sha).
- Hendelser og manifest skrives med `legg_til_rader`: den nye teksten må
  begynne byte for byte med den gamle, overskriften må være lik, og skrivingen
  bruker filens sha, så den feiler hvis noen har endret filen i mellomtiden.
- Git-historikken viser når hver linje kom.

Kontrolleres hver uke (`kontroller`), og kan kjøres for hånd med
`python shadow_oos.py kontroller`:

- hvert snapshot og hver inndatafil mot sha256 i manifestet,
- hashkjeden gjennom alle kjøringer,
- at hendelsesloggen begynner med nøyaktig det den var etter hver kjøring,
- at config stemmer med `specification_hash` i registeret.

Tester (`python test_shadow_oos.py`, kjørt lokalt 05.10, alle ti besto):

- ingenting skrives før 07.10,
- ny kjøring samme uke med endrede tall endrer ikke snapshotet,
- neste uke gir ny fil, og den gamle er byte for byte lik,
- et manipulert gammelt snapshot og en slettet hendelseslinje oppdages,
- tillegg avviser ny overskrift, og opprett avviser eksisterende fil,
- ingen fremtidige data (`available_from`, observasjonsdato og kursdato ≤
  snapshotdato),
- NULL er tom, ikke 0 (S, sterk kandidat, A for skip),
- samme inndata gir samme snapshot (punkt 47),
- en kunstig bunnsone i nikkel gir inngang, fortsettelse, `C_forced_exit`,
  utgang, og ingen ny episode ved ny bunnsone tre uker senere,
- endret kode merkes, og config stemmer med registeret.

## 5. Frysingen

`config/champion_v1_0.json` har reglene i klartekst og sha256 for de 16
kodefilene som bestemmer tallene (`priser.py`, `signaler.py`,
`instrumenter.py`, `uran_kilde.py`, `laks_innhent.py`, `kurve_innhent.py`,
`flagglogg.py`, `kapitulasjon_d.py`, `overlevelse_c.py`, `c_manuell.py`,
`tilbud_b.py`, `rigg_b.py`, `shipping.py`, `bygg_shipping.py`, `helse.py`,
`shadow_oos.py`). Linjeskift normaliseres til LF, så hashen er lik på Windows
og i Actions. `specification_hash` er sha256 av modell og spesifikasjon, og står
også i registeret. `code_commit` er commiten der filene ligger slik de er
hashet. Den føres inn i en egen commit rett etter, siden en commit ikke kan
inneholde sin egen hash.

Data som leses for hånd (`c_manuell.json`, `b_manuell.json`) er data, ikke
kode. Endringer der merkes ikke som kodeendring, men inndatafilen viser hvilken
versjon hver uke brukte.

## 6. Det som ikke er bygget i fase 1

- `shadow_outcomes` regnes ikke (fase 2). Filen er tom.
- Instrumentuniverset fryses alt i snapshotet på signaldatoen, og papirer
  som tas av tavlen etter en inngang logges videre i 37 måneder. Aksjetall og
  markedsverdi hentes ikke (fase 3).
- Ingen C-evaluering, Challengers, faktorer, placeboer eller LIVE OOS-side.
- Rådata (Pink Sheet, EIA, Fearnleys og så videre) arkiveres ikke. Inndatafilen
  peker på de bearbeidede filene i git, som kan hentes fram med blob-sha.
- Ingen `research_log`.

## 7. Spørsmål Frode må avgjøre

**Før 07.10.2026 kl. 06:00 UTC** (det som fryses; etter dette er en endring en
Challenger med ny startdato):

1. **Er det frosne riktig?** Særlig: inngang til kursen på signaldatoen (T0),
   S som NULL til S finnes i koden, ingen sterk kandidat, og
   12-månedersregelen slik flaggloggen har den, pluss shadow-loggens egne
   hendelser. Det mest konservative er valgt der dokumentet og koden kunne
   leses ulikt.
2. **Flere kjøringer samme uke:** første kjøring i ISO-uken vinner, også en
   kjøring for hånd. Er det greit?
3. **Kodeendringer etter start:** I dag skrives snapshotet uansett, med
   `code_changed`. Hva skal skje når regelkoden endres, for eksempel når
   Cowork endrer `c_manuell.py`, eller ved en feilretting i `priser.py`?
   Forslag: feilretting føres i `correction_log` og Champion fortsetter; en
   endret regel gjør Champion til «v1.0 med kjent avvik fra dato X», og den nye
   regelen blir Challenger. Cowork må vite at endringer i disse filene nå
   synes i shadow.

**Før første signal** (data lagres uansett, men valget må tas før utfallene
er kjent):

4. **C i universet:** Skal papirer med C stengt eller ukjent være med i P1 og
   telle for `investable_signal`? Flaggloggens tenkte kjøp tar med alle
   papirer på tavlen; `overlevelse_c.py` kaller C en port for papiret. Derfor
   er `investable_signal` NULL og antallet per C-tilstand lagret.
5. **Makroklynger:** kjedet regel (høyst 183 dager mellom påfølgende
   innganger, som flaggloggen) er valgt. Dokumentet kan også leses som
   «innen seks måneder fra klyngens første signal».

**Før første utfall modnes** (tidligst tre måneder etter første signal):

6. **Benchmark:** ACWI i dollar med utbytte, som flaggloggen allerede logger?
   Og hvordan «samtidige produsenter» og faktorjustering skal måles. Skal
   fastsettes i en egen, versjonert evalueringsspesifikasjon.
7. **36 måneder:** Flaggloggen logger kursen for et papir i 26 måneder etter
   tenkt kjøp. 36-månedersutfallet krever lengre logging. Det er en endring i
   `flagglogg.py` (en fryst fil) og bør gjøres som avtalt feilretting.

**Senere:**

8. Skal rådata arkiveres (punkt 28)? Det krever endringer i innhentingen og
   noen MB per uke.
9. Skal onsdagsrutinen og helsesjekken på dashbordet vise status fra
   `run_manifest.csv` (integritetsavvik, kodeendring)?
10. Champion S: egen startdato når S er definert i koden.

## 8. Slik sjekkes det etter 07.10

- `shadow/run_manifest.csv` på GitHub skal ha en linje med status `ok` og
  `iso_week` 2026-W41, og `shadow/snapshots/champion_v1_0/2026-W41.csv` skal
  finnes.
- `python shadow_oos.py kontroller` (med `GITHUB_TOKEN` satt leses repoet på
  GitHub, ellers den lokale kopien) skal svare «ingen avvik».
- Første snapshot gir `watch_active_at_start` for Henry Hub og jernmalm, og
  ellers ingen hendelser, hvis tallene er som 30.09.
