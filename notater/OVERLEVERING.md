# Overlevering: Syklusbordet

Skrevet 02.10.2026 av Claude Code for en ny økt som skal ta over. Les
`notater/LOGG.md` først (nyeste øverst), så dette. Loggen er fasit når de to
er uenige; oppdater dette notatet når noe her endrer seg, og før det i loggen.

## Hva prosjektet er

Et dashbord som viser hvor lavt hvert sykliske råvare- og shippingsegment
ligger mot sin egen realprishistorikk, med handlbare papirer under hvert
segment. Frode bruker det til å se etter bunner. Skårene:

- **A** prisnivå: persentil av realprisen mot egen historikk (rå, detrendet
  og rullende ti år). Bunnsone krever rå og detrendet A på 80 eller mer.
- **B** tilbud: investeringer delt på avskrivninger over fem år (B2), fra SEC
  og fra `b_manuell.json`; rigger egen beregning i `rigg_b.py`.
- **C** overlevelsesport: kvartaler kontantene holder i selskapets verste år.
  Under 8 er porten stengt. Fra SEC og fra `c_manuell.json`.
- **D** kapitulasjon: hvor langt papirene er falt, mot egen historikk.
- Kontekst uten skår: trend, COT, kurveform, VIX, dollar, rater.

Alt som er testet, står med test og resultat i toppen av skriptet og i
loggen. Regler og terskler settes før kjøring og flyttes ikke etterpå.

## Hvem eier hva

- **Cowork-økten** eier `c_manuell.json`, `c_manuell.py`, `b_manuell.json` og
  `b_manuell.py` (tall lest for hånd fra årsrapporter). Claude Code leser dem,
  men endrer dem ikke. Trengs en endring, skriv en instruks til Cowork.
- **Claude Code** utfører det meste annet: skript, sonder, dashbordet,
  rutiner. Frodes ord: «Cowork eier fortsatt, Code utfører der det er mulig».
- Claude Code får ikke endre `CLAUDE.md` (blokkert). Endringer der gjør
  Frode eller Cowork.
- Arbeidsflytfilene i `.github/workflows/` kan ikke endres herfra. Nye steg
  kalles derfor sist i et eksisterende skript (se under).
- **Ingen kontoer:** ingen økt får opprette konto, registrere seg, be om demo
  eller prøve, eller melde Frode på noen tjeneste (Frodes regel 05.10.2026).
  Trengs en ny kilde med innlogging eller API-nøkkel, foreslå den, og la
  Frode opprette kontoen selv.

## Slik går en uke (helt automatisk)

1. **GitHub Actions, `ukentlig.yml`**, onsdag 06:00 UTC:
   `kapitulasjon_d.py` → `priser.py` (alle prissegmenter, COT, kurve, VIX,
   dollar, kaller `flagglogg.py`) → `shipping.py` (Fearnleys, arkiverer PDF)
   → `bygg_shipping.py`, som til slutt kaller `endringer.uke()`,
   `helse.kjor()` og `shadow_oos.kjor_actions()` (Shadow-OOS fra 07.10.2026;
   den kaller Challengerne og til slutt `kontekst_laks.py` og
   `kontekst_regime.py`). Skriptene skriver til repoet gjennom GitHub-API med
   `GITHUB_TOKEN`; commits heter «oppdatert ...» og føres ikke i loggen.
2. **Rutinen `trig_01HoJvyjwZRq5J4QNcXoFkr3`** («Syklusbordet: oppdater
   dashbordet fra GitHub»), onsdag rundt 09:16 UTC: henter filene fra repoet
   og skriver dem til dashbordets database. Prompten har stegene 1 til 8 (6b
   VIX, 6c dollar, 6d endringer, 6e helse, 6f gass_b, 6g laks_biomasse, 6h
   alu_tilbud skal ikke røres, 6i regime fra 15.10; 8 ukeloggen i prosjektet
   «Handelsalgoritme»). Endres med RemoteTrigger `update` og body
   `{"prompt": ...}`; kontroller etterpå at bare prompten er endret. Den
   prøver ikke på nytt hvis den feiler; det skjedde 30.09, og den ble kjørt
   på nytt for hånd.
3. **Dashbordet** leser databasen når det åpnes. Det trenger ikke publiseres
   for at nye tall skal vises.

