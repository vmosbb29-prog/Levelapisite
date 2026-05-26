# Level-Up Bot Dashboard

A self-hosted web dashboard for managing Free Fire game bots and tracking player EXP in real time.

---

## What It Does

- **Bot Manager** — Log in multiple Free Fire accounts, run auto-start loops with team codes, and monitor live cycles/uptime.
- **EXP Tracker** — Track any player's live EXP gain, smoothed rate (exp/hr), level progress, and estimated level-up time. Updates every 60 seconds.
- **Analytics** — Ring charts and a per-bot performance table (cycles, uptime, rate/hr).
- **Live Logs** — Real-time Server-Sent Events (SSE) log stream per bot.
- **Account Management** — Save/delete game accounts securely (passwords stored in SQLite).
- **Health Check** — `GET /healthz` returns `{"status":"ok","active_bots":N,"active_trackers":N}` for uptime monitors.

---

## Stack

| Layer       | Technology                                          |
|-------------|-----------------------------------------------------|
| Backend     | Python 3.11 · FastAPI · Uvicorn                    |
| Templates   | Jinja2 HTML + vanilla JS + custom CSS              |
| Database    | SQLite (Python stdlib `sqlite3`)                   |
| Bot Engine  | `asyncio` TCP + AES-CBC encrypted protobuf packets |
| EXP API     | `https://infoapibynirob.vercel.app/`               |
| Auto-Update | `https://auto-update-devil.vercel.app/`            |

---

## Quick Start (Local)

### Requirements

- Python 3.10 or 3.11
- pip

### Install & Run

```bash
git clone <your-repo-url>
cd bot-dashboard

pip install -r requirements.txt

python app.py
# OR
uvicorn app:app --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000` in your browser. Register an account on first run.

Verify it is alive:

```bash
curl http://localhost:8000/healthz
# {"status":"ok","active_bots":0,"active_trackers":0}
```

---

## Environment Variables

| Variable  | Default                              | Description                              |
|-----------|--------------------------------------|------------------------------------------|
| `PORT`    | `8000`                               | Port Uvicorn listens on                  |
| `DB_PATH` | `<app-dir>/sessions/app.db`          | Absolute path to the SQLite database     |

Set `DB_PATH` to a persistent disk path on cloud platforms (see sections below).

---

## Database & Data Persistence

The SQLite database lives at `sessions/app.db` by default. It stores:

| Table          | Contents                                         |
|----------------|--------------------------------------------------|
| `users`        | Dashboard accounts (username + SHA-256 hash)     |
| `sessions`     | Login tokens (7-day cookie expiry)               |
| `bot_accounts` | Saved game accounts (UID, password, region, label) |

### What survives a restart

| Data                      | Survives? | Reason                              |
|---------------------------|-----------|-------------------------------------|
| Registered users          | ✅ Yes    | Stored in SQLite                    |
| Saved bot accounts        | ✅ Yes    | Stored in SQLite                    |
| Login session cookies     | ✅ Yes    | Stored in SQLite                    |
| Active bot TCP sessions   | ❌ No     | Live network connections            |
| Active EXP tracker polls  | ❌ No     | Live async tasks                    |

**After any restart:** open the dashboard → click **Start Bot** on each account → re-add tracker UIDs. Everything else is already there.

### Protecting the database

- Never delete the `sessions/` directory.
- Back up `sessions/app.db` regularly (it is a single file — copy it anywhere).
- On cloud platforms, always mount a **persistent disk** and set `DB_PATH` (see below).

---

## Deploy to Render

1. Push this project to a GitHub repository.
2. Go to [render.com](https://render.com) → **New Web Service** → connect your repo.
3. Render auto-detects `render.yaml`. Review the settings and click **Deploy**.
4. A 1 GB persistent disk is automatically mounted at `/data`.
5. `DB_PATH=/data/app.db` is pre-configured — the database survives every redeploy.
6. Render pings `/healthz` to confirm the service is healthy before marking it live.

**Manual settings** (if not using `render.yaml`):

| Field              | Value                                             |
|--------------------|---------------------------------------------------|
| Runtime            | Python 3                                          |
| Build Command      | `pip install -r requirements.txt`                 |
| Start Command      | `uvicorn app:app --host 0.0.0.0 --port $PORT`     |
| Health Check Path  | `/healthz`                                        |
| Disk Mount Path    | `/data`                                           |
| `DB_PATH` env var  | `/data/app.db`                                    |

---

## Deploy to Railway

1. Push to GitHub.
2. New Railway project → **Deploy from GitHub repo**.
3. Railway reads the `Procfile` automatically.
4. Add a **Volume** in the Railway dashboard, mount it at `/data`.
5. Set environment variable `DB_PATH=/data/app.db`.
6. Add a health-check monitor pointing to `/healthz`.

---

## Deploy to VPS / Self-Host

Run behind Nginx or Caddy. The `sessions/` directory is persistent as long as the disk is.

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        # Required for SSE (live logs):
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 3600s;
    }
}
```

Run with systemd or screen:

```bash
uvicorn app:app --host 127.0.0.1 --port 8000
```

---

## Health Check Endpoint

`GET /healthz` — no authentication required.

```json
{
  "status": "ok",
  "active_bots": 2,
  "active_trackers": 1
}
```

- Returns HTTP 200 when the server and database are reachable.
- Safe to use with Render health checks, UptimeRobot, BetterUptime, or any monitor.
- Also exercises the DB connection on every call to catch storage issues early.

---

## Project Structure

```
bot-dashboard/
├── app.py              # FastAPI app — all routes + /healthz
├── bot_engine.py       # Async TCP bot engine (login, auto-start loop)
├── exp_tracker.py      # EXP tracker polling manager
├── exp_chart.py        # Level/EXP progress calculations
├── database.py         # SQLite helpers (users, sessions, bot accounts)
├── models.py           # ActiveBotSession dataclass
├── autoup.py           # Auto-fetches latest FF server URL / version
├── xDL.py              # Encryption helpers (AES, protobuf packet builders)
├── Pb2/                # Compiled protobuf definitions
├── templates/          # Jinja2 HTML templates
│   ├── base.html
│   ├── login.html
│   ├── register.html
│   └── dashboard.html
├── static/             # Served static assets
│   ├── app.js          # Dashboard JS (bot controls, SSE logs, tracker UI)
│   └── style.css       # Full dashboard CSS
├── sessions/           # SQLite database directory
│   └── app.db          # ← DO NOT DELETE
├── requirements.txt    # Python dependencies
├── render.yaml         # Render.com deployment config (disk + healthz)
├── Procfile            # Railway / Heroku process file
└── README.md           # This file
```

---

## Requirements

```
fastapi
uvicorn[standard]
aiohttp
pycryptodome
protobuf>=6.26.0
protobuf-decoder
requests
google-play-scraper
urllib3
jinja2
python-multipart
aiosqlite
PyJWT
pytz
```

---

## Security Notes

- Passwords are stored as SHA-256 hashes — not reversible.
- Session tokens are 64-character random hex strings with 7-day cookie expiry.
- Bot account game passwords are stored in plaintext (needed for re-login). Use dedicated game accounts.
- No rate limiting by default. Put Nginx or Cloudflare in front for production use.
- The `/healthz` endpoint is public (no auth) — it only exposes count values, no user data.

---

## Restart Safety Checklist

After any server restart:

1. Open the dashboard — all your registered accounts and saved bot accounts are there.
2. Go to **My Bots** → click **Start Bot** on each account you want online.
3. Go to **EXP Tracker** → re-add any UIDs you were tracking.

That is all. No database setup, no migrations, no manual fixes needed.
