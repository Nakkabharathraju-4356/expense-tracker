"""SQLite connection management and schema initialisation."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from . import config
from .logger import get_logger

log = get_logger(__name__)


@contextmanager
def get_connection(db_path: Path | str | None = None) -> Iterator[sqlite3.Connection]:
    """Yield a connection with foreign keys on; commit on success, rollback on error."""
    path = Path(db_path or config.DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: Path | str | None = None) -> None:
    """Create tables/indexes and seed default categories (idempotent)."""
    schema = config.SCHEMA_PATH.read_text(encoding="utf-8")
    with get_connection(db_path) as conn:
        conn.executescript(schema)
        conn.executemany(
            "INSERT OR IGNORE INTO categories (name) VALUES (?)",
            [(c,) for c in config.DEFAULT_CATEGORIES],
        )
    log.debug("Database ready at %s", db_path or config.DB_PATH)
