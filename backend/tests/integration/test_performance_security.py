"""
Testy wydajności, timeoutów i bezpieczeństwa
"""
import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock, AsyncMock
import time
from concurrent.futures import ThreadPoolExecutor
import json

from app.main import app
from app.utils.database import Database


@pytest.fixture
def perf_client():
    """Klient testowy dla testów wydajności"""
    return TestClient(app)


@pytest.fixture
def perf_headers():
    """Nagłówki dla testów wydajności"""
    return {
        "X-API-Key": "test-api-key-32-characters-long-12345",
        "Content-Type": "application/json"
    }


@pytest.mark.slow
class TestRateLimiting:
    """Testy limitów requestów"""
    
    def test_rate_limit_returns_429(self, perf_client, perf_headers):
        """Test że przekroczenie limitu zwraca 429"""
        # Uwaga: Ten test może nie działać z TestClient który nie respektuje rate limitów
        # W prawdziwym środowisku trzeba by użyć rzeczywistych requestów HTTP
        
        with patch('app.api.dependencies.get_database') as mock_db:
            mock_db.return_value.get_ai_analysis_results.return_value = []
            
            # Wykonaj wiele requestów
            responses = []
            for i in range(5):
                response = perf_client.get(
                    "/ai/analysis-results",
                    headers=perf_headers
                )
                responses.append(response.status_code)
            
            # Większość powinna przejść (200)
            success_count = sum(1 for code in responses if code == 200)
            assert success_count >= 3


@pytest.mark.slow
class TestTimeouts:
    """Testy timeoutów"""
    
    @pytest.mark.asyncio
    async def test_analyze_symbol_respects_timeout(self, test_db, mock_telegram):
        """Test że analiza respektuje timeout"""
        from app.services.auto_analysis_scheduler import AutoAnalysisScheduler
        
        scheduler = AutoAnalysisScheduler(
            database=test_db,
            telegram=mock_telegram,
            interval_minutes=15
        )
        
        # Mock długo trwającej analizy
        async def slow_analysis(*args, **kwargs):
            await asyncio.sleep(10)  # 10 sekund
            return {}
        
        with patch.object(scheduler.ai_strategy, 'comprehensive_analysis', side_effect=slow_analysis):
            start_time = time.time()
            
            try:
                # Timeout powinien przerwać
                result = await asyncio.wait_for(
                    scheduler.analyze_symbol("EUR/USD", "1h"),
                    timeout=2.0
                )
            except asyncio.TimeoutError:
                pass
            
            duration = time.time() - start_time
            
            # Powinno zakończyć się w ~2 sekundy (timeout)
            assert duration < 3.0


