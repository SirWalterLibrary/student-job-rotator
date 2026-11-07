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
| [ ] T09 | Frontend shell, Islamic theme, tabs | |
| [ ] T10 | Tab 1: Today / Next weekend | |
| [ ] T11 | Tab 2: Monthly calendar | |
| [ ] T12 | Teacher tools drawer: students, jobs, volunteers, up-next, settings | |
| [ ] T13 | Action dialogs: absent swap, shift day, manual change, PIN unlock | |
| [ ] T14 | Dockerize (dev + prod compose) | |
| [ ] T15 | Demo seed, smoke script, acceptance pass, polish | |
| [ ] T16 | Deploy to home server (human-run checklist) | |

Last session: T08 done 2026-11-07 (110 tests passing)
Total tests passing: 110
