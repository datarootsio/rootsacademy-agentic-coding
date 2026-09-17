"""The SQLite adapter, not the domain.

Two things live here that are not domain rules and so do not belong at the
seam (spec T1): what happens when several connections hit the same file at
once, and the fact that the derived balance is a plain sum with no floor under
it. Domain behaviour is asserted in `test_earning_points.py`.
"""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from fastapi.testclient import TestClient

from saving_streak.api import create_app
from saving_streak.clock import in_brussels
from saving_streak.db import connect
from saving_streak.events import MovementReason
from saving_streak.ledger import PointsLedger
from saving_streak.migrations import migrate
from saving_streak.settings import DB_PATH_ENV

CONCURRENCY = 6

#: The ledger is read *at an instant*: a lot past its twelfth month is not in
#: the balance (spec D18). Pinned, so this file behaves the same in every month
#: of the year (spec T2).
READ_AT = in_brussels(datetime(2026, 3, 14, 10, 30))

DEPOSIT = {
    "customer_id": "cust-alice",
    "account_id": "acc-1",
    "deposit_id": "dep-1",
    "amount_eur": "30",
}
REVERSAL = {"customer_id": "cust-alice", "deposit_id": "dep-1"}
WITHDRAWAL = {
    "customer_id": "cust-alice",
    "account_id": "acc-1",
    "withdrawal_id": "wd-1",
    "amount_eur": "30",
}


def test_connections_opened_at_once_against_a_migrated_file_all_work(tmp_path: Path):
    """The UI reads balance and history together, so connections overlap."""
    path = tmp_path / "saving-streak.db"
    migrate(path)
    ready = threading.Barrier(CONCURRENCY)

    def read_balance() -> int:
        ready.wait(timeout=10)
        conn = connect(path)
        try:
            return PointsLedger(conn).balance("cust-alice", READ_AT)
        finally:
            conn.close()

    with ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
        results = [f.result() for f in [pool.submit(read_balance) for _ in range(CONCURRENCY)]]

    assert results == [0] * CONCURRENCY


def test_the_api_survives_the_uis_parallel_balance_and_history_reads(tmp_path, monkeypatch):
    monkeypatch.setenv(DB_PATH_ENV, str(tmp_path / "saving-streak.db"))
    paths = [
        "/api/customers/cust-alice/points/balance",
        "/api/customers/cust-alice/points/history",
    ] * CONCURRENCY

    with TestClient(create_app()) as client:
        with ThreadPoolExecutor(max_workers=len(paths)) as pool:
            responses = [f.result() for f in [pool.submit(client.get, p) for p in paths]]

    assert [r.status_code for r in responses] == [200] * len(paths)


def test_reversals_arriving_at_the_same_moment_claw_back_once(tmp_path, monkeypatch):
    """At-least-once delivery redelivers to whichever worker is free.

    Each request gets its own connection, so "has this deposit already been
    reversed?" and the clawback that follows have to be one unit or every
    racing redelivery reads the same un-reversed ledger.
    """
    monkeypatch.setenv(DB_PATH_ENV, str(tmp_path / "saving-streak.db"))

    with TestClient(create_app()) as client:
        client.post("/api/events/money-deposited", json=DEPOSIT)
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = [
                pool.submit(client.post, "/api/events/deposit-reversed", json=REVERSAL)
                for _ in range(4)
            ]
            statuses = [f.result().status_code for f in futures]
        balance = client.get("/api/customers/cust-alice/points/balance").json()["balance"]

    assert statuses == [200] * 4
    assert balance == 0


def test_deposits_arriving_at_the_same_moment_credit_once(tmp_path, monkeypatch):
    monkeypatch.setenv(DB_PATH_ENV, str(tmp_path / "saving-streak.db"))

    with TestClient(create_app()) as client:
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = [
                pool.submit(client.post, "/api/events/money-deposited", json=DEPOSIT)
                for _ in range(4)
            ]
            statuses = [f.result().status_code for f in futures]
        balance = client.get("/api/customers/cust-alice/points/balance").json()["balance"]

    assert statuses == [200] * 4
    assert balance == 30


