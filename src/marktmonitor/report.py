"""Aggregaties voor het dashboard en het renderen van site/index.html."""
from __future__ import annotations

import json
import statistics
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

from . import config, store
from .classify import ROLE_LABELS

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "templates" / "dashboard.html"
ROLES = list(config.ROLES)
MIN_N_SALARY = 5   # minimaal aantal vacatures met salaris om een mediaan te tonen
COMPOSITION_DAYS = 90


def _d(s: str | None) -> date | None:
    try:
        return datetime.fromisoformat(s[:10]).date() if s else None
    except ValueError:
        return None


def _dedup(rows: list[dict]) -> list[dict]:
    """Eén rij per dedup_key (de eerst geziene), zodat een vacature op meerdere
    bronnen maar één keer telt."""
    seen, out = set(), []
    for r in sorted(rows, key=lambda r: (r.get("first_seen", ""), r["uid"])):
        k = r.get("dedup_key") or r["uid"]
        if k in seen:
            continue
        seen.add(k)
        out.append(r)
    return out


def _pct(n: int, total: int) -> float:
    return round(100 * n / total, 1) if total else 0.0


def _quantiles(vals: list[float]) -> dict | None:
    if len(vals) < MIN_N_SALARY:
        return None
    q = statistics.quantiles(sorted(vals), n=4, method="inclusive")
    return {"p25": round(q[0]), "mediaan": round(q[1]), "p75": round(q[2]), "n": len(vals)}


