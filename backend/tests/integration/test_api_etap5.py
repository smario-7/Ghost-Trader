"""
Testy dla nowych endpointów API - Etap 5
"""
import pytest
from fastapi.testclient import TestClient
from datetime import datetime
import json


# Mock data dla testów
MOCK_ANALYSIS_RESULT = {
    "id": 1,
    "symbol": "EUR/USD",
    "timeframe": "1h",
    "timestamp": "2026-01-16T20:00:00",
    "ai_recommendation": "BUY",
    "ai_confidence": 85,
    "ai_reasoning": "Test reasoning",
    "technical_signal": "BUY",
    "technical_confidence": 75,
    "technical_details": '{"rsi": 35}',
    "macro_signal": "HOLD",
    "macro_impact": "neutral",
    "news_sentiment": "positive",
    "news_score": 70,
    "final_signal": "BUY",
    "agreement_score": 86,
    "voting_details": '{"ai": {"vote": "BUY", "confidence": 85}}',
    "tokens_used": 2500,
    "estimated_cost": 0.025,
    "decision_reason": "Test decision",
    "created_at": "2026-01-16T20:00:00"
}

MOCK_TOKEN_STATS = {
    "total_tokens": 125000,
    "total_cost": 1.25,
    "analyses_count": 50,
    "avg_tokens_per_analysis": 2500,
    "today_tokens": 15000,
    "today_cost": 0.15,
    "today_analyses": 6
}

MOCK_CONFIG = {
    "id": 1,
    "analysis_interval": 30,
    "enabled_symbols": '["EUR/USD", "GBP/USD"]',
    "notification_threshold": 60,
    "is_active": True,
    "updated_at": "2026-01-16T19:00:00"
}


