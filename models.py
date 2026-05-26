from dataclasses import dataclass, field
from typing import Optional
from collections import deque
import asyncio
import datetime


@dataclass
class ActiveBotSession:
    user_id: int
    account_id: int
    uid: str
    bot_uid: str
    display_name: str
    region: str
    key: bytes
    iv: bytes
    token: str
    jwt_token: str
    online_ip: str
    online_port: int
    chat_ip: str
    chat_port: int
    clan_id: Optional[int] = None
    clan_compiled_data: Optional[str] = None

    # Stored for auto-reconnect
    password: str = ""

    online_writer: object = field(default=None, repr=False)
    whisper_writer: object = field(default=None, repr=False)

    auto_start_running: bool = False
    stop_auto: bool = False
    auto_start_task: Optional[asyncio.Task] = field(default=None, repr=False)
    chat_task: Optional[asyncio.Task] = field(default=None, repr=False)
    online_task: Optional[asyncio.Task] = field(default=None, repr=False)
    watchdog_task: Optional[asyncio.Task] = field(default=None, repr=False)

    # Reconnect state
    reconnect_attempts: int = 0
    _missing_writer_count: int = 0
    is_reconnecting: bool = False

    # Notification callback — set by app.py, called by engine/watchdog
    notify_fn: Optional[object] = field(default=None, repr=False)

    status: str = "online"
    bot_state: str = "idle"
    logs: deque = field(default_factory=lambda: deque(maxlen=300))

    cycles_completed: int = 0
    started_at: Optional[datetime.datetime] = None
    last_teamcode: str = ""
    activity: list = field(default_factory=list)

    def add_log(self, message: str, level: str = "info"):
        self.logs.append({
            "time": datetime.datetime.now().strftime("%H:%M:%S"),
            "level": level,
            "msg": message,
        })

    def add_activity(self, event_type: str, **kwargs):
        entry = {
            "ts": datetime.datetime.now().isoformat(timespec="seconds"),
            "type": event_type,
            "display": self.display_name or self.uid,
            **kwargs,
        }
        self.activity.append(entry)
        if len(self.activity) > 100:
            self.activity = self.activity[-100:]

    def to_dict(self) -> dict:
        uptime = 0
        if self.started_at:
            uptime = int((datetime.datetime.now() - self.started_at).total_seconds())

        cycles_per_hour = 0.0
        if self.started_at and self.cycles_completed > 0 and uptime > 0:
            cycles_per_hour = round(self.cycles_completed / (uptime / 3600), 1)

        return {
            "account_id": self.account_id,
            "uid": self.uid,
            "bot_uid": self.bot_uid,
            "display_name": self.display_name,
            "region": self.region,
            "status": self.status,
            "bot_state": self.bot_state,
            "auto_running": self.auto_start_running,
            "clan_id": self.clan_id,
            "cycles_completed": self.cycles_completed,
            "uptime_seconds": uptime,
            "last_teamcode": self.last_teamcode,
            "started_at_ts": self.started_at.timestamp() if self.started_at else None,
            "cycles_per_hour": cycles_per_hour,
            "activity": self.activity[-15:],
        }
