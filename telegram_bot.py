"""
Simple Telegram bot for user subscriptions.

Commands:
  /start                - show welcome and current settings
  /subscribe            - subscribe to reports (uses defaults)
  /unsubscribe          - stop receiving reports
  /setsymbols AAPL,MSFT - set symbols for your report
  /settimes 08:00,20:00 - set delivery times (HH:MM,24h)
  /setfrequency 60      - set report frequency in minutes
  /help                 - show help

Run with:
  python telegram_bot.py
"""

import logging
import time
from typing import Optional, List

import requests

import config
from notifier import send_telegram
from telegram_users import TelegramUser, get_user, upsert_user


logger = logging.getLogger(__name__)


API_URL = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}"


def _call(method: str, **params) -> dict:
    url = f"{API_URL}/{method}"
    r = requests.get(url, params=params, timeout=25)
    r.raise_for_status()
    return r.json()


def _parse_list_arg(text: str) -> List[str]:
    # Split on commas or whitespace, strip, and uppercase for symbols
    items: List[str] = []
    for part in text.replace(",", " ").split():
        cleaned = part.strip()
        if cleaned:
            items.append(cleaned.upper())
    return items


def _handle_start(chat_id: int, username: Optional[str]) -> None:
    user = get_user(chat_id)
    if not user:
        user = TelegramUser(chat_id=chat_id, username=username)
        upsert_user(user)

    msg_lines = [
        "Welcome to Trading Tabby ≽^•⩊•^≼",
        "",
        "You can subscribe to scheduled reports and customise:",
        "- Stocks in your report",
        "- Times of day to receive updates",
        "- Frequency (every N minutes)",
        "",
        "Commands:",
        "/subscribe      - start receiving reports",
        "/unsubscribe    - stop all reports",
        "/setsymbols AAPL,MSFT,TSLA",
        "/settimes 08:00,20:00",
        "/setfrequency 60",
        "/help           - show this help",
    ]
    send_telegram("\n".join(msg_lines), chat_id=str(chat_id))


def _handle_subscribe(chat_id: int, username: Optional[str]) -> None:
    user = get_user(chat_id) or TelegramUser(chat_id=chat_id, username=username)
    user.subscribed = True
    upsert_user(user)
    send_telegram("You are now subscribed to scheduled reports.", chat_id=str(chat_id))


def _handle_unsubscribe(chat_id: int, username: Optional[str]) -> None:
    user = get_user(chat_id) or TelegramUser(chat_id=chat_id, username=username)
    user.subscribed = False
    upsert_user(user)
    send_telegram("You have been unsubscribed from scheduled reports.", chat_id=str(chat_id))


def _handle_setsymbols(chat_id: int, username: Optional[str], args: str) -> None:
    symbols = _parse_list_arg(args)
    if not symbols:
        send_telegram("Please provide at least one symbol, e.g. /setsymbols AAPL,MSFT", chat_id=str(chat_id))
        return
    user = get_user(chat_id) or TelegramUser(chat_id=chat_id, username=username)
    user.symbols = symbols
    upsert_user(user)
    send_telegram(
        "Your report symbols have been updated to: " + ", ".join(symbols),
        chat_id=str(chat_id),
    )


def _handle_settimes(chat_id: int, username: Optional[str], args: str) -> None:
    times = _parse_list_arg(args)
    if not times:
        send_telegram("Please provide at least one time, e.g. /settimes 08:00,20:00", chat_id=str(chat_id))
        return
    # Validation: HH:MM with 00<=HH<=23 and 00<=MM<=59
    cleaned: List[str] = []
    for t in times:
        if len(t) != 5 or t[2] != ":" or not t[:2].isdigit() or not t[3:].isdigit():
            continue
        h = int(t[:2])
        m = int(t[3:])
        if 0 <= h <= 23 and 0 <= m <= 59:
            cleaned.append(f"{h:02d}:{m:02d}")
    if not cleaned:
        send_telegram("Times must be in HH:MM 24h format, e.g. 08:00,20:00", chat_id=str(chat_id))
        return
    user = get_user(chat_id) or TelegramUser(chat_id=chat_id, username=username)
    user.times = cleaned
    # If the user sets explicit times, clear frequency so times take precedence.
    user.frequency_minutes = None
    upsert_user(user)
    send_telegram(
        "Your report times have been updated to: " + ", ".join(cleaned),
        chat_id=str(chat_id),
    )


def _handle_setfrequency(chat_id: int, username: Optional[str], args: str) -> None:
    args = args.strip()
    if not args:
        send_telegram("Usage: /setfrequency <minutes>, e.g. /setfrequency 60", chat_id=str(chat_id))
        return
    try:
        minutes = int(args.split()[0])
    except ValueError:
        send_telegram("Frequency must be a number of minutes, e.g. /setfrequency 60", chat_id=str(chat_id))
        return
    if minutes <= 0:
        send_telegram("Frequency must be a positive number of minutes.", chat_id=str(chat_id))
        return
    if minutes < 5:
        send_telegram("Minimum frequency is 5 minutes to avoid rate limits.", chat_id=str(chat_id))
        return

    user = get_user(chat_id) or TelegramUser(chat_id=chat_id, username=username)
    user.frequency_minutes = minutes
    # Keep any existing times; scheduler will trigger on either times OR frequency.
    upsert_user(user)
    send_telegram(
        f"Your report frequency has been set to every {minutes} minutes.",
        chat_id=str(chat_id),
    )


def _handle_help(chat_id: int) -> None:
    _handle_start(chat_id, None)


def _process_update(update: dict) -> None:
    message = update.get("message") or update.get("edited_message")
    if not message:
        return
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    if chat_id is None:
        return
    text = message.get("text") or ""
    username = (message.get("from") or {}).get("username")

    if not text.startswith("/"):
        return

    parts = text.split(maxsplit=1)
    cmd = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""

    if cmd == "/start":
        _handle_start(chat_id, username)
    elif cmd == "/subscribe":
        _handle_subscribe(chat_id, username)
    elif cmd == "/unsubscribe":
        _handle_unsubscribe(chat_id, username)
    elif cmd == "/setsymbols":
        _handle_setsymbols(chat_id, username, args)
    elif cmd == "/settimes":
        _handle_settimes(chat_id, username, args)
    elif cmd == "/setfrequency":
        _handle_setfrequency(chat_id, username, args)
    elif cmd == "/help":
        _handle_help(chat_id)


def run_bot() -> None:
    if not config.TELEGRAM_BOT_TOKEN:
        raise SystemExit("TELEGRAM_BOT_TOKEN is not set in environment/config.")

    logger.info("Starting Telegram bot long-polling...")
    offset: Optional[int] = None
    while True:
        try:
            params = {"timeout": 20}
            if offset is not None:
                params["offset"] = offset
            data = _call("getUpdates", **params)
            if not data.get("ok"):
                logger.warning(f"Telegram getUpdates returned not ok: {data}")
                time.sleep(5)
                continue
            for update in data.get("result", []):
                offset = update["update_id"] + 1
                _process_update(update)
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"Error in Telegram bot loop: {e}")
            time.sleep(5)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    run_bot()

