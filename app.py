import asyncio
import json
import math
import os
import sys
from collections import deque
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, Request, Form, Cookie, HTTPException
from fastapi.responses import (
    HTMLResponse, RedirectResponse, JSONResponse, StreamingResponse
)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import database as db
import bot_engine
import notify as notifier
from models import ActiveBotSession
from exp_tracker import ExpTrackerManager

db.init_db()

app = FastAPI(title="Level-Up Bot Dashboard")

BASE = os.path.dirname(__file__)
app.mount("/static", StaticFiles(directory=os.path.join(BASE, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE, "templates"))

_bot_sessions: dict[str, ActiveBotSession] = {}
_starting_keys: set[str] = set()
tracker_mgr = ExpTrackerManager()


@app.on_event("startup")
async def _restore_trackers():
    """Re-start all EXP trackers that were active before the last restart."""
    saved = db.get_all_tracked_uids()
    if not saved:
        return
    for row in saved:
        asyncio.get_running_loop().create_task(
            tracker_mgr.restore_uid(row["user_id"], row["uid"])
        )


def _session_key(user_id: int, account_id: int) -> str:
    return f"{user_id}:{account_id}"


def _make_notify(user_id: int):
    """Returns an async callable that sends Telegram/Discord alerts for a user."""
    async def _fn(msg: str):
        try:
            ns = db.get_notification_settings(user_id)
            await notifier.notify_user(ns, msg)
        except Exception as exc:
            import logging
            logging.warning("[Notify] %s", exc)
    return _fn


def _user_sessions(user_id: int) -> list[ActiveBotSession]:
    prefix = f"{user_id}:"
    return [s for k, s in _bot_sessions.items() if k.startswith(prefix)]


def get_current_user(session_token: str | None = None):
    if not session_token:
        return None
    return db.get_session_user(session_token)


# ─── Pages ────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def root(request: Request, session_token: str | None = Cookie(default=None)):
    if not get_current_user(session_token):
        return RedirectResponse("/login", status_code=302)
    return RedirectResponse("/dashboard", status_code=302)


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, session_token: str | None = Cookie(default=None)):
    if get_current_user(session_token):
        return RedirectResponse("/dashboard", status_code=302)
    return templates.TemplateResponse(request, "login.html", {"error": None})


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, session_token: str | None = Cookie(default=None)):
    if get_current_user(session_token):
        return RedirectResponse("/dashboard", status_code=302)
    return templates.TemplateResponse(request, "register.html", {"error": None})


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request, session_token: str | None = Cookie(default=None)):
    user = get_current_user(session_token)
    if not user:
        return RedirectResponse("/login", status_code=302)
    accounts = db.get_bot_accounts(user["id"])
    for acc in accounts:
        key = _session_key(user["id"], acc["id"])
        sess = _bot_sessions.get(key)
        acc["bot_status"]      = sess.status if sess else "offline"
        acc["bot_state"]       = sess.bot_state if sess else "idle"
        acc["auto_running"]    = sess.auto_start_running if sess else False
        acc["display_name"]    = sess.display_name if sess else ""
        acc["bot_uid"]         = sess.bot_uid if sess else ""
        acc["cycles_completed"] = sess.cycles_completed if sess else 0
        acc["last_teamcode"]   = sess.last_teamcode if sess else ""
    notif = db.get_notification_settings(user["id"])
    return templates.TemplateResponse(request, "dashboard.html", {
        "user": user,
        "accounts": accounts,
        "notif": notif,
    })


# ─── Auth endpoints ───────────────────────────────────────────────────────────

@app.post("/login")
async def do_login(request: Request, username: str = Form(...), password: str = Form(...)):
    user = db.verify_user(username, password)
    if not user:
        return templates.TemplateResponse(request, "login.html", {"error": "Invalid username or password"})
    token = db.create_session(user["id"])
    resp = RedirectResponse("/dashboard", status_code=302)
    resp.set_cookie("session_token", token, httponly=True, samesite="lax", max_age=86400 * 7)
    return resp


@app.post("/register")
async def do_register(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    confirm: str = Form(...),
):
    if password != confirm:
        return templates.TemplateResponse(request, "register.html", {"error": "Passwords do not match"})
    if len(username) < 3:
        return templates.TemplateResponse(request, "register.html", {"error": "Username must be at least 3 characters"})
    if len(password) < 6:
        return templates.TemplateResponse(request, "register.html", {"error": "Password must be at least 6 characters"})
    user = db.create_user(username, password)
    if not user:
        return templates.TemplateResponse(request, "register.html", {"error": "Username already taken"})
    token = db.create_session(user["id"])
    resp = RedirectResponse("/dashboard", status_code=302)
    resp.set_cookie("session_token", token, httponly=True, samesite="lax", max_age=86400 * 7)
    return resp


