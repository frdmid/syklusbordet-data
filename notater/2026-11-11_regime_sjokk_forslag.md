# Forslag: sjokkfeltet i regimepanelet deles i to

Skrevet 11.11.2026 av Claude Code på Frodes forslag: sjokkfeltet deles i to
for VIX, månedssnitt av VIX som nivå og månedssnitt av VVIX som volvariasjon,
og begge må over persentil 80 for å kalles forhøyet. Frode ba om et forslag
til skala og innslagspunkter. Ingenting er bygget; `kontekst_regime.py` er
uendret. Tallene under er målt 11.11.2026 og kan kontrolleres med skriptene
som er nevnt nederst.

**Dette er en visning, ikke en regel.** Sonden `sonde_kjor_vvix_sjokk`
(11.11.2026) viste at verken VIX-nivå, VIX-spredning eller VVIX skiller
utfallene etter bunnsonen. Tersklene under er valgt, ikke målt, og
varighetskravet er valgt etter å ha sett hvilke måneder som flimrer. Det er
greit for kontekst, men det må stå på panelet, slik at ingen senere leser
feltet som evidens.

## Hvorfor forslaget passer bordet

Strukturen er den samme som A alt har: to ledd som begge må over 80.

| A | Sjokkfeltet |
|---|---|
| A rå over 80 og A detrendet over 80 gir bunnsone | Nivå over 80 og volvariasjon over 80 gir forhøyet |
| Bare A rå over 80 gir oppsikt | Bare ett ledd over 80 gir uro |

Bordet får dermed ett ordforråd i stedet for to. Det taler for 80 som grense
framfor et nytt tall.

## Det som må løses først

**1. Samme tall betyr ikke det samme på de to leddene.** Med dagens voksende
persentil ligger VVIX over 80 i 33,0 % av månedene og VIX i bare 10,6 %. Da er
«begge over 80» i praksis «VIX over 80», og volvariasjonen bidrar nesten
ingenting. Årsaken er at de to vinduene er ulike: VIX måles mot alt fra 1990
med 2008 inne, VVIX bare mot 2007 og framover.

Forslag: bruk **rullende tiårsvindu for begge**, som `rolling_pct` i
`priser.py` gjør for Ar. Da blir balansen 16,8 % mot 29,6 %, og spørsmålet er
det samme for begge ledd: er dette høyt mot det siste tiåret? Antall måneder
med begge over 80 går fra 14 til 22 av 179, og listen blir mer sammenhengende.
Den fanger blant annet februar 2020, måneden før covid, der nivå leste 82 og
volvariasjon 88.

**2. Ordet flimrer.** Uten varighetskrav skifter ordet 39 ganger på 179
måneder, og 30 % av periodene varer én måned. Det er ikke et regime.

Et symmetrisk krav om to måneder på rad løser flimmeret, men gjør noe verre:
tollsjokket i april 2025 (nivå 98, volvariasjon 94) og mars 2026 (88 og 93)
leses som **rolig**, fordi de var enkeltmåneder. Et sjokk må registreres i
måneden det skjer.

Forslag: **inn med én gang, ut etter to måneder under**. Da er ingen av de
kjente sjokkmånedene lest som rolig, skiftene faller til 37, median periode
blir tre måneder, og andelen perioder på én måned faller fra 30 til 21 %.

**3. Volvariasjon finnes ikke før desember 2011.** VVIX har dagsdata fra
3. januar 2007, og med minst 60 måneder starter persentilen i desember 2011.
204 måneder av VIX-historikken har dermed ikke noe volvariasjonsledd.

Forslag: feltet viser **ukjent** for volvariasjon før desember 2011, og ordet
settes da av nivåleddet alene og merkes «volvariasjon ukjent». VVIX holdes
**utenfor `dims`** i analogavstanden, ellers forsvinner LTCM 1998,
11. september og IT-boblen fra analoglisten, fordi `dims` bruker `dropna()`
over alle dimensjoner.

**4. Papirkorrelasjonen må flyttes ut av ordet.** I dag er sjokk
`max(vix_pct, korr_pct)`. Deles VIX-delen i to, blir `max()` over tre ledd et
ord som står på nesten hele tiden.

Forslag: korrelasjonen blir et **tredje tall som vises, utenfor ordet**, til
den er målt på samme måte. Jeg har ikke målt korrelasjonens historikk her, så
den skal ikke foldes inn på antagelse.

