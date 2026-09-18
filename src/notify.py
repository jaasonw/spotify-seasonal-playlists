import logging
import time

import requests

import config
import constant

# ponytail: module-level cooldown timer, single-process assumption is fine
# since the worker runs as one process; switch to a DB-backed timestamp if
# that changes.
_last_alert_time = 0


def send_telegram(message):
    if not config.telegram_bot_token or not config.telegram_chat_id:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{config.telegram_bot_token}/sendMessage",
            json={"chat_id": config.telegram_chat_id, "text": message},
            timeout=10,
        )
    except Exception:
        logging.exception("Failed to send Telegram alert")


def check_error_rate_and_alert(db):
    """Alert on Telegram if the system-wide error rate is elevated. Rate-limited
    by ALERT_COOLDOWN so an ongoing outage doesn't spam the chat."""
    global _last_alert_time
    now = time.time()
    if now - _last_alert_time < constant.ALERT_COOLDOWN:
        return

    count = db.get_error_count_since(constant.ERROR_RATE_WINDOW)
    if count >= constant.ERROR_RATE_THRESHOLD:
        _last_alert_time = now
        minutes = constant.ERROR_RATE_WINDOW // 60
        send_telegram(
            f"⚠️ Elevated error rate: {count} errors in the last {minutes} min. "
            f"Spotify API or network may be down."
        )
