# Chicago Crime web app

A small Flask site built with HTML templates and one CSS file (no JavaScript). It reads
`../database/chicago_crime.db` in read-only mode.

## Pages

- `/` Dashboard: totals, crimes by year, by day of week, top 10 crime types
- `/crimes` Crime list with filters (year, crime type, community, arrest) and paging
- `/crimes/new`, `/crimes/<id>`, `/crimes/<id>/edit`, `/crimes/<id>/delete` Add, view, edit and delete crimes
  (the `fact_crime` table only). Set `FLASK_SECRET_KEY` when deploying so form tokens survive restarts.
- `/communities` Crimes, arrest rate and crimes per 10k people for each community
- `/charts` Saved charts and findings from use cases 2 to 4
- `/insights` Patrol and prevention recommendations for CPD: priority communities and districts, hotspot
  beats with safety perimeters, and near-term alerts for the latest days in the data (`?days=1..90`).
  Computed live from the database by `insights.py`, so it updates after each new load.

## Run

```powershell
cd app
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000.

If the database is missing, run `notebooks/04_ingestion_pipeline.ipynb` first.

## Settings (environment variables)

| Variable | Default | Purpose |
|---|---|---|
| `CHICAGO_DB_PATH` | `../database/chicago_crime.db` | SQLite file to read |
| `FLASK_HOST` | `127.0.0.1` | Use `0.0.0.0` to accept outside connections |
| `FLASK_PORT` | `5000` | Port |
| `FLASK_DEBUG` | off | Set to `1` only on your own machine |

## Layout

```
app/
  app.py              Flask routes and SQL queries
  requirements.txt    Flask
  templates/          base.html, dashboard.html, crimes.html, communities.html, error.html, _macros.html
  static/style.css    All styling
```
