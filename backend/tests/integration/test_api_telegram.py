"""
Testy API endpointów /telegram.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock

from app.main import app
from app.api.dependencies import get_telegram_service, get_database


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
class TestTelegramEndpoints:
    def test_get_chat_id_public(self, client):
        r = client.get("/telegram/get-chat-id")
        assert r.status_code == 200
        data = r.json()
        assert "message" in data
        assert "steps" in data

    def test_test_message_without_key(self, client):
        r = client.post("/telegram/test-message")
        assert r.status_code == 403

    def test_test_message_with_key_mock(self, client, api_headers):
        mock_tg = MagicMock()
        mock_tg.send_signal = AsyncMock(return_value=True)
        app.dependency_overrides[get_telegram_service] = lambda: mock_tg
        try:
            r = client.post("/telegram/test-message", headers=api_headers)
            assert r.status_code == 200
            assert r.json().get("success") is True
        finally:
            app.dependency_overrides.pop(get_telegram_service, None)

    def test_get_settings_with_key(self, client, api_headers, test_db):
        app.dependency_overrides[get_database] = lambda: test_db
        try:
            r = client.get("/telegram/settings", headers=api_headers)
            assert r.status_code == 200
        finally:
            app.dependency_overrides.pop(get_database, None)
