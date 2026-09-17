"""Claiming a reward from the catalogue, tested at the seam of spec D42.

Commands go in; the voucher, the balance, the history and the claim record
come out. Nothing here knows that claims are rows in SQLite, what a voucher
code looks like inside, or in what order the service calls its collaborators
(spec T1). The voucher issuer is a fake the test inspects afterwards, never a
mock with expectations on it (spec T7).
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from saving_streak.catalogue import Catalogue, CatalogueItem, current_catalogue
from saving_streak.events import (
    ClaimReward,
    DepositReversed,
    DomainError,
    MoneyDeposited,
    MovementReason,
)
from saving_streak.service import SavingStreakService
from saving_streak.vouchers import VoucherIssuanceFailed

CUSTOMER = "cust-alice"
OTHER_CUSTOMER = "cust-bob"

CINEMA = "cinema-ticket"
COFFEE = "coffee-or-snack-voucher"
CHARITY = "charity-donation"
FAMILY = "family-cinema-pack"


def fund(service: SavingStreakService, points: int, *, customer_id: str = CUSTOMER) -> None:
    """Put `points` on the balance the only way the domain allows: a deposit."""
    service.handle(
        MoneyDeposited(
            customer_id=customer_id,
            account_id="acc-savings",
            deposit_id=f"dep-{customer_id}-{points}",
            amount_eur=Decimal(points),
        )
    )


def claim(
    service: SavingStreakService,
    item_id: str,
    *,
    key: str = "key-1",
    customer_id: str = CUSTOMER,
):
    return service.claim(
        ClaimReward(customer_id=customer_id, item_id=item_id, idempotency_key=key)
    )


# ---------------------------------------------------------------- catalogue --


def test_the_catalogue_lists_the_four_rewards_with_their_prices(service):
    catalogue = service.catalogue()

    assert [(item.item_id, item.price_points) for item in catalogue.items] == [
        (CINEMA, 100),
        (COFFEE, 40),
        (CHARITY, 10),
        (FAMILY, 180),
    ]
    assert all(item.name for item in catalogue.items)


def test_the_catalogue_is_readable_as_versioned_data(service):
    """It carries the version it was published as (spec D12)."""
    assert service.catalogue().version == current_catalogue().version
    assert service.catalogue().version >= 1


def test_every_price_is_a_whole_number_of_points(service):
    """Points are integers everywhere; there is no fractional point (spec D4)."""
    for item in service.catalogue().items:
        assert isinstance(item.price_points, int)
        assert not isinstance(item.price_points, bool)


def test_a_catalogue_cannot_price_an_item_in_fractions():
    with pytest.raises(TypeError):
        CatalogueItem("half-a-coffee", "Half a coffee", 20.5)


# -------------------------------------------------------------- the claim ----


def test_claiming_an_affordable_item_deducts_its_price_and_issues_a_voucher(service):
    fund(service, 150)

    result = claim(service, CINEMA)

    assert result.item_name == "Cinema ticket"
    assert result.price_points == 100
    assert result.points_delta == -100
    assert result.balance == 50
    assert result.voucher_code
    assert service.balance(CUSTOMER) == 50


def test_the_voucher_comes_from_the_outbound_issuance_port(service, voucher_issuer):
    """Saving Streak does not mint vouchers; it asks the port (spec D16)."""
    fund(service, 100)

    result = claim(service, CINEMA)

    assert [request.item_id for request in voucher_issuer.issued] == [CINEMA]
    assert voucher_issuer.issued[0].price_points == 100
    assert voucher_issuer.issued[0].customer_id == CUSTOMER
    assert result.voucher_code == "VCH-0001"


def test_the_claim_is_readable_afterwards_with_the_voucher_it_issued(service):
    fund(service, 100)

    result = claim(service, CINEMA)
    (claimed,) = service.claims(CUSTOMER)

    assert claimed.item_id == CINEMA
    assert claimed.price_points == 100
    assert claimed.voucher_code == result.voucher_code


def test_the_claim_appears_in_the_history_as_a_claim(service):
    fund(service, 100)

    claim(service, CINEMA)
    newest, *_ = service.history(CUSTOMER)

    assert newest.reason is MovementReason.CLAIM
    assert newest.points == -100
    assert "Cinema ticket" in newest.description
    assert "100 points" in newest.description


def test_the_balance_stays_derived_from_the_ledger_after_a_claim(service):
    """Spec D7: no mutable balance field, before or after spending."""
    fund(service, 150)
    claim(service, CINEMA)

    assert service.balance(CUSTOMER) == sum(m.points for m in service.history(CUSTOMER))


def test_every_catalogue_item_can_be_claimed(service):
    fund(service, 330)

    for key, item_id in enumerate((CINEMA, COFFEE, CHARITY, FAMILY)):
        claim(service, item_id, key=f"key-{key}")

    assert service.balance(CUSTOMER) == 0
    assert [c.item_id for c in service.claims(CUSTOMER)] == [FAMILY, CHARITY, COFFEE, CINEMA]


def test_claiming_with_exactly_the_price_on_the_balance_is_allowed(service):
    fund(service, 100)

    assert claim(service, CINEMA).balance == 0


def test_an_item_the_catalogue_does_not_sell_is_refused(service, voucher_issuer):
    fund(service, 500)

    with pytest.raises(DomainError):
        claim(service, "a-pony")

    assert service.balance(CUSTOMER) == 500
    assert voucher_issuer.issued == []


# ------------------------------------------------------------- affordability -


def test_a_claim_the_customer_cannot_afford_is_refused_in_full(service, voucher_issuer):
    """No partial redemption, no paying the difference (spec D14)."""
    fund(service, 99)

    with pytest.raises(DomainError) as refusal:
        claim(service, CINEMA)

    assert "100" in str(refusal.value)
    assert service.balance(CUSTOMER) == 99
    assert service.claims(CUSTOMER) == []
    assert voucher_issuer.issued == []
    assert [m.reason for m in service.history(CUSTOMER)] == [MovementReason.DEPOSIT]


def test_an_empty_balance_cannot_claim_even_the_cheapest_item(service):
    with pytest.raises(DomainError):
        claim(service, CHARITY)

    assert service.balance(CUSTOMER) == 0


def test_a_refused_claim_never_leaves_a_negative_balance(service):
    fund(service, 30)

    for key, item_id in enumerate((CINEMA, COFFEE, FAMILY)):
        with pytest.raises(DomainError):
            claim(service, item_id, key=f"key-{key}")

    assert service.balance(CUSTOMER) == 30


def test_a_claim_is_refused_while_the_balance_is_negative_from_a_reversed_deposit(
    service, voucher_issuer
):
    """Spec D11: claiming is blocked until the balance recovers."""
    fund(service, 40)
    claim(service, COFFEE)
    service.handle(DepositReversed(customer_id=CUSTOMER, deposit_id=f"dep-{CUSTOMER}-40"))
    assert service.balance(CUSTOMER) == -40

    with pytest.raises(DomainError) as refusal:
        claim(service, CHARITY, key="key-2")

    assert "negative" in str(refusal.value)
    assert service.balance(CUSTOMER) == -40
    assert len(voucher_issuer.issued) == 1


def test_a_recovered_balance_can_claim_again(service):
    fund(service, 40)
    claim(service, COFFEE)
    service.handle(DepositReversed(customer_id=CUSTOMER, deposit_id=f"dep-{CUSTOMER}-40"))
    fund(service, 50)

    assert service.balance(CUSTOMER) == 10
    assert claim(service, CHARITY, key="key-2").balance == 0


# -------------------------------------------------------------- idempotency --


def test_replaying_an_idempotency_key_returns_the_original_voucher(service, voucher_issuer):
    """Spec D15/T5: exactly one voucher, one balance change."""
    fund(service, 150)

    first = claim(service, CINEMA, key="key-abc")
    replays = [claim(service, CINEMA, key="key-abc") for _ in range(3)]

    assert [r.voucher_code for r in replays] == [first.voucher_code] * 3
    assert [r.points_delta for r in replays] == [0, 0, 0]
    assert [r.replayed for r in replays] == [True, True, True]
    assert first.replayed is False
    assert service.balance(CUSTOMER) == 50
    assert len(voucher_issuer.issued) == 1
    assert len(service.claims(CUSTOMER)) == 1


def test_a_replay_deducts_nothing_even_when_the_balance_could_not_afford_it_again(service):
    """The replay is not a second claim, so affordability is not re-tested."""
    fund(service, 100)
    first = claim(service, CINEMA, key="key-abc")

    replay = claim(service, CINEMA, key="key-abc")

    assert replay.voucher_code == first.voucher_code
    assert service.balance(CUSTOMER) == 0


def test_a_second_claim_under_a_different_key_is_a_second_claim(service, voucher_issuer):
    fund(service, 200)

    first = claim(service, CINEMA, key="key-1")
    second = claim(service, CINEMA, key="key-2")

    assert first.voucher_code != second.voucher_code
    assert len(voucher_issuer.issued) == 2
    assert service.balance(CUSTOMER) == 0


def test_reusing_a_key_for_a_different_item_is_refused(service, voucher_issuer):
    fund(service, 200)
    claim(service, CINEMA, key="key-1")

    with pytest.raises(DomainError):
        claim(service, COFFEE, key="key-1")

    assert service.balance(CUSTOMER) == 100
    assert len(voucher_issuer.issued) == 1


def test_an_idempotency_key_belongs_to_the_customer_who_sent_it(service, voucher_issuer):
    fund(service, 100)
    fund(service, 100, customer_id=OTHER_CUSTOMER)

    alice = claim(service, CINEMA, key="shared-key")
    bob = claim(service, CINEMA, key="shared-key", customer_id=OTHER_CUSTOMER)

    assert alice.voucher_code != bob.voucher_code
    assert len(voucher_issuer.issued) == 2
    assert service.balance(CUSTOMER) == 0
    assert service.balance(OTHER_CUSTOMER) == 0


def test_a_padded_customer_id_is_the_same_customer_on_both_sides_of_the_seam(service):
    """One identifier rule, or the money and the claim are two customers.

    The idempotency key is trimmed so `"k1"` and `" k1"` are one key (spec
    D15). Every other identifier is trimmed with it, because they are matched
    against each other: a `customer_id` trimmed on the claim but not on the
    deposit would deposit to one customer and refuse the claim of another.
    """
    fund(service, 200, customer_id="  cust-padded  ")

    assert service.balance("cust-padded") == 200
    assert service.balance(" cust-padded ") == 200

    result = claim(service, CINEMA, key=" key-1 ", customer_id="cust-padded ")

    assert result.customer_id == "cust-padded"
    assert service.balance("cust-padded") == 100
    assert claim(service, CINEMA, key="key-1", customer_id=" cust-padded").replayed is True
    assert len(service.claims("cust-padded")) == 1


def test_a_core_banking_event_without_a_customer_is_refused(service):
    with pytest.raises(DomainError):
        MoneyDeposited(
            customer_id="  ",
            account_id="acc-savings",
            deposit_id="dep-1",
            amount_eur=Decimal(10),
        )
    with pytest.raises(DomainError):
        DepositReversed(customer_id="", deposit_id="dep-1")


def test_a_claim_needs_an_idempotency_key(service):
    fund(service, 100)

    with pytest.raises(DomainError):
        ClaimReward(customer_id=CUSTOMER, item_id=CINEMA, idempotency_key="")


# ---------------------------------------------------------- issuance failure -


def test_a_failed_issuance_deducts_nothing_and_fails_as_a_unit(service, voucher_issuer):
    """Spec D16: if issuance fails, the points are not deducted."""
    fund(service, 150)
    voucher_issuer.failing = True

    with pytest.raises(VoucherIssuanceFailed):
        claim(service, CINEMA)

    assert service.balance(CUSTOMER) == 150
    assert service.claims(CUSTOMER) == []
    assert [m.reason for m in service.history(CUSTOMER)] == [MovementReason.DEPOSIT]


def test_the_same_key_can_be_retried_once_the_supplier_recovers(service, voucher_issuer):
    fund(service, 150)
    voucher_issuer.failing = True
    with pytest.raises(VoucherIssuanceFailed):
        claim(service, CINEMA, key="key-retry")
    voucher_issuer.failing = False

    result = claim(service, CINEMA, key="key-retry")

    assert result.points_delta == -100
    assert service.balance(CUSTOMER) == 50
    assert len(service.claims(CUSTOMER)) == 1


def test_an_issuer_that_raises_something_else_still_fails_as_a_unit(
    ledger, clock, claims, deposit_ledger
):
    class ExplodingIssuer:
        def issue(self, request):
            raise RuntimeError("connection reset by peer")

    service = SavingStreakService(
        ledger=ledger,
        clock=clock,
        claims=claims,
        voucher_issuer=ExplodingIssuer(),
        deposit_ledger=deposit_ledger,
    )
    fund(service, 150)

    with pytest.raises(VoucherIssuanceFailed):
        claim(service, CINEMA)

    assert service.balance(CUSTOMER) == 150
    assert service.claims(CUSTOMER) == []


# ------------------------------------------------------------- price history -


def test_the_claim_records_the_price_it_was_claimed_at(
    ledger, clock, claims, voucher_issuer, deposit_ledger
):
    """A later catalogue version does not rewrite a claim already made (D12)."""
    today = SavingStreakService(
        ledger=ledger,
        clock=clock,
        claims=claims,
        voucher_issuer=voucher_issuer,
        deposit_ledger=deposit_ledger,
    )
    fund(today, 300)
    claim(today, CINEMA, key="key-1")

    dearer = Catalogue(
        version=current_catalogue().version + 1,
        items=(CatalogueItem(CINEMA, "Cinema ticket", 150),),
    )
    tomorrow = SavingStreakService(
        ledger=ledger,
        clock=clock,
        claims=claims,
        voucher_issuer=voucher_issuer,
        deposit_ledger=deposit_ledger,
        catalogue=dearer,
    )

    (already_claimed,) = tomorrow.claims(CUSTOMER)
    assert already_claimed.price_points == 100
    assert already_claimed.catalogue_version == current_catalogue().version
    assert tomorrow.catalogue().item(CINEMA).price_points == 150
    assert "100 points" in tomorrow.history(CUSTOMER)[0].description

    after = claim(tomorrow, CINEMA, key="key-2")
    assert after.price_points == 150
    assert after.catalogue_version == dearer.version
    assert tomorrow.balance(CUSTOMER) == 50


# -------------------------------------------------------------- no limits ----


def test_there_is_no_stock_limit_and_no_per_customer_claim_limit(service):
    """Spec D13. Twelve claims of the same item, as often as the balance allows."""
    fund(service, 120)

    for n in range(12):
        claim(service, CHARITY, key=f"key-{n}")

    assert service.balance(CUSTOMER) == 0
    assert len(service.claims(CUSTOMER)) == 12

    with pytest.raises(DomainError):
        claim(service, CHARITY, key="key-one-too-many")


def test_one_customers_claim_does_not_touch_anothers_balance(service):
    fund(service, 100)
    fund(service, 100, customer_id=OTHER_CUSTOMER)

    claim(service, CINEMA)

    assert service.balance(CUSTOMER) == 0
    assert service.balance(OTHER_CUSTOMER) == 100
    assert service.claims(OTHER_CUSTOMER) == []
