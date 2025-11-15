from datetime import date, timedelta, datetime
from typing import List, Dict, Optional

from sqlalchemy.orm import Session

import models
from simple_yahoo_api import get_history

from datetime import datetime

from sqlalchemy.orm import Session
import yfinance as yf

from models import Alert
from fastapi import HTTPException


class MarketDataService:
    """
    Serwis odpowiedzialny za:
    - pobieranie danych z Yahoo
    - zapis/odczyt z bazy
    - zwracanie danych dla API (UC1, UC2)
    """

    def __init__(self, db: Session):
        self.db = db

    def get_or_create_instrument(self, symbol: str) -> models.Instrument:
        instrument = (
            self.db.query(models.Instrument)
            .filter(models.Instrument.symbol == symbol)
            .first()
        )
        if instrument is None:
            instrument = models.Instrument(symbol=symbol)
            self.db.add(instrument)
            self.db.commit()
            self.db.refresh(instrument)
        return instrument

    def fetch_and_store_history(
        self,
        symbol: str,
        start: date,
        end: date,
        interval: str = "1d",
    ) -> List[models.HistoricalQuote]:
        instrument = self.get_or_create_instrument(symbol)

        raw_data = get_history(symbol, start=start, end=end, interval=interval)

        quotes: List[models.HistoricalQuote] = []
        for item in raw_data:
            existing = (
                self.db.query(models.HistoricalQuote)
                .filter(
                    models.HistoricalQuote.instrument_id == instrument.id,
                    models.HistoricalQuote.date == item["date"],
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
                quote = models.HistoricalQuote(
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
    ) -> List[models.HistoricalQuote]:
        instrument = (
            self.db.query(models.Instrument)
            .filter(models.Instrument.symbol == symbol)
            .first()
        )
        if instrument is None:
            return []

        query = self.db.query(models.HistoricalQuote).filter(
            models.HistoricalQuote.instrument_id == instrument.id
        )

        if start:
            query = query.filter(models.HistoricalQuote.date >= start)
        if end:
            query = query.filter(models.HistoricalQuote.date <= end)

        return query.order_by(models.HistoricalQuote.date.asc()).all()

    def refresh_recent_history(
        self,
        symbol: str,
        days: int = 5,
        interval: str = "1d",
    ) -> List[models.HistoricalQuote]:
        today = date.today()
        start = today - timedelta(days=days)
        return self.fetch_and_store_history(symbol=symbol, start=start, end=today, interval=interval)

    def get_latest_quote(self, symbol: str) -> Optional[models.HistoricalQuote]:
        quotes = self.get_history_from_db(symbol=symbol)
        if not quotes:
            return None
        return quotes[-1]


class ExportService:
    """
    Serwis do eksportu danych (UC3).
    Na start: eksport historycznych notowań do CSV.
    """

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
            writer.writerow(
                [
                    q.date.isoformat(),
                    q.open if q.open is not None else "",
                    q.high if q.high is not None else "",
                    q.low if q.low is not None else "",
                    q.close,
                    q.volume if q.volume is not None else "",
                ]
            )

        return output.getvalue()


class PortfolioService:
    """
    Serwis do obsługi portfela użytkownika (UC4).
    Dla uproszczenia zakładamy jednego demo-usera i jeden domyślny portfel.
    """

    DEMO_EMAIL = "demo@example.com"

    def __init__(self, db: Session):
        self.db = db

    # --- User / Portfolio helpers ---

    def get_or_create_demo_user(self) -> models.User:
        user = (
            self.db.query(models.User)
            .filter(models.User.email == self.DEMO_EMAIL)
            .first()
        )
        if user is None:
            user = models.User(
                email=self.DEMO_EMAIL,
                display_name="Demo User",
                base_currency_code="USD",
            )
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
        return user

    def get_or_create_default_portfolio(self) -> models.Portfolio:
        user = self.get_or_create_demo_user()
        portfolio = (
            self.db.query(models.Portfolio)
            .filter(
                models.Portfolio.user_id == user.id,
                models.Portfolio.name == "Domyślny portfel",
            )
            .first()
        )
        if portfolio is None:
            portfolio = models.Portfolio(
                user_id=user.id,
                name="Domyślny portfel",
                base_currency_code=user.base_currency_code,
            )
            self.db.add(portfolio)
            self.db.commit()
            self.db.refresh(portfolio)
        return portfolio

    # --- Positions ---

    def add_or_update_position(
        self,
        portfolio_id: int,
        symbol: str,
        quantity: float,
        avg_open_price: float,
    ) -> models.Position:
        market = MarketDataService(self.db)
        instrument = market.get_or_create_instrument(symbol)

        position = (
            self.db.query(models.Position)
            .filter(
                models.Position.portfolio_id == portfolio_id,
                models.Position.instrument_id == instrument.id,
            )
            .first()
        )

        if position is None:
            position = models.Position(
                portfolio_id=portfolio_id,
                instrument_id=instrument.id,
                quantity=quantity,
                avg_open_price=avg_open_price,
                opened_at=datetime.utcnow(),
            )
            self.db.add(position)
        else:
            # proste przeliczenie średniej ceny przy dokładaniu pozycji
            total_old = position.avg_open_price * position.quantity
            total_new = avg_open_price * quantity
            new_qty = position.quantity + quantity
            if new_qty == 0:
                position.quantity = 0
            else:
                position.quantity = new_qty
                position.avg_open_price = (total_old + total_new) / new_qty

        self.db.commit()
        self.db.refresh(position)
        return position

    def get_portfolio_summary(self, portfolio_id: int) -> Dict:
        portfolio = (
            self.db.query(models.Portfolio)
            .filter(models.Portfolio.id == portfolio_id)
            .first()
        )
        if portfolio is None:
            raise ValueError("Portfolio not found")

        positions = (
            self.db.query(models.Position)
            .filter(models.Position.portfolio_id == portfolio_id)
            .all()
        )

        market = MarketDataService(self.db)

        items = []
        total_value = 0.0

        for pos in positions:
            instrument = pos.instrument

            # bierzemy ostatnią cenę z bazy (jeśli jest)
            quotes = market.get_history_from_db(instrument.symbol)
            last = quotes[-1] if quotes else None
            current_price = last.close if last else pos.avg_open_price

            position_value = current_price * pos.quantity
            total_value += position_value

            items.append(
                {
                    "instrument": instrument.symbol,
                    "quantity": pos.quantity,
                    "avg_open_price": pos.avg_open_price,
                    "current_price": current_price,
                    "position_value": position_value,
                }
            )

        return {
            "portfolio_id": portfolio.id,
            "name": portfolio.name,
            "base_currency": portfolio.base_currency_code,
            "positions": items,
            "total_value": total_value,
        }
    
class AlertService:
    """
    Serwis do zarządzania alertami cenowymi (UC4).
    """
    def __init__(self, db: Session):
        self.db = db

    # --- CRUD ---

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

    # --- Monitoring warunków ---

    def _fetch_current_price(self, symbol: str) -> float | None:
        """
        Proste pobranie bieżącej ceny z yfinance.
        Nie zapisuje do bazy – tylko na potrzeby alertów.
        """
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="1d", interval="1m")
        if hist.empty:
            return None
        last_row = hist.iloc[-1]
        return float(last_row["Close"])

    def check_alerts(self) -> list[Alert]:
        """
        Sprawdza wszystkie aktywne alerty.
        Zwraca listę tych, które właśnie się wyzwoliły.
        """
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
                # np. błąd API albo brak danych – pomijamy
                continue

            condition_met = (
                (alert.condition == "above" and price >= alert.threshold_price)
                or
                (alert.condition == "below" and price <= alert.threshold_price)
            )

            if condition_met:
                alert.last_triggered_at = now
                triggered.append(alert)

        if triggered:
            self.db.commit()

        return triggered