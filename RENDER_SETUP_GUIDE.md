# Level-Up Bot Dashboard
## Complete Beginner Deployment Guide for Render

---

This guide walks you through every single step to deploy the Level-Up Bot Dashboard
on Render — from creating your account to keeping your data safe forever.
No technical experience required.

---

## What You Will Have at the End

- Your bot dashboard running 24/7 on the internet
- A permanent link you can open from any device
- All your accounts and trackers saved safely
- Automatic restart if anything goes wrong

---

## PART 1 — Create Your Render Account

1. Open your browser and go to: **https://render.com**
2. Click the **"Get Started for Free"** button
3. Sign up using **GitHub** (recommended) or your email address
4. Confirm your email if asked
5. You are now inside the Render dashboard

> Render's free plan is enough to run this project. No credit card needed to start.

---

## PART 2 — Upload Your Project to GitHub

Render deploys from GitHub. You need to put your project files there first.

### Step 2a — Create a GitHub account (if you don't have one)

1. Go to **https://github.com**
2. Click **Sign up** and follow the steps

### Step 2b — Create a new repository

1. Click the **+** icon (top right) → **New repository**
2. Name it: `level-up-bot-dashboard`
3. Set it to **Private** (important — keeps your files safe)
4. Click **Create repository**

### Step 2c — Upload your files

**Option A — Upload via GitHub website (easiest):**

1. Open your new repository on GitHub
2. Click **"uploading an existing file"** (or drag and drop)
3. Unzip the ZIP file on your computer
4. Drag ALL the files and folders inside into the GitHub upload page
5. Scroll down → click **"Commit changes"**

**Option B — Upload via Git (if you know Git):**

```bash
cd bot-dashboard          # go into the unzipped folder
git init
git add .
git commit -m "initial"
git remote add origin https://github.com/YOUR_USERNAME/level-up-bot-dashboard.git
git push -u origin main
```

---

## PART 3 — Deploy on Render

### Step 3a — Create a new Web Service

1. Go back to **https://dashboard.render.com**
2. Click **"New +"** → **"Web Service"**
3. Click **"Connect a repository"**
4. If asked, click **"Connect GitHub"** and authorize Render
5. Find `level-up-bot-dashboard` in the list → click **"Connect"**

### Step 3b — Configure the service

Fill in these exact settings:

| Setting | Value |
|---------|-------|
| **Name** | `level-up-bot-dashboard` (or any name you like) |
| **Region** | Choose the one closest to you |
| **Branch** | `main` |
| **Runtime** | `Python 3` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `python -m uvicorn app:app --host 0.0.0.0 --port $PORT` |
| **Instance Type** | `Free` |

> The `render.yaml` file in the project sets most of this automatically.
> Double-check these settings before clicking Deploy.

### Step 3c — Click Deploy

Click **"Create Web Service"** at the bottom.

Render will now:
1. Download your code
2. Install Python packages
3. Start the server

This takes about **2–4 minutes**. Wait for the status to show **"Live"** in green.

---

## PART 4 — Set Up the Persistent Disk (CRITICAL — Do This First)

**Without this step, ALL your accounts and data will be deleted every time Render restarts your app.**

### Why this matters

Render's free servers reset their filesystem every time they restart or redeploy.
A Persistent Disk is a separate storage unit that never gets wiped.
Your database lives there and survives everything.

### How to add the Persistent Disk

1. In your Render service page, click **"Disks"** in the left sidebar
2. Click **"Add Disk"**
3. Fill in:
   - **Name:** `db-data`
   - **Mount Path:** `/data`
   - **Size:** `1 GB` (more than enough — the database is tiny)
4. Click **"Save"**

### Tell the app where the database is

1. In your Render service page, click **"Environment"** in the left sidebar
2. Click **"Add Environment Variable"**
3. Add these two variables:

| Key | Value |
|-----|-------|
| `DB_PATH` | `/data/app.db` |
| `SESSION_SECRET` | *(click "Generate" to create a random value)* |

4. Click **"Save Changes"**

Render will restart your service automatically. After restart, all data will be saved permanently at `/data/app.db`.

---

## PART 5 — First Login

1. Open your service URL (shown at the top of Render, like `https://your-app.onrender.com`)
2. Click **"Create one"** to register your first account
3. Choose a username and password
4. Log in

Your account is now saved permanently in the persistent database.

---

## PART 6 — Environment Variables Reference

These are all the environment variables the app understands:

| Variable | Required | Description | Example Value |
|----------|----------|-------------|---------------|
| `DB_PATH` | Recommended | Where the database file is stored | `/data/app.db` |
| `SESSION_SECRET` | Recommended | Secret key for login cookies | Any long random string |

If you don't set these, the app still works — but data won't survive Render restarts.

---

## PART 7 — Keeping Your Data Safe

### What data is saved automatically

| Data | Where | Safe? |
|------|-------|-------|
| User accounts & passwords | SQLite database | ✅ Yes (if disk is set up) |
| Saved bot accounts (UID + password) | SQLite database | ✅ Yes |
| EXP trackers (tracked UIDs) | SQLite database | ✅ Yes, auto-resumes on startup |
| Cycle history & analytics | SQLite database | ✅ Yes |
| Notification settings | SQLite database | ✅ Yes |
| Active bot TCP sessions | Memory only | ⚠️ Must re-start after server restart |

