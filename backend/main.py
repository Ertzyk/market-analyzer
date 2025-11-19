from datetime import date, datetime
from typing import List, Dict, Optional, Literal
import csv
import io
import statistics

from fastapi import FastAPI, Depends, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import delete
from sqlalchemy.orm import Session

from db import Base, engine, get_db
import models
from models import LogEntry
from services import (
    MarketDataService,
    ExportService,
    PortfolioService,
    AlertService,
    LogService,
)

from apscheduler.schedulers.background import BackgroundScheduler
from cache import clear_cache

from db import SessionLocal

# Utworzenie tabel w bazie
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Market Analysis Backend")

# CORS (frontend na innym porcie)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

scheduler = BackgroundScheduler()

# ========================
# DTO / modele Pydantic
# ========================

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


class CurrentQuoteResponse(BaseModel):
    symbol: str
    quote: QuoteDTO


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


class AlertCreate(BaseModel):
    symbol: str
    condition: str
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


class LogEntryDTO(BaseModel):
    id: int
    timestamp: datetime
    level: str
    source: Optional[str] = None
    message: str
    user_email: Optional[str] = None

    class Config:
        orm_mode = True


# ========================
# UC2 – Historia notowań
# ========================

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
    if not symbol or symbol.strip() == "":
        raise HTTPException(422, detail="Symbol cannot be empty")
    if start > end:
        raise HTTPException(422, detail="Start date cannot be after end date")
    service = MarketDataService(db)
    service.fetch_and_store_history(symbol=symbol, start=start, end=end)
    quotes = service.get_history_from_db(symbol=symbol, start=start, end=end)

    # LOG
    LogService(db).add_log(
        message=f"Pobrano historię {symbol} od {start} do {end}",
        level="INFO",
        source="UC2_HISTORY",
    )

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


# ========================
# UC1 – Bieżące dane
# ========================

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
    service.refresh_recent_history(symbol=symbol, days=5)

    latest = service.get_latest_quote(symbol=symbol)
    if latest is None:
        raise HTTPException(status_code=404, detail="Brak danych dla podanego symbolu")

    # LOG
    LogService(db).add_log(
        message=f"Pobrano bieżące dane dla {symbol}",
        level="INFO",
        source="UC1_CURRENT",
    )

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


# ========================
# UC3 – Eksport historii do CSV
# ========================

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

    # LOG
    LogService(db).add_log(
        message=f"Eksport CSV dla {symbol} od {start} do {end} (plik {filename})",
        level="INFO",
        source="UC3_EXPORT",
    )

    return StreamingResponse(
        io.StringIO(csv_data),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )


# ========================
# UC3 – Portfel (demo)
# ========================

@app.post("/api/portfolio/positions", response_model=PortfolioSummaryResponse)
def add_position(
    payload: PositionCreateRequest,
    db: Session = Depends(get_db),
):
    """
    Dodanie/aktualizacja pozycji w portfelu demo.
    """

    if payload.quantity <= 0:
        raise HTTPException(400, detail="Quantity must be positive")

    service = PortfolioService(db)
    portfolio = service.get_or_create_default_portfolio()
    service.add_or_update_position(
        portfolio_id=portfolio.id,
        symbol=payload.symbol,
        quantity=payload.quantity,
        avg_open_price=payload.avg_open_price,
    )
    summary = service.get_portfolio_summary(portfolio.id)

    # LOG
    LogService(db).add_log(
        message=(
            f"Dodano/zaktualizowano pozycję w portfelu: "
            f"{payload.symbol.upper()}, ilość={payload.quantity}, cena={payload.avg_open_price}"
        ),
        level="INFO",
        source="UC3_PORTFOLIO_SAVE",
    )

    return PortfolioSummaryResponse(
        portfolio_id=summary["portfolio_id"],
        name=summary["name"],
        base_currency=summary["base_currency"],
        positions=[PositionSummaryDTO(**pos) for pos in summary["positions"]],
        total_value=summary["total_value"],
    )


@app.get("/api/portfolio", response_model=PortfolioSummaryResponse)
def get_portfolio(
    db: Session = Depends(get_db),
):
    """
    Podsumowanie portfela demo.
    """
    service = PortfolioService(db)
    portfolio = service.get_or_create_default_portfolio()
    summary = service.get_portfolio_summary(portfolio.id)

    # LOG
    LogService(db).add_log(
        message="Wyświetlono podsumowanie portfela demo",
        level="INFO",
        source="UC3_PORTFOLIO_VIEW",
    )

    return PortfolioSummaryResponse(
        portfolio_id=summary["portfolio_id"],
        name=summary["name"],
        base_currency=summary["base_currency"],
        positions=[PositionSummaryDTO(**pos) for pos in summary["positions"]],
        total_value=summary["total_value"],
    )


