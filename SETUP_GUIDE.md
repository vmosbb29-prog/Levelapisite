# Level-Up Bot Dashboard — Setup & Deployment Guide

---

## What this is

A self-hosted web dashboard for managing Free Fire game bots and tracking player EXP.
Built with Python (FastAPI / Uvicorn). Accounts, trackers, and cycle history are stored
in a local SQLite database that survives restarts automatically.

---

## Requirements

| Tool | Version |
|------|---------|
| Python | 3.10 or newer |
| pip | bundled with Python |

No Node.js, no Docker, no external services required.

---

## Local Setup (your own computer)

```bash
# 1. Unzip the project
unzip level-up-bot-dashboard.zip
cd bot-dashboard

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the server
python3 -m uvicorn app:app --host 0.0.0.0 --port 8000

# 4. Open in browser
#    http://localhost:8000
```

Default login: set your own username and password on first run via the register page.

---

## Render Deployment (free hosting, always-on)

### Step 1 — Create a Render account
Go to https://render.com and sign up for free.

### Step 2 — Create a new Web Service
- Click **New → Web Service**
- Choose **Deploy from a Git repo** (push your project to GitHub first)
  - OR choose **Manual deploy** and upload the ZIP

### Step 3 — Configure the service

| Field | Value |
|-------|-------|
| Runtime | Python 3 |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn app:app --host 0.0.0.0 --port $PORT` |
| Instance Type | Free |

### Step 4 — Set environment variables (optional)

| Variable | Purpose | Default |
|----------|---------|---------|
| `SESSION_SECRET` | Cookie signing key | auto-generated if missing |
| `DB_PATH` | Path to SQLite file | `sessions/app.db` |

### Step 5 — Persistent Disk (IMPORTANT for keeping your data)

On Render free tier, the disk resets on every redeploy.
To keep accounts and trackers permanently:

1. In your Render service → **Disks** → **Add Disk**
2. Set mount path: `/data`
3. Set environment variable: `DB_PATH=/data/app.db`

This guarantees accounts, trackers, and cycle history survive every restart and redeploy.

---

## Environment Variables Reference

```env
SESSION_SECRET=your_random_secret_here   # Any long random string
DB_PATH=/data/app.db                     # Where the database lives
```

---

## What survives restarts automatically

| Data | Persists? |
|------|-----------|
| User accounts / passwords | Yes — in SQLite DB |
| Saved bot accounts (UID + password) | Yes — in SQLite DB |
| EXP trackers (tracked UIDs) | Yes — auto-resumed on startup |
| Cycle history / analytics | Yes — in SQLite DB |
| Notification settings (Telegram/Discord) | Yes — in SQLite DB |
| Active bot TCP sessions | No — must re-start bots after server restart |

Active bot sessions are in-memory by design. The watchdog will auto-reconnect
if a TCP connection drops while the server is running.

---

## Telegram Alert Setup

1. Open the **Notifications** tab in the dashboard
2. Create a Telegram bot via @BotFather → copy the **Bot Token**
3. Get your **Chat ID** (message @userinfobot or use @getidsbot)
4. Paste both values → click **Save Settings**
5. Click **Test** to verify

### All 9 alert types you will receive:

| Alert | Trigger |
|-------|---------|
| ✅ Bot online | Bot successfully connected |
| 🔴 Bot stopped | Bot manually stopped |
| 🔄 TCP dropped | Connection lost, reconnect starting |
| ✅ Reconnected | Watchdog re-login succeeded |
| ❌ Reconnect failed | All retry attempts exhausted, bot offline |
| 🚀 Auto-start launched | Team code run started |
| ⏹️ Auto-start stopped | Team code run ended |
| 🔁 Cycle milestone | Every 5 completed cycles |
| 📡 Tracker started | EXP tracker added for a UID |
| 📡 Tracker stopped | EXP tracker removed |
| 🏆 Level up | Tracked player gained a level |

---

## File Structure

```
bot-dashboard/
├── app.py              — Main FastAPI application, all routes
├── bot_engine.py       — TCP bot logic, auto-start loop, watchdog
├── exp_tracker.py      — EXP polling, level-up detection
├── database.py         — SQLite helpers, all DB operations
├── models.py           — ActiveBotSession dataclass
├── notify.py           — Telegram + Discord notification senders
├── auth.py             — Login / session management
├── requirements.txt    — Python dependencies
├── static/
│   └── app.js          — Frontend JavaScript
└── templates/
    └── dashboard.html  — Dashboard HTML (Jinja2)
```

---

## Troubleshooting

**"Address already in use" on startup**
Another process is using port 8000. Run: `fuser -k 8000/tcp` then restart.

**Bots don't reconnect after server restart**
This is expected — TCP sessions are in-memory. Re-start each bot from the dashboard.
Trackers auto-resume; bots need a manual re-login click.

**Telegram alerts not arriving**
- Check Bot Token and Chat ID in the Notifications tab
- Make sure you sent at least one message to your bot first (Telegram requires this)
- Use the Test button to confirm delivery

**Database not persisting on Render**
You must add a Persistent Disk with mount path `/data` and set `DB_PATH=/data/app.db`.
Without this, Render resets the filesystem on every deploy.

---

*Generated for Level-Up Bot Dashboard — stable production build*
