# ---------------------------------------------------------------------------
# sonde_kjor_uran: instrumenter for det nye uransegmentet, og en levende kilde
#
# Del 1. Hvilke papirer i IKZ-universet folger uran.
#   Tolv kandidater ble hentet i IKZ-sonden 22. september, men aldri maalt,
#   fordi det ikke fantes noen uranpris aa maale dem mot (FRED svarte ikke,
#   og kopien i repoet kom foerst 24. september). Naa finnes den. Sonden
#   kjorer sonde_ikz.py med IKZ_KUN=uran: samme maaling, samme krav og samme
#   faste vindu fra 2016 som for de andre segmentene, men bare mot uran og mot
#   hele kandidatuniverset. Resultatet skrives til sonder/ikz_uran.json, og
#   den fulle kjoringen i sonde_ikz.json roeres ikke.
#
#   Uten et maalt papir faar ikke segmentet noen instrumentliste, og da
#   hopper den planlagte kopieringen til dashbordet over det. Det er en sperre
#   med hensikt, saa denne sonden er det som slipper uran inn paa bordet.
#
# Del 2. Hvor kan uranprisen hentes fra, uke for uke.
#   uran_reserve.csv er en fast kopi som slutter i juli 2026. FRED svarer ikke
#   fra Actions. Her proves fem andre veier, og hver sammenlignes med kopien i
#   de maanedene begge har, slik at vi vet om det er samme serie og ikke bare
#   et tall som ligner.
# ---------------------------------------------------------------------------

import io, json, os, re, subprocess, sys, time
import pandas as pd
import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}

# ================================================================ del 1
print("DEL 1. IKZ-maaling mot uran\n", flush=True)
t0 = time.time()
p = subprocess.run([sys.executable, "sonde_ikz.py"], env=dict(os.environ, IKZ_KUN="uran"),
                   capture_output=True, text=True, timeout=3000)
print(p.stdout[-60000:])
if p.stderr.strip():
    print("[stderr]\n" + p.stderr[-4000:])
print(f"\n(del 1 brukte {time.time() - t0:.0f} s, kode {p.returncode})\n", flush=True)


# ================================================================ del 2
print("\nDEL 2. Levende kilder for uranprisen\n")
kopi = pd.read_csv("uran_reserve.csv")
kopi.columns = ["dato", "v"]
kopi["t"] = pd.PeriodIndex(kopi["dato"].astype(str), freq="M")
KOPI = kopi.set_index("t")["v"]
print(f"   kopien: {KOPI.index[0]} til {KOPI.index[-1]}, siste {KOPI.iloc[-1]:.2f}\n")


def sammenlign(navn, s):
    """s: maanedsserie med PeriodIndex. Skriver overlapp, avvik og siste punkt."""
    s = s.dropna()
    felles = s.index.intersection(KOPI.index)
    if len(felles) == 0:
        print(f"   {navn:34} {len(s)} mnd {s.index[0]}..{s.index[-1]}, siste {s.iloc[-1]:.2f}. "
              "Ingen overlapp med kopien.")
        return
    a, b = s.reindex(felles), KOPI.reindex(felles)
    avvik = ((a / b - 1).abs() * 100)
    print(f"   {navn:34} {len(s)} mnd {s.index[0]}..{s.index[-1]}, siste {s.iloc[-1]:.2f}  "
          f"overlapp {len(felles)} mnd, median avvik {avvik.median():.1f} %, "
          f"korr {a.corr(b):.4f}")


def prov(navn, fn):
    try:
        fn()
    except Exception as e:
        print(f"   {navn:34} {type(e).__name__}: {str(e)[:90]}")


