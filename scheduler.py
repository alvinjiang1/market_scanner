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
from notifier import send_report

logger = logging.getLogger(__name__)

_scheduler: BlockingScheduler | None = None


def _run_scheduled_report():
    """Generate report and send via configured channels."""
    now = datetime.now()
    hour = now.hour
    session = "pre-market" if hour < 12 else "post-market"
    logger.info(f"Running scheduled {session} report at {now}")

    try:
        report = generate_report(session)
        save_report(report)
        send_report(report, session)
    except Exception as e:
        logger.exception(f"Report generation failed: {e}")


def _parse_time(time_str: str) -> tuple[int, int]:
    """Parse 'HH:MM' to (hour, minute)."""
    parts = time_str.split(":")
    return int(parts[0]), int(parts[1]) if len(parts) > 1 else 0


def start_scheduler():
    """Start the scheduler for 8am and 8pm reports."""
    global _scheduler
    _scheduler = BlockingScheduler()

    for time_str in config.REPORT_TIMES:
        hour, minute = _parse_time(time_str)
        _scheduler.add_job(
            _run_scheduled_report,
            trigger=CronTrigger(hour=hour, minute=minute),
            id=f"report_{time_str.replace(':', '')}",
            name=f"Report at {time_str}",
        )
        logger.info(f"Scheduled report at {time_str}")

    logger.info("Scheduler started. Press Ctrl+C to exit.")
    _scheduler.start()


def run_report_now(session: str = "manual"):
    """Run report immediately (useful for testing)."""
    report = generate_report(session)
    path = save_report(report)
    send_report(report, session)
    return path
