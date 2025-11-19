def test_create_list_delete_alert(client):

    # Create
    response = client.post(
        "/api/alerts",
        json={"symbol": "AAPL", "condition": "above", "threshold_price": 150}
    )
    assert response.status_code == 200
    alert = response.json()
    assert alert["symbol"] == "AAPL"

    # List
    response = client.get("/api/alerts")
    assert response.status_code == 200
    assert len(response.json()) >= 1

    # Delete
    response = client.delete(f"/api/alerts/{alert['id']}")
    assert response.status_code == 204
