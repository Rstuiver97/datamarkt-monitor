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

# Volumes per rol: welke Adzuna-zoektermen tellen mee. Synoniemen die bij
# Adzuna dezelfde vacatures opleveren (data analist/data analyst) tellen één
# keer: per rol wordt per land het maximum van de alias-groep genomen.
VOLUME_QUERIES = {
    "data_engineer": [["data engineer"]],
    "analytics_engineer": [["analytics engineer"]],
    "ml_engineer": [["machine learning engineer"], ["ml engineer"], ["mlops"]],
    "data_scientist": [["data scientist"]],
    "data_analyst": [["data analyst", "data analist"]],
    "bi_consultant": [["business intelligence"], ["bi developer"], ["bi consultant"], ["power bi"]],
}
# 'AI engineer' als titelzoekterm is breed (ook software engineers met AI in de
# titel) en wordt daarom apart getoond.
AI_TERM_QUERY = "ai engineer"

# Valuta per land en wisselkoers naar EUR (grof, alleen voor vergelijking).
CURRENCY = {"nl": "EUR", "us": "USD"}
USD_TO_EUR = 0.92

COUNTRY_LABELS = {"nl": "Nederland", "us": "Verenigde Staten"}

# --------------------------------------------------------------------------
# AI-blootstelling (Groenewegen et al., online appendix)
# --------------------------------------------------------------------------
# Beroepsgroepen (BRC 2014) die sterk in aanmerking komen voor AI, met de
# onderliggende beroepen uit de appendix. De namen worden in de CBS-tabel
# gezocht op titel (zonder de viercijferige code), dus ze moeten de
# CBS-naam beginnen.
AI_SOURCE = "Groenewegen et al., online appendix: beroepsgroepen en beroepen die sterk in aanmerking komen voor AI"
AI_GROUPS = {
    "Accountants": ["Accountants"],
    "Adviseurs marketing, public relations en sales": [
        "Specialisten marketing, sales en public relations z.n.d.", "Specialisten public relations",
        "Specialisten reclame en marketing", "Vertegenwoordigers en accountmanagers industrie",
        "Vertegenwoordigers informatie- en communicatietechnologie"],
    "Auteurs en taalkundigen": [
        "Auteurs, journalisten en taalkundigen z.n.d.", "Auteurs, technisch schrijvers",
        "Vertalers, tolken en andere taalkundigen"],
    "Bibliothecarissen en conservators": [
        "Archivarissen en conservators", "Bibliothecarissen",
        "Bibliothecarissen, archivarissen en conservators z.n.d."],
    "Boekhouders": [
        "Actuarieel, wiskundig en statistisch analisten",
        "Boekhouders, financieel administrateurs en assistent-accountants",
        "Effecten- en valutahandelaren en -makelaars", "Financieel en wiskundig vakspecialisten z.n.d.",
        "Medewerkers kredieten en leningen", "Taxateurs en schade-experts"],
    "Boekhoudkundig medewerkers": [
        "Administratief medewerkers statistiek, financiën en verzekeringen",
        "Boekhoudkundig medewerkers", "Boekhoudkundig medewerkers z.n.d.", "Loonadministrateurs"],
    "Databank- en netwerkspecialisten": [
        "Databank- en netwerkspecialisten n.e.g.", "Databank- en netwerkspecialisten z.n.d.",
        "Econometrist", "Ontwerpers en beheerders van databases"],
    "Financieel specialisten en economen": [
        "Economen", "Financieel analisten", "Financieel en beleggingsadviseurs",
        "Financieel specialisten z.n.d."],
    "Journalisten": ["Journalisten"],
    "Receptionisten en telefonisten": [
        "Callcentermedewerkers inbound", "Hotelreceptionisten", "Informatieverstrekkers",
        "Interviewers voor enquêtes en marktonderzoek", "Klantenvoorlichters n.e.g.",
        "Klantvoorlichters z.n.d.", "Receptionisten, algemeen",
        "Reisconsulenten en reisbureaumedewerkers", "Telefonisten"],
    "Secretaresses": [
        "Medewerkers data-invoer", "Secretarieel medewerkers, algemeen",
        "Typisten en medewerkers data-invoer z.n.d.", "Typisten en tekstverwerkers"],
    "Software- en applicatieontwikkelaars": [
        "Applicatieprogrammeurs", "Software- en applicatieontwikkelaars en -analisten n.e.g.",
        "Software- en applicatieontwikkelaars en -analisten z.n.d.", "Softwareontwikkelaars",
        "Specialisten informatie- en communicatietechnologie z.n.d.",
        "Systeemanalisten en ICT-adviseurs", "Web- en multimediaontwikkelaars"],
}
# Namen in de CBS-tabel als die afwijken van de appendix. De nieuwe CBS-editie
# (BRC 2014, editie 2025) heeft een paar groepen hernoemd of opgesplitst.
# Elke appendixgroep mag naar meerdere CBS-groepen verwijzen; ze worden opgeteld.
AI_GROUP_CBS = {
    "Bibliothecarissen en conservators": ["Bibliothecarissen en conservatoren", "Bibliothecarissen en conservators"],
    "Boekhoudkundig medewerkers": ["Financieel administratief medewerkers", "Boekhoudkundig medewerkers"],
    "Databank- en netwerkspecialisten": ["Systeembeheerders en netwerkspecialisten", "Databank- en netwerkspecialisten"],
    "Receptionisten en telefonisten": ["Klantenservice medewerkers en receptionisten", "Receptionisten en telefonisten"],
    "Secretaresses": ["Secretarieel medewerkers", "Secretaresses"],
    "Software- en applicatieontwikkelaars": ["Software- en applicatieontwikkelaars", "Systeemanalisten en ICT-adviseurs"],
}
# Groepen waar de datarollen uit deze monitor grotendeels onder vallen.
AI_GROUPS_DATA = ["Databank- en netwerkspecialisten", "Software- en applicatieontwikkelaars",
                  "Financieel specialisten en economen"]
# Moment vanaf wanneer generatieve AI breed beschikbaar was (ChatGPT, nov 2022).
AI_BREAK_YEAR = 2022
AI_BASE_YEAR = 2015

# CBS-tabellen, in volgorde van voorkeur (nieuwste eerst).
CBS_BEROEP_TABLES = ["86320NED", "85276NED"]

# Eurostat: ISCO-08 hoofdgroepen (2-cijferig) waar de beroepen uit de
# appendix grotendeels onder vallen. Dit is een benadering: deze ISCO-groepen
# bevatten ook beroepen die niet in de appendix staan.
EUROSTAT_ISCO = {
    "OC24": "Specialisten bedrijfsvoering en administratie",
    "OC25": "Specialisten ICT",
    "OC26": "Juridische, sociale en culturele specialisten",
    "OC33": "Vakspecialisten bedrijfsvoering en administratie",
    "OC41": "Algemeen administratief en secretariaat",
    "OC42": "Klantenservice en receptie",
    "OC43": "Financieel en logistiek administratief",
}
EUROSTAT_GEO = {
    "NL": "Nederland", "EU27_2020": "EU-27", "DE": "Duitsland", "BE": "België",
    "FR": "Frankrijk", "DK": "Denemarken", "SE": "Zweden", "IE": "Ierland",
}
