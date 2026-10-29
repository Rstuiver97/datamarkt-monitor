"""Verrijking van ruwe vacatures: rol, senioriteit, skills, werkvorm, land, salaris."""
from __future__ import annotations

import html
import re
import unicodedata

from . import config

_FLAGS = re.IGNORECASE

_ROLE_RX = {
    role: [re.compile(p, _FLAGS) for p in spec["title_patterns"]]
    for role, spec in config.ROLES.items()
}
_EXCLUDE_RX = [re.compile(p, _FLAGS) for p in config.EXCLUDE_TITLE_PATTERNS]
_SENIORITY_RX = [(name, re.compile(p, _FLAGS)) for name, p in config.SENIORITY]
_REMOTE_RX = {k: re.compile(p, _FLAGS) for k, p in config.REMOTE_PATTERNS.items()}
_SKILL_RX = {name: re.compile(p, _FLAGS) for name, (_cat, p) in config.SKILLS.items()}

ROLE_LABELS = {k: v["label"] for k, v in config.ROLES.items()}


# --------------------------------------------------------------------------
# Tekst
# --------------------------------------------------------------------------
_TAG_RX = re.compile(r"<[^>]+>")
_WS_RX = re.compile(r"\s+")


def clean_text(text: str | None) -> str:
    """HTML-tags en entities verwijderen, witruimte normaliseren."""
    if not text:
        return ""
    t = html.unescape(str(text))
    t = html.unescape(t)  # sommige feeds zijn dubbel ge-escaped
    t = _TAG_RX.sub(" ", t)
    t = unicodedata.normalize("NFKC", t)
    return _WS_RX.sub(" ", t).strip()


# --------------------------------------------------------------------------
# Rol
# --------------------------------------------------------------------------
def is_excluded(title: str) -> bool:
    return any(rx.search(title) for rx in _EXCLUDE_RX)


def classify_role(title: str | None) -> str | None:
    """Eén rol op basis van de functietitel (eerste match in ROLES-volgorde)."""
    title = clean_text(title)
    if not title or is_excluded(title):
        return None
    for role, patterns in _ROLE_RX.items():
        if any(rx.search(title) for rx in patterns):
            return role
    return None


def find_roles(text: str | None) -> list[str]:
    """Alle rollen die in een tekst genoemd worden (voor HN-posts met meerdere rollen)."""
    text = clean_text(text)
    if not text:
        return []
    return [role for role, pats in _ROLE_RX.items() if any(rx.search(text) for rx in pats)]


# --------------------------------------------------------------------------
# Senioriteit, werkvorm, skills
# --------------------------------------------------------------------------
def classify_seniority(title: str | None) -> str:
    title = clean_text(title)
    for name, rx in _SENIORITY_RX:
        if rx.search(title):
            return name
    return "onbekend"


def classify_work_mode(*texts: str | None, remote_flag: bool | None = None) -> str:
    joined = " ".join(clean_text(t) for t in texts if t)
    if _REMOTE_RX["hybride"].search(joined):
        return "hybride"
    if remote_flag or _REMOTE_RX["remote"].search(joined):
        return "remote"
    if _REMOTE_RX["op_kantoor"].search(joined):
        return "op_kantoor"
    return "onbekend"


def extract_skills(*texts: str | None) -> list[str]:
    joined = " ".join(clean_text(t) for t in texts if t)
    if not joined:
        return []
    return sorted(name for name, rx in _SKILL_RX.items() if rx.search(joined))


