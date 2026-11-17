"""Eurostat (JSON-stat API, geen key nodig).

- lfsa_egai2d: werkenden naar beroep (ISCO-08, 2-cijferig), per land, jaarlijks.
  Gebruikt om Nederland met de EU te vergelijken voor de beroepsgroepen waar
  de AI-gevoelige beroepen grotendeels onder vallen.
- isoc_sks_itspt: ICT-specialisten als aandeel van alle werkenden.

Eurostat publiceert de jaarcijfers één keer per jaar (voorjaar) en reviseert
tussendoor. Daarom wordt maximaal één keer per week opnieuw opgehaald.
"""
from __future__ import annotations

from datetime import date

from .. import config, store
from . import Http, log

API = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/{ds}"
AGE_PREF = ["Y15-74", "Y_GE15", "Y15-64", "Y20-64"]
ISCO_FIELDS = ["land", "isco", "jaar", "waarde"]
ICT_FIELDS = ["land", "eenheid", "jaar", "waarde"]


def decode_jsonstat(d: dict) -> list[dict]:
    """JSON-stat 2.0 -> lijst van {dim: code, ..., 'value': x}."""
    ids, sizes = d.get("id") or [], d.get("size") or []
    if not ids:
        return []
    cats = []
    for dim in ids:
        idx = d["dimension"][dim]["category"]["index"]
        if isinstance(idx, list):
            idx = {c: i for i, c in enumerate(idx)}
        cats.append({v: k for k, v in idx.items()})
    strides = [1] * len(ids)
    for i in range(len(ids) - 2, -1, -1):
        strides[i] = strides[i + 1] * sizes[i + 1]
    values = d.get("value") or {}
    items = values.items() if isinstance(values, dict) else enumerate(values)
    out = []
    for flat, val in items:
        if val is None:
            continue
        flat = int(flat)
        row = {}
        for i, dim in enumerate(ids):
            pos = (flat // strides[i]) % sizes[i]
            row[dim] = cats[i][pos]
        row["value"] = val
        out.append(row)
    return out


def _fetch(http, ds: str, params: list[tuple[str, str]]) -> dict | None:
    return http.get(API.format(ds=ds), params + [("format", "JSON"), ("lang", "en")])


def collect(force: bool = False) -> int:
    versions = store.read_json("meta/versions.json")
    have = (store.DATA_DIR / "eurostat_isco.csv").exists()
    last = versions.get("eurostat:checked", "")
    if have and not force and last and (date.today() - date.fromisoformat(last)).days < 7:
        log.info("Eurostat: vorige controle %s, overgeslagen (wekelijks)", last)
        return 0

    http = Http(timeout=120)
    geo = [("geo", g) for g in config.EUROSTAT_GEO]
    n = 0

    isco = [("isco08", c) for c in list(config.EUROSTAT_ISCO) + ["TOTAL"]]
    d = _fetch(http, "lfsa_egai2d", geo + isco + [("sex", "T"), ("unit", "THS_PER")])
    if d:
        rows = decode_jsonstat(d)
        ages = {r.get("age") for r in rows}
        age = next((a for a in AGE_PREF if a in ages), None)
        out = [{"land": r["geo"], "isco": r["isco08"], "jaar": r["time"], "waarde": r["value"]}
               for r in rows if r.get("age") == age]
        if out:
            store.write_csv("eurostat_isco.csv", out, ISCO_FIELDS)
            versions["eurostat:lfsa_egai2d"] = d.get("updated", "")
            versions["eurostat:lfsa_egai2d_age"] = age
            n += len(out)
        log.info("Eurostat lfsa_egai2d: %d rijen (leeftijd %s)", len(out), age)
    else:
        log.warning("Eurostat lfsa_egai2d niet bereikbaar")

    d = _fetch(http, "isoc_sks_itspt", geo)
    if d:
        rows = decode_jsonstat(d)
        out = [{"land": r["geo"], "eenheid": r.get("unit", ""), "jaar": r["time"], "waarde": r["value"]}
               for r in rows]
        if out:
            store.write_csv("eurostat_ict.csv", out, ICT_FIELDS)
            versions["eurostat:isoc_sks_itspt"] = d.get("updated", "")
            n += len(out)
        log.info("Eurostat isoc_sks_itspt: %d rijen", len(out))
    else:
        log.warning("Eurostat isoc_sks_itspt niet bereikbaar")

    if n:
        versions["eurostat:checked"] = date.today().isoformat()
        store.write_json("meta/versions.json", versions)
    return n
