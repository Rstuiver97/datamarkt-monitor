"""Tests voor de CBS-, Eurostat- en AI-analysecode, met nagebootste API-antwoorden."""
import random

import pytest

from marktmonitor import analysis_ai, config, store
from marktmonitor.collectors import cbs_beroepen, eurostat

GROUPS = [
    ("T001", "Totaal", None),
    ("B04", "04 Bedrijfseconomische en administratieve beroepen", None),
    ("B0411", "0411 Accountants", None),
    ("B0412", "0412 Financieel specialisten en economen", None),
    ("B0421", "0421 Boekhouders", None),
    ("B0432", "0432 Secretaresses", None),
    ("B0433", "0433 Receptionisten en telefonisten", None),
    ("B0434", "0434 Boekhoudkundig medewerkers", None),
    ("B0511", "0511 Adviseurs marketing, public relations en sales", None),
    ("B0311", "0311 Bibliothecarissen en conservators", None),
    ("B0312", "0312 Auteurs en taalkundigen", None),
    ("B0313", "0313 Journalisten", None),
    ("B0811", "0811 Software- en applicatieontwikkelaars", None),
    ("B0812", "0812 Databank- en netwerkspecialisten", None),
    ("B1011", "1011 Artsen", None),
    ("B0111", "0111 Leraren basisonderwijs", None),
]
PK = [("P0", "Totaal personen", "1"), ("P1", "15 tot 25 jaar", "2"), ("P2", "25 tot 45 jaar", "2"),
      ("P3", "45 tot 75 jaar", "2"), ("P4", "1 Basisonderwijs, vmbo, mbo1", "3"),
      ("P5", "2 Havo, vwo, mbo2-4", "3"), ("P6", "3 Hbo, wo", "3"), ("P7", "Werknemer", "4"),
      ("P8", "Zelfstandige", "4")]
YEARS = list(range(2013, 2026))


def _value(bkey, pkey, year):
    rnd = random.Random(f"{bkey}{pkey}{year}")
    base = {"T001": 9000, "B04": 1500, "B0811": 250, "B0812": 70, "B1011": 60, "B0111": 120}.get(bkey, 40)
    grow = 1 + (0.04 if bkey == "B0811" else 0.01) * (year - 2013)
    if bkey in ("B0432", "B0433") and year > 2022:
        grow *= 0.97 ** (year - 2022)
    frac = {"P0": 1, "P1": .12, "P2": .45, "P3": .43, "P4": .15, "P5": .4, "P6": .45, "P7": .85, "P8": .15}[pkey]
    return round(base * grow * frac * rnd.uniform(.98, 1.02))


class FakeCBS:
    """Bootst de CBS OData v3 API na, inclusief $filter op dimensies en substringof."""

    def __init__(self, table="86320NED", modified="2026-10-30T02:00:00"):
        self.table, self.modified, self.calls = table, modified, []

    def get(self, url, params=None, expect_json=True):
        self.calls.append((url, params))
        tail = url.rsplit("/", 1)[1]
        if tail == "TableInfos":
            return {"value": [{"Title": "Werkzame beroepsbevolking; beroep", "Modified": self.modified}]}
        if tail == "DataProperties":
            return {"value": [
                {"Type": "Dimension", "Key": "Geslacht"}, {"Type": "Dimension", "Key": "Persoonskenmerken"},
                {"Type": "Dimension", "Key": "Beroep"}, {"Type": "TimeDimension", "Key": "Perioden"},
                {"Type": "Topic", "Key": "WerkzameBeroepsbevolking_1", "Title": "Werkzame beroepsbevolking"}]}
        if tail == "Geslacht":
            return {"value": [{"Key": "T001038", "Title": "Totaal mannen en vrouwen"}, {"Key": "3000", "Title": "Mannen"}]}
        if tail == "Persoonskenmerken":
            return {"value": [{"Key": k, "Title": t, "CategoryGroupID": g} for k, t, g in PK]}
        if tail == "CategoryGroups":
            return {"value": [{"ID": "1", "Title": ""}, {"ID": "2", "Title": "Leeftijd"},
                              {"ID": "3", "Title": "Onderwijsniveau"}, {"ID": "4", "Title": "Positie in de werkkring"}]}
        if tail == "Beroep":
            return {"value": [{"Key": k + "  ", "Title": t} for k, t, _ in GROUPS]}
        if tail == "Perioden":
            return {"value": [{"Key": f"{y}JJ00"} for y in YEARS]}
        if tail == "TypedDataSet":
            f = params["$filter"]
            pk = next((k for k, *_ in PK if f"'{k}'" in f), "P0")
            if "'JJ'" in f:
                periods = [f"{y}JJ00" for y in YEARS]
            else:
                y = f.split("substringof('")[1][:4]
                periods = [f"{y}KW0{q}" for q in range(1, 5)] if int(y) <= 2026 else []
            return {"value": [
                {"Geslacht": "T001038", "Persoonskenmerken": pk, "Beroep": bk + "  ", "Perioden": p,
                 "WerkzameBeroepsbevolking_1": _value(bk, pk, int(p[:4]))}
                for bk, *_ in GROUPS for p in periods]}
        return None


