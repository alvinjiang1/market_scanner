from typing import Iterable, Tuple


def _infer_from_suffix(symbols: Iterable[str]) -> Tuple[str, str]:
    """
    Very simple heuristic to guess market + timezone from symbol suffixes.
    Defaults to US if nothing matches.
    """
    syms = [s.upper() for s in symbols if s]
    if not syms:
        return "US", "America/New_York"

    # Hong Kong (e.g. 0700.HK)
    if any(s.endswith(".HK") for s in syms):
        return "Hong Kong", "Asia/Hong_Kong"

    # London (e.g. VOD.L)
    if any(s.endswith(".L") for s in syms):
        return "UK", "Europe/London"

    # Tokyo (e.g. 7203.T)
    if any(s.endswith(".T") for s in syms):
        return "Japan", "Asia/Tokyo"

    # Fallback: US markets (NYSE/NASDAQ)
    return "US", "America/New_York"


def infer_market(symbols: Iterable[str]) -> Tuple[str, str]:
    """
    Infer (market_name, timezone_name) from the user's symbol universe.

    Assumes all symbols belong to the same market; falls back to US/Eastern.
    """
    return _infer_from_suffix(symbols)

