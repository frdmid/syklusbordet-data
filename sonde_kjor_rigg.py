# ---------------------------------------------------------------------------
# sonde_kjor_rigg: finnes riggtall med lang nok historikk til B for olje og gass
#
# B for Brent, WTI og Henry Hub mangler. Capex delt paa avskrivninger fra
# amerikanske boersselskaper beskriver skifer, ikke Brent. Forslaget
# (25.09.2026) er EN variabel per segment: riggtallet, maalt som endring over
# tolv maaneder mot egen historikk.
#   WTI         amerikanske oljerigger
#   Henry Hub   amerikanske gassrigger
#   Brent       internasjonalt riggtall (utenfor Nord-Amerika)
#
# Denne sonden maaler bare om dataene finnes og kan hentes fra Actions. Den
# regner ingen sammenheng med pris eller papirer. Den testen settes opp og
# godkjennes foer den kjoeres.
#
# Krav satt foer kjoering: en serie er kandidat hvis den er maanedlig, starter
# senest 1995 og siste verdi er hoeyst to maaneder gammel.
# ---------------------------------------------------------------------------

import io, re, time
import pandas as pd
import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
NAA = pd.Period(pd.Timestamp.now(), freq="M")
RES = []


def vurder(navn, s, kilde):
    s = s.dropna().sort_index()
    if s.empty:
        print(f"   {navn}: tom"); return
    alder = (NAA - s.index[-1]).n
    ok = s.index[0] <= pd.Period("1995-12", "M") and alder <= 2
    RES.append((navn, str(s.index[0]), str(s.index[-1]), len(s), alder, ok, kilde))
    print(f"   {navn}: {s.index[0]} til {s.index[-1]}, {len(s)} mnd, siste {s.iloc[-1]:.0f}, "
          f"{alder} mnd gammel -> {'KANDIDAT' if ok else 'nei'}")
    print(f"      siste seks: {', '.join(f'{p}:{v:.0f}' for p, v in s.tail(6).items())}")


print("1. EIA, riggtall fra Baker Hughes (maanedlig)")
EIA = {"US oljerigger": "E_ERTRRO_XR0_NUS_C", "US gassrigger": "E_ERTRRG_XR0_NUS_C",
       "US totalt": "E_ERTRR0_XR0_NUS_C"}
for navn, kode in EIA.items():
    url = f"https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx?n=PET&s={kode}&f=M"
    try:
        r = requests.get(url, headers=UA, timeout=60)
        print(f"   {navn} ({kode}): HTTP {r.status_code}, {len(r.content)} byte")
        tabs = pd.read_html(io.StringIO(r.text))
        t = max(tabs, key=lambda x: x.size)
        t.columns = [str(c).strip() for c in t.columns]
        aarkol = t.columns[0]
        mnd = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        v = {}
        for _, rad in t.iterrows():
            m = re.match(r"^\s*(\d{4})", str(rad[aarkol]))
            if not m:
                continue
            for i, mn in enumerate(mnd):
                if mn in t.columns:
                    x = pd.to_numeric(str(rad[mn]).replace(",", ""), errors="coerce")
                    if pd.notna(x):
                        v[pd.Period(f"{m.group(1)}-{i + 1:02d}", "M")] = float(x)
        vurder(navn, pd.Series(v), f"EIA {kode}")
    except Exception as e:
        print(f"   {navn}: {type(e).__name__}: {str(e)[:100]}")
    time.sleep(1)

print("\n2. Baker Hughes direkte (internasjonalt riggtall)")
for side in ("https://rigcount.bakerhughes.com/intl-rig-count",
             "https://rigcount.bakerhughes.com/rig-count-overview",
             "https://rigcount.bakerhughes.com/na-rig-count"):
    try:
        r = requests.get(side, headers=UA, timeout=60)
        print(f"   {side}: HTTP {r.status_code}")
        if r.status_code != 200:
            continue
        lenker = sorted(set(re.findall(r'href="([^"]+)"', r.text)))
        filer = [u for u in lenker if re.search(r"static-files|\.xlsx?|\.xlsb|\.csv", u, re.I)]
        for u in filer[:25]:
            print(f"      {u[:140]}")
        for u in filer:
            full = u if u.startswith("http") else "https://rigcount.bakerhughes.com" + u
            if not re.search(r"intl|international|worldwide", full + r.text[max(0, r.text.find(u) - 300):r.text.find(u)], re.I):
                continue
            try:
                b = requests.get(full, headers=UA, timeout=90)
                typ = b.headers.get("content-type", "")
                print(f"      henter {full[:100]}: HTTP {b.status_code}, {typ[:60]}, {len(b.content)} byte")
                if b.status_code == 200 and b.content[:2] == b"PK":
                    ark = pd.read_excel(io.BytesIO(b.content), sheet_name=None, header=None)
                    for n, df in list(ark.items())[:8]:
                        print(f"         ark '{n}': {df.shape}")
                        for i in range(min(6, len(df))):
                            print("            " + " | ".join(str(x)[:14] for x in df.iloc[i].tolist()[:12]))
                    break
            except Exception as e:
                print(f"      {type(e).__name__}: {str(e)[:80]}")
    except Exception as e:
        print(f"   {side}: {type(e).__name__}: {str(e)[:80]}")
    time.sleep(1)

print("\n3. EIA DUC-regnearket")
try:
    b = requests.get("https://www.eia.gov/petroleum/drilling/xls/duc-data.xlsx", headers=UA, timeout=90)
    print(f"   HTTP {b.status_code}, {len(b.content)} byte")
    ark = pd.read_excel(io.BytesIO(b.content), sheet_name=None, header=None)
    for n, df in ark.items():
        print(f"   ark '{n}': {df.shape}")
        for i in range(min(5, len(df))):
            print("      " + " | ".join(str(x)[:16] for x in df.iloc[i].tolist()[:10]))
        datoer = pd.to_datetime(df.iloc[:, 0], errors="coerce").dropna()
        if len(datoer):
            print(f"      datoer {datoer.min().date()} til {datoer.max().date()}")
except Exception as e:
    print(f"   {type(e).__name__}: {str(e)[:100]}")

print("\n4. Oppsummering")
for navn, fra, til, n, alder, ok, kilde in RES:
    print(f"   {navn:16s} {fra} til {til} ({n} mnd, {alder} mnd gammel)  {'KANDIDAT' if ok else 'nei'}  [{kilde}]")
if not any(r[0].startswith("Intl") for r in RES):
    print("   Internasjonalt riggtall er ikke lest som serie her. Se utskriften under punkt 2.")
