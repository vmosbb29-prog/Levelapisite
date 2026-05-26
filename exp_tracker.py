import asyncio
import logging
import time
import statistics
import database as db
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import aiohttp

from exp_chart import get_level_progress

_API_URL        = "https://infoapibynirob.vercel.app/accinfo?uid={uid}"
_TIMEOUT        = aiohttp.ClientTimeout(total=10)
POLL_INTERVAL   = 60          # seconds between polls
MAX_SAMPLES     = 60          # rolling window: 60 samples = ~60 minutes
SPIKE_THRESHOLD = 180_000     # max realistic exp/hr — anything above is a spike
MIN_SAMPLES     = 3           # minimum samples before showing rate
IDLE_POLLS      = 10          # consecutive zero-gain polls → idle


@dataclass
class TrackerEntry:
    user_id:      int
    uid:          str
    nickname:     str  = ""
    region:       str  = ""
    level:        int  = 0
    current_exp:  int  = 0
    start_exp:    int  = 0
    rank:         int  = 0
    liked:        int  = 0
    clan_name:    str  = ""
    last_checked: Optional[datetime] = None
    created_at:   Optional[datetime] = None
    prev_exp:     int  = 0
    tracker_status: str = "collecting"
    consecutive_same: int = 0
    error:        str  = ""
    task:         Optional[asyncio.Task] = field(default=None, repr=False)
    notify_fn:    Optional[object]       = field(default=None, repr=False)
    prev_level:   int  = 0

    # ── Rolling sample history ──────────────────────────────────────────
    # Each entry: (unix_timestamp_float, exp_value)
    _samples:    list  = field(default_factory=list, repr=False)
    _peak_rate:  float = 0.0

    # ── Raw session gain ────────────────────────────────────────────────
    def exp_gain(self) -> int:
        return max(0, self.current_exp - self.start_exp)

    # ── Add a sample (called every time we get a new EXP value) ─────────
    def _push_sample(self, ts: float, exp: int):
        self._samples.append((ts, exp))
        if len(self._samples) > MAX_SAMPLES:
            self._samples.pop(0)

    # ── Build list of per-interval rate values from stored samples ───────
    def _interval_rates(self) -> list[float]:
        rates = []
        for i in range(1, len(self._samples)):
            t0, e0 = self._samples[i - 1]
            t1, e1 = self._samples[i]
            dt = t1 - t0
            de = e1 - e0
            if dt < 30:        # ignore tiny time deltas (duplicate poll)
                continue
            if de < 0:         # negative gain — ignore (shouldn't happen normally)
                continue
            rate = de / (dt / 3600.0)   # convert to per-hour
            if rate > SPIKE_THRESHOLD:  # spike — ignore
                continue
            rates.append(rate)
        return rates

    # ── Weighted rolling EXP/hour ────────────────────────────────────────
    # Split rates into thirds: oldest=20%, middle=30%, newest=50%
    def smoothed_exp_per_hour(self) -> float:
        rates = self._interval_rates()
        if len(rates) < 2:
            return float(rates[0]) if rates else 0.0
        n = len(rates)
        cut1 = n // 3
        cut2 = 2 * n // 3
        seg_old = rates[:cut1]
        seg_mid = rates[cut1:cut2]
        seg_new = rates[cut2:]

        def avg(seg):
            return sum(seg) / len(seg) if seg else None

        parts = [(avg(seg_old), 0.20), (avg(seg_mid), 0.30), (avg(seg_new), 0.50)]
        valid = [(v, w) for v, w in parts if v is not None]
        if not valid:
            return 0.0
        total_w = sum(w for _, w in valid)
        weighted = sum(v * w for v, w in valid) / total_w
        result = round(weighted, 1)
        # Track peak
        if result > self._peak_rate:
            self._peak_rate = result
        return result

    # ── Raw simple EXP/hour (total gain / total time) ────────────────────
    def exp_per_hour(self) -> float:
        if not self.created_at:
            return 0.0
        elapsed = (datetime.now() - self.created_at).total_seconds()
        if elapsed < 60:
            return 0.0
        gain = self.exp_gain()
        if gain <= 0:
            return 0.0
        return round(gain / (elapsed / 3600.0), 1)

    # ── Confidence score (0-100) + label ─────────────────────────────────
    def confidence(self) -> tuple[int, str]:
        rates = self._interval_rates()
        n = len(rates)
        if n < MIN_SAMPLES:
            return 0, "low"

        # Base score from sample count (up to 60 pts)
        base = min(n * 4, 60)

        # Consistency bonus (up to 40 pts): lower coefficient of variation = more consistent
        non_zero = [r for r in rates if r > 0]
        if len(non_zero) >= 3:
            try:
                mean = statistics.mean(non_zero)
                sd   = statistics.stdev(non_zero)
                cv   = sd / mean if mean > 0 else 1.0
                consistency = max(0.0, 40.0 * (1.0 - min(cv, 1.0)))
            except Exception:
                consistency = 0.0
        else:
            consistency = 0.0

        score = min(int(base + consistency), 100)
        if score < 33:
            return score, "low"
        if score < 66:
            return score, "medium"
        return score, "high"

    # ── Tracking state label ─────────────────────────────────────────────
    def tracking_state(self) -> str:
        if get_level_progress(self.level, self.current_exp).get("max_level"):
            return "max_level"
        rates = self._interval_rates()
        if len(rates) < MIN_SAMPLES:
            return "collecting"
        if self.tracker_status == "idle":
            return "idle"
        return "tracking"

    # ── Session duration in seconds ──────────────────────────────────────
    def session_duration_secs(self) -> int:
        if not self.created_at:
            return 0
        return int((datetime.now() - self.created_at).total_seconds())

    # ── ETA using smoothed rate ──────────────────────────────────────────
    def _fmt_levelup(self, remaining: int) -> str:
        rate = self.smoothed_exp_per_hour()
        if rate <= 0 or remaining <= 0:
            # Fall back to simple rate if smoothed not ready
            rate = self.exp_per_hour()
        if rate <= 0 or remaining <= 0:
            return "—"
        hours = remaining / rate
        if hours < 1 / 60:
            return "Soon!"
        elif hours < 1:
            return f"~{int(hours * 60)}m"
        elif hours < 24:
            h = int(hours)
            m = int((hours - h) * 60)
            return f"~{h}h {m}m" if m else f"~{h}h"
        else:
            d = int(hours / 24)
            h = int(hours % 24)
            return f"~{d}d {h}h" if h else f"~{d}d"

    # ── Full dict for API response ───────────────────────────────────────
    def to_dict(self) -> dict:
        prog        = get_level_progress(self.level, self.current_exp)
        raw_rate    = self.exp_per_hour()
        smooth_rate = self.smoothed_exp_per_hour()
        remaining   = prog.get("remaining_exp", 0)
        conf_score, conf_label = self.confidence()
        t_state     = self.tracking_state()

        return {
            "uid":                  self.uid,
            "nickname":             self.nickname,
            "region":               self.region,
            "level":                self.level,
            "current_exp":          self.current_exp,
            "start_exp":            self.start_exp,
            "exp_gain":             self.exp_gain(),
            "exp_per_hour":         raw_rate,
            "smoothed_exp_per_hour": smooth_rate,
            "peak_exp_per_hour":    round(self._peak_rate, 1),
            "rank":                 self.rank,
            "liked":                self.liked,
            "clan_name":            self.clan_name,
            "tracker_status":       self.tracker_status,
            "tracking_state":       t_state,
            "confidence_score":     conf_score,
            "confidence":           conf_label,
            "samples_count":        len(self._samples),
            "session_duration_secs": self.session_duration_secs(),
            "last_checked":         self.last_checked.strftime("%H:%M:%S") if self.last_checked else "—",
            "created_at":           self.created_at.isoformat() if self.created_at else None,
            "estimated_levelup":    self._fmt_levelup(remaining),
            "error":                self.error,
            "base_exp":             prog.get("base_exp", 0),
            "next_level_exp":       prog.get("next_level_exp"),
            "completed_exp":        prog.get("completed_exp", 0),
            "remaining_exp":        remaining,
            "progress_pct":         prog.get("progress_pct", 0.0),
            "max_level":            prog.get("max_level", False),
        }