**Kvartalsvis, `kvartalsvis.yml`** (5. feb, mai, aug, nov 07:00 UTC):
`tilbud_b.py` (kaller `rigg_b.py` til slutt) → `overlevelse_c.py` (kaller
`endringer.kvartal()` til slutt). Kan også startes for hånd i Actions
(«Kvartalsvis tilbudsskaar»), og Cowork ber om det etter endringer i
`c_manuell.json`.

**Sonder, `sonder.yml`** («ad hoc»): `sonde_ad_hoc.py` kjører alle
`sonde_kjor_*.py` som ikke står i `sonder_ferdige.txt`, og legger utskriften i
`sonder/<navn>.txt`. Ny sonde = ny fil `sonde_kjor_<navn>.py`; regler og
kriterium skrives i toppen før kjøring. Ferdig sonde føres i
`sonder_ferdige.txt`.

## Dashbordet

- Adresse: https://claude.ai/artifact/5fSPzKWdZhhV1vWB6DNZbF (siste versjon
  66 per 15.10; Cowork kan ha publisert senere). Nytt fra 12.10: linjen
  «Kull, rullende A 95» i kullpanelet (v63), boksen «Regime nå» øverst (v64)
  med «Hva testene sier om å handle» under (v65, rettet i v66).
- **Omslaget:** filen som Artifact `read` lagrer, begynner med vertens omslag
  (`<!doctype html><html><head><meta charset=utf8>...<body>`) og slutter med
  `</body></html>`. Ta bort begge før publisering, ellers kommer omslaget to
  ganger. Filen som publiseres skal begynne med `<title>Syklusbordet</title>`.
- Uten Playwright: server filen med `python -m http.server` og test i
  nettleserpanelet (konsoll, og `scrollWidth` lik bredden ved 390 px).
- Database: samlingen `segments` (ett dokument per segment, id lik
  segmentets id, inkludert `ship_*`) og samlingen `marked` med dokumentene
  `vix`, `dollar`, `endringer`, `helse`, `gass_b` og `laks_biomasse` (de to
  siste fra 07.10, skrevet av Challengeren for gass og av `kontekst_laks.py`,
  som `shadow_challenger.kjor` kaller hver uke), `regime` (fra 15.10, skrevet
  av `kontekst_regime.py` samme sted) og `alu_tilbud` (fra 12.10, skrevet for
  hånd månedlig med `alu_tilbud_privat.py` fra IAI-fila i `data_privat/`).
- **Kildekoden finnes bare i selve dashbordet.** Les alltid siste versjon med
  Artifact `read` før du endrer noe, og bygg på den. Ellers overskrives den
  andre øktens arbeid.
- **Etter hver publisering:** kontroller at `<title>Syklusbordet</title>` og
  `:root{ --ground:#f4f4f1 ...}` står øverst. Coworks versjon 54 mistet dem
  (lys modus ble fargeløs), og omslaget kom med to ganger.
- Test med Playwright før publisering: ingen feil i konsollen, ingen
  sidevis rulling ved 390 px. Innbakte data (`SEED`, `ENDR_SEED`,
  `HELSE_SEED`) brukes bare når databasen ikke svarer.

## Viktige filer

