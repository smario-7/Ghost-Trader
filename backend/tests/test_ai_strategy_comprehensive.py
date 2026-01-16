"""
Testy jednostkowe dla AIStrategy.comprehensive_analysis() i metod pomocniczych
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

# Dodaj katalog do PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.ai_strategy import AIStrategy


class TestTokenCounting:
    """Testy liczenia tokenów i szacowania kosztów"""
    
    def setup_method(self):
        """Przygotowanie przed każdym testem"""
        self.strategy = AIStrategy(telegram_service=None)
    
    def test_count_tokens_short_text(self):
        """Test liczenia tokenów dla krótkiego tekstu"""
        text = "Analyze EUR/USD"
        tokens = self.strategy._count_tokens(text)
        
        # Powinno być ~4 tokeny + 300 buffer
        assert tokens > 300
        assert tokens < 400
    
    def test_count_tokens_medium_text(self):
        """Test liczenia tokenów dla średniego tekstu"""
        text = "Analyze EUR/USD with technical indicators and macro data" * 10
        tokens = self.strategy._count_tokens(text)
        
        # Przybliżenie: len(text) // 4 + 300
        expected_min = len(text) // 4 + 200
        expected_max = len(text) // 4 + 400
        
        assert tokens >= expected_min
        assert tokens <= expected_max
    
    def test_count_tokens_long_text(self):
        """Test liczenia tokenów dla długiego tekstu"""
        text = "A" * 10000  # 10k znaków
        tokens = self.strategy._count_tokens(text)
        
        # Powinno być ~2500 tokenów + buffer
        assert tokens > 2500
        assert tokens < 3000
    
    def test_count_tokens_empty_text(self):
        """Test liczenia tokenów dla pustego tekstu"""
        tokens = self.strategy._count_tokens("")
        
        # Tylko buffer
        assert tokens == 300
    
    def test_estimate_cost_gpt4o(self):
        """Test szacowania kosztów dla gpt-4o"""
        tokens = 1000
        cost = self.strategy._estimate_cost(tokens, "gpt-4o")
        
        # gpt-4o: input $0.005/1K, output $0.015/1K
        # 60% input (600 tokens), 40% output (400 tokens)
        # (600 * 0.005 / 1000) + (400 * 0.015 / 1000) = 0.003 + 0.006 = 0.009
        expected = 0.009
        
        assert abs(cost - expected) < 0.001
    
    def test_estimate_cost_gpt4o_mini(self):
        """Test szacowania kosztów dla gpt-4o-mini"""
        tokens = 1000
        cost = self.strategy._estimate_cost(tokens, "gpt-4o-mini")
        
        # gpt-4o-mini: input $0.00015/1K, output $0.0006/1K
        # (600 * 0.00015 / 1000) + (400 * 0.0006 / 1000) = 0.00009 + 0.00024 = 0.00033
        expected = 0.00033
        
        assert abs(cost - expected) < 0.00001
    
    def test_estimate_cost_different_models(self):
        """Test szacowania kosztów dla różnych modeli"""
        tokens = 2000
        
        models = ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"]
        costs = []
        
        for model in models:
            cost = self.strategy._estimate_cost(tokens, model)
            costs.append(cost)
            assert cost > 0
        
        # gpt-4o-mini powinien być najtańszy
        assert costs[1] < costs[0]  # mini < 4o
        assert costs[1] < costs[2]  # mini < turbo


class TestTechnicalSignalAnalysis:
    """Testy analizy wskaźników technicznych"""
    
    def setup_method(self):
        """Przygotowanie przed każdym testem"""
        self.strategy = AIStrategy(telegram_service=None)
    
    def test_analyze_technical_signal_buy_oversold_rsi(self):
        """Test sygnału BUY dla oversold RSI"""
        indicators = {
            "rsi": 25,  # Oversold
            "macd": {"value": 0.5, "signal": 0.3, "histogram": 0.2},
            "sma_50": 1.1000,
            "sma_200": 1.0900,
            "price": 1.1050,
            "bollinger": {"upper": 1.1100, "middle": 1.1000, "lower": 1.0900}
        }
        
        result = self.strategy._analyze_technical_signal(indicators)
        
        assert result["signal"] == "BUY"
        assert result["confidence"] > 50
        assert "indicators" in result
    
    def test_analyze_technical_signal_sell_overbought_rsi(self):
        """Test sygnału SELL dla overbought RSI"""
        indicators = {
            "rsi": 75,  # Overbought
            "macd": {"value": -0.3, "signal": -0.1, "histogram": -0.2},
            "sma_50": 1.0900,
            "sma_200": 1.1000,
            "price": 1.0850,
            "bollinger": {"upper": 1.1100, "middle": 1.1000, "lower": 1.0900}
        }
        
        result = self.strategy._analyze_technical_signal(indicators)
        
        assert result["signal"] == "SELL"
        assert result["confidence"] > 50
    
    def test_analyze_technical_signal_hold_neutral(self):
        """Test sygnału HOLD dla neutralnych wskaźników"""
        indicators = {
            "rsi": 50,  # Neutral
            "macd": {"value": 0.0, "signal": 0.0, "histogram": 0.0},
            "sma_50": 1.1000,
            "sma_200": 1.1000,
            "price": 1.1000,
            "bollinger": {"upper": 1.1100, "middle": 1.1000, "lower": 1.0900}
        }
        
        result = self.strategy._analyze_technical_signal(indicators)
        
        assert result["signal"] == "HOLD"
        assert result["confidence"] >= 0
        assert result["confidence"] <= 100
    
    def test_analyze_technical_signal_empty_indicators(self):
        """Test dla pustych wskaźników"""
        result = self.strategy._analyze_technical_signal({})
        
        assert result["signal"] == "HOLD"
        assert result["confidence"] == 0
        assert result["indicators"] == {}
    
    def test_analyze_technical_signal_golden_cross(self):
        """Test dla golden cross (SMA50 > SMA200)"""
        indicators = {
            "rsi": 50,
            "macd": {"value": 0.0, "signal": 0.0, "histogram": 0.0},
            "sma_50": 1.1000,  # Wyżej
            "sma_200": 1.0900,  # Niżej
            "price": 1.1050,
            "bollinger": {"upper": 1.1100, "middle": 1.1000, "lower": 1.0900}
        }
        
        result = self.strategy._analyze_technical_signal(indicators)
        
        # Golden cross powinien wspierać BUY
        assert result["signal"] in ["BUY", "HOLD"]


class TestMacroSignalAnalysis:
    """Testy analizy danych makroekonomicznych"""
    
    def setup_method(self):
        """Przygotowanie przed każdym testem"""
        self.strategy = AIStrategy(telegram_service=None)
    
    def test_analyze_macro_signal_positive(self):
        """Test pozytywnego sygnału makro"""
        macro_data = {
            "fed": {"current_rate": 5.5},
            "inflation": {"cpi_annual": 2.0},  # Niska inflacja
            "gdp": {"growth_rate": 3.0}  # Silny wzrost
        }
        
        result = self.strategy._analyze_macro_signal(macro_data)
        
        assert result["signal"] == "BUY"
        assert result["impact"] == "positive"
        assert result["confidence"] > 50
        assert "summary" in result
    
    def test_analyze_macro_signal_negative(self):
        """Test negatywnego sygnału makro"""
        macro_data = {
            "fed": {"current_rate": 1.5},  # Niskie stopy
            "inflation": {"cpi_annual": 5.0},  # Wysoka inflacja
            "gdp": {"growth_rate": 0.5}  # Słaby wzrost
        }
        
        result = self.strategy._analyze_macro_signal(macro_data)
        
        assert result["signal"] == "SELL"
        assert result["impact"] == "negative"
        assert result["confidence"] > 50
    
    def test_analyze_macro_signal_neutral(self):
        """Test neutralnego sygnału makro"""
        macro_data = {
            "fed": {"current_rate": 3.0},
            "inflation": {"cpi_annual": 3.0},
            "gdp": {"growth_rate": 2.0}
        }
        
        result = self.strategy._analyze_macro_signal(macro_data)
        
        assert result["signal"] == "HOLD"
        assert result["impact"] == "neutral"
        assert result["confidence"] == 50
    
    def test_analyze_macro_signal_empty(self):
        """Test dla pustych danych makro"""
        result = self.strategy._analyze_macro_signal({})
        
        assert result["signal"] == "HOLD"
        assert result["impact"] == "neutral"
        assert result["confidence"] == 50
        assert "Brak danych" in result["summary"]


class TestNewsAnalysis:
    """Testy analizy sentimentu wiadomości"""
    
    def setup_method(self):
        """Przygotowanie przed każdym testem"""
        self.strategy = AIStrategy(telegram_service=None)
    
    def test_analyze_news_sentiment_positive(self):
        """Test pozytywnego sentimentu"""
        news = [
            {"sentiment": "positive"},
            {"sentiment": "positive"},
            {"sentiment": "positive"},
            {"sentiment": "neutral"},
            {"sentiment": "negative"}
        ]
        
        result = self.strategy._analyze_news_sentiment(news)
        
        assert result["sentiment"] == "positive"
        assert result["score"] > 50
        assert result["news_count"] == 5
        assert "summary" in result
    
    def test_analyze_news_sentiment_negative(self):
        """Test negatywnego sentimentu"""
        news = [
            {"sentiment": "negative"},
            {"sentiment": "negative"},
            {"sentiment": "negative"},
            {"sentiment": "neutral"},
            {"sentiment": "positive"}
        ]
        
        result = self.strategy._analyze_news_sentiment(news)
        
        assert result["sentiment"] == "negative"
        assert result["score"] < 50
        assert result["news_count"] == 5
    
    def test_analyze_news_sentiment_neutral(self):
        """Test neutralnego sentimentu"""
        news = [
            {"sentiment": "neutral"},
            {"sentiment": "neutral"},
            {"sentiment": "neutral"}
        ]
        
        result = self.strategy._analyze_news_sentiment(news)
        
        assert result["sentiment"] == "neutral"
        assert result["score"] == 50
        assert result["news_count"] == 3
    
    def test_analyze_news_sentiment_empty(self):
        """Test dla braku wiadomości"""
        result = self.strategy._analyze_news_sentiment([])
        
        assert result["sentiment"] == "neutral"
        assert result["score"] == 50
        assert result["news_count"] == 0
        assert "Brak wiadomości" in result["summary"]
    
    def test_analyze_news_sentiment_mixed(self):
        """Test dla mieszanego sentimentu"""
        news = [
            {"sentiment": "positive"},
            {"sentiment": "negative"}
        ]
        
        result = self.strategy._analyze_news_sentiment(news)
        
        # Powinno być neutralne (50/50)
        assert result["sentiment"] == "neutral"
        assert result["score"] == 50
        assert result["news_count"] == 2


class TestBuildAnalysisPrompt:
    """Testy budowania promptu dla AI"""
    
    def setup_method(self):
        """Przygotowanie przed każdym testem"""
        self.strategy = AIStrategy(telegram_service=None)
    
    def test_build_analysis_prompt_basic(self):
        """Test podstawowego budowania promptu"""
        symbol = "EUR/USD"
        macro_data = {"fed": {"current_rate": 5.5}}
        news = [{"title": "Test news"}]
        technical_indicators = {"rsi": 50}
        
        prompt = self.strategy._build_analysis_prompt(
            symbol, macro_data, news, technical_indicators
        )
        
        assert symbol in prompt
        assert "5.5" in prompt or "fed" in prompt.lower()
        assert len(prompt) > 0
    
    def test_build_analysis_prompt_contains_all_data(self):
        """Test czy prompt zawiera wszystkie dane"""
        symbol = "GBP/USD"
        macro_data = {"fed": {"current_rate": 5.5}, "inflation": {"cpi_annual": 3.2}}
        news = [{"title": "News 1"}, {"title": "News 2"}]
        technical_indicators = {"rsi": 45, "macd": {"value": 0.5}}
        
        prompt = self.strategy._build_analysis_prompt(
            symbol, macro_data, news, technical_indicators
        )
        
        # Sprawdź czy wszystkie elementy są w prompcie
        assert "GBP/USD" in prompt or "gbp" in prompt.lower()
        assert len(prompt) > 100  # Powinien być długi


@pytest.mark.asyncio
class TestComprehensiveAnalysis:
    """Testy metody comprehensive_analysis() z mock'ami"""
    
    def setup_method(self):
        """Przygotowanie przed każdym testem"""
        self.strategy = AIStrategy(telegram_service=None)
    
    async def test_comprehensive_analysis_format(self):
        """Test formatu odpowiedzi comprehensive_analysis()"""
        
        # Mock wszystkich serwisów
        with patch.object(self.strategy.macro_service, 'get_all_macro_data', 
                         return_value={"fed": {"current_rate": 5.5}}):
            with patch.object(self.strategy.news_service, 'get_financial_news',
                             return_value=[{"sentiment": "positive"}]):
                with patch.object(self.strategy, '_calculate_technical_indicators',
                                 return_value={"rsi": 50, "price": 1.1000}):
                    with patch.object(self.strategy.ai_service, 'analyze_macro_data',
                                     return_value={"recommendation": "BUY", "confidence": 75}):
                        
                        result = await self.strategy.comprehensive_analysis("EUR/USD", "1h")
                        
                        # Sprawdź strukturę odpowiedzi
                        assert "symbol" in result
                        assert "timeframe" in result
                        assert "timestamp" in result
                        assert "ai_analysis" in result
                        assert "technical_analysis" in result
                        assert "macro_analysis" in result
                        assert "news_analysis" in result
                        
                        # Sprawdź ai_analysis
                        ai = result["ai_analysis"]
                        assert "recommendation" in ai
                        assert "confidence" in ai
                        assert "reasoning" in ai
                        assert "tokens_used" in ai
                        assert "estimated_cost" in ai
                        
                        # Sprawdź technical_analysis
                        tech = result["technical_analysis"]
                        assert "signal" in tech
                        assert "confidence" in tech
                        assert "indicators" in tech
                        
                        # Sprawdź macro_analysis
                        macro = result["macro_analysis"]
                        assert "signal" in macro
                        assert "confidence" in macro
                        assert "impact" in macro
                        assert "summary" in macro
                        
                        # Sprawdź news_analysis
                        news = result["news_analysis"]
                        assert "sentiment" in news
                        assert "score" in news
                        assert "news_count" in news
    
    async def test_comprehensive_analysis_error_handling(self):
        """Test obsługi błędów w comprehensive_analysis()"""
        
        # Mock który rzuca wyjątek
        with patch.object(self.strategy.macro_service, 'get_all_macro_data',
                         side_effect=Exception("Test error")):
            
            result = await self.strategy.comprehensive_analysis("EUR/USD", "1h")
            
            # Powinien zwrócić bezpieczne wartości domyślne
            assert result["ai_analysis"]["recommendation"] == "HOLD"
            assert result["ai_analysis"]["confidence"] == 0
            assert "error" in result
            assert result["technical_analysis"]["signal"] == "HOLD"
            assert result["macro_analysis"]["signal"] == "HOLD"
            assert result["news_analysis"]["sentiment"] == "neutral"


if __name__ == "__main__":
    # Uruchom testy
    pytest.main([__file__, "-v", "--tb=short"])
