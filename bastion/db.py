"""Database layer for Bastion — all SQLite concerns live here."""

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Optional

_conn: Optional[sqlite3.Connection] = None


# TODO: v2 — swap sqlite3 connection for libsql-python client to support Turso team mode.
# Connection string and auth token passed via bastion.init(mode="team", db_url=..., db_token=...)
def init_db(db_path: str) -> sqlite3.Connection:
    """Open (or create) the SQLite database and initialize the schema.

    Sets WAL mode immediately after connecting for better concurrent read performance.
    """
    global _conn
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS errors (
            id TEXT PRIMARY KEY,
            fingerprint TEXT NOT NULL UNIQUE,
            type TEXT NOT NULL,
            message TEXT NOT NULL,
            function TEXT NOT NULL,
            file TEXT NOT NULL,
            line INTEGER NOT NULL,
            locals TEXT,
            hint TEXT,
            occurrence_count INTEGER DEFAULT 1,
            first_seen TEXT NOT NULL,
            last_seen TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS checkpoints (
            id TEXT PRIMARY KEY,
            flow TEXT NOT NULL,
            step TEXT NOT NULL,
            data TEXT,
            timestamp TEXT NOT NULL,
            run_id TEXT
        );

        CREATE TABLE IF NOT EXISTS expectations (
            id TEXT PRIMARY KEY,
            message TEXT NOT NULL,
            context TEXT,
            passed INTEGER NOT NULL,
            timestamp TEXT NOT NULL,
            file TEXT,
            line INTEGER
        );

        CREATE TABLE IF NOT EXISTS breadcrumbs (
            id TEXT PRIMARY KEY,
            message TEXT NOT NULL,
            severity TEXT NOT NULL DEFAULT 'debug',
            tags TEXT,
            timestamp TEXT NOT NULL
        );
    """)
    conn.commit()
    _conn = conn
    return conn


def get_db() -> sqlite3.Connection:
    """Return the active connection opened by init_db.

    Raises RuntimeError if init_db has not been called yet.
    """
    if _conn is None:
        raise RuntimeError("Bastion not initialized. Call bastion.init() first.")
    return _conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# TODO: v2 — if vector search enabled, generate and store an embedding for the error message
# alongside the structured record
def upsert_error(record: dict) -> None:
    """Insert a new error or increment occurrence_count if the fingerprint already exists."""
    conn = get_db()
    now = _now()
    conn.execute(
        """
        INSERT INTO errors (id, fingerprint, type, message, function, file, line,
                            locals, hint, occurrence_count, first_seen, last_seen)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
        ON CONFLICT(fingerprint) DO UPDATE SET
            occurrence_count = occurrence_count + 1,
            last_seen = excluded.last_seen
        """,
        (
            str(uuid.uuid4()),
            record.get("fingerprint"), # unique identifier for the error
            record.get("type"), # type of the error
            record.get("message"), # error message
            record.get("function"), # function that raised the error (func wrapped by guard)
            record.get("file"), # file that the error occurred in
            record.get("line"), # line number where the error occurred
            record.get("locals"), # local variables from context if you set context at the time of the error or all locals if you didn't set context
            record.get("hint"), # optional developer note that is set in the decorator param (currently null - not implemented)
            record.get("first_seen", now), # time stamp when the error first occurred
            now, # time stamp when the error was last seen
        ),
    )
    conn.commit()


def insert_checkpoint(record: dict) -> None:
    """Insert a checkpoint record."""
    conn = get_db()
    conn.execute(
        """
        INSERT INTO checkpoints (id, flow, step, data, timestamp, run_id)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            str(uuid.uuid4()),
            record.get("flow"),
            record.get("step"),
            json.dumps(record.get("data"), default=str) if record.get("data") is not None else None,
            record.get("timestamp", _now()),
            record.get("run_id"),
        ),
    )
    conn.commit()


def insert_expectation(record: dict) -> None:
    """Insert an expectation record."""
    conn = get_db()
    conn.execute(
        """
        INSERT INTO expectations (id, message, context, passed, timestamp, file, line)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(uuid.uuid4()), # unique identifier for the expectation
            record.get("message"), # human/agent-readable description of what was expected
            json.dumps(record.get("context"), default=str) if record.get("context") is not None else None, # context of the expectation
            1 if record.get("passed") else 0, # 1 if the expectation passed, 0 if it failed
            record.get("timestamp", _now()), # time stamp when the expectation was recorded
            record.get("file"), # file that the expectation was recorded in
            record.get("line"), # line number where the expectation was recorded
        ),
    )
    conn.commit()


def insert_breadcrumb(record: dict) -> None:
    """Insert a breadcrumb record."""
    conn = get_db()
    conn.execute(
        """
        INSERT INTO breadcrumbs (id, message, severity, tags, timestamp)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            str(uuid.uuid4()), # unique identifier for the breadcrumb
            record.get("message"), # human/agent-readable description of the breadcrumb
            record.get("severity", "debug"), # severity of the breadcrumb (debug, info, warning, error, critical)
            json.dumps(record.get("tags"), default=str) if record.get("tags") is not None else None, # tags of the breadcrumb for filtering
            record.get("timestamp", _now()), # time stamp when the breadcrumb was recorded
        ),
    )
    conn.commit()
