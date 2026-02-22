"""
Algo Trading Bot - Main Entry Point

Usage:
  python main.py scan          - Run market scanner once
  python main.py strategy      - Run SMA crossover strategy once
  python main.py report        - Generate and send report immediately
  python main.py scheduler     - Start scheduler (8am/8pm reports)
  python main.py               - Default: run scheduler
"""

import logging
import sys
from pathlib import Path

import config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(config.LOG_DIR / "bot.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


def main():
    cmd = sys.argv[1].lower() if len(sys.argv) > 1 else "scheduler"

    if cmd == "scan":
        from market_scanner import run_scanner

        snapshot = run_scanner()
        for s in snapshot.stocks:
            print(f"{s.symbol}: ${s.price:.2f} | RSI: {s.rsi_14:.1f} | Trend: {s.trend}")

    elif cmd == "strategy":
        from sma_strategy import run_strategy

        results = run_strategy()
        for r in results:
            print(f"{r.symbol}: {r.signal.value} | {r.message}")

    elif cmd == "report":
        from scheduler import run_report_now

        run_report_now("manual")
        print("Report generated and sent.")

    elif cmd == "scheduler":
        from scheduler import start_scheduler

        start_scheduler()

    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
