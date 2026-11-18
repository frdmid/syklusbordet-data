# Dashbordet

Fra 12.11.2026 er **denne mappen kilden** til dashbordet. Før det fantes
kildekoden bare inne i selve artifacten, og regelen var å lese artifacten før
hver endring. Den regelen er snudd: nå leses `dashbord/index.html` i repoet,
og risikoen er den motsatte, å publisere fra et utdatert arbeidstre.

**Gjør derfor alltid `git pull` før du endrer eller publiserer.**

## Filene

| Fil | Hva |
|---|---|
| `index.html` | Hele dashbordet, klar til å publiseres som den er. Ingen byggesteg, ingen omslag. De innbakte dataene (`SEED`, `ENDR_SEED`, `HELSE_SEED`) ligger i filen med vilje, se under |
| `data.json` | Tallene satt sammen av `bygg.py` av filene i repoet. Dashbordets hovedkilde |
| `bygg.py` | Setter sammen `data.json`. Kalles fra `shadow_challenger.kjor` hver uke |
| `kontroller.py` | Kjøres før publisering. Avslutter med kode 1 hvis noe er galt |

## Slik publiserer du

```
git pull origin main
py -X utf8 dashbord/kontroller.py
```

Går kontrollen gjennom, publiseres `dashbord/index.html` som den er til
artifacten https://claude.ai/artifact/5fSPzKWdZhhV1vWB6DNZbF. Filen skal
**ikke** pakkes i noe omslag: verten legger på `<!doctype html>` og
`<meta charset=utf8>` selv. Kontroller etter publisering at siden begynner med
tittelen og at lys modus har farge.

## Hvor tallene kommer fra

Siden leser to kilder, i denne rekkefølgen:

1. Dashbordets egen database, som onsdagsrutinen fyller. **Eneste vei inn.**
2. De innbakte dataene i `index.html`, som siste utvei.

Linjen over tabellen Datahelse sier hvilken av dem som ble brukt, med
databasens dato, og hvilken lastelogikk som kjører (`LASTER_VERSJON`). Den
siste er der for å avsløre en gammel side i nettleserens cache.

**Hvorfor ikke repoet, målt 18.11.2026:** fra 12.11 forsøkte siden å lese
`dashbord/data.json` fra det offentlige repoet først, fordi filen der er
fersk i samme sekund som Actions er ferdig. En publisert artifact får ikke
hente fra noe eksternt nettsted. Både `raw.githubusercontent.com` og
jsDelivr-speilet ga «TypeError: Failed to fetch» i den publiserte siden,
mens samme henting virket fra en lokal server på et annet opphav. Det er
sandkassens CSP (`connect-src`), og den kan ikke endres herfra. Hentingen er
ryddet ut i v85; koden ligger i commit ff22032.

`dashbord/bygg.py` og `dashbord/data.json` står som før. De er den
maskinlesbare kopien av ukens tall i repoet, like fersk som Actions, men
dashbordet kan ikke lese dem. En Claude-økt kan derimot kopiere `data.json`
inn i databasen med Artifact-databasen; det er ikke satt opp.

Siden skriver hvilken kilde som ble brukt i tabellen Datahelse, så en gammel
kilde ikke kan se fersk ut. Databasen er altså ikke slått av: feiler `bygg.py`,
eller blir filen avvist, viser dashbordet det databasen har, som før.

De innbakte dataene er beholdt i filen selv om de er store. Et byggesteg som
baker dem inn ved publisering ville spart plass, men lagt til en feilmåte der
en publisering uten innbaking gir en side uten siste utvei.

## alu_tilbud skal aldri i repoet

`marked/alu_tilbud` er produksjonstall fra IAI med vilkår om personlig bruk,
og repoet er offentlig. Dokumentet ligger bare i databasen og i `data_privat/`.
To sperrer holder det der, og ingen av dem skal fjernes:

1. `bygg.py` har `alu_tilbud` i `FORBUDT` og en `assert` før filen skrives.
2. `index.html` henter alltid `alu_tilbud` fra databasen, aldri fra en annen
   kilde. (Sperren i `index.html` som avviste en `data.json` med dokumentet
   falt bort med hentingen i v85, og trengs ikke: siden leser ikke repoet.)

## Om noen skulle legge henting tilbake

Siden gjør ingen nettkall utenom Google Fonts, og `kontroller.py` advarer
hvis `fetch(` kommer tilbake i filen. Skulle sandkassen en dag slippe
henting ut, gjelder to ting som er målt 18.11.2026:

- **Mål i den PUBLISERTE siden, ikke lokalt.** En side servert fra
  `127.0.0.1` henter fra et annet opphav enn artifacten gjør, og alle fire
  lastetilfellene besto lokalt 12.11 mens hentingen var død i artifacten.
- **Send ingen headere.** `Cache-Control` er ikke en trygg
  forespørselsheader, så den gjør kallet til et som krever CORS-preflight,
  og `raw.githubusercontent.com` svarer 403 på OPTIONS (200 på GET med
  `Access-Control-Allow-Origin: *`). Cache-brekken `?cb=<tid>` og
  `cache: "no-store"` er nok. Rådet om en `no-cache`-header i
  onsdagsrutinen gjelder `curl`, som ikke er underlagt CORS.

## Når noe skal endres

Endrer du lastelogikken, kjør `kontroller.py` og test lokalt først:

```
py -X utf8 -m http.server 8742 --bind 127.0.0.1
```

Lokalt finnes ingen database, så siden faller tilbake til de innbakte
dataene. Det er testen på at reserven står: 19 segmenter, 19 paneler, ingen
feil i konsollen, og linjen skal si «Tallene er de innbakte: databasen
svarte ikke». Kontroller også at ingenting er bredere enn 390 piksler.

**En lokal test kan ikke erstatte en test i den publiserte artifacten.**
Databasen finnes bare der, og en lokal side regnes som samme opphav i regler
som gjelder i artifacten. Etter publisering: åpne dashbordet og les linjen
`#datakilde` først i avsnittet over tabellen Datahelse. Den skal si at
tallene kommer fra databasen, med dato, og hvilken lastelogikk som kjører.
Står det en annen lastelogikk enn den du publiserte, ser du en gammel side
fra cache; lukk fanen og åpne på nytt.

Merk at en testkopi med en lokal `DATA_URL` aldri skal publiseres;
`kontroller.py` stopper det.
