"""Centrale configuratie: rollen, zoektermen en skills-taxonomie.

Pas dit bestand aan om rollen of skills toe te voegen. De regex-patronen
worden case-insensitive toegepast, tenzij anders vermeld.
"""

# --------------------------------------------------------------------------
# Rollen
# --------------------------------------------------------------------------
# Volgorde is belangrijk: de eerste rol die matcht op de titel wint.
# Specifieke rollen (analytics engineer, ML engineer) staan daarom vóór
# algemenere (data engineer, data analist).
ROLES = {
    "analytics_engineer": {
        "label": "Analytics engineer",
        "title_patterns": [
            r"\banalytics[\s-]*engineer",
            r"\bdbt[\s-]*(developer|engineer)",
        ],
    },
    "ml_engineer": {
        "label": "ML/AI engineer",
        "title_patterns": [
            r"\bmachine[\s-]*learning[\s-]*(engineer|ontwikkelaar|developer)",
            r"\bml[\s-]*(ops)?[\s-]*engineer",
            r"\bmlops\b",
            r"\b(ai|a\.i\.|genai|gen[\s-]ai|llm)[\s-]*(\/\s*ml[\s-]*)?(engineer|ontwikkelaar|developer)",
            r"\bdeep[\s-]*learning[\s-]*engineer",
            r"\bcomputer[\s-]*vision[\s-]*engineer",
            r"\bnlp[\s-]*engineer",
        ],
    },
    "data_scientist": {
        "label": "Data scientist",
        "title_patterns": [
            r"\bdata[\s-]*scien(tist|ce)",
            r"\b(applied|research)[\s-]*scientist\b",
            r"\bmachine[\s-]*learning[\s-]*scientist",
            r"\bdecision[\s-]*scientist",
        ],
    },
    "bi_consultant": {
        "label": "BI consultant/developer",
        "title_patterns": [
            r"\bbi[\s-]*(consultant|developer|ontwikkelaar|specialist|analist|analyst|engineer|architect|lead)",
            r"\bbusiness[\s-]*intelligence",
            r"\bpower[\s-]*bi\b",
            r"\btableau[\s-]*(developer|consultant)",
            r"\b(reporting|rapportage)[\s-]*(specialist|analist|analyst|developer|consultant)",
            r"\bqlik",
        ],
    },
    "data_engineer": {
        "label": "Data engineer",
        "title_patterns": [
            r"\b(big[\s-]*)?data[\s-]*(platform[\s-]*)?(engineer|ontwikkelaar|developer)",
            r"\b(etl|elt|dwh|datawarehouse|data[\s-]*warehouse)[\s-]*(developer|engineer|ontwikkelaar|specialist|consultant)",
            r"\bdata[\s-]*(integratie|integration)[\s-]*(specialist|developer|engineer)",
            r"\b(databricks|snowflake|spark)[\s-]*(engineer|developer)",
        ],
    },
    "data_analyst": {
        "label": "Data analist",
        "title_patterns": [
            r"\bdata[\s-]*(analist|analyst|analytics?)\b",
            r"\b(product|marketing|commercial|commerciële|pricing|growth|web|customer|klant|insights?)[\s-]*(data[\s-]*)?(analist|analyst)\b",
            r"\banalytics\b(?![\s-]*engineer)",
        ],
    },
}

# Titels die we altijd uitsluiten (vals-positieven).
EXCLUDE_TITLE_PATTERNS = [
    r"\bdata[\s-]*(entry|invoer|typist|invoerder)",
    r"\bdata[\s-]*(center|centre)",
    r"\bdatacenter",
    r"\bsales\b(?!.*\b(analyst|analist)\b)",
    r"\bverkoop",
    r"\brecruit",
    r"\bdocent|\bteacher|\blecturer|\bprofessor\b",
    r"\bphd\b|\bpromovend|\bpostdoc",
    r"\bfinancial[\s-]*advisor|\bbelastingadviseur",
]

# --------------------------------------------------------------------------
# Senioriteit (eerste match wint)
# --------------------------------------------------------------------------
SENIORITY = [
    ("stage", r"\b(stage|stagiair|intern(ship)?|werkstudent|working[\s-]*student|trainee)\b|afstudeer"),
    ("lead", r"\b(lead|principal|staff|head[\s-]*of|manager|chapter[\s-]*lead|teamlead|architect|director)\b"),
    ("senior", r"\b(senior|sr\.?|ervaren|experienced)\b"),
    ("junior", r"\b(junior|jr\.?|starter|graduate|entry[\s-]*level|young[\s-]*professional)\b"),
    ("medior", r"\b(medior|mid[\s-]*level|intermediate)\b"),
]

