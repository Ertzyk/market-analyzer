from tests.conftest import TestingSessionLocal
from models import Currency, Instrument, Position
from services import PortfolioService

def test_portfolio_value_calculation_with_fx():
    db = TestingSessionLocal()

    usd = Currency(code="USD", name="US Dollar")
    db.add(usd)
    db.commit()

    inst = Instrument(symbol="MSFT", name="Microsoft")
    db.add(inst)
    db.commit()

    service = PortfolioService(db)
    portfolio = service.get_or_create_default_portfolio()

    pos = Position(
        portfolio_id=portfolio.id,
        instrument_id=inst.id,
        quantity=5,
        avg_open_price=10,
    )
    db.add(pos)
    db.commit()

    summary = service.get_portfolio_summary(portfolio.id)

    assert summary["total_value"] == 50  # 5 * 10
