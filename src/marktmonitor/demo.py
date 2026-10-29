"""Synthetische demo-data, zodat je het dashboard kunt bekijken zonder API-keys.

De cijfers zijn VERZONNEN en dienen alleen om de opmaak te tonen. Gebruik
altijd een aparte map via MARKTMONITOR_DATA, zodat je echte data niet
vermengd raakt.
"""
from __future__ import annotations

import random
from datetime import date, timedelta

from . import classify, config, store

TITLES = {
    "data_engineer": ["Data Engineer", "Senior Data Engineer", "Medior Data Engineer", "Big Data Engineer", "Junior Data Engineer", "Lead Data Engineer"],
    "analytics_engineer": ["Analytics Engineer", "Senior Analytics Engineer", "Analytics Engineer (dbt)"],
    "ml_engineer": ["Machine Learning Engineer", "Senior ML Engineer", "AI Engineer", "MLOps Engineer", "GenAI Engineer"],
    "data_scientist": ["Data Scientist", "Senior Data Scientist", "Junior Data Scientist", "Lead Data Scientist"],
    "data_analyst": ["Data Analist", "Data Analyst", "Senior Data Analyst", "Marketing Data Analist", "Product Analyst"],
    "bi_consultant": ["BI Consultant", "Power BI Developer", "Senior BI Developer", "Business Intelligence Specialist"],
}
SKILLS_BY_ROLE = {
    "data_engineer": {"Python": .8, "SQL": .85, "Azure": .5, "AWS": .35, "Databricks": .4, "Spark": .45, "Airflow": .3, "dbt": .25, "Kafka": .2, "Terraform": .2, "Docker": .3, "Snowflake": .2, "Microsoft Fabric": .12},
    "analytics_engineer": {"SQL": .95, "dbt": .85, "Python": .5, "Snowflake": .4, "BigQuery": .3, "Looker": .2, "Power BI": .3, "Git": .5, "Airflow": .2, "Kimball/dimensioneel": .35},
    "ml_engineer": {"Python": .95, "PyTorch": .5, "Docker": .5, "Kubernetes": .4, "MLflow": .3, "AWS": .4, "Azure": .35, "LLM": .45, "RAG": .3, "LangChain/LlamaIndex": .2, "AI agents": .2, "GenAI": .35},
    "data_scientist": {"Python": .9, "SQL": .7, "Statistiek": .6, "scikit-learn": .4, "R": .25, "XGBoost/LightGBM": .2, "LLM": .25, "Azure": .3, "Databricks": .25, "GenAI": .2},
    "data_analyst": {"SQL": .85, "Power BI": .55, "Python": .4, "Tableau": .2, "Statistiek": .2, "DAX": .2, "Looker": .1},
    "bi_consultant": {"Power BI": .85, "DAX": .5, "SQL": .8, "Azure": .4, "SSIS/SSAS": .2, "Microsoft Fabric": .25, "Kimball/dimensioneel": .3, "Tableau": .15, "Qlik": .1},
}
VOLUME = {"nl": {"data_engineer": 9, "analytics_engineer": 2, "ml_engineer": 4, "data_scientist": 4, "data_analyst": 8, "bi_consultant": 6},
          "us": {"data_engineer": 14, "analytics_engineer": 4, "ml_engineer": 12, "data_scientist": 8, "data_analyst": 12, "bi_consultant": 5}}
SALARY = {"nl": {"data_engineer": 66000, "analytics_engineer": 62000, "ml_engineer": 72000, "data_scientist": 65000, "data_analyst": 50000, "bi_consultant": 55000},
          "us": {"data_engineer": 145000, "analytics_engineer": 135000, "ml_engineer": 175000, "data_scientist": 150000, "data_analyst": 95000, "bi_consultant": 110000}}
COMPANIES = {"nl": ["Voorbeeld Bank", "Demo Retail", "Fictief Energie", "Testverzekeraar", "Proef Consultancy", "Schijn Logistiek", "Nep Telecom", "Model Zorg"],
             "us": ["Example Corp", "Demo Inc", "Sample Labs", "Mock Analytics"]}
CITIES = {"nl": ["Amsterdam", "Utrecht", "Rotterdam", "Eindhoven", "Den Haag"], "us": ["New York, NY", "Austin, TX", "Seattle, WA", "Remote (US)"]}


