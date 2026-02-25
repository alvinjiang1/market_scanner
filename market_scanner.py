"""
Market Scanner - computes key technical indicators for market and user-defined stocks.
Runs automatically on a schedule and provides data for reports.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Iterable

import pandas as pd
import numpy as np

import config
from ibkr_connection import connect, disconnect, fetch_historical_bars, bars_to_dataframe
from sma_strategy import _get_sma_settings

logger = logging.getLogger(__name__)


@dataclass
class StockIndicators:
    symbol: str
    price: float
    sma_20: float
    sma_50: float
    rsi_14: float
    macd_line: float
    macd_signal: float
    macd_histogram: float
    volume: int
    volume_sma_20: float
    atr_14: float
    trend: str  # "bullish", "bearish", "neutral"
    error: Optional[str] = None


@dataclass
class MarketSnapshot:
    timestamp: datetime
    stocks: list[StockIndicators] = field(default_factory=list)
    market_summary: dict = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


def compute_rsi(series: pd.Series, period: int = 14) -> float:
    """Compute RSI (Relative Strength Index)."""
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50.0


def compute_macd(
    series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
) -> tuple[float, float, float]:
    """Compute MACD line, signal line, and histogram."""
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    macd_signal = macd_line.ewm(span=signal, adjust=False).mean()
    macd_hist = macd_line - macd_signal
    return (
        float(macd_line.iloc[-1]) if not pd.isna(macd_line.iloc[-1]) else 0.0,
        float(macd_signal.iloc[-1]) if not pd.isna(macd_signal.iloc[-1]) else 0.0,
        float(macd_hist.iloc[-1]) if not pd.isna(macd_hist.iloc[-1]) else 0.0,
    )


def compute_atr(df: pd.DataFrame, period: int = 14) -> float:
    """Compute Average True Range."""
    high = df["high"]
    low = df["low"]
    close = df["close"]
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return float(atr.iloc[-1]) if not pd.isna(atr.iloc[-1]) else 0.0


def get_trend(sma_20: float, sma_50: float, rsi: float) -> str:
    """Determine trend from SMAs and RSI."""
    if sma_20 > sma_50 and rsi < 70:
        return "bullish"
    if sma_20 < sma_50 and rsi > 30:
        return "bearish"
    return "neutral"


def scan_symbol(symbol: str, strategy_type: Optional[str] = None) -> Optional[StockIndicators]:
    """Compute indicators for a single symbol."""
    # Align scanner timeframe with SMA strategy settings so prices/SMA context match.
    settings = _get_sma_settings(strategy_type)
    bars = fetch_historical_bars(
        symbol,
        duration=settings["duration"],
        bar_size=settings["bar_size"],
    )
    if not bars:
        return StockIndicators(
            symbol=symbol,
            price=0,
            sma_20=0,
            sma_50=0,
            rsi_14=50,
            macd_line=0,
            macd_signal=0,
            macd_histogram=0,
            volume=0,
            volume_sma_20=0,
            atr_14=0,
            trend="neutral",
            error="Failed to fetch data",
        )

    df = bars_to_dataframe(bars)
    if df is None or len(df) < 50:
        return StockIndicators(
            symbol=symbol,
            price=0,
            sma_20=0,
            sma_50=0,
            rsi_14=50,
            macd_line=0,
            macd_signal=0,
            macd_histogram=0,
            volume=0,
            volume_sma_20=0,
            atr_14=0,
            trend="neutral",
            error="Insufficient data",
        )

    close = df["close"]
    latest = df.iloc[-1]
    price = float(latest["close"])
    volume = int(latest["volume"]) if "volume" in df.columns else 0

    sma_20 = float(close.rolling(20).mean().iloc[-1]) if len(df) >= 20 else price
    sma_50 = float(close.rolling(50).mean().iloc[-1]) if len(df) >= 50 else price
    rsi = compute_rsi(close, 14)
    macd_line, macd_signal, macd_hist = compute_macd(close)
    atr = compute_atr(df, 14)
    vol_sma_20 = (
        float(df["volume"].rolling(20).mean().iloc[-1])
        if "volume" in df.columns and len(df) >= 20
        else volume
    )

    trend = get_trend(sma_20, sma_50, rsi)

    return StockIndicators(
        symbol=symbol,
        price=price,
        sma_20=sma_20,
        sma_50=sma_50,
        rsi_14=rsi,
        macd_line=macd_line,
        macd_signal=macd_signal,
        macd_histogram=macd_hist,
        volume=volume,
        volume_sma_20=vol_sma_20,
        atr_14=atr,
        trend=trend,
    )


def run_scanner(symbols: Optional[Iterable[str]] = None, strategy_type: Optional[str] = None) -> MarketSnapshot:
    """
    Run market scanner on the given symbols (or default from config).
    Returns a MarketSnapshot with indicators for each stock.
    """
    base_symbols = list(symbols) if symbols is not None else list(config.SCAN_SYMBOLS)
    all_symbols = list(dict.fromkeys(base_symbols + config.MARKET_INDICATORS))
    snapshot = MarketSnapshot(timestamp=datetime.now())

    if not connect():
        snapshot.errors.append("Failed to connect to IBKR")
        return snapshot

    try:
        for symbol in all_symbols:
            try:
                indicators = scan_symbol(symbol, strategy_type=strategy_type)
                if indicators:
                    snapshot.stocks.append(indicators)
                    if indicators.error:
                        snapshot.errors.append(f"{symbol}: {indicators.error}")
            except Exception as e:
                logger.warning(f"Scanner error for {symbol}: {e}")
                snapshot.errors.append(f"{symbol}: {str(e)}")

        # Market summary (SPY/QQQ/VIX if available)
        spy = next((s for s in snapshot.stocks if s.symbol == "SPY"), None)
        qqq = next((s for s in snapshot.stocks if s.symbol == "QQQ"), None)
        if spy:
            snapshot.market_summary["SPY_price"] = spy.price
            snapshot.market_summary["SPY_trend"] = spy.trend
        if qqq:
            snapshot.market_summary["QQQ_price"] = qqq.price
            snapshot.market_summary["QQQ_trend"] = qqq.trend
    finally:
        disconnect()

    return snapshot
