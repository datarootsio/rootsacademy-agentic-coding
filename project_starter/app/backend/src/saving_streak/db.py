"""SQLite plumbing.

Connection handling and the unit of work over it — no schema and no domain
tables. Tickets that need persistence add their own migrations; this module
just makes a correctly configured connection, and one way of writing through
it, available to them.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from .settings import db_path


def connect(path: Path | None = None) -> sqlite3.Connection:
    """Open a connection with the settings the whole app relies on."""
    target = path or db_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    # check_same_thread=False: a sync FastAPI route runs on a worker thread, so
    # the connection is opened on one thread and used on another. Each request
    # still gets its own connection, and sqlite3 serialises access itself.
    conn = sqlite3.connect(target, isolation_level=None, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # Foreign keys are off by default in SQLite; the ledgers will want them.
    conn.execute("PRAGMA foreign_keys = ON")
    # The demo UI reads balance and history in parallel, so several connections
    # open at once against the same file. Wait for a lock instead of failing
    # the request the moment one is held.
    conn.execute("PRAGMA busy_timeout = 5000")
    _enable_wal(conn)
    return conn


def _enable_wal(conn: sqlite3.Connection) -> None:
    """Switch the file to WAL, tolerating a connection that loses the race.

    WAL keeps the reviewer's browser and a CLI poking the same file happy. It
    is a durable property of the database file, so whoever gets there first
    sets it for everyone; a connection that finds the file locked mid-switch
    would rather carry on in the default journal mode than fail a request.
    """
    try:
        conn.execute("PRAGMA journal_mode = WAL")
    except sqlite3.OperationalError:
        pass


@contextmanager
def connection(path: Path | None = None) -> Iterator[sqlite3.Connection]:
    """Connection as a context manager, always closed."""
    conn = connect(path)
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def atomically(conn: sqlite3.Connection) -> Iterator[None]:
    """Run reads and writes on `conn` as one unit, with no writer in between.

    Part of a ledger's contract, not an SQLite detail: an append-only ledger is
    read before it is appended to ("has this deposit already been reversed?"),
    and core-banking feeds are at-least-once, so the same event can arrive on
    two workers at the same moment. Without this, both read the same ledger and
    both append.

    Nesting is allowed and means one transaction, not two. That holds across
    the two ledgers of spec D6 as well as within one: they are separate
    ledgers with separate tables, but a single deposit writes to both, and a
    connection they share must commit both or neither. The block that opened
    the transaction is the one that commits or rolls it back, whichever ledger
    that was — which is why the nesting is tracked on the connection rather
    than on either ledger object. Two ledgers on two connections are two
    independent transactions, each correct on its own.
    """
    if conn.in_transaction:
        yield
        return

    conn.execute("BEGIN IMMEDIATE")
    try:
        yield
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")
