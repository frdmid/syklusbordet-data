# ---------------------------------------------------------------------------
# kurve_innhent: terminkurven tolv maaneder fram, hver uke
#
# Kurvesonden (25.09.2026) viste at Yahoo gir de enkelte maanedskontraktene
# for WTI, Brent, Henry Hub, gull og kobber, og kortere kurver for kakao.
# Historikken bakover, rekonstruert fra utloepte kontrakter, var gal foer 2023
# (WTI leste +4,8 % i april 2020, da kurven sto i ekstrem contango). Derfor
# bygges historikken her framover, en verdi per maaned (siste kjoering i
# maaneden vinner), i kurve_hist.json i repoet. Persentilen kommer naar det er
# 36 maaneder, etter signaler.kurvepersentil.
#
# Formen og beskrivelsen regnes av signaler.kurveform, som dashbordet er bygget
# for. Renten er 13 ukers statskasseveksel (^IRX), brukt til aa lese contango
# mot lagerkostnad.
#
# Feiler noe her, stopper ikke resten av innhentingen.
# ---------------------------------------------------------------------------

import datetime as dt
import json, time
import requests

from signaler import kurveform, kurvepersentil

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
KODE = "FGHJKMNQUVXZ"
ROT = {"wti": ("CL", "NYM", "NYMEX"), "brent": ("BZ", "NYM", "NYMEX"),
       "henryhub": ("NG", "NYM", "NYMEX"), "gold": ("GC", "CMX", "COMEX"),
       "kobber": ("HG", "CMX", "COMEX"), "kakao": ("CC", "NYB", "ICE US")}
MND_FRAM = 15


def siste(sym):
    """Siste dagskurs og dato, eller (None, None)."""
    try:
        r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range=10d&interval=1d",
                         headers=UA, timeout=25)
        if r.status_code != 200:
            return None, None
        res = r.json()["chart"]["result"][0]
        par = [(t, v) for t, v in zip(res.get("timestamp") or [], res["indicators"]["quote"][0]["close"])
               if v is not None]
        if not par:
            return None, None
        return float(par[-1][1]), dt.datetime.utcfromtimestamp(par[-1][0]).strftime("%Y-%m-%d")
    except Exception:
        return None, None


def hent_kurve(rot, bors, idag):
    """[(maaned 'YYYY-MM', maaneder fram fra fronten, pris)], fronten foerst."""
    ut, y, m = [], idag.year, idag.month
    datoer = []
    for _ in range(MND_FRAM):
        m += 1
        if m > 12:
            m, y = 1, y + 1
        p, d = siste(f"{rot}{KODE[m - 1]}{y % 100:02d}.{bors}")
        if p:
            ut.append((f"{y}-{m:02d}", p)); datoer.append(d)
        time.sleep(0.15)
    if not ut:
        return None, None
    f = ut[0][0]
    nr = lambda t: int(t[:4]) * 12 + int(t[5:7])
    return [(t, nr(t) - nr(f), p) for t, p in ut], max(datoer)


def oppdater(segmenter, les, skriv, note=print, idag=None):
    """Setter s["kurve"] paa segmentene der kurven finnes, og oppdaterer
    kurve_hist.json. les(sti) -> tekst eller None, skriv(sti, tekst)."""
    idag = idag or dt.date.today()
    mnd = idag.strftime("%Y-%m")
    rente, _ = siste("%5EIRX")
    hist = json.loads(les("kurve_hist.json") or "{}")
    n = 0
    for s in segmenter:
        if s["id"] not in ROT:
            continue
        rot, bors, navn = ROT[s["id"]]
        try:
            kv, dato = hent_kurve(rot, bors, idag)
            k = kurveform(kv, s["id"], rente) if kv else None
            if not k:
                note(f"kurve {s['id']}", False, "for kort kurve, ingen tolvmaanederspunkt")
                continue
            h = hist.setdefault(s["id"], {})
            h[mnd] = k["helning12"]
            serie = [h[t] for t in sorted(h)]
            p3, pa = kurvepersentil(serie, k["helning12"])
            k.update({"pctl_3aar": p3, "pctl_alle": pa, "fra": min(h)[:4], "mnd_historikk": len(h),
                      "kilde": f"Yahoo, {navn} enkeltkontrakter", "dato": dato})
            s["kurve"] = k
            n += 1
        except Exception as e:
            note(f"kurve {s['id']}", False, f"{type(e).__name__}: {str(e)[:60]}")
    skriv("kurve_hist.json", json.dumps(hist, ensure_ascii=False, indent=0))
    note("kurveform", n > 0, f"{n} segmenter, rente {rente}, historikk " +
         ", ".join(f"{k} {len(v)} mnd" for k, v in hist.items()))
    return n
