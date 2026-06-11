"""
seed_sqlite.py
Creates a local SQLite database file with sample customers/orders data so the
POC can run REAL queries with zero database server install.

Run manually to (re)create the data:   python seed_sqlite.py
It is also called automatically the first time a query runs if the file is
missing (see sql_executor.ensure_sqlite_seeded).
"""
import os
import sqlite3
from pathlib import Path

SCHEMA_AND_DATA = """
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS customers;

CREATE TABLE customers (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_name TEXT NOT NULL,
    region        TEXT,
    created_at    TEXT DEFAULT (datetime('now'))
);

CREATE TABLE orders (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    order_total REAL NOT NULL,
    order_date  TEXT NOT NULL,
    status      TEXT NOT NULL   -- 'paid', 'pending', 'cancelled'
);

INSERT INTO customers (customer_name, region) VALUES
    ('Acme Corp', 'North'),
    ('Globex Ltd', 'West'),
    ('Initech', 'East'),
    ('Umbrella Inc', 'South'),
    ('Soylent Co', 'North');

INSERT INTO orders (customer_id, order_total, order_date, status) VALUES
    (1, 12500.00, '2026-06-01', 'paid'),
    (1,  5000.00, '2026-06-07', 'paid'),
    (2,  8400.50, '2026-06-03', 'paid'),
    (3,  3200.75, '2026-06-05', 'pending'),
    (4,  9800.00, '2026-05-28', 'paid'),
    (4,  2100.00, '2026-06-09', 'cancelled'),
    (5,  6750.25, '2026-06-02', 'paid');
"""


def seed(path: str) -> str:
    """(Re)create the SQLite database at `path` with sample data."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.executescript(SCHEMA_AND_DATA)
        conn.commit()
    return path


if __name__ == "__main__":
    db_path = os.getenv("SQLITE_PATH", "poc.db")
    seed(db_path)
    print(f"Seeded SQLite database at: {os.path.abspath(db_path)}")
