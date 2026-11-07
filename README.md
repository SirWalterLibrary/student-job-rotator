# Khidmah Roster — build kit

A weekend (Saturday/Sunday) class-job rotator with an Islamic theme. This folder is the **plan**: specs, small tasks and a
progress tracker for your Pi agent (qwen3.8-27b) to build the app one task per session. Code appears in `rotator/`, `tests/`
and `scripts/` as tasks are completed.

```
AGENTS.md           rules + session protocol the agent reads first
specs/              what to build (00 overview … 09 acceptance checklist)
tasks/              T00–T16, one small task each
progress/           PROGRESS.md (status table), NOTES.md (deviations, blockers)
run_task.sh         prints the prompt for the next unchecked task
```

## How to run a task
```bash
./run_task.sh            # prints the prompt for the next [ ] task, e.g. "Read AGENTS.md, then do task T00 ..."
# paste it into a fresh Pi session, or: PI_CMD="<your pi command>" ./run_task.sh
```
One task per fresh session. When it finishes the agent ticks `progress/PROGRESS.md` and commits. Review, then start the next.

## Build order
Backend first (T00–T08, all tested with pytest), then UI (T09–T13), then Docker (T14), polish/acceptance (T15), and the
server deployment checklist for you (T16). You can open the app in a browser from T09 onwards:
`DATA_DIR=./data ALLOW_TODAY_OVERRIDE=1 flask --app wsgi run --port 5055 --debug`, then add `?today=2026-11-07` to the URL to
preview a Saturday.

## Run with Docker

Local dev container (data persists in the `rotator_data` volume):
```bash
docker compose -f docker-compose.dev.yml up --build -d
docker compose -f docker-compose.dev.yml down   # stop it later; the data stays in the volume
```
Then open `http://localhost:5055` (PIN `1234` unlocks the teacher tools).

Home server (`~/docker/job-rotator/`, behind Nginx Proxy Manager — full steps in `tasks/T16-deploy-home-server.md`):
```bash
git clone <repo> ~/docker/job-rotator && cd ~/docker/job-rotator
cp .env.example .env      # then set ADMIN_PIN to a real PIN
docker compose up -d --build
```
No host port is published; Nginx Proxy Manager reaches the container by name on the `npm_net` network.

## How the fairness works (plain language)
- Per job, whoever has waited longest goes next. Someone who never had that job goes before anyone who has.
- Nobody gets two jobs on the same day.
- Absent student: another volunteer covers today and the absent student takes the job on the next class day.
- Teacher away: shift the day. Nothing is assigned; everyone's turn moves to the next class day.
- Saturday and Sunday are separate days. Weekdays show the coming Saturday and Sunday; on a weekend, tab 1 shows today.
- Editing needs your PIN; anyone with the link can view.

## Defaults I assumed (change in `specs/00-overview.md` before building if wrong)
See "Decisions" D1–D11 in `specs/00-overview.md`.
