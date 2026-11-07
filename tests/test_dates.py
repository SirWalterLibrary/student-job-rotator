"""Tests for the dates module (reference dates from spec 02)."""
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from rotator.dates import (
    TZ,
    central_today,
    class_days,
    first_class_day_on_or_after,
    is_class_day,
    month_class_days,
    next_class_day_after,
    parse_iso,
    upcoming_weekend,
)

NOV = [date(2026, 11, 1), date(2026, 11, 7), date(2026, 11, 8), date(2026, 11, 14),
       date(2026, 11, 15), date(2026, 11, 21), date(2026, 11, 22),
       date(2026, 11, 28), date(2026, 11, 29)]


def test_upcoming_weekend_friday():
    """Friday 2026-11-06 looks ahead at Saturday and Sunday."""
    assert upcoming_weekend(date(2026, 11, 6)) == [date(2026, 11, 7), date(2026, 11, 8)]


def test_upcoming_weekend_saturday():
    """A Saturday is its own upcoming weekend."""
    assert upcoming_weekend(date(2026, 11, 7)) == [date(2026, 11, 7)]


def test_upcoming_weekend_sunday():
    """A Sunday is its own upcoming weekend."""
    assert upcoming_weekend(date(2026, 11, 8)) == [date(2026, 11, 8)]


def test_upcoming_weekend_monday():
    """Monday 2026-11-09 looks ahead to the next weekend."""
    assert upcoming_weekend(date(2026, 11, 9)) == [date(2026, 11, 14), date(2026, 11, 15)]


def test_next_class_day_after_sat_sun_sat():
    """Sat -> next Sunday; Sunday -> next Saturday."""
    assert next_class_day_after(date(2026, 11, 7)) == date(2026, 11, 8)
    assert next_class_day_after(date(2026, 11, 8)) == date(2026, 11, 14)


def test_next_class_day_after_skips_cancelled():
    """Cancelled class days are skipped."""
    assert next_class_day_after(date(2026, 11, 8)) == date(2026, 11, 14)
    assert next_class_day_after(date(2026, 11, 8), frozenset({date(2026, 11, 14)})) == date(2026, 11, 15)


def test_class_days_range_inclusive():
    """class_days is inclusive on both ends and lists every Sat/Sun."""
    assert class_days(date(2026, 11, 1), date(2026, 11, 30)) == NOV


def test_month_class_days_november_2026():
    """month_class_days covers exactly the month's Sat/Suns."""
    assert month_class_days(2026, 11) == NOV


def test_first_class_day_on_or_after():
    """Weekend days stay; weekdays advance to the next Saturday."""
    assert first_class_day_on_or_after(date(2026, 11, 7)) == date(2026, 11, 7)
    assert first_class_day_on_or_after(date(2026, 11, 8)) == date(2026, 11, 8)
    assert first_class_day_on_or_after(date(2026, 11, 6)) == date(2026, 11, 7)
    assert first_class_day_on_or_after(date(2026, 11, 9)) == date(2026, 11, 14)


def test_central_today_dst_end_utc_is_monday():
    """2026-11-02 05:30 UTC is still Monday 23:30 Central (DST ended 11-01)."""
    assert central_today(datetime(2026, 11, 2, 5, 30, tzinfo=ZoneInfo("UTC"))) == date(2026, 11, 1)


def test_central_today_saturday_late_night():
    """2026-11-08 05:30 UTC is Saturday 23:30 Central."""
    assert central_today(datetime(2026, 11, 8, 5, 30, tzinfo=ZoneInfo("UTC"))) == date(2026, 11, 7)


def test_central_today_dst_start():
    """2027-03-15 04:30 UTC is Sunday 23:30 Central (DST starts 03-14)."""
    assert central_today(datetime(2027, 3, 15, 4, 30, tzinfo=ZoneInfo("UTC"))) == date(2027, 3, 14)


def test_central_today_rejects_naive_datetime():
    """A naive datetime is rejected."""
    with pytest.raises(ValueError):
        central_today(datetime(2026, 11, 7, 12, 0))


def test_central_today_uses_chicago_timezone():
    """The module timezone is America/Chicago."""
    assert str(TZ) == "America/Chicago"


def test_parse_iso_and_is_class_day():
    """parse_iso round-trips ISO dates and rejects junk; is_class_day only Sat/Sun."""
    assert parse_iso("2026-11-07") == date(2026, 11, 7)
    with pytest.raises(ValueError):
        parse_iso("not-a-date")
    assert is_class_day(date(2026, 11, 7)) is True
    assert is_class_day(date(2026, 11, 8)) is True
    assert is_class_day(date(2026, 11, 6)) is False
