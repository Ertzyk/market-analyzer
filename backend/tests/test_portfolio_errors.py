def test_add_position_invalid_payload(client):
    # negative quantity
    response = client.post(
        "/api/portfolio/positions",
        json={"symbol": "AAPL", "quantity": -3, "avg_open_price": 100}
    )
    # backend may return 422 due to Pydantic validation
    assert response.status_code in (400, 422)