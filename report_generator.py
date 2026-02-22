"""
Report generator for market analysis and strategy results.
Creates formatted reports for 8am (pre-market) and 8pm (post-market).
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import config
from market_scanner import run_scanner, MarketSnapshot
from sma_strategy import run_strategy, StrategyResult, Signal

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
        lines.append(f"{r.symbol}: {sig_emoji} | Price: ${r.price:.2f} | Pos: {r.current_position}")
        lines.append(f"   {r.message}")
    return "\n".join(lines)


def generate_report(session: str = "pre-market") -> str:
    """
    Generate full report: market scan + strategy evaluation.
    session: "pre-market" (8am) or "post-market" (8pm)
    """
    lines = [
        f"═══════════════════════════════════",
        f"  ALGO TRADING BOT - {session.upper()} REPORT",
        f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"═══════════════════════════════════",
        "",
    ]

    # Market scan
    snapshot = run_scanner()
    lines.append(format_market_report(snapshot, session))
    lines.append("")
    lines.append("")

    # SMA strategy (optional - run during trading hours only for post-market, or both)
    try:
        results = run_strategy()
        lines.append(format_strategy_report(results))
    except Exception as e:
        logger.warning(f"Strategy report failed: {e}")
        lines.append("(Strategy evaluation skipped due to connection/error)")

    return "\n".join(lines)


def save_report(content: str) -> Path:
    """Save report to file and return path."""
    fname = f"report_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
    path = config.REPORTS_DIR / fname
    path.write_text(content, encoding="utf-8")
    logger.info(f"Report saved to {path}")
    return path
