"""
Testy API endpoints dla AI Analysis
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock, AsyncMock
import json
from datetime import datetime

from app.main import app
from app.utils.database import Database


@pytest.fixture
def client():
    """Klient testowy FastAPI"""
    return TestClient(app)


@pytest.fixture
def test_api_key():
    """Klucz API do testów"""
    return "test-api-key-32-characters-long-12345"


@pytest.fixture
def test_headers(test_api_key):
    """Nagłówki HTTP z kluczem API"""
    return {
        "X-API-Key": test_api_key,
        "Content-Type": "application/json"
    }


@pytest.mark.api
@pytest.mark.integration
class TestAIAnalysisEndpoints:
    """Testy endpointów analizy AI"""
    
    @pytest.mark.asyncio
    def test_ai_analyze_missing_symbol(self, client, test_headers):
        """Test POST /ai/analyze bez symbolu"""
        response = client.post(
            "/ai/analyze",
            headers=test_headers
        )
        
        # Powinno zwrócić błąd walidacji
        assert response.status_code in [400, 422]
    
    def test_ai_analyze_without_api_key(self, client):
        """Test POST /ai/analyze bez klucza API"""
        response = client.post(
            "/ai/analyze?symbol=EUR/USD",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 403
    
    @pytest.mark.asyncio
    def test_market_overview_invalid_symbol(self, client, test_headers):
        """Test GET /ai/market-overview z nieprawidłowym symbolem"""
        with patch('app.services.ai_strategy.AIStrategy.comprehensive_analysis') as mock_analysis:
            mock_analysis.side_effect = Exception("Invalid symbol")
            
            response = client.get(
                "/ai/market-overview/INVALID",
                headers=test_headers
            )
            
            assert response.status_code == 500


@pytest.mark.api
@pytest.mark.integration
class TestAIResultsEndpoints:
    """Testy endpointów wyników analiz"""
    
    def test_get_analysis_results_all(self, client, test_headers):
        """Test GET /ai/analysis-results - wszystkie wyniki"""
        with patch('app.api.dependencies.get_database') as mock_db:
            mock_db.return_value.get_ai_analysis_results.return_value = [
                {
                    "id": 1,
                    "symbol": "EUR/USD",
                    "final_signal": "BUY",
                    "agreement_score": 75
                }
            ]
            
            response = client.get(
                "/ai/analysis-results",
                headers=test_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "results" in data
            assert isinstance(data["results"], list)
    
    def test_get_analysis_results_filter_by_symbol(self, client, test_headers):
        """Test GET /ai/analysis-results?symbol=EUR/USD"""
        with patch('app.api.dependencies.get_database') as mock_db:
            mock_db.return_value.get_ai_analysis_results.return_value = [
                {
                    "id": 1,
                    "symbol": "EUR/USD",
                    "final_signal": "BUY",
                    "agreement_score": 75
                }
            ]
            
            response = client.get(
                "/ai/analysis-results?symbol=EUR/USD",
                headers=test_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert len(data["results"]) >= 0
    
    def test_get_analysis_results_filter_by_signal_type(self, client, test_headers):
        """Test GET /ai/analysis-results?signal_type=BUY"""
        with patch('app.api.dependencies.get_database') as mock_db:
            mock_db.return_value.get_ai_analysis_results.return_value = [
                {
                    "id": 1,
                    "symbol": "EUR/USD",
                    "final_signal": "BUY",
                    "agreement_score": 75
                },
                {
                    "id": 2,
                    "symbol": "GBP/USD",
                    "final_signal": "SELL",
                    "agreement_score": 70
                }
            ]
            
            response = client.get(
                "/ai/analysis-results?signal_type=BUY",
                headers=test_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            # Powinny być tylko BUY
            buy_results = [r for r in data["results"] if r["final_signal"] == "BUY"]
            assert len(buy_results) == len(data["results"])
    
    def test_get_analysis_results_filter_by_min_agreement(self, client, test_headers):
        """Test GET /ai/analysis-results?min_agreement=70"""
        with patch('app.api.dependencies.get_database') as mock_db:
            mock_db.return_value.get_ai_analysis_results.return_value = [
                {
                    "id": 1,
                    "symbol": "EUR/USD",
                    "final_signal": "BUY",
                    "agreement_score": 75
                },
                {
                    "id": 2,
                    "symbol": "GBP/USD",
                    "final_signal": "BUY",
                    "agreement_score": 65
                }
            ]
            
            response = client.get(
                "/ai/analysis-results?min_agreement=70",
                headers=test_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            # Wszystkie wyniki powinny mieć agreement_score >= 70
            for result in data["results"]:
                assert result["agreement_score"] >= 70
    
    def test_get_analysis_results_with_limit(self, client, test_headers):
        """Test GET /ai/analysis-results?limit=10"""
        with patch('app.api.dependencies.get_database') as mock_db:
            # Zwróć 20 wyników
            mock_db.return_value.get_ai_analysis_results.return_value = [
                {"id": i, "symbol": "EUR/USD", "final_signal": "BUY", "agreement_score": 75}
                for i in range(20)
            ]
            
            response = client.get(
                "/ai/analysis-results?limit=10",
                headers=test_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert len(data["results"]) <= 10
    
    def test_get_analysis_results_invalid_signal_type(self, client, test_headers):
        """Test GET /ai/analysis-results?signal_type=INVALID"""
        response = client.get(
            "/ai/analysis-results?signal_type=INVALID",
            headers=test_headers
        )
        
        assert response.status_code == 400
    
    def test_get_analysis_by_id_success(self, client, test_headers):
        """Test GET /ai/analysis-results/{id} - istnieje"""
        with patch('app.api.dependencies.get_database') as mock_db:
            mock_db.return_value.get_ai_analysis_by_id.return_value = {
                "id": 1,
                "symbol": "EUR/USD",
                "final_signal": "BUY",
                "agreement_score": 75,
                "technical_details": '{"rsi": 35}',
                "voting_details": '{"ai": {"vote": "BUY"}}'
            }
            
            response = client.get(
                "/ai/analysis-results/1",
                headers=test_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == 1
            assert data["symbol"] == "EUR/USD"
    
    def test_get_analysis_by_id_not_found(self, client, test_headers):
        """Test GET /ai/analysis-results/{id} - nie istnieje"""
        with patch('app.api.dependencies.get_database') as mock_db:
            mock_db.return_value.get_ai_analysis_by_id.return_value = None
            
            response = client.get(
                "/ai/analysis-results/99999",
                headers=test_headers
            )
            
            assert response.status_code == 404
    
    def test_get_analysis_by_id_parses_json_fields(self, client, test_headers):
        """Test parsowania pól JSON w wynikach"""
        with patch('app.api.dependencies.get_database') as mock_db:
            mock_db.return_value.get_ai_analysis_by_id.return_value = {
                "id": 1,
                "symbol": "EUR/USD",
                "final_signal": "BUY",
                "agreement_score": 75,
                "technical_details": '{"rsi": 35, "macd": "bullish"}',
                "voting_details": '{"ai": {"vote": "BUY", "confidence": 80}}'
            }
            
            response = client.get(
                "/ai/analysis-results/1",
                headers=test_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Sprawdź czy JSON został sparsowany
            assert isinstance(data["technical_details"], dict)
            assert data["technical_details"]["rsi"] == 35
            assert isinstance(data["voting_details"], dict)


@pytest.mark.api
@pytest.mark.integration
class TestTokenStatisticsEndpoints:
    """Testy endpointów statystyk tokenów"""
    
    def test_token_statistics_all_time(self, client, test_headers):
        """Test GET /ai/token-statistics - wszystkie czasy"""
        with patch('app.api.dependencies.get_database') as mock_db:
            mock_db.return_value.get_token_statistics.return_value = {
                "total_tokens": 10000,
                "total_cost": 0.01,
                "analyses_count": 5,
                "avg_tokens_per_analysis": 2000,
                "today_tokens": 2000,
                "today_cost": 0.002,
                "today_analyses": 1
            }
            
            response = client.get(
                "/ai/token-statistics",
                headers=test_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["total_tokens"] == 10000
            assert data["analyses_count"] == 5
    
    def test_token_statistics_with_date_range(self, client, test_headers):
        """Test GET /ai/token-statistics?start_date=...&end_date=..."""
        with patch('app.api.dependencies.get_database') as mock_db:
            mock_db.return_value.get_token_statistics.return_value = {
                "total_tokens": 5000,
                "total_cost": 0.005,
                "analyses_count": 2,
                "avg_tokens_per_analysis": 2500
            }
            
            response = client.get(
                "/ai/token-statistics?start_date=2026-01-01&end_date=2026-01-31",
                headers=test_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "period" in data
            assert data["period"]["start_date"] == "2026-01-01"
    
    def test_token_statistics_invalid_date_format(self, client, test_headers):
        """Test GET /ai/token-statistics z nieprawidłowym formatem daty"""
        response = client.get(
            "/ai/token-statistics?start_date=invalid-date",
            headers=test_headers
        )
        
        assert response.status_code == 400
    
    def test_token_statistics_empty_database(self, client, test_headers):
        """Test GET /ai/token-statistics dla pustej bazy"""
        with patch('app.api.dependencies.get_database') as mock_db:
            mock_db.return_value.get_token_statistics.return_value = {
                "total_tokens": 0,
                "total_cost": 0.0,
                "analyses_count": 0,
                "avg_tokens_per_analysis": 0
            }
            
            response = client.get(
                "/ai/token-statistics",
                headers=test_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["total_tokens"] == 0


@pytest.mark.api
@pytest.mark.integration
class TestConfigurationEndpoints:
    """Testy endpointów konfiguracji"""
    
    def test_get_analysis_config(self, client, test_headers):
        """Test GET /ai/analysis-config"""
        with patch('app.api.dependencies.get_database') as mock_db:
            mock_db.return_value.get_analysis_config.return_value = {
                "id": 1,
                "analysis_interval": 15,
                "enabled_symbols": '["EUR/USD", "GBP/USD"]',
                "notification_threshold": 60,
                "is_active": 1
            }
            
            response = client.get(
                "/ai/analysis-config",
                headers=test_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["analysis_interval"] == 15
            assert data["notification_threshold"] == 60
    
    def test_get_analysis_config_parses_symbols(self, client, test_headers):
        """Test parsowania enabled_symbols z JSON"""
        with patch('app.api.dependencies.get_database') as mock_db:
            mock_db.return_value.get_analysis_config.return_value = {
                "id": 1,
                "analysis_interval": 15,
                "enabled_symbols": '["EUR/USD", "GBP/USD", "USD/JPY"]',
                "notification_threshold": 60,
                "is_active": 1
            }
            
            response = client.get(
                "/ai/analysis-config",
                headers=test_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data["enabled_symbols"], list)
            assert len(data["enabled_symbols"]) == 3
    
    def test_update_config_interval(self, client, test_headers):
        """Test PUT /ai/analysis-config - zmiana interwału"""
        with patch('app.api.dependencies.get_database') as mock_db:
            mock_db.return_value.update_analysis_config.return_value = True
            mock_db.return_value.get_analysis_config.return_value = {
                "id": 1,
                "analysis_interval": 30,
                "enabled_symbols": '[]',
                "notification_threshold": 60,
                "is_active": 1
            }
            
            response = client.put(
                "/ai/analysis-config",
                headers=test_headers,
                json={"analysis_interval": 30}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "updated_config" in data
    
    def test_update_config_symbols(self, client, test_headers):
        """Test PUT /ai/analysis-config - zmiana symboli"""
        with patch('app.api.dependencies.get_database') as mock_db:
            mock_db.return_value.update_analysis_config.return_value = True
            mock_db.return_value.get_analysis_config.return_value = {
                "id": 1,
                "analysis_interval": 15,
                "enabled_symbols": '["EUR/USD", "GBP/USD"]',
                "notification_threshold": 60,
                "is_active": 1
            }
            
            response = client.put(
                "/ai/analysis-config",
                headers=test_headers,
                json={"enabled_symbols": ["EUR/USD", "GBP/USD"]}
            )
            
            assert response.status_code == 200
    
    def test_update_config_threshold(self, client, test_headers):
        """Test PUT /ai/analysis-config - zmiana progu"""
        with patch('app.api.dependencies.get_database') as mock_db:
            mock_db.return_value.update_analysis_config.return_value = True
            mock_db.return_value.get_analysis_config.return_value = {
                "id": 1,
                "analysis_interval": 15,
                "enabled_symbols": '[]',
                "notification_threshold": 70,
                "is_active": 1
            }
            
            response = client.put(
                "/ai/analysis-config",
                headers=test_headers,
                json={"notification_threshold": 70}
            )
            
            assert response.status_code == 200
    
    def test_update_config_all_fields(self, client, test_headers):
        """Test PUT /ai/analysis-config - wszystkie pola"""
        with patch('app.api.dependencies.get_database') as mock_db:
            mock_db.return_value.update_analysis_config.return_value = True
            mock_db.return_value.get_analysis_config.return_value = {
                "id": 1,
                "analysis_interval": 20,
                "enabled_symbols": '["EUR/USD"]',
                "notification_threshold": 65,
                "is_active": 0
            }
            
            response = client.put(
                "/ai/analysis-config",
                headers=test_headers,
                json={
                    "analysis_interval": 20,
                    "enabled_symbols": ["EUR/USD"],
                    "notification_threshold": 65,
                    "is_active": False
                }
            )
            
            assert response.status_code == 200
    
    def test_update_config_invalid_interval(self, client, test_headers):
        """Test PUT /ai/analysis-config - nieprawidłowy interwał"""
        response = client.put(
            "/ai/analysis-config",
            headers=test_headers,
            json={"analysis_interval": 2000}  # Powyżej max 1440
        )
        
        assert response.status_code == 422
    
    def test_update_config_invalid_symbols(self, client, test_headers):
        """Test PUT /ai/analysis-config - nieprawidłowe symbole"""
        response = client.put(
            "/ai/analysis-config",
            headers=test_headers,
            json={"enabled_symbols": ["INVALID"]}  # Brak /
        )
        
        assert response.status_code == 422
    
    def test_update_config_too_many_symbols(self, client, test_headers):
        """Test PUT /ai/analysis-config - za dużo symboli (max 50)"""
        symbols = [f"TEST{i}/USD" for i in range(51)]
        
        response = client.put(
            "/ai/analysis-config",
            headers=test_headers,
            json={"enabled_symbols": symbols}
        )
        
        assert response.status_code == 422


@pytest.mark.api
@pytest.mark.integration
class TestTriggerAnalysisEndpoint:
    """Testy endpointu ręcznego uruchamiania analiz"""
    
    @pytest.mark.asyncio
    def test_trigger_analysis_default_symbols(self, client, test_headers):
        """Test POST /ai/trigger-analysis - domyślne symbole"""
        with patch('app.api.dependencies.get_auto_scheduler') as mock_scheduler_factory:
            mock_scheduler = Mock()
            mock_scheduler.run_analysis_cycle = AsyncMock(return_value=[
                {"analysis_id": 1, "symbol": "EUR/USD", "final_signal": "BUY"}
            ])
            mock_scheduler.get_statistics.return_value = {
                "successful_analyses": 1,
                "failed_analyses": 0,
                "total_tokens": 1000,
                "total_cost": 0.001
            }
            mock_scheduler_factory.return_value = mock_scheduler
            
            response = client.post(
                "/ai/trigger-analysis",
                headers=test_headers,
                json={}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "results" in data
            assert "statistics" in data
    
    @pytest.mark.asyncio
    def test_trigger_analysis_custom_symbols(self, client, test_headers):
        """Test POST /ai/trigger-analysis - niestandardowe symbole"""
        with patch('app.api.dependencies.get_auto_scheduler') as mock_scheduler_factory:
            mock_scheduler = Mock()
            mock_scheduler.run_analysis_cycle = AsyncMock(return_value=[
                {"analysis_id": 1, "symbol": "XAU/USD"}
            ])
            mock_scheduler.get_statistics.return_value = {
                "successful_analyses": 1,
                "failed_analyses": 0,
                "total_tokens": 1000,
                "total_cost": 0.001
            }
            mock_scheduler_factory.return_value = mock_scheduler
            
            response = client.post(
                "/ai/trigger-analysis",
                headers=test_headers,
                json={"symbols": ["XAU/USD"]}
            )
            
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    def test_trigger_analysis_custom_timeframe(self, client, test_headers):
        """Test POST /ai/trigger-analysis - niestandardowy timeframe"""
        with patch('app.api.dependencies.get_auto_scheduler') as mock_scheduler_factory:
            mock_scheduler = Mock()
            mock_scheduler.run_analysis_cycle = AsyncMock(return_value=[])
            mock_scheduler.get_statistics.return_value = {
                "successful_analyses": 0,
                "failed_analyses": 0,
                "total_tokens": 0,
                "total_cost": 0.0
            }
            mock_scheduler_factory.return_value = mock_scheduler
            
            response = client.post(
                "/ai/trigger-analysis",
                headers=test_headers,
                json={"timeframe": "4h"}
            )
            
            assert response.status_code == 200
    
    def test_trigger_analysis_invalid_timeframe(self, client, test_headers):
        """Test POST /ai/trigger-analysis - nieprawidłowy timeframe"""
        response = client.post(
            "/ai/trigger-analysis",
            headers=test_headers,
            json={"timeframe": "invalid"}
        )
        
        assert response.status_code == 422
    
    def test_trigger_analysis_too_many_symbols(self, client, test_headers):
        """Test POST /ai/trigger-analysis - za dużo symboli (max 50)"""
        symbols = [f"TEST{i}/USD" for i in range(51)]
        
        response = client.post(
            "/ai/trigger-analysis",
            headers=test_headers,
            json={"symbols": symbols}
        )
        
        assert response.status_code == 422


@pytest.mark.api
class TestAPISecurityAndValidation:
    """Testy bezpieczeństwa i walidacji API"""
    
    def test_api_key_required(self, client):
        """Test że klucz API jest wymagany"""
        response = client.get("/ai/analysis-results")
        
        assert response.status_code == 403
    
    def test_invalid_api_key_rejected(self, client):
        """Test że nieprawidłowy klucz API jest odrzucany"""
        response = client.get(
            "/ai/analysis-results",
            headers={"X-API-Key": "invalid-key"}
        )
        
        assert response.status_code == 403
    
    def test_sql_injection_protection(self, client, test_headers):
        """Test ochrony przed SQL injection"""
        # Próba SQL injection w parametrze symbol
        response = client.get(
            "/ai/analysis-results?symbol=EUR/USD'; DROP TABLE ai_analysis_results;--",
            headers=test_headers
        )
        
        # Powinno być bezpiecznie obsłużone (nie błąd 500)
        assert response.status_code in [200, 400, 422]
    
    def test_json_injection_protection(self, client, test_headers):
        """Test ochrony przed JSON injection"""
        malicious_json = {
            "enabled_symbols": ["EUR/USD\"; DROP TABLE analysis_config;--"]
        }
        
        response = client.put(
            "/ai/analysis-config",
            headers=test_headers,
            json=malicious_json
        )
        
        # Powinno być odrzucone przez walidację
        assert response.status_code in [400, 422]


def run_tests():
    """Uruchamia testy API"""
    pytest.main([__file__, "-v", "--tb=short", "-m", "api"])


if __name__ == "__main__":
    run_tests()
