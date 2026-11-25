"""Flask frontend for the Chicago crime SQLite database, with CRUD for crime records."""
import os
import secrets
import sqlite3
from datetime import date, datetime
from pathlib import Path

from flask import (Flask, abort, flash, g, redirect, render_template, request, send_from_directory,
                   session, url_for)

from insights import build_insights, caveats

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("CHICAGO_DB_PATH", BASE_DIR.parent / "database" / "chicago_crime.db"))
REPORTS_DIR = Path(os.getenv("CHICAGO_REPORTS_DIR", BASE_DIR.parent / "data" / "reports"))
PAGE_SIZE = 25
USE_CASES = {
    "use_case_2": "Use Case 2: Exploratory analysis",
    "use_case_3": "Use Case 3: Statistical analysis",
    "use_case_4": "Use Case 4: SQL reporting",
}

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY") or secrets.token_hex(32)


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        if not DB_PATH.is_file():
            abort(503)
        g.db = sqlite3.connect(f"{DB_PATH.as_uri()}?mode=rw", uri=True)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def csrf_token() -> str:
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(16)
    return session["csrf"]


app.jinja_env.globals["csrf_token"] = csrf_token


@app.before_request
def check_csrf() -> None:
    # Both sides must be present: with no session and no form token, None == None would pass.
    if request.method == "POST":
        token = request.form.get("csrf")
        if not token or token != session.get("csrf"):
            abort(400)


@app.teardown_appcontext
def close_db(_exc) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def query(sql: str, params: tuple = ()) -> list[sqlite3.Row]:
    return get_db().execute(sql, params).fetchall()


def int_arg(name: str) -> int | None:
    value = request.args.get(name, "").strip()
    return int(value) if value.isdigit() else None


@app.route("/")
def dashboard():
    totals = query(
        "SELECT COUNT(*) AS crimes, SUM(arrest) AS arrests, SUM(domestic) AS domestic FROM fact_crime"
    )[0]
    yearly = query(
        "SELECT crime_year AS label, COUNT(*) AS crimes, SUM(arrest) AS arrests "
        "FROM fact_crime GROUP BY crime_year ORDER BY crime_year"
    )
    types = query(
        "SELECT i.primary_type AS label, COUNT(*) AS crimes, SUM(f.arrest) AS arrests "
        "FROM fact_crime f JOIN dim_iucr i ON i.iucr_code = f.iucr_code "
        "GROUP BY i.primary_type ORDER BY crimes DESC LIMIT 10"
    )
    weekdays = query(
        "SELECT crime_day_name AS label, COUNT(*) AS crimes, SUM(arrest) AS arrests "
        "FROM fact_crime GROUP BY crime_day_of_week, crime_day_name ORDER BY crime_day_of_week"
    )
    return render_template("dashboard.html", totals=totals, yearly=yearly, types=types, weekdays=weekdays)


