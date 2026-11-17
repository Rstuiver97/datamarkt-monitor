"""AI-blootstelling van de Nederlandse arbeidsmarkt.

Combineert de lijst AI-gevoelige beroepsgroepen (Groenewegen et al.) met de
CBS Enquête Beroepsbevolking en Eurostat. Alle teksten in `bevindingen`
worden uit de cijfers afgeleid, zodat ze bij elke nieuwe CBS-publicatie
automatisch meebewegen.

Let op: dit beschrijft samenhang in de tijd, geen oorzaak. Werkgelegenheid
in een beroep hangt ook af van conjunctuur, vergrijzing en beleid.
"""
from __future__ import annotations

import re
from collections import defaultdict

from . import config, store

_AGE_RX = re.compile(r"(\d+)\s*tot\s*(\d+)\s*jaar")


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def match_group(name: str) -> str | None:
    """Welke appendixgroep hoort bij deze CBS-beroepsnaam (of None)."""
    n = _norm(name).rstrip(".… ")
    if len(n) < 6:
        return None
    for g in config.AI_GROUPS:
        for alias in config.AI_GROUP_CBS.get(g, [g]):
            a = _norm(alias)
            if n == a or (len(n) >= 18 and (a.startswith(n) or n.startswith(a))):
                return g
    return None


def _num(v) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def cagr(a: float | None, b: float | None, years: int) -> float | None:
    if not a or not b or years <= 0 or a <= 0 or b <= 0:
        return None
    return round(((b / a) ** (1 / years) - 1) * 100, 1)


def pct(a: float | None, b: float | None) -> float | None:
    if a is None or b is None or not b:
        return None
    return round(100 * a / b, 1)


def change(a: float | None, b: float | None) -> float | None:
    if not a or b is None:
        return None
    return round(100 * (b / a - 1), 1)


def _fmt(x: float | None, sign: bool = True, dec: int = 1) -> str:
    if x is None:
        return "–"
    if round(x, dec) == 0:
        x = 0.0
    s = f"{x:+.{dec}f}" if sign and x != 0 else f"{x:.{dec}f}"
    return s.replace(".", ",")


def _q(q: str) -> str:
    """'2026Q3' -> 'K3 2026'."""
    m = re.fullmatch(r"(\d{4})Q(\d)", q or "")
    return f"K{m.group(2)} {m.group(1)}" if m else q


def _thousands(x: float | None) -> str:
    if x is None:
        return "–"
    v = x * 1000
    if v >= 1_000_000:
        return f"{v / 1_000_000:.2f} miljoen".replace(".", ",")
    return f"{round(v / 1000):,}".replace(",", ".") + ".000"


# --------------------------------------------------------------------------
def _load_cbs():
    rows = store.read_csv("cbs_beroepen_jaar.csv")
    q = store.read_csv("cbs_beroepen_kwartaal.csv")
    return rows, q


def _age_band(kenmerk: str) -> tuple[int, int] | None:
    m = _AGE_RX.search(kenmerk or "")
    return (int(m.group(1)), int(m.group(2))) if m else None


