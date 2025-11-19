from datetime import date, timedelta, datetime
from typing import List, Dict, Optional

from sqlalchemy.orm import Session
from fastapi import HTTPException
import yfinance as yf
from zoneinfo import ZoneInfo

# 🔥 WAŻNE – importujemy modele BEZ "import models"
from models import (
    Instrument,
    HistoricalQuote,
    Currency,
    User,
    Portfolio,
    Position,
    Alert,
    LogEntry,
)

# 🔥 Cache
from cache import cache_get, cache_set


class MarketDataService:
    """
    Serwis odpowiedzialny za:
    - pobieranie danych z Yahoo
    - zapis/odczyt z bazy
    - zwracanie danych dla API (UC1, UC2)
    """

    def __init__(self, db: Session):
        self.db = db

    # --- Instrument helper ---

    def get_or_create_instrument(self, symbol: str) -> Instrument:
        instrument = (
            self.db.query(Instrument)
            .filter(Instrument.symbol == symbol)
            .first()
        )
        if instrument is None:
            instrument = Instrument(symbol=symbol)
            self.db.add(instrument)
            self.db.commit()
            self.db.refresh(instrument)
        return instrument

    # --- Historia ---

    def fetch_and_store_history(
        self,
        symbol: str,
        start: date,
        end: date,
        interval: str = "1d",
    ) -> List[HistoricalQuote]:
        instrument = self.get_or_create_instrument(symbol)

        # pobranie z Yahoo
        import simple_yahoo_api
        raw_data = simple_yahoo_api.get_history(symbol, start=start, end=end, interval=interval)

        quotes: List[HistoricalQuote] = []
        for item in raw_data:
            existing = (
                self.db.query(HistoricalQuote)
                .filter(
                    HistoricalQuote.instrument_id == instrument.id,
                    HistoricalQuote.date == item["date"],
                )
                .first()
            )
            if existing:
                existing.open = item["open"]
                existing.high = item["high"]
                existing.low = item["low"]
                existing.close = item["close"]
                existing.volume = item["volume"]
                quotes.append(existing)
            else:
                quote = HistoricalQuote(
                    instrument_id=instrument.id,
                    date=item["date"],
                    open=item["open"],
                    high=item["high"],
                    low=item["low"],
                    close=item["close"],
                    volume=item["volume"],
                )
                self.db.add(quote)
                quotes.append(quote)

        self.db.commit()
        return quotes

    def get_history_from_db(
        self,
        symbol: str,
        start: Optional[date] = None,
        end: Optional[date] = None,
    ) -> List[HistoricalQuote]:

        # Cache READ
        cache_key = f"history:{symbol}:{start}:{end}"
        cached = cache_get(cache_key)
        if cached:
            return [
                HistoricalQuote(
                    date=item["date"],
                    open=item["open"],
                    high=item["high"],
                    low=item["low"],
                    close=item["close"],
                    volume=item["volume"],
                )
                for item in cached
            ]

        # DB
        instrument = (
            self.db.query(Instrument)
            .filter(Instrument.symbol == symbol)
            .first()
        )
        if instrument is None:
            return []

        query = self.db.query(HistoricalQuote).filter(
            HistoricalQuote.instrument_id == instrument.id
        )

        if start:
            query = query.filter(HistoricalQuote.date >= start)
        if end:
            query = query.filter(HistoricalQuote.date <= end)

        results = query.order_by(HistoricalQuote.date.asc()).all()

        # Cache WRITE
        cache_set(
            cache_key,
            [
                {
                    "date": str(q.date),
                    "open": q.open,
                    "high": q.high,
                    "low": q.low,
                    "close": q.close,
                    "volume": q.volume,
                }
                for q in results
            ],
            ttl_seconds=300
        )

        return results

    def refresh_recent_history(
        self,
        symbol: str,
        days: int = 5,
        interval: str = "1d",
    ) -> List[HistoricalQuote]:
        today = date.today()
        start = today - timedelta(days=days)
        return self.fetch_and_store_history(symbol=symbol, start=start, end=today, interval=interval)

    def get_latest_quote(self, symbol: str) -> Optional[HistoricalQuote]:

        # Cache READ
        cache_key = f"current:{symbol}"
        cached = cache_get(cache_key)
        if cached:
            return HistoricalQuote(
                date=cached["date"],
                open=cached["open"],
                high=cached["high"],
                low=cached["low"],
                close=cached["close"],
                volume=cached["volume"],
            )

        # DB
        quotes = self.get_history_from_db(symbol=symbol)
        if not quotes:
            return None

        last = quotes[-1]

        # Cache WRITE
        cache_set(
            cache_key,
            {
                "date": str(last.date),
                "open": last.open,
                "high": last.high,
                "low": last.low,
                "close": last.close,
                "volume": last.volume,
            },
            ttl_seconds=150
        )

        return last


