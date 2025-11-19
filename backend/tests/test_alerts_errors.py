def test_create_alert_invalid_condition(client):
    response = client.post(
        "/api/alerts",
        json={"symbol": "AAPL", "condition": "WRONG", "threshold_price": 100}
    )
    assert response.status_code == 400


def test_create_alert_invalid_price(client):
    response = client.post(
        "/api/alerts",
        json={"symbol": "AAPL", "condition": "above", "threshold_price": -10}
    )
    assert response.status_code == 400