# --------------------------------------------------------------------------
# Land
# --------------------------------------------------------------------------
_NL_PLACES = (
    "netherlands|nederland|holland|amsterdam|rotterdam|utrecht|eindhoven|den haag|"
    "the hague|'s-gravenhage|delft|leiden|groningen|amersfoort|arnhem|nijmegen|haarlem|"
    "zwolle|breda|tilburg|'s-hertogenbosch|den bosch|maastricht|enschede|hilversum|"
    "schiphol|hoofddorp|almere|apeldoorn|leeuwarden|wageningen|amstelveen|zaandam|"
    "dordrecht|deventer|veenendaal|nieuwegein|houten|zeist|ede|alkmaar|venlo|helmond"
)
_NL_RX = re.compile(rf"(?<!\w)({_NL_PLACES})(?!\w)", _FLAGS)
_US_STATES = (
    "AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV "
    "NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC"
).split()


def detect_country(location: str | None) -> str | None:
    loc = clean_text(location)
    if not loc:
        return None
    if _NL_RX.search(loc):
        return "nl"
    # Staatafkortingen alleen hoofdlettergevoelig controleren
    if re.search(r",\s*(" + "|".join(_US_STATES) + r")\b", loc) or re.search(
        r"\b(united states|usa|new york|san francisco|seattle|boston|chicago|austin|los angeles|"
        r"denver|atlanta|bay area|silicon valley)\b|\bremote\s*[-(,]?\s*(us|usa)\b|\bU\.S\.",
        loc,
        re.IGNORECASE,
    ):
        return "us"
    return None


# --------------------------------------------------------------------------
# Salaris
# --------------------------------------------------------------------------
_NUM = r"\d{1,3}(?:[.,\s]\d{3})+(?:[.,]\d{1,2})?|\d+(?:[.,]\d+)?"
_CUR = r"€|eur(?:o|os)?\b|\$|usd\b"
_MONEY = rf"(?P<cur>{_CUR})\s*(?P<a>{_NUM})\s*(?P<ka>k\b)?"
_RANGE_RX = re.compile(
    _MONEY + rf"\s*(?:-|–|—|to|tot|t/m|en)\s*(?:{_CUR})?\s*(?P<b>{_NUM})\s*(?P<kb>k\b)?",
    _FLAGS,
)
_SINGLE_RX = re.compile(_MONEY, _FLAGS)
_PERIOD_RX = [
    ("uur", re.compile(r"(per|/|p\.?)\s*(uur|hour|hr|h)\b|\buurtarief|\bhourly|\b/u\b", _FLAGS)),
    ("maand", re.compile(r"(per|/|p\.?)\s*(maand|month|mnd|mo)\b|\bp\.?\s*m\.?\b|\bmonthly|\bmaandsalaris|\bbruto per maand", _FLAGS)),
    ("jaar", re.compile(r"(per|/|p\.?)\s*(jaar|year|yr|annum)\b|\bannual(ly)?\b|\bjaarsalaris|\bp\.?\s*j\.?\b|\bper annum|\bpa\b", _FLAGS)),
]


def _to_number(raw: str, k: bool) -> float | None:
    s = raw.strip().replace(" ", "")
    try:
        if re.fullmatch(r"\d{1,3}(?:[.,]\d{3})+", s):
            val = float(re.sub(r"[.,]", "", s))
        elif re.fullmatch(r"\d{1,3}(?:[.,]\d{3})+[.,]\d{1,2}", s):
            val = float(re.sub(r"[.,]", "", s[: -3 if s[-3] in ".," else -2]))
        else:
            val = float(s.replace(",", "."))
    except ValueError:
        return None
    return val * 1000 if k else val


def _guess_period(amount: float, currency: str) -> str:
    if amount < 300:
        return "uur"
    if currency == "EUR" and amount < 15000:
        return "maand"
    if currency == "USD" and amount < 15000:
        return "maand"
    return "jaar"


