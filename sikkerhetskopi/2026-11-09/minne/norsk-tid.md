---
name: norsk-tid
description: "Oppgi alltid klokkeslett i norsk tid til Frode, aldri UTC"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 70736c51-c677-47ba-bebb-8ad506eb9a20
  modified: 2026-10-21T09:35:12.046Z
---

Alle klokkeslett i svar til Frode skal være norsk tid (Europe/Oslo). Ikke skriv UTC, heller ikke i parentes; regn om (cron 06:00 UTC = 08:00 norsk sommertid, 07:00 vintertid; rutinen 09:00 UTC = 11:00/10:00).

**Why:** Frode har sagt det flere ganger (gjentatt 21.10.2026 etter at jeg skrev «06:43 UTC»).

**How to apply:** Gjelder svar, logg og notater. Systemklokka på maskinen er norsk tid (PowerShell Get-Date); Git Bash `date` med TZ gir feil. Tidsstempler fra GitHub og rutine-API er UTC og må regnes om før de nevnes. Se også [[varsling-i-prosjektchat]].
