def test_instrument_creation(client):
    from tests.conftest import TestingSessionLocal
    from models import Instrument

    db = TestingSessionLocal()

    inst = Instrument(symbol="TSLA", name="Tesla")
    db.add(inst)
    db.commit()

    saved = db.query(Instrument).filter_by(symbol="TSLA").first()
    assert saved is not None
    assert saved.name == "Tesla"
