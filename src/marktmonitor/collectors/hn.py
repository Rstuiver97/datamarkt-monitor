"""Hacker News 'Ask HN: Who is hiring?' (maandelijks, via de gratis Algolia API).

Een vroege indicator voor de Amerikaanse tech-markt: welk aandeel van de
vacatureposts noemt een bepaalde rol of tool? Bij de eerste run halen we
24 maanden historie op, daarna alleen de laatste 2 maanden.
"""
from __future__ import annotations

import re
from datetime import datetime

from .. import classify, store
from . import Http, log

SEARCH = "https://hn.algolia.com/api/v1/search_by_date"
ITEM = "https://hn.algolia.com/api/v1/items/{id}"
_TITLE_RX = re.compile(r"who is hiring\?\s*\((\w+)\s+(\d{4})\)", re.IGNORECASE)


def _threads(http, months: int) -> list[tuple[str, str]]:
    found, page = {}, 0
    while len(found) < months and page < 10:
        d = http.get(SEARCH, {"tags": "story,author_whoishiring", "hitsPerPage": 50, "page": page})
        hits = (d or {}).get("hits") or []
        if not hits:
            break
        for h in hits:
            m = _TITLE_RX.search(h.get("title") or "")
            if not m:
                continue
            try:
                month = datetime.strptime(f"{m.group(1)} {m.group(2)}", "%B %Y").strftime("%Y-%m")
            except ValueError:
                continue
            found.setdefault(month, h["objectID"])
        page += 1
    return sorted(found.items(), reverse=True)[:months]


def summarize_thread(month: str, thread_id: str, comments: list[str]) -> list[dict]:
    posts = [c for c in comments if c and len(c) > 80]
    total = len(posts)
    role_n: dict[str, int] = {}
    skill_n: dict[str, int] = {}
    data_posts = 0
    for text in posts:
        clean = classify.clean_text(text)
        head = clean[:400]  # rollen staan bijna altijd in de eerste regel(s)
        roles = classify.find_roles(head)
        for r in roles:
            role_n[r] = role_n.get(r, 0) + 1
        if roles:
            data_posts += 1
        for s in classify.extract_skills(clean):
            skill_n[s] = skill_n.get(s, 0) + 1
    base = {"month": month, "thread_id": thread_id, "total_posts": total}
    rows = [{**base, "kind": "role", "name": k, "n": v} for k, v in role_n.items()]
    rows.append({**base, "kind": "role", "name": "_any_data_role", "n": data_posts})
    rows += [{**base, "kind": "skill", "name": k, "n": v} for k, v in skill_n.items()]
    return rows


def collect(backfill_months: int | None = None) -> int:
    http = Http(timeout=90)
    have = {r["month"] for r in store.read_csv("hn_monthly.csv")}
    months = backfill_months or (2 if have else 24)
    rows = []
    for month, tid in _threads(http, months):
        item = http.get(ITEM.format(id=tid))
        if not item:
            continue
        comments = [c.get("text") for c in item.get("children") or [] if c.get("text")]
        rows += summarize_thread(month, tid, comments)
    if rows:
        store.upsert_hn(rows)
    log.info("Hacker News: %d rijen", len(rows))
    return len(rows)
