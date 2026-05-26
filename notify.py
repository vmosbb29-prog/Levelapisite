import logging
import aiohttp

_TIMEOUT = aiohttp.ClientTimeout(total=8)


async def _post(url: str, payload: dict):
    try:
        async with aiohttp.ClientSession(timeout=_TIMEOUT) as session:
            async with session.post(url, json=payload) as resp:
                if resp.status >= 400:
                    logging.warning("[Notify] HTTP %s from %s", resp.status, url)
    except Exception as exc:
        logging.warning("[Notify] Failed to send: %s", exc)


async def send_discord(webhook_url: str, message: str):
    if not webhook_url:
        return
    await _post(webhook_url, {
        "content": message,
        "username": "Level-Up Bot",
    })


async def send_telegram(token: str, chat_id: str, message: str):
    if not token or not chat_id:
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    await _post(url, {"chat_id": chat_id, "text": message, "parse_mode": "HTML"})


async def notify_user(settings: dict, message: str):
    """Send a notification via all configured channels for a user."""
    if settings.get("discord_webhook"):
        await send_discord(settings["discord_webhook"], message)
    if settings.get("telegram_token") and settings.get("telegram_chat_id"):
        await send_telegram(
            settings["telegram_token"],
            settings["telegram_chat_id"],
            message,
        )
