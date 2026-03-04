"""
Testy API endpointów /signals (check-signals, signals/recent, signals/strategy/{id}).
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
class TestSignalsEndpoints:
    def test_get_recent_signals_without_key(self, client):
        r = client.get("/signals/recent")
        assert r.status_code == 403

    def test_get_recent_signals_with_key(self, client, api_headers, test_db):
        with patch("app.api.dependencies.get_database", return_value=test_db):
            r = client.get("/signals/recent?limit=10", headers=api_headers)
        assert r.status_code == 200
        data = r.json()
        assert "signals" in data

    def test_get_signals_by_strategy(self, client, api_headers, test_db):
        sid = test_db.create_strategy({
            "name": "S",
            "strategy_type": "RSI",
            "parameters": {},
            "symbol": "X",
        })
        with patch("app.api.dependencies.get_database", return_value=test_db):
            r = client.get(f"/signals/strategy/{sid}?limit=10", headers=api_headers)
        assert r.status_code == 200
        assert "signals" in r.json()

    def test_check_signals_with_key(self, client, api_headers, test_db):
        with patch("app.api.dependencies.get_database", return_value=test_db):
            r = client.post("/check-signals", headers=api_headers)
        assert r.status_code == 200
        assert "results" in r.json()
