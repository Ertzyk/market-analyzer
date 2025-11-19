def test_alerts_are_logged(client):
    # tworzenie alertu
    response = client.post("/api/alerts",
        json={"symbol": "AAPL", "condition": "above", "threshold_price": 150}
    )
    assert response.status_code == 200

    logs = client.get("/api/logs").json()
    assert any("Utworzono alert" in log["message"] for log in logs)
