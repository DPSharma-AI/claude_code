"""Database layer for Spendly.

get_db()   — returns a SQLite connection with row_factory and foreign keys enabled
init_db()  — creates all tables using CREATE TABLE IF NOT EXISTS
seed_db()  — inserts sample data for development
"""

import os
import sqlite3
from datetime import datetime, timezone

from flask import current_app, g

DEFAULT_DATABASE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "expense_tracker.db"
)

# ------------------------------------------------------------------ #
# Connection                                                         #
# ------------------------------------------------------------------ #

def get_db(app=None):
    """Return the current request's SQLite connection, opening it if needed.

    The connection uses ``sqlite3.Row`` as its row factory so rows behave like
    dictionaries, and enables foreign key enforcement with ``PRAGMA
    foreign_keys = ON``.
    """
    if app is None:
        app = current_app
    if "db" not in g:
        database = app.config.get("DATABASE", DEFAULT_DATABASE)
        os.makedirs(os.path.dirname(database), exist_ok=True)
        conn = sqlite3.connect(database)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        g.db = conn
    return g.db


def close_db(e=None):
    """Close the database connection at the end of the request."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


# ------------------------------------------------------------------ #
# Schema                                                             #
# ------------------------------------------------------------------ #

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    category TEXT NOT NULL,
    description TEXT,
    date TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_expenses_user_id ON expenses(user_id);
CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(date);
"""


def init_db(app=None):
    """Create all tables using CREATE TABLE IF NOT EXISTS.

    Safe to run repeatedly — existing tables are left untouched.
    """
    if app is None:
        app = current_app
    with app.app_context():
        db = get_db(app)
        db.executescript(SCHEMA)
        db.commit()


# ------------------------------------------------------------------ #
# Seed data                                                          #
# ------------------------------------------------------------------ #

SEED_USER = {
    "name": "Demo User",
    "email": "demo@example.com",
    "password_hash": (
        "scrypt:32768:8:1$"
        "k4sS3mPLe$sAltIsNoTReAl$"
        "hAsHvAlUeIsNoTReAlEither"
    ),
}

SEED_EXPENSES = [
    {"amount": 4500.00, "category": "Bills", "description": "March electricity bill", "date": "2026-03-05"},
    {"amount": 3200.00, "category": "Food", "description": "Groceries", "date": "2026-03-07"},
    {"amount": 2050.00, "category": "Health", "description": "Pharmacy", "date": "2026-03-10"},
    {"amount": 1800.00, "category": "Transport", "description": "Cab fare", "date": "2026-03-12"},
]


def seed_db(app=None):
    """Insert sample data for development.

    Only seeds when the tables are empty, so re-running is safe.
    """
    if app is None:
        app = current_app
    with app.app_context():
        db = get_db(app)

        if db.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
            db.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                (SEED_USER["name"], SEED_USER["email"], SEED_USER["password_hash"]),
            )

        if db.execute("SELECT COUNT(*) FROM expenses").fetchone()[0] == 0:
            user_id = db.execute(
                "SELECT id FROM users WHERE email = ?",
                (SEED_USER["email"],),
            ).fetchone()["id"]
            now = datetime.now(timezone.utc).isoformat()
            for expense in SEED_EXPENSES:
                db.execute(
                    "INSERT INTO expenses "
                    "(user_id, amount, category, description, date, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        user_id,
                        expense["amount"],
                        expense["category"],
                        expense["description"],
                        expense["date"],
                        now,
                    ),
                )

        db.commit()


def init_app(app):
    """Register database helpers with the Flask app.

    Call this from ``app.py`` (e.g. ``database.db.init_app(app)``) so that
    connections are closed after each request and the ``flask init-db`` /
    ``flask seed-db`` CLI commands are available.
    """
    app.teardown_appcontext(close_db)

    @app.cli.command("init-db")
    def init_db_command():
        """Clear existing data and create new tables."""
        init_db(app)
        click_echo = __import__("click").echo
        click_echo("Initialized the database.")

    @app.cli.command("seed-db")
    def seed_db_command():
        """Insert sample data for development."""
        seed_db(app)
        click_echo("Seeded the database.")
