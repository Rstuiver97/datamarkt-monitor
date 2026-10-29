"""Tests voor de collectors met nep-antwoorden (geen netwerk nodig)."""
from marktmonitor import classify, store
from marktmonitor.collectors import adzuna, ats, hn


class FakeHttp:
    def __init__(self, data):
        self.data = data
        self.calls = 0

    def get(self, url, params=None, expect_json=True):
        self.calls += 1
        return self.data


def test_adzuna_normalize_ignores_predicted_salary():
    job = {"id": 1, "title": "Data Engineer", "company": {"display_name": "A"},
           "location": {"display_name": "Utrecht"}, "redirect_url": "u",
           "created": "2026-10-01T10:00:00Z", "description": "Python",
           "salary_min": 50000, "salary_max": 60000, "salary_is_predicted": "1"}
    p = adzuna._normalize(job, "nl")
    assert p["salary"] is None and p["uid"] == "adzuna:nl:1"
    job["salary_is_predicted"] = "0"
    p = adzuna._normalize(job, "nl")
    assert p["salary"] == {"min": 50000.0, "max": 60000.0, "currency": "EUR", "period": "jaar"}
    assert classify.enrich(p)["salary_annual"] == 55000


def test_adzuna_skips_without_key(monkeypatch):
    monkeypatch.delenv("ADZUNA_APP_ID", raising=False)
    monkeypatch.delenv("ADZUNA_APP_KEY", raising=False)
    assert adzuna.collect("2026-10-29") == ([], [])


def test_lever_parsing():
    data = [{"id": "x1", "text": "Senior Data Engineer", "categories": {"location": "Amsterdam"},
             "hostedUrl": "h", "createdAt": 1767225600000, "descriptionPlain": "Spark and dbt",
             "lists": [{"text": "Requirements", "content": "<li>Python</li>"}],
             "workplaceType": "hybrid",
             "salaryRange": {"min": 70000, "max": 90000, "currency": "EUR", "interval": "per-year-salary"}}]
    jobs = list(ats._lever(FakeHttp(data), "acme"))
    assert jobs[0]["title"] == "Senior Data Engineer"
    assert jobs[0]["salary"]["period"] == "jaar"
    assert "Python" in jobs[0]["description"]


def test_greenhouse_missing_board_returns_none():
    assert ats._greenhouse(FakeHttp(None), "bestaatniet") is None


def test_hn_summary():
    comments = [
        "Acme | Senior Data Engineer | Remote (US) | We use Python, dbt and Snowflake to build things for customers.",
        "Foo Inc | ML Engineer, Data Scientist | NYC | LLM and RAG work with PyTorch for our product, onsite.",
        "Bar | Frontend Engineer | SF | React and TypeScript, nothing data related in this long post text.",
        "kort",
    ]
    rows = hn.summarize_thread("2026-10", "123", comments)
    get = {(r["kind"], r["name"]): r["n"] for r in rows}
    assert rows[0]["total_posts"] == 3
    assert get[("role", "data_engineer")] == 1
    assert get[("role", "ml_engineer")] == 1 and get[("role", "data_scientist")] == 1
    assert get[("role", "_any_data_role")] == 2
    assert get[("skill", "dbt")] == 1 and get[("skill", "LLM")] == 1


def test_upsert_postings(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DATA_DIR", tmp_path)
    p = classify.enrich({"uid": "a:1", "source": "a", "country": "nl", "company": "X",
                         "title": "Data Engineer", "description": "Python"})
    assert store.upsert_postings([p], "2026-10-01") == (1, 0)
    assert store.upsert_postings([p], "2026-10-02") == (0, 1)
    row = store.read_csv("postings.csv")[0]
    assert row["first_seen"] == "2026-10-01" and row["last_seen"] == "2026-10-02"
    assert row["skills"] == "Python"
