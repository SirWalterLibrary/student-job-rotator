# 05 — HTTP API

Flask app factory `create_app(config=None)` in `rotator/app.py`. Blueprints: `routes_roster.py`, `routes_schedule.py`,
`routes_actions.py`, `routes_admin.py`. Shared helpers in `routes_common.py` (`request_today()`, `json_error`, `require_pin`).
Static files from `rotator/static/`; `GET /` serves `index.html`. All API paths start with `/api`. JSON in, JSON out.
Dates are `YYYY-MM-DD`. Invalid JSON/fields → 400. Unknown id/date → 404. Rule violations → 409.

## Auth (details in T08)
Mutating routes (POST/PUT/PATCH/DELETE) and `/api/export` need header `X-Admin-Pin: <pin>` when `ADMIN_PIN` is set → else 401.
All GET routes except `/api/export` are public. 5 wrong PINs per minute per IP → 429.

## Read routes
| Method + path | Returns |
|---|---|
| `GET /api/health` | `{"ok": true}` |
| `GET /api/config` | `{"today":"2026-11-06","weekday":"Friday","timezone":"America/Chicago","pin_required":true,"start_date":"2026-11-07"}` |
| `GET /api/today` | see below |
| `GET /api/calendar?month=2026-11` | see below |
| `GET /api/queue` | `{"jobs": [queue_status items from 04]}` |
| `GET /api/students[?include_archived=1]` | `{"students":[{"id":1,"name":"Yusuf","active":true}]}` ordered by name (case-insensitive) |
| `GET /api/jobs[?include_archived=1]` | `{"jobs":[{"id":1,"name":"Mu'adhin","description":"","icon":"","sort_order":0,"active":true,"volunteer_ids":[1,2]}]}` |

### GET /api/today
```json
{"today":"2026-11-06","weekday":"Friday","mode":"upcoming","heading":"Next weekend",
 "sessions":[ <session view for 2026-11-07>, <session view for 2026-11-08> ],
 "next_held": null}
```
- `mode` = `"today"` when today is Sat/Sun (`sessions` has exactly one item, heading `"Today"`);
  `"upcoming"` on Mon–Fri (two items, Saturday then Sunday, heading `"Next weekend"`).
- `next_held` = the next held class-day session view, ONLY when every session in `sessions` is cancelled; else `null`.
- Session view shape is defined in 04. Cancelled sessions are included with `status: "cancelled"`.

### GET /api/calendar?month=YYYY-MM
```json
{"month":"2026-11","label":"November 2026","prev":"2026-10","next":"2026-12","sessions":[ <session view per Sat/Sun in month> ]}
```
`prev`/`next` are `null` outside the allowed window: from the month of `start_date` through 24 months after today.
A month outside the window → 400. Missing `month` → current month. Sessions before `start_date` are omitted.

## Roster routes (mutating, PIN)
| Method + path | Body | Result |
|---|---|---|
| `POST /api/students` | `{"name":"Yusuf"}` | 201 student. Name trimmed, 1–40 chars. Duplicate (case-insensitive) active → 409. Archived duplicate → re-activate, 200. |
| `PATCH /api/students/<id>` | `{"name":"Yusuf A."}` | 200 student |
| `DELETE /api/students/<id>` | — | 200 `{"ok":true}` archive (rules in 01) |
| `POST /api/jobs` | `{"name","description"?,"icon"?,"volunteer_ids"?}` | 201 job. Name 1–60 chars, description ≤ 200, icon ≤ 8 chars. `sort_order` = max+1 |
| `PATCH /api/jobs/<id>` | any of name, description, icon | 200 job |
| `DELETE /api/jobs/<id>` | — | 200 `{"ok":true}` archive |
| `POST /api/jobs/reorder` | `{"ids":[3,1,2]}` | 200; sets `sort_order` 0..n-1 in that order; ids must be exactly the active job ids |
| `PUT /api/jobs/<id>/volunteers` | `{"student_ids":[1,2,5]}` | 200 job. Replaces the set: new ids get `joined_at=now`; existing keep their `joined_at`; removed ids are deleted. Unknown/archived student → 400. |

## Action routes (mutating, PIN) — semantics in 04
| Method + path | Body | Result |
|---|---|---|
| `POST /api/sessions/<date>/absent` | `{"job_id":1,"partner_id":4?,"vacant":false?}` | 200 swap result (04) |
| `POST /api/sessions/<date>/cancel` | `{"note":"Teacher away"?}` | 200 `{"ok":true}` |
| `POST /api/sessions/<date>/restore` | — | 200 `{"ok":true}` |
| `PUT /api/sessions/<date>/assignments/<job_id>` | `{"student_id":4}` | 200 session view for that date |
| `DELETE /api/sessions/<date>/assignments/<job_id>` | — | 200 session view for that date |
| `PUT /api/settings` | `{"start_date":"2026-11-07"}` | 200 `{"start_date":...}`; must be Sat/Sun; may not be after any frozen session's date (409) |

## Admin routes
| Method + path | Notes |
|---|---|
| `POST /api/auth` | `{"pin":"1234"}` → `{"ok":true}` or 401 (rate limited). If no PIN configured → `{"ok":true}` always. |
| `GET /api/export` | PIN. Full JSON dump: `{"version":1,"exported_at":...,"tables":{"students":[...],"jobs":[...],"volunteers":[...],"sessions":[...],"assignments":[...],"settings":[...]}}` |
| `POST /api/import` | PIN. Body = export JSON. Validates `version==1`, then in one transaction deletes all rows and inserts the dump (keeping ids). 400 on bad shape; nothing changes on error. |

## Behavior every read route shares
1. `today = request_today()` (02).
2. `freeze_through(conn, today)` (04) before building anything.
3. Responses send `Cache-Control: no-store`.
