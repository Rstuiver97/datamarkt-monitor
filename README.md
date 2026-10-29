# Datamarkt Monitor

Een geautomatiseerde, gratis monitor van de arbeidsmarkt voor **data engineers, analytics engineers, ML/AI engineers, data scientists, data analisten en BI consultants**, in Nederland en de Verenigde Staten.

Elke ochtend haalt GitHub Actions vacatures en marktcijfers op, classificeert ze, en publiceert een dashboard op GitHub Pages. Alle data wordt als CSV in de repository bewaard, zodat je een groeiende historie opbouwt die je ook in Excel of Power BI kunt openen.

## Wat je krijgt

- **Vraag per rol**: nieuwe vacatures per week en het totaal aantal actieve vacatures, per land.
- **Marktindex**: Indeed Job Postings Index voor Nederland, met Data & Analytics in de VS, Duitsland en het VK als referentie.
- **Skills**: welke tools en technieken per rol gevraagd worden, en een tabel met skills die in de VS al vaker gevraagd worden dan in Nederland.
- **Vroege signalen**: maandelijkse trend van rollen en tools in de Hacker News "Who is hiring?"-threads (VS-tech).
- **Beloning**: salarisbanden per rol (alleen uit vacatures die zelf een salaris noemen) en freelance-uurtarieven.
- **Werkvorm, senioriteit, top-werkgevers** en de CBS-vacaturecijfers voor de ICT-sector.

## Kosten

Nul euro, mits je een **openbare** GitHub-repository gebruikt:

| Onderdeel | Gratis omdat |
|---|---|
| GitHub Actions | Onbeperkte minuten voor openbare repositories |
| GitHub Pages | Gratis voor openbare repositories |
| Adzuna API | Gratis developer-account |
| Indeed, Hacker News, CBS, werkgeversfeeds | Openbare data, geen key nodig |

Met een privé-repository werkt de dataverzameling ook (2.000 gratis Actions-minuten per maand, een run duurt een paar minuten), maar GitHub Pages vereist dan een betaald abonnement. Download in dat geval de map `site/` via de workflow of draai het dashboard lokaal.

## Installatie (ongeveer 15 minuten)

