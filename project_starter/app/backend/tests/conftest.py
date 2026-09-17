"""Shared fixtures.

Everything a test touches is built around the seam of spec D42: a
`SavingStreakService` with a pinned clock and an empty points ledger. Tests
send events in and assert on balances and history — never on ledger internals
or lot identifiers (spec T1).
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from saving_streak.api import create_app, get_service
from saving_streak.claims import ClaimRecords
from saving_streak.clock import FixedClock, in_brussels
from saving_streak.db import connect
from saving_streak.deposits import DepositLedger
from saving_streak.ledger import PointsLedger
from saving_streak.migrations import ensure_schema
from saving_streak.service import SavingStreakService
from saving_streak.settings import DB_PATH_ENV
from saving_streak.vouchers import IssuanceRequest, Voucher, VoucherIssuanceFailed, VoucherIssuer

#: An arbitrary but pinned instant. No test reads wall-clock time (spec T2):
#: this suite behaves the same in January and in March.
PINNED_NOW = in_brussels(datetime(2026, 3, 14, 10, 30))


@pytest.fixture
def clock() -> FixedClock:
    return FixedClock(PINNED_NOW)


@pytest.fixture
def db_file(tmp_path, monkeypatch) -> Path:
    """A throwaway database, and the app configured to use it."""
    path = tmp_path / "saving-streak.db"
    monkeypatch.setenv(DB_PATH_ENV, str(path))
    return path


@pytest.fixture
def ledger_conn(db_file: Path) -> Iterator[sqlite3.Connection]:
    conn = connect(db_file)
    ensure_schema(conn)  # in the app this happens once, at startup
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture
def ledger(ledger_conn: sqlite3.Connection) -> PointsLedger:
    """The points ledger behind the seam.

    A test asks for this only to *arrange* a starting position no command in
    this ticket can reach yet (a balance already spent down). Assertions stay
    at the seam, where spec T1 puts them.
    """
    return PointsLedger(ledger_conn)


@pytest.fixture
def deposit_ledger(ledger_conn: sqlite3.Connection) -> DepositLedger:
    """The deposit-lot ledger behind the seam — the other ledger of spec D6.

    On the points ledger's own connection, so the points lot and the deposit
    lot one deposit opens are written inside the one transaction. They are
    still two ledgers over two tables; sharing a connection is what makes the
    pair commit or roll back together, not what makes them one.
    """
    return DepositLedger(ledger_conn)


class FakeVoucherIssuer(VoucherIssuer):
    """A fake, not a mock (spec T7).

    It issues real-looking vouchers and remembers what it was asked for, so a
    test can inspect it afterwards — "exactly one voucher was issued" is an
    observable fact about the outside world, not an internal call order.
    Setting `failing` makes the supplier say no, which is the only way to
    reach spec D16 from the seam.
    """

    def __init__(self) -> None:
        self.issued: list[IssuanceRequest] = []
        self.failing = False

    def issue(self, request: IssuanceRequest) -> Voucher:
        if self.failing:
            raise VoucherIssuanceFailed("the supplier is down")
        self.issued.append(request)
        return Voucher(code=f"VCH-{len(self.issued):04d}")


@pytest.fixture
def voucher_issuer() -> FakeVoucherIssuer:
    """The outbound issuance port of spec D16, faked."""
    return FakeVoucherIssuer()


@pytest.fixture
def claims(ledger_conn: sqlite3.Connection) -> ClaimRecords:
    """The claim records, on the ledger's own connection.

    Same connection on purpose: a claim and the points it spends are written
    inside the one transaction the ledger opens.
    """
    return ClaimRecords(ledger_conn)


@pytest.fixture
def service(
    ledger: PointsLedger,
    clock: FixedClock,
    claims: ClaimRecords,
    voucher_issuer: FakeVoucherIssuer,
    deposit_ledger: DepositLedger,
) -> SavingStreakService:
    """The seam under test, with its collaborators injected (spec D42/D5)."""
    return SavingStreakService(
        ledger=ledger,
        clock=clock,
        claims=claims,
        voucher_issuer=voucher_issuer,
        deposit_ledger=deposit_ledger,
    )


@pytest.fixture
def client(service: SavingStreakService) -> Iterator[TestClient]:
    """The HTTP adapter in front of that same seam."""
    app = create_app()
    app.dependency_overrides[get_service] = lambda: service
    with TestClient(app) as test_client:
        yield test_client
