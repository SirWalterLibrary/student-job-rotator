# Khidmah Roster

A weekend class-job rotator with an Islamic theme, for a small classroom. Every class day
(Saturday and Sunday) each student is assigned each khidmah (service role) in turn. The app
is deterministic — no randomness, no "free riders" — and runs completely offline on the
classroom LAN (no npm, no CDNs, no external fonts).

## What it does

- **Tab 1 (Today / Next Weekend).** On a class day it shows today's Job→Student table; on a
  weekday it previews the coming Saturday and Sunday.
- **Tab 2 (Calendar).** The month's class days in a grid (stacked on narrow screens). Every
  cell shows the assigned roles; weekends before the first class are dimmed. Click a
  weekend for the full day in a dialog.
- **Teacher tools (PIN).** A drawer with Students, Jobs + volunteers, a live Fairness queue
  ("up next" per job), and Settings (start date, roster export/import). Buttons appear on
  Tab 1 and on calendar day dialogs.
- **Fairness (spec 03).** For every job, the student who has *not* done it the longest goes
  next; a student who never had the job goes before anyone who has. Volunteers for a job
  take it before the general queue. Nobody gets two jobs on the same day.
- **Absence.** A student who can't serve swaps with a partner who covers that day and takes
  the job on the next class day (marked with ⇄ in the calendar).
- **Teacher away.** "Shift this day" assigns nothing; everyone's turn moves to the next
  class day. Restore brings the day back.
- Everyone with the link can *view*; only the teacher PIN can *edit*.

## Run it locally

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# optional: seed a 10-student / 6-job demo roster (10 named students, overlapping
# volunteers, start date 2026-11-07). Use --reset to wipe and reseed.
python scripts/seed_demo.py --data ./data

DATA_DIR=./data ADMIN_PIN=1234 ALLOW_TODAY_OVERRIDE=1 \
  flask --app wsgi run --port 5055 --debug
```

Open `http://localhost:5055`. Without the seed, add students and jobs in **Teacher tools**
(PIN `1234`); the app stays useful from an empty roster. Tests: `pytest -q` (110).
Smoke: `python scripts/smoke.py` — runs the whole 12-week determinism/swap/shift battery
in-process and prints `SMOKE OK`.

## Run with Docker

Local dev container (data persists in the `rotator_data` volume):

```bash
docker compose -f docker-compose.dev.yml up --build -d
docker compose -f docker-compose.dev.yml down   # stop it later; the data stays in the volume
```

Then open `http://localhost:5055` (PIN `1234` unlocks the teacher tools).

Home server (behind Nginx Proxy Manager — full steps in `tasks/T16-deploy-home-server.md`):

```bash
git clone <repo> ~/docker/job-rotator && cd ~/docker/job-rotator
cp .env.example .env      # then set ADMIN_PIN to a real PIN (at least 6 digits)
docker compose up -d --build
```

No host port is published; Nginx Proxy Manager reaches the container by name on the
`npm_net` network. In production the server refuses to boot without `ADMIN_PIN`
(dev/`flask run` auto-sets `1234` and says so in the log).

## The teacher PIN

- `ADMIN_PIN` is read at boot. Omit it and the app generates a random 6-digit PIN and
  prints it to the log once.
- Wrong PIN → 401; 5 wrong PINs from one address → 60-second lockout (429).
- In the UI the PIN dialog also unlocks the teacher drawer and all buttons.

## Preview other days (dev only)

Set `ALLOW_TODAY_OVERRIDE=1` and append `?today=2026-11-07` (any ISO date) to the URL to
see what the app would show on that day — e.g. preview a Saturday from your Wednesday
morning. **Production ignores `?today`** — "today" always comes from the server's Central
timezone clock (America/Chicago). The browser never computes dates itself.

## Data and backups

Everything lives in one SQLite file: `data/rotator.db` (Docker: the `rotator_data`
volume). To back up, copy that file (or `sqlite3 data/rotator.db ".backup backup.db"`).
To move to a new machine, put the file back in `data/` (or the volume) and start the app.
The in-app **Settings → Export** downloads a JSON backup of the whole roster
(students, jobs, volunteers, schedule, settings); **Import** restores it.

## Build status

T00–T15 are done (110 tests + smoke + the acceptance checklist in `specs/09-acceptance.md`).
The only remaining task, **T16 — deploy to your home server**, is a human-run checklist in
`tasks/T16-deploy-home-server.md`; it needs your machine, your Nginx Proxy Manager and your
domain, so no agent can do it for you.

To continue agent work: `./run_task.sh` prints the prompt for the next unchecked task in
`progress/PROGRESS.md` (paste it into a fresh Pi session — one task per session, per
`AGENTS.md`).

## Where the specs are

`specs/` is the source of truth: `00-overview` (goals, decisions), `01-schema`,
`02-dates`, `03-scheduler`, `04-schedule-service`, `05-actions`, `06-api`, `07-frontend`,
`08-docker`, `09-acceptance` (the manual checklist this project was accepted against).
`tasks/` holds the T00–T16 build log; `progress/` tracks what is done; `AGENTS.md` has the
rules the build agent worked under.
