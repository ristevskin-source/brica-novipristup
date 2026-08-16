# Brica Novipristup

Simple booking app for a barber shop. This repository contains a Flask app that serves a lightweight frontend (templates/index.html) and provides API endpoints backed by a SQLite database (default: `brica.db`).

Quick start (local)

1. Create virtualenv and install dependencies

```bash
python3 -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. Run the app

```bash
python baza.py
```

The app will be available at http://127.0.0.1:5000

Important endpoints

- GET /api/usluge — list of services
- GET /api/slotovi/YYYY-MM-DD — available slots for date
- POST /api/zakazi — make a reservation (JSON: datum, vreme, ime, telefon, usluga, cena)
- GET /health — health check
- GET /api/backup?token=... — download database backup (enabled only if env BACKUP_TOKEN is set)

Deploy notes (Render)

- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn baza:app --bind 0.0.0.0:$PORT`
- Environment variables:
  - `DB_NAME` (optional) — path/name of SQLite DB file (default: `brica.db`)
  - `BACKUP_TOKEN` (optional) — token required to download a DB backup via `/api/backup`

Persistence

On free hosting (e.g. free Render instances) the filesystem is ephemeral — the `brica.db` file may not persist across deploys/restarts. For production use, consider using a managed Postgres DB and updating the code to use it (I can help migrate).

Security

- The `/admin` route is currently not protected; restrict access if you enable it publicly.
- The `/api/backup` endpoint is protected by a token (if configured) — change token via Render environment settings.

Backup example

To download a backup (if `BACKUP_TOKEN` is set):

```bash
curl -H "X-BACKUP-TOKEN: yourtoken" "https://your-site/api/backup" -o brica_backup.db
```

If you want, I can add automatic backup to remote storage.
