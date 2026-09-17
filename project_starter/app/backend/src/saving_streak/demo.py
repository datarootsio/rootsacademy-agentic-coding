"""Demo identity selection and one-time sample history, not authentication.

The existing event API stays a classroom simulator. Login selects a known
profile; it does not turn that API into a protected banking application.
"""

from __future__ import annotations

import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from .banking import register
from .claims import ClaimRecords
from .clock import FixedClock
from .db import atomically
from .deposits import DepositLedger
from .events import ClaimReward, DomainError, MoneyDeposited, MoneyWithdrawn
from .ledger import PointsLedger
from .service import SavingStreakService
from .vouchers import LocalVoucherIssuer


@dataclass(frozen=True)
class DemoCustomer:
    id: str
    name: str
    email: str
    initials: str
    goal: str
    account_id: str
    account_name: str = "Everyday savings"


CUSTOMERS = (
    DemoCustomer(
        "demo-anke",
        "Anke Peeters",
        "anke@example.com",
        "AP",
        "A little more adventure",
        "savings-anke",
    ),
    DemoCustomer(
        "demo-bram",
        "Bram De Vos",
        "bram@example.com",
        "BD",
        "Building a rainy-day fund",
        "savings-bram",
    ),
    DemoCustomer(
        "demo-lina", "Lina Janssens", "lina@example.com", "LJ", "A fresh start", "savings-lina"
    ),
)


def directory() -> list[dict[str, str]]:
    return [asdict(customer) for customer in CUSTOMERS]


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute("CREATE TABLE IF NOT EXISTS demo_seed_runs (customer_id TEXT PRIMARY KEY)")


def open_demo(email: str, conn: sqlite3.Connection, now: datetime) -> dict[str, str]:
    customer = next((c for c in CUSTOMERS if c.email == email.strip().casefold()), None)
    if customer is None:
        raise DomainError("Choose a demo profile or enter one of the demo email addresses below.")
    clock = FixedClock(now)
    service = SavingStreakService(
        ledger=PointsLedger(conn),
        clock=clock,
        claims=ClaimRecords(conn),
        voucher_issuer=LocalVoucherIssuer(),
        deposit_ledger=DepositLedger(conn),
    )
    # Seed once, atomically. Signing in or restarting never restores spent points
    # or moves the sample dates forward. Existing customer activity is preserved.
    with atomically(conn):
        register(conn, customer.id, customer.account_id, customer.account_name)
        if conn.execute(
            "SELECT 1 FROM demo_seed_runs WHERE customer_id = ?", (customer.id,)
        ).fetchone():
            return asdict(customer)
        deposits = {
            "demo-anke": [(400, "100"), (90, "1200"), (30, "450"), (7, "250")],
            "demo-bram": [(330, "300"), (45, "150"), (10, "50")],
            "demo-lina": [],
        }[customer.id]
        for index, (days, amount) in enumerate(deposits):
            clock.set(now - timedelta(days=days))
            service.handle(
                MoneyDeposited(
                    customer_id=customer.id,
                    account_id=customer.account_id,
                    deposit_id=f"{customer.id}-seed-{index}",
                    amount_eur=Decimal(amount),
                )
            )
        if customer.id != "demo-lina":
            clock.set(now - timedelta(days=3))
            service.handle(
                MoneyWithdrawn(
                    customer_id=customer.id,
                    account_id=customer.account_id,
                    withdrawal_id=f"{customer.id}-seed-withdrawal",
                    amount_eur=Decimal("200" if customer.id == "demo-anke" else "75"),
                )
            )
            clock.set(now - timedelta(days=2))
            service.claim(
                ClaimReward(
                    customer_id=customer.id,
                    item_id="cinema-ticket"
                    if customer.id == "demo-anke"
                    else "coffee-or-snack-voucher",
                    idempotency_key=f"{customer.id}-seed-claim",
                )
            )
        conn.execute("INSERT INTO demo_seed_runs (customer_id) VALUES (?)", (customer.id,))
    return asdict(customer)
