"""
sql_executor.py
Validates that a generated query is READ-ONLY and runs it against the
configured database engine.

DB_ENGINE in .env selects the backend:
  - "sqlite" : a local file database (no install) -- the POC default
  - "mssql"  : Microsoft SQL Server via pyodbc
  - "mock"   : canned sample rows, no real database
"""
import os
import re
import sqlite3
from pathlib import Path

# Statements that are never allowed in a read-only flow.
_FORBIDDEN = [
    "insert", "update", "delete", "merge", "drop", "alter", "create",
    "truncate", "grant", "revoke", "exec", "execute", "sp_", "xp_",
    "into", "backup", "restore", "shutdown", "reconfigure",
]


class UnsafeQueryError(Exception):
    """Raised when a query is not a safe, single, read-only SELECT."""


def _normalize(sql: str) -> str:
    # Strip line + block comments so they can't hide bad keywords.
    sql = re.sub(r"--[^\n]*", " ", sql)
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    return sql.strip().strip(";").strip()


def validate_read_only(sql: str) -> str:
    """Raise UnsafeQueryError unless `sql` is a single read-only SELECT/CTE."""
    cleaned = _normalize(sql)
    if not cleaned:
        raise UnsafeQueryError("Empty query.")

    lowered = cleaned.lower()

    # Must start with SELECT or a WITH ... CTE.
    if not (lowered.startswith("select") or lowered.startswith("with")):
        raise UnsafeQueryError("Only SELECT queries are allowed.")

    # No stacked statements (a semicolon in the middle = multiple statements).
    if ";" in cleaned:
        raise UnsafeQueryError("Multiple statements are not allowed.")

    # Word-boundary check for forbidden keywords.
    for word in _FORBIDDEN:
        if re.search(rf"\b{re.escape(word)}", lowered):
            raise UnsafeQueryError(f"Forbidden keyword detected: '{word}'.")

    return cleaned


# --------------------------------------------------------------------------- #
# Execution
# --------------------------------------------------------------------------- #
def _mock_run(sql: str, max_rows: int):
    columns = ["id", "customer_name", "order_total", "order_date"]
    rows = [
        [1, "Acme Corp", 12500.00, "2026-06-01"],
        [2, "Globex Ltd", 8400.50, "2026-06-03"],
        [3, "Initech", 3200.75, "2026-06-05"],
    ]
    return columns, rows[:max_rows]


def _real_run(sql: str, max_rows: int):
    import pyodbc

    driver = os.getenv("MSSQL_DRIVER", "ODBC Driver 18 for SQL Server")
    server = os.getenv("MSSQL_SERVER", "localhost")
    port = os.getenv("MSSQL_PORT", "1433")
    database = os.getenv("MSSQL_DATABASE", "")
    user = os.getenv("MSSQL_USER", "")
    password = os.getenv("MSSQL_PASSWORD", "")
    trust = "yes" if os.getenv("MSSQL_TRUST_CERT", "yes").lower() in ("yes", "true", "1") else "no"

    conn_str = (
        f"DRIVER={{{driver}}};"
        f"SERVER={server},{port};"
        f"DATABASE={database};"
        f"UID={user};PWD={password};"
        f"Encrypt=yes;TrustServerCertificate={trust};"
        f"ApplicationIntent=ReadOnly;"
    )

    # autocommit + read-only intent; the SELECT is wrapped in a TOP cap upstream.
    with pyodbc.connect(conn_str, autocommit=True, timeout=15) as conn:
        cursor = conn.cursor()
        cursor.execute(sql)
        columns = [c[0] for c in cursor.description]
        rows = [list(r) for r in cursor.fetchmany(max_rows)]
    return columns, rows


def ensure_sqlite_seeded(path: str) -> None:
    """Create + populate the SQLite file on first use if it doesn't exist."""
    if not Path(path).exists():
        import seed_sqlite
        seed_sqlite.seed(path)


def _sqlite_run(sql: str, max_rows: int):
    path = os.getenv("SQLITE_PATH", "poc.db")
    ensure_sqlite_seeded(path)

    # Open the file READ-ONLY via URI so writes are impossible at the DB layer
    # (a second safety net on top of validate_read_only()).
    uri = f"file:{Path(path).as_posix()}?mode=ro"
    with sqlite3.connect(uri, uri=True, timeout=15) as conn:
        cursor = conn.execute(sql)
        columns = [c[0] for c in cursor.description]
        rows = [list(r) for r in cursor.fetchmany(max_rows)]
    return columns, rows


def _resolve_engine() -> str:
    """Pick the engine: explicit DB_ENGINE wins; otherwise honor USE_MOCK_DB."""
    engine = (os.getenv("DB_ENGINE") or "").strip().lower()
    if engine:
        return engine
    if os.getenv("USE_MOCK_DB", "true").lower() in ("true", "1", "yes"):
        return "mock"
    return "mssql"


def run_query(sql: str, max_rows: int = 200):
    """Validate then execute. Returns (columns, rows). Raises UnsafeQueryError."""
    safe_sql = validate_read_only(sql)
    engine = _resolve_engine()
    if engine == "mock":
        return _mock_run(safe_sql, max_rows)
    if engine == "sqlite":
        return _sqlite_run(safe_sql, max_rows)
    return _real_run(safe_sql, max_rows)
