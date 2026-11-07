# NOTES

Agent: append here. Keep entries short and dated.

## Deviations from the spec
(none yet) — if you had to differ from a spec file, say which file, what you did, and why.

## BLOCKED
- BLOCKED sync: T00 — `git push -u origin HEAD` failed: `fatal: could not read Username for 'https://github.com': Device not configured` (remote https://github.com/SirWalterLibrary/student-job-rotator.git; no stored credentials). The earlier `git pull --rebase` also failed only because origin has no branches yet and the local branch had no upstream. Commit 7473da5 ("T00: scaffold, config, health endpoint, pytest fixtures") is local; push it once GitHub credentials are available.
- BLOCKED sync: T01 (2026-11-06) — same auth failure on `git push -u origin HEAD`: `fatal: could not read Username for 'https://github.com': Device not configured`. `git fetch` succeeds (public repo) but origin still has no branches, so `git pull --rebase` fails only for lack of upstream. Local commits 7473da5 (T00), c6fd7d6 (T00 note), c09915c (T01) are unpushed; push them once GitHub push credentials are configured.

## Ideas for later (do NOT build now)
- Student view that highlights "my next turn"
- Printable month PDF
- Per-job rotation history page
