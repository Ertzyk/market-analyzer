from datetime import date, datetime
from typing import List, Dict, Optional

import yfinance as yf


def get_history(
    symbol: str,
    period: str = "1y",
    interval: str = "1d",
    start: Optional[date] = None,
    end: Optional[date] = None,
) -> List[Dict]:
    """
    Wrapper na yfinance.Ticker.history:
    - jeśli podane start/end -> używa zakresu dat,
    - jeśli nie -> używa period (tak jak w starym prototypie).
    Dzięki temu działa zarówno stare wywołanie get_history(symbol, "1y", "1d"),
    jak i nowe: get_history(symbol, start=..., end=..., interval=...).
    """
    ticker = yf.Ticker(symbol)

    # Jeśli podano zakres dat, użyj go
    if start is not None or end is not None:
        # yfinance akceptuje stringi YYYY-MM-DD, więc konwertujemy jeśli trzeba
        if isinstance(start, (date, datetime)):
            start_str = start.isoformat()
        else:
            start_str = start

        if isinstance(end, (date, datetime)):
            end_str = end.isoformat()
        else:
            end_str = end

        df = ticker.history(start=start_str, end=end_str, interval=interval)
    else:
        # Wsteczne kompatybilne zachowanie – tylko period
        df = ticker.history(period=period, interval=interval)

    df = df.reset_index()

    results: List[Dict] = []
    for _, row in df.iterrows():
        dt = row["Date"]
        # pandas.Timestamp -> date
        if hasattr(dt, "date"):
            dt = dt.date()

        def _to_float_or_none(v):
            # NaN != NaN, więc tak łapiemy NaN bez importowania pandas
            if v is None or v != v:
                return None
            return float(v)

        results.append(
            {
                "date": dt,
                "open": _to_float_or_none(row["Open"]),
                "high": _to_float_or_none(row["High"]),
                "low": _to_float_or_none(row["Low"]),
                "close": float(row["Close"]),
                "volume": _to_float_or_none(row["Volume"]),
            }
        )

    return results