> Active bot sessions are in-memory by design. After a restart, just click
> "Start Bot" again for each account. Everything else restores automatically.

### How to back up your database

**Method 1 — Render Shell (easiest):**

1. In Render, go to your service → click **"Shell"** tab
2. Type this command and press Enter:
   ```
   cp /data/app.db /data/app.db.backup
   ```
3. Your backup is now at `/data/app.db.backup`

**Method 2 — Download via Shell:**

1. Open Render Shell
2. Run:
   ```
   base64 /data/app.db
   ```
3. Copy the entire output and save it in a text file on your computer
4. To restore later, run:
   ```
   echo "PASTE_YOUR_BASE64_HERE" | base64 -d > /data/app.db
   ```

### How to restore your database

If you ever need to restore from a backup:

1. Open the Render Shell
2. Run:
   ```
   cp /data/app.db.backup /data/app.db
   ```
3. Restart the service (from Render dashboard → **"Restart"**)

---

## PART 8 — Restarting Safely

### How to restart the service

1. Go to your service on Render dashboard
2. Click the **"Manual Deploy"** button → **"Deploy latest commit"**
   — OR —
   Click the three-dot menu → **"Restart service"**

### What happens when the service restarts

- The server stops (all active bot sessions disconnect)
- The server starts again fresh
- The database is still intact on the persistent disk
- EXP trackers **auto-resume** from the saved list
- Bot sessions **must be re-started manually** (click Start Bot for each)

---

## PART 9 — Updating the Project

When you get a new version of the project:

1. Unzip the new version on your computer
2. Go to your GitHub repository
3. Upload the new files (they will replace the old ones)
4. Commit the changes
5. Go back to Render → your service will **auto-redeploy** within 1–2 minutes

> Your database is on the persistent disk and is **never touched** during an update.
> All accounts, bots, and trackers are preserved automatically.

---

## PART 10 — Monitoring and Logs

### How to check if the app is running

- Open your service URL in a browser — if the login page loads, it's working
- Render also shows **"Live"** in green on the service page

### How to view server logs

1. Go to your Render service
2. Click **"Logs"** in the left sidebar
3. You can see all server output, errors, and startup messages in real-time

### How to check for errors

Look for lines starting with `ERROR` or `CRITICAL` in the logs.
Common issues and fixes are listed in Part 11 below.

### Uptime monitoring (optional, free)

Use **https://uptimerobot.com** (free):
1. Create an account
2. Add a new monitor → type: HTTP(s)
3. URL: `https://your-app.onrender.com/healthz`
4. It will alert you if the app goes down

---

## PART 11 — Troubleshooting

### App shows "Service Unavailable" or won't load

**Cause:** Render's free tier puts services to sleep after 15 minutes of inactivity.
**Fix:** Just open the URL — it will wake up in about 30 seconds.
To prevent sleep: Use UptimeRobot to ping `/healthz` every 10 minutes.

---

### "Internal Server Error" on login page

**Cause:** Database could not be created (disk not mounted).
**Fix:**
1. Check that `DB_PATH=/data/app.db` is set in Environment variables
2. Check that the Persistent Disk is added with mount path `/data`
3. Restart the service

---

### Lost all accounts after redeploy

**Cause:** Persistent Disk was not set up.
**Fix:**
1. Add the Persistent Disk now (Part 4 above)
2. Set `DB_PATH=/data/app.db`
3. Restart — future data will be saved permanently

> Unfortunately data lost before the disk was set up cannot be recovered.
> Register your accounts again, then they will be safe going forward.

---

### Bots not reconnecting after restart

**This is expected behavior.** Active TCP sessions are in-memory.
After any restart, go to the dashboard and click **"Start Bot"** for each account.
EXP trackers resume automatically — only bot sessions need manual restart.

---

### Telegram alerts not arriving

1. Open the **Notifications** tab in the dashboard
2. Verify your Bot Token and Chat ID are correct
3. Make sure you sent at least one message to your bot (Telegram requires this)
4. Click **"Test"** to verify delivery

---

### Build fails on Render

**Cause:** A Python package failed to install.
**Fix:**
1. Click **"Logs"** on Render → scroll to the failed install line
2. Check `requirements.txt` has all dependencies
3. Try adding pinned versions (e.g. `fastapi==0.115.0`) if a specific package fails

---

## PART 12 — Render Free Plan Limits

| Limit | Value |
|-------|-------|
| Monthly hours | 750 hours (enough for 1 service running all month) |
| Persistent Disk | Available on free plan |
| Custom domain | Available (requires DNS setup) |
| Sleep after inactivity | 15 minutes (use UptimeRobot to prevent) |
| RAM | 512 MB |
| CPU | Shared |

The dashboard is lightweight and runs comfortably within the free plan limits.

---

## Quick Reference Card

```
Service Type:     Web Service
Runtime:          Python 3
Build Command:    pip install -r requirements.txt
Start Command:    python -m uvicorn app:app --host 0.0.0.0 --port $PORT
Health Check:     /healthz

Environment Variables:
  DB_PATH         = /data/app.db
  SESSION_SECRET  = (generate random value)

Persistent Disk:
  Name            = db-data
  Mount Path      = /data
  Size            = 1 GB
```

---

*Level-Up Bot Dashboard — Render Setup Guide*
*Keep this file for reference. Safe deploying!*
