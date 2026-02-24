"""
Scheduler for 8am and 8pm report generation and delivery.
Uses APScheduler with a persistent job store.
"""

import logging
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

import config
from report_generator import generate_report, save_report
from notifier import send_report, send_telegram_report_to_user
from telegram_users import all_users, get_user

logger = logging.getLogger(__name__)

_scheduler: BlockingScheduler | None = None


def _run_scheduled_report():
    """Generate report and send via configured channels."""
    now = datetime.now()
    hour = now.hour
    session = "pre-market" if hour < 12 else "post-market"
    logger.info(f"Running scheduled {session} report at {now}")

    try:
        # For the global report, if an owner chat is configured and has custom symbols,
        # use those for the scan universe; strategy uses TRADE_SYMBOLS unless the owner
        # explicitly set symbols.
        scan_symbols = None
        strategy_symbols = None
        if config.OWNER_TELEGRAM_CHAT_ID:
            try:
                owner_chat_id = int(config.OWNER_TELEGRAM_CHAT_ID)
                owner = get_user(owner_chat_id)
                if owner:
                    scan_symbols = owner.effective_symbols()
                    strategy_symbols = owner.effective_strategy_symbols()
            except ValueError:
                scan_symbols = None
                strategy_symbols = None

        report = generate_report(
            session,
            symbols=scan_symbols,
            include_strategy=True,
            strategy_symbols=strategy_symbols,
        )
        save_report(report)
        send_report(report, session)
    except Exception as e:
        logger.exception(f"Report generation failed: {e}")


def _run_user_reports():
    """Generate and send reports for subscribed Telegram users based on their times."""
    now = datetime.now()
    current_time = now.strftime("%H:%M")
    minute_of_day = now.hour * 60 + now.minute
    hour = now.hour
    session = "pre-market" if hour < 12 else "post-market"

    users = all_users()
    if not users:
        return

    for user in users:
        if not user.subscribed:
            continue

        should_run = False
        # 1) Frequency-based trigger if configured
        if getattr(user, "frequency_minutes", None):
            freq = user.frequency_minutes or 0
            if freq > 0 and minute_of_day % freq == 0:
                should_run = True

        # 2) Fallback / additional: explicit times
        if current_time in user.effective_times():
            should_run = True

        if not should_run:
            continue
        try:
            logger.info(f"Running {session} report for chat_id={user.chat_id} at {current_time}")

            is_owner = (
                bool(config.OWNER_TELEGRAM_CHAT_ID)
                and str(user.chat_id) == config.OWNER_TELEGRAM_CHAT_ID
            )

            if is_owner:
                # Owner gets both scanner and strategy based on their selected symbols.
                report = generate_report(
                    session,
                    symbols=user.effective_symbols(),
                    include_strategy=True,
                    strategy_symbols=user.effective_strategy_symbols(),
                )
            else:
                # Other users get only the scanner section; no strategy details or trades.
                report = generate_report(
                    session,
                    symbols=user.effective_symbols(),
                    include_strategy=False,
                )
            save_report(report)
            send_telegram_report_to_user(report, session, chat_id=str(user.chat_id))
        except Exception as e:
            logger.exception(f"User report failed for chat_id={user.chat_id}: {e}")


def _parse_time(time_str: str) -> tuple[int, int]:
    """Parse 'HH:MM' to (hour, minute)."""
    parts = time_str.split(":")
    return int(parts[0]), int(parts[1]) if len(parts) > 1 else 0


def start_scheduler():
    """Start the scheduler for reports."""
    global _scheduler
    _scheduler = BlockingScheduler()

    # Legacy global schedule based on REPORT_TIMES (uses default config recipients)
    for time_str in config.REPORT_TIMES:
        hour, minute = _parse_time(time_str)
        _scheduler.add_job(
            _run_scheduled_report,
            trigger=CronTrigger(hour=hour, minute=minute),
            id=f"report_global_{time_str.replace(':', '')}",
            name=f"Global report at {time_str}",
        )
        logger.info(f"Scheduled global report at {time_str}")

    # Per-user Telegram schedules: check every minute and match user-defined times
    _scheduler.add_job(
        _run_user_reports,
        trigger=CronTrigger(minute="*"),
        id="user_reports_minutely",
        name="User-specific Telegram reports",
    )
    logger.info("Scheduled user-specific Telegram reports (every minute dispatcher)")

    logger.info("Scheduler started. Press Ctrl+C to exit.")
    _scheduler.start()


def run_report_now(session: str = "manual"):
    """Run report immediately (useful for testing)."""
    # Treat manual run as an owner-style report if OWNER_TELEGRAM_CHAT_ID is configured
    scan_symbols = None
    strategy_symbols = None
    if config.OWNER_TELEGRAM_CHAT_ID:
        try:
            owner_chat_id = int(config.OWNER_TELEGRAM_CHAT_ID)
            owner = get_user(owner_chat_id)
            if owner:
                scan_symbols = owner.effective_symbols()
                strategy_symbols = owner.effective_strategy_symbols()
        except ValueError:
            scan_symbols = None
            strategy_symbols = None

    report = generate_report(
        session,
        symbols=scan_symbols,
        include_strategy=True,
        strategy_symbols=strategy_symbols,
    )
    path = save_report(report)
    send_report(report, session)
    return path