| Fil | Gjør |
|---|---|
| `priser.py` | Alle prissegmenter, deflator, skårer, logg i `index.json` |
| `instrumenter.py` | Papirene per segment (målt, ikke valgt på fortelling) |
| `kapitulasjon_d.py` | D per papir og segment, `d_kapitulasjon.json` |
| `signaler.py` | Regler for trend og kurveform (brukt av `kurve_innhent.py` og `timing_motor.py`; feltene på bordet regnes i `priser.py`) |
| `flagglogg.py` | Ukelogg i `logg/` (flagg, kurser, hendelser, 60/40) |
| `shipping.py`, `bygg_shipping.py` | Fearnleys og skipssegmentene |
| `tilbud_b.py`, `rigg_b.py` | B for metaller og rigger |
| `overlevelse_c.py` | C fra SEC, bruker `c_manuell.py` for resten |
| `endringer.py` | Endringsboksen, bilder i `logg/endringer_snap.json` |
| `helse.py` | Datahelse, etterslep per kilde står i toppen |
| `shadow_oos.py` | Shadow-OOS: ukens frosne snapshot, hendelser og manifest i `shadow/`, bare tillegg. Plan og spørsmål i `notater/shadow_oos_plan.md` |
| `shadow_challenger.py` | Challengere: registrering (`registrer <spesifikasjon.json>`) og ukentlig kjøring som egne grener. Regler i `challengers/<id>.py`, config i `config/challengers/`. Ikke frosset med Champion |
| `challengers/` | Reglene for Challengerne (`<navn>.py`) og spesifikasjonene (`spes_<id>.json`); fem stykker per 15.10, se Åpne punkter |
| `kontekst_laks.py`, `kontekst_regime.py` | Kontekst til dashbordet (`laks_biomasse.json`, `regime.json`), kalt fra `shadow_challenger.kjor`. Ikke hashet av noen modell |
| `serier/priser_mnd.csv` | Hele månedsserien (nominell og real) per råvaresegment, skrevet av `priser.py` hver uke, til Challengere |
| `test_shadow_oos.py` | Testene for shadow (`python test_shadow_oos.py`, lokalt, skriver ikke til repoet) |
| `config/champion_v1_1.json` | Frosne regler for Champion v1.1 (fra 14.10.2026) og sha256 for de 16 kodefilene. `config/champion_v1_0.json` er v1.0, avløst fordi D hadde feil kursdata |
| `shadow/` | `model_registry.csv`, `snapshots/`, `inndata/`, `shadow_events.csv`, `shadow_outcomes.csv` (tom), `correction_log.csv`, `run_manifest.csv` |

## Fallgruver

- **Loggen:** før dato og klokkeslett fra `TZ=Europe/Oslo date`, ikke anslå.
  Innslaget skal i samme commit som endringen. Ingen tankestrek i tekst.
- **Lokal kopi:** Fra 02.10 ligger Frodes arbeidskopi i
  `C:\Users\FrodeMidjo\kode\syklusbordet-data`, utenfor OneDrive. Den gamle
  kopien i OneDrive (under `Skrivebord\Syklusbordet_linket`) skal ikke brukes.
  01.10 la en commit derfra en eldre `LOGG.md` på main, og tre innslag
  forsvant. Se likevel etter at egne innslag fortsatt står.
- **Git på Frodes maskin:** ikke i PATH. Bruk den som følger med GitHub
  Desktop: `%LOCALAPPDATA%\GitHubDesktop\app-<versjon>\resources\app\git\cmd\git.exe`.
- **Push:** `git pull origin main` før arbeid; push til main og til egen
  gren, med nye forsøk (2, 4, 8, 16 s) ved nettverksfeil eller 503.
- **raw.githubusercontent** cacher; bruk `?cb=$RANDOM` og
  `Cache-Control: no-cache`. GitHub-API er sikrere for ferske filer.
- **FRED** henger med nettleser-UA; bruk `User-Agent: Syklusbordet`.
- **SEC** krever en User-Agent med kontaktinfo.
- Nettilgang i Code-økten er åpen for SEC, Yahoo, FRED og selskapenes sider.
- **Shadow-OOS:** filene i `shadow/` og `config/champion_*.json` rettes
  aldri for hånd. En feil føres i `shadow/correction_log.csv` (ny linje,
  originalen står). Endringer i en av de 16 kodefilene i config merkes som
  `code_changed` i snapshotet fra uken etter. Frodes regel: endret regelkode
  gir en Challenger med egen startdato, en frosset Champion endres aldri
  (unntak: implementasjonsfeil, da ny Championversjon, slik v1.1). Si fra i
  loggen hva endringen er. Uken i shadow går fra onsdag til tirsdag, og
  referansene er OSEBX og MSCI World (`IWDA.L`), side om side.
- Ting som kan se ut som feil, men ikke er det: uran har ingen
  instrumenter før uransonden er kjørt; real lik nom de siste månedene i
  shipping (deflatoren slutter før serien).

- **Repoet er offentlig.** Data med vilkår om personlig bruk (IAI) skal aldri
  inn i repoet; de ligger i `data_privat/` (ignorert av git) og går bare til
  det private dashbordet.
