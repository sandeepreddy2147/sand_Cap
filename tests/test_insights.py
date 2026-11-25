import sqlite3

import pytest

from insights import build_insights, haversine_m, iqr_upper_fence, perimeter, recent_alerts, render_markdown


def make_db():
    conn = sqlite3.connect(":memory:")
    conn.executescript("""
        CREATE TABLE dim_community (community_code INTEGER PRIMARY KEY, community_name TEXT, population INTEGER);
        CREATE TABLE dim_district (district_code INTEGER PRIMARY KEY, district_name TEXT);
        CREATE TABLE dim_iucr (iucr_code TEXT PRIMARY KEY, primary_type TEXT);
        CREATE TABLE fact_crime (id INTEGER PRIMARY KEY, date TEXT, crime_day_name TEXT, iucr_code TEXT,
            block TEXT, location_desc TEXT, arrest INTEGER, domestic INTEGER, beat_num INTEGER,
            district_code INTEGER, community_code INTEGER, latitude REAL, longitude REAL);
        INSERT INTO dim_community VALUES (1, 'Alpha', 10000), (2, 'Beta', 20000);
        INSERT INTO dim_district VALUES (1, 'North');
        INSERT INTO dim_iucr VALUES ('0486', 'BATTERY'), ('0820', 'THEFT');
    """)
    rows = [(i, "2016-05-0%d" % (1 + i % 3), "Monday", "0486" if i % 2 else "0820", "1XX A ST", "STREET",
             i % 4 == 0, 0, 111, 1, 1 if i < 8 else 2, 41.88 + i * 1e-4, -87.62) for i in range(10)]
    conn.executemany("INSERT INTO fact_crime VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    return conn


def test_iqr_fence():
    assert iqr_upper_fence([1, 2, 3, 4, 5, 6, 7, 8, 9, 100]) < 100


def test_haversine_known_distance():
    # One degree of latitude is about 111 km.
    assert haversine_m(41, -87, 42, -87) == pytest.approx(111_195, rel=0.01)


def test_perimeter_radius_and_empty():
    assert perimeter([]) is None
    p = perimeter([(41.0, -87.0)] * 5)
    assert p["radius_m"] == 0 and p["points"] == 5


def test_build_insights_counts_and_rates():
    ins = build_insights(make_db())
    assert ins["totals"]["crimes"] == 10
    assert ins["totals"]["arrests"] == 3
    assert ins["totals"]["arrest_rate"] == 30.0
    top = ins["communities_by_count"][0]
    assert top["name"] == "Alpha" and top["crimes"] == 8 and top["per_10k"] == 8.0
    assert ins["top_types"][0]["share"] == 50.0
    assert ins["hotspot_beats"][0]["beat_num"] == 111


def test_recent_alerts_window_ends_at_newest_date():
    alerts = recent_alerts(make_db(), window_days=1, min_incidents=2)
    assert alerts["end"] == "2016-05-03" and alerts["start"] == "2016-05-03"
    assert all(b["crimes"] >= 2 for b in alerts["beats"])


def test_empty_database_does_not_crash():
    conn = make_db()
    conn.execute("DELETE FROM fact_crime")
    assert build_insights(conn)["totals"]["crimes"] == 0


def test_markdown_renders_on_real_database(db):
    text = render_markdown(build_insights(db))
    assert "## Recommendations" in text and "## Caveats" in text
