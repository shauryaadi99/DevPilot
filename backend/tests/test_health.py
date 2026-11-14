"""Tests for backend health-check endpoints."""

def test_liveness_health_endpoint(client):
    """Test basic GET /health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("healthy", "degraded")
    assert "version" in data
    assert "timestamp" in data
    assert "components" in data


def test_api_v1_health_endpoint(client):
    """Test detailed GET /api/v1/health endpoint."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("healthy", "degraded")
    assert data["version"] == "0.1.0"
    assert "environment" in data
    assert "timestamp" in data

    components = data["components"]
    assert "database" in components
    assert components["database"]["status"] == "connected"
    assert components["database"]["engine"] in ("sqlite", "postgresql")

    assert "llm" in components
    assert components["llm"]["provider"] == "groq"
    assert "configured" in components["llm"]
    assert "model" in components["llm"]
