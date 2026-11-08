# T18 — Fix drawer scrolling and oversized form fields

Depends on: T17.
Read: `AGENTS.md`, `specs/06-ui.md` ("Teacher tools drawer"), `specs/07-theme.md` (Dialogs/drawer). Then open `css/layout.css` and `js/manage.js`.

## Reported bugs (from the teacher, with screenshots)
1. In the Teacher tools panel the **Students** section does not scroll. After adding about 4 students, the "New student name" box
   and the **Add student** button are cut off and cannot be reached.
2. In **Jobs**, the "Job name", "Short description" and "Icon" fields are huge empty white boxes (as tall as a text area).
3. Other sections are also clipped at the bottom (the Import file chooser is cut off).

## Likely causes — CONFIRM before changing code
- A section body has a fixed `height`/`max-height` with `overflow: hidden`, or the drawer is `height: 100vh` while its children are
  `flex: 1` and shrink. Look for these in `css/layout.css` for the drawer and the accordion section selectors.
- The job form inputs stretch because they sit in a flex/grid container with `align-items: stretch` and `flex: 1` in a column with
  a fixed height, or the inputs have no explicit height.

## Fix
1. Drawer structure (`#drawer`):
   - `position: fixed; top: 0; right: 0; bottom: 0; width: min(420px, 100vw); display: flex; flex-direction: column;`
   - Header (title + X button): `flex: 0 0 auto`, stays visible.
   - Content wrapper (`.drawer-body`, add it if missing): `flex: 1 1 auto; min-height: 0; overflow-y: auto; overscroll-behavior: contain;`
     This is the ONLY scrolling area. The whole list of sections scrolls as one column.
2. Accordion sections: no fixed `height` or `max-height`, no `overflow: hidden` on the section body (only on the rounded outer
   border if needed, using `overflow: clip`). Sections grow to fit their content.
3. Students list: if it has more than ~8 names, it may use `max-height: 40vh; overflow-y: auto` **inside** its own box, but the
   "New student name" input and **Add student** button must stay below the list and always be reachable (render the add form
   ABOVE the list so it never scrolls out of view).
4. Forms: inputs are single-line `<input>` elements, `height: 44px`, `width: 100%`, `box-sizing: border-box`. Remove any
   `flex: 1`/`height: 100%` on them. Only the description may be a `<textarea rows="2">` if you want multi-line.
   Add `gap: .5rem` between fields; labels above fields.
5. Student rows and job rows must wrap at 360px wide without clipping the Rename/Remove buttons (`flex-wrap: wrap`).
6. When the drawer opens, focus the first control and scroll the body to the top.
7. Do not change backend code or API calls.

## Tests / checks
- Add a test in `tests/test_static_assets.py`: `test_drawer_body_scrolls` asserts `css/layout.css` contains `overflow-y: auto` and
  that no rule for the accordion section body contains `max-height` with `overflow: hidden` (a simple regex check is enough).
- Manual, with the demo seed (`python scripts/seed_demo.py --data ./data --reset`) and a PIN set:
  - Add 10 more students quickly: the add box and button stay reachable and the drawer scrolls with the mouse wheel and on touch
  - Expand a job with 10+ students: the volunteer checkbox list is fully reachable by scrolling
  - Job form fields are single-line height; Import file chooser is fully visible at the bottom
  - 360px and 1200px widths; no horizontal scroll; focus ring visible

## Done when
`pytest -q` passes and all manual checks are OK.

## Don't
Change open/close behaviour (done in T17) or any backend code.