@app.route("/crimes")
def crimes():
    filters = {
        "year": int_arg("year"),
        "type": request.args.get("type", "").strip(),
        "community": int_arg("community"),
        "arrest": request.args.get("arrest", ""),
    }
    page = max(int_arg("page") or 1, 1)

    where, params = [], []
    if filters["year"]:
        where.append("f.crime_year = ?")
        params.append(filters["year"])
    if filters["type"]:
        where.append("i.primary_type = ?")
        params.append(filters["type"])
    if filters["community"]:
        where.append("f.community_code = ?")
        params.append(filters["community"])
    if filters["arrest"] in ("0", "1"):
        where.append("f.arrest = ?")
        params.append(int(filters["arrest"]))
    where_sql = f"WHERE {' AND '.join(where)}" if where else ""

    base = (
        "FROM fact_crime f JOIN dim_iucr i ON i.iucr_code = f.iucr_code "
        f"LEFT JOIN dim_community c ON c.community_code = f.community_code {where_sql}"
    )
    total = query(f"SELECT COUNT(*) AS n {base}", tuple(params))[0]["n"]
    pages = max((total + PAGE_SIZE - 1) // PAGE_SIZE, 1)
    page = min(page, pages)
    rows = query(
        "SELECT f.id, f.case_number, f.date, f.block, i.primary_type, i.description, f.location_desc, "
        f"f.arrest, f.domestic, c.community_name {base} ORDER BY f.date DESC, f.id LIMIT ? OFFSET ?",
        (*params, PAGE_SIZE, (page - 1) * PAGE_SIZE),
    )
    options = {
        "years": [r["crime_year"] for r in query("SELECT DISTINCT crime_year FROM fact_crime ORDER BY 1")],
        "types": [r["primary_type"] for r in query(
            "SELECT DISTINCT i.primary_type FROM fact_crime f JOIN dim_iucr i ON i.iucr_code = f.iucr_code ORDER BY 1"
        )],
        "communities": query("SELECT community_code, community_name FROM dim_community ORDER BY community_name"),
    }
    return render_template(
        "crimes.html", rows=rows, total=total, page=page, pages=pages, filters=filters, options=options
    )


CRIME_FIELDS = ("case_number", "date", "iucr_code", "fbi_code", "block", "location_desc",
                "arrest", "domestic", "beat_num", "district_code", "ward_no", "community_code")
LOOKUPS = {
    "beat_num": ("dim_beat", "beat_num", "Beat"),
    "district_code": ("dim_district", "district_code", "District"),
    "ward_no": ("dim_ward", "ward_no", "Ward"),
    "community_code": ("dim_community", "community_code", "Community"),
}


def get_crime(crime_id: int) -> sqlite3.Row:
    row = get_db().execute(
        "SELECT f.*, i.primary_type, i.description, c.community_name FROM fact_crime f "
        "LEFT JOIN dim_iucr i ON i.iucr_code = f.iucr_code "
        "LEFT JOIN dim_community c ON c.community_code = f.community_code WHERE f.id = ?",
        (crime_id,),
    ).fetchone()
    if row is None:
        abort(404)
    return row


def exists(table: str, column: str, value) -> bool:
    return get_db().execute(f"SELECT 1 FROM {table} WHERE {column} = ?", (value,)).fetchone() is not None


def validate_crime(form, crime_id: int | None = None) -> tuple[dict, list[str]]:
    """Read the form, check every field, and return (values, errors)."""
    errors = []
    v = {name: form.get(name, "").strip() for name in CRIME_FIELDS}
    v["case_number"] = v["case_number"].upper()
    v["block"] = v["block"].upper()
    v["location_desc"] = v["location_desc"].upper() or None
    v["fbi_code"] = v["fbi_code"].upper() or None
    v["arrest"] = 1 if form.get("arrest") else 0
    v["domestic"] = 1 if form.get("domestic") else 0

    if not v["case_number"].isalnum() or len(v["case_number"]) > 16:
        errors.append("Case number is required: letters and digits only, at most 16 characters.")
    else:
        other = get_db().execute("SELECT id FROM fact_crime WHERE case_number = ?", (v["case_number"],)).fetchone()
        if other and other["id"] != crime_id:
            errors.append("Another crime already uses this case number.")
    try:
        v["date"] = datetime.strptime(v["date"], "%Y-%m-%d").date()
        if v["date"] > date.today():
            errors.append("Date cannot be in the future.")
    except ValueError:
        errors.append("Date is required (YYYY-MM-DD).")
    if not exists("dim_iucr", "iucr_code", v["iucr_code"]):
        errors.append("Choose a crime type (IUCR code).")
    if not v["block"] or len(v["block"]) > 64:
        errors.append("Block is required, at most 64 characters.")
    if v["location_desc"] and len(v["location_desc"]) > 64:
        errors.append("Location description can be at most 64 characters.")
    if v["fbi_code"] and len(v["fbi_code"]) > 3:
        errors.append("FBI code can be at most 3 characters.")
    for name, (table, column, label) in LOOKUPS.items():
        if not v[name]:
            v[name] = None
        elif not v[name].isdigit():
            errors.append(f"{label} must be a number.")
        elif not exists(table, column, int(v[name])):
            errors.append(f"{label} {v[name]} does not exist.")
        else:
            v[name] = int(v[name])
    return v, errors


def date_columns(d: date) -> dict:
    """Derived date columns, matching the cleaning notebook (Monday = 0)."""
    return {
        "date": d.isoformat(), "date_raw": f"{d.month}/{d.day}/{d.year}", "year": d.year,
        "crime_year": d.year, "crime_month": d.month, "crime_day_of_week": d.weekday(),
        "crime_day_name": d.strftime("%A"), "date_of_update": date.today().isoformat(),
    }


def form_options() -> dict:
    return {
        "iucr": query("SELECT iucr_code, primary_type, description FROM dim_iucr ORDER BY primary_type, description"),
        "communities": query("SELECT community_code, community_name FROM dim_community ORDER BY community_name"),
    }


@app.route("/crimes/<int:crime_id>")
def crime_detail(crime_id: int):
    return render_template("crime_detail.html", crime=get_crime(crime_id))


@app.route("/crimes/new", methods=["GET", "POST"])
def crime_create():
    form = request.form if request.method == "POST" else {"date": date.today().isoformat()}
    if request.method == "POST":
        v, errors = validate_crime(request.form)
        if not errors:
            db = get_db()
            new_id = db.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM fact_crime").fetchone()[0]
            source_row = db.execute("SELECT COALESCE(MAX(source_row), 0) + 1 FROM fact_crime").fetchone()[0]
            row = {**{k: v[k] for k in CRIME_FIELDS if k != "date"}, **date_columns(v["date"]),
                   "id": new_id, "source_row": source_row, "is_possible_duplicate": 0}
            cols = ", ".join(row)
            db.execute(f"INSERT INTO fact_crime ({cols}) VALUES ({', '.join('?' * len(row))})", tuple(row.values()))
            db.commit()
            flash(f"Crime {v['case_number']} added.")
            return redirect(url_for("crime_detail", crime_id=new_id))
        for e in errors:
            flash(e, "error")
    return render_template("crime_form.html", form=form, options=form_options(), crime=None)


@app.route("/crimes/<int:crime_id>/edit", methods=["GET", "POST"])
def crime_edit(crime_id: int):
    crime = get_crime(crime_id)
    form = request.form if request.method == "POST" else dict(crime)
    if request.method == "POST":
        v, errors = validate_crime(request.form, crime_id)
        if not errors:
            row = {**{k: v[k] for k in CRIME_FIELDS if k != "date"}, **date_columns(v["date"])}
            sets = ", ".join(f"{k} = ?" for k in row)
            db = get_db()
            db.execute(f"UPDATE fact_crime SET {sets} WHERE id = ?", (*row.values(), crime_id))
            db.commit()
            flash(f"Crime {v['case_number']} updated.")
            return redirect(url_for("crime_detail", crime_id=crime_id))
        for e in errors:
            flash(e, "error")
    return render_template("crime_form.html", form=form, options=form_options(), crime=crime)


@app.route("/crimes/<int:crime_id>/delete", methods=["GET", "POST"])
def crime_delete(crime_id: int):
    crime = get_crime(crime_id)
    if request.method == "POST":
        db = get_db()
        db.execute("DELETE FROM fact_crime WHERE id = ?", (crime_id,))
        db.commit()
        flash(f"Crime {crime['case_number']} deleted.")
        return redirect(url_for("crimes"))
    return render_template("crime_delete.html", crime=crime)


@app.route("/communities")
def communities():
    rows = query(
        "SELECT c.community_code, c.community_name, c.population, COUNT(f.id) AS crimes, "
        "COALESCE(SUM(f.arrest), 0) AS arrests "
        "FROM dim_community c LEFT JOIN fact_crime f ON f.community_code = c.community_code "
        "GROUP BY c.community_code ORDER BY crimes DESC, c.community_name"
    )
    return render_template("communities.html", rows=rows)


@app.route("/insights")
def insights_page():
    days = int_arg("days") or 7
    ins = build_insights(get_db(), window_days=min(max(days, 1), 90))
    return render_template("insights.html", ins=ins, notes=caveats(ins) if ins.get("recommendations") else [])
def chart_title(filename: str) -> str:
    stem = Path(filename).stem
    words = stem.split("_", 1)[1] if stem[:2].isdigit() else stem
    title = words.replace("_", " ").replace("top10", "top 10").replace("top5", "top 5")
    return title[:1].upper() + title[1:]


def read_findings(folder: Path) -> list[dict]:
    """Turn the use case's *_interpretations.md into [{heading, text}] without a Markdown library."""
    files = sorted(folder.glob("*_interpretations.md"))
    if not files:
        return []
    findings, current = [], None
    for line in files[0].read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("## "):
            current = {"heading": line[3:], "text": []}
            findings.append(current)
        elif line and current is not None and not line.startswith("#"):
            current["text"].append(line)
    return findings


@app.route("/charts")
def charts():
    sections = []
    for key, title in USE_CASES.items():
        folder = REPORTS_DIR / key
        images = sorted(folder.glob("*.png")) if folder.is_dir() else []
        sections.append({
            "key": key,
            "title": title,
            "charts": [{"file": p.name, "title": chart_title(p.name)} for p in images],
            "findings": read_findings(folder) if folder.is_dir() else [],
        })
    return render_template("charts.html", sections=sections)


@app.route("/charts/<use_case>/<path:filename>")
def chart_image(use_case: str, filename: str):
    if use_case not in USE_CASES or not filename.lower().endswith(".png"):
        abort(404)
    return send_from_directory(REPORTS_DIR / use_case, filename, max_age=3600)


@app.errorhandler(404)
def not_found(_e):
    return render_template("error.html", title="Page not found",
                           message="The page you asked for does not exist."), 404


@app.errorhandler(400)
def bad_request(_e):
    return render_template("error.html", title="Form expired",
                           message="Please reload the page and submit the form again."), 400


@app.errorhandler(503)
def no_database(_e):
    return render_template(
        "error.html", title="Database not found",
        message="The file database/chicago_crime.db is missing. Restore it to run the website.",
    ), 503


@app.template_filter("pct")
def pct(part, whole) -> float:
    return round(100 * (part or 0) / whole, 1) if whole else 0.0


if __name__ == "__main__":
    app.run(
        host=os.getenv("FLASK_HOST", "127.0.0.1"),
        port=int(os.getenv("FLASK_PORT", "5000")),
        debug=os.getenv("FLASK_DEBUG") == "1",
    )
