"""Finite demo funding accounts in front of the core-banking event consumer."""

from __future__ import annotations

import sqlite3
from dataclasses import asdict
from decimal import Decimal

from .claims import ClaimRecords
from .clock import Clock
from .db import atomically
from .deposits import DepositLedger, euros
from .events import DomainError, MoneyDeposited, MoneyWithdrawn, identifier
from .ledger import PointsLedger
from .service import SavingStreakService
from .vouchers import LocalVoucherIssuer


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS demo_funding_accounts (
            customer_id TEXT PRIMARY KEY,
            account_id TEXT NOT NULL UNIQUE,
            account_name TEXT NOT NULL,
            available_cents INTEGER NOT NULL CHECK (available_cents >= 0)
        );
        CREATE TABLE IF NOT EXISTS demo_transfers (
            customer_id TEXT NOT NULL,
            transfer_id TEXT NOT NULL,
            account_id TEXT NOT NULL,
            direction TEXT NOT NULL,
            amount_cents INTEGER NOT NULL,
            PRIMARY KEY (customer_id, transfer_id)
        );
    """)


def register(conn: sqlite3.Connection, customer_id: str, account_id: str, name: str) -> None:
    """Grant the initial €2,500 once, including for profiles seeded before this feature."""
    conn.execute(
        "INSERT OR IGNORE INTO demo_funding_accounts VALUES (?, ?, ?, ?)",
        (customer_id, account_id, name, 250_000),
    )


class DemoBanking:
    def __init__(self, conn: sqlite3.Connection, clock: Clock):
        self.conn = conn
        self.service = SavingStreakService(
            PointsLedger(conn), clock, ClaimRecords(conn), LocalVoucherIssuer(), DepositLedger(conn)
        )

    def accounts(self, customer_id: str) -> dict:
        with atomically(self.conn):
            account = self.conn.execute(
                "SELECT * FROM demo_funding_accounts WHERE customer_id = ?", (customer_id,)
            ).fetchone()
            if account is None:
                raise DomainError("Sign in to open your accounts.")
            savings = self.service.deposit_standing(customer_id).outstanding_eur
            available = euros(account["available_cents"])
            return {
                "customer_id": customer_id,
                "account_id": account["account_id"],
                "account_name": account["account_name"],
                "funding_account_id": f"funding-{customer_id}",
                "funding_account_name": "Spending account",
                "savings_eur": savings,
                "available_eur": available,
                "total_eur": savings + available,
            }

    def transfer(
        self,
        customer_id: str,
        account_id: str,
        transfer_id: str,
        direction: str,
        amount_eur: Decimal,
    ) -> dict:
        identifier(transfer_id, "transfer_id")
        if direction not in {"deposit", "withdrawal"}:
            raise DomainError("Choose deposit or withdrawal.")
        if (
            not amount_eur.is_finite()
            or amount_eur <= 0
            or amount_eur > Decimal("1000000000")
            or amount_eur != amount_eur.quantize(Decimal("0.01"))
        ):
            raise DomainError("Enter a positive amount with at most two decimal places.")
        cents = int(amount_eur * 100)
        with atomically(self.conn):
            accounts = self.accounts(customer_id)
            if account_id != accounts["account_id"]:
                raise DomainError("This savings account does not belong to the selected customer.")
            previous = self.conn.execute(
                "SELECT * FROM demo_transfers WHERE customer_id = ? AND transfer_id = ?",
                (customer_id, transfer_id),
            ).fetchone()
            if previous:
                if (previous["account_id"], previous["direction"], previous["amount_cents"]) != (
                    account_id,
                    direction,
                    cents,
                ):
                    raise DomainError(
                        "This transfer reference was already used for another transfer."
                    )
                return {
                    "customer_id": customer_id,
                    "points_delta": 0,
                    "balance": self.service.balance(customer_id),
                    "replayed": True,
                }
            limit = accounts["available_eur" if direction == "deposit" else "savings_eur"]
            if amount_eur > limit:
                source = "spending" if direction == "deposit" else "savings"
                raise DomainError(f"Insufficient funds. Available in {source}: €{limit:.2f}.")
            # Prefix IDs so classroom event references cannot collide with transfers.
            event_id = f"demo-transfer-{transfer_id}"
            event = (
                MoneyDeposited(customer_id, account_id, event_id, amount_eur)
                if direction == "deposit"
                else MoneyWithdrawn(customer_id, account_id, event_id, amount_eur)
            )
            result = self.service.handle(event)
            self.conn.execute(
                "UPDATE demo_funding_accounts SET available_cents = available_cents + ?"
                " WHERE customer_id = ?",
                (-cents if direction == "deposit" else cents, customer_id),
            )
            self.conn.execute(
                "INSERT INTO demo_transfers VALUES (?, ?, ?, ?, ?)",
                (customer_id, transfer_id, account_id, direction, cents),
            )
            return {**asdict(result), "replayed": False}
