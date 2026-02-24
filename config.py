"""
Configuration for the Algo Trading Bot.
Edit this file to set your IBKR credentials, watchlist, and notification preferences.
"""

import os
from pathlib import Path

# Load .env if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ============== IBKR Connection ==============
IBKR_HOST = os.getenv("IBKR_HOST", "127.0.0.1")
IBKR_PORT = int(os.getenv("IBKR_PORT", "7497"))  # 7497 for TWS, 4001 for IB Gateway
IBKR_CLIENT_ID = int(os.getenv("IBKR_CLIENT_ID", "1"))

# Use delayed data if you don't have real-time subscriptions (1=live, 3=delayed)
IBKR_MARKET_DATA_TYPE = int(os.getenv("IBKR_MARKET_DATA_TYPE", "3"))

# ============== SMA Crossover Strategy ==============
# Symbols to trade (edit with your target securities)
TRADE_SYMBOLS = ["SPY", "QQQ", "AAPL", "MSFT"]

# SMA periods: buy when fast crosses above slow, sell when fast crosses below slow
SMA_FAST_PERIOD = int(os.getenv("SMA_FAST_PERIOD", "10"))
SMA_SLOW_PERIOD = int(os.getenv("SMA_SLOW_PERIOD", "50"))

# Position sizing (shares per trade)
SHARES_PER_TRADE = int(os.getenv("SHARES_PER_TRADE", "10"))

# Number of past reports to show in the owner's SMA section
PORTFOLIO_HISTORY_LENGTH = int(os.getenv("PORTFOLIO_HISTORY_LENGTH", "10"))

# Paper trading mode - set to False for real orders
PAPER_TRADING = os.getenv("PAPER_TRADING", "true").lower() == "true"

# ============== Market Scanner ==============
# Stocks to scan (can overlap with TRADE_SYMBOLS)
SCAN_SYMBOLS = [
    "SPY", "QQQ", "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "MU"
]

# Market-wide indicators (SPY/QQQ work as stocks; VIX requires Index contract)
MARKET_INDICATORS = ["SPY", "QQQ"]

# Scan interval in minutes (how often to refresh scanner data)
SCAN_INTERVAL_MINUTES = int(os.getenv("SCAN_INTERVAL_MINUTES", "15"))

# ============== Report Schedule ==============
# Times for daily reports (24h format, local timezone)
REPORT_TIMES = ["08:00", "20:00"]  # 8am and 8pm

# ============== Notifications ==============
# Choose one or more: "telegram", "email", "whatsapp"
NOTIFICATION_METHODS = ["telegram"]  # Easiest to set up

# Telegram (create bot via @BotFather, get chat_id from @userinfobot)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Telegram chat ID that owns the IBKR account.
# Strategy trades and strategy sections in reports are only for this chat.
OWNER_TELEGRAM_CHAT_ID = os.getenv("OWNER_TELEGRAM_CHAT_ID", TELEGRAM_CHAT_ID)

# Email (SMTP)
EMAIL_SMTP_HOST = os.getenv("EMAIL_SMTP_HOST", "smtp.gmail.com")
EMAIL_SMTP_PORT = int(os.getenv("EMAIL_SMTP_PORT", "587"))
EMAIL_FROM = os.getenv("EMAIL_FROM", "")
EMAIL_TO = os.getenv("EMAIL_TO", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")  # Use app-specific password for Gmail

# WhatsApp (via Twilio - requires Twilio account)
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
TWILIO_WHATSAPP_TO = os.getenv("TWILIO_WHATSAPP_TO", "")  # e.g. whatsapp:+1234567890

# ============== Paths ==============
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"
LOG_DIR = PROJECT_ROOT / "logs"
REPORTS_DIR = PROJECT_ROOT / "reports"

# Create directories if needed
for d in [DATA_DIR, LOG_DIR, REPORTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)
