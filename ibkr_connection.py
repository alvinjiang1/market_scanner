"""
IBKR (Interactive Brokers) connection module using ib_async.
Handles connection, historical data fetching, and order placement.
"""

import logging
from typing import Optional

from ib_async import IB, Stock, util, BarData

import config

logger = logging.getLogger(__name__)

_ib_instance: Optional[IB] = None


def get_connection() -> IB:
    """Get or create IBKR connection."""
    global _ib_instance
    if _ib_instance is None:
        _ib_instance = IB()
    return _ib_instance


def connect() -> bool:
    """Connect to TWS or IB Gateway."""
    ib = get_connection()
    try:
        if not ib.isConnected():
            ib.connect(
                config.IBKR_HOST,
                config.IBKR_PORT,
                clientId=config.IBKR_CLIENT_ID,
            )
            ib.reqMarketDataType(config.IBKR_MARKET_DATA_TYPE)
            logger.info("Connected to IBKR")
        return True
    except Exception as e:
        logger.error(f"Failed to connect to IBKR: {e}")
        return False


def disconnect():
    """Disconnect from IBKR."""
    global _ib_instance
    if _ib_instance and _ib_instance.isConnected():
        _ib_instance.disconnect()
        logger.info("Disconnected from IBKR")
    _ib_instance = None


def get_stock_contract(symbol: str) -> Stock:
    """Create a Stock contract for US equities."""
    return Stock(symbol, "SMART", "USD")


def fetch_historical_bars(
    symbol: str,
    duration: str = "1 M",
    bar_size: str = "1 day",
    use_rth: bool = True,
) -> Optional[list[BarData]]:
    """
    Fetch historical bars for a symbol.
    
    Args:
        symbol: Stock symbol (e.g., AAPL)
        duration: Duration string (e.g., '1 D', '1 W', '1 M', '1 Y')
        bar_size: Bar size (e.g., '1 min', '5 mins', '1 hour', '1 day')
        use_rth: Regular trading hours only
    
    Returns:
        List of BarData or None on failure
    """
    ib = get_connection()
    if not ib.isConnected():
        if not connect():
            return None

    try:
        contract = get_stock_contract(symbol)
        bars = ib.reqHistoricalData(
            contract,
            endDateTime="",
            durationStr=duration,
            barSizeSetting=bar_size,
            whatToShow="TRADES",
            useRTH=use_rth,
        )
        return bars
    except Exception as e:
        logger.error(f"Failed to fetch bars for {symbol}: {e}")
        return None


def bars_to_dataframe(bars: list[BarData]):
    """Convert BarData list to pandas DataFrame."""
    if not bars:
        return None
    return util.df(bars)


def place_market_order(symbol: str, action: str, quantity: int):
    """
    Place a market order.
    
    Args:
        symbol: Stock symbol
        action: 'BUY' or 'SELL'
        quantity: Number of shares
    
    Returns:
        Trade object or None on failure
    """
    from ib_async import MarketOrder

    ib = get_connection()
    if not ib.isConnected():
        if not connect():
            return None

    if config.PAPER_TRADING:
        logger.info(f"[PAPER] Would place {action} {quantity} {symbol}")
        return None

    try:
        contract = get_stock_contract(symbol)
        order = MarketOrder(action, quantity)
        trade = ib.placeOrder(contract, order)
        logger.info(f"Order placed: {action} {quantity} {symbol}")
        return trade
    except Exception as e:
        logger.error(f"Failed to place order: {e}")
        return None


def get_positions():
    """Get current positions."""
    ib = get_connection()
    if not ib.isConnected():
        connect()
    return ib.positions() if ib.isConnected() else []


def get_account_summary():
    """Get account summary."""
    ib = get_connection()
    if not ib.isConnected():
        connect()
    if not ib.isConnected():
        return []
    accounts = ib.managedAccounts()
    if not accounts:
        return []
    return ib.accountSummary(accounts[0])
