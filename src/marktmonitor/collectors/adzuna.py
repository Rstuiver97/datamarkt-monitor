"""Adzuna API (gratis developer-account): vacatures + totaal-aantallen per zoekterm.

Eén call per zoekterm levert zowel het totaal aantal actieve vacatures (`count`)
als de 50 nieuwste vacatures op. Het aantal calls per run is begrensd zodat je
ruim binnen het gratis tegoed blijft (instelbaar via ADZUNA_MAX_CALLS).
"""
from __future__ import annotations

import os
from datetime import date, datetime, timedelta

from .. import config
from . import Http, log

BASE = "https://api.adzuna.com/v1/api/jobs/{country}/search/{page}"
PER_PAGE = 50


def _is_recent(created: str | None, days: int) -> bool:
    if not created:
        return False
    try:
        d = datetime.fromisoformat(created.replace("Z", "+00:00")).date()
    except ValueError:
        return False
    return d >= date.today() - timedelta(days=days)


def _normalize(job: dict, country: str) -> dict:
    predicted = str(job.get("salary_is_predicted", "1")) == "1"
    sal = None
    if not predicted and job.get("salary_min"):
        sal = {
            "min": float(job["salary_min"]),
            "max": float(job.get("salary_max") or job["salary_min"]),
            "currency": config.CURRENCY[country],
            "period": "jaar",
        }
    return {
        "uid": f"adzuna:{country}:{job.get('id')}",
        "source": "adzuna",
        "country": country,
        "company": (job.get("company") or {}).get("display_name"),
        "title": job.get("title"),
        "location": (job.get("location") or {}).get("display_name"),
        "url": job.get("redirect_url"),
        "posted_at": (job.get("created") or "")[:10],
        "description": job.get("description"),  # Adzuna geeft een ingekorte tekst
        "salary": sal,
    }


def collect(today: str, app_id: str | None = None, app_key: str | None = None,
            max_calls: int | None = None) -> tuple[list[dict], list[dict]]:
    app_id = app_id or os.environ.get("ADZUNA_APP_ID")
    app_key = app_key or os.environ.get("ADZUNA_APP_KEY")
    if not (app_id and app_key):
        log.warning("Adzuna overgeslagen: ADZUNA_APP_ID/ADZUNA_APP_KEY ontbreken.")
        return [], []
    max_calls = max_calls or int(os.environ.get("ADZUNA_MAX_CALLS", "30"))
    http = Http(pause=2.6)  # free tier: max ~25 calls/minuut

    postings, counts = [], []
    pending_more = []  # (country, query) waar pagina 2+ nog nieuwe vacatures kan bevatten

    for country, queries in config.ADZUNA_QUERIES.items():
        for q in queries:
            if http.calls >= max_calls:
                log.warning("Adzuna call-budget (%s) bereikt.", max_calls)
                break
            params = {
                "app_id": app_id, "app_key": app_key, "results_per_page": PER_PAGE,
                "title_only": q, "sort_by": "date", "content-type": "application/json",
            }
            data = http.get(BASE.format(country=country, page=1), params)
            if not data:
                continue
            counts.append({"date": today, "source": "adzuna", "country": country,
                           "query": q, "count": int(data.get("count") or 0)})
            results = data.get("results") or []
            postings += [_normalize(j, country) for j in results]
            if len(results) == PER_PAGE and _is_recent(results[-1].get("created"), 2):
                pending_more.append((country, q))

    # Resterend budget: extra pagina's voor zoektermen met veel nieuwe vacatures
    for country, q in pending_more:
        page = 2
        while http.calls < max_calls and page <= 5:
            params = {
                "app_id": app_id, "app_key": app_key, "results_per_page": PER_PAGE,
                "title_only": q, "sort_by": "date", "content-type": "application/json",
            }
            data = http.get(BASE.format(country=country, page=page), params)
            results = (data or {}).get("results") or []
            postings += [_normalize(j, country) for j in results]
            if len(results) < PER_PAGE or not _is_recent(results[-1].get("created"), 2):
                break
            page += 1

    log.info("Adzuna: %d vacatures, %d tellingen, %d calls", len(postings), len(counts), http.calls)
    return postings, counts