def generate(days: int = 180, seed: int = 7) -> None:
    rnd = random.Random(seed)
    today = date.today()
    rows, counts = [], []
    for c in ("nl", "us"):
        for role, per_week in VOLUME[c].items():
            for d in range(days):
                day = today - timedelta(days=days - d)
                trend = 1 + (0.6 if role in ("ml_engineer", "analytics_engineer") else 0.05) * d / days
                n = sum(1 for _ in range(int(per_week * trend * 2)) if rnd.random() < 1 / 7 * 0.5)
                for i in range(n):
                    title = rnd.choice(TITLES[role])
                    skills = sorted(s for s, p in SKILLS_BY_ROLE[role].items()
                                    if rnd.random() < p * (1.4 if c == "us" and config.SKILLS[s][0] == "GenAI" else 1)
                                    * (0.4 + 1.2 * d / days if config.SKILLS[s][0] == "GenAI" else 1))
                    sen = classify.classify_seniority(title)
                    mult = {"junior": .75, "senior": 1.2, "lead": 1.4}.get(sen, 1)
                    has_sal = rnd.random() < (0.45 if c == "nl" else 0.7)
                    company = rnd.choice(COMPANIES[c])
                    hourly = c == "nl" and rnd.random() < 0.08
                    rows.append({
                        "uid": f"demo:{c}:{role}:{d}:{i}", "source": "demo", "country": c,
                        "company": company, "title": title, "location": rnd.choice(CITIES[c]),
                        "url": "", "posted_at": day.isoformat(), "first_seen": day.isoformat(),
                        "last_seen": day.isoformat(), "role": role, "seniority": sen,
                        "work_mode": rnd.choices(["hybride", "remote", "op_kantoor", "onbekend"],
                                                 [.55, .1, .1, .25] if c == "nl" else [.35, .25, .2, .2])[0],
                        "skills": ";".join(skills),
                        "salary_annual": round(rnd.gauss(SALARY[c][role] * mult, SALARY[c][role] * .12)) if has_sal and not hourly else "",
                        "salary_hourly": round(rnd.gauss(95, 15)) if hourly else "",
                        "salary_currency": config.CURRENCY[c] if has_sal or hourly else "",
                        "dedup_key": f"{c}|{company}|{title}|{d}|{i}",
                    })
        for d in range(0, days, 1):
            day = (today - timedelta(days=days - d)).isoformat()
            for q, role in config.QUERY_ROLE.items():
                if q not in config.ADZUNA_QUERIES[c]:
                    continue
                base = VOLUME[c][role] * 60 / max(1, sum(1 for qq, rr in config.QUERY_ROLE.items() if rr == role))
                trend = 1 + (0.5 if role in ("ml_engineer", "analytics_engineer") else -0.05) * d / days
                counts.append({"date": day, "source": "adzuna", "country": c, "query": q,
                               "count": int(base * trend * rnd.uniform(.93, 1.07))})
    store.write_csv("postings.csv", rows, store.POSTING_FIELDS)
    store.write_csv("counts.csv", counts, store.COUNT_FIELDS)

    hn = []
    for k in range(24):
        y, m = divmod(today.year * 12 + today.month - 1 - (23 - k), 12)
        month = f"{y}-{m + 1:02d}"
        total = rnd.randint(320, 480)
        base = {"month": month, "thread_id": f"demo{k}", "total_posts": total}
        for role, share in {"data_engineer": .09, "ml_engineer": .07 + .06 * k / 23, "data_scientist": .05 - .015 * k / 23,
                            "data_analyst": .03, "analytics_engineer": .012 + .01 * k / 23, "bi_consultant": .005}.items():
            hn.append({**base, "kind": "role", "name": role, "n": int(total * share)})
        hn.append({**base, "kind": "role", "name": "_any_data_role", "n": int(total * .25)})
        for skill, (a, b) in {"Python": (.42, .45), "LLM": (.10, .30), "AWS": (.30, .27), "Kubernetes": (.20, .19),
                              "AI agents": (.01, .14), "PyTorch": (.08, .12), "Snowflake": (.05, .06), "dbt": (.03, .05)}.items():
            hn.append({**base, "kind": "skill", "name": skill, "n": int(total * (a + (b - a) * k / 23) * rnd.uniform(.9, 1.1))})
    store.write_csv("hn_monthly.csv", hn, store.HN_FIELDS)
