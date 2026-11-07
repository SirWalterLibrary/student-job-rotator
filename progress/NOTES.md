# NOTES

Agent: append here. Keep entries short and dated.

## Deviations from the spec
- T03: added a one-line module docstring to `rotator/scheduler.py` (AGENTS.md requires docstrings; the spec's code block has none). Algorithm copied verbatim, unchanged.
- T04: spec 05 defines duplicate handling only for POST /api/students; I applied the same rule to jobs (active duplicate → 409; archived duplicate → re-activate, 200) following spec 01's general "re-adding an archived name re-activates the same row". Also: archiving a job keeps its `volunteers` rows (spec 01 only requires deleting future assignments) so re-activating restores the roster. `create_app` imports the roster blueprint lazily to avoid an app↔routes import cycle.
- T05: spec 04 documents `walk` as returning `dict[date, dict]`, but the task file instructs returning `(results, last_served)` — I follow the task file (internal-only API; `queue_status` needs the final `last_served`). Also `queue_status` shows each student's `last_served` from that final dict (so a projected pick for the next class day shows that date) rather than the DB's MAX(date); this keeps the displayed date consistent with the queue ordering the spec derives from the same dict.

## BLOCKED
- BLOCKED sync: T00 — `git push -u origin HEAD` failed: `fatal: could not read Username for 'https://github.com': Device not configured` (remote https://github.com/SirWalterLibrary/student-job-rotator.git; no stored credentials). The earlier `git pull --rebase` also failed only because origin has no branches yet and the local branch had no upstream. Commit 7473da5 ("T00: scaffold, config, health endpoint, pytest fixtures") is local; push it once GitHub credentials are available.
- BLOCKED sync: T01 (2026-11-06) — same auth failure on `git push -u origin HEAD`: `fatal: could not read Username for 'https://github.com': Device not configured`. `git fetch` succeeds (public repo) but origin still has no branches, so `git pull --rebase` fails only for lack of upstream. Local commits 7473da5 (T00), c6fd7d6 (T00 note), 3f6208a (T01) are unpushed; push them once GitHub push credentials are configured.

## Ideas for later (do NOT build now)
- Student view that highlights "my next turn"
- Printable month PDF
- Per-job rotation history page