# ── HTTP fetch ──────────────────────────────────────────────────────────────
async def _fetch(uid: str) -> dict | None:
    url = _API_URL.format(uid=uid)
    try:
        async with aiohttp.ClientSession(timeout=_TIMEOUT) as session:
            async with session.get(url, ssl=False) as resp:
                if resp.status == 200:
                    return await resp.json(content_type=None)
    except Exception as exc:
        logging.warning("[Tracker] API error uid=%s: %s", uid, exc)
    return None


# ── Apply a raw API response to a TrackerEntry ──────────────────────────────
def _apply(raw: dict, entry: TrackerEntry) -> bool:
    try:
        basic = raw.get("basicInfo") or {}
        clan  = raw.get("clanBasicInfo") or {}

        new_exp = int(basic.get("exp",   entry.current_exp))
        new_lv  = int(basic.get("level", entry.level))

        # Validate: ignore if exp went backwards unrealistically
        if entry.current_exp > 0 and new_exp < entry.current_exp - 10:
            logging.info("[Tracker] uid=%s: ignoring suspicious exp drop %d→%d",
                         entry.uid, entry.current_exp, new_exp)
            entry.error = ""
            return True  # keep old value, don't crash

        prev_exp         = entry.current_exp
        entry.prev_exp   = prev_exp
        entry.current_exp = new_exp
        entry.level      = new_lv
        entry.nickname   = str(basic.get("nickname", entry.nickname))
        entry.region     = str(basic.get("region",   entry.region))
        entry.rank       = int(basic.get("rank",  entry.rank))
        entry.liked      = int(basic.get("liked", entry.liked))
        if clan:
            entry.clan_name = str(clan.get("clanName", entry.clan_name))
        entry.last_checked = datetime.now()
        entry.error = ""

        # Push sample
        entry._push_sample(time.time(), new_exp)

        # Status detection
        if new_exp > prev_exp:
            entry.tracker_status   = "grinding"
            entry.consecutive_same = 0
        else:
            entry.consecutive_same += 1
            if entry.consecutive_same >= IDLE_POLLS:
                entry.tracker_status = "idle"
            # between 1 and IDLE_POLLS: keep previous status (don't flip too fast)

        return True
    except Exception as exc:
        logging.warning("[Tracker] Parse error uid=%s: %s", entry.uid, exc)
        entry.error = "parse error"
        return False


