# T12 — Teacher tools drawer: students, jobs, volunteers, up-next, settings

Depends on: T08, T10, T11.
Read: `AGENTS.md`, `specs/06-ui.md` ("Teacher tools drawer" and "Unlock / PIN"), `specs/05-api.md` (Roster routes, queue, settings, export/import).

## Create / change
- `js/auth.js`: `isUnlocked()`, `unlock(pin)` (POST `/api/auth`, store PIN on success), `lock()`, and the PIN dialog UI.
  `config.pin_required === false` → always unlocked. Listen for `kr:locked` and re-lock + reopen the PIN dialog.
  Header button toggles "Teacher login" / "Lock".
- `js/manage.js`: `openDrawer()` builds the four accordion sections from 06 using the API:
  1. Students — list, add (Enter submits), rename, remove with confirm
  2. Jobs — list with ▲/▼ reorder, add form (name, description, icon), expand to edit + volunteer checkbox list (saves on change),
     remove with confirm
  3. Fairness & up next — `/api/queue`: ordered names, turns, last served; highlight first; single-volunteer hint; help text
  4. Settings — start date (YYYY-MM-DD date input; show server error if not Sat/Sun), Export backup (download JSON blob via
     `<a download>`), Import backup (file input + confirm)
- Focus trap, Esc to close, return focus to the opener, full-width on phones.
- After any successful change: toast "Saved ✓", refresh the drawer sections and re-render the visible tab.
- `css/layout.css`: drawer, accordion, forms, checkbox lists.
- `js/app.js`: wire the Teacher-tools button.

## Done when (manual, with a PIN set: `ADMIN_PIN=1234 flask run`)
- Viewer (locked) cannot open the drawer; after PIN it opens; wrong PIN shows an error message
- Add 3 students, a job, tick 3 volunteers; reload the page: data is still there; Tab 1 shows the job with a student
- Removing a student removes them from the volunteer lists; reordering jobs changes table order
- Export downloads a JSON file; Import restores it
- No `innerHTML` with user data anywhere (`grep -n innerHTML rotator/static/js` shows none or only constant strings)
- `pytest -q` passes

## Don't
Implement swap/shift/manual dialogs (T13).
