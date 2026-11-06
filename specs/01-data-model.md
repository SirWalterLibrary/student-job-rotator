# 01 — Data model

SQLite file at `$DATA_DIR/rotator.db` (default `./data/rotator.db`; in Docker `/data/rotator.db` on a named volume).
Every connection: `PRAGMA foreign_keys=ON`, `PRAGMA journal_mode=WAL`, `PRAGMA busy_timeout=5000`, `row_factory=sqlite3.Row`.
Create tables on startup from `rotator/schema.sql` (idempotent, `IF NOT EXISTS`).
`created_at` / `joined_at` = UTC ISO string with microseconds, e.g. `2026-11-06T18:04:11.123456+00:00`.

## rotator/schema.sql
```sql
CREATE TABLE IF NOT EXISTS students (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE COLLATE NOCASE,
  active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS jobs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE COLLATE NOCASE,
  description TEXT NOT NULL DEFAULT '',
  icon TEXT NOT NULL DEFAULT '',
  sort_order INTEGER NOT NULL DEFAULT 0,
  active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS volunteers (
  job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
  joined_at TEXT NOT NULL,
  PRIMARY KEY (job_id, student_id)
);

CREATE TABLE IF NOT EXISTS sessions (
  date TEXT PRIMARY KEY,
  status TEXT NOT NULL DEFAULT 'held' CHECK (status IN ('held','cancelled')),
  frozen INTEGER NOT NULL DEFAULT 0,
  note TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS assignments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  date TEXT NOT NULL,
  job_id INTEGER NOT NULL REFERENCES jobs(id),
  student_id INTEGER NOT NULL REFERENCES students(id),
  source TEXT NOT NULL CHECK (source IN ('auto','swap','manual')),
  note TEXT NOT NULL DEFAULT '',
  group_id TEXT,
  created_at TEXT NOT NULL,
  UNIQUE (date, job_id),
  UNIQUE (date, student_id)
);

CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
```
`UNIQUE (date, student_id)` enforces "one role per student per day" at the database level.
`UNIQUE (date, job_id)` enforces one student per job per day.

## Meaning of the columns
- `sessions` rows exist only when needed: a cancelled day, or a frozen day. A class day with no row is a normal, not-yet-frozen day.
- `assignments.source`: `auto` = written by the freeze step (only on dates <= today); `swap` = made by an absence swap
  (two rows share a `group_id`, one on each day); `manual` = teacher override.
- Future `auto` assignments are NEVER stored. They are computed on read ("projected").
- `settings` keys: `start_date` (ISO date, a Saturday or Sunday).

## Archive rules (nothing is hard-deleted from the UI)
- Archive student: `students.active=0`; delete their `volunteers` rows; delete their `assignments` rows with `date > today`.
- Archive job: `jobs.active=0`; delete its `assignments` rows with `date > today`. Old assignments stay for history.
- Re-adding an archived name re-activates the same row (keeps history linked).

## Python helpers (rotator/db.py)
```python
def connect(path: str) -> sqlite3.Connection
def init_db(conn) -> None                      # runs schema.sql
def get_setting(conn, key, default=None) -> str | None
def set_setting(conn, key, value) -> None
def utc_now_iso() -> str
```
Flask: one connection per request stored on `flask.g`, closed in `teardown_appcontext`.
`create_app(config: dict | None = None)` accepts overrides such as `DATA_DIR`, `ADMIN_PIN`, `ALLOW_TODAY_OVERRIDE`.

## Config (rotator/config.py, read from environment)
| Env var | Default | Meaning |
|---|---|---|
| `DATA_DIR` | `./data` | folder for rotator.db (created if missing) |
| `ADMIN_PIN` | empty | teacher PIN; empty = editing open |
| `APP_ENV` | `development` | `production` requires non-empty `ADMIN_PIN` or the app refuses to start |
| `ALLOW_TODAY_OVERRIDE` | `0` | `1` lets `?today=YYYY-MM-DD` override today (tests / previews only) |
| `TRUST_PROXY` | `0` | `1` trusts one `X-Forwarded-For` hop (Nginx Proxy Manager) |
