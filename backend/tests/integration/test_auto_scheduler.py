"""
Testy jednostkowe dla AutoAnalysisScheduler
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
import json

from app.services.auto_analysis_scheduler import AutoAnalysisScheduler


@pytest.mark.unit
@pytest.mark.integration
class TestAutoAnalysisSchedulerInitialization:
    """Testy inicjalizacji schedulera"""
    
    def test_scheduler_initialization(self, test_db, mock_telegram):
        """Test podstawowej inicjalizacji schedulera"""
        scheduler = AutoAnalysisScheduler(
            database=test_db,
            telegram=mock_telegram,
            interval_minutes=15
        )
        
        assert scheduler.db == test_db
        assert scheduler.telegram == mock_telegram
        assert scheduler.interval == 15
        assert len(scheduler.symbols) > 0
    
    def test_scheduler_with_custom_interval(self, test_db, mock_telegram):
        """Test inicjalizacji z niestandardowym interwałem"""
        scheduler = AutoAnalysisScheduler(
            database=test_db,
            telegram=mock_telegram,
            interval_minutes=30
        )
        
        assert scheduler.interval == 30
    
    def test_get_enabled_symbols(self, test_db, mock_telegram):
        """Test pobierania listy symboli do analizy"""
        scheduler = AutoAnalysisScheduler(
            database=test_db,
            telegram=mock_telegram,
            interval_minutes=15
        )
        
        symbols = scheduler._get_enabled_symbols()
        
        assert isinstance(symbols, list)
        assert len(symbols) > 0
        # Sprawdź czy symbole mają poprawny format
        for symbol in symbols:
            assert "/" in symbol


@pytest.mark.unit
@pytest.mark.integration
class TestAutoAnalysisSchedulerSingleAnalysis:
    """Testy pojedynczej analizy symbolu"""
    
    @pytest.mark.asyncio
    async def test_analyze_symbol_success(self, test_db, mock_telegram):
        """Test pomyślnej analizy symbolu"""
        scheduler = AutoAnalysisScheduler(
            database=test_db,
            telegram=mock_telegram,
            interval_minutes=15
        )
        
        # Mock AIStrategy i SignalAggregator
        with patch.object(scheduler.ai_strategy, 'comprehensive_analysis') as mock_analysis, \
             patch.object(scheduler.aggregator, 'aggregate_signals') as mock_aggregate:
            
            # Przygotuj mock wyniki
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
            
            mock_aggregate.return_value = {
                "final_signal": "BUY",
                "agreement_score": 75,
                "voting_details": {},
                "decision_reason": "Test",
                "should_notify": True
            }
            
            result = await scheduler.analyze_symbol("EUR/USD", "1h")
            
            assert result is not None
            assert "analysis_id" in result
            assert result["symbol"] == "EUR/USD"
            assert result["final_signal"] == "BUY"
    
    @pytest.mark.asyncio
    async def test_analyze_symbol_saves_to_database(self, test_db, mock_telegram):
        """Test czy analiza jest zapisywana do bazy"""
        test_db.initialize_default_config()
        
        scheduler = AutoAnalysisScheduler(
            database=test_db,
            telegram=mock_telegram,
            interval_minutes=15
        )
        
        with patch.object(scheduler.ai_strategy, 'comprehensive_analysis') as mock_analysis, \
             patch.object(scheduler.aggregator, 'aggregate_signals') as mock_aggregate:
            
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
            
            mock_aggregate.return_value = {
                "final_signal": "BUY",
                "agreement_score": 75,
                "voting_details": {},
                "decision_reason": "Test",
                "should_notify": False
            }
            
            result = await scheduler.analyze_symbol("EUR/USD", "1h")
            
            # Sprawdź czy zapisano w bazie
            saved_analysis = test_db.get_ai_analysis_by_id(result["analysis_id"])
            assert saved_analysis is not None
            assert saved_analysis["symbol"] == "EUR/USD"
    
    @pytest.mark.asyncio
    async def test_analyze_symbol_sends_notification_when_threshold_met(
        self, test_db, mock_telegram
    ):
        """Test wysyłania powiadomienia gdy próg jest spełniony"""
        test_db.initialize_default_config()
        
        scheduler = AutoAnalysisScheduler(
            database=test_db,
            telegram=mock_telegram,
            interval_minutes=15
        )
        
        with patch.object(scheduler.ai_strategy, 'comprehensive_analysis') as mock_analysis, \
             patch.object(scheduler.aggregator, 'aggregate_signals') as mock_aggregate:
            
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
            
            mock_aggregate.return_value = {
                "final_signal": "BUY",
                "agreement_score": 75,
                "voting_details": {},
                "decision_reason": "Test decision",
                "should_notify": True
            }
            
            await scheduler.analyze_symbol("EUR/USD", "1h")
            
            # Sprawdź czy wysłano powiadomienie
            assert mock_telegram.send_count > 0
            assert "EUR/USD" in mock_telegram.get_last_message()
    
    @pytest.mark.asyncio
    async def test_analyze_symbol_no_notification_below_threshold(
        self, test_db, mock_telegram
    ):
        """Test braku powiadomienia gdy próg nie jest spełniony"""
        test_db.initialize_default_config()
        
        scheduler = AutoAnalysisScheduler(
            database=test_db,
            telegram=mock_telegram,
            interval_minutes=15
        )
        
        with patch.object(scheduler.ai_strategy, 'comprehensive_analysis') as mock_analysis, \
             patch.object(scheduler.aggregator, 'aggregate_signals') as mock_aggregate:
            
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
            
            mock_aggregate.return_value = {
                "final_signal": "BUY",
                "agreement_score": 45,  # Poniżej progu 60%
                "voting_details": {},
                "decision_reason": "Test",
                "should_notify": False
            }
            
            await scheduler.analyze_symbol("EUR/USD", "1h")
            
            # Sprawdź że NIE wysłano powiadomienia
            assert mock_telegram.send_count == 0
    
    @pytest.mark.asyncio
    async def test_analyze_symbol_handles_api_error(self, test_db, mock_telegram):
        """Test obsługi błędu API podczas analizy"""
        scheduler = AutoAnalysisScheduler(
            database=test_db,
            telegram=mock_telegram,
            interval_minutes=15
        )
        
        with patch.object(scheduler.ai_strategy, 'comprehensive_analysis') as mock_analysis:
            # Symuluj błąd API
            mock_analysis.side_effect = Exception("API Error")
            
            # Nie powinno rzucić wyjątku
            result = await scheduler.analyze_symbol("EUR/USD", "1h")
            
            # Może zwrócić None lub pusty wynik
            assert result is None or "error" in result


@pytest.mark.unit
@pytest.mark.integration
class TestAutoAnalysisSchedulerCycle:
    """Testy cyklu analiz dla wielu symboli"""
    
    @pytest.mark.asyncio
    async def test_run_analysis_cycle_all_symbols(self, test_db, mock_telegram):
        """Test uruchomienia cyklu dla wszystkich symboli"""
        scheduler = AutoAnalysisScheduler(
            database=test_db,
            telegram=mock_telegram,
            interval_minutes=15
        )
        
        # Ogranicz do 2 symboli dla szybkości testu
        scheduler.symbols = ["EUR/USD", "GBP/USD"]
        
        with patch.object(scheduler, 'analyze_symbol') as mock_analyze:
            mock_analyze.return_value = {
                "analysis_id": 1,
                "symbol": "EUR/USD",
                "final_signal": "BUY",
                "agreement_score": 75
            }
            
            results = await scheduler.run_analysis_cycle()
            
            assert len(results) == 2
            assert mock_analyze.call_count == 2
    
    @pytest.mark.asyncio
    async def test_run_analysis_cycle_custom_symbols(self, test_db, mock_telegram):
        """Test cyklu z niestandardową listą symboli"""
        scheduler = AutoAnalysisScheduler(
            database=test_db,
            telegram=mock_telegram,
            interval_minutes=15
        )
        
        custom_symbols = ["XAU/USD", "XAG/USD"]
        scheduler.symbols = custom_symbols
        
        with patch.object(scheduler, 'analyze_symbol') as mock_analyze:
            mock_analyze.return_value = {"analysis_id": 1}
            
            results = await scheduler.run_analysis_cycle()
            
            assert len(results) == 2
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_run_analysis_cycle_with_rate_limiting(self, test_db, mock_telegram):
        """Test pauzy między analizami (rate limiting)"""
        import time
        
        scheduler = AutoAnalysisScheduler(
            database=test_db,
            telegram=mock_telegram,
            interval_minutes=15
        )
        
        scheduler.symbols = ["EUR/USD", "GBP/USD"]
        
        with patch.object(scheduler, 'analyze_symbol') as mock_analyze:
            mock_analyze.return_value = {"analysis_id": 1}
            
            start_time = time.time()
            await scheduler.run_analysis_cycle()
            duration = time.time() - start_time
            
            # Powinno być co najmniej 2 sekundy (1 pauza między 2 symbolami)
            assert duration >= 2.0
    
    @pytest.mark.asyncio
    async def test_run_analysis_cycle_continues_on_error(self, test_db, mock_telegram):
        """Test że cykl kontynuuje po błędzie jednego symbolu"""
        scheduler = AutoAnalysisScheduler(
            database=test_db,
            telegram=mock_telegram,
            interval_minutes=15
        )
        
        scheduler.symbols = ["EUR/USD", "GBP/USD", "USD/JPY"]
        
        call_count = 0
        
        async def mock_analyze_with_error(symbol, timeframe):
            nonlocal call_count
            call_count += 1
            if symbol == "GBP/USD":
                raise Exception("Error for GBP/USD")
            return {"analysis_id": call_count, "symbol": symbol}
        
        with patch.object(scheduler, 'analyze_symbol', side_effect=mock_analyze_with_error):
            results = await scheduler.run_analysis_cycle()
            
            # Powinno przeanalizować wszystkie 3 symbole mimo błędu
            assert call_count == 3
            # Wyniki powinny zawierać tylko udane analizy
            assert len(results) >= 2
    
    @pytest.mark.asyncio
    async def test_run_analysis_cycle_statistics(self, test_db, mock_telegram):
        """Test zbierania statystyk po cyklu"""
        test_db.initialize_default_config()
        
        scheduler = AutoAnalysisScheduler(
            database=test_db,
            telegram=mock_telegram,
            interval_minutes=15
        )
        
        scheduler.symbols = ["EUR/USD", "GBP/USD"]
        
        with patch.object(scheduler.ai_strategy, 'comprehensive_analysis') as mock_analysis, \
             patch.object(scheduler.aggregator, 'aggregate_signals') as mock_aggregate:
            
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
            
            mock_aggregate.return_value = {
                "final_signal": "BUY",
                "agreement_score": 75,
                "voting_details": {},
                "decision_reason": "Test",
                "should_notify": False
            }
            
            results = await scheduler.run_analysis_cycle()
            
            # Sprawdź statystyki w bazie
            stats = test_db.get_token_statistics()
            assert stats["analyses_count"] == 2
            assert stats["total_tokens"] == 2000  # 2 x 1000


@pytest.mark.unit
class TestAutoAnalysisSchedulerErrorHandling:
    """Testy obsługi błędów"""
    
    @pytest.mark.asyncio
    async def test_analyze_symbol_invalid_symbol(self, test_db, mock_telegram):
        """Test analizy z nieprawidłowym symbolem"""
        scheduler = AutoAnalysisScheduler(
            database=test_db,
            telegram=mock_telegram,
            interval_minutes=15
        )
        
        with patch.object(scheduler.ai_strategy, 'comprehensive_analysis') as mock_analysis:
            mock_analysis.side_effect = ValueError("Invalid symbol")
            
            result = await scheduler.analyze_symbol("INVALID", "1h")
            
            # Powinno obsłużyć błąd gracefully
            assert result is None or "error" in result
    
    @pytest.mark.asyncio
    async def test_analyze_symbol_network_timeout(self, test_db, mock_telegram):
        """Test obsługi timeoutu sieciowego"""
        scheduler = AutoAnalysisScheduler(
            database=test_db,
            telegram=mock_telegram,
            interval_minutes=15
        )
        
        with patch.object(scheduler.ai_strategy, 'comprehensive_analysis') as mock_analysis:
            mock_analysis.side_effect = asyncio.TimeoutError("Network timeout")
            
            result = await scheduler.analyze_symbol("EUR/USD", "1h")
            
            assert result is None or "error" in result
    
    @pytest.mark.asyncio
    async def test_analyze_symbol_database_error(self, test_db, mock_telegram):
        """Test obsługi błędu bazy danych"""
        scheduler = AutoAnalysisScheduler(
            database=test_db,
            telegram=mock_telegram,
            interval_minutes=15
        )
        
        with patch.object(scheduler.ai_strategy, 'comprehensive_analysis') as mock_analysis, \
             patch.object(scheduler.aggregator, 'aggregate_signals') as mock_aggregate, \
             patch.object(test_db, 'create_ai_analysis_result') as mock_db:
            
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
            
            mock_aggregate.return_value = {
                "final_signal": "BUY",
                "agreement_score": 75,
                "voting_details": {},
                "decision_reason": "Test",
                "should_notify": False
            }
            
            # Symuluj błąd bazy danych
            mock_db.side_effect = Exception("Database error")
            
            result = await scheduler.analyze_symbol("EUR/USD", "1h")
            
            # Powinno obsłużyć błąd
            assert result is None or "error" in result


@pytest.mark.unit
class TestAutoAnalysisSchedulerStatistics:
    """Testy statystyk schedulera"""
    
    @pytest.mark.asyncio
    async def test_get_statistics_after_cycle(self, test_db, mock_telegram):
        """Test pobierania statystyk po cyklu analiz"""
        test_db.initialize_default_config()
        
        scheduler = AutoAnalysisScheduler(
            database=test_db,
            telegram=mock_telegram,
            interval_minutes=15
        )
        
        scheduler.symbols = ["EUR/USD"]
        
        with patch.object(scheduler.ai_strategy, 'comprehensive_analysis') as mock_analysis, \
             patch.object(scheduler.aggregator, 'aggregate_signals') as mock_aggregate:
            
            mock_analysis.return_value = {
                "symbol": "EUR/USD",
                "timeframe": "1h",
                "timestamp": datetime.now().isoformat(),
                "ai_analysis": {
                    "recommendation": "BUY",
                    "confidence": 80,
                    "reasoning": "Test",
                    "tokens_used": 1500,
                    "estimated_cost": 0.0015
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
                "voting_details": {},
                "decision_reason": "Test",
                "should_notify": False
            }
            
            await scheduler.run_analysis_cycle()
            
            stats = scheduler.get_statistics()
            
            assert "successful_analyses" in stats
            assert "failed_analyses" in stats
            assert "total_tokens" in stats
            assert "total_cost" in stats
    
    @pytest.mark.asyncio
    async def test_statistics_token_counting(self, test_db, mock_telegram):
        """Test zliczania tokenów w statystykach"""
        test_db.initialize_default_config()
        
        scheduler = AutoAnalysisScheduler(
            database=test_db,
            telegram=mock_telegram,
            interval_minutes=15
        )
        
        scheduler.symbols = ["EUR/USD", "GBP/USD"]
        
        with patch.object(scheduler.ai_strategy, 'comprehensive_analysis') as mock_analysis, \
             patch.object(scheduler.aggregator, 'aggregate_signals') as mock_aggregate:
            
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
                "voting_details": {},
                "decision_reason": "Test",
                "should_notify": False
            }
            
            await scheduler.run_analysis_cycle()
            
            db_stats = test_db.get_token_statistics()
            assert db_stats["total_tokens"] == 4000  # 2 x 2000
            assert abs(db_stats["total_cost"] - 0.004) < 0.0001
    
    @pytest.mark.asyncio
    async def test_statistics_success_failure_ratio(self, test_db, mock_telegram):
        """Test stosunku udanych do nieudanych analiz"""
        scheduler = AutoAnalysisScheduler(
            database=test_db,
            telegram=mock_telegram,
            interval_minutes=15
        )
        
        scheduler.symbols = ["EUR/USD", "GBP/USD", "USD/JPY"]
        
        call_count = 0
        
        async def mock_analyze_mixed(symbol, timeframe):
            nonlocal call_count
            call_count += 1
            if symbol == "GBP/USD":
                return None  # Błąd
            return {"analysis_id": call_count, "symbol": symbol}
        
        with patch.object(scheduler, 'analyze_symbol', side_effect=mock_analyze_mixed):
            results = await scheduler.run_analysis_cycle()
            
            stats = scheduler.get_statistics()
            
            # 2 udane, 1 nieudana
            assert stats["successful_analyses"] == 2
            assert stats["failed_analyses"] == 1


def run_tests():
    """Uruchamia testy schedulera"""
    pytest.main([__file__, "-v", "--tb=short"])


if __name__ == "__main__":
    run_tests()
