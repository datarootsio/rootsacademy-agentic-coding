"""Bringing the database up to date, in one place.

Each storage module owns its own DDL; this is the list of them. Schema creation
is a write transaction, so it happens once, at startup, rather than whenever a
collaborator is constructed — otherwise a read-only balance query takes a write
lock on the file.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from . import banking, claims, demo, deposits, ledger
from .db import connection


def ensure_schema(conn: sqlite3.Connection) -> None:
    """Create every table the app needs, if they are not there yet."""
    ledger.ensure_schema(conn)
    deposits.ensure_schema(conn)
    claims.ensure_schema(conn)
    demo.ensure_schema(conn)
    banking.ensure_schema(conn)


def migrate(path: Path | None = None) -> None:
    """Migrate the configured database, once, before the app serves anything."""
    with connection(path) as conn:
        ensure_schema(conn)
