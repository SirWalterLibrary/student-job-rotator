# 09 — Acceptance checklist

Run in T15 (agent, with `ALLOW_TODAY_OVERRIDE=1` and the demo seed) and again by the teacher in T16 on the real server.
Demo data = `scripts/seed_demo.py`: 6 jobs, 10 students, overlapping volunteers, start date 2026-11-07.

| # | Requirement | How to verify |
|---|---|---|
| 1 | Add jobs / volunteers | Teacher tools: add a job and a student, tick the student as volunteer; it appears in Fairness panel |
| 2 | Islamic theme | Bismillah header, emerald/gold/cream, star pattern, Arabic footer text renders right-to-left |
| 3 | Sat + Sun rotation | `/api/calendar?month=2026-11` shows both days for each weekend with different students |
| 4 | No repeat until all served | `scripts/smoke.py` simulates 12 weekends: before each Saturday it takes `/api/queue` as of the previous Saturday (the state before that weekend) and asserts each pick is the first person in that job's queue who is not busy on that Saturday, so nobody repeats while an available volunteer with an older turn is waiting |
| 5 | No double roles | smoke script asserts no student appears twice on any day across 12 weekends |
| 6 | Table on Sat/Sun | `?today=2026-11-07` → tab 1 shows ONE card "Today" with a Job/Student table |
| 7 | Central time | `?today` ignored in production; unit tests for 2026-11-01/2027-03-14 UTC-vs-Central cases pass |
| 8 | Monthly calendar | Tab 2 grid Mon→Sun, Sat/Sun cells list Job — Student, prev/next month work, month before start unreachable |
| 9 | Absent swap | On Saturday mark student A absent for job J: B covers Saturday, calendar shows A holding J on Sunday with ⇄ mark |
| 10 | Teacher away shift | Shift Saturday: Saturday shows "No class"; Sunday roles equal what Saturday's would have been; restore reverses |
| 11 | Two tabs | Exactly two tabs; Teacher tools is a drawer, not a tab |
| 12 | Weekday vs weekend | `?today=2026-11-06` (Fri) → tab 1 "Next Weekend" with Saturday and Sunday cards; Sat/Sun → "Today" with one card |
| 13 | Persistence | Add data, reload the page, restart the container (`docker compose restart`), data is still there |

## Extra checks
- With a PIN set: viewer sees no teacher buttons; wrong PIN → error; 6 wrong PINs in a minute → 429.
- Export backup → wipe → import → everything identical (compare `/api/calendar` JSON before/after).
- 360px wide phone layout: no horizontal scroll; weekends stack.
- Browser console has no errors on any tab; keyboard-only use of tabs, drawer and dialogs works.
- `pytest -q` is green; no test depends on the real date.
- Fresh database + no jobs: both tabs show friendly empty states, no errors.