- **Python** ligger ikke i PATH på Frodes maskin; bruk `py`.
- **KPI med basisår 2015:** Eurostat (HICP), ECB og SSB (03013) har ikke data
  etter desember 2025 i de gamle seriene. Nye sonder og Challengere bør ikke
  hvile på dem; trend eller nye serier med basisår 2025.

## Status og åpne punkter per 15.10.2026

**Modeller i Shadow-OOS**
- Champion v1.1 fra 14.10.2026 (D rettet til dagskurser 12.10; v1.0 har bare
  W41, feilene står i `shadow/correction_log.csv`). Første kjøring 14.10 var
  ok, uten `code_changed`.
- Challengere (alle med egen startdato, registrert før de ser data):
  `challenger_laks_tilbud_v1` (laks: A i EUR 70+ og biomasse lavere enn året
  før), `challenger_gass_rigger_v1` (Henry Hub: lav pris og færre gassrigger;
  skriver `gass_b.json`), `challenger_olje_rigger_v1` (Brent og WTI: lav pris
  og færre oljerigger), alle fra 14.10; `challenger_kull_ar95_v1` (kull:
  rullende A 95 og detrendet A 80, Frodes valg, ikke testet som regel) og
  `challenger_bred_nedgang_v1` (Championens bunnsone bare når 40 % eller færre
  av råvarene er i oppgang), begge fra 21.10. **21.10: manifestet skal ha
  Champion og fem Challengere ok.**
- B på bordet er ikke endret (Frodes beslutning 12.10). Tilbudsmålene er
  Challengere eller kontekst, aldri `scores.B`.

**Regimepanelet** (fra 15.10, `kontekst_regime.py`, `regime.json`, steg 6i)
- Vekst = andel råvarer i oppgang over 12 mnd (testet, holdt). Sjokk = VIX og
  korrelasjonen mellom papirene (valgt etter at sondens eget mål feilet med
  ett poeng på covid; begge klarte samme krav). Boom = median A (fanger bare
  toppene). Likviditet = Feds netto likviditet, reverse repo, Fed + ECB + BoJ
  (beskrivende, for kort historikk). Analoger. Kontekst, ikke testet som
  signal. Felt `nedgang_siden` og `sjokk_siden` kommer fra 21.10.
- Funn (`sonde_kjor_regime*`, `sonde_kjor_ventetid_hold`): bunnflagg i bred
  nedgang har gitt +33 % mot -3 % over 24 mnd (holder; ikke på 1 til 12 mnd).
  Sjokk og likviditet holder ikke eller kan ikke avgjøres. Inngang ved start
  på bred nedgang har gitt fall videre; å vente 9 mnd unngår fallet, men
  papirer kjøpt da har ikke gjort det bedre enn en tilfeldig måned for noen
  holdetid (1 til 24 mnd) og har ligget under S&P 500. Teksten under panelet
  sier dette.

**Andre funn 12. til 15.10** (detaljer i loggen)
- Terminkurven varsler verken A eller papirene for WTI og Henry Hub.
- Felles A 80 står; tilpasning per råvare (grupper, halveringstid,
  krymping) holdt ikke. Jernmalm har for kort serie til å tilpasses.
- Test-flagget (B2 og D papirer) holder ikke med dagskurser
  (`sonde_kjor_b_signal_v2`); Frode avgjør hva som skjer med det.

**Praktisk**
- Kvartalsvis tilbudsskår kjørt for hånd 14.10 uten endringer. Neste
  planlagte 5. november.
- FRED svarer ikke fra Frodes maskin; det som trenger FRED, kjøres i Actions
  (sondeflyten «ad hoc»).
- Grenen `forbered-privat-repo` er laget fra eldre main og har gammel
  `kapitulasjon_d.py`; flett main inn før den tas i bruk. Repoet gjøres ikke
  privat før Frode bestemmer det.
- Varselboksen sier «B er målt for fem»; det er seks metaller pluss rigger.
- Forslag om en ekstra rutine torsdag som kjører onsdagsrutinen på nytt hvis
  databasen ikke har ukens tall. Ikke bestilt.
- Onsdagsrutinen skal ikke vise shadow-status; si fra til Frode i den aktive
  prosjektchatten når noe må avgjøres.
- Parallelt signal for Brent og WTI (detrendet A 95 eller mer) holdes etter
  regelen fra desember 2025 til desember 2027.
