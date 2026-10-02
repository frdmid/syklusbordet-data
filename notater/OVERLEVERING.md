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

## Slik går en uke (helt automatisk)

1. **GitHub Actions, `ukentlig.yml`**, onsdag 06:00 UTC:
   `kapitulasjon_d.py` → `priser.py` (alle prissegmenter, COT, kurve, VIX,
   dollar, kaller `flagglogg.py`) → `shipping.py` (Fearnleys, arkiverer PDF)
   → `bygg_shipping.py`, som til slutt kaller `endringer.uke()` og
   `helse.kjor()`. Skriptene skriver til repoet gjennom GitHub-API med
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
  55 per 30.09; Cowork kan ha publisert senere).
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

## Fallgruver

- **Loggen:** før dato og klokkeslett fra `TZ=Europe/Oslo date`, ikke anslå.
  Innslaget skal i samme commit som endringen. Ingen tankestrek i tekst.
- **OneDrive:** Frodes kopi av repoet ligger i en OneDrive-mappe. 01.10 la en
  commit fra Frode en eldre `LOGG.md` på main, og tre innslag forsvant (Cowork
  satte dem inn igjen). Se etter at egne innslag fortsatt står.
- **Push:** `git pull origin main` før arbeid; push til main og til egen
  gren, med nye forsøk (2, 4, 8, 16 s) ved nettverksfeil eller 503.
- **raw.githubusercontent** cacher; bruk `?cb=$RANDOM` og
  `Cache-Control: no-cache`. GitHub-API er sikrere for ferske filer.
- **FRED** henger med nettleser-UA; bruk `User-Agent: Syklusbordet`.
- **SEC** krever en User-Agent med kontaktinfo.
- Nettilgang i Code-økten er åpen for SEC, Yahoo, FRED og selskapenes sider.
- Ting som kan se ut som feil, men ikke er det: uran har ingen
  instrumenter før uransonden er kjørt; real lik nom de siste månedene i
  shipping (deflatoren slutter før serien).

## Åpne punkter per 02.10.2026

- Varselboksen sier «B er målt for fem»; det er seks metaller pluss rigger.
  Kan regnes i koden på samme måte som C-tellingen.
- Forslag om en ekstra rutine torsdag som kjører onsdagsrutinen på nytt hvis
  databasen ikke har ukens tall. Ikke bestilt.
- 07.10: første ukekjøring med Fearnleys-arkivet (rundt 18 MB første gang,
  de 41 rapportene som ikke kan leses) og helse.json fra arbeidsflyten.
- Neste kvartalskjøring: nikkel og tinn ventes å gå fra stengt til åpen etter
  Coworks Glencore-regel 01.10.
- Parallelt signal for Brent og WTI (detrendet A 95 eller mer) holdes etter
  regelen fra desember 2025 til desember 2027.