def build() -> dict:
    rows, qrows = _load_cbs()
    versions = store.read_json("meta/versions.json")
    out: dict = {"beschikbaar": False, "bron_lijst": config.AI_SOURCE}
    if not rows:
        out["europa"] = _europe()
        return out

    # waarde[kenmerk][beroepnaam][jaar]
    val: dict = defaultdict(lambda: defaultdict(dict))
    codes: dict[str, str] = {}
    kgroups: dict[str, str] = {}
    for r in rows:
        v = _num(r["waarde"])
        if v is None:
            continue
        name = r["beroep"] or "Totaal"
        val[r["kenmerk"]][name][int(r["jaar"])] = v
        codes[name] = r["beroep_code"]
        kgroups[r["kenmerk"]] = r["kenmerk_groep"]

    totaal_kenmerk = next((k for k in val if _norm(k).startswith("totaal")), None) or next(iter(val))
    tot = val[totaal_kenmerk]
    total_name = next((n for n in tot if _norm(n).startswith("totaal") and not codes.get(n)), None)
    if not total_name:
        return out
    years = sorted(tot[total_name])
    last = years[-1]
    base = config.AI_BASE_YEAR if config.AI_BASE_YEAR in years else years[0]
    brk = config.AI_BREAK_YEAR if config.AI_BREAK_YEAR in years else years[len(years) // 2]

    group_names: dict[str, list[str]] = {}
    for name in tot:
        g = match_group(name)
        if g and len(codes.get(name, "")) == 4:
            group_names.setdefault(g, []).append(name)
    exposed_names = [n for ns in group_names.values() for n in ns]

    def series(kenmerk: str, names: list[str]) -> list[float | None]:
        d = val.get(kenmerk, {})
        res = []
        for y in years:
            vals = [d.get(n, {}).get(y) for n in names]
            res.append(round(sum(v for v in vals if v is not None), 1) if any(v is not None for v in vals) else None)
        return res

    s_tot = [tot[total_name].get(y) for y in years]
    s_exp = series(totaal_kenmerk, exposed_names)
    s_rest = [round(t - e, 1) if t is not None and e is not None else None for t, e in zip(s_tot, s_exp)]
    yi = {y: i for i, y in enumerate(years)}

    def at(s, y):
        return s[yi[y]] if y in yi else None

    # ---- kenmerken herkennen -------------------------------------------
    ages = sorted(((b, k) for k in val if (b := _age_band(k))), key=lambda x: x[0])
    young_k = [k for (a, b), k in ages if a < 25]
    edu_high = [k for k in val if re.match(r"^\s*3\b", k) or "hbo" in _norm(k)]
    self_emp = [k for k in val if "zelfstandig" in _norm(k)]

    def share(kenmerken: list[str], names: list[str], y: int) -> float | None:
        if not kenmerken:
            return None
        num = sum((at(series(k, names), y) or 0) for k in kenmerken)
        den = at(series(totaal_kenmerk, names), y)
        return pct(num, den)

    # ---- per groep ---------------------------------------------------------
    groepen = []
    for g, subs in config.AI_GROUPS.items():
        names = group_names.get(g)
        if not names:
            groepen.append({"naam": g, "gevonden": False, "beroepen": subs})
            continue
        s = series(totaal_kenmerk, names)
        groepen.append({
            "naam": g, "gevonden": True, "code": " + ".join(codes.get(n, "") for n in names),
            "cbs_namen": [f"{codes.get(n, '')} {n}" for n in names],
            "data_relevant": g in config.AI_GROUPS_DATA, "beroepen": subs,
            "reeks": s, "laatste": at(s, last),
            "aandeel_werkenden": pct(at(s, last), at(s_tot, last)),
            "groei_voor": cagr(at(s, base), at(s, brk), brk - base),
            "groei_na": cagr(at(s, brk), at(s, last), last - brk),
            "verandering_na": change(at(s, brk), at(s, last)),
            "aandeel_jong": share(young_k, names, last),
            "aandeel_jong_break": share(young_k, names, brk),
            "aandeel_hoog": share(edu_high, names, last),
            "aandeel_zelfstandig": share(self_emp, names, last),
        })

    # ---- jongeren ------------------------------------------------------------
    rest_names = [n for n in tot if n != total_name and len(codes.get(n, "")) == 4 and n not in exposed_names]
    jong = {}
    for (a, b), k in ages:
        e = series(k, exposed_names)
        t_all = series(k, [total_name])
        r = [round(x - y, 1) if x is not None and y is not None else None for x, y in zip(t_all, e)]
        jong[k] = {"band": [a, b], "blootgesteld": e, "overig": r}

    # ---- kwartalen -------------------------------------------------------
    qv: dict = defaultdict(dict)
    for r in qrows:
        v = _num(r["waarde"])
        if v is not None:
            qv[r["beroep"] or "Totaal"][r["kwartaal"]] = v
    quarters = sorted(qv.get(total_name, {}))
    q_tot = [qv[total_name].get(q) for q in quarters]
    q_exp = []
    for q in quarters:
        vals = [qv.get(n, {}).get(q) for n in exposed_names]
        q_exp.append(round(sum(v for v in vals if v is not None), 1) if any(v is not None for v in vals) else None)
    q_rest = [round(t - e, 1) if t is not None and e is not None else None for t, e in zip(q_tot, q_exp)]
    def qsum(names, q):
        vals = [qv.get(n, {}).get(q) for n in names]
        return round(sum(v for v in vals if v is not None), 1) if any(v is not None for v in vals) else None
    q_groups = {g: [qsum(ns, q) for q in quarters] for g, ns in group_names.items()}

    def roll4(s, i):
        w = s[i - 3:i + 1] if i >= 3 else []
        return sum(w) / 4 if len(w) == 4 and all(x is not None for x in w) else None

    q_yoy = {}
    if len(quarters) >= 8:
        i = len(quarters) - 1
        q_yoy = {
            "periode": f"{quarters[i - 3]}–{quarters[i]}",
            "periode_tekst": f"{_q(quarters[i - 3])} tot en met {_q(quarters[i])}",
            "blootgesteld": change(roll4(q_exp, i - 4), roll4(q_exp, i)),
            "overig": change(roll4(q_rest, i - 4), roll4(q_rest, i)),
        }

    out.update({
        "beschikbaar": True,
        "tabel": versions.get("cbs_beroepen_tabel", ""),
        "tabel_titel": versions.get("cbs_beroepen_titel", ""),
        "jaren": years, "laatste_jaar": last, "basisjaar": base, "breukjaar": brk,
        "totaal": s_tot, "blootgesteld": s_exp, "overig": s_rest,
        "aandeel": pct(at(s_exp, last), at(s_tot, last)),
        "aandeel_break": pct(at(s_exp, brk), at(s_tot, brk)),
        "groei": {
            "blootgesteld_voor": cagr(at(s_exp, base), at(s_exp, brk), brk - base),
            "blootgesteld_na": cagr(at(s_exp, brk), at(s_exp, last), last - brk),
            "overig_voor": cagr(at(s_rest, base), at(s_rest, brk), brk - base),
            "overig_na": cagr(at(s_rest, brk), at(s_rest, last), last - brk),
        },
        "groepen": groepen,
        "jongeren": jong,
        "jong_aandeel": {
            "blootgesteld": [share(young_k, exposed_names, y) for y in years],
            "overig": [share(young_k, rest_names, y) for y in years],
        },
        "hoog_aandeel": {
            "blootgesteld": share(edu_high, exposed_names, last),
            "overig": share(edu_high, rest_names, last),
        },
        "kwartaal": {"kwartalen": quarters, "blootgesteld": q_exp, "overig": q_rest,
                     "groepen": q_groups, "yoy": q_yoy},
        "kenmerken": {"leeftijd": [k for _, k in ages], "jong": young_k,
                      "hoog": edu_high, "zelfstandig": self_emp},
    })
    out["europa"] = _europe()
    out["bevindingen"] = findings(out)
    return out


# --------------------------------------------------------------------------
def _europe() -> dict:
    rows = store.read_csv("eurostat_isco.csv")
    ict = store.read_csv("eurostat_ict.csv")
    res: dict = {"beschikbaar": bool(rows or ict), "landen": config.EUROSTAT_GEO,
                 "isco": config.EUROSTAT_ISCO}
    if rows:
        d: dict = defaultdict(lambda: defaultdict(dict))
        for r in rows:
            v = _num(r["waarde"])
            if v is not None:
                d[r["land"]][r["isco"]][int(r["jaar"])] = v
        years = sorted({int(r["jaar"]) for r in rows})
        res["jaren"] = years
        # aandeel van totale werkgelegenheid per ISCO-groep
        res["aandeel"] = {
            geo: {c: [pct(d[geo][c].get(y), d[geo]["TOTAL"].get(y)) for y in years]
                  for c in config.EUROSTAT_ISCO}
            for geo in d if "TOTAL" in d[geo]
        }
        res["niveau"] = {geo: {c: [d[geo][c].get(y) for y in years] for c in list(config.EUROSTAT_ISCO) + ["TOTAL"]}
                         for geo in d}
    if ict:
        units = {r["eenheid"] for r in ict}
        unit = "PC_EMP" if "PC_EMP" in units else sorted(units)[0]
        yrs = sorted({int(r["jaar"]) for r in ict if r["eenheid"] == unit})
        dd: dict = defaultdict(dict)
        for r in ict:
            if r["eenheid"] == unit and _num(r["waarde"]) is not None:
                dd[r["land"]][int(r["jaar"])] = _num(r["waarde"])
        res["ict"] = {"jaren": yrs, "eenheid": unit, "reeks": {g: [dd[g].get(y) for y in yrs] for g in dd}}
    return res


def findings(a: dict) -> list[dict]:
    """Automatisch gegenereerde kernbevindingen (titel + tekst)."""
    f = []
    last, brk, base = a["laatste_jaar"], a["breukjaar"], a["basisjaar"]
    i_last = a["jaren"].index(last)
    g = a["groei"]
    f.append({
        "titel": f"{_fmt(a['aandeel'], sign=False)}% van de werkenden zit in een AI-gevoelig beroep",
        "tekst": (f"In {last} werkten {_thousands(a['blootgesteld'][i_last])} mensen in de "
                  f"{sum(1 for x in a['groepen'] if x['gevonden'])} beroepsgroepen die sterk in aanmerking komen voor AI, "
                  f"van in totaal {_thousands(a['totaal'][i_last])} werkenden."),
    })
    if None not in (g["blootgesteld_voor"], g["blootgesteld_na"], g["overig_voor"], g["overig_na"]):
        d_exp = g["blootgesteld_na"] - g["blootgesteld_voor"]
        d_rest = g["overig_na"] - g["overig_voor"]
        verschil = d_exp - d_rest
        if verschil > 0.3:
            titel = f"AI-gevoelige beroepen doen het sinds {brk} beter dan de rest"
        elif verschil < -0.3:
            titel = f"AI-gevoelige beroepen blijven sinds {brk} achter bij de rest"
        else:
            titel = f"Sinds {brk} geen duidelijk verschil met de rest van de arbeidsmarkt"
        f.append({
            "titel": titel,
            "tekst": (f"Van {base} tot {brk} groeiden deze beroepen met {_fmt(g['blootgesteld_voor'])}% per jaar, "
                      f"van {brk} tot {last} met {_fmt(g['blootgesteld_na'])}% per jaar. In de overige beroepen ging dat van "
                      f"{_fmt(g['overig_voor'])}% naar {_fmt(g['overig_na'])}% per jaar."),
        })
    found = [x for x in a["groepen"] if x["gevonden"] and x.get("groei_na") is not None and x.get("groei_voor") is not None]
    if found:
        for x in found:
            x["_delta"] = x["groei_na"] - x["groei_voor"]
        worst = sorted(found, key=lambda x: x["_delta"])[:3]
        best = sorted(found, key=lambda x: -x["_delta"])[:2]
        f.append({
            "titel": "Grootste omslag: " + ", ".join(w["naam"].lower() for w in worst[:2]),
            "tekst": ("Vergeleken met hun eigen trend vóór 2022 zakte de jaarlijkse groei het sterkst bij "
                      + "; ".join(f"{w['naam'].lower()} ({_fmt(w['groei_voor'])}% → {_fmt(w['groei_na'])}%)" for w in worst)
                      + ". "
                      + (f"Alle {len(found)} groepen groeien langzamer dan vóór {brk}; het minst vertraagd: "
                         if all(x["_delta"] < 0 for x in found) else "Versneld: ")
                      + "; ".join(f"{b['naam'].lower()} ({_fmt(b['groei_voor'])}% → {_fmt(b['groei_na'])}%)" for b in best) + "."),
        })
        for x in found:
            x.pop("_delta", None)
    ja = a.get("jong_aandeel") or {}
    jb, jo = ja.get("blootgesteld") or [], ja.get("overig") or []
    i_brk = a["jaren"].index(brk)
    if jb and jb[i_last] is not None and jb[i_brk] is not None and jo[i_last] is not None and jo[i_brk] is not None:
        db, do = jb[i_last] - jb[i_brk], jo[i_last] - jo[i_brk]
        f.append({
            "titel": ("Jongeren: " + ("minder" if db < do - 0.3 else "meer" if db > do + 0.3 else "geen opvallend verschil in")
                      + (" instroom in AI-gevoelige beroepen" if abs(db - do) > 0.3 else " instroom")),
            "tekst": (f"Het aandeel jongeren (tot 25 jaar) in AI-gevoelige beroepen ging van {_fmt(jb[i_brk], False)}% in {brk} "
                      f"naar {_fmt(jb[i_last], False)}% in {last}. In de overige beroepen van {_fmt(jo[i_brk], False)}% naar "
                      f"{_fmt(jo[i_last], False)}%. Jongeren doen vaak het instapwerk dat AI het eerst raakt; "
                      "in de VS is daar al een daling gemeten."),
        })
    data = [x for x in a["groepen"] if x.get("data_relevant") and x["gevonden"]]
    if data:
        f.append({
            "titel": "De beroepen achter datarollen groeien nog",
            "tekst": ("Datarollen vallen grotendeels onder " + ", ".join(d["naam"].lower() for d in data) + ". "
                      + " ".join(f"{d['naam']}: {_fmt(d['groei_voor'])}% per jaar vóór {brk}, {_fmt(d['groei_na'])}% erna."
                                 for d in data)),
        })
        if all((d.get("groei_na") or 0) <= 0 for d in data):
            f[-1]["titel"] = "De beroepen achter datarollen groeien niet meer"
        elif all((d.get("groei_na") or 0) < (d.get("groei_voor") or 0) - 1.5 for d in data):
            f[-1]["titel"] = "De beroepen achter datarollen groeien nog, maar veel langzamer"
    q = (a.get("kwartaal") or {}).get("yoy") or {}
    if q.get("blootgesteld") is not None:
        b = q["blootgesteld"]
        f.append({
            "titel": "Meest recent: " + ("krimp" if b < 0 else "groei") + " in AI-gevoelige beroepen",
            "tekst": (f"Gemiddeld over {q.get('periode_tekst', q['periode'])} werkten er {_fmt(abs(b), sign=False)}% "
                      + ("minder" if b < 0 else "meer")
                      + f" mensen in AI-gevoelige beroepen dan een jaar eerder. "
                      f"In de overige beroepen was dat {_fmt(q['overig'])}%."),
        })
    return f
