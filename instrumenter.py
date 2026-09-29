# Instrumenter per segment, valgt paa maaling og ikke paa fortelling.
#
# Kilde: sonde_ikz.py, kjort 2026-09-22. 203 papirer, 4554 par, maalt i dollar
# og i realpriser mot den samme deflatoren som raavarene.
#
# Utvalgskrav:
#   1. Handlbart paa IKZ hos Nordnet. Ingen ETC, ingen ETN, ingen ETF med
#      amerikansk domisil. UCITS-fond paa Xetra, London eller Amsterdam, og
#      enkeltaksjer paa Oslo, Stockholm, Kobenhavn, Helsinki, London, Xetra,
#      Amsterdam, Paris, SIX, USA og Toronto.
#   2. Okonomisk begrunnet paa forhaand. Ingen treff funnet ved leting.
#   3. Minst 72 maaneder i det faste vinduet fra 2016-01.
#   4. Korrelasjon i manedlige realendringer, og den samme korrelasjonen etter
#      at verdensindeksen er tatt ut. Begge maa holde. Et papir som bare folger
#      markedet er ubrukelig som raavareeksponering uansett raatall.
#
# Tallene i kommentarene: r = korrelasjon i maanedsendringer, rm = samme etter
# markedet, b = utslag per enhet raavare over tolv maaneder, f = papirets
# tolvmaanedersavkastning fra daterte bunner delt paa raavarens.
#
# Den overlappende tolvmaanederskorrelasjonen er IKKE brukt til utvelgelse.
# Den ga Maersk mot kobber 0,81 og Nutrien mot gass 0,82, altsaa den felles
# makrosyklusen fra 2016 til 2026 og ikke en sammenheng. Maanedstallet skiller:
# Maersk mot kobber faller fra 0,81 til 0,20.
#
# retning "-" foran kommentaren = omvendt eksponering. Papiret stiger naar
# raavaren faller, fordi raavaren er en kostnad og ikke en inntekt. Inngangen
# er da raavarens topp og ikke dens bunn.
#
# Fjernet fra bordet 2026-09-22: fiskemel, urea, kaffe, te, kokosolje, gummi og
# kalium. De seks forste fordi ingen av dem hadde et handlbart instrument over
# 0,30 i maanedskorrelasjon: oppdretterne laa paa 0,07 mot fiskemel og Nutrien
# paa 0,05 mot urea. Kalium fordi prisen er administrert i hele historikken,
# segmentet aldri fikk en prisnivaaskaar, og papirene derfor aldri ble maalt.

