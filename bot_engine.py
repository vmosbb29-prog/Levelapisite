import asyncio
import ssl
import time
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

import aiohttp
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from datetime import datetime

from xDL import (
    EnC_PacKeT, CrEaTe_ProTo, DecodE_HeX, GeneRaTePk,
    EnC_Uid, EnC_Vr, AuthClan, Uaa
)
from autoup import AuToUpDaTE
from Pb2 import MajoRLoGinrEq_pb2, MajoRLoGinrEs_pb2, PorTs_pb2
from models import ActiveBotSession

login_url, ob_version, version = AuToUpDaTE()

# ── Reconnect settings ────────────────────────────────────────────────────────
_RECONNECT_CHECK_SECS  = 30   # watchdog poll interval
_RECONNECT_MISS_LIMIT  = 2    # consecutive missed checks before re-login
_RECONNECT_MAX_TRIES   = 3    # give up after this many failed re-logins

_BASE_HR = {
    'Connection': "Keep-Alive",
    'Accept-Encoding': "gzip",
    'Content-Type': "application/x-www-form-urlencoded",
    'Expect': "100-continue",
    'X-Unity-Version': "2018.4.11f1",
    'X-GA': "v1 1",
    'ReleaseVersion': ob_version,
}

_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE

_TIMEOUT = aiohttp.ClientTimeout(total=30)


async def generate_access(uid: str, password: str, ua: str):
    url = "https://100067.connect.garena.com/oauth/guest/token/grant"
    headers = {
        "Host": "100067.connect.garena.com",
        "User-Agent": ua,
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "close",
    }
    data = {
        "uid": uid,
        "password": password,
        "response_type": "token",
        "client_type": "2",
        "client_secret": "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3",
        "client_id": "100067",
    }
    async with aiohttp.ClientSession(timeout=_TIMEOUT) as session:
        async with session.post(url, headers=headers, data=data) as resp:
            if resp.status == 200:
                body = await resp.json(content_type=None)
                return body.get("open_id"), body.get("access_token")
    return None, None


async def _encrypted_proto(encoded: bytes) -> bytes:
    key = b'Yg&tc%DEuh6%Zc^8'
    iv  = b'6oyZDr22E3ychjM%'
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return cipher.encrypt(pad(encoded, AES.block_size))


async def build_major_login_payload(open_id: str, access_token: str) -> bytes:
    req = MajoRLoGinrEq_pb2.MajorLogin()
    req.event_time = str(datetime.now())[:-7]
    req.game_name = "free fire"
    req.platform_id = 1
    req.client_version = version
    req.system_software = "Android OS 9 / API-28 (PQ3B.190801.10101846/G9650ZHU2ARC6)"
    req.system_hardware = "Handheld"
    req.telecom_operator = "Verizon"
    req.network_type = "WIFI"
    req.screen_width = 1920
    req.screen_height = 1080
    req.screen_dpi = "280"
    req.processor_details = "ARM64 FP ASIMD AES VMH | 2865 | 4"
    req.memory = 3003
    req.gpu_renderer = "Adreno (TM) 640"
    req.gpu_version = "OpenGL ES 3.1 v1.46"
    req.unique_device_id = "Google|34a7dcdf-a7d5-4cb6-8d7e-3b0e448a0c57"
    req.client_ip = "223.191.51.89"
    req.language = "en"
    req.open_id = open_id
    req.open_id_type = "4"
    req.device_type = "Handheld"
    req.memory_available.version = 55
    req.memory_available.hidden_value = 81
    req.access_token = access_token
    req.platform_sdk_id = 1
    req.network_operator_a = "Verizon"
    req.network_type_a = "WIFI"
    req.client_using_version = "7428b253defc164018c604a1ebbfebdf"
    req.external_storage_total = 36235
    req.external_storage_available = 31335
    req.internal_storage_total = 2519
    req.internal_storage_available = 703
    req.game_disk_storage_available = 25010
    req.game_disk_storage_total = 26628
    req.external_sdcard_avail_storage = 32992
    req.external_sdcard_total_storage = 36235
    req.login_by = 3
    req.library_path = "/data/app/com.dts.freefireth-YPKM8jHEwAJlhpmhDhv5MQ==/lib/arm64"
    req.reg_avatar = 1
    req.library_token = "5b892aaabd688e571f688053118a162b|/data/app/com.dts.freefireth-YPKM8jHEwAJlhpmhDhv5MQ==/base.apk"
    req.channel_type = 3
    req.cpu_type = 2
    req.cpu_architecture = "64"
    req.client_version_code = "2019118695"
    req.graphics_api = "OpenGLES2"
    req.supported_astc_bitset = 16383
    req.login_by = 3
    req.login_open_id_type = 4
    req.analytics_detail = b"FwQVTgUPX1UaUllDDwcWCRBpWAUOUgsvA1snWlBaO1kFYg=="
    req.loading_time = 13564
    req.release_channel = "android"
    req.extra_info = "KqsHTymw5/5GB23YGniUYN2/q47GATrq7eFeRatf0NkwLKEMQ0PK5BKEk72dPflAxUlEBir6Vtey83XqF593qsl8hwY="
    req.android_engine_init_flag = 110009
    req.if_push = 1
    req.is_vpn = 1
    req.origin_platform_type = "4"
    req.primary_platform_type = "4"
    return await _encrypted_proto(req.SerializeToString())


