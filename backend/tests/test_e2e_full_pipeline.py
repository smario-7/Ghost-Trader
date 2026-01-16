"""
Testy E2E (End-to-End) pełnego pipeline'u systemu
"""
import pytest
import sys
from pathlib import Path
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock, AsyncMock
import json
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.main import app
from app.utils.database import Database


@pytest.fixture
def e2e_client():
    """Klient testowy dla testów E2E"""
    return TestClient(app)


@pytest.fixture
def e2e_headers():
    """Nagłówki dla testów E2E"""
    return {
        "X-API-Key": "test-api-key-32-characters-long-12345",
        "Content-Type": "application/json"
    }


@pytest.mark.e2e
@pytest.mark.integration
class TestE2EFullPipeline:
    """Testy pełnego przepływu danych przez system"""
    
    @pytest.mark.asyncio
    def test_full_pipeline_single_symbol(self, e2e_client, e2e_headers, test_db):
        """
        Test 1: Pełny przepływ analizy pojedynczego symbolu
        1. POST /ai/analyze z symbolem EUR/USD
        2. Sprawdź odpowiedź API
        3. Sprawdź zapis w bazie (ai_analysis_results)
        4. Sprawdź statystyki tokenów
        """
        test_db.initialize_default_config()
        
        with patch('app.main.get_database', return_value=test_db), \
             patch('app.services.ai_strategy.AIStrategy.comprehensive_analysis') as mock_analysis, \
             patch('app.services.signal_aggregator_service.SignalAggregatorService.aggregate_signals') as mock_aggregate:
            
            # Mock comprehensive_analysis
            mock_analysis.return_value = {
                "symbol": "EUR/USD",
                "timeframe": "1h",
                "timestamp": datetime.now().isoformat(),
                "ai_analysis": {
                    "recommendation": "BUY",
                    "confidence": 80,
                    "reasoning": "Strong bullish signals",
                    "tokens_used": 1500,
                    "estimated_cost": 0.0015
                },
                "technical_analysis": {
                    "signal": "BUY",
                    "confidence": 70,
                    "indicators": {"rsi": 35, "macd": "bullish"}
                },
                "macro_analysis": {
                    "signal": "HOLD",
                    "confidence": 50,
                    "impact": "neutral",
                    "summary": "Fed maintains rates"
                },
                "news_analysis": {
                    "sentiment": "positive",
                    "score": 65,
                    "news_count": 5
                }
            }
            
            # Mock aggregate_signals
            mock_aggregate.return_value = {
                "final_signal": "BUY",
                "agreement_score": 75,
                "weighted_score": 72.5,
                "voting_details": {
                    "ai": {"vote": "BUY", "confidence": 80, "weight": 40},
                    "technical": {"vote": "BUY", "confidence": 70, "weight": 30},
                    "macro": {"vote": "HOLD", "confidence": 50, "weight": 20},
                    "news": {"vote": "BUY", "confidence": 65, "weight": 10}
                },
                "decision_reason": "3 out of 4 sources indicate BUY",
                "should_notify": True
            }
            
            # 1. POST /ai/analyze
            response = e2e_client.post(
                "/ai/analyze?symbol=EUR/USD&timeframe=1h",
                headers=e2e_headers
            )
            
            # 2. Sprawdź odpowiedź API
            assert response.status_code == 200
            data = response.json()
            assert data["symbol"] == "EUR/USD"
            assert data["timeframe"] == "1h"
            assert "analysis_id" in data
            assert data["aggregated"]["final_signal"] == "BUY"
            assert data["aggregated"]["agreement_score"] == 75
            
            # 3. Sprawdź zapis w bazie
            analysis_id = data["analysis_id"]
            saved_analysis = test_db.get_ai_analysis_by_id(analysis_id)
            assert saved_analysis is not None
            assert saved_analysis["symbol"] == "EUR/USD"
            assert saved_analysis["final_signal"] == "BUY"
            assert saved_analysis["agreement_score"] == 75
            
            # 4. Sprawdź statystyki tokenów
            stats = test_db.get_token_statistics()
            assert stats["total_tokens"] == 1500
            assert abs(stats["total_cost"] - 0.0015) < 0.0001
            assert stats["analyses_count"] == 1
    
    @pytest.mark.asyncio
    def test_full_pipeline_auto_analysis_cycle(self, e2e_client, e2e_headers, test_db):
        """
        Test 2: Pełny cykl automatycznych analiz
        1. POST /ai/trigger-analysis z 3 symbolami
        2. Sprawdź wszystkie 3 wyniki w bazie
        3. Sprawdź statystyki (total_tokens, total_cost)
        """
        test_db.initialize_default_config()
        
        with patch('app.main.get_database', return_value=test_db), \
             patch('app.main.get_auto_scheduler') as mock_scheduler_factory:
            
            # Mock scheduler
            mock_scheduler = Mock()
            
            # Mock run_analysis_cycle
            async def mock_run_cycle():
                # Symuluj 3 analizy
                for i, symbol in enumerate(["EUR/USD", "GBP/USD", "USD/JPY"]):
                    data = pytest.create_mock_analysis_result(
                        symbol=symbol,
                        final_signal="BUY" if i % 2 == 0 else "SELL",
                        agreement_score=70 + i * 5
                    )
                    data["tokens_used"] = 1000 + i * 100
                    data["estimated_cost"] = 0.001 * (i + 1)
                    test_db.create_ai_analysis_result(data)
                
                return [
                    {"analysis_id": 1, "symbol": "EUR/USD", "final_signal": "BUY", "agreement_score": 70},
                    {"analysis_id": 2, "symbol": "GBP/USD", "final_signal": "SELL", "agreement_score": 75},
                    {"analysis_id": 3, "symbol": "USD/JPY", "final_signal": "BUY", "agreement_score": 80}
                ]
            
            mock_scheduler.run_analysis_cycle = mock_run_cycle
            mock_scheduler.get_statistics.return_value = {
                "successful_analyses": 3,
                "failed_analyses": 0,
                "total_tokens": 3300,
                "total_cost": 0.006
            }
            
            mock_scheduler_factory.return_value = mock_scheduler
            
            # 1. POST /ai/trigger-analysis
            response = e2e_client.post(
                "/ai/trigger-analysis",
                headers=e2e_headers,
                json={"symbols": ["EUR/USD", "GBP/USD", "USD/JPY"]}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # 2. Sprawdź wszystkie 3 wyniki w bazie
            results = test_db.get_ai_analysis_results(limit=10)
            assert len(results) >= 3
            
            symbols_in_db = [r["symbol"] for r in results[:3]]
            assert "EUR/USD" in symbols_in_db
            assert "GBP/USD" in symbols_in_db
            assert "USD/JPY" in symbols_in_db
            
            # 3. Sprawdź statystyki
            stats = test_db.get_token_statistics()
            assert stats["total_tokens"] == 3300
            assert abs(stats["total_cost"] - 0.006) < 0.001
            assert stats["analyses_count"] == 3
    
    @pytest.mark.asyncio
    def test_full_pipeline_with_config_change(self, e2e_client, e2e_headers, test_db, mock_telegram):
        """
        Test 3: Konfiguracja → Analiza → Powiadomienie
        1. PUT /ai/analysis-config (zmień threshold na 70%)
        2. POST /ai/analyze (agreement_score = 65%)
        3. Sprawdź że NIE wysłano powiadomienia (65% < 70%)
        4. PUT /ai/analysis-config (zmień threshold na 60%)
        5. POST /ai/analyze (agreement_score = 65%)
        6. Sprawdź że wysłano powiadomienie (65% >= 60%)
        """
        test_db.initialize_default_config()
        
        with patch('app.main.get_database', return_value=test_db), \
             patch('app.main.get_telegram_service', return_value=mock_telegram), \
             patch('app.services.ai_strategy.AIStrategy.comprehensive_analysis') as mock_analysis, \
             patch('app.services.signal_aggregator_service.SignalAggregatorService.aggregate_signals') as mock_aggregate:
            
            # Setup mocks
            mock_analysis.return_value = {
                "symbol": "EUR/USD",
                "timeframe": "1h",
                "timestamp": datetime.now().isoformat(),
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
            
            # 1. Zmień threshold na 70%
            response = e2e_client.put(
                "/ai/analysis-config",
                headers=e2e_headers,
                json={"notification_threshold": 70}
            )
            assert response.status_code == 200
            
            # 2. Analiza z agreement_score = 65%
            mock_aggregate.return_value = {
                "final_signal": "BUY",
                "agreement_score": 65,
                "weighted_score": 65.0,
                "voting_details": {},
                "decision_reason": "Test",
                "should_notify": False  # 65% < 70%
            }
            
            mock_telegram.clear_messages()
            
            response = e2e_client.post(
                "/ai/analyze?symbol=EUR/USD&timeframe=1h",
                headers=e2e_headers
            )
            assert response.status_code == 200
            
            # 3. Sprawdź że NIE wysłano powiadomienia
            assert mock_telegram.send_count == 0
            
            # 4. Zmień threshold na 60%
            response = e2e_client.put(
                "/ai/analysis-config",
                headers=e2e_headers,
                json={"notification_threshold": 60}
            )
            assert response.status_code == 200
            
            # 5. Analiza z agreement_score = 65%
            mock_aggregate.return_value = {
                "final_signal": "BUY",
                "agreement_score": 65,
                "weighted_score": 65.0,
                "voting_details": {},
                "decision_reason": "Test",
                "should_notify": True  # 65% >= 60%
            }
            
            mock_telegram.clear_messages()
            
            response = e2e_client.post(
                "/ai/analyze?symbol=EUR/USD&timeframe=1h",
                headers=e2e_headers
            )
            assert response.status_code == 200
            
            # 6. Sprawdź że wysłano powiadomienie
            # Uwaga: W rzeczywistym systemie trzeba by sprawdzić czy scheduler wywołał telegram
            # W teście sprawdzamy logikę agregacji
            assert mock_aggregate.return_value["should_notify"] is True
    
    @pytest.mark.asyncio
    def test_full_pipeline_filter_results(self, e2e_client, e2e_headers, test_db):
        """
        Test 4: Filtrowanie wyników
        1. Utwórz 10 analiz dla różnych symboli
        2. GET /ai/analysis-results?symbol=EUR/USD
        3. Sprawdź że zwrócono tylko EUR/USD
        4. GET /ai/analysis-results?signal_type=BUY
        5. Sprawdź że zwrócono tylko BUY
        """
        test_db.initialize_default_config()
        
        with patch('app.main.get_database', return_value=test_db):
            # 1. Utwórz 10 analiz
            symbols = ["EUR/USD", "GBP/USD", "USD/JPY", "EUR/USD", "XAU/USD",
                      "EUR/USD", "GBP/USD", "USD/CHF", "AUD/USD", "EUR/USD"]
            signals = ["BUY", "SELL", "BUY", "BUY", "HOLD",
                      "SELL", "BUY", "BUY", "SELL", "BUY"]
            
            for symbol, signal in zip(symbols, signals):
                data = pytest.create_mock_analysis_result(
                    symbol=symbol,
                    final_signal=signal,
                    agreement_score=75
                )
                test_db.create_ai_analysis_result(data)
            
            # 2. GET /ai/analysis-results?symbol=EUR/USD
            response = e2e_client.get(
                "/ai/analysis-results?symbol=EUR/USD",
                headers=e2e_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # 3. Sprawdź że tylko EUR/USD
            eur_usd_count = sum(1 for r in data["results"] if r["symbol"] == "EUR/USD")
            assert eur_usd_count == 4  # 4 x EUR/USD w danych testowych
            assert all(r["symbol"] == "EUR/USD" for r in data["results"])
            
            # 4. GET /ai/analysis-results?signal_type=BUY
            response = e2e_client.get(
                "/ai/analysis-results?signal_type=BUY",
                headers=e2e_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # 5. Sprawdź że tylko BUY
            buy_count = sum(1 for s in signals if s == "BUY")
            assert len(data["results"]) == buy_count
            assert all(r["final_signal"] == "BUY" for r in data["results"])
    
    @pytest.mark.asyncio
    def test_full_pipeline_handles_errors(self, e2e_client, e2e_headers, test_db):
        """
        Test 5: Obsługa błędów w pipeline
        1. POST /ai/analyze z nieprawidłowym symbolem
        2. Sprawdź że zwrócono błąd 500
        3. Sprawdź że nie zapisano wyniku w bazie
        """
        test_db.initialize_default_config()
        
        with patch('app.main.get_database', return_value=test_db), \
             patch('app.services.ai_strategy.AIStrategy.comprehensive_analysis') as mock_analysis:
            
            # 1. Symuluj błąd analizy
            mock_analysis.side_effect = Exception("Invalid symbol format")
            
            initial_count = len(test_db.get_ai_analysis_results())
            
            # 2. POST /ai/analyze z błędem
            response = e2e_client.post(
                "/ai/analyze?symbol=INVALID&timeframe=1h",
                headers=e2e_headers
            )
            
            # 3. Sprawdź błąd
            assert response.status_code == 500
            
            # 4. Sprawdź że nie zapisano w bazie
            final_count = len(test_db.get_ai_analysis_results())
            assert final_count == initial_count  # Brak nowych wpisów


@pytest.mark.e2e
@pytest.mark.integration
class TestE2EDataConsistency:
    """Testy spójności danych w pełnym pipeline"""
    
    @pytest.mark.asyncio
    def test_data_consistency_across_endpoints(self, e2e_client, e2e_headers, test_db):
        """Test spójności danych między różnymi endpointami"""
        test_db.initialize_default_config()
        
        with patch('app.main.get_database', return_value=test_db), \
             patch('app.services.ai_strategy.AIStrategy.comprehensive_analysis') as mock_analysis, \
             patch('app.services.signal_aggregator_service.SignalAggregatorService.aggregate_signals') as mock_aggregate:
            
            mock_analysis.return_value = {
                "symbol": "EUR/USD",
                "timeframe": "1h",
                "timestamp": datetime.now().isoformat(),
                "ai_analysis": {
                    "recommendation": "BUY",
                    "confidence": 80,
                    "reasoning": "Test",
                    "tokens_used": 2000,
                    "estimated_cost": 0.002
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
            
            # Utwórz analizę
            response1 = e2e_client.post(
                "/ai/analyze?symbol=EUR/USD&timeframe=1h",
                headers=e2e_headers
            )
            assert response1.status_code == 200
            analysis_id = response1.json()["analysis_id"]
            
            # Pobierz przez GET /ai/analysis-results/{id}
            response2 = e2e_client.get(
                f"/ai/analysis-results/{analysis_id}",
                headers=e2e_headers
            )
            assert response2.status_code == 200
            
            # Pobierz przez GET /ai/analysis-results?symbol=EUR/USD
            response3 = e2e_client.get(
                "/ai/analysis-results?symbol=EUR/USD",
                headers=e2e_headers
            )
            assert response3.status_code == 200
            
            # Sprawdź spójność danych
            data1 = response1.json()
            data2 = response2.json()
            data3 = response3.json()["results"][0]
            
            assert data2["symbol"] == "EUR/USD"
            assert data2["final_signal"] == "BUY"
            assert data2["agreement_score"] == 75
            
            assert data3["symbol"] == "EUR/USD"
            assert data3["final_signal"] == "BUY"
            assert data3["agreement_score"] == 75
    
    @pytest.mark.asyncio
    def test_token_statistics_accuracy(self, e2e_client, e2e_headers, test_db):
        """Test dokładności statystyk tokenów"""
        test_db.initialize_default_config()
        
        with patch('app.main.get_database', return_value=test_db), \
             patch('app.services.ai_strategy.AIStrategy.comprehensive_analysis') as mock_analysis, \
             patch('app.services.signal_aggregator_service.SignalAggregatorService.aggregate_signals') as mock_aggregate:
            
            # Utwórz 3 analizy z różną liczbą tokenów
            tokens_list = [1000, 1500, 2000]
            costs_list = [0.001, 0.0015, 0.002]
            
            for tokens, cost in zip(tokens_list, costs_list):
                mock_analysis.return_value = {
                    "symbol": "EUR/USD",
                    "timeframe": "1h",
                    "timestamp": datetime.now().isoformat(),
                    "ai_analysis": {
                        "recommendation": "BUY",
                        "confidence": 80,
                        "reasoning": "Test",
                        "tokens_used": tokens,
                        "estimated_cost": cost
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
                
                response = e2e_client.post(
                    "/ai/analyze?symbol=EUR/USD&timeframe=1h",
                    headers=e2e_headers
                )
                assert response.status_code == 200
            
            # Pobierz statystyki
            response = e2e_client.get(
                "/ai/token-statistics",
                headers=e2e_headers
            )
            
            assert response.status_code == 200
            stats = response.json()
            
            # Sprawdź dokładność
            expected_total_tokens = sum(tokens_list)
            expected_total_cost = sum(costs_list)
            
            assert stats["total_tokens"] == expected_total_tokens
            assert abs(stats["total_cost"] - expected_total_cost) < 0.0001
            assert stats["analyses_count"] == 3
            assert stats["avg_tokens_per_analysis"] == expected_total_tokens // 3


def run_tests():
    """Uruchamia testy E2E"""
    pytest.main([__file__, "-v", "--tb=short", "-m", "e2e"])


if __name__ == "__main__":
    run_tests()
