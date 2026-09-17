"""Demo selection and seeded history use the same service as real interactions."""

from datetime import timedelta
from decimal import Decimal

import pytest

from saving_streak.demo import directory, open_demo
from saving_streak.events import ClaimReward, DomainError, MoneyDeposited
from saving_streak.service import SavingStreakService


def test_demo_directory_contains_three_distinct_profiles():
    profiles = directory()
    assert len(profiles) == 3
    assert len({p["id"] for p in profiles}) == 3
    assert len({p["email"] for p in profiles}) == 3
    assert len({p["account_id"] for p in profiles}) == 3


def test_seeded_histories_show_savings_rewards_and_a_fresh_start(ledger_conn, clock, service):
    for profile in directory():
        open_demo(profile["email"], ledger_conn, clock.now())
    assert service.balance("demo-anke") == 1800
    assert service.deposit_standing("demo-anke").outstanding_eur == Decimal("1800")
    assert len(service.claims("demo-anke")) == 1
    assert service.balance("demo-bram") == 460
    assert service.deposit_standing("demo-bram").outstanding_eur == Decimal("425")
    assert service.balance("demo-lina") == 0
    assert service.deposit_standing("demo-lina").lots == []
    assert {m.reason.value for m in service.history("demo-anke")} == {"deposit", "claim", "expiry"}


def test_signing_in_again_preserves_spending_and_seed_dates(ledger_conn, clock, service):
    open_demo("anke@example.com", ledger_conn, clock.now())
    dates = [lot.deposited_at for lot in service.deposit_standing("demo-anke").lots]
    service.claim(ClaimReward("demo-anke", "charity-donation", "after-login"))
    clock.advance(timedelta(days=1))
    open_demo(" ANKE@EXAMPLE.COM ", ledger_conn, clock.now())
    assert service.balance("demo-anke") == 1790
    assert len(service.claims("demo-anke")) == 2
    assert [lot.deposited_at for lot in service.deposit_standing("demo-anke").lots] == dates


def test_fresh_profile_stays_populated_after_returning(ledger_conn, clock, service):
    profile = open_demo("lina@example.com", ledger_conn, clock.now())
    service.handle(MoneyDeposited(profile["id"], profile["account_id"], "mine", Decimal("75")))
    open_demo(profile["email"], ledger_conn, clock.now())
    assert service.balance(profile["id"]) == 75
    assert service.balance("demo-bram") == 0


def test_unknown_email_changes_nothing(ledger_conn, clock, service):
    with pytest.raises(DomainError, match="Choose a demo profile"):
        open_demo("unknown@example.com", ledger_conn, clock.now())
    assert ledger_conn.execute("SELECT count(*) FROM demo_seed_runs").fetchone()[0] == 0
    assert service.balance("demo-anke") == 0


def test_interrupted_seed_rolls_back_and_can_retry(ledger_conn, clock, service, monkeypatch):
    original = SavingStreakService.handle
    calls = 0

    def fail_second(self, event):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("interrupted")
        return original(self, event)

    with monkeypatch.context() as patch:
        patch.setattr(SavingStreakService, "handle", fail_second)
        with pytest.raises(RuntimeError, match="interrupted"):
            open_demo("anke@example.com", ledger_conn, clock.now())
    assert service.deposit_standing("demo-anke").lots == []
    assert ledger_conn.execute("SELECT count(*) FROM demo_seed_runs").fetchone()[0] == 0
    open_demo("anke@example.com", ledger_conn, clock.now())
    assert service.balance("demo-anke") == 1800


def test_demo_http_directory_and_email_login(client):
    response = client.get("/api/demo/customers")
    assert response.status_code == 200
    assert len(response.json()) == 3
    login = client.post("/api/demo/session", json={"email": " BRAM@EXAMPLE.COM "})
    assert login.status_code == 200
    assert login.json()["name"] == "Bram De Vos"
    assert (
        client.post("/api/demo/session", json={"email": "unknown@example.com"}).status_code == 400
    )
    assert client.post("/api/demo/session", json={"email": ""}).status_code == 422
