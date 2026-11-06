# 08 — Packaging and deployment

Develop and test locally first, then run it as a Docker container on the home server (Ubuntu, Docker, Nginx Proxy Manager).

## Local development
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
DATA_DIR=./data flask --app wsgi run --port 5055 --debug
pytest -q
```
Preview other days while developing: `ALLOW_TODAY_OVERRIDE=1 DATA_DIR=./data flask --app wsgi run --port 5055`
then open `http://localhost:5055/api/today?today=2026-11-07`.

## requirements.txt
```
flask>=3.0,<4
gunicorn>=22
tzdata
pytest>=8
```
(pytest is fine in the production image; it keeps one requirements file. Nothing else.)

## wsgi.py
```python
from rotator.app import create_app
app = create_app()
```

## Dockerfile
```dockerfile
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 DATA_DIR=/data TZ=America/Chicago
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY rotator ./rotator
COPY wsgi.py .
RUN useradd -r -u 10001 app && mkdir -p /data && chown app /data
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health').status==200 else 1)"
CMD ["gunicorn", "-b", "0.0.0.0:8000", "-w", "1", "--threads", "4", "wsgi:app"]
```
One worker on purpose: SQLite plus a tiny classroom app. `.dockerignore`: `.venv data tests progress tasks specs .git __pycache__`.

## docker-compose.dev.yml (local Docker test)
```yaml
services:
  job-rotator:
    build: .
    ports: ["5055:8000"]
    environment:
      ADMIN_PIN: "1234"
      APP_ENV: development
    volumes:
      - rotator_data:/data
volumes:
  rotator_data:
```

## docker-compose.yml (home server, `~/docker/job-rotator/`)
Follows the server conventions: `~/docker/<service>/`, external `npm_net`, `restart: always`, named volume, `.env` secrets.
```yaml
services:
  job-rotator:
    build: .
    container_name: job-rotator
    restart: always
    env_file: .env
    environment:
      APP_ENV: production
      TRUST_PROXY: "1"
      TZ: America/Chicago
    volumes:
      - rotator_data:/data
    networks: [npm_net]
networks:
  npm_net:
    external: true
volumes:
  rotator_data:
```
`.env` (never committed; commit `.env.example` with `ADMIN_PIN=change-me`). No host port is published; Nginx Proxy Manager reaches
the container by name on `npm_net`.

## Nginx Proxy Manager (done by hand in the UI, see T16)
Proxy Host: domain e.g. `jobs.sirwalterlibrary.ddns.net` (any subdomain), Scheme `http`, Forward Hostname `job-rotator`,
Forward Port `8000`, Block Common Exploits on, Websockets off. SSL tab: request a Let's Encrypt certificate, Force SSL on.
Add the same DNS/DDNS subdomain the other services use.

## Safety
- `APP_ENV=production` and empty `ADMIN_PIN` → the app raises at startup with a clear message.
- The PIN is compared with `hmac.compare_digest`; the public can view but not change anything.
- Backups: the app's **Export backup** button (06) is the supported backup. Optionally also copy the volume
  (`/var/lib/docker/volumes/job-rotator_rotator_data/_data/rotator.db`) with the server's usual backup job.
- Updating: `git pull && docker compose up -d --build` in `~/docker/job-rotator/`. The volume keeps the data.