@app.post("/logout")
async def do_logout(session_token: str | None = Cookie(default=None)):
    if session_token:
        db.delete_session(session_token)
    resp = RedirectResponse("/login", status_code=302)
    resp.delete_cookie("session_token")
    return resp


# ─── Account management ───────────────────────────────────────────────────────

@app.post("/bot/accounts/add")
async def add_account(
    uid: str = Form(...),
    password: str = Form(...),
    region: str = Form("IND"),
    label: str = Form(""),
    session_token: str | None = Cookie(default=None),
):
    user = get_current_user(session_token)
    if not user:
        return JSONResponse({"ok": False, "error": "Not authenticated"}, status_code=401)
    db.save_bot_account(user["id"], uid.strip(), password.strip(), region.upper(), label.strip())
    return JSONResponse({"ok": True})


@app.post("/bot/accounts/delete")
async def delete_account(
    account_id: int = Form(...),
    session_token: str | None = Cookie(default=None),
):
    user = get_current_user(session_token)
    if not user:
        return JSONResponse({"ok": False, "error": "Not authenticated"}, status_code=401)
    key = _session_key(user["id"], account_id)
    sess = _bot_sessions.pop(key, None)
    if sess:
        await bot_engine.stop_bot(sess)
    db.delete_bot_account(account_id, user["id"])
    return JSONResponse({"ok": True})


# ─── Bot control ──────────────────────────────────────────────────────────────

@app.post("/bot/start")
async def api_start_bot(
    account_id: int = Form(...),
    uid: str = Form(...),
    password: str = Form(...),
    session_token: str | None = Cookie(default=None),
):
    user = get_current_user(session_token)
    if not user:
        return JSONResponse({"ok": False, "error": "Not authenticated"}, status_code=401)

    key = _session_key(user["id"], account_id)

    if key in _starting_keys:
        return JSONResponse({"ok": False, "error": "Bot is already connecting. Please wait…"})

    existing = _bot_sessions.get(key)
    if existing and existing.status == "online":
        return JSONResponse({"ok": False, "error": "This bot is already online."})

    _starting_keys.add(key)
    try:
        session = await bot_engine.start_bot(
            user_id=user["id"],
            account_id=account_id,
            uid=uid.strip(),
            password=password.strip(),
        )
        _bot_sessions[key] = session
        nfn = _make_notify(user["id"])
        session.notify_fn = nfn
        asyncio.get_event_loop().create_task(
            nfn(
                f"✅ Bot online\n"
                f"Name: {session.display_name}\n"
                f"UID: {session.bot_uid}  |  Region: {session.region}"
            )
        )
        return JSONResponse({
            "ok": True,
            "message": f"Bot online: {session.display_name} (UID {session.bot_uid})",
            "bot": session.to_dict(),
        })
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)})
    finally:
        _starting_keys.discard(key)


@app.post("/bot/stop")
async def api_stop_bot(
    account_id: int = Form(...),
    session_token: str | None = Cookie(default=None),
):
    user = get_current_user(session_token)
    if not user:
        return JSONResponse({"ok": False, "error": "Not authenticated"}, status_code=401)

    key = _session_key(user["id"], account_id)
    session = _bot_sessions.pop(key, None)
    if not session:
        return JSONResponse({"ok": False, "error": "Bot is not running"})

    if session.cycles_completed > 0 and session.started_at:
        session_minutes = max(1, int((datetime.now() - session.started_at).total_seconds() / 60))
        db.save_cycle_log(
            user["id"],
            session.account_id,
            session.uid,
            session.display_name,
            session.cycles_completed,
            session_minutes,
        )

    nfn = _make_notify(user["id"])
    asyncio.get_event_loop().create_task(
        nfn(
            f"🔴 Bot stopped\n"
            f"Name: {session.display_name}\n"
            f"Cycles completed: {session.cycles_completed}"
        )
    )

    await bot_engine.stop_bot(session)
    return JSONResponse({"ok": True, "message": "Bot stopped"})


@app.post("/bot/run")
async def api_run_teamcode(
    account_id: int = Form(...),
    teamcode: str = Form(...),
    session_token: str | None = Cookie(default=None),
):
    user = get_current_user(session_token)
    if not user:
        return JSONResponse({"ok": False, "error": "Not authenticated"}, status_code=401)

    key = _session_key(user["id"], account_id)
    session = _bot_sessions.get(key)
    if not session or session.status != "online":
        return JSONResponse({"ok": False, "error": "Bot is not online. Start it first."})

    try:
        await bot_engine.run_teamcode(session, teamcode.strip())
        return JSONResponse({"ok": True, "message": f"Auto-start running for team {teamcode}"})
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)})


