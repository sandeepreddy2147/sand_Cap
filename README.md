<<<<<<< HEAD
﻿# Chicago Crime Analytics (final)

| Folder | Content |
|---|---|
| `data/raw/` | The six supplied CSV files |
| `notebooks/` | `01` to `04`: one notebook per use case, already run, with explanations |
| `data/reports/` | One answers file per use case and the charts the use cases ask for |
| `database/chicago_crime.db` | SQLite star schema used by the Flask website |
| `database/chicago_crime_analysis.db` | Tables and views written by the notebooks when MySQL is not used |
| `app/` | Flask website with CRUD for crimes, dashboard, charts and insights |
| `tests/` | pytest checks for the notebook outputs, the database and the website |

## Run

    pip install -r requirements.txt
    jupyter notebook notebooks        # run 01, 02, 03, 04 in order
    python app/app.py                 # website at http://127.0.0.1:5000
    python -m pytest tests

## MySQL

Copy `.env.example` to `.env` and fill in `MYSQL_USER` and `MYSQL_PASSWORD`. The notebooks then use MySQL
(SQLAlchemy + PyMySQL in notebook 01, MySQL Connector in notebook 04). With `MYSQL_USER` empty, or when the server
is not running, they use the SQLite file instead. The tables, SQL and views are the same.

## Data note
The crime file has 498 records, 490 of them from 2016, and its dates have no time of day. Yearly, monthly and hourly
results describe this sample. The notebooks say so wherever it changes a conclusion.
=======
# sand_Cap
>>>>>>> e6c337b976e5f31f6facf5a7fafcfaae091296cb
