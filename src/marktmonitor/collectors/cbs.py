"""CBS StatLine (open data): openstaande vacatures en vacaturegraad per sector.

Tabel 80567ned 'Vacatures; vacaturegraad naar SBI 2008', per kwartaal.
We bewaren 'Totaal' en 'J Informatie en communicatie' (de ICT-sector).
Dimensie- en onderwerpnamen worden op titel gezocht, zodat kleine
wijzigingen in de tabel de collector niet breken.
"""
from __future__ import annotations

from .. import store
from . import Http, log

BASE = "https://opendata.cbs.nl/ODataApi/odata/80567ned"
FIELDS = ["period", "sector", "measure", "value"]


def collect() -> int:
    http = Http(timeout=60)
    props = (http.get(f"{BASE}/DataProperties") or {}).get("value") or []
    if not props:
        log.warning("CBS: tabel 80567ned niet bereikbaar")
        return 0

    dims = [p for p in props if p.get("Type") in ("Dimension", "GeoDimension")]
    topics = [p for p in props if p.get("Type") == "Topic"]
    sector_dim = next((d for d in dims if "sbi" in d["Key"].lower() or "bedrijf" in d["Key"].lower()), None)
    if not sector_dim:
        log.warning("CBS: sectordimensie niet gevonden")
        return 0

    entries = (http.get(f"{BASE}/{sector_dim['Key']}") or {}).get("value") or []
    def wanted(title: str) -> bool:
        t = title.lower().strip()
        return "informatie en communicatie" in t or t.startswith(("a-u", "totaal", "alle economische"))

    sectors = {e["Key"]: e["Title"] for e in entries if wanted(e["Title"])}
    measures = {t["Key"]: t["Title"] for t in topics
                if "vacature" in t["Title"].lower() and "seizoen" not in t["Title"].lower()}
    if not sectors or not measures:
        log.warning("CBS: geen passende sectoren/onderwerpen gevonden")
        return 0

    rows = []
    for key, title in sectors.items():
        d = http.get(f"{BASE}/TypedDataSet", {"$filter": f"{sector_dim['Key']} eq '{key}'"})
        for r in (d or {}).get("value") or []:
            period = (r.get("Perioden") or "").strip()
            if "KW" not in period:
                continue
            for mkey, mtitle in measures.items():
                val = r.get(mkey)
                if val is not None:
                    rows.append({"period": period, "sector": title.strip(),
                                 "measure": mtitle.strip(), "value": val})
    if rows:
        store.write_csv("cbs_vacatures.csv", rows, FIELDS)
    log.info("CBS: %d rijen", len(rows))
    return len(rows)
