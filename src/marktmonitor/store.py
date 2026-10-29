"""Opslag in platte CSV-bestanden onder data/ (git-vriendelijk, gratis, Excel-leesbaar)."""
from __future__ import annotations

import csv
import os
from pathlib import Path

DATA_DIR = Path(os.environ.get("MARKTMONITOR_DATA", Path(__file__).resolve().parents[2] / "data"))

POSTING_FIELDS = [
    "uid", "source", "country", "company", "title", "location", "url",
    "posted_at", "first_seen", "last_seen", "role", "seniority", "work_mode",
    "skills", "salary_annual", "salary_hourly", "salary_currency", "dedup_key",
]
COUNT_FIELDS = ["date", "source", "country", "query", "count"]
HN_FIELDS = ["month", "thread_id", "total_posts", "kind", "name", "n"]


def path(name: str) -> Path:
    p = DATA_DIR / name
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def read_csv(name: str) -> list[dict]:
    p = path(name)
    if not p.exists():
        return []
    with p.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(name: str, rows: list[dict], fields: list[str]) -> None:
    p = path(name)
    tmp = p.with_suffix(p.suffix + ".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in fields})
    tmp.replace(p)


# --------------------------------------------------------------------------
# Vacatures
# --------------------------------------------------------------------------
def upsert_postings(new: list[dict], today: str) -> tuple[int, int]:
    """Voeg nieuwe vacatures toe en werk last_seen bij van bestaande.

    Geeft (aantal nieuw, aantal bijgewerkt) terug.
    """
    rows = {r["uid"]: r for r in read_csv("postings.csv")}
    added = updated = 0
    for p in new:
        p = dict(p)
        if isinstance(p.get("skills"), list):
            p["skills"] = ";".join(p["skills"])
        uid = p["uid"]
        if uid in rows:
            old = rows[uid]
            old["last_seen"] = today
            # Verrijkte velden verversen (taxonomie kan verbeterd zijn)
            for k in ("role", "seniority", "work_mode", "skills", "title", "dedup_key"):
                if p.get(k):
                    old[k] = p[k]
            for k in ("salary_annual", "salary_hourly", "salary_currency"):
                if p.get(k) not in (None, ""):
                    old[k] = p[k]
            updated += 1
        else:
            p.setdefault("first_seen", today)
            p["last_seen"] = today
            rows[uid] = p
            added += 1
    ordered = sorted(rows.values(), key=lambda r: (r.get("first_seen", ""), r["uid"]))
    write_csv("postings.csv", ordered, POSTING_FIELDS)
    return added, updated


def append_counts(new: list[dict]) -> None:
    """Dagelijkse tellingen; een (datum, bron, land, query) wordt overschreven bij herhaalde run."""
    rows = read_csv("counts.csv")
    keys = {(r["date"], r["source"], r["country"], r["query"]) for r in new}
    rows = [r for r in rows if (r["date"], r["source"], r["country"], r["query"]) not in keys]
    rows.extend(new)
    rows.sort(key=lambda r: (r["date"], r["source"], r["country"], r["query"]))
    write_csv("counts.csv", rows, COUNT_FIELDS)


def upsert_hn(new: list[dict]) -> None:
    rows = read_csv("hn_monthly.csv")
    months = {r["month"] for r in new}
    rows = [r for r in rows if r["month"] not in months] + new
    rows.sort(key=lambda r: (r["month"], r["kind"], r["name"]))
    write_csv("hn_monthly.csv", rows, HN_FIELDS)
