"""Funded demo commands preserve money and refuse overdrafts, even on retries."""

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import pytest

from saving_streak.banking import DemoBanking
from saving_streak.db import connection
from saving_streak.demo import open_demo
from saving_streak.events import DomainError


@pytest.fixture
def bank(ledger_conn, clock):
    open_demo("lina@example.com", ledger_conn, clock.now())
    return DemoBanking(ledger_conn, clock)


def transfer(bank, amount, direction="deposit", reference="first", account="savings-lina"):
    return bank.transfer("demo-lina", account, reference, direction, Decimal(amount))


def test_money_moves_between_accounts_and_total_is_preserved(bank):
    assert bank.accounts("demo-lina")["total_eur"] == Decimal("2500")
    transfer(bank, "150.99")
    a = bank.accounts("demo-lina")
    assert (a["savings_eur"], a["available_eur"], a["total_eur"]) == (
        Decimal("150.99"),
        Decimal("2349.01"),
        Decimal("2500"),
    )
    transfer(bank, "150.99", "withdrawal", "second")
    a = bank.accounts("demo-lina")
    assert (a["savings_eur"], a["available_eur"]) == (0, Decimal("2500"))
    assert bank.service.balance("demo-lina") == 150


def test_exhausting_each_source_refuses_more_without_changing_money_or_points(bank):
    with pytest.raises(DomainError, match="Insufficient funds"):
        transfer(bank, "0.01", "withdrawal")
    transfer(bank, "2500")
    before = bank.accounts("demo-lina")
    with pytest.raises(DomainError, match="Insufficient funds"):
        transfer(bank, "0.01", reference="over")
    with pytest.raises(DomainError, match="Insufficient funds"):
        transfer(bank, "2500.01", "withdrawal", "over-withdraw")
    assert bank.accounts("demo-lina") == before
    assert bank.service.balance("demo-lina") == 2500


def test_retries_are_idempotent_even_when_source_is_empty(bank):
    transfer(bank, "2500")
    assert transfer(bank, "2500")["replayed"] is True
    assert bank.accounts("demo-lina")["savings_eur"] == 2500
    with pytest.raises(DomainError, match="reference"):
        transfer(bank, "2499")
    transfer(bank, "2500", "withdrawal", "out")
    assert transfer(bank, "2500", "withdrawal", "out")["replayed"] is True
    assert bank.accounts("demo-lina")["available_eur"] == 2500


@pytest.mark.parametrize("amount", ["0", "-1", "0.001", "1.999", "NaN", "Infinity"])
def test_invalid_money_is_rejected(bank, amount):
    with pytest.raises(DomainError):
        transfer(bank, amount)
    assert bank.accounts("demo-lina")["total_eur"] == 2500
    assert bank.service.balance("demo-lina") == 0


def test_account_ownership_and_unknown_customer(bank):
    with pytest.raises(DomainError, match="does not belong"):
        transfer(bank, "1", account="savings-anke")
    with pytest.raises(DomainError, match="Sign in"):
        bank.accounts("missing")


def test_relogin_and_new_connection_preserve_funds(bank, ledger_conn, clock, db_file):
    transfer(bank, "50")
    open_demo("lina@example.com", ledger_conn, clock.now())
    with connection(db_file) as conn:
        a = DemoBanking(conn, clock).accounts("demo-lina")
        assert a["available_eur"] == 2450
        assert a["savings_eur"] == 50


def test_existing_profile_gets_funding_without_resetting_savings(ledger_conn, clock):
    open_demo("anke@example.com", ledger_conn, clock.now())
    bank = DemoBanking(ledger_conn, clock)
    assert bank.accounts("demo-anke")["total_eur"] == 4300
    assert bank.accounts("demo-anke")["savings_eur"] == 1800


def test_concurrent_transfers_cannot_overdraw(bank, db_file, clock):
    def run(reference):
        with connection(db_file) as conn:
            try:
                transfer(DemoBanking(conn, clock), "2000", reference=reference)
                return "accepted"
            except DomainError:
                return "refused"

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(run, ["one", "two"])) == ["accepted", "refused"]
    a = bank.accounts("demo-lina")
    assert (a["available_eur"], a["savings_eur"]) == (500, 2000)


def test_failed_event_rolls_back_transfer_and_can_retry(bank, monkeypatch):
    original = bank.service.handle

    def fail(event):
        original(event)
        raise RuntimeError("interrupted after ledger write")

    with monkeypatch.context() as patch:
        patch.setattr(bank.service, "handle", fail)
        with pytest.raises(RuntimeError):
            transfer(bank, "50")
    assert bank.accounts("demo-lina")["savings_eur"] == 0
    assert bank.service.balance("demo-lina") == 0
    transfer(bank, "50")
    assert bank.accounts("demo-lina")["savings_eur"] == 50


def test_http_checks_limits_precision_and_ownership(client):
    client.post("/api/demo/session", json={"email": "lina@example.com"})
    body = dict(
        customer_id="demo-lina",
        account_id="savings-lina",
        transfer_id="http",
        direction="deposit",
        amount_eur="2500.01",
    )
    assert client.post("/api/demo/transfers", json=body).status_code == 400
    response = client.post("/api/demo/transfers", json={**body, "amount_eur": "1.001"})
    assert response.status_code == 422
    response = client.post(
        "/api/demo/transfers", json={**body, "amount_eur": "1", "account_id": "savings-anke"}
    )
    assert response.status_code == 400
    response = client.post("/api/demo/transfers", json={**body, "amount_eur": "2500"})
    assert response.status_code == 200
    response = client.get("/api/demo/customers/demo-lina/accounts")
    assert response.status_code == 200
    assert Decimal(str(response.json()["available_eur"])) == 0
