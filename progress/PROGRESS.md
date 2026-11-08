# PROGRESS

Agent: after finishing a task change `[ ]` to `[x]` and fill in the notes (date, tests passing, anything odd).
Use `[!]` if blocked (details go in NOTES.md). Do not reorder rows.

| Status / Task | Title | Notes |
|---|---|---|
| [x] T00 | Scaffold, config, health endpoint, pytest fixtures | 2026-11-06: 5 tests passing; dev server serves /api/health. See NOTES.md for pytest.ini addition.
| [x] T01 | SQLite schema + db helpers + settings | 2026-11-06: 13 tests passing (8 new). |
| [x] T02 | Dates module (Central time, class days) | 2026-11-06: 31 tests passing (18 new). |
| [x] T03 | Scheduler core (pure fairness algorithm) | 2026-11-06: 43 tests passing (12 new); purity grep clean. |
| [x] T04 | Roster API: students, jobs, volunteers | 2026-11-06: 57 tests passing (14 new); see NOTES.md for job re-activation choice. |
| [x] T05 | Schedule service: freeze + build sessions | 2026-11-06: 67 tests passing (10 new); see NOTES.md for walk/queue_status interpretation. |
| [x] T06 | Read API: config, today, calendar, queue | 2026-11-07: 81 tests passing (14 new); curl of /api/today?today=2026-11-06 verified on live server. |
| [x] T07 | Actions: absent swap, cancel/restore day, manual override | 2026-11-07: 98 tests passing (17 new); curl swap check: cover + make-up notes visible in /api/today and /api/calendar. See NOTES.md for vacant/clear vs walker refill. |
| [x] T08 | Admin PIN, rate limit, export/import | 2026-11-07: 110 tests passing (12 new); live curl verified 401/429/201 + export. See NOTES.md. |
| [x] T09 | Frontend shell, Islamic theme, tabs | 2026-11-07: 110 tests passing (no new tests); live server + Node DOM-stub smoke verified tabs, hash routing, 401 lock. See NOTES.md for /static/ path note. |
| [x] T10 | Tab 1: Today / Next weekend | 2026-11-07: 110 tests passing (no new tests); Node DOM-stub against live server verified Friday two-card (Next Weekend), Saturday one-card (Today + tomorrow line), cancelled card (note + roles-move, no table), 500→error+Retry, visibilitychange + midnight config reload. See NOTES.md. |
| [x] T11 | Tab 2: Monthly calendar | 2026-11-07: 110 tests passing (no new tests, frontend-only); Node DOM-stub against live server: 35 checks (grid, nav disable rules, cancelled/swap states, dialog + focus return, narrow stacked weekends, error/Retry, exact role match vs API). See NOTES.md. |
| [x] T12 | Teacher tools drawer: students, jobs, volunteers, up-next, settings | 2026-11-07: 110 tests passing (no new, frontend-only); Node DOM-stub against the live server (ADMIN_PIN=1234, ?today=2026-11-06): 40 checks all pass (lock/login flow, 4 sections, add/rename/remove, job add + expand + volunteer ticks, reordering, queue, settings error, export/import round trip, focus/Esc, 401 re-lock, accordion). See NOTES.md for css/manage.css + manage-roster.js split. |
| [x] T13 | Action dialogs: absent swap, shift day, manual change, PIN unlock | 2026-11-07: 110 tests passing (no new, UI-only); Node DOM-stub against the live server (ADMIN_PIN=1234, ?today=2026-11-07): 18 checks all pass (swap chip/toast/calendar ⇄, vacant + fairness, shift "No class" + Sunday equals pre-shift Saturday + restore, change options, lock, 401 re-lock, day dialog editable). See NOTES.md: one backend change (request lock in app.py — the task's refreshAll exposed a concurrency 500 in freeze_through) and the vacant-refill nuance. |
| [x] T14 | Dockerize (dev + prod compose) | 2026-11-07: all done-when checks pass (see NOTES.md): app on :5055 + PIN 1234, student survives restart, Minnesota date, healthy, uid 10001, production exits with clear error. |
| [x] T15 | Demo seed, smoke script, acceptance pass, polish | 2026-11-07: seed_demo + smoke (12/12 SMOKE OK); acceptance passed (68 API checks incl. spec 09 rows + export/import + PIN limit, 35 DOM-stub UI checks, 5 scenarios; production ignores ?today); README rewritten; 110 tests unchanged. See NOTES.md for the row-10 restore nuance and the specs/09 row-4 wording fix. |
| [x] T16 | Deploy to home server (human-run checklist) | Mohamed verified |
| [x] T17 | Fix drawer: X button, blank panel after refresh, lock state | 2026-11-07: 112 tests passing (2 new static-asset guards); Node DOM-stub against the live server (ADMIN_PIN=1234, seeded demo, 37 checks, 4 scenarios incl. 3× refresh-while-unlocked): X/Esc close with focus return, drawer closed + "Lock" header + working buttons after every refresh, Lock persists, private window locked. Root cause A confirmed (see NOTES.md). |
| [ ] T18 | Fix drawer scrolling and oversized form fields | |

Last session: T17 done 2026-11-07 (112 tests + 37 DOM-stub checks)
Total tests passing: 112
