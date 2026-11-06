# T13 — Action dialogs: absent swap, shift day, manual change

Depends on: T12.
Read: `AGENTS.md`, `specs/06-ui.md` (Tab 1 teacher actions, "Dialogs"), `specs/04-schedule-service.md` (Actions), `specs/05-api.md` (Action routes).

## Create / change
- `js/actions.js`: `openAbsentDialog(session, role)`, `openShiftDialog(session)`, `openRestoreConfirm(session)`,
  `openChangeDialog(session, role)`, `clearAssignment(session, role)`. Each uses `<dialog>`, shows server `error` text inline on
  failure, and on success closes, toasts, and calls a shared `refreshAll()` (re-render the visible tab + calendar cache).
  Messages exactly as in 06 (swap toast: "{B} covers today. {A} takes it on {next date}.").
- `js/today.js`: when `isUnlocked()` and the session is today or in the future, render the action buttons:
  per row **Absent**, **Change student**, **Leave empty**; per held card **Teacher away — shift this day**; per cancelled card
  **Bring back this day**. Hide them for past sessions and when locked. `renderSessionTable(session, {editable})` handles this.
- `js/calendar.js`: the day dialog passes `editable: isUnlocked()`.
- Re-render when the lock state changes.
- `css/layout.css`: action buttons (small, 44px target), dialog forms.

## Done when (manual; `ADMIN_PIN=1234 ALLOW_TODAY_OVERRIDE=1`, demo data, `?today=2026-11-07`)
- Absent on Saturday for job J: toast appears; Tab 1 shows a "Covering for …" chip on the new student; calendar Sunday shows the
  absent student on job J with ⇄
- "Leave job empty today" → row says "No one available"; next weekend that student is first in line (check Fairness panel)
- Shift Saturday: Saturday card shows "No class — the teacher is away."; calendar cell shows pattern; Sunday's roles equal what
  Saturday's were before; "Bring back this day" restores
- Change student: only volunteers not busy today are listed
- Locked viewers see no buttons; a 401 re-locks the UI
- `pytest -q` passes

## Don't
Change backend behavior. If the UI needs something the API doesn't give, write it in NOTES.md and stop.