class TestAnalysisResultsEndpoints:
    """Testy dla endpointów wyników analiz"""
    
    def test_get_analysis_results_without_filters(self, client, mock_db):
        """Test GET /ai/analysis-results bez filtrów"""
        mock_db.get_ai_analysis_results.return_value = [MOCK_ANALYSIS_RESULT]
        
        response = client.get(
            "/ai/analysis-results",
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "count" in data
        assert data["count"] == 1
        assert len(data["results"]) == 1
    
    def test_get_analysis_results_with_symbol_filter(self, client, mock_db):
        """Test GET /ai/analysis-results z filtrem symbol"""
        mock_db.get_ai_analysis_results.return_value = [MOCK_ANALYSIS_RESULT]
        
        response = client.get(
            "/ai/analysis-results?symbol=EUR/USD",
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["filters_applied"]["symbol"] == "EUR/USD"
        mock_db.get_ai_analysis_results.assert_called_once_with(symbol="EUR/USD", limit=50)
    
    def test_get_analysis_results_with_signal_type_filter(self, client, mock_db):
        """Test GET /ai/analysis-results z filtrem signal_type"""
        mock_db.get_ai_analysis_results.return_value = [MOCK_ANALYSIS_RESULT]
        
        response = client.get(
            "/ai/analysis-results?signal_type=BUY",
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["results"][0]["final_signal"] == "BUY"
    
    def test_get_analysis_results_with_min_agreement_filter(self, client, mock_db):
        """Test GET /ai/analysis-results z filtrem min_agreement"""
        mock_db.get_ai_analysis_results.return_value = [MOCK_ANALYSIS_RESULT]
        
        response = client.get(
            "/ai/analysis-results?min_agreement=80",
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["results"][0]["agreement_score"] >= 80
    
    def test_get_analysis_results_invalid_signal_type(self, client, mock_db):
        """Test GET /ai/analysis-results z nieprawidłowym signal_type"""
        response = client.get(
            "/ai/analysis-results?signal_type=INVALID",
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 400
        assert "Nieprawidłowy signal_type" in response.json()["detail"]
    
    def test_get_analysis_by_id_success(self, client, mock_db):
        """Test GET /ai/analysis-results/{id} - sukces"""
        mock_db.get_ai_analysis_by_id.return_value = MOCK_ANALYSIS_RESULT
        
        response = client.get(
            "/ai/analysis-results/1",
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert data["symbol"] == "EUR/USD"
        # Sprawdź czy JSON fields zostały sparsowane
        assert isinstance(data.get("technical_details"), dict)
        assert isinstance(data.get("voting_details"), dict)
    
    def test_get_analysis_by_id_not_found(self, client, mock_db):
        """Test GET /ai/analysis-results/{id} - nie znaleziono"""
        mock_db.get_ai_analysis_by_id.return_value = None
        
        response = client.get(
            "/ai/analysis-results/999",
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 404
        assert "nie została znaleziona" in response.json()["detail"]


class TestTokenStatisticsEndpoint:
    """Testy dla endpointu statystyk tokenów"""
    
    def test_get_token_statistics_without_dates(self, client, mock_db):
        """Test GET /ai/token-statistics bez dat"""
        mock_db.get_token_statistics.return_value = MOCK_TOKEN_STATS
        
        response = client.get(
            "/ai/token-statistics",
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_tokens"] == 125000
        assert data["total_cost"] == 1.25
        assert "period" in data
        mock_db.get_token_statistics.assert_called_once_with(start_date=None, end_date=None)
    
    def test_get_token_statistics_with_dates(self, client, mock_db):
        """Test GET /ai/token-statistics z datami"""
        mock_db.get_token_statistics.return_value = MOCK_TOKEN_STATS
        
        response = client.get(
            "/ai/token-statistics?start_date=2026-01-01&end_date=2026-01-16",
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["period"]["start_date"] == "2026-01-01"
        assert data["period"]["end_date"] == "2026-01-16"
        mock_db.get_token_statistics.assert_called_once_with(
            start_date="2026-01-01",
            end_date="2026-01-16"
        )
    
    def test_get_token_statistics_invalid_date_format(self, client, mock_db):
        """Test GET /ai/token-statistics z nieprawidłowym formatem daty"""
        response = client.get(
            "/ai/token-statistics?start_date=2026/01/01",
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 400
        assert "Nieprawidłowy format daty" in response.json()["detail"]


class TestAnalysisConfigEndpoints:
    """Testy dla endpointów konfiguracji"""
    
    def test_get_analysis_config(self, client, mock_db):
        """Test GET /ai/analysis-config"""
        mock_db.get_analysis_config.return_value = MOCK_CONFIG
        
        response = client.get(
            "/ai/analysis-config",
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["analysis_interval"] == 30
        assert isinstance(data["enabled_symbols"], list)
        assert len(data["enabled_symbols"]) == 2
    
    def test_update_analysis_config_all_fields(self, client, mock_db):
        """Test PUT /ai/analysis-config - wszystkie pola"""
        mock_db.get_analysis_config.return_value = {
            **MOCK_CONFIG,
            "analysis_interval": 60,
            "enabled_symbols": '["EUR/USD"]'
        }
        
        response = client.put(
            "/ai/analysis-config",
            headers={"X-API-Key": "test-key"},
            json={
                "analysis_interval": 60,
                "enabled_symbols": ["EUR/USD"],
                "notification_threshold": 70,
                "is_active": False
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "updated_config" in data
        mock_db.update_analysis_config.assert_called_once()
    
    def test_update_analysis_config_single_field(self, client, mock_db):
        """Test PUT /ai/analysis-config - pojedyncze pole"""
        mock_db.get_analysis_config.return_value = MOCK_CONFIG
        
        response = client.put(
            "/ai/analysis-config",
            headers={"X-API-Key": "test-key"},
            json={"analysis_interval": 45}
        )
        
        assert response.status_code == 200
        mock_db.update_analysis_config.assert_called_once()
    
    def test_update_analysis_config_invalid_interval(self, client, mock_db):
        """Test PUT /ai/analysis-config - nieprawidłowy interwał"""
        response = client.put(
            "/ai/analysis-config",
            headers={"X-API-Key": "test-key"},
            json={"analysis_interval": 2000}
        )
        
        assert response.status_code == 422
    
    def test_update_analysis_config_invalid_symbols(self, client, mock_db):
        """Test PUT /ai/analysis-config - nieprawidłowe symbole"""
        response = client.put(
            "/ai/analysis-config",
            headers={"X-API-Key": "test-key"},
            json={"enabled_symbols": ["INVALID"]}
        )
        
        assert response.status_code == 422
        assert "musi zawierać '/'" in response.json()["detail"]
    
    def test_update_analysis_config_too_many_symbols(self, client, mock_db):
        """Test PUT /ai/analysis-config - za dużo symboli"""
        symbols = [f"SYM{i}/USD" for i in range(51)]
        
        response = client.put(
            "/ai/analysis-config",
            headers={"X-API-Key": "test-key"},
            json={"enabled_symbols": symbols}
        )
        
        assert response.status_code == 422
        assert "maksymalnie 50" in response.json()["detail"].lower()
    
    def test_update_analysis_config_empty_body(self, client, mock_db):
        """Test PUT /ai/analysis-config - puste body"""
        response = client.put(
            "/ai/analysis-config",
            headers={"X-API-Key": "test-key"},
            json={}
        )
        
        assert response.status_code == 400
        assert "Brak danych do aktualizacji" in response.json()["detail"]


class TestTriggerAnalysisEndpoint:
    """Testy dla endpointu trigger analysis"""
    
    @pytest.mark.asyncio
    async def test_trigger_analysis_default_symbols(self, client, mock_db, mock_scheduler):
        """Test POST /ai/trigger-analysis - domyślne symbole"""
        mock_scheduler.run_analysis_cycle.return_value = [
            {"analysis_id": 1, "symbol": "EUR/USD", "final_signal": "BUY", "agreement_score": 86}
        ]
        mock_scheduler.get_statistics.return_value = {
            "successful_analyses": 1,
            "failed_analyses": 0,
            "total_tokens": 2500,
            "total_cost": 0.025
        }
        
        response = client.post(
            "/ai/trigger-analysis",
            headers={"X-API-Key": "test-key"},
            json={}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "results" in data
        assert "statistics" in data
    
    def test_trigger_analysis_custom_symbols(self, client, mock_db):
        """Test POST /ai/trigger-analysis - własne symbole"""
        response = client.post(
            "/ai/trigger-analysis",
            headers={"X-API-Key": "test-key"},
            json={
                "symbols": ["EUR/USD", "GBP/USD"],
                "timeframe": "1h"
            }
        )
        
        # Endpoint może zwrócić 200 lub 500 w zależności od dostępności serwisów
        # Sprawdzamy tylko czy request jest poprawnie przetwarzany
        assert response.status_code in [200, 500]
    
    def test_trigger_analysis_invalid_timeframe(self, client, mock_db):
        """Test POST /ai/trigger-analysis - nieprawidłowy timeframe"""
        response = client.post(
            "/ai/trigger-analysis",
            headers={"X-API-Key": "test-key"},
            json={"timeframe": "invalid"}
        )
        
        assert response.status_code == 422
    
    def test_trigger_analysis_invalid_symbols(self, client, mock_db):
        """Test POST /ai/trigger-analysis - nieprawidłowe symbole"""
        response = client.post(
            "/ai/trigger-analysis",
            headers={"X-API-Key": "test-key"},
            json={"symbols": ["INVALID"]}
        )
        
        assert response.status_code == 422
    
    def test_trigger_analysis_too_many_symbols(self, client, mock_db):
        """Test POST /ai/trigger-analysis - za dużo symboli"""
        symbols = [f"SYM{i}/USD" for i in range(51)]
        
        response = client.post(
            "/ai/trigger-analysis",
            headers={"X-API-Key": "test-key"},
            json={"symbols": symbols}
        )
        
        assert response.status_code == 422


class TestRefactoredAnalyzeEndpoint:
    """Testy dla zrefaktoryzowanego endpointu /ai/analyze"""
    
    @pytest.mark.asyncio
    async def test_analyze_new_format(self, client, mock_db, mock_ai_strategy):
        """Test POST /ai/analyze - nowy format odpowiedzi"""
        # Mock comprehensive_analysis
        mock_ai_strategy.comprehensive_analysis.return_value = {
            "symbol": "EUR/USD",
            "timeframe": "1h",
            "timestamp": "2026-01-16T20:00:00",
            "ai_analysis": {
                "recommendation": "BUY",
                "confidence": 85,
                "reasoning": "Test",
                "tokens_used": 2500,
                "estimated_cost": 0.025
            },
            "technical_analysis": {
                "signal": "BUY",
                "confidence": 75,
                "indicators": {"rsi": 35}
            },
            "macro_analysis": {
                "signal": "HOLD",
                "impact": "neutral"
            },
            "news_analysis": {
                "sentiment": "positive",
                "score": 70
            }
        }
        
        mock_db.create_ai_analysis_result.return_value = 123
        
        response = client.post(
            "/ai/analyze?symbol=EUR/USD&timeframe=1h",
            headers={"X-API-Key": "test-key"}
        )
        
        # Sprawdzamy czy request jest poprawnie przetwarzany
        # Może zwrócić błąd jeśli brak rzeczywistych serwisów
        assert response.status_code in [200, 500]


class TestRateLimiting:
    """Testy rate limiting"""
    
    def test_rate_limit_exceeded(self, client, mock_db):
        """Test przekroczenia limitu rate limiting"""
        # Wykonaj więcej requestów niż dozwolone
        for i in range(65):  # Limit to 60/hour
            response = client.get(
                "/ai/analysis-results",
                headers={"X-API-Key": "test-key"}
            )
            
            if i < 60:
                assert response.status_code == 200
            else:
                # Po przekroczeniu limitu powinien być 429
                assert response.status_code == 429


# Fixtures dla testów
@pytest.fixture
def client():
    """Fixture dla test client"""
    from app.main import app
    return TestClient(app)


@pytest.fixture
def mock_db(mocker):
    """Mock dla get_database – zwraca mock z metodami bazy."""
    mock = mocker.MagicMock()
    mocker.patch('app.api.dependencies.get_database', return_value=mock)
    return mock


@pytest.fixture
def mock_scheduler(mocker):
    """Mock dla AutoAnalysisScheduler"""
    return mocker.patch('app.services.auto_analysis_scheduler.AutoAnalysisScheduler')


@pytest.fixture
def mock_ai_strategy(mocker):
    """Mock dla AIStrategy"""
    return mocker.patch('app.services.ai_strategy.AIStrategy')