def parse_salary(text: str | None, default_currency: str | None = None) -> dict | None:
    """Zoek een salarisvermelding in vrije tekst.

    Geeft {min, max, currency, period} terug, of None. Periode: uur/maand/jaar.
    """
    t = clean_text(text)
    if not t:
        return None
    m = _RANGE_RX.search(t)
    if m:
        a = _to_number(m.group("a"), bool(m.group("ka")) or bool(m.group("kb")))
        b = _to_number(m.group("b"), bool(m.group("kb")))
        end = m.end()
    else:
        m = _SINGLE_RX.search(t)
        if not m:
            return None
        a = _to_number(m.group("a"), bool(m.group("ka")))
        b = a
        end = m.end()
    if a is None or b is None or a <= 0:
        return None
    lo, hi = sorted((a, b))
    cur_raw = m.group("cur").lower()
    currency = "USD" if cur_raw in ("$", "usd") else "EUR"
    window = t[max(0, m.start() - 40): end + 60]
    period = None
    for name, rx in _PERIOD_RX:
        if rx.search(window):
            period = name
            break
    if period is None:
        period = _guess_period(hi, currency)
    return {"min": lo, "max": hi, "currency": currency, "period": period}


def annual_salary(sal: dict | None) -> float | None:
    """Midpoint omgerekend naar bruto jaarsalaris (maand x 12), in eigen valuta.

    Uurtarieven (vaak freelance) geven None; die worden apart gerapporteerd.
    """
    if not sal or sal.get("period") == "uur":
        return None
    mid = (sal["min"] + sal["max"]) / 2
    if sal.get("period") == "maand":
        mid *= 12
    lo, hi = (15_000, 400_000) if sal.get("currency") == "EUR" else (20_000, 800_000)
    return round(mid) if lo <= mid <= hi else None


def hourly_rate(sal: dict | None) -> float | None:
    if not sal or sal.get("period") != "uur":
        return None
    mid = (sal["min"] + sal["max"]) / 2
    return round(mid, 2) if 10 <= mid <= 300 else None


# --------------------------------------------------------------------------
# Ontdubbeling
# --------------------------------------------------------------------------
_COMPANY_NOISE = re.compile(
    r"\b(b\.?v\.?|n\.?v\.?|inc\.?|llc|ltd\.?|gmbh|holding|group|groep|nederland|netherlands|the)\b",
    _FLAGS,
)


def _norm(s: str | None) -> str:
    s = clean_text(s).lower()
    s = _COMPANY_NOISE.sub(" ", s)
    s = re.sub(r"\(.*?\)", " ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return s.strip()


def dedup_key(company: str | None, title: str | None, country: str | None) -> str:
    """Zelfde bedrijf + (genormaliseerde) titel + land = dezelfde vacature."""
    t = _norm(title)
    t = re.sub(r"\b(m v x|m v|v m|f m d|m w d|hybrid|hybride|remote)\b", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return f"{country or '?'}|{_norm(company)}|{t}"


# --------------------------------------------------------------------------
# Alles in één keer
# --------------------------------------------------------------------------
def enrich(posting: dict) -> dict | None:
    """Verrijk een genormaliseerde posting. None als het geen data-rol is."""
    role = classify_role(posting.get("title"))
    if role is None:
        return None
    text = posting.get("description") or ""
    currency_default = config.CURRENCY.get(posting.get("country") or "", None)

    sal = posting.get("salary")  # gestructureerd salaris van de bron
    if not sal:
        sal = parse_salary(text, currency_default)

    out = dict(posting)
    out.update(
        role=role,
        seniority=classify_seniority(posting.get("title")),
        work_mode=classify_work_mode(
            posting.get("title"), posting.get("location"), text,
            remote_flag=posting.get("remote_flag"),
        ),
        skills=extract_skills(posting.get("title"), text),
        salary_annual=annual_salary(sal),
        salary_hourly=hourly_rate(sal),
        salary_currency=(sal or {}).get("currency"),
        dedup_key=dedup_key(posting.get("company"), posting.get("title"), posting.get("country")),
    )
    out.pop("salary", None)
    out.pop("remote_flag", None)
    out.pop("description", None)  # niet opslaan: scheelt ruimte en auteursrecht
    return out
