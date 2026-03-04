"""
Testy API endpointów /statistics.
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
class TestStatisticsEndpoints:
    def test_get_statistics_without_key(self, client):
        r = client.get("/statistics")
        assert r.status_code == 403

    def test_get_statistics_with_key(self, client, api_headers, test_db):
        with patch("app.api.dependencies.get_database", return_value=test_db):
            r = client.get("/statistics", headers=api_headers)
        assert r.status_code == 200
