def test_log_filtering(client):
    # generate some logs
    for _ in range(3):
        client.get(
            "/api/history",
            params={"symbol": "AAPL", "start": "2024-01-01", "end": "2024-01-02"}
        )

    # filter by nonexistent level
    response = client.get("/api/logs?level=WRONG")
    assert response.status_code == 200
    assert response.json() == []  # no logs