def test_a_deposit_racing_its_own_reversal_nets_to_zero(tmp_path, monkeypatch):
    """The two events are commutative, not merely atomic one at a time.

    At-least-once delivery says nothing about order, and two workers can take
    the deposit and its reversal at the same moment. Whichever commits first,
    the pair has to settle at zero: if the reversal wins, the deposit finds it
    cancelled; if the deposit wins, the reversal finds points to claw back.
    """
    monkeypatch.setenv(DB_PATH_ENV, str(tmp_path / "saving-streak.db"))
    balances = []

    with TestClient(create_app()) as client:
        for n in range(8):
            customer = f"cust-race-{n}"
            deposit = dict(DEPOSIT, customer_id=customer)
            reversal = dict(REVERSAL, customer_id=customer)
            ready = threading.Barrier(2)

            def post(path, body, ready=ready):
                ready.wait(timeout=10)
                return client.post(path, json=body)

            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [
                    pool.submit(post, "/api/events/money-deposited", deposit),
                    pool.submit(post, "/api/events/deposit-reversed", reversal),
                ]
                assert [f.result().status_code for f in futures] == [200, 200]
            balances.append(
                client.get(f"/api/customers/{customer}/points/balance").json()["balance"]
            )

    assert balances == [0] * 8


def test_the_derived_balance_is_never_floored_at_zero(tmp_path: Path):
    """Spec D7/D11: the balance is `SUM(points)`, and the sum may be negative.

    The storage is where a clamp would have to be written, so this is where
    its absence is checked: a consumption larger than everything credited
    comes back negative. Ticket 01 cannot reach that position through the seam
    — every clawback is exactly its own deposit — so the consumption is
    arranged as the claim it would be (ticket 02).
    """
    path = tmp_path / "saving-streak.db"
    migrate(path)
    conn = connect(path)
    stamp = READ_AT
    try:
        ledger = PointsLedger(conn)
        ledger.append(
            customer_id="cust-alice",
            occurred_at=stamp,
            points=10,
            reason=MovementReason.DEPOSIT,
            description="Deposit of €10.00 into account acc-1",
        )
        ledger.append(
            customer_id="cust-alice",
            occurred_at=stamp,
            points=-30,
            reason=MovementReason.CLAIM,
            description="Claimed a €30 voucher",
        )

        assert ledger.balance("cust-alice", READ_AT) == -20
    finally:
        conn.close()


def test_points_survive_a_restart(tmp_path, monkeypatch):
    monkeypatch.setenv(DB_PATH_ENV, str(tmp_path / "saving-streak.db"))
    with TestClient(create_app()) as first:
        first.post(
            "/api/events/money-deposited",
            json={
                "customer_id": "cust-alice",
                "account_id": "acc-1",
                "deposit_id": "dep-1",
                "amount_eur": "10.99",
            },
        )

    with TestClient(create_app()) as second:
        assert second.get("/api/customers/cust-alice/points/balance").json()["balance"] == 10


def test_a_double_submitted_claim_issues_exactly_one_voucher(tmp_path, monkeypatch):
    """Spec D15: a flaky connection must not cost the customer 100 points.

    Four identical claims at once, on four connections, against a balance that
    can only afford one. Each request reads "has this key already claimed?"
    and then deducts, so the pair has to be one unit or every racing
    submission finds the same un-spent balance.
    """
    monkeypatch.setenv(DB_PATH_ENV, str(tmp_path / "saving-streak.db"))
    claim = {
        "customer_id": "cust-alice",
        "item_id": "cinema-ticket",
        "idempotency_key": "key-double-click",
    }

    with TestClient(create_app()) as client:
        client.post("/api/events/money-deposited", json=dict(DEPOSIT, amount_eur="100"))
        ready = threading.Barrier(4)

        def submit():
            ready.wait(timeout=10)
            return client.post("/api/claims", json=claim)

        with ThreadPoolExecutor(max_workers=4) as pool:
            responses = [f.result() for f in [pool.submit(submit) for _ in range(4)]]
        balance = client.get("/api/customers/cust-alice/points/balance").json()["balance"]
        claims = client.get("/api/customers/cust-alice/claims").json()["claims"]

    assert [r.status_code for r in responses] == [200] * 4
    assert len({r.json()["voucher_code"] for r in responses}) == 1
    assert sum(r.json()["points_delta"] for r in responses) == -100
    assert len(claims) == 1
    assert balance == 0


