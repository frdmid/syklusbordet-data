# Steg 1, 3 og 5 gjennomført, med robusthet først

Skrevet 12.11.2026 av Claude Code på Frodes bestilling: gjør endringene 1, 3
og 5 fra `notater/2026-11-11_gjennomgang.md`, prioriter robusthet, reduser
muligheten for at feil oppstår, og se over at koden er konsistent. Repoet
forblir offentlig, som Frode bestemte.

Vurderingen av negative følger som ligger bak valgene under, står i
prosjektchatten 12.11.2026 og er oppsummert her der den endret noe.

## Det korte

Alle tre stegene er additive. Feiler noe av det nye, oppfører bordet seg som
før: dashbordet faller tilbake på databasen, og onsdagsrutinen går uendret.
Ingen av Championens 16 hashede filer er rørt, så ingenting er merket som
kodeendring. Arbeidsflytene er ikke endret; det som krever det, står under
«Det Cowork må gjøre».

## Steg 1: miljøet

**Gjort:** `miljo_logg.py` skriver en rad per uke og plattform til
`logg/miljo.csv` med hvilke versjoner som faktisk kjørte, og sier fra når de
avviker fra `config/miljo_kjent.json`. Øvre grenser i `requirements.txt` ved
neste majorversjon.

**Ikke gjort, med vilje: eksakte pinner.** En eksakt pinne gjør stille avvik
til hard feil. Mangler et hjul for runnerens Python, stopper hele onsdagen, og
`ukentlig.yml` har ingen reserveinstallasjon. Det strider mot prosjektets eget
prinsipp fra shadow-planen, at klokken skal gå og avviket skal synes. Øvre
grenser stopper det som faktisk er farlig, et sprang over en majorversjon, og
lar sikkerhetsoppdateringer komme inn.

**Funn underveis:** `requirements.txt` krevde bare `pandas>=2.0`, og kjøringen
11.11.2026 brukte pandas 3.1.1. Flyten har altså alt krysset en majorversjon
uten at noen vet når. Det er nettopp det loggen nå fanger. Frodes maskin og
Actions er dessuten ulike (pandas 3.0.6 mot 3.1.1), og derfor er raden per uke
OG plattform: en lokal kjøring skal ikke bruke opp plassen til den som lager
dataene.

**Miljøloggen ligger ikke i `shadow/`**, som den første planen sa. Den mappen
er modellens frosne register med hashkjede og manifest, og en fil utenfor
manifestet hører ikke hjemme der.

## Steg 3: dashbordet leser repoet

**Gjort:** `dashbord/bygg.py` setter sammen `dashbord/data.json` av filene i
repoet hver uke. `dashbord/index.html` er nå kilden til dashbordet og leser
den filen først, databasen som reserve, og de innbakte dataene som siste
utvei. `dashbord/kontroller.py` kjøres før publisering.
`dashbord/README.md` har rutinen.

**Bevaringssperren er beholdt.** Rutinens punkt 5 legger tilbake felt som er
falt bort, fordi en eldre arbeidsflyt en gang slettet instrumentlister usett.
Hadde den sperren bare ligget i rutinen, ville den forsvunnet når databasen
ikke lenger er hovedkilden. `bygg.py` gjør det samme mot FORRIGE `data.json`.

**Valget mellom kildene tas på friskhet, ikke på hvem som svarer.** Ellers
kan en kilde som er nede gi et gammelt tall som ser ferskt ut. Siden skriver
hvilken kilde som ble brukt i tabellen Datahelse.

**De innbakte dataene er beholdt i filen**, ikke flyttet til `seed.json` som
planen sa. Et byggesteg som baker dem inn ved publisering sparer plass, men
legger til en feilmåte der en publisering uten innbaking gir en side uten
siste utvei. Publisering er nå en ren kopi uten byggesteg.

**Tre sperrer holder IAI-tallene ute av det offentlige repoet:** `FORBUDT` og
en `assert` i `bygg.py`, avvisning i `index.html` av en `data.json` som
inneholder dokumentet, og at `alu_tilbud` alltid hentes fra databasen. Dette
er den foreseelige feilen en senere økt kan gjøre ved å «forenkle», og ingen
av sperrene skal fjernes.

**Regelen om dashbordkilden er snudd.** Før: les artifacten først, kilden
finnes bare der. Nå: `git pull` først, kilden er i repoet. Den gamle regelen
sto i `notater/OVERLEVERING.md` og på Notion-siden og er rettet begge steder.

