def test_export_csv(client):
    response = client.get(
        "/api/export/csv",
        params={
            "symbol": "AAPL",
            "start": "2023-01-01",
            "end": "2023-01-10"
        }
    )

    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