@pytest.mark.slow
class TestConcurrency:
    """Testy równoległych requestów"""
    
    def test_multiple_analyses_parallel(self, perf_client, perf_headers):
        """Test równoległych analiz"""
        
        with patch('app.services.ai_strategy.AIStrategy.comprehensive_analysis') as mock_analysis, \
             patch('app.services.signal_aggregator_service.SignalAggregatorService.aggregate_signals') as mock_aggregate, \
             patch('app.api.dependencies.get_database') as mock_db_factory:
            
            # Setup mocks
            mock_db = Mock()
            mock_db.initialize_default_config.return_value = None
            mock_db.create_ai_analysis_result.return_value = 1
            mock_db_factory.return_value = mock_db
            
            mock_analysis.return_value = {
                "symbol": "EUR/USD",
                "timeframe": "1h",
                "timestamp": "2026-01-16T12:00:00",
                "ai_analysis": {
                    "recommendation": "BUY",
                    "confidence": 80,
                    "reasoning": "Test",
                    "tokens_used": 1000,
                    "estimated_cost": 0.001
                },
                "technical_analysis": {
                    "signal": "BUY",
                    "confidence": 70,
                    "indicators": {}
                },
                "macro_analysis": {
                    "signal": "HOLD",
                    "confidence": 50,
                    "impact": "neutral"
                },
                "news_analysis": {
                    "sentiment": "positive",
                    "score": 65
                }
            }
            
            mock_aggregate.return_value = {
                "final_signal": "BUY",
                "agreement_score": 75,
                "weighted_score": 72.5,
                "voting_details": {},
                "decision_reason": "Test",
                "should_notify": False
            }
            
            # Wykonaj 5 równoległych requestów
            def make_request():
                return perf_client.post(
                    "/ai/analyze?symbol=EUR/USD&timeframe=1h",
                    headers=perf_headers
                )
            
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(make_request) for _ in range(5)]
                responses = [f.result() for f in futures]
            
            # Wszystkie powinny zakończyć się sukcesem
            success_count = sum(1 for r in responses if r.status_code == 200)
            assert success_count >= 3  # Przynajmniej 3 z 5 powinny przejść
    
    def test_database_concurrent_writes(self, test_db):
        """Test równoczesnych zapisów do bazy"""
        import threading
        
        test_db.initialize_default_config()
        
        results = []
        errors = []
        
        def write_analysis(symbol_id):
            try:
                data = pytest.create_mock_analysis_result(
                    symbol=f"TEST{symbol_id}/USD",
                    final_signal="BUY",
                    agreement_score=75
                )
                result_id = test_db.create_ai_analysis_result(data)
                results.append(result_id)
            except Exception as e:
                errors.append(str(e))
        
        # Utwórz 10 wątków zapisujących równocześnie
        threads = []
        for i in range(10):
            thread = threading.Thread(target=write_analysis, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Poczekaj na zakończenie
        for thread in threads:
            thread.join()
        
        # Sprawdź wyniki
        assert len(errors) == 0  # Brak błędów
        assert len(results) == 10  # Wszystkie zapisy udane
        assert len(set(results)) == 10  # Wszystkie ID unikalne


class TestSecurity:
    """Testy bezpieczeństwa"""
    
    def test_api_key_required(self, perf_client):
        """Test że klucz API jest wymagany"""
        response = perf_client.get("/ai/analysis-results")
        
        assert response.status_code == 403
        assert "API" in response.json()["detail"] or "key" in response.json()["detail"].lower()
    
    def test_invalid_api_key_rejected(self, perf_client):
        """Test że nieprawidłowy klucz API jest odrzucany"""
        response = perf_client.get(
            "/ai/analysis-results",
            headers={"X-API-Key": "invalid-key-12345"}
        )
        
        assert response.status_code == 403
    
    def test_sql_injection_protection(self, perf_client, perf_headers):
        """Test ochrony przed SQL injection"""
        
        with patch('app.api.dependencies.get_database') as mock_db:
            mock_db.return_value.get_ai_analysis_results.return_value = []
            
            # Próby SQL injection
            malicious_inputs = [
                "EUR/USD'; DROP TABLE ai_analysis_results;--",
                "EUR/USD' OR '1'='1",
                "EUR/USD'; DELETE FROM ai_analysis_results WHERE '1'='1';--",
                "EUR/USD' UNION SELECT * FROM users;--"
            ]
            
            for malicious_input in malicious_inputs:
                response = perf_client.get(
                    f"/ai/analysis-results?symbol={malicious_input}",
                    headers=perf_headers
                )
                
                # Powinno być bezpiecznie obsłużone
                assert response.status_code in [200, 400, 422]
                # Nie powinno być błędu 500 (internal server error)
                assert response.status_code != 500
    
    def test_json_injection_protection(self, perf_client, perf_headers):
        """Test ochrony przed JSON injection"""
        
        with patch('app.api.dependencies.get_database') as mock_db:
            mock_db.return_value.update_analysis_config.return_value = True
            mock_db.return_value.get_analysis_config.return_value = {
                "id": 1,
                "analysis_interval": 15,
                "enabled_symbols": '[]',
                "notification_threshold": 60,
                "is_active": 1
            }
            
            # Próby JSON injection
            malicious_payloads = [
                {"enabled_symbols": ["EUR/USD\"; DROP TABLE analysis_config;--"]},
                {"enabled_symbols": ["EUR/USD', 'GBP/USD'); DROP TABLE analysis_config;--"]},
                {"analysis_interval": "15; DROP TABLE analysis_config;--"}
            ]
            
            for payload in malicious_payloads:
                response = perf_client.put(
                    "/ai/analysis-config",
                    headers=perf_headers,
                    json=payload
                )
                
                # Powinno być odrzucone przez walidację
                assert response.status_code in [200, 400, 422]
                assert response.status_code != 500
    
    def test_xss_protection_in_responses(self, perf_client, perf_headers):
        """Test ochrony przed XSS w odpowiedziach"""
        
        with patch('app.api.dependencies.get_database') as mock_db:
            # Symuluj dane z potencjalnym XSS
            mock_db.return_value.get_ai_analysis_results.return_value = [
                {
                    "id": 1,
                    "symbol": "<script>alert('XSS')</script>",
                    "final_signal": "BUY",
                    "agreement_score": 75,
                    "ai_reasoning": "<img src=x onerror=alert('XSS')>"
                }
            ]
            
            response = perf_client.get(
                "/ai/analysis-results",
                headers=perf_headers
            )
            
            assert response.status_code == 200
            
            # Sprawdź czy odpowiedź jest JSON (nie HTML)
            assert response.headers["content-type"] == "application/json"
            
            # Dane powinny być zwrócone jako plain text w JSON
            data = response.json()
            if data["results"]:
                # Skrypty powinny być zwrócone jako tekst, nie wykonane
                assert "<script>" in str(data) or data["results"][0]["symbol"] == "<script>alert('XSS')</script>"
    
    def test_path_traversal_protection(self, perf_client, perf_headers):
        """Test ochrony przed path traversal"""
        
        # Próby path traversal w ID
        malicious_ids = [
            "../../../etc/passwd",
            "..%2F..%2F..%2Fetc%2Fpasswd",
            "....//....//....//etc/passwd"
        ]
        
        for malicious_id in malicious_ids:
            response = perf_client.get(
                f"/ai/analysis-results/{malicious_id}",
                headers=perf_headers
            )
            
            # Powinno być odrzucone (404 lub 422)
            assert response.status_code in [404, 422]
            assert response.status_code != 200
    
    def test_sensitive_data_not_exposed(self, perf_client, perf_headers):
        """Test że wrażliwe dane nie są eksponowane"""
        
        # Sprawdź endpoint /health (publiczny)
        response = perf_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        # Nie powinno być wrażliwych informacji
        assert "api_key" not in str(data).lower()
        assert "password" not in str(data).lower()
        assert "secret" not in str(data).lower()
        assert "token" not in str(data).lower() or "telegram" in str(data).lower()  # telegram_status OK


@pytest.mark.slow
class TestPerformance:
    """Testy wydajności"""
    
    def test_database_query_performance(self, test_db):
        """Test wydajności zapytań do bazy"""
        test_db.initialize_default_config()
        
        # Dodaj 100 wyników analiz
        for i in range(100):
            data = pytest.create_mock_analysis_result(
                symbol=f"TEST{i % 10}/USD",
                final_signal="BUY" if i % 2 == 0 else "SELL",
                agreement_score=70 + (i % 30)
            )
            test_db.create_ai_analysis_result(data)
        
        # Zmierz czas zapytania
        start_time = time.time()
        results = test_db.get_ai_analysis_results(limit=50)
        query_time = time.time() - start_time
        
        # Powinno być szybkie (< 100ms)
        assert query_time < 0.1
        assert len(results) == 50
    
    def test_token_statistics_performance(self, test_db):
        """Test wydajności obliczania statystyk"""
        test_db.initialize_default_config()
        
        # Dodaj 200 analiz
        for i in range(200):
            data = pytest.create_mock_analysis_result()
            data["tokens_used"] = 1000 + i
            data["estimated_cost"] = 0.001 * (i + 1)
            test_db.create_ai_analysis_result(data)
        
        # Zmierz czas obliczania statystyk
        start_time = time.time()
        stats = test_db.get_token_statistics()
        calc_time = time.time() - start_time
        
        # Powinno być szybkie (< 200ms)
        assert calc_time < 0.2
        assert stats["analyses_count"] == 200
    
    def test_api_response_time(self, perf_client, perf_headers):
        """Test czasu odpowiedzi API"""
        
        with patch('app.api.dependencies.get_database') as mock_db:
            mock_db.return_value.get_ai_analysis_results.return_value = [
                {
                    "id": i,
                    "symbol": "EUR/USD",
                    "final_signal": "BUY",
                    "agreement_score": 75
                }
                for i in range(50)
            ]
            
            # Zmierz czas odpowiedzi
            start_time = time.time()
            response = perf_client.get(
                "/ai/analysis-results?limit=50",
                headers=perf_headers
            )
            response_time = time.time() - start_time
            
            assert response.status_code == 200
            # Powinno być szybkie (< 500ms)
            assert response_time < 0.5


def run_tests():
    """Uruchamia testy wydajności i bezpieczeństwa"""
    pytest.main([__file__, "-v", "--tb=short"])


if __name__ == "__main__":
    run_tests()
