"""
Testy API endpointów /activity-logs.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

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
class TestActivityEndpoints:
    def test_get_activity_logs_without_key(self, client):
        r = client.get("/activity-logs")
        assert r.status_code == 403

    def test_get_activity_logs_with_key(self, client, api_headers, test_db):
        test_db.create_activity_log("test", "Test log", symbol="EUR/USD")
        with patch("app.api.dependencies.get_database", return_value=test_db):
            r = client.get("/activity-logs", headers=api_headers)
        assert r.status_code == 200
        data = r.json()
        assert "logs" in data
        assert "count" in data

    def test_get_new_activity_logs(self, client, api_headers, test_db):
        with patch("app.api.dependencies.get_database", return_value=test_db):
            r = client.get("/activity-logs/new?last_id=0&limit=10", headers=api_headers)
        assert r.status_code == 200
        data = r.json()
        assert "logs" in data
        assert "last_id" in data