**Onsdagsrutinen går uendret.** Den er ikke slått av og ikke redusert. Den
fyller databasen, som nå er reserve, og den skriver ukeloggen, som er den
eneste fortellende historikken. Å redusere den er en egen avgjørelse for
Frode, og den bør tas først når to onsdager har vist at repolesingen virker.

**Prøvd 12.11.2026 i nettleserpanelet**, alle fire tilfellene: en gyldig
`data.json` (siden viser repoets tall og sier det), en som mangler, en med
for få segmenter, og en som inneholder `alu_tilbud`. I de tre siste faller
siden tilbake og sier det. Ingen feil i konsollen, ingenting bredere enn 390
piksler.

**Kostnad:** `data.json` er 832 kB og skrives hver uke, så repoet vokser rundt
40 MB i året mer enn før. Segmentfilene er alt 1,2 MB til sammen, så den
ukentlige mengden omtrent dobles.

## Steg 5: loggen og ukerapporten

**Gjort:** September og oktober 2026 er flyttet til `notater/logg/2026-09.md`
og `notater/logg/2026-10.md`, ord for ord. `notater/LOGG.md` er 25 kB i stedet
for 186 kB og har en blokk «Status nå» øverst. `ukerapport.py` skriver
`logg/uke/<uke>.md` hver uke.

**Flyttingen er kontrollert mot git:** 166 innslag før, 166 etter, identisk
mengde, ingenting mistet og ingenting lagt til. Prosjektet mistet tre innslag
01.10.2026, så kontrollen var hele poenget.

**«Status nå» har en vedlikeholdsregel i seg selv:** den oppdateres i samme
commit som endringen, og sier at den ikke er til å stole på hvis den er eldre
enn det nyeste innslaget. En blokk som leses først og ikke vedlikeholdes er
verre enn ingen blokk.

**Ukerapporten erstatter ikke rutinens rapport.** Et skript kan rapportere
fakta, men ikke diagnose, og det er rutinens tolkning som har fanget feil som
uranprisen 04.11.2026. Filen sier det selv i toppen, og at rutinens rapport
gjelder når de to er uenige. Den skrives med `opprett`, aldri `erstatt`, så
reservekjøringen ikke kan skrive over hovedkjøringen.

## Rekkefølgen i ukeflyten

`shadow_challenger.kjor` kaller nå, etter Challengerne:

1. `kontekst_laks`, `kontekst_regime`, `kontekst_uran`, `kontekst_miners`,
   `kontekst_handel` som før
2. `miljo_logg`
3. `dashbord/bygg`, som må gå etter kontekstfilene, ellers blir regime,
   gullgruver og handlingslisten en uke gamle i `data.json`
4. `ukerapport`, sist, fordi den leser miljøloggen

Hver er pakket i try/except som før, så en feil i én rammer ingen andre.

## Det Cowork må gjøre

1. **Reserveinstallasjon i `ukentlig.yml`** hvis Frode vil ha eksakte pinner
   senere: et steg som prøver `pip install -r requirements.txt` og ved feil
   faller tilbake til installasjon uten pinner, slik at en manglende hjulfil
   ikke stopper onsdagen. Uten det steget skal pinnene ikke strammes.
2. **`CLAUDE.md`**: regelen om å lese loggen bør peke til blokken «Status nå»
   og inneværende måned, og si at eldre innslag ligger i `notater/logg/`.
3. **Alle fire cron-tidene** i `ukentlig.yml` (steg 4 i gjennomgangen, ikke
   gjort her).

## Det som ikke er gjort

Steg 2 (evalueringsprotokollen for Championen) og steg 4 (cron-tidene) står
igjen. Steg 2 venter på Frodes krav; steg 4 eies av Cowork.

## Hvis noe ser galt ut

- **Dashbordet viser gamle tall:** se linjen i tabellen Datahelse. Står det
  «fra databasen», svarte ikke repoet eller filen var eldre. Står det
  «innbakte», svarte ingen av dem.
- **Et segment mangler et felt:** se `avvist` og `bevart` i
  `dashbord/data.json`. Avvist betyr at filen ikke bestod kravene og at
  forrige versjon ble båret videre.
- **Miljøet har endret seg:** kolonnen `avvik` i `logg/miljo.csv`. Et avvik er
  ikke en feil i seg selv; vurder det, og godta det ved å oppdatere
  `config/miljo_kjent.json`.
- **Rull tilbake dashbordet:** `sikkerhetskopi/2026-11-12/dashbord_v78_til_publisering.html`
  er versjonen uten repolesing.
