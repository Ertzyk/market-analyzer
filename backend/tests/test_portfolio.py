def test_portfolio_flow(client):
    # 1. Dodaj pozycję
    response = client.post(
        "/api/portfolio/positions",
        json={
            "symbol": "AAPL",
            "quantity": 5,
            "avg_open_price": 150
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["portfolio_id"] > 0
    assert len(data["positions"]) > 0

    # 2. Pobierz portfel
    response = client.get("/api/portfolio")
    assert response.status_code == 200