async def do_major_login(payload: bytes, ua: str) -> bytes | None:
    url = f"{login_url}MajorLogin"
    headers = {**_BASE_HR, 'User-Agent': ua}
    async with aiohttp.ClientSession(timeout=_TIMEOUT) as session:
        async with session.post(url, data=payload, headers=headers, ssl=_SSL_CTX) as resp:
            if resp.status == 200:
                return await resp.read()
    return None


async def get_login_data(base_url: str, payload: bytes, jwt_token: str, ua: str) -> bytes | None:
    url = f"{base_url}/GetLoginData"
    headers = {**_BASE_HR, 'User-Agent': ua, 'Authorization': f"Bearer {jwt_token}"}
    async with aiohttp.ClientSession(timeout=_TIMEOUT) as session:
        async with session.post(url, data=payload, headers=headers, ssl=_SSL_CTX) as resp:
            if resp.status == 200:
                return await resp.read()
    return None


def decrypt_major_login(data: bytes) -> MajoRLoGinrEs_pb2.MajorLoginRes:
    proto = MajoRLoGinrEs_pb2.MajorLoginRes()
    proto.ParseFromString(data)
    return proto


def decrypt_login_data(data: bytes) -> PorTs_pb2.GetLoginData:
    proto = PorTs_pb2.GetLoginData()
    proto.ParseFromString(data)
    return proto


