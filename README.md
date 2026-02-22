# market_scanner

An algorithmic trading bot with SMA crossover strategy, market scanner, and automated reports. Connects to Interactive Brokers (IBKR) and sends daily reports via Telegram, Email, or WhatsApp.

## Features

- **SMA Crossover Strategy**: Buy when fast SMA crosses above slow SMA; sell on death cross
- **Market Scanner**: Computes RSI, MACD, ATR, SMAs for user-defined stocks
- **Scheduled Reports**: 8am (pre-market) and 8pm (post-market) reports
- **Notifications**: Telegram, Email, or WhatsApp delivery

## Prerequisites

1. **Python 3.10+**
2. **IBKR Account** with TWS or IB Gateway running
3. **API enabled** in TWS/Gateway (Configure → API → Settings)

## Quick Start

### 1. Install Dependencies

```bash
cd market_scanner
pip install -r requirements.txt
```

### 2. Configure

Edit `config.py` or set environment variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `TRADE_SYMBOLS` | Symbols for SMA strategy | `["SPY", "QQQ", "AAPL"]` |
| `SCAN_SYMBOLS` | Symbols for market scanner | Same or extended list |
| `TELEGRAM_BOT_TOKEN` | From @BotFather | `123456:ABC...` |
| `TELEGRAM_CHAT_ID` | Your chat ID | `123456789` |
| `PAPER_TRADING` | Safe mode (no real orders) | `true` |

**Telegram setup:**
1. Message [@BotFather](https://t.me/botfather) → `/newbot` → get token
2. Message your bot, then visit `https://api.telegram.org/bot<TOKEN>/getUpdates` to find your `chat_id`

### 3. Run

```bash
# Run market scanner once
python main.py scan

# Run SMA strategy once
python main.py strategy

# Generate and send report now
python main.py report

# Start scheduler (8am & 8pm reports)
python main.py scheduler
```

## Project Structure

```
market_scanner/
├── config.py           # Configuration (edit symbols, credentials)
├── ibkr_connection.py  # IBKR connection & data/orders
├── sma_strategy.py     # SMA crossover logic
├── market_scanner.py   # Technical indicators scanner
├── report_generator.py # Report formatting
├── notifier.py         # Telegram/Email/WhatsApp
├── scheduler.py        # 8am/8pm scheduling
├── main.py             # Entry point
├── data/               # Cached data (if any)
├── logs/               # Log files
└── reports/            # Saved reports
```

## IBKR Setup

1. Start **TWS** (port 7497) or **IB Gateway** (port 4001)
2. Enable API: Configure → API → Settings
3. Check "Download open orders on connection"
4. Add `127.0.0.1` to Trusted IPs

## Notification Methods

### Telegram (recommended)
- Create bot via @BotFather
- Set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`

### Email
- Set `EMAIL_FROM`, `EMAIL_TO`, `EMAIL_PASSWORD`
- For Gmail: use an [App Password](https://support.google.com/accounts/answer/185833)

### WhatsApp
- Requires [Twilio](https://www.twilio.com/) account
- Set `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_FROM`, `TWILIO_WHATSAPP_TO`

## Paper Trading

By default `PAPER_TRADING=true` — no real orders are placed. Set to `false` in config or env to enable live trading. **Use at your own risk.**

## Disclaimer

This bot is for educational purposes. Trading involves risk. Past performance does not guarantee future results. Always test with paper trading first.
