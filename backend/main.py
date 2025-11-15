from datetime import date
from typing import List

from fastapi import FastAPI, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db import Base, engine, get_db
import models
from services import MarketDataService
from fastapi import HTTPException

from fastapi.responses import StreamingResponse

import io

from datetime import date
from typing import List, Optional

from services import MarketDataService, ExportService, PortfolioService

from typing import Dict
import statistics

from typing import Literal  # dopisz, jeśli nie ma

from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException

from services import MarketDataService, AlertService

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Market Analysis Backend")

# jeśli front stoi na innym porcie/domenie:
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # na devie ok, potem można zawęzić
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QuoteDTO(BaseModel):
    date: date
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float
    volume: float | None = None

class ComparisonPointDTO(BaseModel):
    date: date
    close: float
    normalized: float  # 100 = cena startowa


class InstrumentMetricsDTO(BaseModel):
    symbol: str
    return_pct: float          # zwrot w % w okresie
    volatility_pct: float      # odchylenie std dziennych zwrotów w %
    max_drawdown_pct: float    # maksymalny spadek od szczytu w %


class ComparisonResponse(BaseModel):
    symbols: List[str]
    series: Dict[str, List[ComparisonPointDTO]]
    metrics: List[InstrumentMetricsDTO]


class HistoryResponse(BaseModel):
    symbol: str
    quotes: List[QuoteDTO]

class AlertCreate(BaseModel):
    symbol: str
    condition: Literal["above", "below"]
    threshold_price: float


class AlertResponse(BaseModel):
    id: int
    symbol: str
    condition: str
    threshold_price: float
    active: bool
    created_at: datetime
    last_triggered_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class AlertCheckResponse(BaseModel):
    triggered: List[AlertResponse]


