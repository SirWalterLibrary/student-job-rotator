# 00 — Overview

**App name:** Khidmah Roster (خدمة = "service"). A weekend class-jobs rotator for one teacher and his students.
The teacher manages jobs and volunteers. Anyone with the link can view who has which job. Rotation is fair,
predictable and visible, so no student ever feels skipped.

## Requirement map (teacher's original 13 points)
| # | Requirement | Specified in |
|---|---|---|
| 1 | Add jobs, add students who volunteer for each job | 05-api (roster), 06-ui (Teacher tools drawer) |
| 2 | Islamic theme | 07-theme |
| 3 | Rotating schedule for both Saturday and Sunday | 03-scheduler, 04-schedule-service |
| 4 | No repeat of a role until every other volunteer has had a turn | 03-scheduler |
| 5 | Never two roles for one student on the same day | 03-scheduler |
| 6 | Table of jobs and current students on Saturday/Sunday | 06-ui (Tab 1) |
| 7 | Central Time, Minnesota | 02-dates |
| 8 | Calendar of the rotation per weekend, split by month | 06-ui (Tab 2) |
| 9 | Student absent → switch with another student the next day | 04-schedule-service (`swap_absent`) |
| 10 | Shift a day when the teacher is away | 04-schedule-service (`cancel_session`) |
| 11 | Two tabs: current roles, calendar | 06-ui |
| 12 | Weekday shows next Sat/Sun; Sat/Sun shows today | 05-api `/api/today`, 06-ui |
| 13 | Data survives refresh | 01-data-model (SQLite on a Docker volume) |

## Glossary
- **Session** = one class day: a Saturday or a Sunday.
- **Job** = a classroom role (e.g. Mu'adhin). Each active job needs exactly one student per session.
- **Volunteer** = a student who offered to do a particular job. A student may volunteer for many jobs.
- **Queue** = for one job, its volunteers ordered by "least recently served first".
- **Frozen session** = a session dated today or earlier. Its assignments are stored and never recomputed.
- **Projected** = a future assignment computed on demand (not stored). It can change if the roster changes.
- **Locked row** = a stored assignment on a future date created by a swap or manual change.

## Decisions (defaults — change only if the teacher says so)
- **D1** Saturday and Sunday are separate sessions. Each active job is done by one student per session.
- **D2** Fair = per job, least-recently-served first. Never-served volunteers go first, in the order they volunteered.
  No randomness, so anyone can predict who is next.
- **D3** One role per student per session is a hard rule. If every volunteer of a job is busy, the job shows
  "No one available" and nobody is forced into two roles.
- **D4** A student may serve on Saturday and also on Sunday (different days). The one-role rule is per day.
- **D5** Absent student A (role J on day D): A is swapped with partner B. B covers J on day D,
  A does J on the next class day N. Default B = whoever was projected for J on N. See 04.
- **D6** Teacher away on day D: the day is cancelled. Everyone's turn shifts to the next class day automatically
  because cancelled days consume no turns. See 04.
- **D7** Sessions dated today or earlier are frozen (stored). Future sessions are recomputed from the current roster.
- **D8** Rotation starts at a `start_date` setting (default: first class day on or after the first time the app runs).
- **D9** Viewing is open to anyone with the link. Editing needs the teacher's PIN (`ADMIN_PIN`). Empty PIN = open (dev only).
- **D10** "Remove" student/job = archive (history is kept).
- **D11** Hijri dates are shown next to Gregorian dates, computed in the browser, labelled approximate.

## Non-goals (v1)
Student logins, notifications/email, multiple classes, attendance tracking beyond the swap action, native apps.
