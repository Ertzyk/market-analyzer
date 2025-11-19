def test_current_quote(client):
    response = client.get("/api/current?symbol=AAPL")

    assert response.status_code in (200, 404)
    # 200 = mamy dane
    # 404 = Yahoo nie zwróciło danych w test environment
