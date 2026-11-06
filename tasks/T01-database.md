# T01 — SQLite schema, db helpers, settings

Depends on: T00.
Read: `AGENTS.md`, `specs/01-data-model.md`.

## Create / change
- `rotator/schema.sql` — copy the SQL from 01 exactly.
- `rotator/db.py`: `connect(path)`, `init_db(conn)`, `get_setting`, `set_setting`, `utc_now_iso`
  (signatures in 01). `connect` applies the PRAGMAs and `row_factory`.
- `rotator/app.py`: add `get_conn()` (stores a connection on `flask.g`, path `DATA_DIR/rotator.db`), a `teardown_appcontext`
  that closes it, and call `init_db` once inside `create_app`.
- `tests/test_db.py`

## Tests
- `test_schema_creates_all_tables` (query `sqlite_master`)
- `test_init_db_is_idempotent` (call twice)
- `test_foreign_keys_enforced` (insert a volunteer with a missing job → `sqlite3.IntegrityError`)
- `test_unique_student_per_day` (two assignments same date + student, different jobs → IntegrityError)
- `test_unique_job_per_day`
- `test_names_unique_case_insensitive` (students "Yusuf" and "yusuf" → IntegrityError)
- `test_settings_roundtrip` (`get_setting` default, `set_setting` twice overwrites)
- `test_data_persists_between_connections` (write, close, reopen the file, read)

## Done when
`pytest -q` passes (all earlier tests too).

## Don't
Create routes or business logic.
