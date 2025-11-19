from services import PortfolioService
from sqlalchemy.orm import Session
from models import Position, Instrument

def test_portfolio_average_price_calculation():
    from tests.conftest import TestingSessionLocal
    db: Session = TestingSessionLocal()

    service = PortfolioService(db)

    # Portfolio musi powstać przed pozycjami
    portfolio = service.get_or_create_default_portfolio()

    # Tworzymy instrument, który NIE istnieje w demo-portfolio
    instrument = Instrument(symbol="TEST123", name="Test Inc.")
    db.add(instrument)
    db.commit()
    db.refresh(instrument)

    # Pierwszy zakup
    service.add_or_update_position(
        portfolio_id=portfolio.id,
        symbol="TEST123",
        quantity=10,
        avg_open_price=100,
    )

    # Drugi zakup
    service.add_or_update_position(
        portfolio_id=portfolio.id,
        symbol="TEST123",
        quantity=10,
        avg_open_price=200,
    )

    # Pobieramy pozycję
    pos = db.query(Position).filter_by(
        portfolio_id=portfolio.id,
        instrument_id=instrument.id
    ).first()

    assert pos is not None
    assert pos.quantity == 20
    assert pos.avg_open_price == 150
