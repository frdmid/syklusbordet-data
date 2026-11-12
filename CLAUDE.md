# Syklusbordet-data

- `notater/LOGG.md` er felles logg for Cowork-økten og Claude Code-økten.
  Les blokken «Status nå» øverst og innslagene fra inneværende måned før du
  begynner. Eldre innslag ligger i `notater/logg/<år>-<mnd>.md`, en fil per
  måned. «Status nå» oppdateres i samme commit som endringen, og ved
  månedsskifte flyttes forrige måned ut.
- Kilden til dashbordet er `dashbord/index.html` i repoet, ikke den
  publiserte artifacten. Kjør `git pull` før du endrer eller publiserer, og
  `py -X utf8 dashbord/kontroller.py` før hver publisering. Publiserer du
  fra den gamle artifacten, overskrives arbeidet i mappen.
- Før hver vesentlige endring der, nyeste øverst, i samme commit som endringen:
  dato og klokkeslett (norsk tid), hvilken økt, hva som ble gjort, hvilke filer,
  og hva den andre økten må vite. Et eget notat i `notater/` skal også ha en
  linje i loggen. Automatiske commits fra GitHub Actions føres ikke.
- Skriv på norsk. Ingen tankestrek i tekst.
- Les også `notater/OVERLEVERING.md`.
