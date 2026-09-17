"""The record of claims: what was redeemed, at what price, for which voucher.

A claim is instant and final (spec: "Claim"), and every claim carries a
caller-supplied idempotency key (spec D15). This store is what makes replaying
a key return the *original* voucher instead of issuing a second one, and what
holds the price the item was claimed at so a later catalogue version never
rewrites it (spec D12).

It is not a third ledger. The points side of a claim is one consumption entry
in the points ledger (spec D6); this is the claim itself — the voucher, the
price, the catalogue version — which the points ledger has no column for.

Like the points ledger, it is an injected collaborator behind the seam of spec
D42. It shares the ledger's connection, so a claim and the points it spends are
written inside the one transaction `PointsLedger.atomically()` opens.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime

from .clock import in_brussels

SCHEMA = """
CREATE TABLE IF NOT EXISTS claims (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id       TEXT    NOT NULL,
    idempotency_key   TEXT    NOT NULL,
    item_id           TEXT    NOT NULL,
    item_name         TEXT    NOT NULL,
    price_points      INTEGER NOT NULL,   -- the price it was CLAIMED at (spec D12)
    catalogue_version INTEGER NOT NULL,
    voucher_code      TEXT    NOT NULL,
    claimed_at        TEXT    NOT NULL    -- ISO 8601, Europe/Brussels (spec D5)
);
-- The key is the customer's, not the system's: two customers sending the same
-- key are two claims, and one customer replaying theirs is one.
CREATE UNIQUE INDEX IF NOT EXISTS ux_claims_idempotency
    ON claims (customer_id, idempotency_key);
CREATE INDEX IF NOT EXISTS ix_claims_customer
    ON claims (customer_id, id);
"""


def ensure_schema(conn: sqlite3.Connection) -> None:
    """Create the claims table if it is not there yet."""
    conn.executescript(SCHEMA)


@dataclass(frozen=True)
class ClaimRecord:
    """One claim, as it was made. Nothing here is ever rewritten."""

    customer_id: str
    idempotency_key: str
    item_id: str
    item_name: str
    price_points: int
    catalogue_version: int
    voucher_code: str
    claimed_at: datetime


class ClaimRecords:
    """Append-only store of claims over SQLite."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def find(self, customer_id: str, idempotency_key: str) -> ClaimRecord | None:
        """The claim this key already made, if it made one."""
        row = self._conn.execute(
            "SELECT * FROM claims WHERE customer_id = ? AND idempotency_key = ?",
            (customer_id, idempotency_key),
        ).fetchone()
        return _record(row) if row is not None else None

    def record(self, claim: ClaimRecord) -> None:
        """Write the claim. The unique index is the last word on replays."""
        self._conn.execute(
            "INSERT INTO claims"
            " (customer_id, idempotency_key, item_id, item_name, price_points,"
            "  catalogue_version, voucher_code, claimed_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                claim.customer_id,
                claim.idempotency_key,
                claim.item_id,
                claim.item_name,
                claim.price_points,
                claim.catalogue_version,
                claim.voucher_code,
                in_brussels(claim.claimed_at).isoformat(),
            ),
        )

    def for_customer(self, customer_id: str) -> list[ClaimRecord]:
        """Every claim this customer made, newest first."""
        rows = self._conn.execute(
            "SELECT * FROM claims WHERE customer_id = ?", (customer_id,)
        ).fetchall()
        # Sorted on the parsed instant, not on the stored string: two stamps an
        # hour apart across the Brussels autumn fold share a wall-clock reading
        # and differ only in their offset, which sorts the wrong way as text.
        # `id` breaks a genuine tie in the order the claims were written.
        ordered = sorted(
            rows,
            key=lambda row: (datetime.fromisoformat(row["claimed_at"]), row["id"]),
            reverse=True,
        )
        return [_record(row) for row in ordered]


def _record(row: sqlite3.Row) -> ClaimRecord:
    return ClaimRecord(
        customer_id=row["customer_id"],
        idempotency_key=row["idempotency_key"],
        item_id=row["item_id"],
        item_name=row["item_name"],
        price_points=int(row["price_points"]),
        catalogue_version=int(row["catalogue_version"]),
        voucher_code=row["voucher_code"],
        claimed_at=datetime.fromisoformat(row["claimed_at"]),
    )