@app.get("/api/history", response_model=HistoryResponse)
def get_history(
    symbol: str = Query(..., description="Ticker, np. AAPL"),
    start: date = Query(..., description="Początek zakresu (YYYY-MM-DD)"),
    end: date = Query(..., description="Koniec zakresu (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
):
    """
    UC2: Analiza trendów historycznych.
    Pobiera dane z Yahoo, zapisuje do bazy, i zwraca zakres dat.
    """
    service = MarketDataService(db)
    # najpierw dociągamy / aktualizujemy dane
    service.fetch_and_store_history(symbol=symbol, start=start, end=end)

    quotes = service.get_history_from_db(symbol=symbol, start=start, end=end)

    return HistoryResponse(
        symbol=symbol,
        quotes=[
            QuoteDTO(
                date=q.date,
                open=q.open,
                high=q.high,
                low=q.low,
                close=q.close,
                volume=q.volume,
            )
            for q in quotes
        ],
    )

class CurrentQuoteResponse(BaseModel):
    symbol: str
    quote: QuoteDTO


@app.get("/api/current", response_model=CurrentQuoteResponse)
def get_current(
    symbol: str = Query(..., description="Ticker, np. AAPL"),
    db: Session = Depends(get_db),
):
    """
    UC1: Przegląd bieżących danych rynkowych.
    Dociąga ostatnie dni danych i zwraca najnowszą świecę.
    """
    service = MarketDataService(db)

    # dociągamy ostatnie kilka dni, żeby mieć świeże dane w bazie
    service.refresh_recent_history(symbol=symbol, days=5)

    latest = service.get_latest_quote(symbol=symbol)
    if latest is None:
        raise HTTPException(status_code=404, detail="Brak danych dla podanego symbolu")

    return CurrentQuoteResponse(
        symbol=symbol,
        quote=QuoteDTO(
            date=latest.date,
            open=latest.open,
            high=latest.high,
            low=latest.low,
            close=latest.close,
            volume=latest.volume,
        ),
    )

@app.get("/api/export/csv")
def export_history_csv(
    symbol: str = Query(..., description="Ticker, np. AAPL"),
    start: date = Query(..., description="Początek zakresu (YYYY-MM-DD)"),
    end: date = Query(..., description="Koniec zakresu (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
):
    """
    UC3: Eksport danych / raportu.
    Zwraca plik CSV z danymi historycznymi dla danego instrumentu.
    """
    export_service = ExportService(db)
    csv_data = export_service.export_history_to_csv(symbol=symbol, start=start, end=end)

    filename = f"{symbol}_{start.isoformat()}_{end.isoformat()}.csv"

    return StreamingResponse(
        io.StringIO(csv_data),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )

class PositionSummaryDTO(BaseModel):
    instrument: str
    quantity: float
    avg_open_price: float
    current_price: float
    position_value: float


class PortfolioSummaryResponse(BaseModel):
    portfolio_id: int
    name: str
    base_currency: str | None
    positions: List[PositionSummaryDTO]
    total_value: float


class PositionCreateRequest(BaseModel):
    symbol: str
    quantity: float
    avg_open_price: float


@app.post("/api/portfolio/positions", response_model=PortfolioSummaryResponse)
def add_position(
    payload: PositionCreateRequest,
    db: Session = Depends(get_db),
):
    """
    UC4: Dodanie/aktualizacja pozycji w portfelu.
    Dla uproszczenia operujemy na jednym domyślnym portfelu demo-usera.
    """
    service = PortfolioService(db)
    portfolio = service.get_or_create_default_portfolio()
    service.add_or_update_position(
        portfolio_id=portfolio.id,
        symbol=payload.symbol,
        quantity=payload.quantity,
        avg_open_price=payload.avg_open_price,
    )
    summary = service.get_portfolio_summary(portfolio.id)
    return PortfolioSummaryResponse(
        portfolio_id=summary["portfolio_id"],
        name=summary["name"],
        base_currency=summary["base_currency"],
        positions=[
            PositionSummaryDTO(**pos) for pos in summary["positions"]
        ],
        total_value=summary["total_value"],
    )


@app.get("/api/portfolio", response_model=PortfolioSummaryResponse)
def get_portfolio(
    db: Session = Depends(get_db),
):
    """
    UC4: Podsumowanie portfela użytkownika.
    """
    service = PortfolioService(db)
    portfolio = service.get_or_create_default_portfolio()
    summary = service.get_portfolio_summary(portfolio.id)
    return PortfolioSummaryResponse(
        portfolio_id=summary["portfolio_id"],
        name=summary["name"],
        base_currency=summary["base_currency"],
        positions=[
            PositionSummaryDTO(**pos) for pos in summary["positions"]
        ],
        total_value=summary["total_value"],
    )

@app.get("/api/compare", response_model=ComparisonResponse)
def compare_instruments(
    symbols: str = Query(
        ...,
        description="Lista symboli oddzielona przecinkami, np. AAPL,MSFT,TSLA",
    ),
    start: date = Query(..., description="Początek zakresu (YYYY-MM-DD)"),
    end: date = Query(..., description="Koniec zakresu (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
):
    """
    UC4 (interpretacja z prezentacji): porównanie kilku instrumentów
    w zadanym okresie + podstawowe metryki (zwrot, zmienność, max drawdown).
    """
    service = MarketDataService(db)

    # parsowanie listy symboli
    symbols_list = [
        s.strip().upper()
        for s in symbols.split(",")
        if s.strip()
    ]
    if len(symbols_list) < 2:
        raise HTTPException(status_code=400, detail="Podaj co najmniej dwa symbole, np. AAPL,MSFT")

    series: Dict[str, List[ComparisonPointDTO]] = {}
    metrics: List[InstrumentMetricsDTO] = []

    for sym in symbols_list:
        # pobranie i zapis historii w bazie
        quotes = service.fetch_and_store_history(symbol=sym, start=start, end=end)

        if not quotes:
            raise HTTPException(status_code=404, detail=f"Brak danych dla symbolu {sym} w podanym zakresie")

        closes = [q.close for q in quotes]
        base_price = closes[0] if closes[0] > 0 else 1.0

        points: List[ComparisonPointDTO] = []
        for q in quotes:
            normalized = (q.close / base_price) * 100.0
            points.append(
                ComparisonPointDTO(
                    date=q.date,
                    close=q.close,
                    normalized=normalized,
                )
            )
        series[sym] = points

        # metryki: zwrot, zmienność, max drawdown
        if len(closes) >= 2:
            total_return = (closes[-1] / closes[0] - 1.0) * 100.0

            daily_returns = [
                (closes[i] / closes[i - 1] - 1.0)
                for i in range(1, len(closes))
                if closes[i - 1] > 0
            ]
            if len(daily_returns) >= 2:
                volatility_pct = statistics.pstdev(daily_returns) * 100.0
            else:
                volatility_pct = 0.0

            peak = closes[0]
            max_drawdown_pct = 0.0
            for c in closes:
                if c > peak:
                    peak = c
                drawdown = (c / peak - 1.0) * 100.0
                if drawdown < max_drawdown_pct:
                    max_drawdown_pct = drawdown
        else:
            total_return = 0.0
            volatility_pct = 0.0
            max_drawdown_pct = 0.0

        metrics.append(
            InstrumentMetricsDTO(
                symbol=sym,
                return_pct=total_return,
                volatility_pct=volatility_pct,
                max_drawdown_pct=max_drawdown_pct,
            )
        )

    return ComparisonResponse(
        symbols=symbols_list,
        series=series,
        metrics=metrics,
    )

# ========================
# UC4 – Zarządzanie alertami cenowymi
# ========================

@app.get("/api/alerts", response_model=List[AlertResponse])
def list_alerts(db: Session = Depends(get_db)):
    """
    Zwraca listę wszystkich alertów zapisanych w systemie.
    """
    service = AlertService(db)
    return service.list_alerts()


@app.post("/api/alerts", response_model=AlertResponse)
def create_alert(payload: AlertCreate, db: Session = Depends(get_db)):
    """
    Dodanie nowego alertu (scenariusz główny UC4).
    """
    service = AlertService(db)
    try:
        return service.create_alert(
            symbol=payload.symbol,
            condition=payload.condition,
            threshold_price=payload.threshold_price,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/alerts/{alert_id}/toggle", response_model=AlertResponse)
def toggle_alert(alert_id: int, db: Session = Depends(get_db)):
    """
    Włączenie / wyłączenie monitorowania alertu.
    """
    service = AlertService(db)
    return service.toggle_alert(alert_id)


@app.delete("/api/alerts/{alert_id}", status_code=204)
def delete_alert(alert_id: int, db: Session = Depends(get_db)):
    """
    Usunięcie alertu.
    """
    service = AlertService(db)
    service.delete_alert(alert_id)
    return


@app.post("/api/alerts/check", response_model=AlertCheckResponse)
def check_alerts(db: Session = Depends(get_db)):
    """
    Sprawdzenie alertów (scenariusz „Monitoring w tle”).

    Na razie to endpoint – później front może go wołać cyklicznie
    np. co 30–60 sekund i wyświetlać powiadomienia.
    """
    service = AlertService(db)
    triggered = service.check_alerts()
    return {"triggered": triggered}