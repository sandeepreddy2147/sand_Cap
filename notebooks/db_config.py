"""Shared paths, database connections and report helpers for the four notebooks.

MySQL is used when MYSQL_USER is set in .env (see .env.example) and the server answers.
Otherwise every notebook falls back to the SQLite file database/chicago_crime_analysis.db,
so the notebooks also run on a computer without MySQL. The SQL used is the same for both.
"""
import os
import re
import sqlite3
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

try:
    from dotenv import load_dotenv
except ImportError:  # python-dotenv is optional
    load_dotenv = None

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
REPORTS_DIR = ROOT / "data" / "reports"
SQLITE_PATH = ROOT / "database" / "chicago_crime_analysis.db"

if load_dotenv:
    load_dotenv(ROOT / ".env")


def mysql_settings() -> dict | None:
    """Read MySQL settings from the environment. Returns None when MySQL is not configured."""
    user = os.getenv("MYSQL_USER")
    if not user:
        return None
    database = os.getenv("MYSQL_DATABASE", "chicago_crime")
    if not re.fullmatch(r"\w+", database):
        raise ValueError("MYSQL_DATABASE may contain only letters, digits and underscores.")
    return {
        "host": os.getenv("MYSQL_HOST", "localhost"),
        "port": int(os.getenv("MYSQL_PORT", "3306")),
        "user": user,
        "password": os.getenv("MYSQL_PASSWORD", ""),
        "database": database,
    }


def get_engine():
    """Return (SQLAlchemy engine, backend name). Uses PyMySQL for MySQL, otherwise SQLite."""
    cfg = mysql_settings()
    if cfg:
        try:
            server_url = URL.create("mysql+pymysql", cfg["user"], cfg["password"], cfg["host"], cfg["port"])
            with create_engine(server_url).begin() as conn:
                conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{cfg['database']}`"))
            engine = create_engine(server_url.set(database=cfg["database"]))
            engine.connect().close()
            print(f"Connected to MySQL database '{cfg['database']}' on {cfg['host']}:{cfg['port']}.")
            return engine, "mysql"
        except Exception as exc:  # any connection problem -> use SQLite instead
            print(f"MySQL is not reachable ({type(exc).__name__}). Falling back to SQLite.")
    SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    print(f"Using SQLite database {SQLITE_PATH.name} (MySQL is not configured or not running).")
    return create_engine(f"sqlite:///{SQLITE_PATH.as_posix()}"), "sqlite"


def get_dbapi_connection():
    """Return (connection, backend, placeholder). MySQL Connector for MySQL, sqlite3 otherwise."""
    cfg = mysql_settings()
    if cfg:
        try:
            import mysql.connector

            conn = mysql.connector.connect(**cfg)
            print(f"Connected with MySQL Connector to '{cfg['database']}'.")
            return conn, "mysql", "%s"
        except Exception as exc:
            print(f"MySQL Connector could not connect ({type(exc).__name__}). Falling back to SQLite.")
    SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    print(f"Using SQLite database {SQLITE_PATH.name} (MySQL is not configured or not running).")
    return sqlite3.connect(SQLITE_PATH), "sqlite", "?"


def report_folder(name: str) -> Path:
    folder = REPORTS_DIR / name
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def save_fig(fig, folder: str, filename: str) -> Path:
    path = report_folder(folder) / filename
    fig.savefig(path, dpi=130, bbox_inches="tight")
    return path


def write_report(folder: str, filename: str, title: str, sections: list[tuple[str, str]]) -> Path:
    """Write a Markdown file with one '## heading' per section and one paragraph of text each."""
    lines = [f"# {title}", ""]
    for heading, body in sections:
        lines += [f"## {heading}", body, ""]
    path = report_folder(folder) / filename
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