# ── Manager ─────────────────────────────────────────────────────────────────
class ExpTrackerManager:
    def __init__(self):
        self._entries: dict[str, TrackerEntry] = {}

    def _key(self, user_id: int, uid: str) -> str:
        return f"{user_id}:{uid.strip()}"

    def is_active(self, user_id: int, uid: str) -> bool:
        return self._key(user_id, uid) in self._entries

    def get_all(self, user_id: int) -> list[dict]:
        prefix = f"{user_id}:"
        return [e.to_dict() for k, e in self._entries.items() if k.startswith(prefix)]

    async def start(self, user_id: int, uid: str, notify_fn=None) -> dict:
        uid = uid.strip()
        key = self._key(user_id, uid)

        if key in self._entries:
            return {"ok": True, "already": True, "data": self._entries[key].to_dict()}

        entry = TrackerEntry(user_id=user_id, uid=uid, created_at=datetime.now())

        raw = await _fetch(uid)
        if raw is None:
            return {"ok": False, "error": f"Could not reach API for UID {uid}. Check the UID and try again."}

        if not _apply(raw, entry):
            return {"ok": False, "error": "Received data but failed to parse player info."}

        entry.start_exp  = entry.current_exp
        entry.prev_level = entry.level
        entry.created_at = datetime.now()
        entry.notify_fn  = notify_fn
        # Push initial sample
        entry._samples.clear()
        entry._push_sample(time.time(), entry.current_exp)

        self._entries[key] = entry
        db.save_tracked_uid(user_id, uid)

        loop = asyncio.get_running_loop()
        entry.task = loop.create_task(self._poll_loop(key))
        return {"ok": True, "already": False, "data": entry.to_dict()}

    async def stop(self, user_id: int, uid: str) -> bool:
        key = self._key(user_id, uid)
        entry = self._entries.pop(key, None)
        if not entry:
            return False
        if entry.task and not entry.task.done():
            entry.task.cancel()
            try:
                await entry.task
            except asyncio.CancelledError:
                pass
        db.remove_tracked_uid(user_id, uid)
        return True

    async def restore_uid(self, user_id: int, uid: str):
        """Re-start tracking for a UID loaded from the database."""
        try:
            result = await self.start(user_id, uid)
            if result.get("ok"):
                logging.info("[Tracker] Restored tracker uid=%s user=%s", uid, user_id)
            else:
                logging.warning(
                    "[Tracker] Could not restore uid=%s user=%s: %s",
                    uid, user_id, result.get("error", "unknown"),
                )
                db.remove_tracked_uid(user_id, uid)
        except Exception as exc:
            logging.warning("[Tracker] Restore error uid=%s: %s", uid, exc)

    async def refresh_now(self, user_id: int, uid: str) -> dict:
        key = self._key(user_id, uid)
        entry = self._entries.get(key)
        if not entry:
            return {"ok": False, "error": "Tracker not found"}
        raw = await _fetch(uid)
        if raw:
            _apply(raw, entry)
        else:
            entry.error = "API unreachable"
        return {"ok": True, "data": entry.to_dict()}

    async def _poll_loop(self, key: str):
        while key in self._entries:
            await asyncio.sleep(POLL_INTERVAL)
            if key not in self._entries:
                break
            entry = self._entries[key]
            try:
                raw = await _fetch(entry.uid)
                if raw:
                    prev_lv = entry.level
                    _apply(raw, entry)
                    if (entry.notify_fn and entry.level > prev_lv
                            and prev_lv > 0):
                        asyncio.get_event_loop().create_task(
                            entry.notify_fn(
                                f"🏆 Level up!\n"
                                f"Player: {entry.nickname or entry.uid}\n"
                                f"Level {prev_lv} → {entry.level}"
                            )
                        )
                else:
                    entry.error = "API unreachable"
            except asyncio.CancelledError:
                break
            except Exception as exc:
                entry.error = str(exc)
                logging.warning("[Tracker] Poll error uid=%s: %s", entry.uid, exc)
