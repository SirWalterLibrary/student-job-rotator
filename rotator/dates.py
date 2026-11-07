"""Date logic: Central time, class days (Saturday/Sunday)."""
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/Chicago")
SAT, SUN = 5, 6                      # date.weekday(): Mon=0 ... Sun=6


def central_today(now: datetime | None = None) -> date:
    """Today's date in America/Chicago (raises ValueError for naive input)."""
    if now is None:
        now = datetime.now(TZ)
    if now.tzinfo is None:
        raise ValueError("now must be a timezone-aware datetime")
    return now.astimezone(TZ).date()


def parse_iso(s: str) -> date:
    """Parse a YYYY-MM-DD string (raises ValueError on bad input)."""
    return date.fromisoformat(s)


def is_class_day(d: date) -> bool:
    """True when d is a Saturday or Sunday."""
    return d.weekday() in (SAT, SUN)


def first_class_day_on_or_after(d: date) -> date:
    """The first class day on or after d."""
    while not is_class_day(d):
        d += timedelta(days=1)
    return d


def class_days(start: date, end: date) -> list[date]:
    """All class days from start to end inclusive, ascending."""
    days = []
    d = start
    while d <= end:
        if is_class_day(d):
            days.append(d)
        d += timedelta(days=1)
    return days


def month_class_days(year: int, month: int) -> list[date]:
    """All class days within the given month."""
    last = (date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)) - timedelta(days=1)
    return class_days(date(year, month, 1), last)


def upcoming_weekend(today: date) -> list[date]:
    """[Saturday, Sunday] ahead of today, or [today] when today is a class day."""
    if today.weekday() in (SAT, SUN):
        return [today]
    sat = today + timedelta(days=SAT - today.weekday())
    return [sat, sat + timedelta(days=1)]


def next_class_day_after(d: date, cancelled: frozenset[date] = frozenset()) -> date:
    """Smallest class day strictly after d that is not in cancelled."""
    cur = d + timedelta(days=1)
    while not is_class_day(cur) or cur in cancelled:
        cur += timedelta(days=1)
    return cur
