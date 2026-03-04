"""
Testy jednostkowe dla SignalAggregatorService
"""
import pytest
import asyncio

from app.services.signal_aggregator_service import SignalAggregatorService


class MockDatabase:
    """Mock bazy danych dla testów"""
    
    def __init__(self, notification_threshold=60):
        self.notification_threshold = notification_threshold
    
    def get_analysis_config(self):
        return {
            "notification_threshold": self.notification_threshold,
            "is_active": True
        }


class TestSignalAggregatorService:
    """Testy dla SignalAggregatorService"""
    
    @pytest.fixture
    def mock_db(self):
        """Fixture zwracający mock bazy danych"""
        return MockDatabase()
    
    @pytest.fixture
    def aggregator(self, mock_db):
        """Fixture zwracający instancję aggregatora"""
        return SignalAggregatorService(database=mock_db)
    
    def test_initialization(self, aggregator):
        """Test inicjalizacji serwisu"""
        assert aggregator.weights["ai"] == 40
        assert aggregator.weights["technical"] == 30
        assert aggregator.weights["macro"] == 20
        assert aggregator.weights["news"] == 10
        assert sum(aggregator.weights.values()) == 100
    
    def test_initialization_with_custom_weights(self, mock_db):
        """Test inicjalizacji z niestandardowymi wagami"""
        custom_weights = {"ai": 50, "technical": 25, "macro": 15, "news": 10}
        aggregator = SignalAggregatorService(database=mock_db, weights=custom_weights)
        
        assert aggregator.weights == custom_weights
    
    def test_normalize_ai_signal(self, aggregator):
        """Test normalizacji sygnału AI"""
        ai_result = {"recommendation": "BUY", "confidence": 80}
        normalized = aggregator._normalize_signal("ai", ai_result)
        
        assert normalized["vote"] == "BUY"
        assert normalized["confidence"] == 80
    
    def test_normalize_technical_signal(self, aggregator):
        """Test normalizacji sygnału technicznego"""
        tech_result = {"signal": "SELL", "confidence": 70}
        normalized = aggregator._normalize_signal("technical", tech_result)
        
        assert normalized["vote"] == "SELL"
        assert normalized["confidence"] == 70
    
    def test_normalize_macro_signal(self, aggregator):
        """Test normalizacji sygnału makro"""
        macro_result = {"signal": "HOLD", "impact": "neutral", "confidence": 50}
        normalized = aggregator._normalize_signal("macro", macro_result)
        
        assert normalized["vote"] == "HOLD"
        assert normalized["confidence"] == 50
    
    def test_normalize_news_signal_positive(self, aggregator):
        """Test normalizacji pozytywnego sentimentu wiadomości"""
        news_result = {"sentiment": "positive", "score": 65}
        normalized = aggregator._normalize_signal("news", news_result)
        
        assert normalized["vote"] == "BUY"
        assert normalized["confidence"] == 65
    
    def test_normalize_news_signal_negative(self, aggregator):
        """Test normalizacji negatywnego sentimentu wiadomości"""
        news_result = {"sentiment": "negative", "score": 40}
        normalized = aggregator._normalize_signal("news", news_result)
        
        assert normalized["vote"] == "SELL"
        assert normalized["confidence"] == 40
    
    def test_normalize_empty_result(self, aggregator):
        """Test normalizacji pustego wyniku"""
        normalized = aggregator._normalize_signal("ai", {})
        
        assert normalized["vote"] == "HOLD"
        assert normalized["confidence"] == 0
    
    def test_calculate_agreement_majority_buy(self, aggregator):
        """Test głosowania większościowego - większość BUY"""
        votes = {
            "ai": {"vote": "BUY", "confidence": 80},
            "technical": {"vote": "BUY", "confidence": 70},
            "macro": {"vote": "HOLD", "confidence": 50},
            "news": {"vote": "BUY", "confidence": 60}
        }
        
        final_signal, agreement_score, weighted_score = aggregator._calculate_agreement(votes)
        
        assert final_signal == "BUY"
        assert agreement_score > 50  # Większość głosów za BUY
        assert weighted_score > 0
    
    def test_calculate_agreement_majority_sell(self, aggregator):
        """Test głosowania większościowego - większość SELL"""
        votes = {
            "ai": {"vote": "SELL", "confidence": 75},
            "technical": {"vote": "SELL", "confidence": 80},
            "macro": {"vote": "SELL", "confidence": 60},
            "news": {"vote": "HOLD", "confidence": 50}
        }
        
        final_signal, agreement_score, weighted_score = aggregator._calculate_agreement(votes)
        
        assert final_signal == "SELL"
        assert agreement_score > 60
    
    def test_calculate_agreement_conflicting_signals(self, aggregator):
        """Test głosowania z konfliktowymi sygnałami"""
        votes = {
            "ai": {"vote": "BUY", "confidence": 60},
            "technical": {"vote": "SELL", "confidence": 65},
            "macro": {"vote": "HOLD", "confidence": 50},
            "news": {"vote": "BUY", "confidence": 55}
        }
        
        final_signal, agreement_score, weighted_score = aggregator._calculate_agreement(votes)
        
        # Sygnał powinien być określony (nie NO_SIGNAL)
        assert final_signal in ["BUY", "SELL", "HOLD"]
        # Agreement score powinien być niższy przy konfliktowych sygnałach
        assert 0 <= agreement_score <= 100
    
    def test_calculate_agreement_all_hold(self, aggregator):
        """Test gdy wszystkie źródła wskazują HOLD"""
        votes = {
            "ai": {"vote": "HOLD", "confidence": 50},
            "technical": {"vote": "HOLD", "confidence": 45},
            "macro": {"vote": "HOLD", "confidence": 50},
            "news": {"vote": "HOLD", "confidence": 48}
        }
        
        final_signal, agreement_score, weighted_score = aggregator._calculate_agreement(votes)
        
        # Przy niskim confidence i HOLD powinno być NO_SIGNAL
        assert final_signal in ["HOLD", "NO_SIGNAL"]
    
    def test_generate_decision_reason(self, aggregator):
        """Test generowania uzasadnienia decyzji"""
        votes = {
            "ai": {"vote": "BUY", "confidence": 80},
            "technical": {"vote": "BUY", "confidence": 70},
            "macro": {"vote": "HOLD", "confidence": 50},
            "news": {"vote": "BUY", "confidence": 60}
        }
        
        reason = aggregator._generate_decision_reason(
            votes=votes,
            final_signal="BUY",
            agreement_score=75,
            weighted_score=68.0
        )
        
        assert "BUY" in reason
        assert "75%" in reason
        assert "AI" in reason
        assert "Technical" in reason
    
    def test_should_generate_signal_above_threshold(self, aggregator):
        """Test decyzji o powiadomieniu - powyżej progu"""
        should_notify = aggregator._should_generate_signal(
            agreement_score=75,
            final_signal="BUY"
        )
        
        assert should_notify is True
    
    def test_should_generate_signal_below_threshold(self, aggregator):
        """Test decyzji o powiadomieniu - poniżej progu"""
        should_notify = aggregator._should_generate_signal(
            agreement_score=45,
            final_signal="BUY"
        )
        
        assert should_notify is False
    
    def test_should_generate_signal_hold(self, aggregator):
        """Test decyzji o powiadomieniu - sygnał HOLD"""
        should_notify = aggregator._should_generate_signal(
            agreement_score=80,
            final_signal="HOLD"
        )
        
        # HOLD nie powinien generować powiadomienia
        assert should_notify is False
    
    def test_should_generate_signal_no_signal(self, aggregator):
        """Test decyzji o powiadomieniu - NO_SIGNAL"""
        should_notify = aggregator._should_generate_signal(
            agreement_score=90,
            final_signal="NO_SIGNAL"
        )
        
        assert should_notify is False
    
    @pytest.mark.asyncio
    async def test_aggregate_signals_success(self, aggregator):
        """Test pełnej agregacji sygnałów - sukces"""
        ai_result = {"recommendation": "BUY", "confidence": 80}
        technical_result = {"signal": "BUY", "confidence": 70}
        macro_result = {"signal": "HOLD", "confidence": 50, "impact": "neutral"}
        news_result = {"sentiment": "positive", "score": 65}
        
        result = await aggregator.aggregate_signals(
            symbol="EUR/USD",
            timeframe="1h",
            ai_result=ai_result,
            technical_result=technical_result,
            macro_result=macro_result,
            news_result=news_result
        )
        
        assert "final_signal" in result
        assert "agreement_score" in result
        assert "weighted_score" in result
        assert "voting_details" in result
        assert "decision_reason" in result
        assert "should_notify" in result
        
        assert result["final_signal"] == "BUY"
        assert result["agreement_score"] > 0
        assert len(result["voting_details"]) == 4
    
    @pytest.mark.asyncio
    async def test_aggregate_signals_with_error(self, aggregator):
        """Test agregacji z błędnymi danymi"""
        # Przekaż None jako wyniki
        result = await aggregator.aggregate_signals(
            symbol="EUR/USD",
            timeframe="1h",
            ai_result=None,
            technical_result=None,
            macro_result=None,
            news_result=None
        )
        
        # Powinien zwrócić bezpieczny wynik
        assert result["final_signal"] in ["HOLD", "NO_SIGNAL"]
        assert result["agreement_score"] >= 0
    
    def test_update_weights(self, aggregator):
        """Test aktualizacji wag"""
        new_weights = {"ai": 50, "technical": 25, "macro": 15, "news": 10}
        success = aggregator.update_weights(new_weights)
        
        assert success is True
        assert aggregator.weights == new_weights
    
    def test_update_weights_invalid_sum(self, aggregator):
        """Test aktualizacji wag z nieprawidłową sumą"""
        invalid_weights = {"ai": 50, "technical": 30, "macro": 20, "news": 10}  # suma = 110
        success = aggregator.update_weights(invalid_weights)
        
        assert success is False
        # Wagi nie powinny się zmienić
        assert aggregator.weights["ai"] == 40
    
    def test_get_weights(self, aggregator):
        """Test pobierania wag"""
        weights = aggregator.get_weights()
        
        assert isinstance(weights, dict)
        assert sum(weights.values()) == 100
        assert "ai" in weights
        assert "technical" in weights
        assert "macro" in weights
        assert "news" in weights


def run_tests():
    """Uruchamia testy"""
    pytest.main([__file__, "-v", "--tb=short"])


if __name__ == "__main__":
    run_tests()
