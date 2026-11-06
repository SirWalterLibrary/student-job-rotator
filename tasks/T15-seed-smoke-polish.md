# T15 — Demo seed, smoke script, acceptance pass, polish

Depends on: T13 (T14 optional).
Read: `AGENTS.md`, `specs/09-acceptance.md`, `specs/03-scheduler.md` ("Known consequences").

## Create
- `scripts/seed_demo.py`: `python scripts/seed_demo.py --data ./data [--reset]`
  Seeds fake data (never real students): 10 students — Yusuf, Maryam, Ibrahim, Aisha, Omar, Fatima, Hamza, Khadija, Bilal, Zainab;
  6 jobs with icons and volunteers (overlapping): Mu'adhin 🕌 (Yusuf, Omar, Hamza, Bilal), Qur'an recitation 📖
  (Maryam, Aisha, Khadija, Fatima, Zainab), Du'a leader 🤲 (Ibrahim, Yusuf, Maryam, Bilal), Board cleaner 🧽 (Omar, Fatima, Hamza),
  Line leader 🚶 (Aisha, Ibrahim, Zainab, Khadija), Shoe rack helper 👟 (Hamza, Fatima, Bilal, Zainab, Omar).
  Set `start_date` 2026-11-07. Uses `rotator.db` functions, not raw SQL strings copied around.
- `scripts/smoke.py`: runs the API in-process (Flask test client, temp DB, `ALLOW_TODAY_OVERRIDE`), seeds the demo data, then
  for `today` = each Saturday of 12 weekends: GET `/api/today` and assert
  (a) no student appears twice on the same day, (b) for every job each pick was the oldest-served available volunteer
  (use `/api/queue` before each Saturday to check the first in line is picked unless busy), (c) a Saturday cancel followed by
  restore returns the same roles, (d) an absent-swap results in the absent student holding the job on Sunday. Prints "SMOKE OK".
- Fix `specs/09-acceptance.md` row 4 wording if your smoke script checks something slightly different; note it in NOTES.md.

## Polish pass (small fixes only)
- Walk the whole checklist in `specs/09-acceptance.md` manually with `?today=` for Fri/Sat/Sun and fix bugs you find.
- Check 360px, keyboard-only use, console errors, empty database states.
- Write the final `README.md` (what it is, local run, Docker, PIN, backup, how to preview other days, where the specs are).

## Done when
- `pytest -q` and `python scripts/smoke.py` pass
- Every row of the acceptance table is verified; any exception listed in NOTES.md
- `git status` is clean after commit

## Don't
Add features. Log only to NOTES.md ideas that aren't in the spec.