# --------------------------------------------------------------------------
# Werkvorm
# --------------------------------------------------------------------------
REMOTE_PATTERNS = {
    "remote": r"\b(fully[\s-]*remote|100%[\s-]*remote|remote[\s-]*first|volledig[\s-]*(op[\s-]*afstand|remote|thuis)|remote\b(?![\s-]*(possible|mogelijk|optie)))",
    "hybride": r"\b(hybrid|hybride|thuiswerk|deels[\s-]*thuis|remote[\s-]*(possible|mogelijk|optie)|\d[\s-]*dag(en)?[\s-]*(per[\s-]*week[\s-]*)?(op[\s-]*kantoor|thuis))",
    "op_kantoor": r"\b(on[\s-]*site|onsite|op[\s-]*kantoor|in[\s-]*office|op[\s-]*locatie)\b",
}

# --------------------------------------------------------------------------
# Skills-taxonomie: naam -> (categorie, regex)
# --------------------------------------------------------------------------
SKILLS = {
    # Talen
    "Python": ("Taal", r"\bpython\b"),
    "SQL": ("Taal", r"\b(t-?sql|pl/?sql|sql)\b"),
    "R": ("Taal", r"(?-i:(?:^|[\s,(/])R(?=[\s,)/.]|$))"),
    "Scala": ("Taal", r"\bscala\b"),
    "Java": ("Taal", r"\bjava\b(?!script)"),
    "DAX": ("Taal", r"\bdax\b"),
    # Cloud
    "Azure": ("Cloud", r"\bazure\b"),
    "AWS": ("Cloud", r"\b(aws|amazon[\s-]*web[\s-]*services)\b"),
    "GCP": ("Cloud", r"\b(gcp|google[\s-]*cloud)\b"),
    # Dataplatforms & opslag
    "Databricks": ("Platform", r"\bdatabricks\b"),
    "Snowflake": ("Platform", r"\bsnowflake\b"),
    "BigQuery": ("Platform", r"\bbig[\s-]*query\b"),
    "Redshift": ("Platform", r"\bredshift\b"),
    "Synapse": ("Platform", r"\bsynapse\b"),
    "Microsoft Fabric": ("Platform", r"\b(microsoft|ms)[\s-]*fabric\b|\bfabric[\s-]*(lakehouse|data|warehouse)\b|\bonelake\b"),
    "Delta Lake": ("Platform", r"\bdelta[\s-]*lake\b"),
    "Iceberg": ("Platform", r"\b(apache[\s-]*)?iceberg\b"),
    "DuckDB": ("Platform", r"\bduckdb\b"),
    "PostgreSQL": ("Database", r"\bpostgres(ql)?\b"),
    "SQL Server": ("Database", r"\b(ms[\s-]*)?sql[\s-]*server\b"),
    "Oracle": ("Database", r"\boracle\b"),
    "MongoDB": ("Database", r"\bmongo(db)?\b"),
    # Verwerking & orkestratie
    "Spark": ("Verwerking", r"\b(py)?spark\b"),
    "Kafka": ("Verwerking", r"\bkafka\b"),
    "Flink": ("Verwerking", r"\bflink\b"),
    "Airflow": ("Orkestratie", r"\bairflow\b"),
    "Dagster": ("Orkestratie", r"\bdagster\b"),
    "Prefect": ("Orkestratie", r"\bprefect\b"),
    "Azure Data Factory": ("Orkestratie", r"\b(azure[\s-]*)?data[\s-]*factory\b|\badf\b"),
    "dbt": ("Transformatie", r"\bdbt\b"),
    "Pandas": ("Transformatie", r"\bpandas\b"),
    "Polars": ("Transformatie", r"\bpolars\b"),
    "Data Vault": ("Modellering", r"\bdata[\s-]*vault\b"),
    "Kimball/dimensioneel": ("Modellering", r"\b(kimball|dimensional[\s-]*model|dimensionele?[\s-]*model|star[\s-]*schema|sterschema)"),
    # BI
    "Power BI": ("BI", r"\bpower[\s-]*bi\b"),
    "Tableau": ("BI", r"\btableau\b"),
    "Looker": ("BI", r"\blooker\b"),
    "Qlik": ("BI", r"\bqlik"),
    "SSIS/SSAS": ("BI", r"\bss(is|as|rs)\b"),
    # Machine learning
    "scikit-learn": ("ML", r"\b(scikit[\s-]*learn|sklearn)\b"),
    "PyTorch": ("ML", r"\bpytorch\b|\btorch\b"),
    "TensorFlow": ("ML", r"\btensor[\s-]*flow\b|\bkeras\b"),
    "XGBoost/LightGBM": ("ML", r"\b(xgboost|lightgbm|catboost)\b"),
    "MLflow": ("MLOps", r"\bmlflow\b"),
    "Kubeflow": ("MLOps", r"\bkubeflow\b"),
    "SageMaker": ("MLOps", r"\bsage[\s-]*maker\b"),
    "Vertex AI": ("MLOps", r"\bvertex[\s-]*ai\b"),
    "Azure ML": ("MLOps", r"\b(azure[\s-]*ml|azure[\s-]*machine[\s-]*learning)\b"),
    # Generatieve AI
    "LLM": ("GenAI", r"\b(llms?|large[\s-]*language[\s-]*models?)\b"),
    "GenAI": ("GenAI", r"\b(gen[\s-]*ai|generative[\s-]*ai|generatieve[\s-]*ai)\b"),
    "RAG": ("GenAI", r"\b(rag|retrieval[\s-]*augmented)\b"),
    "LangChain/LlamaIndex": ("GenAI", r"\b(langchain|langgraph|llama[\s-]*index)\b"),
    "Vector DB": ("GenAI", r"\b(vector[\s-]*(database|db|store)|pinecone|weaviate|qdrant|pgvector|chroma[\s-]*db)\b"),
    "AI agents": ("GenAI", r"\b(ai[\s-]*agents?|agentic|multi[\s-]*agent)\b"),
    "Hugging Face": ("GenAI", r"\bhugging[\s-]*face\b"),
    "OpenAI/Anthropic API": ("GenAI", r"\b(openai|anthropic|claude|gpt-?\d|azure[\s-]*openai)\b"),
    # Engineering
    "Docker": ("DevOps", r"\bdocker\b"),
    "Kubernetes": ("DevOps", r"\b(kubernetes|k8s|aks|eks|gke)\b"),
    "Terraform": ("DevOps", r"\bterraform\b"),
    "CI/CD": ("DevOps", r"\b(ci\s*/\s*cd|github[\s-]*actions|azure[\s-]*devops|gitlab[\s-]*ci)\b"),
    "Git": ("DevOps", r"\bgit\b"),
    # Overig
    "Statistiek": ("Methode", r"\b(statisti(cs|ek|cal|sche)|a/b[\s-]*test|experimentation|causal[\s-]*inference|bayes)"),
    "Data governance": ("Methode", r"\b(data[\s-]*governance|data[\s-]*quality|datakwaliteit|data[\s-]*catalog|data[\s-]*lineage|data[\s-]*contracts?)\b"),
    "Data mesh": ("Methode", r"\bdata[\s-]*mesh\b"),
}