@app.post("/bot/stop-auto")
async def api_stop_auto(
    account_id: int = Form(...),
    session_token: str | None = Cookie(default=None),
):
    user = get_current_user(session_token)
    if not user:
        return JSONResponse({"ok": False, "error": "Not authenticated"}, status_code=401)

    key = _session_key(user["id"], account_id)
    session = _bot_sessions.get(key)
    if not session:
        return JSONResponse({"ok": False, "error": "No active bot session"})

    await bot_engine.stop_teamcode(session)
    return JSONResponse({"ok": True, "message": "Auto-start stopped"})


# ─── Status & analytics endpoints ─────────────────────────────────────────────

@app.get("/bot/all-status")
async def api_all_status(session_token: str | None = Cookie(default=None)):
    user = get_current_user(session_token)
    if not user:
        return JSONResponse({"ok": False, "error": "Not authenticated"}, status_code=401)
    sessions = _user_sessions(user["id"])
    return JSONResponse({"ok": True, "bots": [s.to_dict() for s in sessions]})


@app.get("/bot/global-stats")
async def api_global_stats(session_token: str | None = Cookie(default=None)):
    user = get_current_user(session_token)
    if not user:
        return JSONResponse({"ok": False}, status_code=401)

    sessions = _user_sessions(user["id"])
    total_cycles = sum(s.cycles_completed for s in sessions)
    total_uptime = sum(
        int((datetime.now() - s.started_at).total_seconds())
        for s in sessions if s.started_at and s.status == "online"
    )
    active = sum(1 for s in sessions if s.status == "online")

    rates = [
        s.cycles_completed / ((datetime.now() - s.started_at).total_seconds() / 3600)
        for s in sessions
        if s.started_at and s.cycles_completed > 0
        and (datetime.now() - s.started_at).total_seconds() > 0
    ]
    avg_rate = round(sum(rates) / len(rates), 1) if rates else 0.0

    return JSONResponse({
        "ok": True,
        "active_bots": active,
        "total_cycles": total_cycles,
        "total_uptime_seconds": total_uptime,
        "cycles_per_hour": avg_rate,
    })


@app.get("/bot/activity")
async def api_activity(session_token: str | None = Cookie(default=None)):
    user = get_current_user(session_token)
    if not user:
        return JSONResponse({"ok": False}, status_code=401)

    sessions = _user_sessions(user["id"])
    all_events = []
    for s in sessions:
        for ev in s.activity:
            all_events.append(ev)
    all_events.sort(key=lambda e: e["ts"], reverse=True)
    return JSONResponse({"ok": True, "events": all_events[:40]})


@app.get("/bot/{account_id}/status")
async def api_bot_status(account_id: int, session_token: str | None = Cookie(default=None)):
    user = get_current_user(session_token)
    if not user:
        return JSONResponse({"ok": False, "error": "Not authenticated"}, status_code=401)
    key = _session_key(user["id"], account_id)
    session = _bot_sessions.get(key)
    if not session:
        return JSONResponse({"ok": True, "status": "offline", "bot_state": "idle"})
    return JSONResponse({"ok": True, **session.to_dict()})


@app.get("/bot/{account_id}/logs")
async def api_bot_logs(account_id: int, session_token: str | None = Cookie(default=None)):
    user = get_current_user(session_token)
    if not user:
        raise HTTPException(status_code=401)

    async def event_stream():
        last_idx = 0
        while True:
            key = _session_key(user["id"], account_id)
            session = _bot_sessions.get(key)
            if session:
                logs = list(session.logs)
                for entry in logs[last_idx:]:
                    yield f"data: {json.dumps(entry)}\n\n"
                last_idx = len(logs)
            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ─── EXP Tracker endpoints ────────────────────────────────────────────────────

@app.post("/tracker/start")
async def api_tracker_start(
    tracking_uid: str = Form(...),
    session_token: str | None = Cookie(default=None),
):
    user = get_current_user(session_token)
    if not user:
        return JSONResponse({"ok": False, "error": "Not authenticated"}, status_code=401)
    uid = tracking_uid.strip()
    if not uid:
        return JSONResponse({"ok": False, "error": "UID is required"})
    nfn = _make_notify(user["id"])
    result = await tracker_mgr.start(user["id"], uid, notify_fn=nfn)
    if result.get("ok") and not result.get("already"):
        name = (result.get("data") or {}).get("nickname") or uid
        asyncio.get_event_loop().create_task(
            nfn(f"📡 EXP Tracker started\nPlayer: {name}  |  UID: {uid}")
        )
    return JSONResponse(result)


