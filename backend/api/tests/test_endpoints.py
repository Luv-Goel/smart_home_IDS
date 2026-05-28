def test_get_alerts(client):
    response = client.get("/api/alerts/")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "total" in data

def test_get_devices(client):
    response = client.get("/api/devices/")
    assert response.status_code == 200

def test_get_flows(client):
    response = client.get("/api/flows/")
    assert response.status_code == 200

def test_get_metrics(client):
    response = client.get("/api/metrics/")
    assert response.status_code == 200

def test_create_threshold(client):
    response = client.post("/api/thresholds/", json={
        "name": "high_cpu",
        "value": 90.0,
        "description": "High CPU usage",
        "is_active": True
    })
    assert response.status_code == 201
    assert response.json()["name"] == "high_cpu"
