# ticker, borsnavn, selskap/fond, type, kommentar. retning "-" = omvendt eksponering.
INSTR = {
"brent": [
  ("AKRBP.OL","Oslo","Aker BP","aksje","Ren norsk produsent, hoy beta mot Brent. Ingen raffinering som demper."),
  ("VAR.OL","Oslo","Vår Energi","aksje","Samme profil, noe mer gassvektet. Hoy utbytteandel."),
  ("BRNT.L","London","WisdomTree Brent Crude Oil","ETC","Ren pris, ingen selskapsrisiko. Rullekostnad i contango.")],
"wti": [
  ("FANG","Nasdaq","Diamondback Energy","aksje","Permian, ren WTI-eksponering."),
  ("DVN","NYSE","Devon Energy","aksje","Samme basseng, hoyere utbytteandel."),
  ("CRUD.L","London","WisdomTree WTI Crude Oil","ETC","Ren pris. Par med BRNT for aa spille spreaden.")],
"henryhub": [
  ("EQT","NYSE","EQT Corporation","aksje","Storste amerikanske gassprodusent, Appalachia."),
  ("AR","NYSE","Antero Resources","aksje","Gass og NGL, hoyere beta enn EQT."),
  ("NGAS.L","London","WisdomTree Natural Gas","ETC","Ren pris. Sterk rullekostnad, egner seg daarlig for lang holdetid.")],
"ttf": [
  ("EQNR.OL","Oslo","Equinor","aksje","Europas storste gassleverandor. Det beste TTF-uttrykket paa noen bors."),
  ("SHEL.L","London","Shell","aksje","Storst paa LNG globalt, bredere enn Equinor."),
  ("CNA.L","London","Centrica","aksje","Britisk gass, lagring og handel. Tettere paa europeisk pris enn produsentene.")],
"gold": [
  ("SGLN.L","London","iShares Physical Gold ETC","ETC","Fysisk gull, lav kostnad. Ingen selskapsrisiko."),
  ("AEM","NYSE","Agnico Eagle Mines","aksje","Operasjonelt sterkest av de store. Gearing mot gullprisen."),
  ("NEM","NYSE","Newmont","aksje","Storst, mest likvid. Mer eksponert mot kostnadsinflasjon.")],
"kobber": [
  ("ANTO.L","London","Antofagasta","aksje","Naermeste rene kobberspill paa borsene du handler."),
  ("FCX","NYSE","Freeport-McMoRan","aksje","Storst utenfor Chile. Grasberg gir gullinntekt ved siden av."),
  ("COPA.L","London","WisdomTree Copper","ETC","Ren pris, ingen utvanningsrisiko.")],
"nikkel": [
  ("GLEN.L","London","Glencore","aksje","Nikkel pluss kobber, sink og kull. Bredt, ikke rent."),
  ("VALE","NYSE","Vale","aksje","Nest storst paa nikkel globalt, men domineres av jernmalm."),
  ("NICK.L","London","WisdomTree Nickel","ETC","Eneste rene uttrykk. Tynn likviditet.")],
"aluminium": [
  ("NHY.OL","Oslo","Norsk Hydro","aksje","Integrert fra bauksitt til valseverk. Beste norske uttrykk."),
  ("AA","NYSE","Alcoa","aksje","Renere oppstromsspill enn Hydro, mer volatil."),
  ("ALUM.L","London","WisdomTree Aluminium","ETC","Ren LME-pris uten kraftkostnadsrisiko.")],
"sink": [
  ("BOL.ST","Stockholm","Boliden","aksje","Nordisk, sink og kobber fra egne gruver og smelteverk."),
  ("NEXA","NYSE","Nexa Resources","aksje","Renere sinkspill, Latin-Amerika."),
  ("ZINC.L","London","WisdomTree Zinc","ETC","Ren pris.")],
"bly": [
  ("BOL.ST","Stockholm","Boliden","aksje","Bly kommer som biprodukt i sinkproduksjonen."),
  ("TECK-B.TO","Toronto","Teck Resources","aksje","Red Dog er verdens storste sink- og blygruve."),
  ("LEAD.L","London","WisdomTree Lead","ETC","Ren pris. Svaert tynn.")],
"tinn": [
  ("AFM.V","TSX Venture","Alphamin Resources","aksje","Bisie i Kongo. Naermest et rent tinnspill som finnes notert."),
  ("GLEN.L","London","Glencore","aksje","Handel og smelting, ikke ren eksponering."),
  ("TINM.L","London","WisdomTree Tin","ETC","Ren pris, men svaert lav omsetning. Sjekk spread for du handler.")],
"jernmalm": [
  ("RIO.L","London","Rio Tinto","aksje","Pilbara dominerer resultatet. Tettest paa jernmalmprisen av de store."),
  ("VALE","NYSE","Vale","aksje","Brasiliansk malm, hoyere kvalitet og hoyere politisk risiko."),
  ("FXPO.L","London","Ferrexpo","aksje","Pelletsprodusent. Hoy gearing, men ukrainsk driftsrisiko.")],
"kull": [
  ("TGA.L","London","Thungela Resources","aksje","Rent termisk kull, Sor-Afrika. Hoy utbytteandel i gode aar."),
  ("BTU","NYSE","Peabody Energy","aksje","Termisk og metallurgisk, amerikansk."),
  ("HCC","NYSE","Warrior Met Coal","aksje","Kun kokskull. Folger staalsyklusen, ikke kraftmarkedet.")],
"urea": [
  ("YAR.OL","Oslo","Yara International","aksje","Margin er i praksis ammoniakkpris minus TTF. Beste norske uttrykk."),
  ("CF","NYSE","CF Industries","aksje","Renere nitrogenspill, amerikansk gass som innsats."),
  ("NTR","NYSE","Nutrien","aksje","Bredest: nitrogen, kalium og fosfat i ett.")],
"kalium": [
  ("NTR","NYSE","Nutrien","aksje","Storst paa kalium globalt."),
  ("MOS","NYSE","Mosaic","aksje","Kalium og fosfat, hoyere gearing enn Nutrien."),
  ("YAR.OL","Oslo","Yara International","aksje","Bare delvis kalium. Med som norsk alternativ, ikke som naermeste spor.")],
"fiskemel": [
  ("AUSS.OL","Oslo","Austevoll Seafood","aksje","Pelagisk fangst og fiskemelproduksjon. Eneste norske LANGE eksponering."),
  ("MOWI.OL","Oslo","Mowi","aksje","- Fiskemel er en kostnad. Hoy melpris presser margin."),
  ("SALM.OL","Oslo","SalMar","aksje","- Samme omvendte forhold, hoyere kostnadsgearing.")],
"kakao": [
  ("COCO.L","London","WisdomTree Cocoa","ETC","Eneste rene uttrykk. Produsentene i Vest-Afrika er ikke noterte."),
  ("BARN.SW","Zürich","Barry Callebaut","aksje","- Verdens storste foredler. Hoy kakaopris presser marginen."),
  ("HSY","NYSE","Hershey","aksje","- Samme omvendte forhold, mer merkevare og mindre raavare.")],
"kaffe_arabica": [
  ("COFF.L","London","WisdomTree Coffee","ETC","Eneste rene uttrykk paa borsene du handler."),
  ("SBUX","Nasdaq","Starbucks","aksje","- Kaffe er innsatsfaktor. Hoy pris presser margin."),
  ("JDEP.AS","Amsterdam","JDE Peet's","aksje","- Rendyrket kaffeforedler. Utenfor listen din, tatt med som referanse.")],
"kaffe_robusta": [
  ("COFF.L","London","WisdomTree Coffee","ETC","Indeksen er arabica-tung, saa robusta spores bare delvis."),
  ("SBUX","Nasdaq","Starbucks","aksje","- Innsatsfaktor, omvendt eksponering."),
  ("NESN.SW","Zürich","Nestlé","aksje","- Storst paa loselig kaffe, som er robusta-basert. Utenfor listen din.")],
"palmeolje": [
  ("MPE.L","London","M.P. Evans Group","aksje","Indonesiske plantasjer, rent palmeoljespill paa London."),
  ("RE.L","London","REA Holdings","aksje","Mindre og mer gearet, hoyere driftsrisiko."),
  ("ADM","NYSE","Archer-Daniels-Midland","aksje","Handelshus. Margin folger volatilitet, ikke flatpris.")],
"gummi_rss3": [
  ("MICP.PA","Paris","Michelin","aksje","- Gummi er innsatsfaktor. Utenfor listen din."),
  ("GT","Nasdaq","Goodyear","aksje","- Samme omvendte forhold, hoyere gearing."),
  ("HAL.SI","Singapore","Halcyon Agri","aksje","Eneste rene produsent. Ikke tilgjengelig paa dine borser.")],
"gummi_tsr20": [
  ("GT","Nasdaq","Goodyear","aksje","- Innsatsfaktor, omvendt eksponering."),
  ("MICP.PA","Paris","Michelin","aksje","- Samme, utenfor listen din."),
  ("HAL.SI","Singapore","Halcyon Agri","aksje","Ren produsent, utilgjengelig.")],
"kokosolje": [
  ("ADM","NYSE","Archer-Daniels-Midland","aksje","Handel med vegetabilske oljer, svakt spor."),
  ("BG","NYSE","Bunge Global","aksje","Samme, storre paa knusing enn paa tropiske oljer."),
  ("MPE.L","London","M.P. Evans Group","aksje","Palmeolje korrelerer med kokosolje, ikke direkte eksponering.")],
"te": [
  ("UNA.AS","Amsterdam","Unilever","aksje","- Var storst paa te, men skilte ut virksomheten. Svakt spor."),
  ("TATACONSUM.NS","Mumbai","Tata Consumer","aksje","Rendyrket, men utilgjengelig paa dine borser."),
  ("MPE.L","London","M.P. Evans Group","aksje","Har hatt teplantasjer. Marginalt spor i dag.")],
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
  ("2020.OL","Oslo","2020 Bulkers","aksje","Samme modell, eldre flate. Maanedlig utbytte."),
  ("SBLK","Nasdaq","Star Bulk Carriers","aksje","Capesize som del av en bredere flate. Lavere beta, lavere risiko.")],
"ship_handysize": [
  ("TMIP.L","London","Taylor Maritime","aksje","Handysize og Supramax, naermeste rene uttrykk."),
  ("GNK","NYSE","Genco Shipping","aksje","Handysize-andel ved siden av storre skip."),
  ("PANL","Nasdaq","Pangaea Logistics","aksje","Mindre skip i nisjefart.")],
}