INSTR = {
"brent": [
  ("IOGP.L","London","iShares Oil & Gas Exploration & Production UCITS","ETF",
   "r 0,67  rm 0,63  b 0,64  f 0,54. Reneste uttrykket i universet: fond, ikke ETC, og nesten alt gjenstaar etter markedet."),
  ("DNO.OL","Oslo","DNO","aksje",
   "r 0,68  rm 0,57  b 1,08  f 0,95. Hoyeste raatall. Mer selskapsrisiko, og nedbetaen (0,75) er hoyere enn oppbetaen (0,45)."),
  ("AKRBP.OL","Oslo","Aker BP","aksje",
   "r 0,64  rm 0,48  b 0,72  f 0,97. Fanget nesten hele oppgangen fra daterte bunner, men bare 0,27 fra topper.")],
"wti": [
  ("CVE.TO","Toronto","Cenovus Energy","aksje",
   "r 0,71  rm 0,64  b 0,98  f 0,50. Sterkeste par i hele sonden. Raffinering demper: fangsten fra bunn er bare halve raavarens."),
  ("WCP.TO","Toronto","Whitecap Resources","aksje",
   "r 0,69  rm 0,57  b 0,83  f 0,38. Nedbeta 1,18 mot oppbeta 0,21. Folger WTI ned langt villigere enn opp."),
  ("IOGP.L","London","iShares Oil & Gas Exploration & Production UCITS","ETF",
   "r 0,66  rm 0,62  b 0,72  f 0,42. Samme fond som paa Brent. Symmetrisk og uten enkeltselskapsrisiko.")],
"henryhub": [
  ("BIR.TO","Toronto","Birchcliff Energy","aksje",
   "r 0,30  rm 0,32  b 1,00  f 0,65. Svakt segment. Ingen instrument naadde 0,31."),
  ("TOU.TO","Toronto","Tourmaline Oil","aksje",
   "r 0,30  rm 0,31  b 0,54  f 0,60. Storst kanadisk gassprodusent, lavere utslag enn Birchcliff."),
  ("EQT","NYSE","EQT Corporation","aksje",
   "r 0,29  rm 0,31  b 0,36  f 0,39. Appalachia. Integrert transport demper ratefolsomheten.")],
"ttf": [
  ("EQNR.OL","Oslo","Equinor","aksje",
   "r 0,40  rm 0,33  b 0,28  f 0,13. Eneste positive over 0,30. Merk at utslaget er lite: fangsten fra bunn er 13 prosent av gassens."),
  ("AI.PA","Paris","Air Liquide","aksje",
   "- r -0,21  rm -0,19  fT -0,25. Industrigass. Naturgass er innsatsfaktor, saa papiret stiger naar gassen faller."),
  ("HEI.DE","Xetra","Heidelberg Materials","aksje",
   "- r -0,20  rm -0,21  fT -0,30. Sement er energitungt. Samme mekanisme, samme retning.")],
"gold": [
  ("GDX.L","London","VanEck Gold Miners UCITS","ETF",
   "r 0,56  rm 0,57  b 1,68  f 2,49. UCITS-utgaven av GDX, kjopbar paa IKZ. Fangsten fra bunn er 2,5 ganger gullets egen."),
  ("GJGB.L","London","VanEck Junior Gold Miners UCITS","ETF",
   "r 0,58  rm 0,59  b 1,89  f 1,13. Hoyeste korrelasjon og hoyeste utslag. Bare 110 maaneder historikk."),
  ("SPGP.L","London","iShares Gold Producers UCITS","ETF",
   "r 0,57  rm 0,59  b 1,86  f 2,56. Sterkeste fangst fra bunn i hele sonden. Bredere enn GDX.")],
"kobber": [
  ("CS.TO","Toronto","Capstone Copper","aksje",
   "r 0,56  rm 0,42  b 1,87  f 3,50. Rent kobber. Oppbeta 0,20 mot nedbeta 1,51, altsaa svaert asymmetrisk."),
  ("ATYM.L","London","Atalaya Mining","aksje",
   "r 0,52  rm 0,42  b 1,55  f 1,47. Symmetrisk (opp 1,22, ned 1,60) og dermed mer forutsigbar enn Capstone."),
  ("EXV6.DE","Xetra","iShares STOXX Europe 600 Basic Resources UCITS","ETF",
   "r 0,50  rm 0,43  b 1,17  f 1,22. Fra 2007, lengst historikk av fondene. Bredt gruvefond, ikke rent kobber.")],
"nikkel": [
  ("ERA.PA","Paris","Eramet","aksje",
   "r 0,34  rm 0,37  b 0,89  f 1,32. Beste nikkeluttrykk. Korrelasjonen stiger etter markedsjustering, altsaa reell nikkelkobling."),
  ("GLEN.L","London","Glencore","aksje",
   "r 0,30  rm 0,32  b 1,21. Nikkel er en liten del av porteforljen. Oppbeta 0,18 mot nedbeta 0,78."),
  ("EXV6.DE","Xetra","iShares STOXX Europe 600 Basic Resources UCITS","ETF",
   "r 0,30  rm 0,32  b 0,82  f 1,17. Bredt, men eneste fondsalternativ over stripa.")],
"aluminium": [
  ("NHY.OL","Oslo","Norsk Hydro","aksje",
   "r 0,52  rm 0,49  b 1,63  f 2,02. Sterkeste par utenfor olje og gull. Doblet aluminiumets egen oppgang fra bunn."),
  ("AA","NYSE","Alcoa","aksje",
   "r 0,48  rm 0,42  b 1,07  f 1,52. Renere aluminium enn Hydro, som har stor nedstromsvirksomhet."),
  ("CENX","Nasdaq","Century Aluminum","aksje",
   "r 0,44  rm 0,41  b 2,99  f 3,49. Hoyeste utslag i hele sonden. Smelteverk uten egen kraft, altsaa hoy operasjonell gearing.")],
"sink": [
  ("GLEN.L","London","Glencore","aksje",
   "r 0,42  rm 0,38  b 1,62  f 1,68. Storste sinkprodusent blant de handlbare."),
  ("BOL.ST","Stockholm","Boliden","aksje",
   "r 0,39  rm 0,36  b 1,49  f 1,94. Nordisk, symmetrisk (opp 1,20, ned 1,07)."),
  ("HBM.TO","Toronto","Hudbay Minerals","aksje",
   "r 0,39  rm 0,33  b 1,65  f 2,36. Sink ved siden av kobber, hoyere utslag enn Boliden.")],
"bly": [
  ("EXV6.DE","Xetra","iShares STOXX Europe 600 Basic Resources UCITS","ETF",
   "r 0,41  rm 0,30  b 1,19  f 0,92. Beste blyuttrykk er et bredt fond. Det sier noe om hvor tynt segmentet er."),
  ("BOL.ST","Stockholm","Boliden","aksje",
   "r 0,38  rm 0,27  b 1,16  f 1,73. Bly som biprodukt av sink."),
  ("NEXA","NYSE","Nexa Resources","aksje",
   "r 0,35  rm 0,26  b 2,06  f 2,80. Hoyeste utslag, men bare 106 maaneder og tynn likviditet.")],
"tinn": [
  ("GLEN.L","London","Glencore","aksje",
   "r 0,44  rm 0,30  b 0,98  f 1,31. Eneste handlbare papir som holder maal. Alphamin er TSX Venture og gaar ikke paa Nordnet. "
   "Merk at fangsten fra topper er -0,55, altsaa at papiret fulgte tinn ned.")],
# Jernmalm 26.09.2026: Cleveland-Cliffs er byttet ut med Vale (Frodes
# beslutning). Cleveland-Cliffs kjoepte AK Steel og ArcelorMittal USA i 2020 og
# er siden et staalverk som kjoeper malm, ikke selger den. Sonden hadde den
# allerede som forbruker (vent f), og porten C var stengt (0,3 kvartaler).
# Korrelasjonen i vinduet fra 2016 kom trolig fra aarene foer oppkjoepet. Vale
# er maalt i samme sonde (22.09.2026) og bestaar kravene. Rio Tinto (r 0,39,
# rm 0,29) bestaar ikke kravet etter verdensindeksen.
"jernmalm": [
  ("LIF.TO","Toronto","Labrador Iron Ore Royalty","aksje",
   "r 0,51  rm 0,42  b 0,92  f 0,76. Royalty, ikke drift. Derfor renest mot prisen og uten kostnadsinflasjon."),
  ("VALE","NYSE","Vale","aksje",
   "r 0,42  rm 0,34  b 0,95  f 0,70. Verdens nest stoerste malmprodusent, jernmalm er det meste av driften. Fulgte ogsaa prisen ned fra toppene (0,57). Nikkel og kobber i tillegg."),
  ("CIA.TO","Toronto","Champion Iron","aksje",
   "r 0,41  rm 0,34  b 1,35  f 1,70. Rent hoygradig konsentrat. Sterkeste fangst fra bunn i segmentet.")],
"kull": [
  ("BTU","NYSE","Peabody Energy","aksje",
   "r 0,28  rm 0,30  b 1,10. Svakt segment, ingen naadde 0,30 paa maanedstallet. Oppbeta 1,19 mot nedbeta 0,02."),
  ("GLEN.L","London","Glencore","aksje",
   "r 0,26  rm 0,29  b 0,58  f 1,06. Storste borsnoterte termiske kullprodusent, men kull er en del av et stort hus."),
  ("ARLP","Nasdaq","Alliance Resource Partners","aksje",
   "r 0,24  rm 0,23  b 0,58  f 0,87. Amerikansk innenlandskull paa lange kontrakter, derfor treg mot spotprisen.")],
"kakao": [
  ("HSY","NYSE","Hershey","aksje",
   "- r -0,23  rm -0,23  fT -0,83. Omvendt eksponering. Ni daterte kakaotopper siden 1984: 8 av 8 positive for Hershey."),
  ("BARN.SW","Zurich","Barry Callebaut","aksje",
   "- r -0,19  rm -0,23  fT -0,57. Reneste kakaoforedler paa bors. 5 av 5 topper positive, sist +46 prosent etter toppen i januar 2025."),
  ("NESN.SW","Zurich","Nestlé","aksje",
   "- r -0,18  rm -0,24  fT -0,33. Sterkest av de tre etter markedsjustering, men kakao er en liten del av huset.")],
"palmeolje": [
  ("MPE.L","London","M.P. Evans Group","aksje",
   "r 0,35  rm 0,32  b 0,63  f 1,07. Ren indonesisk plantasjedrift. Symmetrisk opp og ned."),
  ("RE.L","London","REA Holdings","aksje",
   "r 0,31  rm 0,28  b 0,95  f 0,53. Hoyere utslag, men liten og gjeldstynget. Sjekk overlevelsesporten for dette papiret."),
  ("ISAG.L","London","iShares Agribusiness UCITS","ETF",
   "r 0,31  rm 0,23  b 0,26  f 0,01. Fondsalternativ, men fanget ingenting fra daterte bunner. Bredt landbruk, ikke palme.")],

# Uran, lagt inn 2026-09-24. Maalt mot Camecos maanedsslutt spot fra 1988
# (sonde_kjor_uran, IKZ_KUN=uran), ikke mot IMF-serien, som ligger 22 til 27 %
# for lavt fra 2022. Maalt mot IMF-serien laa Cameco paa 0,29. Mot riktig
# serie ligger den paa 0,48, og uran er blant de sterkeste segmentene paa
# bordet. De to UCITS-fondene (URNU.L, U3O8.L) har under 72 maaneder
# historikk og er ikke med. Paladin (PDN.AX) er 0,36 men handles i Sydney.
"uran": [
  ("CCJ","NYSE","Cameco","aksje",
   "r 0,48  rm 0,45  b 0,77  f 0,19. Stoerst noterte produsent og lengst historikk (fra 1996). Fanget lite av oppgangen fra bunn, fordi mye av salget gaar paa langsiktige kontrakter."),
  ("UUUU","NYSE","Energy Fuels","aksje",
   "r 0,44  rm 0,40  b 1,58  f 0,96. Hoyest utslag og nesten hele oppgangen fra bunn. Merk at selskapet ogsaa driver med sjeldne jordarter og vanadium."),
  ("U-UN.TO","Toronto","Sprott Physical Uranium Trust","fond",
   "r 0,55  rm 0,55  b 0,85  f 0,31. Sterkeste par: fysisk uran i et lukket fond. Nordnet Norge foerer den som aksje paa Toronto med kjoep og salg aapent (sjekket 24.09.2026), saa den er trolig kjoepbar paa IKZ. Endelig svar gir foerst en ordre. Staar som fond her fordi den ikke har drift, og da gir porten C ingen mening.")],
"ship_vlcc": [
  ("FRO.OL","Oslo","Frontline","aksje","Storste norske VLCC-flate. Hoyeste beta mot raten."),
  ("OET.OL","Oslo","Okeanis Eco Tankers","aksje","Ung flate, VLCC og Suezmax. Lav kontantkostnad."),
  ("DHT","NYSE","DHT Holdings","aksje","Ren VLCC, konservativ balanse. Lavest konkursrisiko av de tre.")],
"ship_suezmax": [
  ("FRO.OL","Oslo","Frontline","aksje","Betydelig Suezmax ved siden av VLCC."),
  ("OET.OL","Oslo","Okeanis Eco Tankers","aksje","Balansert mellom de to segmentene."),
  ("NAT","NYSE","Nordic American Tankers","aksje","Rent Suezmax. Hoy utvanningshistorikk, sjekk aksjetallet.")],
"ship_aframax": [
  ("HAFNI.OL","Oslo","Hafnia","aksje","LR2 og MR. Storste produkttankrederi paa Oslo Bors."),
  ("TRMD-A.CO","København","TORM","aksje","Rent produkttank, nordisk."),
  ("TNK","NYSE","Teekay Tankers","aksje","Aframax- og Suezmax-tung raaolje.")],
"ship_kamsarmax": [
  ("SBLK","Nasdaq","Star Bulk Carriers","aksje","Bredest torrlastflate, tung paa Kamsarmax og Supramax."),
  ("GNK","NYSE","Genco Shipping","aksje","Lav gjeld, hoy utbytteandel i gode rater."),
  ("PANL","Nasdaq","Pangaea Logistics","aksje","Mindre, isklasse og egen logistikk. Mindre ren ratebeta.")],
"ship_ultramax": [
  ("SBLK","Nasdaq","Star Bulk Carriers","aksje","Storst eksponering mot Ultramax og Supramax."),
  ("GNK","NYSE","Genco Shipping","aksje","Betydelig Ultramax-andel."),
  ("PANL","Nasdaq","Pangaea Logistics","aksje","Supramax og Ultramax med logistikkpaaslag.")],
"ship_capesize": [
  ("HSHP.OL","Oslo","Himalaya Shipping","aksje","Rene Newcastlemax, alle paa indeksrelatert certeparti. Hoyeste beta."),
  # 2020 Bulkers (2020.OL) tatt ut 29.09.2026 (Frodes beslutning). Kursen hos
  # Yahoo falt 97 % i april 2026 uten at adjclose fanget det, trolig en stor
  # utdeling. Det ga falsk kapitulasjon (D 95) for papiret og for capesize.
  # Se sonder/sonde_kjor_utbytte.txt. Kan tas inn igjen naar dataene er rettet.
  ("SBLK","Nasdaq","Star Bulk Carriers","aksje","Capesize som del av en bredere flate. Lavere beta, lavere risiko."),
  ("CMBT","NYSE","CMB.TECH","aksje",
   "Ny sammensetning, ikke maalt. Stoerste noterte capesize-eier etter Golden Ocean (38 Newcastlemax og 37 capesize i januar 2026), "
   "men ogsaa tankskip, kjemikalier, container og offshore. Kurshistorikken er Euronav, et tankrederi, saa korrelasjon, "
   "kapitulasjon D og overlevelse C kan ikke maales ennaa og regnes ikke. Tatt inn 29.09.2026 etter Frodes beslutning.")],
"ship_handysize": [
  ("TMIP.L","London","Taylor Maritime","aksje","Handysize og Supramax, naermeste rene uttrykk."),
  ("GNK","NYSE","Genco Shipping","aksje","Handysize-andel ved siden av storre skip."),
  ("PANL","Nasdaq","Pangaea Logistics","aksje","Mindre skip i nisjefart.")],
# Laks kom inn 25.09.2026 som observasjonspanel uten flagg. Papirene er de fire
# som besto K3 i laksesonden: korrelasjon i maanedsendringer mot sesongjustert
# realpris i dollar fra 2016, raa og etter verdensindeksen, begge over 0,30.
# Grieg (0,28), Masoval (for kort historikk) og Austevoll (blandet) besto ikke.
"laks": [
  ("MOWI.OL","Oslo","Mowi","aksje",
   "r 0,36  rm 0,37. Storst i verden, oppdrett i seks land. Kroner mot kroner 0,33."),
  ("SALM.OL","Oslo","SalMar","aksje",
   "r 0,35  rm 0,34. Rent norsk, pluss havbruk til havs. Kroner mot kroner 0,30."),
  ("LSG.OL","Oslo","Lerøy Seafood","aksje",
   "r 0,32  rm 0,31. Oppdrett, villfisk og videreforedling. Svakeste av de fire: uten september og oktober 2022 faller den til 0,29."),
  ("BAKKA.OL","Oslo","Bakkafrost","aksje",
   "r 0,39  rm 0,38. Færøyene og Skottland. Sterkeste paret, også kroner mot kroner (0,36).")],
# Oljeservice kom inn 29.09.2026 som observasjonspanel uten flagg (Frodes
# beslutning etter sonde_kjor_oljeservice). Papirene er valgt paa lang
# kurshistorikk og lav gjeld, ikke paa korrelasjon mot prisserien, som ikke er
# maalt. Riggselskapene (Transocean, Valaris, Noble, Seadrill, Borr) er holdt
# utenfor: de er nye noteringer etter konkurs eller har falt 99 %, saa C og D
# kan ikke maales paa dem. OIH og XES er amerikanske fond, som norske
# privatpersoner normalt ikke kan kjoepe (PRIIPs); de staar for maaling.
"oljeservice": [
  ("OIH","NYSE","VanEck Oil Services ETF","ETF",
   "Bredt oljeservicefond, 25 store selskaper. Kurser fra 2001."),
  ("XES","NYSE","SPDR S&P Oil & Gas Equipment & Services","ETF",
   "Tilnærmet likevektet, mer mindre selskaper og mer landbasert boring enn OIH. Kurser fra 2006."),
  ("SLB","NYSE","SLB (Schlumberger)","aksje",
   "Størst i verden. Aldri negativ driftskontantstrøm hos SEC siden 2007 (verste år 2020)."),
  ("HAL","NYSE","Halliburton","aksje",
   "Mest eksponert mot amerikansk skifer. Negativ drift i 2016."),
  ("BKR","Nasdaq","Baker Hughes","aksje",
   "Utstyr og gassteknologi, bredere enn ren oljeservice. Negativ drift i 2017."),
  ("SUBC.OL","Oslo","Subsea 7","aksje",
   "Offshore installasjon og subsea. Ikke hos SEC, så C må leses manuelt."),
  ("TGS.OL","Oslo","TGS","aksje",
   "Seismikk, etter sammenslåingen med PGS (2024). Ikke hos SEC, så C må leses manuelt.")],
}


# Papirer paa tavlen der kurshistorikken tilhoerer et annet selskap enn det
# som handles i dag. De vises og logges, men holdes utenfor kapitulasjon D
# (kapitulasjon_d.py) og overlevelsesporten C (overlevelse_c.py), fordi
# begge maales mot papirets egen historikk. Lagt til 29.09.2026.
UTEN_HISTORIKK = {
    "CMBT": "Kurshistorikken er Euronav (tankskip) fram til fusjonene med CMB.TECH (2024) og Golden Ocean (2025).",
}
