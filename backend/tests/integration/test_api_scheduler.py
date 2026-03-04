"""
Testy API endpointów /scheduler (config, status).
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
class TestSchedulerEndpoints:
    def test_get_config_without_key(self, client):
        r = client.get("/scheduler/config")
        assert r.status_code == 403

    def test_get_config_with_key(self, client, api_headers, test_db):
        with patch("app.api.dependencies.get_database", return_value=test_db):
            r = client.get("/scheduler/config", headers=api_headers)
        assert r.status_code == 200
        data = r.json()
        assert "success" in data
        assert "config" in data
        assert "status" in data

    def test_get_status_with_key(self, client, api_headers, test_db):
        with patch("app.api.dependencies.get_database", return_value=test_db):
            r = client.get("/scheduler/status", headers=api_headers)
        assert r.status_code == 200
