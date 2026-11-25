"""Integrity checks on the SQLite database."""
import pytest

BRIEF_VIEWS = ["chicago_crime", "iucr", "police_beat_info", "district_ps_info", "city_community", "ward_office"]


def count(db, sql):
    return db.execute(sql).fetchone()[0]


def test_foreign_keys_have_no_orphans(db):
    assert db.execute("PRAGMA foreign_key_check").fetchall() == []


@pytest.mark.parametrize("column,table,key", [
    ("iucr_code", "dim_iucr", "iucr_code"),
    ("beat_num", "dim_beat", "beat_num"),
    ("district_code", "dim_district", "district_code"),
    ("ward_no", "dim_ward", "ward_no"),
    ("community_code", "dim_community", "community_code"),
])
def test_every_crime_key_exists_in_its_dimension(db, column, table, key):
    missing = count(db, f"SELECT COUNT(*) FROM fact_crime WHERE {column} IS NOT NULL "
                        f"AND {column} NOT IN (SELECT {key} FROM {table})")
    assert missing == 0


def test_case_number_is_unique(db):
    assert count(db, "SELECT COUNT(*) - COUNT(DISTINCT case_number) FROM fact_crime") == 0


def test_year_matches_date(db):
    bad = count(db, "SELECT COUNT(*) FROM fact_crime WHERE date IS NOT NULL "
                    "AND CAST(strftime('%Y', date) AS INTEGER) <> crime_year")
    assert bad == 0


def test_reporting_views_match_fact_table(db):
    total = count(db, "SELECT COUNT(*) FROM fact_crime")
    assert count(db, "SELECT SUM(crimes) FROM vw_crime_yearly") == total
    assert count(db, "SELECT SUM(crimes) FROM vw_crime_by_category") == total
    assert count(db, "SELECT SUM(arrests) FROM vw_crime_yearly") == count(db, "SELECT SUM(arrest) FROM fact_crime")


@pytest.mark.parametrize("name", BRIEF_VIEWS)
def test_brief_named_views_exist(db, name):
    row = db.execute("SELECT type FROM sqlite_master WHERE name = ?", (name,)).fetchone()
    assert row is not None and row[0] == "view", "run python scripts/apply_brief_views.py"


def test_chicago_crime_view_has_brief_columns(db):
    cols = [r[1] for r in db.execute("PRAGMA table_info(chicago_crime)")]
    expected = ["id", "case_number", "date", "block", "iucr_code", "location_desc", "arrest", "domestic",
                "beat_num", "district_code", "ward_no", "community_code", "fbi_code", "x_coordinate",
                "y_coordinate", "year", "date_of_update", "latitude", "longitude", "location"]
    assert cols == expected
