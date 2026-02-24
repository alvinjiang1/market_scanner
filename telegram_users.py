import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict

import config


USERS_FILE = config.DATA_DIR / "telegram_users.json"

def _is_valid_hhmm(t: str) -> bool:
    if len(t) != 5 or t[2] != ":":
        return False
    hh, mm = t[:2], t[3:]
    if not hh.isdigit() or not mm.isdigit():
        return False
    h = int(hh)
    m = int(mm)
    return 0 <= h <= 23 and 0 <= m <= 59


@dataclass
class TelegramUser:
    chat_id: int
    username: str | None = None
    subscribed: bool = True
    symbols: List[str] | None = None
    times: List[str] | None = None  # "HH:MM" strings
    frequency_minutes: int | None = None  # If set, send every N minutes

    def effective_symbols(self) -> List[str]:
        from config import SCAN_SYMBOLS

        return self.symbols or list(SCAN_SYMBOLS)

    def effective_strategy_symbols(self) -> List[str]:
        from config import TRADE_SYMBOLS

        # If the user explicitly chose symbols, use them for strategy too;
        # otherwise fall back to the global strategy universe.
        return self.symbols or list(TRADE_SYMBOLS)

    def effective_times(self) -> List[str]:
        from config import REPORT_TIMES

        base = self.times or list(REPORT_TIMES)
        cleaned = [t for t in base if isinstance(t, str) and _is_valid_hhmm(t)]
        return cleaned or ["08:00", "20:00"]


def _load_raw() -> Dict[str, dict]:
    if not USERS_FILE.exists():
        return {}
    try:
        return json.loads(USERS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_raw(data: Dict[str, dict]) -> None:
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    USERS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def get_user(chat_id: int) -> TelegramUser | None:
    data = _load_raw()
    entry = data.get(str(chat_id))
    if not entry:
        return None
    return TelegramUser(**entry)


def upsert_user(user: TelegramUser) -> None:
    data = _load_raw()
    data[str(user.chat_id)] = asdict(user)
    _save_raw(data)


def all_users() -> List[TelegramUser]:
    data = _load_raw()
    return [TelegramUser(**v) for v in data.values()]

