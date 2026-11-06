# T03 — Scheduler core (pure fairness algorithm)

Depends on: T00.
Read: `AGENTS.md`, `specs/03-scheduler.md`.

## Create
- `rotator/scheduler.py` — copy the code block from 03 exactly. Do not change the algorithm.
- `tests/test_scheduler.py` — all 12 tests listed in 03, with the `days(n)` helper.

## Done when
- `pytest tests/test_scheduler.py -q` passes (12 tests)
- `grep -nE "import (sqlite3|flask|random)|datetime|open\(" rotator/scheduler.py` prints nothing

## Don't
Add database code, clock access or randomness. Don't "optimize" the ordering rules.
