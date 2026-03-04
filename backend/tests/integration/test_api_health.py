"""
Testy API endpointów health (/, /test, /health, /test-activity-logs).
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def api_headers():
    return {
        "X-API-Key": "test-api-key-32-characters-long-12345",
        "Content-Type": "application/json",
    }


@pytest.mark.api
@pytest.mark.integration
class TestHealthEndpoints:
    def test_root_public(self, client):
        r = client.get("/")
        assert r.status_code == 200
        data = r.json()
        assert "name" in data
        assert "status" in data

    def test_test_endpoint_public(self, client):
        r = client.get("/test")
        assert r.status_code == 200
        assert r.json().get("status") == "ok"

    def test_health_public(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert "status" in data
        assert "database" in data
        assert "telegram" in data

    def test_test_activity_logs_requires_key(self, client):
        r = client.get("/test-activity-logs")
        assert r.status_code == 403

    def test_test_activity_logs_with_key(self, client, api_headers):
        r = client.get("/test-activity-logs", headers=api_headers)
        assert r.status_code == 200
        assert r.json().get("status") == "ok"
