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

Siden prøver tre kilder i denne rekkefølgen, og velger på **friskhet** og ikke
på hvem som svarer først:

1. `dashbord/data.json` fra det offentlige repoet, hentet med cache-brekk.
   Den er fersk i samme sekund som GitHub Actions er ferdig.
2. Dashbordets egen database, som onsdagsrutinen fyller en time senere.
3. De innbakte dataene i `index.html`, som siste utvei.

Siden skriver hvilken kilde som ble brukt i tabellen Datahelse, så en gammel
kilde ikke kan se fersk ut. Databasen er altså ikke slått av: feiler `bygg.py`,
eller blir filen avvist, viser dashbordet det databasen har, som før.

De innbakte dataene er beholdt i filen selv om de er store. Et byggesteg som
baker dem inn ved publisering ville spart plass, men lagt til en feilmåte der
en publisering uten innbaking gir en side uten siste utvei.

## alu_tilbud skal aldri i repoet

`marked/alu_tilbud` er produksjonstall fra IAI med vilkår om personlig bruk,
og repoet er offentlig. Dokumentet ligger bare i databasen og i `data_privat/`.
Tre sperrer holder det der, og ingen av dem skal fjernes:

1. `bygg.py` har `alu_tilbud` i `FORBUDT` og en `assert` før filen skrives.
2. `index.html` avviser en `data.json` som inneholder dokumentet.
3. `index.html` henter alltid `alu_tilbud` fra databasen, aldri fra repoet.

## Når noe skal endres

Endrer du lastelogikken, kjør `kontroller.py` og test lokalt først:

```
py -X utf8 -m http.server 8742 --bind 127.0.0.1
```

Test minst fire tilfeller, alle fire er prøvd 12.11.2026: en gyldig
`data.json`, en som mangler (404), en med for få segmenter, og en som
inneholder `alu_tilbud`. I alle tre siste skal siden falle tilbake og si det i
tabellen Datahelse. Kontroller også at ingenting er bredere enn 390 piksler.

Merk at en testkopi med en lokal `DATA_URL` aldri skal publiseres;
`kontroller.py` stopper det.
