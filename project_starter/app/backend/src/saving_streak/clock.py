"""The clock, injected everywhere (spec D5).

Nothing in the domain reads the wall clock. The application service is handed a
`Clock` and stamps every ledger movement with it, so a test can pin "now" and a
later ticket can time-travel by advancing it instead of sleeping (spec T2/T3).

All time arithmetic is Europe/Brussels.
"""

from __future__ import annotations

import calendar
from abc import ABC, abstractmethod
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from .events import DomainError
from .settings import TIMEZONE

#: The one timezone in the system (spec D5).
BRUSSELS = ZoneInfo(TIMEZONE)


def in_brussels(moment: datetime) -> datetime:
    """Return `moment` as an aware Europe/Brussels datetime that really exists.

    A naive datetime is read as a Brussels wall-clock reading; an aware one is
    converted. Either way the rest of the system only ever sees Brussels.

    The round trip through UTC is the normalisation: it is the identity for a
    local time that exists, and for one that does not — 02:30 on the March
    morning the clocks jump from 02:00 to 03:00 — it yields the instant the
    Brussels clock actually reached. Expiry and the daily sweep (spec D20) do
    their arithmetic on these values, so a wall-clock reading that never
    happened must never reach the ledger.
    """
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=BRUSSELS)
    return moment.astimezone(timezone.utc).astimezone(BRUSSELS)


def add_months(moment: datetime, months: int) -> datetime:
    """`moment` shifted by whole calendar months, clamped to a day that exists.

    Calendar months, not 365 days, and a day the target month does not have
    clamps to the last one it does, the way an anniversary does (spec D27):
    29 February lands on 28 February in a common year. The wall-clock reading
    is preserved and then normalised through `in_brussels`, so a time the
    Brussels clock skips on a spring-forward morning never reaches a ledger.

    Both twelve-month clocks in the system are this one function: a points
    lot's expiry (spec D17) and a deposit lot's recurring anniversary (spec
    D22). The recurring one always counts from the original deposit date
    rather than from the previous anniversary, which is what keeps the
    clamping honest — a 29 February deposit lot vests on 28 February in the
    common years and back on 29 February in the leap ones, instead of
    drifting a day earlier every time it clamps.
    """
    moment = in_brussels(moment)
    shifted = moment.month - 1 + months
    year, month = moment.year + shifted // 12, shifted % 12 + 1
    day = min(moment.day, calendar.monthrange(year, month)[1])
    return in_brussels(moment.replace(tzinfo=None).replace(year=year, month=month, day=day))


#: The last instant the system will read a position at (spec D5).
#:
#: `datetime` stops at the end of year 9999, and a deposit lot's recurring
#: anniversary clock (spec D22) steps up to a year past the instant it is read
#: at to find the anniversary that has not passed yet. Asked to read in 9999,
#: it would look for a date in a year the calendar does not have. The horizon
#: is therefore the end of 9998: the last instant at which every twelve-month
#: clock in the system still lands inside the calendar.
LAST_READABLE_INSTANT = in_brussels(datetime(9998, 12, 31, 23, 59, 59, 999999))


def readable_instant(moment: datetime, what: str) -> datetime:
    """`moment` in Brussels, or the domain refuses to read at it.

    An instant past the end of the calendar is refused the way an amount past
    the end of the ledger is (`events.MAX_AMOUNT_EUR`): cleanly, as a
    `DomainError` the HTTP adapter maps to a 400, and at the edge rather than
    part-way through the arithmetic. Without it the refusal arrives as a
    `ValueError` out of a `datetime.replace` deep inside an anniversary walk,
    or an `OverflowError` out of the conversion into Brussels — neither of
    which is a `DomainError`, so both escape the seam as a 500.

    Every read on the seam comes through here, so a page that asks four
    questions at one instant gets one answer to all four, rather than two
    answers and a crash.
    """
    refusal = (
        f"{what} of {moment.isoformat()} is past"
        f" {LAST_READABLE_INSTANT.date().isoformat()}, the last date this system reads at"
    )
    try:
        # Brussels is ahead of UTC, so converting an instant near the end of
        # the calendar is itself enough to run off it.
        in_range = in_brussels(moment)
    except (OverflowError, ValueError) as exc:
        raise DomainError(refusal) from exc
    if in_range > LAST_READABLE_INSTANT:
        raise DomainError(refusal)
    return in_range


class Clock(ABC):
    """The seam's view of time."""

    @abstractmethod
    def now(self) -> datetime:
        """The current instant, as an aware Europe/Brussels datetime."""

    def today(self) -> date:
        """The current business date in Europe/Brussels."""
        return self.now().date()


class SystemClock(Clock):
    """Production clock: real time, in Brussels."""

    def now(self) -> datetime:
        return datetime.now(BRUSSELS)


class FixedClock(Clock):
    """A clock a test (or a demo) pins and moves by hand.

    This is the only way time advances in tests: no `sleep`, no wall-clock
    reading, no test that behaves differently in January than in March.
    """

    def __init__(self, moment: datetime) -> None:
        self._now = in_brussels(moment)

    def now(self) -> datetime:
        return self._now

    def set(self, moment: datetime) -> None:
        self._now = in_brussels(moment)

    def advance(self, delta: timedelta) -> datetime:
        """Move time on by `delta`, in the two senses a calendar needs.

        Whole days are wall-clock arithmetic: `+1 day` from 23:30 is 23:30 the
        next day, whatever the offset does in between. That is what the daily
        sweep steps by (spec D20/D43), and a sweep that ran at 03:00 must run
        at 03:00 the next day too, not at 02:00 or 04:00.

        What is left over is real elapsed time, so it is added in UTC: three
        hours of advance is three real hours on both of the days Brussels
        changes offset. Wall-clock arithmetic cannot do that — on the March
        morning it lands on 02:30, a reading that never happened, and on the
        October morning the hour that repeats is silently skipped or replayed,
        which would move the clock backwards while advancing it.
        """
        backwards = delta < timedelta(0)
        magnitude = -delta if backwards else delta
        whole_days = timedelta(days=magnitude.days)
        remainder = magnitude - whole_days
        if backwards:
            whole_days, remainder = -whole_days, -remainder

        moment = self._now
        if whole_days:
            moment = in_brussels(moment.replace(tzinfo=None) + whole_days)
        if remainder:
            moment = (moment.astimezone(timezone.utc) + remainder).astimezone(BRUSSELS)
        self._now = moment
        return self._now