# --------------------------------------------------------------------------
# Zoektermen voor Adzuna (titel-zoekopdrachten per land)
# --------------------------------------------------------------------------
ADZUNA_QUERIES = {
    "nl": [
        "data engineer", "analytics engineer", "machine learning engineer",
        "ml engineer", "ai engineer", "mlops", "data scientist",
        "data analist", "data analyst", "bi consultant", "bi developer",
        "business intelligence", "power bi",
    ],
    "us": [
        "data engineer", "analytics engineer", "machine learning engineer",
        "ml engineer", "ai engineer", "mlops", "data scientist",
        "data analyst", "bi developer", "business intelligence", "power bi",
    ],
}

# Welke Adzuna-zoekterm telt mee voor welke rol (voor volumegrafieken).
QUERY_ROLE = {
    "data engineer": "data_engineer",
    "analytics engineer": "analytics_engineer",
    "machine learning engineer": "ml_engineer",
    "ml engineer": "ml_engineer",
    "ai engineer": "ml_engineer",
    "mlops": "ml_engineer",
    "data scientist": "data_scientist",
    "data analist": "data_analyst",
    "data analyst": "data_analyst",
    "bi consultant": "bi_consultant",
    "bi developer": "bi_consultant",
    "business intelligence": "bi_consultant",
    "power bi": "bi_consultant",
}

# Valuta per land en wisselkoers naar EUR (grof, alleen voor vergelijking).
CURRENCY = {"nl": "EUR", "us": "USD"}
USD_TO_EUR = 0.92

COUNTRY_LABELS = {"nl": "Nederland", "us": "Verenigde Staten"}
