"""
Testy API endpointów /chart-data i /macro-data.
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
class TestChartDataEndpoints:
    def test_chart_data_without_key(self, client):
        r = client.get("/chart-data?symbol=EUR/USD&timeframe=1h")
        assert r.status_code == 403

    def test_chart_data_invalid_timeframe(self, client, api_headers):
        r = client.get(
            "/chart-data?symbol=EUR/USD&timeframe=invalid&period=1mo",
            headers=api_headers,
        )
        assert r.status_code == 400

    def test_macro_data_without_key(self, client):
        r = client.get("/macro-data")
        assert r.status_code == 403

    def test_macro_data_with_key(self, client, api_headers):
        r = client.get("/macro-data", headers=api_headers)
        assert r.status_code in (200, 500)
