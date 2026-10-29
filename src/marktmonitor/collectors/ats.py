"""Openbare vacature-feeds van werkgevers (Greenhouse, Lever, Recruitee, Ashby,
Workable, SmartRecruiters). Geen API-key nodig.

De lijst met werkgevers staat in config/companies.json. Draai
`python -m marktmonitor validate-companies` om te controleren welke feeds werken.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .. import classify
from . import Http, log

COMPANIES_FILE = Path(__file__).resolve().parents[3] / "config" / "companies.json"


def _ts(ms) -> str:
    try:
        return datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc).date().isoformat()
    except (TypeError, ValueError):
        return ""


def _greenhouse(http, slug):
    d = http.get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs", {"content": "true"})
    if d is None:
        return None

    def rows():
        for j in d.get("jobs", []):
            yield {
                "id": j.get("id"), "title": j.get("title"),
                "location": (j.get("location") or {}).get("name"),
                "url": j.get("absolute_url"), "posted_at": (j.get("updated_at") or "")[:10],
                "description": j.get("content"),
            }

    return list(rows())


def _lever(http, slug):
    d = http.get(f"https://api.lever.co/v0/postings/{slug}", {"mode": "json"})
    if d is None:
        return None

    def rows():
        for j in d:
            cats = j.get("categories") or {}
            lists = " ".join(
                f"{x.get('text', '')} {x.get('content', '')}" for x in (j.get("lists") or [])
            )
            sr = j.get("salaryRange") or {}
            sal = None
            if sr.get("min"):
                period = {"per-year-salary": "jaar", "per-month-salary": "maand",
                          "per-hour-wage": "uur"}.get(sr.get("interval"), "jaar")
                sal = {"min": float(sr["min"]), "max": float(sr.get("max") or sr["min"]),
                       "currency": sr.get("currency") or "USD", "period": period}
            yield {
                "id": j.get("id"), "title": j.get("text"),
                "location": cats.get("location") or ", ".join(cats.get("allLocations") or []),
                "url": j.get("hostedUrl"), "posted_at": _ts(j.get("createdAt")),
                "description": f"{j.get('descriptionPlain', '')} {lists} {j.get('additionalPlain', '')}",
                "remote_flag": j.get("workplaceType") == "remote", "salary": sal,
            }

    return list(rows())


def _recruitee(http, slug):
    d = http.get(f"https://{slug}.recruitee.com/api/offers/")
    if d is None:
        return None

    def rows():
        for j in d.get("offers", []):
            loc = ", ".join(filter(None, [j.get("city"), j.get("country")])) or j.get("location")
            sal = None
            s = j.get("salary") or {}
            if isinstance(s, dict) and s.get("min"):
                sal = {"min": float(s["min"]), "max": float(s.get("max") or s["min"]),
                       "currency": (s.get("currency") or "EUR").upper(),
                       "period": {"month": "maand", "hour": "uur"}.get(s.get("period"), "jaar")}
            yield {
                "id": j.get("id"), "title": j.get("title"), "location": loc,
                "url": j.get("careers_url"), "posted_at": (j.get("published_at") or j.get("created_at") or "")[:10],
                "description": f"{j.get('description', '')} {j.get('requirements', '')}",
                "remote_flag": bool(j.get("remote")), "salary": sal,
            }

    return list(rows())


def _ashby(http, slug):
    d = http.get(f"https://api.ashbyhq.com/posting-api/job-board/{slug}",
                 {"includeCompensation": "true"})
    if d is None:
        return None

    def rows():
        for j in d.get("jobs", []):
            comp = (j.get("compensation") or {}).get("compensationTierSummary") or ""
            yield {
                "id": j.get("id"), "title": j.get("title"),
                "location": j.get("location") or "",
                "url": j.get("jobUrl"), "posted_at": (j.get("publishedAt") or "")[:10],
                "description": f"{j.get('descriptionPlain', '')} {comp}",
                "remote_flag": bool(j.get("isRemote")),
            }

    return list(rows())


def _workable(http, slug):
    d = http.get(f"https://apply.workable.com/api/v1/widget/accounts/{slug}")
    if d is None:
        return None

    def rows():
        for j in d.get("jobs", []):
            yield {
                "id": j.get("shortcode") or j.get("id"), "title": j.get("title"),
                "location": ", ".join(filter(None, [j.get("city"), j.get("country")])),
                "url": j.get("url") or j.get("shortlink"), "posted_at": (j.get("published_on") or "")[:10],
                "description": "", "remote_flag": bool(j.get("telecommuting")),
            }

    return list(rows())


def _smartrecruiters(http, slug):
    d = http.get(f"https://api.smartrecruiters.com/v1/companies/{slug}/postings", {"limit": 100})
    if d is None:
        return None

    def rows():
        for j in d.get("content", []):
            loc = j.get("location") or {}
            yield {
                "id": j.get("id"), "title": j.get("name"),
                "location": ", ".join(filter(None, [loc.get("city"), loc.get("country")])),
                "url": f"https://jobs.smartrecruiters.com/{slug}/{j.get('id')}",
                "posted_at": (j.get("releasedDate") or "")[:10], "description": "",
                "remote_flag": bool(loc.get("remote")),
            }

    return list(rows())


FETCHERS = {
    "greenhouse": _greenhouse, "lever": _lever, "recruitee": _recruitee,
    "ashby": _ashby, "workable": _workable, "smartrecruiters": _smartrecruiters,
}


def load_companies() -> list[dict]:
    with COMPANIES_FILE.open(encoding="utf-8") as f:
        return [c for c in json.load(f)["companies"] if c.get("enabled", True)]


def collect(today: str) -> tuple[list[dict], list[dict]]:
    http = Http(pause=0.3)
    postings, counts, failed = [], [], []
    per_country_role: dict[tuple[str, str], int] = {}
    for c in load_companies():
        fetch = FETCHERS.get(c["ats"])
        if not fetch:
            continue
        gen = fetch(http, c["slug"])
        if gen is None:
            failed.append(c["name"])
            continue
        for j in gen:
            role = classify.classify_role(j.get("title"))
            if not role:
                continue
            country = classify.detect_country(j.get("location")) or c.get("default_country")
            if country not in ("nl", "us"):
                continue
            postings.append({
                "uid": f"{c['ats']}:{c['slug']}:{j['id']}",
                "source": c["ats"], "country": country, "company": c["name"],
                "title": j.get("title"), "location": j.get("location"), "url": j.get("url"),
                "posted_at": j.get("posted_at"), "description": j.get("description"),
                "remote_flag": j.get("remote_flag"), "salary": j.get("salary"),
            })
            per_country_role[(country, role)] = per_country_role.get((country, role), 0) + 1
    for (country, role), n in sorted(per_country_role.items()):
        counts.append({"date": today, "source": "ats", "country": country, "query": role, "count": n})
    if failed:
        log.warning("ATS-feeds niet gevonden (controleer slug): %s", ", ".join(failed))
    log.info("ATS: %d data-vacatures uit %d werkgevers", len(postings), len(load_companies()))
    return postings, counts


def validate() -> list[dict]:
    """Controleer per werkgever of de feed werkt en hoeveel (data-)vacatures er zijn."""
    http = Http(pause=0.2, retries=1)
    report = []
    for c in load_companies():
        gen = FETCHERS[c["ats"]](http, c["slug"])
        if gen is None:
            report.append({**c, "status": "NIET GEVONDEN", "jobs": 0, "data_jobs": 0})
            continue
        jobs = list(gen)
        n_data = sum(1 for j in jobs if classify.classify_role(j.get("title")))
        report.append({**c, "status": "ok", "jobs": len(jobs), "data_jobs": n_data})
    return report
