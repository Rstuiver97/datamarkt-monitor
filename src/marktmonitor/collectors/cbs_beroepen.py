"""CBS StatLine: werkzame beroepsbevolking naar beroep (Enquête Beroepsbevolking).

Tabel 86320NED (BRC 2014 editie 2025, vanaf 2013, per kwartaal en jaar).
Valt terug op 85276NED (BRC 2014, 2013-2025) als de nieuwe tabel niet werkt.

Ophalen gebeurt alleen als CBS de tabel sinds de vorige run heeft gewijzigd
(veld `Modified` in TableInfos). De dagelijkse run kost dus vrijwel niets;
nieuwe cijfers verschijnen automatisch zodra CBS ze publiceert.

Uitvoer:
  data/cbs_beroepen_jaar.csv      jaar x persoonskenmerk x beroep (x 1 000)
  data/cbs_beroepen_kwartaal.csv  kwartaal x beroep, totaal personen (x 1 000)
  data/meta/cbs_<tabel>.json      tabelstructuur, voor controle en debugging
"""
from __future__ import annotations

import json
import re

from .. import config, store
from . import Http, log

BASE = "https://opendata.cbs.nl/ODataApi/odata/{table}"
YEAR_FIELDS = ["jaar", "kenmerk_groep", "kenmerk", "beroep_code", "beroep", "waarde"]
QUARTER_FIELDS = ["kwartaal", "beroep_code", "beroep", "waarde"]
_CODE_RX = re.compile(r"^\s*(\d{1,4})\s+(.*)$")


COLLECTOR_VERSION = "2"  # ophogen dwingt bij de volgende run een nieuwe download af


def split_beroep(title: str, description: str = "") -> tuple[str, str]:
    """'0812 Databank- en netwerkspecialisten' -> ('0812', 'Databank- en ...').

    De API kort lange titels af ('Klantenservice medewerkers en re...'). De
    omschrijving begint met de volledige naam ('Naam: Deze beroepsgroep ...'),
    dus die gebruiken we als de titel is afgekort.
    """
    m = _CODE_RX.match(title or "")
    code, name = (m.group(1), m.group(2).strip()) if m else ("", (title or "").strip())
    full = (description or "").split(":", 1)[0].strip()
    if full and (name.endswith("...") or name.endswith("…")) and full.lower().startswith(name.rstrip(".… ").lower()[:10]):
        name = full
    return code, name


def _period(p: str) -> tuple[str, str] | None:
    p = (p or "").strip()
    m = re.fullmatch(r"(\d{4})JJ00", p)
    if m:
        return "jaar", m.group(1)
    m = re.fullmatch(r"(\d{4})KW0?(\d)", p)
    if m:
        return "kwartaal", f"{m.group(1)}Q{m.group(2)}"
    return None


def _get_all(http, url: str, params: dict | None = None) -> list[dict] | None:
    """Haal een OData-collectie op, inclusief vervolgpagina's."""
    rows, nxt, first = [], url, True
    while nxt:
        d = http.get(nxt, params if first else None)
        first = False
        if d is None:
            return None if not rows else rows
        rows += d.get("value") or []
        nxt = d.get("odata.nextLink")
    return rows


class Table:
    def __init__(self, http, table: str):
        self.http, self.table, self.base = http, table, BASE.format(table=table)
        self.info: dict = {}
        self.props: list[dict] = []
        self.dims: dict[str, list[dict]] = {}
        self.groups: dict[str, dict] = {}

    def load_meta(self) -> bool:
        info = _get_all(self.http, f"{self.base}/TableInfos")
        if not info:
            return False
        self.info = info[0]
        self.props = _get_all(self.http, f"{self.base}/DataProperties") or []
        for p in self.props:
            if p.get("Type") in ("Dimension", "TimeDimension", "GeoDimension", "GeoDetail"):
                self.dims[p["Key"]] = _get_all(self.http, f"{self.base}/{p['Key']}") or []
        for g in _get_all(self.http, f"{self.base}/CategoryGroups") or []:
            self.groups[str(g.get("ID"))] = g
        return bool(self.dims)

    # -- dimensies herkennen ------------------------------------------------
    def dim_key(self, *hints: str) -> str | None:
        for k in self.dims:
            if any(h in k.lower() for h in hints):
                return k
        return None

    @property
    def topic(self) -> str | None:
        topics = [p for p in self.props if p.get("Type") == "Topic"]
        for t in topics:
            if "werkzame" in (t.get("Title") or "").lower():
                return t["Key"]
        return topics[0]["Key"] if topics else None

    def total_key(self, dim: str) -> str | None:
        for e in self.dims.get(dim, []):
            if (e.get("Title") or "").lower().startswith("totaal"):
                return e["Key"]
        return self.dims[dim][0]["Key"] if self.dims.get(dim) else None

    def group_title(self, entry: dict) -> str:
        """Naam van de categoriegroep (bv. 'Leeftijd'), met ouders erbij."""
        gid = str(entry.get("CategoryGroupID") or "")
        names = []
        while gid and gid in self.groups and len(names) < 4:
            g = self.groups[gid]
            names.append(g.get("Title") or "")
            gid = str(g.get("ParentID") or "")
        return " / ".join(reversed([n for n in names if n])) or "Totaal"

    def meta_dump(self) -> dict:
        return {
            "table": self.table, "info": self.info,
            "properties": self.props,
            "dimensions": {k: v for k, v in self.dims.items()},
            "category_groups": list(self.groups.values()),
        }

    # -- data -----------------------------------------------------------------
    def fetch(self, filt: str) -> list[dict] | None:
        return _get_all(self.http, f"{self.base}/TypedDataSet", {"$filter": filt})