def test_claims_racing_for_the_last_points_do_not_overdraw(tmp_path, monkeypatch):
    """Different keys, so four genuine claims — and only one is affordable."""
    monkeypatch.setenv(DB_PATH_ENV, str(tmp_path / "saving-streak.db"))

    with TestClient(create_app()) as client:
        client.post("/api/events/money-deposited", json=dict(DEPOSIT, amount_eur="100"))
        ready = threading.Barrier(4)

        def submit(n):
            ready.wait(timeout=10)
            return client.post(
                "/api/claims",
                json={
                    "customer_id": "cust-alice",
                    "item_id": "cinema-ticket",
                    "idempotency_key": f"key-{n}",
                },
            )

        with ThreadPoolExecutor(max_workers=4) as pool:
            responses = [f.result() for f in [pool.submit(submit, n) for n in range(4)]]
        balance = client.get("/api/customers/cust-alice/points/balance").json()["balance"]
        claims = client.get("/api/customers/cust-alice/claims").json()["claims"]

    assert sorted(r.status_code for r in responses) == [200, 400, 400, 400]
    assert len(claims) == 1
    assert balance == 0


def test_claims_survive_a_restart(tmp_path, monkeypatch):
    monkeypatch.setenv(DB_PATH_ENV, str(tmp_path / "saving-streak.db"))
    with TestClient(create_app()) as first:
        first.post("/api/events/money-deposited", json=dict(DEPOSIT, amount_eur="100"))
        issued = first.post(
            "/api/claims",
            json={
                "customer_id": "cust-alice",
                "item_id": "cinema-ticket",
                "idempotency_key": "key-1",
            },
        ).json()

    with TestClient(create_app()) as second:
        assert second.get("/api/customers/cust-alice/points/balance").json()["balance"] == 0
        (claim,) = second.get("/api/customers/cust-alice/claims").json()["claims"]
        assert claim["voucher_code"] == issued["voucher_code"]
        # And the key still belongs to that claim after a restart.
        replay = second.post(
            "/api/claims",
            json={
                "customer_id": "cust-alice",
                "item_id": "cinema-ticket",
                "idempotency_key": "key-1",
            },
        ).json()
        assert replay["voucher_code"] == issued["voucher_code"]
        assert replay["points_delta"] == 0


def test_deposit_lots_survive_a_restart(tmp_path, monkeypatch):
    """The money side is a second table on the same file (spec D6).

    What is outstanding is derived by replaying that table, so a restart has
    to find the entries a withdrawal left behind, not a number it cached. The
    anniversary is not asserted here — it hangs off the real clock, and this
    file says nothing about what month it is run in (spec T2).
    """
    monkeypatch.setenv(DB_PATH_ENV, str(tmp_path / "saving-streak.db"))
    with TestClient(create_app()) as first:
        first.post("/api/events/money-deposited", json=dict(DEPOSIT, amount_eur="100"))
        first.post("/api/events/money-withdrawn", json=WITHDRAWAL)

    with TestClient(create_app()) as second:
        body = second.get("/api/customers/cust-alice/deposit-lots").json()

    assert body["outstanding_eur"] == "70.00"
    (lot,) = body["lots"]
    assert (lot["amount_eur"], lot["outstanding_eur"]) == ("100.00", "70.00")
    assert lot["next_anniversary"]


def test_withdrawals_arriving_at_the_same_moment_consume_once(tmp_path, monkeypatch):
    """The money side has its own at-least-once guard, on its own ledger.

    Core banking redelivers to whichever worker is free, and each request gets
    its own connection: "has this withdrawal already been recorded?" and the
    entry that follows have to be one unit, or four redeliveries of one €30
    withdrawal take €120 out of the customer's deposit lots.
    """
    monkeypatch.setenv(DB_PATH_ENV, str(tmp_path / "saving-streak.db"))

    with TestClient(create_app()) as client:
        client.post("/api/events/money-deposited", json=dict(DEPOSIT, amount_eur="100"))
        ready = threading.Barrier(4)

        def submit():
            ready.wait(timeout=10)
            return client.post("/api/events/money-withdrawn", json=WITHDRAWAL)

        with ThreadPoolExecutor(max_workers=4) as pool:
            statuses = [f.result().status_code for f in [pool.submit(submit) for _ in range(4)]]
        outstanding = client.get("/api/customers/cust-alice/deposit-lots").json()
        balance = client.get("/api/customers/cust-alice/points/balance").json()["balance"]

    assert statuses == [200] * 4
    assert outstanding["outstanding_eur"] == "70.00"
    # And none of it reached the points side (spec D10).
    assert balance == 100
