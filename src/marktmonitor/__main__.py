"""Gebruik:

    python -m marktmonitor run                 # alles ophalen + dashboard bouwen
    python -m marktmonitor collect [bron ...]  # alleen ophalen (adzuna ats hn indeed cbs)
    python -m marktmonitor report              # alleen dashboard bouwen uit data/
    python -m marktmonitor validate-companies  # controleer werkgevers-feeds
    python -m marktmonitor demo                # dashboard met synthetische data
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import date

from . import classify, report, store
from .collectors import log

ALL_SOURCES = ["indeed", "hn", "cbs", "ats", "adzuna"]


def collect(sources: list[str]) -> int:
    today = date.today().isoformat()
    failures = 0
    raw, counts = [], []
    for src in sources:
        try:
            if src == "indeed":
                from .collectors import indeed
                indeed.collect()
            elif src == "hn":
                from .collectors import hn
                hn.collect()
            elif src == "cbs":
                from .collectors import cbs
                cbs.collect()
            elif src == "ats":
                from .collectors import ats
                p, c = ats.collect(today)
                raw += p
                counts += c
            elif src == "adzuna":
                from .collectors import adzuna
                p, c = adzuna.collect(today)
                raw += p
                counts += c
            else:
                log.error("Onbekende bron: %s", src)
        except Exception:  # één kapotte bron mag de rest niet stoppen
            log.exception("Bron %s faalde", src)
            failures += 1

    enriched = [e for e in (classify.enrich(p) for p in raw) if e]
    added, updated = store.upsert_postings(enriched, today)
    if counts:
        store.append_counts(counts)
    log.info("Vacatures: %d nieuw, %d bijgewerkt (%d ruwe, %d data-rollen)",
             added, updated, len(raw), len(enriched))
    return failures


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ap = argparse.ArgumentParser(prog="marktmonitor")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("collect")
    c.add_argument("sources", nargs="*", default=ALL_SOURCES)
    sub.add_parser("report")
    r = sub.add_parser("run")
    r.add_argument("sources", nargs="*", default=ALL_SOURCES)
    sub.add_parser("validate-companies")
    sub.add_parser("demo")
    args = ap.parse_args(argv)

    if args.cmd in ("collect", "run"):
        failures = collect(args.sources)
        if args.cmd == "run":
            path = report.render(report.build())
            log.info("Dashboard: %s", path)
        # Alleen falen als álle bronnen faalden
        return 1 if failures == len(args.sources) else 0
    if args.cmd == "report":
        log.info("Dashboard: %s", report.render(report.build()))
        return 0
    if args.cmd == "validate-companies":
        from .collectors import ats
        rows = ats.validate()
        w = max(len(x["name"]) for x in rows)
        for x in rows:
            print(f"{x['name']:<{w}}  {x['ats']:<15} {x['slug']:<25} {x['status']:<14} "
                  f"{x['jobs']:>5} vacatures, {x['data_jobs']:>4} data-rollen")
        return 0
    if args.cmd == "demo":
        from . import demo
        demo.generate()
        from .collectors import indeed
        try:
            indeed.collect()
        except Exception:
            log.exception("Indeed niet bereikbaar; demo zonder Indeed-reeksen")
        path = report.render(report.build(demo=True), store.DATA_DIR.parent / "site")
        log.info("Demo-dashboard: %s", path)
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
