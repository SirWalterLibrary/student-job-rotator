# T10 — Tab 1: Today / Next Weekend

Depends on: T09.
Read: `AGENTS.md`, `specs/06-ui.md` ("Tab 1" section), `specs/07-theme.md` (Components: card, table, badges), `specs/04-schedule-service.md` (Session view).

## Create / change
- `js/today.js`: `renderToday(panelEl)`:
  - `GET /api/today`, show skeleton while loading, friendly error + Retry on failure
  - for each session build a day card per the spec: title, Hijri line, badge (Today/Upcoming), table with Job and Student columns,
    chips for `swap` and `manual`, muted "No one available" for null students, cancelled-day card with `next_held` message,
    empty-roster message
  - export `renderSessionTable(session, {editable})` so the calendar day dialog (T11) can reuse it; `editable` is false for now
  - Saturday extra line "Tomorrow: Sunday, November 8" under the card (only when mode is today and today is Saturday)
  - auto refresh: every 5 min and on `visibilitychange`; if `today` differs from the previous response, reload `/api/config` and re-render
- `css/layout.css`: day card, table, chips, badges, cancelled card (rules from 07).
- `js/api.js`: if `location.search` contains `today=YYYY-MM-DD`, append it to every GET (preview of other days; the server ignores
  it unless `ALLOW_TODAY_OVERRIDE=1`).
- `js/app.js`: call `renderToday` when tab 1 is shown.

## Done when
Seed with the demo script from T15 or by hand via curl, then:
- `?today=2026-11-06` (Friday) → "Next Weekend" tab with a Saturday card and a Sunday card
- `?today=2026-11-07` → "Today" tab with ONE card
- Cancelled day (insert via sqlite) → muted card with next class day text
- The page works at 360px; student names are large and readable
- `pytest -q` still passes

## Don't
Add teacher action buttons (T13) or touch the calendar.
