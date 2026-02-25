"""
Report generator for market analysis and strategy results.
Creates formatted reports for 8am (pre-market) and 8pm (post-market).
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Iterable
from zoneinfo import ZoneInfo

import config
from market_scanner import run_scanner, MarketSnapshot
from sma_strategy import run_strategy, StrategyResult, Signal, _get_sma_settings
from portfolio_history import record_snapshot, get_recent_history, format_positions
from markets import infer_market

logger = logging.getLogger(__name__)


def format_market_report(snapshot: MarketSnapshot, session: str) -> str:
    """Format market scanner snapshot into a readable report."""
    lines = [
        f"📊 MARKET REPORT - {session}",
        f"Generated: {snapshot.timestamp.strftime('%Y-%m-%d %H:%M')}",
        "",
        "=== MARKET INDICATORS ===",
    ]

    for stock in snapshot.stocks:
        # Skip symbols that failed to fetch or have errors; they will still appear in the
        # errors section below so the user understands what was skipped.
        if getattr(stock, "error", None):
            continue
        emoji = "🟢" if stock.trend == "bullish" else "🔴" if stock.trend == "bearish" else "⚪"
        lines.append(
            f"{emoji} {stock.symbol}: ${stock.price:.2f} | SMA20: ${stock.sma_20:.2f} | "
            f"SMA50: ${stock.sma_50:.2f} | RSI: {stock.rsi_14:.1f} | Trend: {stock.trend}"
        )
        lines.append(
            f"   MACD: {stock.macd_histogram:+.4f} | ATR: ${stock.atr_14:.2f} | Vol: {stock.volume:,}"
        )

    if snapshot.market_summary:
        lines.append("")
        lines.append("=== MARKET SUMMARY ===")
        for k, v in snapshot.market_summary.items():
            lines.append(f"  {k}: {v}")

    if snapshot.errors:
        lines.append("")
        lines.append("⚠️ Errors:")
        for e in snapshot.errors:
            lines.append(f"  - {e}")

    return "\n".join(lines)


def format_strategy_report(results: list[StrategyResult]) -> str:
    """Format SMA strategy results into a report."""
    if not results:
        return "No strategy results."

    lines = [
        "=== SMA CROSSOVER STRATEGY ===",
    ]
    for r in results:
        sig_emoji = "🟢 BUY" if r.signal == Signal.BUY else "🔴 SELL" if r.signal == Signal.SELL else "⚪ HOLD"
        lines.append(
            f"{r.symbol}: {sig_emoji} | Price: ${r.price:.2f} | "
            f"SMA_fast: ${r.fast_sma:.2f} | SMA_slow: ${r.slow_sma:.2f} | Pos: {r.current_position}"
        )
        lines.append(f"   {r.message}")
    return "\n".join(lines)


def build_strategy_section(
    strategy_symbols: Optional[Iterable[str]] = None,
    strategy_type: Optional[str] = None,
) -> str:
    """Build the SMA strategy section, handling errors gracefully."""
    lines: list[str] = []

    # 1) Record and show portfolio history
    try:
        latest_value = record_snapshot()
        history = get_recent_history()
        lines.append("=== PORTFOLIO VALUE HISTORY ===")
        if latest_value is None and not history:
            lines.append("Could not retrieve portfolio value.")
        else:
            for snap in history:
                lines.append(f"{snap.timestamp}: ${snap.total_value:,.2f}")
        lines.append("")
    except Exception as e:
        logger.warning(f"Portfolio history section failed: {e}")
        lines.append("=== PORTFOLIO VALUE HISTORY ===")
        lines.append("(Failed to load portfolio history)")
        lines.append("")

    # 2) Current positions
    try:
        lines.append("=== CURRENT POSITIONS ===")
        lines.append(format_positions())
        lines.append("")
    except Exception as e:
        logger.warning(f"Positions section failed: {e}")
        lines.append("=== CURRENT POSITIONS ===")
        lines.append("(Failed to load positions)")
        lines.append("")

    # 3) SMA strategy settings + results
    try:
        settings = _get_sma_settings(strategy_type)
        bar = settings["bar_size"]
        fast = settings["fast"]
        slow = settings["slow"]
        mode = (strategy_type or config.SMA_STRATEGY_TYPE or "position").lower()
        lines.append("=== SMA STRATEGY SETTINGS ===")
        lines.append(f"Mode: {mode}")
        lines.append(f"Timeframe: {bar}")
        lines.append(f"SMA fast/slow: {fast}/{slow}")
        lines.append("")
    except Exception as e:
        logger.warning(f"Strategy settings section failed: {e}")

    try:
        results = run_strategy(strategy_symbols, strategy_type=strategy_type)
        lines.append(format_strategy_report(results))
    except Exception as e:
        logger.warning(f"Strategy report failed: {e}")
        lines.append("=== SMA CROSSOVER STRATEGY ===")
        lines.append("(Strategy evaluation skipped due to connection/error)")

    return "\n".join(lines)


def generate_report(
    session: str = "pre-market",
    symbols: Optional[Iterable[str]] = None,
    include_strategy: bool = True,
    strategy_symbols: Optional[Iterable[str]] = None,
    strategy_type: Optional[str] = None,
) -> str:
    """
    Generate full report: market scan + (optionally) strategy evaluation.

    session: logical session label, e.g. "pre-market" / "post-market".
    The displayed title is adjusted based on the inferred market & timezone.
    """
    # Infer market + timezone from the symbols universe
    symbol_universe = list(symbols) if symbols is not None else list(config.SCAN_SYMBOLS)
    market_name, tz_name = infer_market(symbol_universe)
    now_market = datetime.now(ZoneInfo(tz_name))

    # Derive a phase label using the market local time if not explicitly given
    if session:
        phase_label = session.upper().replace("-", " ")
    else:
        phase_label = "PRE-MARKET" if now_market.hour < 12 else "POST-MARKET"

    title = f"{market_name} {phase_label} REPORT"

    lines = [
        f"═══════════════════════════════════",
        f"  ALGO TRADING BOT - {title}",
        f"  {now_market.strftime('%Y-%m-%d %H:%M')} ({tz_name})",
        f"═══════════════════════════════════",
        "",
    ]

    # Market scan
    snapshot = run_scanner(symbols=symbols, strategy_type=strategy_type)
    lines.append(format_market_report(snapshot, session))
    lines.append("")
    lines.append("")

    # SMA strategy (optional - run during trading hours only for post-market, or both)
    if include_strategy:
        lines.append(build_strategy_section(strategy_symbols, strategy_type=strategy_type))

    return "\n".join(lines)


def save_report(content: str) -> Path:
    """Save report to file and return path."""
    fname = f"report_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
    path = config.REPORTS_DIR / fname
    path.write_text(content, encoding="utf-8")
    logger.info(f"Report saved to {path}")
    return path