# ========================
# UC4 – Porównanie instrumentów
# ========================

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
    Porównanie kilku instrumentów w zadanym okresie + metryki.
    """
    service = MarketDataService(db)

    symbols_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    if len(symbols_list) < 2:
        raise HTTPException(
            status_code=400,
            detail="Podaj co najmniej dwa symbole, np. AAPL,MSFT",
        )

    series: Dict[str, List[ComparisonPointDTO]] = {}
    metrics: List[InstrumentMetricsDTO] = []

    for sym in symbols_list:
        quotes = service.fetch_and_store_history(symbol=sym, start=start, end=end)
        if not quotes:
            raise HTTPException(
                status_code=404,
                detail=f"Brak danych dla symbolu {sym} w podanym zakresie",
            )

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

    # LOG
    LogService(db).add_log(
        message=f"Porównanie instrumentów: {', '.join(symbols_list)} od {start} do {end}",
        level="INFO",
        source="UC4_COMPARE",
    )

    return ComparisonResponse(symbols=symbols_list, series=series, metrics=metrics)


# ========================
# UC6 – Przeglądanie logów
# ========================

@app.get("/api/logs", response_model=List[LogEntryDTO])
def get_logs(
    level: Optional[str] = Query(
        None, description="Poziom logu: INFO / WARNING / ERROR"
    ),
    source: Optional[str] = Query(
        None, description="Źródło / moduł, np. UC1, UC4, PORTFOLIO"
    ),
    date_from: Optional[datetime] = Query(
        None, description="Początek zakresu (ISO 8601, np. 2024-01-01T00:00:00)"
    ),
    date_to: Optional[datetime] = Query(
        None, description="Koniec zakresu (ISO 8601)"
    ),
    db: Session = Depends(get_db),
):
    """
    UC6 – Panel logów: pobranie listy logów z filtrami.
    """
    service = LogService(db)
    logs = service.list_logs(
        level=level, source=source, date_from=date_from, date_to=date_to
    )
    return logs


@app.get("/api/logs/export")
def export_logs_csv(
    level: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
):
    """
    UC6 – eksport logów do pliku CSV.
    """
    service = LogService(db)
    logs = service.list_logs(
        level=level, source=source, date_from=date_from, date_to=date_to
    )

    def generate():
        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow(["id", "timestamp", "level", "source", "message", "user_email"])
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)

        for l in logs:
            writer.writerow(
                [
                    l.id,
                    l.timestamp.isoformat() if l.timestamp else "",
                    l.level,
                    l.source or "",
                    l.message,
                    l.user_email or "",
                ]
            )
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)

    return StreamingResponse(
        generate(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="logs.csv"'},
    )


@app.delete("/api/logs")
def clear_logs(db: Session = Depends(get_db)):
    """
    UC6 – Reset logów: usuń wszystkie wpisy z tabeli logs.
    """
    total = db.query(LogEntry).count()
    db.execute(delete(LogEntry))
    db.commit()
    return {"status": "OK", "deleted": total}


# ========================
# UC4 – Alerty cenowe
# ========================

@app.get("/api/alerts", response_model=List[AlertResponse])
def list_alerts(db: Session = Depends(get_db)):
    """
    Zwraca listę wszystkich alertów zapisanych w systemie.
    """
    service = AlertService(db)
    alerts = service.list_alerts()

    LogService(db).add_log(
        message=f"Pobrano listę alertów (liczba={len(alerts)})",
        level="INFO",
        source="UC4_ALERTS",
    )

    return alerts


@app.post("/api/alerts", response_model=AlertResponse)
def create_alert(payload: AlertCreate, db: Session = Depends(get_db)):
    """
    Dodanie nowego alertu.
    """
    service = AlertService(db)
    try:
        alert = service.create_alert(
            symbol=payload.symbol,
            condition=payload.condition,
            threshold_price=payload.threshold_price,
        )

        LogService(db).add_log(
            message=(
                f"Utworzono alert: {alert.symbol} {alert.condition} "
                f"{alert.threshold_price}"
            ),
            level="INFO",
            source="UC4_ALERTS",
        )

        return alert
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/alerts/{alert_id}/toggle", response_model=AlertResponse)
def toggle_alert(alert_id: int, db: Session = Depends(get_db)):
    """
    Włączenie / wyłączenie monitorowania alertu.
    """
    service = AlertService(db)
    alert = service.toggle_alert(alert_id)

    status_txt = "aktywowany" if alert.active else "dezaktywowany"
    LogService(db).add_log(
        message=f"Zmieniono status alertu id={alert_id} ({status_txt})",
        level="INFO",
        source="UC4_ALERTS",
    )

    return alert


@app.delete("/api/alerts/{alert_id}", status_code=204)
def delete_alert(alert_id: int, db: Session = Depends(get_db)):
    """
    Usunięcie alertu.
    """
    service = AlertService(db)
    service.delete_alert(alert_id)

    LogService(db).add_log(
        message=f"Usunięto alert id={alert_id}",
        level="WARNING",
        source="UC4_ALERTS",
    )

    return


@app.post("/api/alerts/check", response_model=AlertCheckResponse)
def check_alerts(db: Session = Depends(get_db)):
    """
    Sprawdzenie alertów (monitoring w tle).
    """
    service = AlertService(db)
    triggered = service.check_alerts()

    LogService(db).add_log(
        message=f"Sprawdzono alerty (wyzwolone: {len(triggered)})",
        level="INFO",
        source="UC4_ALERTS_CHECK",
    )

    return {"triggered": triggered}

@app.on_event("startup")
def start_scheduler():
    scheduler.add_job(clear_cache, "interval", minutes=15)
    scheduler.start()
    print("APScheduler started")

@app.on_event("shutdown")
def stop_scheduler():
    scheduler.shutdown()
    print("APScheduler stopped")

def fetch_daily_popular():
    for symbol in ["AAPL", "MSFT", "GOOGL"]:
        service = MarketDataService(next(get_db()))
        service.fetch_and_store_history(symbol=symbol)

def backup_db():
    shutil.copy("market.db", "market_backup.db")

def check_alerts():
    db = SessionLocal()
    try:
        service = MarketDataService(db)
        service.check_alerts()
    finally:
        db.close()

scheduler.add_job(fetch_daily_popular, "cron", hour=2)  # codziennie o 02:00
scheduler.add_job(check_alerts, "interval", minutes=1)
scheduler.add_job(backup_db, "cron", hour=0)  # codziennie o północy