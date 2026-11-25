import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))
sys.path.insert(0, str(ROOT / "scripts"))

DB_PATH = ROOT / "database" / "chicago_crime.db"


@pytest.fixture(scope="session")
def db():
    """Read-only connection to the real database."""
    if not DB_PATH.is_file():
        pytest.skip("database/chicago_crime.db not found")
    conn = sqlite3.connect(f"{DB_PATH.as_uri()}?mode=ro", uri=True)
    yield conn
    conn.close()