# =========================
# EXPORT (UC3)
# =========================

class ExportService:
    def __init__(self, db: Session):
        self.db = db

    def export_history_to_csv(
        self,
        symbol: str,
        start: Optional[date] = None,
        end: Optional[date] = None,
    ) -> str:

        import csv
        import io

        market_service = MarketDataService(self.db)

        if start and end:
            market_service.fetch_and_store_history(symbol=symbol, start=start, end=end)

        quotes = market_service.get_history_from_db(symbol=symbol, start=start, end=end)

        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow(["date", "open", "high", "low", "close", "volume"])

        for q in quotes:
            date_value = q.date.isoformat() if hasattr(q.date, "isoformat") else str(q.date)
            writer.writerow(
                [
                    date_value,
                    q.open or "",
                    q.high or "",
                    q.low or "",
                    q.close,
                    q.volume or "",
                ]
            )

        return output.getvalue()


# =========================
# PORTFOLIO (UC3)
# =========================

class PortfolioService:
    DEMO_EMAIL = "demo@example.com"

    def __init__(self, db: Session):
        self.db = db

    def get_or_create_demo_user(self) -> User:
        user = (
            self.db.query(User)
            .filter(User.email == self.DEMO_EMAIL)
            .first()
        )
        if user:
            return user

        # Ensure currency exists
        currency = (
            self.db.query(Currency)
            .filter(Currency.code == "USD")
            .first()
        )
        if not currency:
            currency = Currency(code="USD", name="US Dollar")
            self.db.add(currency)

        user = User(
            email=self.DEMO_EMAIL,
            display_name="Demo User",
            base_currency_code="USD",
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def get_or_create_default_portfolio(self) -> Portfolio:
        user = self.get_or_create_demo_user()
        portfolio = (
            self.db.query(Portfolio)
            .filter(
                Portfolio.user_id == user.id,
                Portfolio.name == "Domyślny portfel",
            )
            .first()
        )
        if portfolio:
            return portfolio

        portfolio = Portfolio(
            user_id=user.id,
            name="Domyślny portfel",
            base_currency_code="USD",
        )
        self.db.add(portfolio)
        self.db.commit()
        self.db.refresh(portfolio)

        return portfolio

    def add_or_update_position(
        self,
        portfolio_id: int,
        symbol: str,
        quantity: float,
        avg_open_price: float,
    ) -> Position:

        market = MarketDataService(self.db)
        instrument = market.get_or_create_instrument(symbol)

        position = (
            self.db.query(Position)
            .filter(
                Position.portfolio_id == portfolio_id,
                Position.instrument_id == instrument.id,
            )
            .first()
        )

        if position is None:
            position = Position(
                portfolio_id=portfolio_id,
                instrument_id=instrument.id,
                quantity=quantity,
                avg_open_price=avg_open_price,
                opened_at=datetime.utcnow(),
            )
            self.db.add(position)
        else:
            total_old = position.avg_open_price * position.quantity
            total_new = avg_open_price * quantity
            new_qty = position.quantity + quantity

            if new_qty != 0:
                position.avg_open_price = (total_old + total_new) / new_qty
            position.quantity = new_qty

        self.db.commit()
        self.db.refresh(position)
        return position

    def get_portfolio_summary(self, portfolio_id: int) -> Dict:

        portfolio = self.db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
        if portfolio is None:
            raise ValueError("Portfolio not found")

        positions = (
            self.db.query(Position)
            .filter(Position.portfolio_id == portfolio_id)
            .all()
        )

        market = MarketDataService(self.db)

        items = []
        total_value = 0.0

        for pos in positions:
            instrument = pos.instrument
            quotes = market.get_history_from_db(instrument.symbol)
            last = quotes[-1] if quotes else None
            current_price = last.close if last else pos.avg_open_price

            value = current_price * pos.quantity
            total_value += value

            items.append(
                {
                    "instrument": instrument.symbol,
                    "quantity": pos.quantity,
                    "avg_open_price": pos.avg_open_price,
                    "current_price": current_price,
                    "position_value": value,
                }
            )

        return {
            "portfolio_id": portfolio.id,
            "name": portfolio.name,
            "base_currency": portfolio.base_currency_code,
            "positions": items,
            "total_value": total_value,
        }


# =========================
# ALERTS (UC4)
# =========================

class AlertService:
    def __init__(self, db: Session):
        self.db = db

    def list_alerts(self) -> list[Alert]:
        return (
            self.db.query(Alert)
            .order_by(Alert.symbol, Alert.threshold_price)
            .all()
        )

    def create_alert(self, symbol: str, condition: str, threshold_price: float) -> Alert:

        symbol = symbol.strip().upper()

        if condition not in ("above", "below"):
            raise ValueError("condition musi być 'above' lub 'below'.")

        if threshold_price <= 0:
            raise ValueError("threshold_price musi być > 0.")

        alert = Alert(
            symbol=symbol,
            condition=condition,
            threshold_price=threshold_price,
            active=True,
        )
        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)

        return alert

    def toggle_alert(self, alert_id: int) -> Alert:
        alert = self.db.get(Alert, alert_id)
        if not alert:
            raise HTTPException(status_code=404, detail="Alert nie istnieje.")

        alert.active = not alert.active

        self.db.commit()
        self.db.refresh(alert)

        return alert

    def delete_alert(self, alert_id: int) -> None:
        alert = self.db.get(Alert, alert_id)
        if not alert:
            raise HTTPException(status_code=404, detail="Alert nie istnieje.")

        self.db.delete(alert)
        self.db.commit()

    def _fetch_current_price(self, symbol: str) -> float | None:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="1d", interval="1m")
        if hist.empty:
            return None
        return float(hist.iloc[-1]["Close"])

    def check_alerts(self) -> list[Alert]:

        active_alerts = (
            self.db.query(Alert)
            .filter(Alert.active.is_(True))
            .all()
        )

        now = datetime.utcnow()
        triggered: list[Alert] = []

        for alert in active_alerts:
            price = self._fetch_current_price(alert.symbol)
            if price is None:
                continue

            condition_ok = (
                (alert.condition == "above" and price >= alert.threshold_price)
                or
                (alert.condition == "below" and price <= alert.threshold_price)
            )

            if condition_ok:
                alert.last_triggered_at = now
                triggered.append(alert)

        if triggered:
            self.db.commit()

        return triggered


# =========================
# LOGI (UC6)
# =========================

class LogService:
    def __init__(self, db):
        self.db = db

    def add_log(
        self,
        message: str,
        level: str = "INFO",
        source: Optional[str] = None,
        user_email: Optional[str] = None,
        details: Optional[str] = None,
    ) -> LogEntry:
        entry = LogEntry(
            timestamp=datetime.utcnow() + timedelta(hours=1),
            level=level,
            source=source,
            message=message,
            user_email=user_email,
            details=details,
        )
        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)
        return entry

    def list_logs(
        self,
        level: Optional[str] = None,
        source: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ):
        q = self.db.query(LogEntry).order_by(LogEntry.timestamp.desc())

        if level:
            q = q.filter(LogEntry.level == level)

        if source:
            q = q.filter(LogEntry.source == source)

        if date_from:
            q = q.filter(LogEntry.timestamp >= date_from)

        if date_to:
            q = q.filter(LogEntry.timestamp <= date_to)

        return q.all()