1. **Adzuna-key aanvragen.** Maak een gratis account op [developer.adzuna.com](https://developer.adzuna.com/signup). Je krijgt een *Application ID* en een *Application Key*.
2. **Repository aanmaken.** Maak op GitHub een nieuwe, openbare repository (bijvoorbeeld `datamarkt-monitor`) en upload de inhoud van deze map. Via de website: *Add file → Upload files*, en sleep alle bestanden en mappen erin. Let op dat de verborgen map `.github` meekomt.
3. **Keys toevoegen.** Ga in de repository naar *Settings → Secrets and variables → Actions → New repository secret* en maak twee secrets aan: `ADZUNA_APP_ID` en `ADZUNA_APP_KEY`.
4. **Pages aanzetten.** Ga naar *Settings → Pages* en kies bij *Source* voor **GitHub Actions**.
5. **Eerste run starten.** Ga naar het tabblad *Actions*, kies *Datamarkt Monitor* en klik op *Run workflow*. Na een paar minuten staat je dashboard op `https://<jouw-gebruikersnaam>.github.io/datamarkt-monitor/`.

Daarna draait het elke ochtend vanzelf.

## Na de eerste run

**Werkgeverslijst controleren.** In `config/companies.json` staat een startlijst van werkgevers met een openbare vacaturefeed. Niet alle bedrijfs-ID's zijn gecontroleerd. Draai lokaal:

```bash
pip install -r requirements.txt
PYTHONPATH=src python -m marktmonitor validate-companies
```

Zet werkgevers met status `NIET GEVONDEN` op `"enabled": false` of verbeter de `slug`. Voeg vooral Nederlandse werkgevers toe die voor jou relevant zijn. De slug vind je in de URL van hun vacaturepagina, bijvoorbeeld `boards.greenhouse.io/adyen` → `greenhouse` / `adyen`, of `bedrijf.recruitee.com` → `recruitee` / `bedrijf`.

**Historie opbouwen.** Trends worden pas betekenisvol na een paar weken. De Indeed-index en Hacker News hebben direct historie (Indeed vanaf 2020, Hacker News 24 maanden terug bij de eerste run).

## Lokaal draaien

```bash
pip install -r requirements.txt
export ADZUNA_APP_ID=... ADZUNA_APP_KEY=...
PYTHONPATH=src python -m marktmonitor run            # alles ophalen + dashboard in site/
PYTHONPATH=src python -m marktmonitor collect hn     # één bron
PYTHONPATH=src python -m marktmonitor report         # alleen dashboard opnieuw bouwen
```

Dashboard bekijken zonder data of keys:

```bash
MARKTMONITOR_DATA=/tmp/demo/data PYTHONPATH=src python -m marktmonitor demo
# open /tmp/demo/site/index.html
```

De demo gebruikt **verzonnen** vacatures (met een duidelijke waarschuwing bovenaan) en de echte Indeed-index. Gebruik altijd een aparte map via `MARKTMONITOR_DATA`, zodat demodata niet in je echte data terechtkomt.

## Aanpassen

| Wat | Waar |
|---|---|
| Rollen en hoe titels worden herkend | `src/marktmonitor/config.py` → `ROLES` |
| Skills en tools | `config.py` → `SKILLS` |
| Zoektermen voor Adzuna | `config.py` → `ADZUNA_QUERIES` en `QUERY_ROLE` |
| Werkgevers | `config/companies.json` |
| Tijdstip van de dagelijkse run | `.github/workflows/marktmonitor.yml` → `cron` |
| Dashboard | `templates/dashboard.html` |

Na een wijziging in de classificatie draai je `python -m pytest`. De tests bevatten Nederlandse en Engelse voorbeeldtitels en salaristeksten; voeg er gerust je eigen randgevallen aan toe.

## Opslag

Alles staat in `data/`:

| Bestand | Inhoud |
|---|---|
| `postings.csv` | Eén rij per vacature: bron, land, werkgever, titel, rol, senioriteit, werkvorm, skills, salaris, eerst en laatst gezien |
| `counts.csv` | Dagelijkse totaal-aantallen per Adzuna-zoekterm en per rol uit de werkgeversfeeds |
| `hn_monthly.csv` | Per maand het aantal HN-posts per rol en per skill |
| `indeed.csv` | Indeed-index per land en sector |
| `cbs_vacatures.csv` | CBS-vacatures en vacaturegraad per kwartaal |

Vacatureteksten worden niet opgeslagen: alleen de afgeleide kenmerken. Dat houdt de repository klein en respecteert het auteursrecht van de werkgevers.

## Methode en beperkingen

- **Rolclassificatie** gaat op functietitel, met regels voor Nederlandse en Engelse varianten. Officiële beroepsindelingen kennen geen "analytics engineer", dus dit is bewust eigen werk. Specifieke rollen gaan voor algemene: "Analytics Engineer" telt niet als data engineer.
- **Ontdubbeling**: dezelfde werkgever + genormaliseerde titel + land telt één keer, ook als de vacature via meerdere bronnen binnenkomt. Recruitmentbureaus die vacatures herplaatsen onder hun eigen naam worden niet herkend als dubbel.
- **Skills bij Adzuna** zijn gebaseerd op een ingekorte vacaturetekst, dus de aandelen zijn een ondergrens. De werkgeversfeeds geven de volledige tekst.
- **Salaris**: alleen als het in de vacature staat. Door Adzuna geschatte salarissen worden genegeerd. Maandbedragen zijn ×12 gerekend, zonder vakantiegeld of 13e maand. Een mediaan verschijnt pas bij minstens 5 vacatures.
- **Adzuna-tegoed**: standaard maximaal 30 calls per run, ruim binnen het gratis tegoed. Aanpassen via de repository-variabele `ADZUNA_MAX_CALLS`.
- **Hacker News** is een steekproef van de VS-techsector (veel startups), niet van de hele Amerikaanse markt. Het is bedoeld als vroege indicator.
- **UWV Spanningsindicator** heeft geen bruikbare API en is daarom niet geautomatiseerd. Bekijk die per kwartaal op het UWV-dashboard.
- **LinkedIn en Indeed-vacatures** worden niet gescrapet: dat is in strijd met hun voorwaarden en breekt snel.

## Status van de collectors

Gebouwd en getest met nep-antwoorden; de Indeed-collector is ook live getest. De Adzuna-, Hacker News-, CBS- en werkgeverscollectors konden vanuit de bouwomgeving niet live worden getest, omdat die geen toegang had tot die websites. Controleer na de eerste run de log in het tabblad *Actions*: elke bron meldt hoeveel rijen hij ophaalde, en een kapotte bron stopt de andere niet.

## Bronnen en licenties

- Indeed Hiring Lab, [Job Postings Index](https://github.com/hiring-lab/job_postings_tracker), CC BY 4.0. Vermeld Indeed Hiring Lab als bron bij hergebruik.
- [Adzuna API](https://developer.adzuna.com), volgens de Adzuna-gebruiksvoorwaarden.
- Hacker News via de [Algolia HN Search API](https://hn.algolia.com/api).
- CBS StatLine, tabel [80567ned](https://www.cbs.nl/nl-nl/cijfers/detail/80567ned), CC BY 4.0.
- Openbare vacaturefeeds van werkgevers via Greenhouse, Lever, Recruitee, Ashby, Workable en SmartRecruiters.