async def build_auth_packet(bot_uid: int, token: str, timestamp: int, key: bytes, iv: bytes) -> str:
    uid_hex = hex(bot_uid)[2:]
    uid_len = len(uid_hex)
    enc_ts = await DecodE_HeX(timestamp)
    enc_token = token.encode().hex()
    enc_pkt = await EnC_PacKeT(enc_token, key, iv)
    pkt_len = hex(len(enc_pkt) // 2)[2:]
    padding = {9: '0000000', 8: '00000000', 10: '000000', 7: '000000000'}.get(uid_len, '0000000')
    return f"0115{padding}{uid_hex}{enc_ts}00000{pkt_len}{enc_pkt}"


async def join_teamcode_packet(team_code: str, key: bytes, iv: bytes, region: str) -> bytes:
    fields = {
        1: 4,
        2: {
            4: bytes.fromhex("01090a0b121920"),
            5: str(team_code),
            6: 6,
            8: 1,
            9: {2: 800, 6: 11, 8: "1.111.1", 9: 5, 10: 1},
        },
    }
    if region.lower() == "ind":
        ptype = '0514'
    elif region.lower() == "bd":
        ptype = "0519"
    else:
        ptype = "0515"
    return await GeneRaTePk((await CrEaTe_ProTo(fields)).hex(), ptype, key, iv)


async def start_auto_packet(key: bytes, iv: bytes, region: str) -> bytes:
    fields = {1: 9, 2: {1: 12480598706}}
    if region.lower() == "ind":
        ptype = '0514'
    elif region.lower() == "bd":
        ptype = "0519"
    else:
        ptype = "0515"
    return await GeneRaTePk((await CrEaTe_ProTo(fields)).hex(), ptype, key, iv)


async def leave_squad_packet(key: bytes, iv: bytes, region: str) -> bytes:
    fields = {1: 7, 2: {1: 12480598706}}
    if region.lower() == "ind":
        ptype = '0514'
    elif region.lower() == "bd":
        ptype = "0519"
    else:
        ptype = "0515"
    return await GeneRaTePk((await CrEaTe_ProTo(fields)).hex(), ptype, key, iv)


async def tcp_online(session: ActiveBotSession):
    while session.status == "online":
        writer = None
        try:
            reader, writer = await asyncio.open_connection(session.online_ip, session.online_port)
            session.online_writer = writer
            writer.write(bytes.fromhex(session.token))
            await writer.drain()
            session.add_log(f"[Online TCP] Connected → {session.online_ip}:{session.online_port}", "success")
            while True:
                data = await reader.read(9999)
                if not data:
                    break
        except asyncio.CancelledError:
            break
        except Exception as e:
            session.add_log(f"[Online TCP] Error: {e}", "error")
        finally:
            session.online_writer = None
            if writer:
                try:
                    writer.close()
                    await writer.wait_closed()
                except Exception:
                    pass
        if session.status != "online":
            break
        await asyncio.sleep(0.5)


async def tcp_chat(session: ActiveBotSession, ready_event: asyncio.Event):
    while session.status == "online":
        writer = None
        try:
            reader, writer = await asyncio.open_connection(session.chat_ip, session.chat_port)
            session.whisper_writer = writer
            writer.write(bytes.fromhex(session.token))
            await writer.drain()
            ready_event.set()
            session.add_log(f"[Chat TCP] Connected → {session.chat_ip}:{session.chat_port}", "success")
            if session.clan_id:
                pkt = await AuthClan(session.clan_id, session.clan_compiled_data, session.key, session.iv)
                if pkt:
                    writer.write(pkt)
                    await writer.drain()
                    session.add_log("[Chat TCP] Clan auth sent", "info")
            while True:
                data = await reader.read(9999)
                if not data:
                    break
        except asyncio.CancelledError:
            break
        except Exception as e:
            if not ready_event.is_set():
                ready_event.set()
            session.add_log(f"[Chat TCP] Error: {e}", "error")
        finally:
            session.whisper_writer = None
            if writer:
                try:
                    writer.close()
                    await writer.wait_closed()
                except Exception:
                    pass
        if session.status != "online":
            break
        await asyncio.sleep(0.5)


START_SPAM_DURATION = 18
WAIT_AFTER_MATCH    = 5
START_SPAM_DELAY    = 0.1


async def auto_start_loop(session: ActiveBotSession, team_code: str):
    session.auto_start_running = True
    session.stop_auto = False
    session.add_log(f"Auto-start loop started for team {team_code}", "success")
    session.add_activity("loop_start", code=team_code)

    if session.notify_fn:
        asyncio.get_event_loop().create_task(
            session.notify_fn(
                f"🚀 Auto-start launched\n"
                f"Bot: {session.display_name}\n"
                f"Team code: {team_code}"
            )
        )

    while not session.stop_auto and session.status == "online":
        cycle = session.cycles_completed + 1
        try:
            session.bot_state = "searching"
            session.add_log(f"[Cycle {cycle}] Joining squad → code {team_code}")
            session.add_activity("searching", cycle=cycle, code=team_code)

            join_pkt = await join_teamcode_packet(team_code, session.key, session.iv, session.region)
            if session.online_writer:
                session.online_writer.write(join_pkt)
                await session.online_writer.drain()
            await asyncio.sleep(2)

            session.bot_state = "in_match"
            session.add_log(f"[Cycle {cycle}] Spamming start packets ({START_SPAM_DURATION}s)…")
            session.add_activity("in_match", cycle=cycle)

            start_pkt = await start_auto_packet(session.key, session.iv, session.region)
            end_time = time.time() + START_SPAM_DURATION
            while time.time() < end_time and not session.stop_auto:
                if session.online_writer:
                    session.online_writer.write(start_pkt)
                    await session.online_writer.drain()
                await asyncio.sleep(START_SPAM_DELAY)

            if session.stop_auto:
                break

            session.bot_state = "waiting"
            session.add_log(f"[Cycle {cycle}] Waiting {WAIT_AFTER_MATCH}s after match…")
            waited = 0
            while waited < WAIT_AFTER_MATCH and not session.stop_auto:
                await asyncio.sleep(1)
                waited += 1

            if session.stop_auto:
                break

            session.bot_state = "idle"
            session.add_log(f"[Cycle {cycle}] Leaving squad")
            leave_pkt = await leave_squad_packet(session.key, session.iv, session.region)
            if session.online_writer:
                session.online_writer.write(leave_pkt)
                await session.online_writer.drain()
            await asyncio.sleep(2)

            session.cycles_completed += 1
            session.add_activity("cycle_complete", cycle=session.cycles_completed)

            if session.notify_fn and session.cycles_completed % 5 == 0:
                asyncio.get_event_loop().create_task(
                    session.notify_fn(
                        f"🔁 Cycle milestone: {session.cycles_completed} cycles done\n"
                        f"Bot: {session.display_name}  |  Code: {team_code}"
                    )
                )

        except asyncio.CancelledError:
            break
        except Exception as e:
            session.add_log(f"[Cycle {cycle}] Error: {e}", "error")
            session.add_activity("error", cycle=cycle, msg=str(e))
            break

    session.bot_state = "idle"
    session.auto_start_running = False
    session.stop_auto = False
    session.add_log("Auto-start loop stopped", "warn")
    session.add_activity("loop_stop")

    if session.notify_fn:
        asyncio.get_event_loop().create_task(
            session.notify_fn(
                f"⏹️ Auto-start stopped\n"
                f"Bot: {session.display_name}  |  Total cycles: {session.cycles_completed}"
            )
        )


async def start_bot(user_id: int, account_id: int, uid: str, password: str) -> ActiveBotSession:
    ua = Uaa()

    open_id, access_token = await generate_access(uid, password, ua)
    if not open_id or not access_token:
        raise RuntimeError("OAuth failed — check UID / Password")

    payload = await build_major_login_payload(open_id, access_token)
    raw = await do_major_login(payload, ua)
    if not raw:
        raise RuntimeError("MajorLogin request failed — server may be down")
    login_res = decrypt_major_login(raw)

    jwt_token = login_res.token
    base_url  = login_res.url
    key       = login_res.key
    iv        = login_res.iv
    timestamp = int(login_res.timestamp)
    region    = login_res.region or "IND"
    bot_uid   = int(login_res.account_uid)

    if not jwt_token:
        raise RuntimeError("MajorLogin returned empty token — credentials may be wrong")

    ld_raw = await get_login_data(base_url, payload, jwt_token, ua)
    if not ld_raw:
        raise RuntimeError("GetLoginData request failed")
    ld = decrypt_login_data(ld_raw)

    online_ip, online_port_str = ld.Online_IP_Port.split(":")
    chat_ip,   chat_port_str   = ld.AccountIP_Port.split(":")
    display_name = getattr(ld, 'AccountName', '') or uid

    auth_token = await build_auth_packet(bot_uid, jwt_token, timestamp, key, iv)

    session = ActiveBotSession(
        user_id=user_id,
        account_id=account_id,
        uid=uid,
        bot_uid=str(bot_uid),
        display_name=display_name,
        region=region,
        key=key,
        iv=iv,
        token=auth_token,
        jwt_token=jwt_token,
        online_ip=online_ip,
        online_port=int(online_port_str),
        chat_ip=chat_ip,
        chat_port=int(chat_port_str),
        clan_id=int(ld.Clan_ID) if ld.Clan_ID else None,
        clan_compiled_data=str(ld.Clan_Compiled_Data) if ld.Clan_Compiled_Data else None,
        status="online",
        bot_state="idle",
        started_at=datetime.now(),
        password=password,
    )
    session.add_log(f"Logged in as {display_name} (UID {bot_uid}) | Region: {region}", "success")
    session.add_log(f"Online: {online_ip}:{online_port_str}  Chat: {chat_ip}:{chat_port_str}")
    session.add_activity("started", region=region)

    ready_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    session.chat_task    = loop.create_task(tcp_chat(session, ready_event))
    session.online_task  = loop.create_task(tcp_online(session))

    try:
        await asyncio.wait_for(ready_event.wait(), timeout=15.0)
        session.add_log("Bot is ONLINE", "success")
        session.watchdog_task = loop.create_task(_watchdog(session))
    except asyncio.TimeoutError:
        session.status = "offline"
        for t in [session.chat_task, session.online_task]:
            t.cancel()
        raise RuntimeError(
            f"TCP connection timed out — could not reach {chat_ip}:{chat_port_str}. "
            "Server may be blocking outbound TCP on this port."
        )

    return session


async def _do_reconnect(session: ActiveBotSession):
    """Full re-login to refresh game server credentials in-place."""
    ua = Uaa()
    open_id, access_token = await generate_access(session.uid, session.password, ua)
    if not open_id or not access_token:
        raise RuntimeError("OAuth failed during reconnect")

    payload = await build_major_login_payload(open_id, access_token)
    raw = await do_major_login(payload, ua)
    if not raw:
        raise RuntimeError("MajorLogin failed during reconnect")

    login_res = decrypt_major_login(raw)
    jwt_token = login_res.token
    if not jwt_token:
        raise RuntimeError("Re-login returned empty token")

    key       = login_res.key
    iv        = login_res.iv
    timestamp = int(login_res.timestamp)
    bot_uid   = int(login_res.account_uid)

    ld_raw = await get_login_data(login_res.url, payload, jwt_token, ua)
    if not ld_raw:
        raise RuntimeError("GetLoginData failed during reconnect")
    ld = decrypt_login_data(ld_raw)

    online_ip, online_port_str = ld.Online_IP_Port.split(":")
    chat_ip,   chat_port_str   = ld.AccountIP_Port.split(":")

    auth_token = await build_auth_packet(bot_uid, jwt_token, timestamp, key, iv)

    # Update session credentials in-place
    session.key         = key
    session.iv          = iv
    session.token       = auth_token
    session.jwt_token   = jwt_token
    session.online_ip   = online_ip
    session.online_port = int(online_port_str)
    session.chat_ip     = chat_ip
    session.chat_port   = int(chat_port_str)

    # Cancel stale tasks
    for task in [session.chat_task, session.online_task]:
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    ready_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    session.chat_task   = loop.create_task(tcp_chat(session, ready_event))
    session.online_task = loop.create_task(tcp_online(session))
    await asyncio.wait_for(ready_event.wait(), timeout=15.0)


async def _watchdog(session: ActiveBotSession):
    """Monitors TCP health; triggers full re-login if writers go missing."""
    while session.status == "online":
        await asyncio.sleep(_RECONNECT_CHECK_SECS)
        if session.status != "online":
            break
        if session.is_reconnecting:
            continue

        both_missing = (
            session.online_writer is None and session.whisper_writer is None
        )
        if both_missing:
            session._missing_writer_count += 1
        else:
            session._missing_writer_count = 0
            session.reconnect_attempts = 0

        if session._missing_writer_count >= _RECONNECT_MISS_LIMIT:
            session._missing_writer_count = 0
            if session.reconnect_attempts >= _RECONNECT_MAX_TRIES:
                session.status = "offline"
                session.add_log(
                    f"Auto-reconnect gave up after {_RECONNECT_MAX_TRIES} attempts.",
                    "error",
                )
                session.add_activity("reconnect_failed")
                if session.notify_fn:
                    asyncio.get_event_loop().create_task(
                        session.notify_fn(
                            f"❌ Reconnect failed — bot went offline\n"
                            f"Bot: {session.display_name}\n"
                            f"All {_RECONNECT_MAX_TRIES} re-login attempts failed."
                        )
                    )
                break

            session.reconnect_attempts += 1
            session.is_reconnecting = True
            session.add_log(
                f"[Watchdog] TCP lost — re-login attempt "
                f"{session.reconnect_attempts}/{_RECONNECT_MAX_TRIES}…",
                "warn",
            )
            if session.notify_fn:
                asyncio.get_event_loop().create_task(
                    session.notify_fn(
                        f"🔄 TCP connection dropped — reconnecting\n"
                        f"Bot: {session.display_name}\n"
                        f"Attempt {session.reconnect_attempts}/{_RECONNECT_MAX_TRIES}…"
                    )
                )
            try:
                await _do_reconnect(session)
                session.is_reconnecting = False
                session.add_log("Auto-reconnect successful!", "success")
                session.add_activity("reconnected")
                if session.notify_fn:
                    asyncio.get_event_loop().create_task(
                        session.notify_fn(
                            f"✅ Reconnected successfully!\n"
                            f"Bot: {session.display_name} is back online."
                        )
                    )
            except Exception as exc:
                session.is_reconnecting = False
                session.add_log(f"[Watchdog] Re-login error: {exc}", "error")


async def run_teamcode(session: ActiveBotSession, team_code: str):
    if session.auto_start_running:
        raise RuntimeError("Auto-start already running. Stop it first.")
    if not team_code.strip().isdigit():
        raise ValueError("Team code must be numeric digits only.")
    session.last_teamcode = team_code.strip()
    loop = asyncio.get_running_loop()
    session.auto_start_task = loop.create_task(auto_start_loop(session, team_code.strip()))


async def stop_teamcode(session: ActiveBotSession):
    session.stop_auto = True
    if session.auto_start_task and not session.auto_start_task.done():
        session.auto_start_task.cancel()
        try:
            await session.auto_start_task
        except asyncio.CancelledError:
            pass
    session.auto_start_running = False
    session.bot_state = "idle"
    session.add_log("Auto-start stopped by user", "warn")


async def stop_bot(session: ActiveBotSession):
    session.status = "offline"
    session.bot_state = "idle"
    session.stop_auto = True
    for task in [session.watchdog_task, session.auto_start_task, session.chat_task, session.online_task]:
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
    for writer in [session.whisper_writer, session.online_writer]:
        if writer:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
    session.whisper_writer = None
    session.online_writer  = None
    session.add_log("Bot disconnected", "warn")
    session.add_activity("stopped")
