# AGENTS.md — read this first, every session

Project: **Khidmah Roster**, an Islamic-themed weekend job rotator for a classroom.
Stack: Python 3.12 + Flask 3 + SQLite (stdlib `sqlite3`) + plain HTML/CSS/JS (ES modules, no build step).
Timezone: America/Chicago (Minnesota). Teacher: Mohamed.

## Session protocol (one task per session)
1. Open `progress/PROGRESS.md`. Take the first task marked `[ ]` (or the one the user names).
2. Read that task file in `tasks/`, then ONLY the spec files it lists. Do not read other tasks.
3. Do exactly what the task says. No extra features, no refactors outside the listed files.
4. Run the task's "Done when" commands. Fix until they pass.
5. Update `progress/PROGRESS.md`: change `[ ]` to `[x]`, add a short note (date, test count).
   Put surprises or deviations in `progress/NOTES.md`.
6. `git add -A && git commit -m "T05: <title>"`. Then stop.

## Hard rules
- "Today" ALWAYS comes from `rotator.dates.central_today()`. Never `date.today()`, never `datetime.now()` without a timezone. In the browser, never compute today — use the `today` value from `/api/config`.
- No randomness anywhere. Scheduling is deterministic.
- `rotator/scheduler.py` is pure: no sqlite3, no Flask, no clock, no file access.
- SQL is parameterized (`?`), never string-formatted.
- Frontend: build DOM with `textContent` / `createElement`. Never put student or job names into `innerHTML`.
- No npm, no CDN, no external fonts or scripts. Everything works offline on the LAN.
- API errors are JSON: `{"error": "message"}` with the right status code (400, 401, 404, 409, 429).
- Keep every file under 250 lines. Split into a new module if it grows.
- Small typed functions with a one-line docstring. Match names in `specs/` exactly.
- Dates are ISO strings `YYYY-MM-DD` everywhere (DB, API, JS).
- Each task adds its own tests. Never delete or weaken an existing test to make it pass.

## Commands
```bash
python3 -m venv .venv && source .venv/bin/activate   # first time only
pip install -r requirements.txt
pytest -q                                            # all tests
DATA_DIR=./data flask --app wsgi run --port 5055 --debug   # dev server
```

## If you are stuck
Do not invent large workarounds. Add a `BLOCKED T##` entry to `progress/NOTES.md` (what you tried, error text),
mark the task `[!]` in PROGRESS.md, and stop.

## Layout
```
rotator/        Python package (config, db, schema.sql, dates, scheduler, service modules, routes, auth)
rotator/static/ index.html, css/, js/
tests/          pytest
scripts/        seed_demo.py, smoke.py
specs/          what to build (source of truth)
tasks/          one small task per file
progress/       PROGRESS.md, NOTES.md
```
