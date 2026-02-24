import json
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List

import config
from ibkr_connection import get_account_summary, get_positions, connect, disconnect


HISTORY_FILE = config.DATA_DIR / "portfolio_history.json"


@dataclass
class PortfolioSnapshot:
    timestamp: str  # ISO8601
    total_value: float


def _load_history() -> List[PortfolioSnapshot]:
    if not HISTORY_FILE.exists():
        return []
    try:
        raw = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []
    out: List[PortfolioSnapshot] = []
    for item in raw:
        try:
            out.append(PortfolioSnapshot(**item))
        except TypeError:
            continue
    return out


def _save_history(items: List[PortfolioSnapshot]) -> None:
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_FILE.write_text(json.dumps([asdict(i) for i in items], indent=2), encoding="utf-8")


def _extract_total_value() -> float | None:
    """
    Pull total account value from account summary.
    Tries common keys across base currency values.
    """
    if not connect():
        return None
    try:
        rows = get_account_summary()
        # ib_async accountSummary rows have fields: tag, value, currency, account
        # We look for NetLiquidation or TotalCashValue in base currency.
        candidates = []
        for row in rows:
            tag = getattr(row, "tag", "")
            value = getattr(row, "value", "")
            currency = getattr(row, "currency", "")
            if not value:
                continue
            if tag in ("NetLiquidation", "TotalCashValue"):
                try:
                    v = float(value)
                except ValueError:
                    continue
                # Prefer base currency, but if unknown just take it
                candidates.append((tag, currency, v))
        if not candidates:
            return None
        # Prefer NetLiquidation over TotalCashValue
        candidates.sort(key=lambda x: 0 if x[0] == "NetLiquidation" else 1)
        return candidates[0][2]
    finally:
        disconnect()


def record_snapshot() -> float | None:
    """
    Record a new portfolio snapshot and return the total value.
    """
    value = _extract_total_value()
    if value is None:
        return None
    history = _load_history()
    history.append(PortfolioSnapshot(timestamp=datetime.now().isoformat(timespec="minutes"), total_value=value))
    # Trim to configured length
    history = history[-config.PORTFOLIO_HISTORY_LENGTH :]
    _save_history(history)
    return value


def get_recent_history() -> List[PortfolioSnapshot]:
    """
    Get the most recent N snapshots (where N is PORTFOLIO_HISTORY_LENGTH).
    """
    history = _load_history()
    return history[-config.PORTFOLIO_HISTORY_LENGTH :]


def format_positions() -> str:
    """
    Return a human-readable summary of current positions.
    """
    if not connect():
        return "Could not connect to IBKR for positions."
    try:
        positions = get_positions()
        if not positions:
            return "No open positions."
        lines = []
        for pos in positions:
            contract = getattr(pos, "contract", None)
            symbol = getattr(contract, "symbol", "?")
            sec_type = getattr(contract, "secType", "")
            currency = getattr(contract, "currency", "")
            position = getattr(pos, "position", 0)
            avg_cost = getattr(pos, "avgCost", 0.0)
            lines.append(
                f"{symbol} ({sec_type} {currency}): {position} @ {avg_cost:.2f}"
            )
        return "\n".join(lines)
    finally:
        disconnect()

