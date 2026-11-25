"""Patrol and prevention insights for the Chicago Police Department, computed from SQLite.

Used by the Flask page /insights (live, so new records show up on the next page load) and by
scripts/generate_insights.py (writes data/reports/cpd_insights.md). Only the standard library
is needed.
"""
import math
import sqlite3
from datetime import date, timedelta

EARTH_RADIUS_M = 6_371_000
PERIMETER_SHARE = 0.80  # the perimeter circle holds this share of a hotspot's incidents


def _rows(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> list[dict]:
    cur = conn.execute(sql, params)
    names = [c[0] for c in cur.description]
    return [dict(zip(names, r)) for r in cur.fetchall()]


def _quantile(sorted_values: list[float], q: float) -> float:
    """Linear-interpolated quantile (same method as numpy's default)."""
    if not sorted_values:
        return float("nan")
    pos = (len(sorted_values) - 1) * q
    lo, hi = math.floor(pos), math.ceil(pos)
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * (pos - lo)


def iqr_upper_fence(values: list[int]) -> float:
    s = sorted(values)
    q1, q3 = _quantile(s, 0.25), _quantile(s, 0.75)
    return q3 + 1.5 * (q3 - q1)


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def perimeter(points: list[tuple[float, float]]) -> dict | None:
    """Circle around the centre of the incidents that holds PERIMETER_SHARE of them."""
    if not points:
        return None
    lat = sum(p[0] for p in points) / len(points)
    lon = sum(p[1] for p in points) / len(points)
    dists = sorted(haversine_m(lat, lon, p[0], p[1]) for p in points)
    return {
        "center_lat": round(lat, 5),
        "center_lon": round(lon, 5),
        "radius_m": round(_quantile(dists, PERIMETER_SHARE)),
        "points": len(points),
    }


def build_insights(conn: sqlite3.Connection, window_days: int = 7) -> dict:
    out: dict = {}
    t = _rows(conn, """
        SELECT COUNT(*) AS crimes, COALESCE(SUM(arrest), 0) AS arrests,
               COALESCE(SUM(domestic), 0) AS domestic, MIN(date) AS first_date,
               MAX(date) AS last_date, COUNT(DISTINCT date) AS distinct_dates
        FROM fact_crime""")[0]
    n = t["crimes"] or 0
    t["arrest_rate"] = round(100 * t["arrests"] / n, 2) if n else 0.0
    t["domestic_rate"] = round(100 * t["domestic"] / n, 2) if n else 0.0
    out["totals"] = t
    if not n:
        return out

    comm = _rows(conn, """
        SELECT c.community_code AS code, c.community_name AS name, c.population,
               COUNT(f.id) AS crimes, COALESCE(SUM(f.arrest), 0) AS arrests
        FROM dim_community c LEFT JOIN fact_crime f ON f.community_code = c.community_code
        GROUP BY c.community_code""")
    for r in comm:
        r["per_10k"] = round(10000 * r["crimes"] / r["population"], 2) if r["population"] else None
        r["share"] = round(100 * r["crimes"] / n, 2)
    fence = iqr_upper_fence([r["crimes"] for r in comm])
    out["community_fence"] = round(fence, 1)
    out["communities_by_count"] = sorted(comm, key=lambda r: (-r["crimes"], r["name"]))[:5]
    out["communities_by_rate"] = sorted(
        (r for r in comm if r["per_10k"] is not None), key=lambda r: (-r["per_10k"], r["name"]))[:5]
    out["high_crime_communities"] = [r for r in out["communities_by_count"] if r["crimes"] > fence]

    out["districts"] = _rows(conn, """
        SELECT d.district_code AS code, d.district_name AS name, COUNT(*) AS crimes,
               SUM(f.arrest) AS arrests
        FROM fact_crime f JOIN dim_district d ON d.district_code = f.district_code
        GROUP BY d.district_code ORDER BY crimes DESC, d.district_code LIMIT 5""")

    out["types"] = _rows(conn, """
        SELECT i.primary_type AS name, COUNT(*) AS crimes, SUM(f.arrest) AS arrests,
               ROUND(100.0 * COUNT(*) / ?, 2) AS share,
               ROUND(100.0 * SUM(f.arrest) / COUNT(*), 2) AS arrest_rate
        FROM fact_crime f JOIN dim_iucr i ON i.iucr_code = f.iucr_code
        GROUP BY i.primary_type ORDER BY crimes DESC, name""", (n,))
    out["top_types"] = out["types"][:5]
    out["low_arrest_types"] = sorted(
        (r for r in out["types"][:10] if r["arrest_rate"] < out["totals"]["arrest_rate"]),
        key=lambda r: (r["arrest_rate"], -r["crimes"]))[:3]

    out["locations"] = _rows(conn, """
        SELECT location_desc AS name, COUNT(*) AS crimes FROM fact_crime
        WHERE location_desc IS NOT NULL GROUP BY location_desc ORDER BY crimes DESC, name LIMIT 5""")
    out["blocks"] = _rows(conn, """
        SELECT block AS name, COUNT(*) AS crimes FROM fact_crime
        WHERE block IS NOT NULL GROUP BY block HAVING COUNT(*) >= 2
        ORDER BY crimes DESC, name LIMIT 5""")
    out["weekdays"] = _rows(conn, """
        SELECT crime_day_name AS name, COUNT(*) AS crimes FROM fact_crime
        WHERE crime_day_name IS NOT NULL GROUP BY crime_day_name ORDER BY crimes DESC""")

    # Hotspot beats and their safety perimeters.
    beats = _rows(conn, """
        SELECT beat_num, district_code, COUNT(*) AS crimes, SUM(arrest) AS arrests
        FROM fact_crime WHERE beat_num IS NOT NULL
        GROUP BY beat_num ORDER BY crimes DESC, beat_num""")
    beat_fence = iqr_upper_fence([b["crimes"] for b in beats]) if beats else 0
    hot = [b for b in beats if b["crimes"] > beat_fence] or beats[:5]
    out["beat_fence"] = round(beat_fence, 1)
    out["beat_fence_used"] = any(b["crimes"] > beat_fence for b in beats)
    hotspots = []
    for b in hot[:5]:
        pts = [(r[0], r[1]) for r in conn.execute(
            "SELECT latitude, longitude FROM fact_crime WHERE beat_num = ? "
            "AND latitude IS NOT NULL AND longitude IS NOT NULL", (b["beat_num"],))]
        b["perimeter"] = perimeter(pts)
        hotspots.append(b)
    out["hotspot_beats"] = hotspots

    out["alerts"] = recent_alerts(conn, window_days)
    out["window_days"] = window_days
    out["recommendations"] = recommendations(out)
    return out


def recent_alerts(conn: sqlite3.Connection, window_days: int = 7, min_incidents: int = 2) -> dict:
    """Beats with the most incidents in the latest window_days of data.

    The window ends at the newest crime date in the database, so the alerts update as soon as
    new records are ingested.
    """
    last = conn.execute("SELECT MAX(date) FROM fact_crime").fetchone()[0]
    if not last:
        return {"start": None, "end": None, "beats": []}
    end = date.fromisoformat(last)
    start = end - timedelta(days=window_days - 1)
    beats = _rows(conn, """
        SELECT beat_num, district_code, COUNT(*) AS crimes, SUM(arrest) AS arrests
        FROM fact_crime WHERE date BETWEEN ? AND ? AND beat_num IS NOT NULL
        GROUP BY beat_num HAVING COUNT(*) >= ?
        ORDER BY crimes DESC, beat_num LIMIT 5""", (start.isoformat(), end.isoformat(), min_incidents))
    for b in beats:
        top = conn.execute("""
            SELECT i.primary_type FROM fact_crime f JOIN dim_iucr i ON i.iucr_code = f.iucr_code
            WHERE f.beat_num = ? AND f.date BETWEEN ? AND ?
            GROUP BY i.primary_type ORDER BY COUNT(*) DESC, i.primary_type LIMIT 1""",
            (b["beat_num"], start.isoformat(), end.isoformat())).fetchone()
        b["top_type"] = top[0] if top else None
    return {"start": start.isoformat(), "end": end.isoformat(), "beats": beats}


def recommendations(ins: dict) -> list[str]:
    recs = []
    for r in ins["high_crime_communities"]:
        recs.append(
            f"Add patrols in {r['name']} (community {r['code']}): {r['crimes']} records, above the "
            f"IQR upper fence of {ins['community_fence']}.")
    if not ins["high_crime_communities"]:
        top = ins["communities_by_count"][0]
        recs.append(f"No community is above the IQR fence. Start with {top['name']} ({top['crimes']} records).")
    rate = ins["communities_by_rate"][0]
    recs.append(
        f"Check {rate['name']} on a per-resident basis: {rate['per_10k']} records per 10,000 residents, "
        "the highest rate. Small populations inflate rates, so confirm with a longer period.")
    if ins["districts"]:
        d = ins["districts"][0]
        recs.append(f"Prioritise district {d['code']} ({d['name']}) for staffing: {d['crimes']} records, the most of any district.")
    if ins["top_types"]:
        t = ins["top_types"][0]
        recs.append(f"Run prevention campaigns for {t['name']}: {t['share']}% of all records.")
    for t in ins["low_arrest_types"]:
        recs.append(
            f"Review investigation follow-up for {t['name']}: arrest rate {t['arrest_rate']}% against "
            f"{ins['totals']['arrest_rate']}% overall.")
    if ins["hotspot_beats"]:
        h = ins["hotspot_beats"][0]
        p = h["perimeter"]
        where = (f", perimeter radius about {p['radius_m']} m around ({p['center_lat']}, {p['center_lon']})"
                 if p else "")
        recs.append(f"Set a safety perimeter for beat {h['beat_num']} ({h['crimes']} records){where}.")
    if ins["weekdays"]:
        if ins["totals"]["distinct_dates"] >= 100:
            recs.append(f"Schedule extra shifts on {ins['weekdays'][0]['name']}, the weekday with the most records.")
        else:
            recs.append("Do not set shift patterns from weekday counts yet: the data covers only "
                        f"{ins['totals']['distinct_dates']} distinct dates, so weekday totals reflect which dates were sampled.")
    if ins["alerts"]["beats"]:
        b = ins["alerts"]["beats"][0]
        recs.append(
            f"Near-term alert: beat {b['beat_num']} had {b['crimes']} incidents between "
            f"{ins['alerts']['start']} and {ins['alerts']['end']} (mostly {b['top_type']}). Consider sending a patrol.")
    return recs


def caveats(ins: dict) -> list[str]:
    t = ins["totals"]
    notes = [
        f"The database holds {t['crimes']} records on {t['distinct_dates']} distinct dates "
        f"({t['first_date']} to {t['last_date']}). This is the sample supplied with the project, not the full "
        "2012 to 2016 extract, so counts show this sample and not citywide levels.",
        "The source has no time of day, so hour-of-day patrol timing cannot be derived.",
        "Counts are reported crimes and are not adjusted for population, except where a rate is shown.",
    ]
    return notes


def render_markdown(ins: dict) -> str:
    t = ins["totals"]
    L = ["# Chicago Police Department: patrol and prevention insights",
         "",
         f"Generated from `database/chicago_crime.db`. {t['crimes']} records, "
         f"{t['arrests']} arrests ({t['arrest_rate']}%), {t['domestic_rate']}% domestic.", "",
         "## Caveats", ""]
    L += [f"- {c}" for c in caveats(ins)]
    L += ["", "## Recommendations", ""]
    L += [f"{i}. {r}" for i, r in enumerate(ins["recommendations"], 1)]

    def table(title, header, rows):
        L.extend(["", f"## {title}", "", "| " + " | ".join(header) + " |",
                  "|" + "---|" * len(header)])
        L.extend("| " + " | ".join(str(c) for c in r) + " |" for r in rows)

    table("Communities needing patrols (by count)", ["Community", "Records", "Share %", "Per 10k residents"],
          [(r["name"], r["crimes"], r["share"], r["per_10k"]) for r in ins["communities_by_count"]])
    table("Communities with the highest rate per resident", ["Community", "Population", "Records", "Per 10k residents"],
          [(r["name"], r["population"], r["crimes"], r["per_10k"]) for r in ins["communities_by_rate"]])
    table("Police districts", ["District", "Name", "Records", "Arrests"],
          [(r["code"], r["name"], r["crimes"], r["arrests"]) for r in ins["districts"]])
    table("Top crime types", ["Type", "Records", "Share %", "Arrest rate %"],
          [(r["name"], r["crimes"], r["share"], r["arrest_rate"]) for r in ins["top_types"]])
    label = "above the IQR fence" if ins["beat_fence_used"] else "top 5 (none above the IQR fence)"
    table(f"High-crime beats and safety perimeters ({label}, fence {ins['beat_fence']})",
          ["Beat", "District", "Records", "Centre (lat, lon)", "Radius m (80% of incidents)"],
          [(b["beat_num"], b["district_code"], b["crimes"],
            f"{b['perimeter']['center_lat']}, {b['perimeter']['center_lon']}" if b["perimeter"] else "n/a",
            b["perimeter"]["radius_m"] if b["perimeter"] else "n/a") for b in ins["hotspot_beats"]])
    table("Hotspot blocks (2 or more records)", ["Block", "Records"], [(r["name"], r["crimes"]) for r in ins["blocks"]])
    table("Common location types", ["Location", "Records"], [(r["name"], r["crimes"]) for r in ins["locations"]])
    table("Weekday load", ["Weekday", "Records"], [(r["name"], r["crimes"]) for r in ins["weekdays"]])
    a = ins["alerts"]
    table(f"Near-term alerts: last {ins['window_days']} days of data ({a['start']} to {a['end']})",
          ["Beat", "District", "Incidents", "Main type"],
          [(b["beat_num"], b["district_code"], b["crimes"], b["top_type"]) for b in a["beats"]])
    L += ["", "The alert window ends at the newest crime date in the database. Re-run "
          "`python scripts/generate_insights.py` or open the `/insights` page after each new load.", ""]
    return "\n".join(L)
