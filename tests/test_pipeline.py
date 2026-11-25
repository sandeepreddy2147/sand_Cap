"""Checks on the notebook outputs. They read the analysis database created by the notebooks (SQLite fallback)."""
import sqlite3
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
ANALYSIS_DB = ROOT / "database" / "chicago_crime_analysis.db"
REPORTS = ROOT / "data" / "reports"


@pytest.fixture(scope="module")
def conn():
    if not ANALYSIS_DB.is_file():
        pytest.skip("Run the notebooks first (or MySQL is in use)")
    c = sqlite3.connect(f"{ANALYSIS_DB.as_uri()}?mode=ro", uri=True)
    yield c
    c.close()


def scalar(conn, sql):
    return conn.execute(sql).fetchone()[0]


def test_crime_table_has_all_rows(conn):
    assert scalar(conn, "SELECT COUNT(*) FROM crime") == 498


def test_unique_crime_types(conn):
    assert scalar(conn, "SELECT COUNT(DISTINCT primary_type) FROM crime") == 23


def test_every_crime_has_a_type(conn):
    assert scalar(conn, "SELECT COUNT(*) FROM crime WHERE primary_type IS NULL") == 0


def test_text_columns_are_upper_case_and_trimmed(conn):
    bad = scalar(conn, "SELECT COUNT(*) FROM crime WHERE block <> UPPER(TRIM(block)) "
                       "OR location_desc <> UPPER(TRIM(location_desc))")
    assert bad == 0


def test_year_month_and_weekday_features_match_the_date(conn):
    bad = scalar(conn, "SELECT COUNT(*) FROM crime WHERE crime_year <> CAST(strftime('%Y', crime_date) AS INT) "
                       "OR crime_month <> CAST(strftime('%m', crime_date) AS INT)")
    assert bad == 0


def test_views_match_the_crime_table(conn):
    assert scalar(conn, "SELECT SUM(total_crimes) FROM vw_crime_yearly") == 498
    assert scalar(conn, "SELECT SUM(crime_count) FROM vw_crime_by_category") == 498
    assert scalar(conn, "SELECT SUM(arrest_count) FROM vw_crime_yearly") == scalar(conn, "SELECT SUM(arrest) FROM crime")


def test_summary_tables_are_filled(conn):
    for table in ("summary_crime_yearly", "summary_crime_by_category", "summary_arrest_yearly"):
        assert scalar(conn, f"SELECT COUNT(*) FROM {table}") > 0


@pytest.mark.parametrize("path", [
    "use_case_1/use_case_1_answers.md",
    "use_case_2/use_case_2_interpretations.md", "use_case_2/05_top10_community_areas.png",
    "use_case_3/use_case_3_interpretations.md", "use_case_3/03_correlation_heatmap.png",
    "use_case_4/use_case_4_interpretations.md", "use_case_4/05_crimes_by_police_district.png",
])
def test_report_files_exist(path):
    assert (REPORTS / path).is_file()