# a) IMF sitt nye dataportal-API, SDMX 2.1. PCPS er Primary Commodity Prices.
def imf_ny():
    for url in ("https://api.imf.org/external/sdmx/2.1/data/IMF.RES,PCPS/W00.PURAN.USD.M",
                "https://api.imf.org/external/sdmx/2.1/data/PCPS/W00.PURAN.USD.M",
                "https://api.imf.org/external/sdmx/2.1/data/IMF.RES,PCPS,1.0/W00.PURAN.USD.M"):
        r = requests.get(url, headers={**UA, "Accept": "application/vnd.sdmx.data+csv;version=1.0.0"},
                         timeout=40)
        print(f"   IMF api.imf.org  {url[-40:]:40} HTTP {r.status_code} {len(r.content)//1024} kB")
        if r.status_code == 200 and r.text.strip():
            d = pd.read_csv(io.StringIO(r.text))
            print(f"      kolonner: {list(d.columns)[:12]}")
            tk = next((c for c in d.columns if c.upper() in ("TIME_PERIOD", "TIME")), None)
            vk = next((c for c in d.columns if c.upper() in ("OBS_VALUE", "VALUE")), None)
            if tk and vk:
                s = pd.Series(pd.to_numeric(d[vk], errors="coerce").values,
                              index=pd.PeriodIndex(d[tk].astype(str).str.replace("M", "-"), freq="M"))
                sammenlign("IMF api.imf.org", s.sort_index())
                return

# b) IMF sitt gamle JSON-API. Kan vaere nedlagt.
def imf_gammel():
    url = "http://dataservices.imf.org/REST/SDMX_JSON.svc/CompactData/PCPS/M.W00.PURAN.USD"
    r = requests.get(url, headers=UA, timeout=40)
    print(f"   IMF dataservices                   HTTP {r.status_code} {len(r.content)//1024} kB")
    if r.status_code == 200:
        obs = r.json()["CompactData"]["DataSet"]["Series"]["Obs"]
        s = pd.Series({pd.Period(o["@TIME_PERIOD"], freq="M"): float(o["@OBS_VALUE"]) for o in obs})
        sammenlign("IMF dataservices", s.sort_index())

# c) FRED, for aa se om den fortsatt ikke svarer herfra
def fred():
    r = requests.get("https://fred.stlouisfed.org/graph/fredgraph.csv?id=PURANUSDM",
                     headers=UA, timeout=25)
    print(f"   FRED                               HTTP {r.status_code}")
    d = pd.read_csv(io.StringIO(r.text)); d.columns = ["d", "v"]
    s = pd.Series(pd.to_numeric(d["v"], errors="coerce").values,
                  index=pd.PeriodIndex(pd.to_datetime(d["d"]), freq="M"))
    sammenlign("FRED PURANUSDM", s)

# d) Cameco publiserer maanedsslutt spot fra UxC og TradeTech
def cameco():
    url = "https://www.cameco.com/invest/markets/uranium-price"
    r = requests.get(url, headers=UA, timeout=40)
    print(f"   Cameco uranium-price               HTTP {r.status_code} {len(r.content)//1024} kB")
    if r.status_code == 200:
        tab = pd.read_html(io.StringIO(r.text))
        print(f"      {len(tab)} tabeller. Forste: {list(tab[0].columns)[:6] if tab else '-'}")
        for t in tab[:2]:
            print("      " + t.head(4).to_string().replace("\n", "\n      "))

# e) Yahoo: CME sin uranfutures (UxC), ulike symbolgjetninger
def yahoo():
    for sym in ("UX=F", "UXA=F", "UX1!", "URA=F"):
        r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}",
                         params={"range": "20y", "interval": "1mo"}, headers=UA, timeout=30)
        ok = r.status_code == 200 and (r.json().get("chart", {}).get("result") or [None])[0]
        if not ok:
            print(f"   Yahoo {sym:8}                     HTTP {r.status_code}, ingen serie")
            continue
        res = r.json()["chart"]["result"][0]
        ts, cl = res.get("timestamp") or [], res["indicators"]["quote"][0].get("close") or []
        s = pd.Series(cl, index=pd.PeriodIndex(pd.to_datetime(ts, unit="s"), freq="M")).dropna()
        s = s[~s.index.duplicated(keep="last")]
        sammenlign(f"Yahoo {sym} ({res['meta'].get('longName') or res['meta'].get('symbol')})", s)

for navn, fn in [("IMF ny", imf_ny), ("IMF gammel", imf_gammel), ("FRED", fred),
                 ("Cameco", cameco), ("Yahoo", yahoo)]:
    prov(navn, fn)
    time.sleep(1)

print("\nEn kilde kan brukes hvis den har overlapp med kopien, median avvik under")
print("et par prosent og korrelasjon over 0,99. Futures og maanedsslutt vil ligge")
print("litt fra IMF sitt maanedssnitt, men skal folge den tett.")
print("\nSend hele utskriften tilbake.")