@pytest.fixture
def data(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DATA_DIR", tmp_path)
    return tmp_path


def test_split_beroep():
    assert cbs_beroepen.split_beroep("0812 Databank- en netwerkspecialisten") == ("0812", "Databank- en netwerkspecialisten")
    assert cbs_beroepen.split_beroep("Totaal") == ("", "Totaal")


def test_cbs_collect_and_skip_when_unchanged(data, monkeypatch):
    fake = FakeCBS()
    monkeypatch.setattr(cbs_beroepen, "Http", lambda **kw: fake)
    assert cbs_beroepen.collect() == 1
    rows = store.read_csv("cbs_beroepen_jaar.csv")
    assert {r["kenmerk"] for r in rows} >= {"Totaal personen", "15 tot 25 jaar", "3 Hbo, wo"}
    db = [r for r in rows if r["beroep_code"] == "0812" and r["kenmerk"] == "Totaal personen"]
    assert len(db) == len(YEARS)
    assert any(r["kenmerk_groep"] == "Leeftijd" for r in rows)
    q = store.read_csv("cbs_beroepen_kwartaal.csv")
    assert any(r["kwartaal"] == "2026Q3" for r in q)
    assert (data / "meta" / "cbs_86320NED.json").exists()
    # tweede run zonder wijziging: niets ophalen
    n_calls = len(fake.calls)
    assert cbs_beroepen.collect() == 0
    assert not any("TypedDataSet" in u for u, _ in fake.calls[n_calls:])


def test_cbs_falls_back_to_old_table(data, monkeypatch):
    class Half(FakeCBS):
        def get(self, url, params=None, expect_json=True):
            if "86320NED" in url:
                return None
            return super().get(url, params, expect_json)
    fake = Half()
    monkeypatch.setattr(cbs_beroepen, "Http", lambda **kw: fake)
    assert cbs_beroepen.collect() == 1
    assert store.read_json("meta/versions.json")["cbs_beroepen_tabel"] == "85276NED"


def test_analysis(data, monkeypatch):
    monkeypatch.setattr(cbs_beroepen, "Http", lambda **kw: FakeCBS())
    cbs_beroepen.collect()
    a = analysis_ai.build()
    assert a["beschikbaar"] and a["laatste_jaar"] == 2025
    found = [g for g in a["groepen"] if g["gevonden"]]
    assert len(found) == len(config.AI_GROUPS)
    i = a["jaren"].index(2025)
    assert a["blootgesteld"][i] + a["overig"][i] == pytest.approx(a["totaal"][i], abs=0.5)
    assert 0 < a["aandeel"] < 100
    sw = next(g for g in found if g["naam"].startswith("Software"))
    assert sw["groei_voor"] > 2 and sw["data_relevant"]
    sec = next(g for g in found if g["naam"] == "Secretaresses")
    assert sec["groei_na"] < sec["groei_voor"]
    assert a["kenmerken"]["jong"] == ["15 tot 25 jaar"]
    assert a["hoog_aandeel"]["blootgesteld"] is not None
    assert a["kwartaal"]["yoy"]["periode"].endswith("2026Q4")
    titles = " ".join(f["titel"] for f in a["bevindingen"])
    assert "AI-gevoelig beroep" in titles and len(a["bevindingen"]) >= 5


def test_analysis_without_data(data):
    a = analysis_ai.build()
    assert a["beschikbaar"] is False


def test_jsonstat_decode():
    d = {"id": ["geo", "isco08", "time"], "size": [2, 2, 2],
         "dimension": {"geo": {"category": {"index": {"NL": 0, "EU27_2020": 1}}},
                       "isco08": {"category": {"index": {"OC25": 0, "TOTAL": 1}}},
                       "time": {"category": {"index": {"2023": 0, "2024": 1}}}},
         "value": {"0": 400, "1": 420, "3": 9800, "7": 216000}}
    rows = eurostat.decode_jsonstat(d)
    assert {"geo": "NL", "isco08": "OC25", "time": "2024", "value": 420} in rows
    assert {"geo": "EU27_2020", "isco08": "TOTAL", "time": "2024", "value": 216000} in rows
    assert len(rows) == 4


def test_eurostat_collect_weekly(data, monkeypatch):
    def payload(ds):
        if ds == "lfsa_egai2d":
            return {"id": ["age", "isco08", "geo", "time"], "size": [2, 2, 1, 1], "updated": "2026-05-01",
                    "dimension": {"age": {"category": {"index": {"Y15-64": 0, "Y15-74": 1}}},
                                  "isco08": {"category": {"index": {"OC25": 0, "TOTAL": 1}}},
                                  "geo": {"category": {"index": {"NL": 0}}},
                                  "time": {"category": {"index": {"2024": 0}}}},
                    "value": {"0": 1, "1": 2, "2": 450, "3": 9900}}
        return {"id": ["unit", "geo", "time"], "size": [1, 1, 1],
                "dimension": {"unit": {"category": {"index": {"PC_EMP": 0}}},
                              "geo": {"category": {"index": {"NL": 0}}},
                              "time": {"category": {"index": {"2024": 0}}}},
                "value": {"0": 6.6}}

    class F:
        calls = 0

        def get(self, url, params=None, expect_json=True):
            F.calls += 1
            return payload(url.rsplit("/", 1)[1])
    monkeypatch.setattr(eurostat, "Http", lambda **kw: F())
    assert eurostat.collect() == 3
    rows = store.read_csv("eurostat_isco.csv")
    assert {r["waarde"] for r in rows} == {"450", "9900"}  # leeftijd 15-74 gekozen
    assert eurostat.collect() == 0 and F.calls == 2   # binnen een week: overgeslagen
    e = analysis_ai._europe()
    assert e["aandeel"]["NL"]["OC25"] == [pytest.approx(4.5, abs=0.05)]
    assert e["ict"]["reeks"]["NL"] == [6.6]


def test_truncated_titles_and_renamed_groups():
    from marktmonitor.collectors.cbs_beroepen import split_beroep
    assert split_beroep("0433 Klantenservice medewerkers en re...",
                        "Klantenservice medewerkers en receptionisten: Deze beroepsgroep omvat ...") == \
        ("0433", "Klantenservice medewerkers en receptionisten")
    assert analysis_ai.match_group("Klantenservice medewerkers en receptionisten") == "Receptionisten en telefonisten"
    assert analysis_ai.match_group("Secretarieel medewerkers") == "Secretaresses"
    assert analysis_ai.match_group("Systeemanalisten en ICT-adviseurs") == "Software- en applicatieontwikkelaars"
    assert analysis_ai.match_group("Systeembeheerders en netwerkspecialisten") == "Databank- en netwerkspecialisten"
    assert analysis_ai.match_group("Administratief medewerkers") is None
    assert analysis_ai.match_group("Totaal") is None
