import pytest

from marktmonitor import classify as c


@pytest.mark.parametrize("title,role", [
    ("Data Engineer", "data_engineer"),
    ("Senior Data Engineer (m/v/x)", "data_engineer"),
    ("Medior Data-engineer Azure", "data_engineer"),
    ("Big Data Engineer", "data_engineer"),
    ("Data Platform Engineer", "data_engineer"),
    ("ETL Developer", "data_engineer"),
    ("DWH Ontwikkelaar", "data_engineer"),
    ("Databricks Engineer", "data_engineer"),
    ("Analytics Engineer", "analytics_engineer"),
    ("Senior Analytics Engineer - dbt", "analytics_engineer"),
    ("Machine Learning Engineer", "ml_engineer"),
    ("ML Engineer", "ml_engineer"),
    ("MLOps Engineer", "ml_engineer"),
    ("AI Engineer", "ml_engineer"),
    ("GenAI Engineer", "ml_engineer"),
    ("LLM Engineer", "ml_engineer"),
    ("Data Scientist", "data_scientist"),
    ("Junior Data Scientist", "data_scientist"),
    ("Applied Scientist", "data_scientist"),
    ("Data Analist", "data_analyst"),
    ("Data Analyst", "data_analyst"),
    ("Marketing Data Analist", "data_analyst"),
    ("Product Analyst", "data_analyst"),
    ("Head of Analytics", "data_analyst"),
    ("BI Consultant", "bi_consultant"),
    ("Power BI Developer", "bi_consultant"),
    ("Business Intelligence Specialist", "bi_consultant"),
    ("Senior BI Ontwikkelaar", "bi_consultant"),
    ("Rapportage specialist", "bi_consultant"),
])
def test_roles(title, role):
    assert c.classify_role(title) == role


@pytest.mark.parametrize("title", [
    "Data Entry Medewerker", "Datacenter Technicus", "Data Center Engineer",
    "Business Analyst", "Software Engineer", "Recruiter Data & Analytics",
    "Docent Data Science", "PhD candidate Machine Learning", "Accountmanager",
    "Sales Engineer", "Verkoopmedewerker", "Financial Analyst",
])
def test_non_roles(title):
    assert c.classify_role(title) is None


@pytest.mark.parametrize("title,sen", [
    ("Senior Data Engineer", "senior"), ("Sr. Data Scientist", "senior"),
    ("Junior Data Analist", "junior"), ("Medior BI Consultant", "medior"),
    ("Lead Data Engineer", "lead"), ("Principal ML Engineer", "lead"),
    ("Afstudeerstage Data Science", "stage"), ("Data Engineer", "onbekend"),
    ("Starter Data Analist", "junior"),
])
def test_seniority(title, sen):
    assert c.classify_seniority(title) == sen


def test_skills():
    text = ("Je werkt met Python, SQL en dbt op Snowflake. Ervaring met Airflow, "
            "Power BI en Azure Data Factory is een pré. Kennis van LLM's en RAG.")
    s = c.extract_skills(text)
    for k in ["Python", "SQL", "dbt", "Snowflake", "Airflow", "Power BI",
              "Azure", "Azure Data Factory", "RAG"]:
        assert k in s, k
    assert "Java" not in c.extract_skills("JavaScript developer")


def test_skill_r_case_sensitive():
    assert "R" in c.extract_skills("Experience with Python, R and SQL")
    assert "R" not in c.extract_skills("R&D department, our product")
    assert "R" not in c.extract_skills("je bent r eigenlijk goed in")


@pytest.mark.parametrize("text,exp", [
    ("Salaris € 4.500 - € 6.000 bruto per maand", (4500, 6000, "EUR", "maand")),
    ("€60k–€80k per year", (60000, 80000, "EUR", "jaar")),
    ("Jaarsalaris tussen €65.000 en €80.000", (65000, 80000, "EUR", "jaar")),
    ("$150,000 - $200,000 a year", (150000, 200000, "USD", "jaar")),
    ("Uurtarief € 85 - € 105 per uur", (85, 105, "EUR", "uur")),
    ("Salaris tot €5.200,- per maand", (5200, 5200, "EUR", "maand")),
    ("Salary: EUR 4,000 to 5,500", (4000, 5500, "EUR", "maand")),
])
def test_salary(text, exp):
    s = c.parse_salary(text)
    assert s is not None
    assert (s["min"], s["max"], s["currency"], s["period"]) == exp


def test_salary_annualize():
    assert c.annual_salary({"min": 4500, "max": 5500, "currency": "EUR", "period": "maand"}) == 60000
    assert c.annual_salary({"min": 85, "max": 105, "currency": "EUR", "period": "uur"}) is None
    assert c.hourly_rate({"min": 85, "max": 105, "currency": "EUR", "period": "uur"}) == 95
    assert c.annual_salary({"min": 5, "max": 6, "currency": "EUR", "period": "jaar"}) is None
    assert c.parse_salary("geen salaris genoemd") is None


@pytest.mark.parametrize("loc,cc", [
    ("Amsterdam, Netherlands", "nl"), ("Utrecht", "nl"), ("'s-Hertogenbosch", "nl"),
    ("Remote - Netherlands", "nl"), ("New York, NY", "us"), ("San Francisco, CA", "us"),
    ("Remote (US)", "us"), ("United States", "us"), ("Berlin, Germany", None),
    ("London, UK", None), ("Remote", None),
])
def test_country(loc, cc):
    assert c.detect_country(loc) == cc


def test_work_mode():
    assert c.classify_work_mode("Hybride: 2 dagen op kantoor") == "hybride"
    assert c.classify_work_mode("Fully remote within EU") == "remote"
    assert c.classify_work_mode("Remote mogelijk") == "hybride"
    assert c.classify_work_mode("Op kantoor in Utrecht") == "op_kantoor"
    assert c.classify_work_mode("") == "onbekend"


def test_dedup_key():
    a = c.dedup_key("Voorbeeld B.V.", "Senior Data Engineer (m/v/x)", "nl")
    b = c.dedup_key("Voorbeeld", "Senior Data Engineer", "nl")
    assert a == b


def test_enrich_drops_description_and_non_roles():
    p = {"uid": "x", "title": "Data Engineer", "country": "nl", "company": "A",
         "description": "Python, € 5.000 - € 6.000 per maand, hybride"}
    e = c.enrich(p)
    assert e["role"] == "data_engineer" and "description" not in e
    assert e["salary_annual"] == 66000 and e["work_mode"] == "hybride"
    assert c.enrich({"uid": "y", "title": "Accountmanager"}) is None
