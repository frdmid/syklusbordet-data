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
   `helse.kjor()` og `shadow_oos.kjor_actions()` (Shadow-OOS fra 07.10.2026). Skriptene skriver til repoet gjennom GitHub-API med
   `GITHUB_TOKEN`; commits heter «oppdatert ...» og føres ikke i loggen.
2. **Rutinen `trig_01HoJvyjwZRq5J4QNcXoFkr3`** («Syklusbordet: oppdater
   dashbordet fra GitHub»), onsdag rundt 09:16 UTC: henter filene fra repoet
   og skriver dem til dashbordets database. Prompten har stegene 1 til 7 (6b
   VIX, 6c dollar, 6d endringer, 6e helse). Den prøver ikke på nytt hvis den
   feiler; det skjedde 30.09, og den ble kjørt på nytt for hånd.
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
  58 per 07.10; Cowork kan ha publisert senere).
- **Omslaget:** filen som Artifact `read` lagrer, begynner med vertens omslag
  (`<!doctype html><html><head><meta charset=utf8>...<body>`) og slutter med
  `</body></html>`. Ta bort begge før publisering, ellers kommer omslaget to
  ganger. Filen som publiseres skal begynne med `<title>Syklusbordet</title>`.
- Uten Playwright: server filen med `python -m http.server` og test i
  nettleserpanelet (konsoll, og `scrollWidth` lik bredden ved 390 px).
- Database: samlingen `segments` (ett dokument per segment, id lik
  segmentets id, inkludert `ship_*`) og samlingen `marked` med dokumentene
  `vix`, `dollar`, `endringer` og `helse`.
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
| `serier/priser_mnd.csv` | Hele månedsserien (nominell og real) per råvaresegment, skrevet av `priser.py` hver uke, til Challengere |
| `test_shadow_oos.py` | Testene for shadow (`python test_shadow_oos.py`, lokalt, skriver ikke til repoet) |
| `config/champion_v1_0.json` | Frosne regler for Champion v1.0 og sha256 for de 16 kodefilene |
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
- **Shadow-OOS:** filene i `shadow/` og `config/champion_v1_0.json` rettes
  aldri for hånd. En feil føres i `shadow/correction_log.csv` (ny linje,
  originalen står). Endringer i en av de 16 kodefilene i config merkes som
  `code_changed` i snapshotet fra uken etter. Frodes regel: endret regelkode
  gir en Challenger med egen startdato, Champion v1.0 endres aldri. Si fra i
  loggen hva endringen er. Uken i shadow går fra onsdag til tirsdag, og
  referansene er OSEBX og MSCI World (`IWDA.L`), side om side.
- Ting som kan se ut som feil, men ikke er det: uran har ingen
  instrumenter før uransonden er kjørt; real lik nom de siste månedene i
  shipping (deflatoren slutter før serien).

- **KPI med basisår 2015:** Eurostat (HICP), ECB og SSB (03013) har ikke data
  etter desember 2025 i de gamle seriene. Nye sonder og Challengere bør ikke
  hvile på dem; trend eller nye serier med basisår 2025.

## Åpne punkter per 07.10.2026

- Varselboksen sier «B er målt for fem»; det er seks metaller pluss rigger.
  Kan regnes i koden på samme måte som C-tellingen.
- Forslag om en ekstra rutine torsdag som kjører onsdagsrutinen på nytt hvis
  databasen ikke har ukens tall. Ikke bestilt.
- Shadow-OOS gikk 07.10 (Champion v1.0, uke 2026-W41, 105 rader). Frodes
  avgjørelser står i `notater/shadow_oos_plan.md`. Onsdagsrutinen skal ikke
  vise shadow-status; si fra til Frode i den aktive prosjektchatten når noe må
  avgjøres.
- 14.10: første kjøring av `challenger_laks_tilbud_v1` (laks: A_pris i EUR 70
  eller mer og biomasse lavere enn året før). Sjekk `shadow/run_manifest.csv`
  og `shadow/snapshots/challenger_laks_tilbud_v1/`.
- B for Henry Hub: `sonde_kjor_b_gass` besto kriteriet, men B1 måler mest
  overgangen til kapitaldisiplin. Frode har ikke avgjort om den skal bli
  Challenger.
- Laks: valuta tilførte ingenting til A, smoltutsett varsler ikke slakt,
  biomasse gjør det. Se loggen 07.10.
- Parallelt signal for Brent og WTI (detrendet A 95 eller mer) holdes etter
  regelen fra desember 2025 til desember 2027.
