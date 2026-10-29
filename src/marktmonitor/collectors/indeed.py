"""Indeed Hiring Lab Job Postings Index (GitHub, CC BY 4.0).

Nederland heeft alleen een totaalindex; voor sectoren (Data & Analytics,
Software Development) gebruiken we de VS, Duitsland en het VK als
Europese referentie.
"""
from __future__ import annotations

import csv
import io

from .. import store
from . import Http, log

RAW = "https://raw.githubusercontent.com/hiring-lab/job_postings_tracker/master/{cc}/{file}"
SECTORS = {"Data & Analytics", "Software Development"}

SOURCES = [
    ("NL", "aggregate_job_postings_NL.csv", "aggregate"),
    ("US", "aggregate_job_postings_US.csv", "aggregate"),
    ("US", "job_postings_by_sector_US.csv", "sector"),
    ("DE", "aggregate_job_postings_DE.csv", "aggregate"),
    ("DE", "job_postings_by_sector_DE.csv", "sector"),
    ("GB", "job_postings_by_sector_GB.csv", "sector"),
]
FIELDS = ["date", "country", "series", "index"]


def collect() -> int:
    http = Http(timeout=60)
    rows = []
    for cc, fname, kind in SOURCES:
        text = http.get(RAW.format(cc=cc, file=fname), expect_json=False)
        if not text:
            log.warning("Indeed: %s/%s niet beschikbaar", cc, fname)
            continue
        for r in csv.DictReader(io.StringIO(text)):
            if r.get("variable") != "total postings":
                continue
            if kind == "aggregate":
                val = r.get("indeed_job_postings_index_SA")
                series = "Alle vacatures"
            else:
                if r.get("display_name") not in SECTORS:
                    continue
                val = r.get("indeed_job_postings_index")
                series = r["display_name"]
            if val:
                rows.append({"date": r["date"], "country": cc, "series": series, "index": val})
    if rows:
        store.write_csv("indeed.csv", rows, FIELDS)
    log.info("Indeed: %d rijen", len(rows))
    return len(rows)
