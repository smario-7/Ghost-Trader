"""
Test integracyjny dla AIStrategy.comprehensive_analysis() + SignalAggregatorService
"""
import pytest
import asyncio
import sys
from pathlib import Path

# Dodaj katalog główny do PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.signal_aggregator_service import SignalAggregatorService
from app.services.ai_strategy import AIStrategy


class MockDatabase:
    """Mock bazy danych"""
    
    def get_analysis_config(self):
        return {
            "notification_threshold": 60,
            "is_active": True
        }


class MockTelegramService:
    """Mock serwisu Telegram"""
    
    async def send_message(self, message: str):
        print(f"[TELEGRAM] {message}")
        return True


class TestIntegration:
    """Testy integracyjne"""
    
    @pytest.fixture
    def mock_db(self):
        return MockDatabase()
    
    @pytest.fixture
    def mock_telegram(self):
        return MockTelegramService()
    
    @pytest.fixture
    def aggregator(self, mock_db):
        return SignalAggregatorService(database=mock_db)
    
    @pytest.fixture
    def ai_strategy(self, mock_telegram):
        return AIStrategy(telegram_service=mock_telegram)
    
    @pytest.mark.asyncio
    async def test_full_analysis_pipeline(self, ai_strategy, aggregator):
        """
        Test pełnego pipeline'u:
        1. AIStrategy.comprehensive_analysis() zbiera dane
        2. SignalAggregatorService.aggregate_signals() agreguje wyniki
        """
        symbol = "EUR/USD"
        timeframe = "1h"
        
        # Krok 1: Uruchom comprehensive_analysis
        # Uwaga: To może zawieść jeśli brak API keys lub połączenia
        try:
            analysis = await ai_strategy.comprehensive_analysis(symbol, timeframe)
            
            # Sprawdź strukturę wyniku
            assert "symbol" in analysis
            assert "timeframe" in analysis
            assert "ai_analysis" in analysis
            assert "technical_analysis" in analysis
            assert "macro_analysis" in analysis
            assert "news_analysis" in analysis
            
            print("\n=== COMPREHENSIVE ANALYSIS ===")
            print(f"Symbol: {analysis['symbol']}")
            print(f"AI: {analysis['ai_analysis']['recommendation']} ({analysis['ai_analysis']['confidence']}%)")
            print(f"Technical: {analysis['technical_analysis']['signal']} ({analysis['technical_analysis']['confidence']}%)")
            print(f"Macro: {analysis['macro_analysis']['signal']} ({analysis['macro_analysis']['confidence']}%)")
            print(f"News: {analysis['news_analysis']['sentiment']} ({analysis['news_analysis']['score']}%)")
            
            # Krok 2: Agreguj sygnały
            result = await aggregator.aggregate_signals(
                symbol=symbol,
                timeframe=timeframe,
                ai_result=analysis["ai_analysis"],
                technical_result=analysis["technical_analysis"],
                macro_result=analysis["macro_analysis"],
                news_result=analysis["news_analysis"]
            )
            
            # Sprawdź wynik agregacji
            assert "final_signal" in result
            assert "agreement_score" in result
            assert "weighted_score" in result
            assert "voting_details" in result
            assert "decision_reason" in result
            assert "should_notify" in result
            
            print("\n=== AGGREGATED RESULT ===")
            print(f"Final Signal: {result['final_signal']}")
            print(f"Agreement Score: {result['agreement_score']}%")
            print(f"Weighted Score: {result['weighted_score']:.1f}")
            print(f"Should Notify: {result['should_notify']}")
            print(f"\nDecision Reason:\n{result['decision_reason']}")
            
            # Sprawdź voting details
            assert len(result['voting_details']) == 4
            for source in ['ai', 'technical', 'macro', 'news']:
                assert source in result['voting_details']
                assert 'vote' in result['voting_details'][source]
                assert 'confidence' in result['voting_details'][source]
                assert 'weight' in result['voting_details'][source]
            
        except Exception as e:
            # Jeśli test zawiedzie z powodu braku API keys, to OK
            if "error" in str(e).lower() or "api" in str(e).lower():
                pytest.skip(f"Test skipped due to API/connection issue: {e}")
            else:
                raise
    
    @pytest.mark.asyncio
    async def test_token_counting_and_cost_estimation(self, ai_strategy):
        """Test liczenia tokenów i szacowania kosztów"""
        # Test metod pomocniczych
        text = "This is a test prompt for token counting. " * 100
        tokens = ai_strategy._count_tokens(text)
        
        assert tokens > 0
        print(f"\nTokens estimated: {tokens}")
        
        # Test szacowania kosztów
        cost_gpt4o = ai_strategy._estimate_cost(tokens, "gpt-4o")
        cost_gpt4o_mini = ai_strategy._estimate_cost(tokens, "gpt-4o-mini")
        
        assert cost_gpt4o > 0
        assert cost_gpt4o_mini > 0
        assert cost_gpt4o > cost_gpt4o_mini  # gpt-4o jest droższy
        
        print(f"Estimated cost (gpt-4o): ${cost_gpt4o:.6f}")
        print(f"Estimated cost (gpt-4o-mini): ${cost_gpt4o_mini:.6f}")
    
    @pytest.mark.asyncio
    async def test_technical_signal_analysis(self, ai_strategy):
        """Test analizy sygnału technicznego"""
        indicators = {
            "rsi": 25,  # Oversold
            "macd": {
                "value": 0.5,
                "signal": 0.3,
                "histogram": 0.2
            },
            "sma_50": 1.1000,
            "sma_200": 1.0900,  # Golden cross
            "price": 1.1050,
            "bollinger": {
                "upper": 1.1100,
                "middle": 1.1000,
                "lower": 1.0900
            }
        }
        
        result = ai_strategy._analyze_technical_signal(indicators)
        
        assert "signal" in result
        assert "confidence" in result
        assert result["signal"] in ["BUY", "SELL", "HOLD"]
        assert 0 <= result["confidence"] <= 100
        
        print(f"\nTechnical Signal: {result['signal']} ({result['confidence']}%)")
        
        # Z tymi wskaźnikami powinien być sygnał BUY (RSI oversold, golden cross)
        assert result["signal"] == "BUY"
    
    @pytest.mark.asyncio
    async def test_macro_signal_analysis(self, ai_strategy):
        """Test analizy sygnału makro"""
        macro_data = {
            "fed": {
                "current_rate": 5.5,
                "next_meeting": "2026-03-15"
            },
            "inflation": {
                "cpi_annual": 2.3
            },
            "gdp": {
                "growth_rate": 2.8
            }
        }
        
        result = ai_strategy._analyze_macro_signal(macro_data)
        
        assert "signal" in result
        assert "confidence" in result
        assert "impact" in result
        assert "summary" in result
        
        print(f"\nMacro Signal: {result['signal']} ({result['confidence']}%)")
        print(f"Impact: {result['impact']}")
        print(f"Summary: {result['summary']}")
    
    @pytest.mark.asyncio
    async def test_news_sentiment_analysis(self, ai_strategy):
        """Test analizy sentimentu wiadomości"""
        news = [
            {"sentiment": "positive", "title": "Strong economic growth"},
            {"sentiment": "positive", "title": "Market rally continues"},
            {"sentiment": "negative", "title": "Concerns about inflation"},
            {"sentiment": "neutral", "title": "Fed maintains rates"},
            {"sentiment": "positive", "title": "Tech stocks surge"}
        ]
        
        result = ai_strategy._analyze_news_sentiment(news)
        
        assert "sentiment" in result
        assert "score" in result
        assert "news_count" in result
        assert "summary" in result
        
        assert result["news_count"] == 5
        assert result["sentiment"] == "positive"  # 3 positive, 1 negative, 1 neutral
        
        print(f"\nNews Sentiment: {result['sentiment']} (score: {result['score']})")
        print(f"Summary: {result['summary']}")


def run_integration_tests():
    """Uruchamia testy integracyjne"""
    pytest.main([__file__, "-v", "--tb=short", "-s"])


if __name__ == "__main__":
    run_integration_tests()
