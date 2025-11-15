from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Date,
    DateTime,
    Boolean,
    ForeignKey,   
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.orm import relationship

from db import Base


class Currency(Base):
    __tablename__ = "currencies"

    code = Column(String(3), primary_key=True)  # np. USD, PLN, EUR
    name = Column(String(100), nullable=True)
    symbol = Column(String(10), nullable=True)


class Instrument(Base):
    __tablename__ = "instruments"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=True)
    type = Column(String(50), nullable=True)  # STOCK, FOREX, itp.

    # waluta, w której podawana jest cena (np. USD dla AAPL, PLN dla KGHM)
    pricing_currency_code = Column(String(3), ForeignKey("currencies.code"), nullable=True)
    pricing_currency = relationship("Currency")

    quotes = relationship("HistoricalQuote", back_populates="instrument")


class HistoricalQuote(Base):
    __tablename__ = "historical_quotes"

    id = Column(Integer, primary_key=True, index=True)
    instrument_id = Column(Integer, ForeignKey("instruments.id"), nullable=False)
    date = Column(Date, index=True, nullable=False)
    open = Column(Float, nullable=True)
    high = Column(Float, nullable=True)
    low = Column(Float, nullable=True)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=True)

    instrument = relationship("Instrument", back_populates="quotes")

    __table_args__ = (
        UniqueConstraint("instrument_id", "date", name="uq_instrument_date"),
    )


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False)
    display_name = Column(String(255), nullable=True)
    base_currency_code = Column(String(3), ForeignKey("currencies.code"), nullable=True)

    base_currency = relationship("Currency")
    portfolios = relationship("Portfolio", back_populates="user")


class Portfolio(Base):
    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    base_currency_code = Column(String(3), ForeignKey("currencies.code"), nullable=True)

    user = relationship("User", back_populates="portfolios")
    base_currency = relationship("Currency")
    positions = relationship("Position", back_populates="portfolio")


class Position(Base):
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)
    instrument_id = Column(Integer, ForeignKey("instruments.id"), nullable=False)

    quantity = Column(Float, nullable=False)          # ile jednostek instrumentu
    avg_open_price = Column(Float, nullable=False)    # średnia cena zakupu (w walucie instrumentu)
    opened_at = Column(DateTime, nullable=True)

    portfolio = relationship("Portfolio", back_populates="positions")
    instrument = relationship("Instrument")

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, nullable=False, index=True)
    # "above" – powiadom gdy kurs >= próg
    # "below" – powiadom gdy kurs <= próg
    condition = Column(String, nullable=False)
    threshold_price = Column(Float, nullable=False)

    active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    last_triggered_at = Column(DateTime, nullable=True)