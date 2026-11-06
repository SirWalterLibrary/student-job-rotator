# 02 — Dates, time zone, class days

All date logic lives in `rotator/dates.py`. Timezone is `America/Chicago` (handles CST/CDT automatically).
`requirements.txt` MUST include `tzdata` (slim Docker images have no system tz database).

```python
from datetime import date, datetime
from zoneinfo import ZoneInfo
TZ = ZoneInfo("America/Chicago")
SAT, SUN = 5, 6                      # date.weekday(): Mon=0 ... Sun=6

def central_today(now: datetime | None = None) -> date
    # now=None -> datetime.now(TZ). If given, must be tz-aware; convert with now.astimezone(TZ).date().
def parse_iso(s: str) -> date                       # "2026-11-07"; raises ValueError on bad input
def is_class_day(d: date) -> bool                   # Saturday or Sunday
def first_class_day_on_or_after(d: date) -> date
def class_days(start: date, end: date) -> list[date]    # inclusive, ascending, only Sat/Sun
def month_class_days(year: int, month: int) -> list[date]
def upcoming_weekend(today: date) -> list[date]
def next_class_day_after(d: date, cancelled: frozenset[date] = frozenset()) -> date
```

## upcoming_weekend(today)
| today is | returns |
|---|---|
| Monday–Friday | `[next Saturday, next Sunday]` |
| Saturday | `[today]` |
| Sunday | `[today]` |

## next_class_day_after(d, cancelled)
Smallest Saturday/Sunday strictly after `d` that is not in `cancelled`. (Sat → Sun same weekend; Sun → next Sat.)

## Reference dates (2026–2027), use them in tests
- 2026-11-06 is Friday → `upcoming_weekend` = `[2026-11-07, 2026-11-08]`
- 2026-11-07 Saturday → `[2026-11-07]`; 2026-11-08 Sunday → `[2026-11-08]`
- 2026-11-09 Monday → `[2026-11-14, 2026-11-15]`
- `next_class_day_after(2026-11-08)` = `2026-11-14`; with `cancelled={2026-11-14}` = `2026-11-15`

## Time-zone tests (the reason central_today exists)
- DST ends Sun 2026-11-01 (02:00 CDT → 01:00 CST).
  `datetime(2026,11,2,5,30,tzinfo=UTC)` → Central 2026-11-01 23:30 → returns `2026-11-01` (UTC already says Monday).
- `datetime(2026,11,8,5,30,tzinfo=UTC)` → Central 2026-11-07 23:30 → returns `2026-11-07` (Saturday).
- DST starts Sun 2027-03-14. `datetime(2027,3,15,4,30,tzinfo=UTC)` → Central 2027-03-14 23:30 → `2027-03-14`.
- Naive datetimes are rejected: `central_today(datetime(2026,11,7,12,0))` raises `ValueError`.

## "Today override" (tests and previews only)
When `ALLOW_TODAY_OVERRIDE=1`, the routes accept `?today=YYYY-MM-DD`. Implement once in a helper
`request_today()` in `rotator/routes_common.py`; every route calls it instead of calling `central_today()` directly.
When the flag is off the query parameter is ignored.

## Hijri date (browser only)
Do not compute Hijri on the server. In JS:
```js
const hijri = new Intl.DateTimeFormat('en-u-ca-islamic-umalqura-nu-latn',
  { day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC' });
hijri.format(new Date(Date.UTC(y, m - 1, d, 12)));   // noon UTC avoids off-by-one
```
It is approximate (local moon sighting can differ by a day). The UI footer says so.
