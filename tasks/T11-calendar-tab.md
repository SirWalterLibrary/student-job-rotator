# T11 — Tab 2: Monthly calendar

Depends on: T09, T10.
Read: `AGENTS.md`, `specs/06-ui.md` ("Tab 2" section), `specs/07-theme.md` (Calendar cells), `specs/05-api.md` (`/api/calendar`).

## Create / change
- `js/calendar.js`: `renderCalendar(panelEl, monthIso)`:
  - `GET /api/calendar?month=...`; skeleton/error states as in Tab 1
  - toolbar: ‹ Previous, month label + approximate Hijri month range, Next ›, This month (disabled when API gives `null`)
  - Monday-first grid (`repeat(5, .45fr) 2fr 2fr`) with weekday header; leading/trailing days of neighbouring months are blank.
    Only Saturday/Sunday cells of this month have role lists (`Job — Student`, one line each, ellipsis); Mon–Fri cells show the
    day number only, dimmed.
  - cell states: today ring, past dimmed, cancelled pattern + "No class", ⇄ mark with `title` for swap rows
  - clicking or pressing Enter on a weekend cell opens the day dialog (`<dialog id="dialog">`) containing the Tab 1 table via
    `renderSessionTable(session, {editable:false})` and a Close button
  - month in `location.hash` (`#calendar/2026-12`); initial month = current month from `config.today`
  - narrow screens (<700px): hide Mon–Fri cells; render each weekend as a stacked block "Weekend of Nov 7" (CSS only if possible,
    otherwise a second render path under a `matchMedia` listener)
  - `@media print` rules per spec
- `css/layout.css`: grid and cell styles.

## Done when
With demo data and `?today=2026-11-06`:
- November 2026 shows weekends 7/8, 14/15, 21/22, 28/29 with different students; December works via Next; "This month" returns
- Previous is disabled on the month of `start_date`; Next disabled at the 24-month limit
- Cancelled day shows pattern and "No class"; swapped student shows ⇄
- Keyboard: Tab to a weekend cell, Enter opens dialog, Esc closes, focus returns to the cell
- 360px layout stacks weekends with no horizontal scroll; print preview is legible black-on-white
- `pytest -q` passes

## Don't
Add editing features or the drawer.
