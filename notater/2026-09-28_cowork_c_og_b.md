# C for olje og B for jernmalm, 28.09.2026

Notat fra Cowork-økten, slik at andre økter kan lese hva som er gjort.
Kodeøkten sitt notat (2026-09-28_backtest.md) er lest.

## Overlevelsesporten C utenfor SEC

- Nytt: `c_manuell.py` og `c_manuell.json`. `overlevelse_c.py` leser dem
  for papirer uten SEC-tall. Samme regnestykke og port som SEC-delen.
  Driftsår i annen valuta regnes om med Norges Banks årssnitt.
- Aker BP (kvartalsvis kjøring 28.09 kl. 13:48): åpen, 23,0 kvartaler,
  verste år 2006 (Pertra), netto gjeld/EK 0,54. Brent-porten er åpen.
- DNO (lagt inn nå, regnes ved neste kvartalsvise kjøring): prøvekjørt til
  trang, 10,1 kvartaler, verste år 2015 (−74,1 MUSD), netto gjeld/EK 0,40.
  2008 og 2009 mangler. Faller et av dem under −121 MUSD, blir porten stengt.
  NewsWeb-vedlegg hentes med
  `https://api3.oslo.oslobors.no/v1/newsreader/attachment?messageId=..&attachmentId=..`.
- Whitecap: selskapets sider ga ingen PDF-er. WTI-porten er åpen via Cenovus.

## Tilbudsskåren B for jernmalm

- Ny `b_manuell.json`, lest av `tilbud_b.py` (del 2b).
- Kumba: capex 2007–2025, med kapitalisert avdekking fra 2012 (IFRIC 20).
- Vale, jernmalmsegmentet: 2016–2025. Investeringer mot segmentets
  avskrivninger.
- Champion: FY2021–FY2026.
- Tall per selskap (capex / avskrivning, siste år): Kumba 1,63,
  Vale 1,82, Champion 2,19.
- Prøvekjørt med grove valutakurser: B1 = 20, B2 = 0. Bransjen investerer
  rundt 1,9 ganger avskrivningene. Det er ingen tilbudsknapphet. Endelige
  tall kommer fra den kvartalsvise kjøringen.
- Regelen om tynne år kutter år der under halve kurven har tall. Serien
  blir derfor 2016–2025, til Fortescue er inne.
- `sonde_kjor_b_fmg.py` henter Fortescue sine årsrapporter
  (FY2008–FY2026). Kontantstrøm, avskrivninger og segmentnote skrives ut,
  slik at investeringene i Fortescue Energy kan trekkes fra.

## Til kodeøkten

- B for jernmalm kan brukes i den foreslåtte testen «flagget kombinert
  med B» når Fortescue er inne. Kumba går tilbake til 2007, Vale bare til
  2016.
- Jeg rører ikke sonder_ferdige.txt i denne runden.
