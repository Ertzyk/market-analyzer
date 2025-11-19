def test_history_empty_symbol(client):
    response = client.get("/api/history?symbol=&start=2024-01-01&end=2024-01-02")
    assert response.status_code == 422
