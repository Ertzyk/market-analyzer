from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from simple_yahoo_api import get_history

app = FastAPI(title="MarketView API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

@app.get("/api/fetch")
def fetch(symbol: str = "AAPL", period: str = "1y", interval: str = "1d"):
    """
    Zwraca {symbol, period, interval, points:[{date, open, high, low, close, volume}]}
    """
    data = get_history(symbol, period, interval)
    if not data:
        raise HTTPException(404, "Brak danych (symbol/okres) lub limit API")
    return {"symbol": symbol, "period": period, "interval": interval, "points": data}