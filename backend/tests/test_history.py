def test_history_returns_data(client):
    response = client.get(
        "/api/history",
        params={
            "symbol": "AAPL",
            "start": "2023-01-01",
            "end": "2023-01-10",
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "AAPL"
    assert isinstance(data["quotes"], list)
