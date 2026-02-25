"""
SMA (Simple Moving Average) Crossover Strategy.
Buy when fast SMA crosses above slow SMA; sell when fast crosses below slow.
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Iterable

import pandas as pd

import config
from ibkr_connection import (
    connect,
    disconnect,
    fetch_historical_bars,
    bars_to_dataframe,
    place_market_order,
    get_positions,
)

logger = logging.getLogger(__name__)


class Signal(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass
class StrategyResult:
    symbol: str
    signal: Signal
    price: float
    fast_sma: float
    slow_sma: float
    current_position: int
    message: str


def compute_sma(df: pd.DataFrame, fast: int, slow: int) -> pd.DataFrame:
    """Add fast and slow SMA columns to DataFrame."""
    df = df.copy()
    df["sma_fast"] = df["close"].rolling(window=fast).mean()
    df["sma_slow"] = df["close"].rolling(window=slow).mean()
    return df


def _get_sma_settings(strategy_type: Optional[str] = None) -> dict:
    """
    Return settings for the current SMA strategy type.

    Types:
      - scalping: 5 min bars, 20/50 SMA
      - swing:   1h bars, 20/50 SMA
      - position (default): 1D bars, 50/200 SMA
    """
    mode = (strategy_type or getattr(config, "SMA_STRATEGY_TYPE", "position")).lower()
    if mode == "scalping":
        return {
            "duration": "2 D",
            "bar_size": "5 mins",
            "fast": 20,
            "slow": 50,
        }
    if mode == "swing":
        return {
            "duration": "30 D",
            "bar_size": "1 hour",
            "fast": 20,
            "slow": 50,
        }
    # position (default)
    return {
        "duration": "12 M",
        "bar_size": "1 day",
        "fast": 50,
        "slow": 200,
    }


def detect_crossover(df: pd.DataFrame) -> Signal:
    """
    Detect SMA crossover on the latest bars.
    Returns BUY if fast crossed above slow, SELL if fast crossed below slow.
    """
    if len(df) < 3:
        return Signal.HOLD

    # Compare last 3 rows to detect crossover
    prev = df.iloc[-3]
    curr = df.iloc[-2]
    latest = df.iloc[-1]

    prev_fast = prev["sma_fast"]
    prev_slow = prev["sma_slow"]
    curr_fast = curr["sma_fast"]
    curr_slow = curr["sma_slow"]
    latest_fast = latest["sma_fast"]
    latest_slow = latest["sma_slow"]

    # Skip if any NaN
    if pd.isna(prev_fast) or pd.isna(prev_slow) or pd.isna(curr_fast) or pd.isna(curr_slow):
        return Signal.HOLD

    # Golden cross: fast was below slow, now above
    if prev_fast <= prev_slow and curr_fast > curr_slow:
        return Signal.BUY

    # Death cross: fast was above slow, now below
    if prev_fast >= prev_slow and curr_fast < curr_slow:
        return Signal.SELL

    return Signal.HOLD


def evaluate_symbol(symbol: str, strategy_type: Optional[str] = None) -> Optional[StrategyResult]:
    """
    Evaluate SMA crossover for a single symbol using the configured strategy type.
    Fetches data, computes SMAs, and returns signal.
    """
    settings = _get_sma_settings(strategy_type)

    bars = fetch_historical_bars(
        symbol,
        duration=settings["duration"],
        bar_size=settings["bar_size"],
    )
    if not bars:
        return None

    df = bars_to_dataframe(bars)
    if df is None or len(df) < settings["slow"]:
        return None

    df = compute_sma(df, settings["fast"], settings["slow"])
    signal = detect_crossover(df)

    latest = df.iloc[-1]
    price = float(latest["close"])
    fast_sma = float(latest["sma_fast"])
    slow_sma = float(latest["sma_slow"])

    # Get current position
    positions = get_positions()
    current_position = 0
    for pos in positions:
        if hasattr(pos.contract, "symbol") and pos.contract.symbol == symbol:
            current_position = pos.position
            break

    if signal == Signal.BUY:
        message = f"Golden cross: SMA{settings['fast']} crossed above SMA{settings['slow']}"
    elif signal == Signal.SELL:
        message = f"Death cross: SMA{settings['fast']} crossed below SMA{settings['slow']}"
    else:
        message = "No crossover signal"

    return StrategyResult(
        symbol=symbol,
        signal=signal,
        price=price,
        fast_sma=fast_sma,
        slow_sma=slow_sma,
        current_position=current_position,
        message=message,
    )


def run_strategy(symbols: Optional[Iterable[str]] = None, strategy_type: Optional[str] = None):
    """
    Run SMA crossover strategy on all configured symbols.
    Executes trades based on signals.
    """
    if not connect():
        logger.error("Cannot connect to IBKR. Aborting strategy.")
        return []

    trade_symbols = list(symbols) if symbols is not None else list(config.TRADE_SYMBOLS)

    results = []
    try:
        for symbol in trade_symbols:
            result = evaluate_symbol(symbol, strategy_type=strategy_type)
            if result:
                results.append(result)

                if result.signal == Signal.BUY:
                    place_market_order(symbol, "BUY", config.SHARES_PER_TRADE)
                elif result.signal == Signal.SELL and result.current_position > 0:
                    place_market_order(symbol, "SELL", result.current_position)
    finally:
        disconnect()

    return results