@app.post("/tracker/stop")
async def api_tracker_stop(
    tracking_uid: str = Form(...),
    session_token: str | None = Cookie(default=None),
):
    user = get_current_user(session_token)
    if not user:
        return JSONResponse({"ok": False, "error": "Not authenticated"}, status_code=401)
    uid = tracking_uid.strip()
    stopped = await tracker_mgr.stop(user["id"], uid)
    if stopped:
        nfn = _make_notify(user["id"])
        asyncio.get_event_loop().create_task(
            nfn(f"📡 EXP Tracker stopped\nUID: {uid}")
        )
    return JSONResponse({"ok": True, "stopped": stopped})


@app.get("/tracker/all")
async def api_tracker_all(session_token: str | None = Cookie(default=None)):
    user = get_current_user(session_token)
    if not user:
        return JSONResponse({"ok": False, "error": "Not authenticated"}, status_code=401)
    trackers = tracker_mgr.get_all(user["id"])
    return JSONResponse({"ok": True, "trackers": trackers})


@app.post("/tracker/refresh")
async def api_tracker_refresh(
    tracking_uid: str = Form(...),
    session_token: str | None = Cookie(default=None),
):
    user = get_current_user(session_token)
    if not user:
        return JSONResponse({"ok": False, "error": "Not authenticated"}, status_code=401)
    uid = tracking_uid.strip()
    if not tracker_mgr.is_active(user["id"], uid):
        return JSONResponse({"ok": False, "error": "Tracker not active for this UID"})
    result = await tracker_mgr.refresh_now(user["id"], uid)
    return JSONResponse(result)


# ─── Notification settings ────────────────────────────────────────────────────

@app.get("/settings/notifications")
async def api_get_notif_settings(session_token: str | None = Cookie(default=None)):
    user = get_current_user(session_token)
    if not user:
        return JSONResponse({"ok": False, "error": "Not authenticated"}, status_code=401)
    return JSONResponse({"ok": True, "settings": db.get_notification_settings(user["id"])})


@app.post("/settings/notifications")
async def api_save_notif_settings(
    discord_webhook:  str = Form(""),
    telegram_token:   str = Form(""),
    telegram_chat_id: str = Form(""),
    session_token: str | None = Cookie(default=None),
):
    user = get_current_user(session_token)
    if not user:
        return JSONResponse({"ok": False, "error": "Not authenticated"}, status_code=401)
    db.save_notification_settings(
        user["id"],
        discord_webhook.strip(),
        telegram_token.strip(),
        telegram_chat_id.strip(),
    )
    return JSONResponse({"ok": True})


@app.post("/settings/notifications/test")
async def api_test_notif(session_token: str | None = Cookie(default=None)):
    user = get_current_user(session_token)
    if not user:
        return JSONResponse({"ok": False, "error": "Not authenticated"}, status_code=401)
    ns = db.get_notification_settings(user["id"])
    if not ns.get("discord_webhook") and not ns.get("telegram_token"):
        return JSONResponse({"ok": False, "error": "No channels configured yet"})
    await notifier.notify_user(ns, "🔔 Test notification from Level-Up Bot Dashboard!")
    return JSONResponse({"ok": True, "message": "Test notification sent!"})


# ─── Cycle history ────────────────────────────────────────────────────────────

@app.api_route("/healthz", methods=["GET", "HEAD"])
async def api_cycle_history(
    days: int = 7,
    session_token: str | None = Cookie(default=None),
):
    user = get_current_user(session_token)
    if not user:
        return JSONResponse({"ok": False, "error": "Not authenticated"}, status_code=401)
    days = max(1, min(days, 30))
    rows = db.get_cycle_history(user["id"], days)
    return JSONResponse({"ok": True, "history": rows, "days": days})


# ─── Health check ─────────────────────────────────────────────────────────────

@app.get("/healthz")
async def healthz():
    """Lightweight health-check used by Render / Railway / uptime monitors."""
    try:
        db.get_session_user("__probe__")   # exercises the DB connection
    except Exception:
        pass                               # table exists, bad token is fine
    active_bots    = sum(1 for s in _bot_sessions.values() if s.status == "online")
    active_trackers = len(tracker_mgr._entries)
    return JSONResponse({
        "status": "ok",
        "active_bots": active_bots,
        "active_trackers": active_trackers,
    })


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)
