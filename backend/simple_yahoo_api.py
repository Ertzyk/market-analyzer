import yfinance as yf
from datetime import datetime

def get_today_data(symbol="AAPL"):
    # Pobieranie danych z dzisiaj
    stock = yf.Ticker(symbol)
    hist = stock.history(period="1d")
    
    if hist.empty:
        print("Brak danych dla dzisiaj")
        return
    
    # Ostatni wiersz czyli dane z dzisiaj
    today = hist.iloc[-1]
    
    print("=" * 50)
    print(f"DANE AKCJI: {symbol}")
    print("=" * 50)
    print(f"Data: {datetime.now().strftime('%Y-%m-%d')}")
    print(f"Otwarcie: ${today['Open']:.2f}")
    print(f"Zamknicie: ${today['Close']:.2f}")
    print(f"Zmiana: ${today['Close'] - today['Open']:.2f}")
    print(f"Min: ${today['Low']:.2f}")
    print(f"Max: ${today['High']:.2f}")
    print(f"Wolumen: {int(today['Volume']):,}")
    print("=" * 50)

if __name__ == "__main__":
    get_today_data("AAPL")  # Wybieramy symbol spółki

def get_history(symbol="AAPL", period="1y", interval="1d"):
    stock = yf.Ticker(symbol)
    hist = stock.history(period=period, interval=interval)
    if hist.empty:
        return []
    hist = hist.reset_index()
    out = []
    for _, row in hist.iterrows():
        out.append({
            "date": row["Date"].strftime("%Y-%m-%d"),
            "open": float(row["Open"]),
            "high": float(row["High"]),
            "low":  float(row["Low"]),
            "close": float(row["Close"]),
            "volume": int(row["Volume"]),
        })
    return out