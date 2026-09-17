"""The base mechanic, tested at the seam of spec D42 (spec T1).

Events go in; balances and history come out. Nothing here knows that the
ledger is SQLite, what a lot identifier looks like, or in what order the
service calls its collaborators — those are exactly the details the exercises
will refactor.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest

from conftest import PINNED_NOW
from saving_streak.events import (
    ClaimReward,
    DepositReversed,
    DepositSource,
    DomainError,
    MoneyDeposited,
    MoneyWithdrawn,
    MovementReason,
)

CUSTOMER = "cust-alice"
OTHER_CUSTOMER = "cust-bob"


def deposit(
    service,
    *,
    amount: str,
    deposit_id: str = "dep-1",
    account_id: str = "acc-1",
    customer_id: str = CUSTOMER,
    source: DepositSource = DepositSource.EXTERNAL,
):
    return service.handle(
        MoneyDeposited(
            customer_id=customer_id,
            account_id=account_id,
            deposit_id=deposit_id,
            amount_eur=Decimal(amount),
            source=source,
        )
    )


# ------------------------------------------------------- earning on deposit --


def test_a_ten_euro_deposit_credits_ten_points_immediately(service):
    result = deposit(service, amount="10")

    assert result.points_delta == 10
    assert result.balance == 10
    # Immediately: readable straight after the event, with no sweep in between.
    assert service.balance(CUSTOMER) == 10


@pytest.mark.parametrize(
    ("amount", "expected_points"),
    [
        ("10", 10),
        ("10.99", 10),
        ("0.99", 0),
        ("1.00", 1),
        ("99.999", 99),
        ("2500.50", 2500),
    ],
)
def test_deposit_amounts_floor_to_whole_euros(service, amount, expected_points):
    result = deposit(service, amount=amount)

    assert result.balance == expected_points
    assert isinstance(result.balance, int)


def test_no_deposit_ever_produces_a_fractional_point(service):
    deposit(service, amount="10.99", deposit_id="dep-1")
    deposit(service, amount="0.50", deposit_id="dep-2")
    deposit(service, amount="3.33", deposit_id="dep-3")

    assert service.balance(CUSTOMER) == 13
    assert all(isinstance(m.points, int) for m in service.history(CUSTOMER))


def test_a_deposit_too_small_to_earn_a_point_credits_nothing(service):
    result = deposit(service, amount="0.99")

    assert result.points_delta == 0
    assert service.balance(CUSTOMER) == 0


def test_a_deposit_must_be_a_positive_amount(service):
    with pytest.raises(DomainError):
        deposit(service, amount="0")
    with pytest.raises(DomainError):
        deposit(service, amount="-10")


def test_an_amount_too_large_to_be_a_deposit_is_refused_not_crashed(service):
    """A number the storage cannot hold is a refused event, not a stack trace."""
    with pytest.raises(DomainError):
        deposit(service, amount="1e19")

    assert service.balance(CUSTOMER) == 0


def test_an_amount_too_large_to_be_a_withdrawal_is_refused_not_crashed(service):
    """The ceiling guards every amount that reaches a ledger — now both.

    This test used to assert the opposite, on the premise that a withdrawal
    "never becomes points and never reaches the ledger". Deposit lots falsified
    that premise: a withdrawal's amount is now written to the deposit-lot
    ledger in cents and consumes lots by it, so a number no row could hold is
    refused at the edge of the domain instead of raising out of the seam as
    something that is not a `DomainError`.
    """
    deposit(service, amount="100")

    with pytest.raises(DomainError):
        service.handle(
            MoneyWithdrawn(
                customer_id=CUSTOMER,
                account_id="acc-1",
                withdrawal_id="wd-1",
                amount_eur=Decimal("1e19"),
            )
        )

    assert service.balance(CUSTOMER) == 100


def test_a_withdrawal_far_larger_than_the_balance_is_still_accepted(service):
    """Refusing an amount is about storage, never about the money (spec D1).

    Anything the ledger can hold is taken as core banking sends it, however
    much larger than what this system has ever seen. It costs no base points
    (spec D10) either way.
    """
    deposit(service, amount="100")

    result = service.handle(
        MoneyWithdrawn(
            customer_id=CUSTOMER,
            account_id="acc-1",
            withdrawal_id="wd-1",
            amount_eur=Decimal("1000000000"),
        )
    )

    assert result.points_delta == 0
    assert service.balance(CUSTOMER) == 100


# -------------------------------------------------- one balance per customer --


def test_deposits_into_two_accounts_land_in_one_balance(service):
    deposit(service, amount="10", deposit_id="dep-1", account_id="acc-savings")
    deposit(service, amount="25", deposit_id="dep-2", account_id="acc-holiday")

    assert service.balance(CUSTOMER) == 35


def test_one_customers_deposits_do_not_touch_anothers_balance(service):
    deposit(service, amount="10", deposit_id="dep-1")
    deposit(service, amount="40", deposit_id="dep-2", customer_id=OTHER_CUSTOMER)

    assert service.balance(CUSTOMER) == 10
    assert service.balance(OTHER_CUSTOMER) == 40


def test_an_unknown_customer_has_an_empty_balance_and_history(service):
    assert service.balance("cust-nobody") == 0
    assert service.history("cust-nobody") == []


# ------------------------------------------------- only external money earns --


@pytest.mark.parametrize(
    "source",
    [DepositSource.INTEREST, DepositSource.INTERNAL_TRANSFER, DepositSource.REFUND],
)
def test_money_that_is_not_an_external_credit_earns_nothing(service, source):
    result = deposit(service, amount="100", source=source)

    assert result.points_delta == 0
    assert service.balance(CUSTOMER) == 0
    assert service.history(CUSTOMER) == []


def test_an_interest_credit_does_not_dilute_an_earned_balance(service):
    deposit(service, amount="10", deposit_id="dep-1")
    deposit(service, amount="500", deposit_id="dep-interest", source=DepositSource.INTEREST)

    assert service.balance(CUSTOMER) == 10


# ------------------------------------------------------------- withdrawals --


def test_a_withdrawal_does_not_reduce_the_points_balance(service):
    deposit(service, amount="100")

    result = service.handle(
        MoneyWithdrawn(
            customer_id=CUSTOMER,
            account_id="acc-1",
            withdrawal_id="wd-1",
            amount_eur=Decimal("80"),
        )
    )

    assert result.points_delta == 0
    assert service.balance(CUSTOMER) == 100


def test_a_withdrawal_leaves_no_points_movement_behind(service):
    deposit(service, amount="100")
    service.handle(
        MoneyWithdrawn(
            customer_id=CUSTOMER,
            account_id="acc-1",
            withdrawal_id="wd-1",
            amount_eur=Decimal("100"),
        )
    )

    reasons = [m.reason for m in service.history(CUSTOMER)]
    assert reasons == [MovementReason.DEPOSIT]


# -------------------------------------------------------- reversed deposits --


def test_a_reversed_deposit_claws_back_exactly_what_it_credited(service):
    deposit(service, amount="10.99", deposit_id="dep-1")
    deposit(service, amount="40", deposit_id="dep-2")

    result = service.handle(DepositReversed(customer_id=CUSTOMER, deposit_id="dep-1"))

    assert result.points_delta == -10
    assert service.balance(CUSTOMER) == 40


def test_a_redelivered_reversal_claws_back_nothing_more(service):
    """Core banking's feed is at-least-once (spec D1).

    "Exactly the points that deposit credited" is a total, not a rate: however
    many times the reversal arrives, one deposit is clawed back one time.
    """
    deposit(service, amount="30", deposit_id="dep-1")
    service.handle(DepositReversed(customer_id=CUSTOMER, deposit_id="dep-1"))

    result = service.handle(DepositReversed(customer_id=CUSTOMER, deposit_id="dep-1"))

    assert result.points_delta == 0
    assert result.balance == 0
    assert service.balance(CUSTOMER) == 0


def test_a_deposit_and_its_reversal_net_to_zero_however_often_they_arrive(service):
    for _ in range(3):
        deposit(service, amount="30", deposit_id="dep-1")
    for _ in range(4):
        service.handle(DepositReversed(customer_id=CUSTOMER, deposit_id="dep-1"))

    assert service.balance(CUSTOMER) == 0


def test_a_reversal_that_arrives_before_its_deposit_leaves_no_points_behind(service):
    """Core banking's feed is at-least-once, and unordered with it (spec D1).

    A reversal can reach the seam before the deposit it cancels. The deposit
    that follows is money that never really arrived, so it must not leave
    points behind (spec D11) — whichever order the two turn up in.
    """
    reversal = service.handle(DepositReversed(customer_id=CUSTOMER, deposit_id="dep-1"))
    late = deposit(service, amount="30", deposit_id="dep-1")

    assert (reversal.points_delta, late.points_delta) == (0, 0)
    assert service.balance(CUSTOMER) == 0


def test_a_deposit_cancelled_before_it_arrived_stays_cancelled(service):
    """Redelivery of the deposit does not resurrect it either."""
    service.handle(DepositReversed(customer_id=CUSTOMER, deposit_id="dep-1"))
    for _ in range(3):
        deposit(service, amount="30", deposit_id="dep-1")
    service.handle(DepositReversed(customer_id=CUSTOMER, deposit_id="dep-1"))

    assert service.balance(CUSTOMER) == 0


def test_a_reversal_that_arrives_first_does_not_cancel_the_customers_other_deposits(service):
    deposit(service, amount="40", deposit_id="dep-2")

    service.handle(DepositReversed(customer_id=CUSTOMER, deposit_id="dep-1"))
    deposit(service, amount="30", deposit_id="dep-1")

    assert service.balance(CUSTOMER) == 40


def test_a_redelivered_deposit_credits_its_points_only_once(service):
    first = deposit(service, amount="10", deposit_id="dep-1")
    second = deposit(service, amount="10", deposit_id="dep-1")

    assert (first.points_delta, second.points_delta) == (10, 0)
    assert service.balance(CUSTOMER) == 10


def test_the_same_deposit_id_for_two_customers_is_two_deposits(service):
    deposit(service, amount="10", deposit_id="shared")
    deposit(service, amount="70", deposit_id="shared", customer_id=OTHER_CUSTOMER)

    service.handle(DepositReversed(customer_id=CUSTOMER, deposit_id="shared"))

    assert service.balance(CUSTOMER) == 0
    assert service.balance(OTHER_CUSTOMER) == 70


def test_a_clawback_is_not_clamped_by_the_balance_it_lands_on(service):
    """The balance may go negative (spec D11): nothing floors it.

    A deposit credits `+n` and its one clawback takes exactly `-n`, so a
    deposit alone can never take the sum below zero. What leaves a balance too
    small for a clawback to fit is the customer having *spent* it — so they
    spend it, on a real claim through the seam (ticket 02), and then the
    money behind one of the deposits bounces: 45 points earned, 40 spent on a
    coffee voucher, and a deposit of 30 reversed leaves the customer owing 25.
    """
    deposit(service, amount="30", deposit_id="dep-1")
    deposit(service, amount="15", deposit_id="dep-2")
    service.claim(
        ClaimReward(
            customer_id=CUSTOMER,
            item_id="coffee-or-snack-voucher",
            idempotency_key="key-coffee",
        )
    )

    result = service.handle(DepositReversed(customer_id=CUSTOMER, deposit_id="dep-1"))

    assert result.points_delta == -30
    assert result.balance == -25
    assert service.balance(CUSTOMER) == -25


def test_reversing_a_deposit_that_earned_nothing_claws_back_nothing(service):
    deposit(service, amount="500", deposit_id="dep-interest", source=DepositSource.INTEREST)
    deposit(service, amount="40", deposit_id="dep-1")

    result = service.handle(DepositReversed(customer_id=CUSTOMER, deposit_id="dep-interest"))

    assert result.points_delta == 0
    assert service.balance(CUSTOMER) == 40


def test_a_reversal_of_a_deposit_that_earned_nothing_is_still_recorded(service):
    """Zero points moved, but the deposit is cancelled, and that is a fact.

    It is also what stops a redelivery of the same deposit — an interest
    credit reclassified as an external one, say — earning after the fact.
    """
    service.handle(DepositReversed(customer_id=CUSTOMER, deposit_id="dep-interest"))

    (movement,) = service.history(CUSTOMER)

    assert movement.points == 0
    assert movement.reason is MovementReason.DEPOSIT_REVERSAL
    assert service.balance(CUSTOMER) == 0


def test_a_reversal_only_touches_the_customer_whose_deposit_it_was(service):
    deposit(service, amount="10", deposit_id="dep-1")
    deposit(service, amount="10", deposit_id="dep-2", customer_id=OTHER_CUSTOMER)

    service.handle(DepositReversed(customer_id=CUSTOMER, deposit_id="dep-1"))

    assert service.balance(CUSTOMER) == 0
    assert service.balance(OTHER_CUSTOMER) == 10


# ----------------------------------------------------- balance is derived ----


def test_the_balance_is_always_the_sum_of_the_history(service):
    deposit(service, amount="10.99", deposit_id="dep-1")
    deposit(service, amount="40", deposit_id="dep-2", account_id="acc-2")
    deposit(service, amount="500", deposit_id="dep-interest", source=DepositSource.INTEREST)
    service.handle(
        MoneyWithdrawn(
            customer_id=CUSTOMER,
            account_id="acc-1",
            withdrawal_id="wd-1",
            amount_eur=Decimal("50"),
        )
    )
    service.handle(DepositReversed(customer_id=CUSTOMER, deposit_id="dep-2"))

    movements = service.history(CUSTOMER)

    assert service.balance(CUSTOMER) == sum(m.points for m in movements)
    assert service.balance(CUSTOMER) == 10


def test_a_negative_balance_is_read_back_as_it_is(service):
    """Read back through the seam, not clamped on the way out.

    The spend is a real claim: 10 points earned and kept, 10 more earned and
    spent on a charity donation, and then the deposit behind the spent points
    bounces.
    """
    deposit(service, amount="10", deposit_id="dep-1")
    deposit(service, amount="10", deposit_id="dep-2")
    service.claim(
        ClaimReward(
            customer_id=CUSTOMER,
            item_id="charity-donation",
            idempotency_key="key-charity",
        )
    )
    service.handle(DepositReversed(customer_id=CUSTOMER, deposit_id="dep-1"))
    service.handle(DepositReversed(customer_id=CUSTOMER, deposit_id="dep-2"))

    assert service.balance(CUSTOMER) == -10
    assert [m.points for m in service.history(CUSTOMER)] == [-10, -10, -10, 10, 10]


# ------------------------------------------------------------------ history --


def test_the_history_is_newest_by_when_it_happened_not_by_when_it_was_written(service, clock):
    """"Newest first" is the clock's order, not the insertion order.

    Under the real clock the two agree, so this only bites once something
    stamps a movement for a date that has already passed — the sweep of spec
    D20 catching up missed business dates in order is exactly that. The clock
    is the seam's, so the test moves the clock rather than the rows.
    """
    deposit(service, amount="10", deposit_id="dep-today")
    clock.set(PINNED_NOW - timedelta(days=2))
    deposit(service, amount="40", deposit_id="dep-backdated")

    assert [m.points for m in service.history(CUSTOMER)] == [10, 40]


def test_a_movement_at_the_same_instant_reads_in_the_order_it_was_written(service):
    """Two stamps that tie fall back on insertion order, newest first.

    A claim and the deposit that funded it can share an instant; the claim is
    still the later of the two.
    """
    deposit(service, amount="10", deposit_id="dep-1")
    service.claim(
        ClaimReward(
            customer_id=CUSTOMER,
            item_id="charity-donation",
            idempotency_key="key-charity",
        )
    )

    assert [m.points for m in service.history(CUSTOMER)] == [-10, 10]


def test_the_history_names_every_movement_and_its_reason(service):
    deposit(service, amount="10.99", deposit_id="dep-1", account_id="acc-savings")
    deposit(service, amount="40", deposit_id="dep-2", account_id="acc-holiday")
    service.handle(DepositReversed(customer_id=CUSTOMER, deposit_id="dep-1"))

    movements = service.history(CUSTOMER)

    assert [(m.points, m.reason) for m in movements] == [
        (-10, MovementReason.DEPOSIT_REVERSAL),
        (40, MovementReason.DEPOSIT),
        (10, MovementReason.DEPOSIT),
    ]
    # The clawback says which money bounced, in the customer's own terms.
    assert "€10.99" in movements[0].description
    assert "acc-savings" in movements[0].description
    assert "acc-holiday" in movements[1].description


def test_the_history_line_states_the_amount_the_points_came_from(service):
    """Spec user story 5: the customer reads the history to check the number.

    99 points next to "EUR 100.00" is the one line they cannot check, so the
    amount is floored the way the points are (spec D4), never rounded up.
    """
    deposit(service, amount="99.999", deposit_id="dep-1", account_id="acc-savings")

    (movement,) = service.history(CUSTOMER)

    assert movement.points == 99
    assert "€99.99" in movement.description
    assert "€100" not in movement.description


def test_the_history_is_newest_first(service, clock):
    deposit(service, amount="10", deposit_id="dep-1")
    clock.advance(timedelta(days=1))
    deposit(service, amount="20", deposit_id="dep-2")

    movements = service.history(CUSTOMER)

    assert [m.points for m in movements] == [20, 10]
    assert movements[0].occurred_at > movements[1].occurred_at


# ------------------------------------------------------------ injected clock --


def test_movements_are_stamped_with_the_injected_clock(service, clock):
    deposit(service, amount="10", deposit_id="dep-1")

    clock.advance(timedelta(days=400))
    deposit(service, amount="20", deposit_id="dep-2")

    # 400 days is past the twelve months the first lot had, so the history
    # also carries its expiry by now; the deposits are what this pins.
    newest, oldest = [m for m in service.history(CUSTOMER) if m.reason is MovementReason.DEPOSIT]
    assert oldest.occurred_at == PINNED_NOW
    assert newest.occurred_at == PINNED_NOW + timedelta(days=400)


def test_all_stamps_are_europe_brussels(service, clock):
    deposit(service, amount="10", deposit_id="dep-1")

    (movement,) = service.history(CUSTOMER)

    assert movement.occurred_at.utcoffset() == PINNED_NOW.utcoffset()


def test_an_unknown_event_is_refused(service):
    with pytest.raises(DomainError):
        service.handle(object())
