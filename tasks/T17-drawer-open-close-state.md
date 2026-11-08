# T17 — Fix drawer: X button, blank panel after refresh, lock state

Depends on: T13 (all earlier tasks done).
Read: `AGENTS.md`, `specs/06-ui.md` ("Teacher tools drawer" and "Unlock / PIN"). Then open `rotator/static/index.html`,
`css/layout.css`, `js/manage.js`, `js/auth.js`, `js/app.js`.

## Reported bugs (from the teacher, with screenshots)
1. The **X** button in the Teacher tools panel does nothing. The panel must close.
2. After a page refresh while unlocked, the right-hand panel shows as a **blank cream column** and the header shows "Lock".
   The teacher must click Lock, then unlock again, to get a working page.
3. Refreshing should never open the drawer. A refresh while unlocked should keep the teacher unlocked (PIN is in
   `sessionStorage` key `kr_pin`) and show the normal page with the drawer closed.

## Likely causes — CONFIRM each one before changing code
- **A. `hidden` is overridden by CSS.** `#drawer` (or `.drawer`) probably has `display: flex/grid/block`, which beats the HTML
  `hidden` attribute, so the drawer is always visible and "close" (`drawer.hidden = true`) has no effect. The empty blank panel on load
  is the drawer being visible before `openDrawer()` ever filled it.
  Check with: `grep -n "drawer" rotator/static/css/layout.css` and look for a `display:` on the drawer selector.
- **B. Close handler.** Make sure the X button has a click handler that closes the drawer, and Esc does too. Check it is wired once
  (not re-bound on every open) and that it also works after the drawer has been opened twice.
- **C. Boot order.** On load, `app.js` / `auth.js` may render the unlocked UI (Lock button) without building or hiding the drawer.
  The drawer's contents must only be built inside `openDrawer()`, and the drawer must start closed.

## Fix
1. Add at the top of `css/theme.css`: `[hidden] { display: none !important; }`.
2. Create one pair of functions in `js/manage.js`: `openDrawer()` and `closeDrawer()`.
   - `closeDrawer()`: set `drawer.hidden = true`, set `aria-hidden="true"`, remove the body class `drawer-open` if you use one,
     and return focus to the Teacher tools button.
   - `openDrawer()`: build/refresh content, set `hidden = false`, `aria-hidden="false"`, move focus to the drawer's X button.
   - X button click and Esc key both call `closeDrawer()`. Clicking outside the drawer (on a dim backdrop, if one exists) also closes it.
3. On boot (`app.js`), always call `closeDrawer()` first, so the drawer is closed after every refresh.
4. Lock state on refresh:
   - `isUnlocked()` returns true if `config.pin_required === false` OR `sessionStorage.kr_pin` exists.
   - On boot, if a stored PIN exists, verify it once with `POST /api/auth`. If it succeeds, stay unlocked (header shows "Lock").
     If it fails with 401, clear the PIN, show "Teacher login".
   - Header button must always match the real state. After refresh, no manual Lock → Unlock should be needed.
5. Clicking **Lock** also calls `closeDrawer()` and re-renders the visible tab (teacher buttons disappear).
6. Do not change backend code.

## Tests / checks
- Add `tests/test_static_assets.py`:
  - `test_hidden_attribute_rule_present`: read `rotator/static/css/theme.css`, assert it contains `[hidden]` and `display: none`.
  - `test_drawer_markup_starts_hidden`: read `index.html`, assert the drawer element has the `hidden` attribute.
- Manual (start `ADMIN_PIN=1234 flask --app wsgi run --port 5055`):
  - Unlock, open Teacher tools, click X → panel disappears, page is full width again
  - Open again, press Esc → closes
  - Unlock, refresh (F5) several times → drawer closed, header says "Lock", teacher buttons still work, no blank column
  - Click Lock → header says "Teacher login"; refresh → still locked
  - Open a new private window → locked, no teacher buttons
  - Browser console has no errors

## Done when
`pytest -q` passes and every manual check above is OK. Log the confirmed root cause (A, B, C or something else) in `progress/NOTES.md`.

## Don't
Change the scrolling or form layout inside the drawer (that is T18).