def _matches_ai_groups(dims_beroep: list[dict]) -> int:
    from ..analysis_ai import match_group
    names = [split_beroep(e.get("Title", ""), e.get("Description", ""))[1] for e in dims_beroep]
    return len({g for n in names if (g := match_group(n))})


def _collect_table(http, table: str, force: bool) -> bool | None:
    """True = bijgewerkt, False = ongewijzigd, None = mislukt."""
    t = Table(http, table)
    if not t.load_meta():
        log.warning("CBS %s: metadata niet bereikbaar", table)
        return None

    store.path("meta/x").parent.mkdir(parents=True, exist_ok=True)
    (store.DATA_DIR / "meta" / f"cbs_{table}.json").write_text(
        json.dumps(t.meta_dump(), ensure_ascii=False, indent=1), encoding="utf-8")

    versions = store.read_json("meta/versions.json")
    modified = f'{t.info.get("Modified") or ""}|v{COLLECTOR_VERSION}'
    have = (store.DATA_DIR / "cbs_beroepen_jaar.csv").exists()
    if not force and have and versions.get(f"cbs:{table}") == modified:
        log.info("CBS %s: ongewijzigd sinds %s, overgeslagen", table, modified)
        return False

    k_ber = t.dim_key("beroep")
    k_per = t.dim_key("perioden")
    k_pk = t.dim_key("persoonskenmerk", "kenmerk")
    k_sex = t.dim_key("geslacht")
    topic = t.topic
    if not (k_ber and k_per and topic):
        log.warning("CBS %s: dimensies niet herkend: %s", table, list(t.dims))
        return None
    n_match = _matches_ai_groups(t.dims[k_ber])
    log.info("CBS %s: %d van de %d AI-groepen herkend", table, n_match, len(config.AI_GROUPS))
    if n_match < len(config.AI_GROUPS) // 2:
        log.warning("CBS %s: te weinig beroepsgroepen herkend, tabel overgeslagen", table)
        return None

    beroep = {e["Key"].strip(): split_beroep(e.get("Title", ""), e.get("Description", "")) for e in t.dims[k_ber]}
    pk = {e["Key"].strip(): e for e in t.dims.get(k_pk, [])}
    sex_tot = t.total_key(k_sex) if k_sex else None
    pk_tot = t.total_key(k_pk) if k_pk else None

    def base_filter() -> list[str]:
        f = []
        if k_sex and sex_tot:
            f.append(f"{k_sex} eq '{sex_tot}'")
        return f

    # ---- jaarcijfers: per persoonskenmerk één request ------------------
    year_rows = []
    pk_keys = [e["Key"] for e in t.dims.get(k_pk, [])] or [None]
    for key in pk_keys:
        f = base_filter() + [f"substringof('JJ',{k_per})"]
        if key is not None:
            f.append(f"{k_pk} eq '{key}'")
        rows = t.fetch(" and ".join(f))
        if rows is None:
            log.warning("CBS %s: jaarcijfers voor %s mislukt", table, key)
            continue
        entry = pk.get((key or "").strip(), {})
        for r in rows:
            per = _period(r.get(k_per))
            val = r.get(topic)
            if not per or per[0] != "jaar" or val is None:
                continue
            code, name = beroep.get((r.get(k_ber) or "").strip(), ("", ""))
            year_rows.append({
                "jaar": per[1],
                "kenmerk_groep": t.group_title(entry) if entry else "Totaal",
                "kenmerk": (entry.get("Title") or "Totaal personen").strip(),
                "beroep_code": code, "beroep": name, "waarde": val,
            })

    # ---- kwartaalcijfers: totaal personen, per jaar één request ---------
    q_rows = []
    years = sorted({r["jaar"] for r in year_rows} | {str(int(max(
        [r["jaar"] for r in year_rows] or ["2025"])) + 1)})
    for y in years:
        f = base_filter() + [f"substringof('{y}KW',{k_per})"]
        if k_pk and pk_tot:
            f.append(f"{k_pk} eq '{pk_tot}'")
        for r in t.fetch(" and ".join(f)) or []:
            per = _period(r.get(k_per))
            val = r.get(topic)
            if not per or per[0] != "kwartaal" or val is None:
                continue
            code, name = beroep.get((r.get(k_ber) or "").strip(), ("", ""))
            q_rows.append({"kwartaal": per[1], "beroep_code": code, "beroep": name, "waarde": val})

    if not year_rows:
        log.warning("CBS %s: geen jaarcijfers ontvangen", table)
        return None
    store.write_csv("cbs_beroepen_jaar.csv", year_rows, YEAR_FIELDS)
    store.write_csv("cbs_beroepen_kwartaal.csv", q_rows, QUARTER_FIELDS)
    versions[f"cbs:{table}"] = modified
    versions["cbs_beroepen_tabel"] = table
    versions["cbs_beroepen_titel"] = t.info.get("Title", "")
    store.write_json("meta/versions.json", versions)
    log.info("CBS %s: %d jaar- en %d kwartaalrijen", table, len(year_rows), len(q_rows))
    return True


def collect(force: bool = False) -> int:
    http = Http(timeout=90)
    for table in config.CBS_BEROEP_TABLES:
        res = _collect_table(http, table, force)
        if res is not None:
            return 1 if res else 0
    log.warning("CBS beroepen: geen enkele tabel bruikbaar")
    return 0
