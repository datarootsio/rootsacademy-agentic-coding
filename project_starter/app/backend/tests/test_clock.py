"""The injected clock (spec D5), including the two days a year it is hard.

The sweep and expiry tickets time-travel by advancing this clock (spec T2/T3),
so what it produces has to be a Brussels instant that really existed — the
ledger stamps every movement with it.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from saving_streak.clock import BRUSSELS, FixedClock, in_brussels

#: The night Brussels jumps from 02:00 CET straight to 03:00 CEST.
SPRING_FORWARD_EVE = datetime(2026, 3, 28, 23, 30)

#: The night Brussels repeats 02:00–03:00: 01:30 UTC is the *second* pass
#: through 02:30 local, the one `fold=1` names.
AUTUMN_FOLD_SECOND_PASS = datetime(2026, 10, 25, 1, 30, tzinfo=timezone.utc)


def test_a_pinned_clock_reads_back_what_it_was_pinned_to():
    clock = FixedClock(datetime(2026, 3, 14, 10, 30))

    assert clock.now() == in_brussels(datetime(2026, 3, 14, 10, 30))
    assert clock.now().tzinfo is BRUSSELS
    assert clock.today() == datetime(2026, 3, 14).date()


def test_advancing_whole_days_keeps_the_wall_clock_reading():
    """`+1 day` is the sweep's step: the same time of day, the next date."""
    clock = FixedClock(SPRING_FORWARD_EVE)

    clock.advance(timedelta(days=1))

    assert clock.now().date() == datetime(2026, 3, 29).date()
    assert (clock.now().hour, clock.now().minute) == (23, 30)
    assert clock.now().utcoffset() == timedelta(hours=2)  # CEST, recomputed


def test_advancing_across_the_spring_forward_gap_lands_on_a_real_instant():
    """23:30 CET + 3h is 03:30 CEST. 02:30 that morning never happened."""
    clock = FixedClock(SPRING_FORWARD_EVE)

    clock.advance(timedelta(hours=3))

    assert clock.now() == in_brussels(datetime(2026, 3, 29, 3, 30))
    assert (clock.now().hour, clock.now().minute) == (3, 30)
    assert clock.now().utcoffset() == timedelta(hours=2)


def test_a_local_time_that_never_happened_is_normalised_on_the_way_in():
    assert in_brussels(datetime(2026, 3, 29, 2, 30)) == in_brussels(datetime(2026, 3, 29, 3, 30))


def test_advancing_never_loses_or_invents_elapsed_time():
    """Three hours of advance is three real hours.

    Subtracting two Brussels readings compares wall clocks (23:30 to 03:30
    looks like four hours across the gap), so the elapsed time is read where
    it is unambiguous: in UTC.
    """
    clock = FixedClock(SPRING_FORWARD_EVE)
    before = clock.now().astimezone(timezone.utc)

    after = clock.advance(timedelta(hours=3)).astimezone(timezone.utc)

    assert after - before == timedelta(hours=3)


def test_advancing_inside_the_autumn_fold_moves_time_forwards():
    """02:30 comes round twice on 25 October; ten minutes on is 02:40, once.

    Wall-clock arithmetic loses the fold and lands on the *first* 02:40, which
    is fifty minutes earlier in real time than where it started: an advance
    that moves the clock backwards.
    """
    clock = FixedClock(AUTUMN_FOLD_SECOND_PASS)
    before = clock.now().astimezone(timezone.utc)

    after = clock.advance(timedelta(minutes=10))

    assert after - before == timedelta(minutes=10)
    assert after.astimezone(timezone.utc) == datetime(2026, 10, 25, 1, 40, tzinfo=timezone.utc)


def test_advancing_across_the_repeated_hour_counts_it_once():
    """01:30 CEST + 2h is 02:30 CET — two real hours, not three.

    The hour from 02:00 to 03:00 happens twice that morning; wall-clock
    arithmetic reads 01:30 + 2h as 03:30 and so invents an extra hour.
    """
    clock = FixedClock(datetime(2026, 10, 25, 1, 30))
    before = clock.now().astimezone(timezone.utc)

    after = clock.advance(timedelta(hours=2))

    assert after - before == timedelta(hours=2)
    assert (after.hour, after.minute) == (2, 30)
    assert after.utcoffset() == timedelta(hours=1)  # CET, the second pass


def test_advancing_a_whole_day_over_the_autumn_change_keeps_the_wall_clock_reading():
    """The sweep runs at 03:00 every day (spec D20), including that one."""
    clock = FixedClock(datetime(2026, 10, 24, 3, 0))

    clock.advance(timedelta(days=1))

    assert clock.now() == in_brussels(datetime(2026, 10, 25, 3, 0))
    assert (clock.now().hour, clock.now().minute) == (3, 0)
    assert clock.now().utcoffset() == timedelta(hours=1)  # CET, recomputed


def test_advancing_a_day_and_a_half_splits_into_days_then_real_time():
    clock = FixedClock(SPRING_FORWARD_EVE)

    after = clock.advance(timedelta(days=1, hours=12))

    # +1 day keeps 23:30 (now CEST), then twelve real hours land on 11:30.
    assert after == in_brussels(datetime(2026, 3, 30, 11, 30))


def test_a_clock_can_be_wound_back():
    """Symmetry, so a test that steps back does not silently drift."""
    clock = FixedClock(SPRING_FORWARD_EVE)
    before = clock.now().astimezone(timezone.utc)

    clock.advance(timedelta(hours=3))
    after = clock.advance(timedelta(hours=-3)).astimezone(timezone.utc)

    assert after == before
