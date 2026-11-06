# T14 — Dockerize (dev + prod compose)

Depends on: T08, T13 (works with any earlier state, but run after the UI is done).
Read: `AGENTS.md`, `specs/08-deployment.md`.

## Create
- `Dockerfile`, `.dockerignore`, `docker-compose.dev.yml`, `docker-compose.yml` (home server version), `.env.example`
  — contents exactly as in 08.
- `README.md` section "Run with Docker" (3 commands for dev, 3 for server — see T16 for the server steps).

## Done when
- `docker compose -f docker-compose.dev.yml up --build -d` → `http://localhost:5055` shows the app; PIN `1234` unlocks it
- Add a student, then `docker compose -f docker-compose.dev.yml restart` → the student is still there (volume works)
- `docker compose -f docker-compose.dev.yml exec job-rotator date` and `python -c "from rotator.dates import central_today; print(central_today())"`
  print the Minnesota date
- `docker inspect --format '{{.State.Health.Status}}' <container>` becomes `healthy`
- Production config check: `APP_ENV=production` with no `ADMIN_PIN` → container exits with the clear error message (verify with
  `docker compose run --rm -e APP_ENV=production -e ADMIN_PIN= job-rotator`)
- Image runs as non-root (`docker compose exec job-rotator id -u` prints 10001)
- `docker compose -f docker-compose.dev.yml down` (keep the volume)

If Docker isn't available on this machine, stop and write `BLOCKED T14: docker not available` in NOTES.md.

## Don't
Change application code. Don't publish a host port in the server compose file.
