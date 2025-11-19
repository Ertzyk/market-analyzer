def test_logs_recording(client):

    # trigger some event (history)
    client.get(
        "/api/history",
        params={"symbol": "AAPL", "start": "2023-01-01", "end": "2023-01-02"}
    )

    # check logs
    response = client.get("/api/logs")
    assert response.status_code == 200
    logs = response.json()
    assert len(logs) >= 1