## Forslag til skala

To ledd, begge månedssnitt av dagsdata, begge som rullende tiårspersentil med
minst 60 måneder:

- **nivå** = månedssnitt av VIX
- **volvariasjon** = månedssnitt av VVIX

Per ledd: under 80 er normal, 80 og over er forhøyet, 95 og over er høy.

Ordet settes av paret, med inngang etter én måned og utgang etter to måneder
under:

| Nivå | Volvariasjon | Ord | Andel av 179 mnd |
|---|---|---|---|
| 95 og over | 95 og over | **sjokk** | 2,8 % |
| 80 og over | 80 og over | **forhøyet** | 12,8 % |
| 80 og over | under 80 | **spent nivå** | del av 27,4 % |
| under 80 | 80 og over | **urolig forventning** | del av 27,4 % |
| under 80 | under 80 | **rolig** | 57,0 % |

De to enkeltleddstilstandene er med vilje ikke slått sammen til ett ord, for
de betyr motsatte ting:

- **spent nivå** (nivå høyt, volvariasjon ikke): uroen er priset og stabil.
  Juni 2022, inflasjonstoppen, leste nivå 95 og volvariasjon 61. En seig
  nedgang, ikke et sjokk. Sjelden: 5 av 179 måneder på den voksende
  persentilen.
- **urolig forventning** (volvariasjon høy, nivå ikke): markedet er usikkert
  på usikkerheten, ofte før en bevegelse. Februar 2018 leste nivå 74 og
  volvariasjon 100, august 2015 nivå 62 og volvariasjon 92. Dette er den
  vanlige av de to.

## Slik leser de kjente månedene seg

| Måned | Hendelse | Nivå | Volvar | Ord |
|---|---|---|---|---|
| 2015-08 | Kina og oljefallet | 62 | 92 | urolig forventning |
| 2018-02 | volmageddon | 74 | 100 | urolig forventning |
| 2018-12 | renter og handelskrig | 87 | 78 | forhøyet |
| 2020-02 | måneden før covid | 82 | 88 | forhøyet |
| 2020-03 | covid | 100 | 100 | sjokk |
| 2021-01 | meme-aksjene | 88 | 97 | forhøyet |
| 2022-03 | Ukraina | 95 | 92 | forhøyet |
| 2022-06 | inflasjonstoppen | 95 | 61 | spent nivå |
| 2025-04 | tollsjokket | 98 | 94 | forhøyet |
| 2026-03 | mars 2026 | 88 | 93 | forhøyet |
| 2026-10 | nå | 44 | 59 | rolig |

Sjokktrinnet står i fem måneder i hele perioden, alle i 2020. Det er strengt
med hensikt: et ord som brukes hvert år er ikke et sjokk.

## Resten som må med

- **Hel måned.** En måned med under 15 handledager tas ikke med, slik
  `priser.py` kaster en påbegynt måned. Den påbegynte måneden kan vises for
  seg, merket som ufullstendig. Per 11.11 leser november 2026 nivå 21,29 og
  volvariasjon 108,61 på elleve dager, altså høyere enn oktober.
- **Panelet står på forrige måned.** `siste` krever bredde og median A fra
  månedsserien, så ordet leses på oktober selv om VIX er kjent til i dag. Det
  bør stå ved feltet, eller de to VIX-leddene bør vises for inneværende måned
  ved siden av regimeordet.
- **Ingen Challenger trengs.** Regime er kontekst og ligger ikke blant
  Championens hashede filer. Skal noen av disse leddene inn i et signal, må
  det bli en Challenger med egen startdato.

## Hvis forslaget skal bygges

Endringene ligger i `kontekst_regime.py` (nytt VVIX-kall, rullende persentil
for begge ledd, hysterese, de fem ordene, `dims` uendret) og i dashbordets
regimeboks. Onsdagsrutinens punkt 6i må få de nye feltnavnene i kravene sine.
Tallene over er målt med `maal_skala.py`, `maal_skala2.py` og
`maal_skala3.py`; de lå i arbeidsmappen og er ikke committet, siden sonden
`sonde_kjor_vvix_sjokk.py` dekker den delen som skal stå i repoet. Skal
tallene kunne regnes på nytt senere, bør målingen legges inn som en egen
sonde.