def build(today: date | None = None, demo: bool = False) -> dict:
    today = today or date.today()
    postings = _dedup(store.read_csv("postings.csv"))
    since = today - timedelta(days=COMPOSITION_DAYS)
    recent = [p for p in postings if (_d(p.get("first_seen")) or date.min) >= since]

    out: dict = {
        "meta": {
            "gegenereerd": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "vandaag": today.isoformat(),
            "demo": demo,
            "venster_dagen": COMPOSITION_DAYS,
            "rollen": ROLE_LABELS,
            "landen": config.COUNTRY_LABELS,
            "totaal_vacatures": len(postings),
            "bronnen": dict(Counter(p["source"] for p in postings)),
        }
    }

    # ---- KPI's: nieuwe vacatures laatste 30 dagen per land en rol --------
    d30 = today - timedelta(days=30)
    d60 = today - timedelta(days=60)
    kpi = {}
    for c in config.COUNTRY_LABELS:
        rows = [p for p in postings if p["country"] == c]
        cur = Counter(p["role"] for p in rows if (_d(p["first_seen"]) or date.min) > d30)
        prev = Counter(p["role"] for p in rows if d60 < (_d(p["first_seen"]) or date.min) <= d30)
        kpi[c] = {r: {"n30": cur.get(r, 0), "vorige30": prev.get(r, 0)} for r in ROLES}
    out["kpi"] = kpi

    # ---- Nieuwe vacatures per week (laatste 26 weken) --------------------
    # Alleen volledige weken: de lopende week zou als een daling ogen.
    this_monday = today - timedelta(days=today.weekday())
    start = this_monday - timedelta(weeks=26)
    weeks = [(start + timedelta(weeks=i)).isoformat() for i in range(26)]
    weekly = {}
    for c in config.COUNTRY_LABELS:
        cnt = defaultdict(Counter)
        for p in postings:
            fs = _d(p["first_seen"])
            if p["country"] != c or not fs or fs < start or fs >= this_monday:
                continue
            wk = (fs - timedelta(days=fs.weekday())).isoformat()
            cnt[p["role"]][wk] += 1
        weekly[c] = {r: [cnt[r].get(w, 0) for w in weeks] for r in ROLES}
    out["wekelijks"] = {"weken": weeks, "data": weekly}

    # ---- Adzuna totaal-aantallen (marktvolume) --------------------------
    counts = [r for r in store.read_csv("counts.csv") if r["source"] == "adzuna"]
    vol = defaultdict(lambda: defaultdict(Counter))
    for r in counts:
        role = config.QUERY_ROLE.get(r["query"])
        if role:
            vol[r["country"]][role][r["date"]] += int(r["count"] or 0)
    dates = sorted({r["date"] for r in counts})
    out["volume"] = {
        "datums": dates,
        "data": {c: {r: [vol[c][r].get(d) for d in dates] for r in ROLES} for c in vol},
    }

    # ---- Indeed index ----------------------------------------------------
    indeed = store.read_csv("indeed.csv")
    keep = ["NL · Alle vacatures", "US · Alle vacatures", "US · Data & Analytics",
            "US · Software Development", "DE · Data & Analytics", "DE · Software Development",
            "GB · Data & Analytics", "GB · Software Development"]
    series = defaultdict(dict)
    for r in indeed:
        d = _d(r["date"])
        name = f"{r['country']} · {r['series']}"
        # Wekelijks sampelen (maandag) houdt de pagina licht
        if d and d.weekday() == 0 and name in keep:
            series[name][r["date"]] = float(r["index"])
    idx_dates = sorted({d for s in series.values() for d in s})
    out["indeed"] = {
        "datums": idx_dates,
        "reeksen": {k: [series[k].get(d) for d in idx_dates] for k in keep if k in series},
    }

    # ---- Skills: aandeel vacatures dat een skill noemt -------------------
    skills_out = {}
    for c in config.COUNTRY_LABELS:
        rows = [p for p in recent if p["country"] == c]
        per_role = {}
        for r in ROLES + ["_alle"]:
            sub = rows if r == "_alle" else [p for p in rows if p["role"] == r]
            cnt = Counter(s for p in sub for s in (p.get("skills") or "").split(";") if s)
            per_role[r] = {"n": len(sub), "aandeel": {k: _pct(v, len(sub)) for k, v in cnt.most_common(25)}}
        skills_out[c] = per_role
    out["skills"] = skills_out
    out["skill_categorie"] = {k: v[0] for k, v in config.SKILLS.items()}

    # VS-voorsprong: waar ligt het aandeel in de VS het hoogst boven NL?
    nl_all = skills_out["nl"]["_alle"]
    us_all = skills_out["us"]["_alle"]
    lead = []
    if nl_all["n"] >= 20 and us_all["n"] >= 20:
        names = set(nl_all["aandeel"]) | set(us_all["aandeel"])
        for s in names:
            a, b = us_all["aandeel"].get(s, 0.0), nl_all["aandeel"].get(s, 0.0)
            lead.append({"skill": s, "us": a, "nl": b, "verschil": round(a - b, 1)})
        lead.sort(key=lambda x: -x["verschil"])
    out["voorsprong"] = lead[:12]

    # ---- Salaris --------------------------------------------------------
    sal = {}
    for c in config.COUNTRY_LABELS:
        sal[c] = {}
        for r in ROLES:
            vals = [float(p["salary_annual"]) for p in postings
                    if p["country"] == c and p["role"] == r and p.get("salary_annual")
                    and (_d(p["first_seen"]) or date.min) >= today - timedelta(days=180)]
            sal[c][r] = _quantiles(vals)
    hourly = [float(p["salary_hourly"]) for p in postings
              if p["country"] == "nl" and p.get("salary_hourly")]
    out["salaris"] = {"jaar": sal, "uurtarief_nl": _quantiles(hourly),
                      "valuta": config.CURRENCY}

    # ---- Werkvorm & senioriteit -----------------------------------------
    wm, sen = {}, {}
    for c in config.COUNTRY_LABELS:
        rows = [p for p in recent if p["country"] == c]
        known = [p for p in rows if p["work_mode"] != "onbekend"]
        wm[c] = {"n": len(known), "aandeel": {k: _pct(v, len(known)) for k, v in Counter(p["work_mode"] for p in known).items()}}
        sen[c] = {}
        for r in ROLES:
            sub = [p for p in rows if p["role"] == r and p["seniority"] != "onbekend"]
            sen[c][r] = {"n": len(sub), "aandeel": {k: _pct(v, len(sub)) for k, v in Counter(p["seniority"] for p in sub).items()}}
    out["werkvorm"] = wm
    out["senioriteit"] = sen

    # ---- Top werkgevers NL ----------------------------------------------
    emp = Counter(p["company"] for p in recent if p["country"] == "nl" and p.get("company"))
    out["werkgevers_nl"] = [{"naam": k, "n": v} for k, v in emp.most_common(15)]

    # ---- Hacker News -----------------------------------------------------
    hn = store.read_csv("hn_monthly.csv")
    months = sorted({r["month"] for r in hn})
    totals = {r["month"]: int(r["total_posts"]) for r in hn}
    hn_role = defaultdict(dict)
    hn_skill = defaultdict(dict)
    for r in hn:
        share = _pct(int(r["n"]), totals.get(r["month"], 0))
        (hn_role if r["kind"] == "role" else hn_skill)[r["name"]][r["month"]] = share
    if months:
        last = months[-1]
        top_skills = sorted(hn_skill, key=lambda s: -hn_skill[s].get(last, 0))[:8]
    else:
        top_skills = []
    out["hn"] = {
        "maanden": months,
        "posts": [totals.get(m) for m in months],
        "rollen": {r: [hn_role.get(r, {}).get(m, 0) for m in months] for r in ROLES + ["_any_data_role"]},
        "skills": {s: [hn_skill[s].get(m, 0) for m in months] for s in top_skills},
    }

    # ---- CBS -----------------------------------------------------------
    out["cbs"] = store.read_csv("cbs_vacatures.csv")
    return out


PAGE = """<!doctype html>
<html lang="nl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
</head>
<body>
{body}
</body>
</html>
"""


def render_fragment(data: dict) -> str:
    html = TEMPLATE.read_text(encoding="utf-8")
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return html.replace("/*__DATA__*/null", payload)


def render(data: dict, out_dir: Path | None = None) -> Path:
    out_dir = out_dir or ROOT / "site"
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "index.html"
    target.write_text(PAGE.format(body=render_fragment(data)), encoding="utf-8")
    (out_dir / "data.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    # Ruwe CSV's meeleveren zodat je ze vanaf de site kunt downloaden
    for name in ("postings.csv", "counts.csv", "hn_monthly.csv", "indeed.csv", "cbs_vacatures.csv"):
        src = store.DATA_DIR / name
        if src.exists():
            (out_dir / name).write_bytes(src.read_bytes())
    return target
