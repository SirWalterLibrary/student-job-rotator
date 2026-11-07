# NOTES

Agent: append here. Keep entries short and dated.

## Deviations from the spec
- T03: added a one-line module docstring to `rotator/scheduler.py` (AGENTS.md requires docstrings; the spec's code block has none). Algorithm copied verbatim, unchanged.
- T04: spec 05 defines duplicate handling only for POST /api/students; I applied the same rule to jobs (active duplicate → 409; archived duplicate → re-activate, 200) following spec 01's general "re-adding an archived name re-activates the same row". Also: archiving a job keeps its `volunteers` rows (spec 01 only requires deleting future assignments) so re-activating restores the roster. `create_app` imports the roster blueprint lazily to avoid an app↔routes import cycle.
- T05: spec 04 documents `walk` as returning `dict[date, dict]`, but the task file instructs returning `(results, last_served)` — I follow the task file (internal-only API; `queue_status` needs the final `last_served`). Also `queue_status` shows each student's `last_served` from that final dict (so a projected pick for the next class day shows that date) rather than the DB's MAX(date); this keeps the displayed date consistent with the queue ordering the spec derives from the same dict.
- T07: the walker's same-day refill (spec 04 step 5: `d == today` re-runs on every call) would re-insert an auto row that `vacant`/`clear` just deleted within the same request. So `swap_absent(vacant=True)` and `clear_assignment` return the pre-delete session view minus the cleared role and do not re-walk. The deletion stays in the DB; a *later* read of the same day re-fills the slot (the same behaviour the restore flow relies on), but past-day reads keep it empty.
- T07: spec 04 types `clear_assignment -> None`, but it returns the session view (the route must return one and building it in the route would trigger the re-filling walk). `vacant` returns a session dict rather than the swap dict for the same reason.
- T07: `set_manual` rejects a student only when they hold a *different* job that day, per spec 04's "must not have a role that day (or already hold the same job)".
- T07: the dev machine's clock is 2026-11-06 (Friday, Central), so `central_today()` matches the fixture dates in tests; every test passes `?today=` and conftest enables the override.

- T08: the task puts the `TRUST_PROXY` ProxyFix under `routes_admin.py`, but `app.wsgi_app` only exists in `app.create_app`, so the ProxyFix wrap lives in `app.py` (one line, after blueprint registration).
- T08: `require_pin` checks the per-IP block (429) *before* the PIN (401), so a blocked IP gets 429 even with the right PIN; a *missing* header does not count as a failure (only wrong PINs do, per spec 05).
- T08: added a `FailureLimiter.reset(key)` helper (in-memory dict cleanup) so tests can start unblocked; routes share one process-wide limiter, lazily created in `rotator/auth.py`.
- T08: import validates the whole dump (version 1, all six tables, per-column types) *before* touching the DB, then deletes + inserts in one `with conn:` transaction; table names come from an internal dict, never user input.
- T08: a stale dev server from the T06 session was still listening on :5055 during the live smoke test (old code); killed it and re-verified on a fresh server.
- T09: the task writes `<script src="js/app.js">`, but Flask serves the static folder at `/static/` (static_url_path in app.py, which this task may not touch), so index.html uses `/static/css/…` and `/static/js/app.js` — bare `js/app.js` would 404.
- T09: no browser was scriptable on the dev machine, so the shell was verified with a small Node DOM stub driving the real modules against a live server (tab click, arrow keys, hash routing incl. `#calendar/YYYY-MM` deep link, 401 → `kr:locked`). `applyHash` also syncs `state.month` when only the hash month changes on the calendar tab, so later modules (T10/T11) react to deep links.
- T09: kept `theme.css` under the 250-line rule by omitting blank lines between rule blocks of the same component (all spec 07 styles present).

- T10: `js/today.js` imports `state` from `app.js` (a circular ESM import, safe because it is only dereferenced at call time) so the midnight-crossing path can refresh the shared `state.config`.
- T10: the "Tomorrow: Sunday, November 8" line is computed from the Saturday session's date (server's `upcoming_weekend` returns a single session on class days, so the Sunday isn't in the response); it links to `#calendar/YYYY-MM` per spec 06, which app.js's existing hash routing already resolves.
- T10: no browser on the dev machine, so the UI was verified with a Node DOM-stub harness driving the real modules against the live server (scenarios: Friday two-card with cancelled Sunday, Saturday one-card + tomorrow line, fully-cancelled Saturday with "Roles move to…", 500 → friendly error + Retry, visibilitychange refresh + `today` change → `/api/config` reload). `pytest -q`: 110 passing (unchanged, frontend-only task, same as T09).

## BLOCKED
- BLOCKED sync: T00 — `git push -u origin HEAD` failed: `fatal: could not read Username for 'https://github.com': Device not configured` (remote https://github.com/SirWalterLibrary/student-job-rotator.git; no stored credentials). The earlier `git pull --rebase` also failed only because origin has no branches yet and the local branch had no upstream. Commit 7473da5 ("T00: scaffold, config, health endpoint, pytest fixtures") is local; push it once GitHub credentials are available.
- BLOCKED sync: T01 (2026-11-06) — same auth failure on `git push -u origin HEAD`: `fatal: could not read Username for 'https://github.com': Device not configured`. `git fetch` succeeds (public repo) but origin still has no branches, so `git pull --rebase` fails only for lack of upstream. Local commits 7473da5 (T00), c6fd7d6 (T00 note), 3f6208a (T01) are unpushed; push them once GitHub push credentials are configured.
- Resolved (T06/T07, 2026-11-07): GitHub push credentials are now configured; `git pull --rebase` + `git push -u origin HEAD` succeeded, so `origin/main` is current. The two entries above are historical.

## Ideas for later (do NOT build now)
- Student view that highlights "my next turn"
- Printable month PDF
- Per-job rotation history page
