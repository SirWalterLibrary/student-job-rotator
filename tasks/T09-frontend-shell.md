# T09 — Frontend shell, Islamic theme, tabs

Depends on: T06.
Read: `AGENTS.md`, `specs/06-ui.md` ("Page frame" only), `specs/07-theme.md`.

## Create
- `rotator/static/index.html`: header plate (Bismillah, title, subtitle), Teacher-tools button (inert for now), tablist with two
  tabs and two `role="tabpanel"` sections (`#panel-today`, `#panel-calendar`), footer, empty `<dialog id="dialog">` and
  `<aside id="drawer" hidden>` placeholders. `<script type="module" src="js/app.js">`.
- `css/theme.css` (tokens, body pattern, typography, header plate, footer, buttons, badges, skeleton, `.sr-only`) and
  `css/layout.css` (page container max-width 960px, tabs, card base, responsive rules).
- `js/dom.js`: `h(tag, attrs, ...children)` (children: strings → text nodes, never HTML), `toast(message)`, `clear(el)`.
- `js/api.js`: `api.get(path)`, `api.send(method, path, body)` (JSON, adds `X-Admin-Pin` from `sessionStorage` key `kr_pin`),
  throws `ApiError(message, status)` using the server's `error` field. On 401 clears the stored PIN and dispatches
  `window` event `kr:locked`.
- `js/dates.js`: `weekdayName`, `monthName`, `longDate("2026-11-07") -> "Saturday, November 7, 2026"`, `shortDate -> "Nov 7"`,
  `hijriDate(iso)` per 02. Parse ISO with `Date.UTC`, never `new Date("YYYY-MM-DD")` (timezone bug).
- `js/app.js`: fetch `/api/config`, store as `state.config`; set tab-1 label ("Today" or "Next Weekend" via `/api/today` `mode`; fetch it
  once at boot); tab switching with ARIA attributes, arrow keys, and `location.hash` (`#today`, `#calendar`, `#calendar/YYYY-MM`);
  each panel temporarily shows placeholder text "Loading…". Export `state` for other modules.

## Done when
- `flask run` → page shows the themed header, two working tabs, correct tab label, no console errors, looks right at 360px and 1200px
- Reload keeps the selected tab (hash)
- `pytest -q` still passes
- Manually check: tab key order is logical; focus ring visible

## Don't
Render roles/calendars (T10, T11) or build the drawer (T12). No external fonts/CDNs. No `innerHTML` with data.
