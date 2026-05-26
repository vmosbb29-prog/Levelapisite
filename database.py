import sqlite3
import hashlib
import os
import secrets
from contextlib import contextmanager

DB_PATH = os.environ.get(
    "DB_PATH",
    os.path.join(os.path.dirname(__file__), "sessions", "app.db")
)

def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

@contextmanager
def db():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    _db_dir = os.path.dirname(DB_PATH)
    if _db_dir:
        os.makedirs(_db_dir, exist_ok=True)
    with db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS bot_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                uid TEXT NOT NULL,
                password TEXT NOT NULL,
                region TEXT NOT NULL DEFAULT 'IND',
                label TEXT DEFAULT '',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS tracked_uids (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                uid TEXT NOT NULL,
                UNIQUE(user_id, uid),
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS notification_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                discord_webhook TEXT NOT NULL DEFAULT '',
                telegram_token TEXT NOT NULL DEFAULT '',
                telegram_chat_id TEXT NOT NULL DEFAULT '',
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS cycle_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                account_id INTEGER NOT NULL,
                uid TEXT NOT NULL,
                label TEXT DEFAULT '',
                cycles INTEGER NOT NULL DEFAULT 0,
                session_minutes INTEGER NOT NULL DEFAULT 0,
                logged_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
        """)

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(username: str, password: str) -> dict | None:
    try:
        with db() as conn:
            conn.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (username, hash_password(password))
            )
            row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
            return dict(row)
    except sqlite3.IntegrityError:
        return None

def get_user_by_username(username: str) -> dict | None:
    with db() as conn:
        row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        return dict(row) if row else None

def verify_user(username: str, password: str) -> dict | None:
    user = get_user_by_username(username)
    if user and user["password_hash"] == hash_password(password):
        return user
    return None

def create_session(user_id: int) -> str:
    token = secrets.token_hex(32)
    with db() as conn:
        conn.execute("INSERT INTO sessions (token, user_id) VALUES (?, ?)", (token, user_id))
    return token

def get_session_user(token: str) -> dict | None:
    with db() as conn:
        row = conn.execute(
            "SELECT u.* FROM users u JOIN sessions s ON u.id = s.user_id WHERE s.token = ?",
            (token,)
        ).fetchone()
        return dict(row) if row else None

def delete_session(token: str):
    with db() as conn:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))

def save_bot_account(user_id: int, uid: str, password: str, region: str, label: str = "") -> dict:
    with db() as conn:
        conn.execute(
            "INSERT INTO bot_accounts (user_id, uid, password, region, label) VALUES (?, ?, ?, ?, ?)",
            (user_id, uid, password, region, label)
        )
        row = conn.execute(
            "SELECT * FROM bot_accounts WHERE user_id = ? AND uid = ? ORDER BY id DESC LIMIT 1",
            (user_id, uid)
        ).fetchone()
        return dict(row)

def get_bot_accounts(user_id: int) -> list[dict]:
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM bot_accounts WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,)
        ).fetchall()
        return [dict(r) for r in rows]

def delete_bot_account(account_id: int, user_id: int):
    with db() as conn:
        conn.execute(
            "DELETE FROM bot_accounts WHERE id = ? AND user_id = ?",
            (account_id, user_id)
        )


# ── Tracker persistence ────────────────────────────────────────────────────────

def save_tracked_uid(user_id: int, uid: str):
    with db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO tracked_uids (user_id, uid) VALUES (?, ?)",
            (user_id, uid)
        )

def remove_tracked_uid(user_id: int, uid: str):
    with db() as conn:
        conn.execute(
            "DELETE FROM tracked_uids WHERE user_id = ? AND uid = ?",
            (user_id, uid)
        )

def get_all_tracked_uids() -> list[dict]:
    with db() as conn:
        rows = conn.execute("SELECT user_id, uid FROM tracked_uids").fetchall()
        return [dict(r) for r in rows]


# ── Notification settings ──────────────────────────────────────────────────────

def get_notification_settings(user_id: int) -> dict:
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM notification_settings WHERE user_id = ?", (user_id,)
        ).fetchone()
    if row:
        return dict(row)
    return {
        "user_id": user_id,
        "discord_webhook": "",
        "telegram_token": "",
        "telegram_chat_id": "",
    }

def save_notification_settings(
    user_id: int,
    discord_webhook: str,
    telegram_token: str,
    telegram_chat_id: str,
):
    with db() as conn:
        conn.execute("""
            INSERT INTO notification_settings
                (user_id, discord_webhook, telegram_token, telegram_chat_id)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                discord_webhook  = excluded.discord_webhook,
                telegram_token   = excluded.telegram_token,
                telegram_chat_id = excluded.telegram_chat_id
        """, (user_id, discord_webhook, telegram_token, telegram_chat_id))


# ── Cycle log ─────────────────────────────────────────────────────────────────

def save_cycle_log(
    user_id: int,
    account_id: int,
    uid: str,
    label: str,
    cycles: int,
    session_minutes: int,
):
    if cycles <= 0:
        return
    with db() as conn:
        conn.execute(
            """INSERT INTO cycle_log
               (user_id, account_id, uid, label, cycles, session_minutes)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, account_id, uid, label, cycles, session_minutes),
        )

def get_cycle_history(user_id: int, days: int = 7) -> list[dict]:
    with db() as conn:
        rows = conn.execute("""
            SELECT
                DATE(logged_at)  AS date,
                SUM(cycles)      AS total_cycles,
                COUNT(*)         AS sessions
            FROM cycle_log
            WHERE user_id = ?
              AND logged_at >= DATE('now', ?)
            GROUP BY DATE(logged_at)
            ORDER BY date ASC
        """, (user_id, f"-{days} days")).fetchall()
    return [dict(r) for r in rows]
