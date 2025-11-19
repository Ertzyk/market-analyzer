def test_history_invalid_dates(client):
    response = client.get(
        "/api/history",
        params={"symbol": "AAPL", "start": "2025-12-31", "end": "2025-01-01"}
    )
    assert response.status_code == 422  # FastAPI validation