# T16 — Deploy to the home server (human-run checklist)

Not for the coding agent unless Mohamed pastes outputs. The agent may help interpret errors.
Depends on: T14, T15.
Read: `specs/08-deployment.md`.

Commands below are meant to be run directly on the server while already logged in over SSH.

## 1. Copy the project
```bash
mkdir -p ~/docker/job-rotator && cd ~/docker/job-rotator
```
Get the code there (git clone your repo, or copy the folder from your dev machine). The folder must contain
`Dockerfile`, `docker-compose.yml`, `rotator/`, `wsgi.py`, `requirements.txt`.

## 2. Secrets
```bash
cp .env.example .env
nano .env        # set ADMIN_PIN to a PIN only you know (6+ characters); it is shared by nothing else
```

## 3. Build and start
```bash
docker compose up -d --build
docker compose ps
docker compose logs --tail=30 job-rotator
```
Expect status `healthy` after ~30 s. If it exits with "ADMIN_PIN must be set", fix `.env`.

## 4. Nginx Proxy Manager
Add a Proxy Host: domain (e.g. `jobs.sirwalterlibrary.ddns.net`), scheme `http`, forward host `job-rotator`, port `8000`,
Block Common Exploits on. SSL tab → request a certificate, Force SSL on. Make sure the subdomain resolves through your DDNS
the same way your other services do.

## 5. Verify (from your phone on cellular, then on the LAN)
- Page loads over https, Bismillah header visible, both tabs work
- Viewer mode has no teacher buttons; "Teacher login" with the PIN unlocks them
- Add your real jobs and students; reload the page: still there
- `docker compose restart` then reload: still there
- Export backup and save the JSON somewhere safe (NAS)
- Check the first Saturday it is "Today" in Central time and the Friday before shows "Next Weekend"

## 6. Optional hardening
- Add the site to Uptime Kuma (HTTP check on `/api/health`)
- Include the volume in the server's backup routine

## Updating later
```bash
cd ~/docker/job-rotator && git pull && docker compose up -d --build
```

## If something fails
Paste the output of `docker compose logs --tail=60 job-rotator` and the NPM proxy host settings into your assistant.
