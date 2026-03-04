"""
Testy API endpointów /strategies.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from app.main import app
from app.api.dependencies import get_database, get_telegram_service


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def api_headers():
    return {
        "X-API-Key": "test-api-key-32-characters-long-12345",
        "Content-Type": "application/json",
    }


@pytest.fixture
def override_deps(test_db):
    mock_telegram = MagicMock()
    mock_telegram.check_connection = MagicMock(return_value=True)
    app.dependency_overrides[get_database] = lambda: test_db
    app.dependency_overrides[get_telegram_service] = lambda: mock_telegram
    yield
    app.dependency_overrides.clear()


@pytest.mark.api
@pytest.mark.integration
class TestStrategiesEndpoints:
    def test_get_strategies_without_key(self, client):
        r = client.get("/strategies")
        assert r.status_code == 403

    def test_get_strategies_with_key(self, client, api_headers, override_deps):
        r = client.get("/strategies", headers=api_headers)
        assert r.status_code == 200
        data = r.json()
        assert "strategies" in data
        assert isinstance(data["strategies"], list)

    def test_post_create_strategy(self, client, api_headers, override_deps):
        r = client.post(
            "/strategies",
            headers=api_headers,
            json={
                "name": "Test RSI",
                "strategy_type": "RSI",
                "parameters": {"period": 14, "overbought": 70, "oversold": 30},
                "symbol": "EUR/USD",
                "timeframe": "1h",
            },
        )
        assert r.status_code in (200, 201)
        data = r.json()
        assert "id" in data or "strategy" in data

    def test_get_strategy_by_id(self, client, api_headers, override_deps, test_db):
        sid = test_db.create_strategy({
            "name": "GetById",
            "strategy_type": "RSI",
            "parameters": {},
            "symbol": "X",
        })
        r = client.get(f"/strategies/{sid}", headers=api_headers)
        assert r.status_code == 200, r.json()
        assert r.json().get("strategy", {}).get("name") == "GetById"

    def test_get_strategy_not_found(self, client, api_headers, override_deps):
        r = client.get("/strategies/99999", headers=api_headers)
        assert r.status_code == 404

    def test_delete_strategy(self, client, api_headers, override_deps, test_db):
        sid = test_db.create_strategy({
            "name": "ToDel",
            "strategy_type": "RSI",
            "parameters": {},
            "symbol": "X",
        })
        r = client.delete(f"/strategies/{sid}", headers=api_headers)
        assert r.status_code == 200, r.json()
        assert test_db.get_strategy(sid) is None
