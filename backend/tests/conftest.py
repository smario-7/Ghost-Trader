"""
Wspólne fixtures i mocki dla wszystkich testów
"""
import pytest
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List
import json

# Dodaj katalog główny do PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.database import Database


# ===== DATABASE FIXTURES =====

@pytest.fixture
def test_db():
    """
    Tymczasowa baza danych w pamięci dla testów
    
    Tworzy czystą bazę danych SQLite w pamięci, inicjalizuje wszystkie tabele
    i zwraca gotową do użycia instancję Database.
    """
    db = Database(":memory:")
    db.initialize()
    yield db


@pytest.fixture
def test_db_with_data(test_db):
    """
    Baza danych z przykładowymi danymi testowymi
    """
    # Dodaj przykładową konfigurację analiz
    test_db.initialize_default_config()
    
    # Dodaj przykładowe wyniki analiz
    for i in range(5):
        test_db.create_ai_analysis_result({
            "symbol": f"TEST{i}/USD",
            "timeframe": "1h",
            "ai_recommendation": "BUY" if i % 2 == 0 else "SELL",
            "ai_confidence": 70 + i * 2,
            "ai_reasoning": f"Test reasoning {i}",
            "technical_signal": "BUY",
            "technical_confidence": 65,
            "technical_details": json.dumps({"rsi": 35 + i}),
            "macro_signal": "HOLD",
            "macro_impact": "neutral",
            "news_sentiment": "positive",
            "news_score": 60,
            "final_signal": "BUY",
            "agreement_score": 70 + i,
            "voting_details": json.dumps({}),
            "decision_reason": f"Test decision {i}",
            "tokens_used": 1000 + i * 100,
            "estimated_cost": 0.001 * (i + 1)
        })
    
    yield test_db


# ===== MOCK SERVICES =====

@pytest.fixture
def mock_telegram():
    """
    Mock serwisu Telegram do testowania powiadomień
    
    Śledzi wszystkie wysłane wiadomości w liście `messages`.
    """
    class MockTelegramService:
        def __init__(self):
            self.messages = []
            self.send_count = 0
            self.should_fail = False
        
        async def send_message(self, message: str) -> bool:
            """Symuluje wysłanie wiadomości"""
            if self.should_fail:
                raise Exception("Telegram API error")
            
            self.messages.append({
                "message": message,
                "timestamp": datetime.now().isoformat()
            })
            self.send_count += 1
            return True
        
        async def check_connection(self) -> bool:
            """Symuluje sprawdzenie połączenia"""
            return not self.should_fail
        
        def get_last_message(self) -> str:
            """Zwraca ostatnią wysłaną wiadomość"""
            return self.messages[-1]["message"] if self.messages else None
        
        def clear_messages(self):
            """Czyści listę wiadomości"""
            self.messages = []
            self.send_count = 0
    
    return MockTelegramService()


@pytest.fixture
def mock_ai_strategy():
    """
    Mock AIStrategy zwracający predefiniowane wyniki analiz
    """
    class MockAIStrategy:
        def __init__(self):
            self.analysis_count = 0
            self.should_fail = False
            self.custom_result = None
        
        async def comprehensive_analysis(
            self,
            symbol: str,
            timeframe: str
        ) -> Dict[str, Any]:
            """Zwraca mock wynik comprehensive_analysis"""
            if self.should_fail:
                raise Exception("AI analysis failed")
            
            self.analysis_count += 1
            
            if self.custom_result:
                return self.custom_result
            
            return {
                "symbol": symbol,
                "timeframe": timeframe,
                "timestamp": datetime.now().isoformat(),
                "ai_analysis": {
                    "recommendation": "BUY",
                    "confidence": 80,
                    "reasoning": "Mock AI reasoning",
                    "tokens_used": 1250,
                    "estimated_cost": 0.0025
                },
                "technical_analysis": {
                    "signal": "BUY",
                    "confidence": 70,
                    "indicators": {
                        "rsi": 35,
                        "macd": "bullish",
                        "ma_cross": "golden_cross"
                    }
                },
                "macro_analysis": {
                    "signal": "HOLD",
                    "confidence": 50,
                    "impact": "neutral",
                    "summary": "Mock macro summary"
                },
                "news_analysis": {
                    "sentiment": "positive",
                    "score": 65,
                    "news_count": 5
                }
            }
    
    return MockAIStrategy()


@pytest.fixture
def mock_signal_aggregator():
    """
    Mock SignalAggregatorService zwracający kontrolowane wyniki
    """
    class MockSignalAggregator:
        def __init__(self):
            self.aggregation_count = 0
            self.should_fail = False
            self.custom_result = None
        
        async def aggregate_signals(
            self,
            symbol: str,
            timeframe: str,
            ai_result: Dict[str, Any],
            technical_result: Dict[str, Any],
            macro_result: Dict[str, Any],
            news_result: Dict[str, Any]
        ) -> Dict[str, Any]:
            """Zwraca mock wynik agregacji"""
            if self.should_fail:
                raise Exception("Aggregation failed")
            
            self.aggregation_count += 1
            
            if self.custom_result:
                return self.custom_result
            
            return {
                "final_signal": "BUY",
                "agreement_score": 75,
                "weighted_score": 72.5,
                "voting_details": {
                    "ai": {"vote": "BUY", "confidence": 80, "weight": 40},
                    "technical": {"vote": "BUY", "confidence": 70, "weight": 30},
                    "macro": {"vote": "HOLD", "confidence": 50, "weight": 20},
                    "news": {"vote": "BUY", "confidence": 65, "weight": 10}
                },
                "decision_reason": "Mock decision reason",
                "should_notify": True
            }
    
    return MockSignalAggregator()


# ===== SAMPLE DATA FIXTURES =====

@pytest.fixture
def sample_ai_result():
    """Przykładowy wynik analizy AI"""
    return {
        "recommendation": "BUY",
        "confidence": 80,
        "reasoning": "Strong bullish signals based on market conditions",
        "tokens_used": 1250,
        "estimated_cost": 0.0025,
        "key_factors": ["Fed dovish stance", "Strong employment data"],
        "risks": ["Inflation concerns", "Geopolitical tensions"]
    }


@pytest.fixture
def sample_technical_result():
    """Przykładowy wynik analizy technicznej"""
    return {
        "signal": "BUY",
        "confidence": 70,
        "indicators": {
            "rsi": 35,
            "macd": "bullish",
            "ma_cross": "golden_cross",
            "bollinger": "lower_band_touch"
        }
    }


@pytest.fixture
def sample_macro_result():
    """Przykładowy wynik analizy makro"""
    return {
        "signal": "HOLD",
        "confidence": 50,
        "impact": "neutral",
        "summary": "Fed maintains rates, inflation stable"
    }


@pytest.fixture
def sample_news_result():
    """Przykładowy wynik analizy wiadomości"""
    return {
        "sentiment": "positive",
        "score": 65,
        "news_count": 5,
        "key_themes": ["economic growth", "market optimism"]
    }


@pytest.fixture
def sample_analysis_data():
    """Kompletny zestaw danych analizy"""
    return {
        "symbol": "EUR/USD",
        "timeframe": "1h",
        "ai_recommendation": "BUY",
        "ai_confidence": 80,
        "ai_reasoning": "Strong bullish signals",
        "technical_signal": "BUY",
        "technical_confidence": 70,
        "technical_details": json.dumps({
            "rsi": 35,
            "macd": "bullish"
        }),
        "macro_signal": "HOLD",
        "macro_impact": "neutral",
        "news_sentiment": "positive",
        "news_score": 65,
        "final_signal": "BUY",
        "agreement_score": 75,
        "voting_details": json.dumps({
            "ai": {"vote": "BUY", "confidence": 80},
            "technical": {"vote": "BUY", "confidence": 70},
            "macro": {"vote": "HOLD", "confidence": 50},
            "news": {"vote": "BUY", "confidence": 65}
        }),
        "decision_reason": "3 out of 4 sources indicate BUY",
        "tokens_used": 1250,
        "estimated_cost": 0.0025
    }


# ===== API TESTING FIXTURES =====

@pytest.fixture
def api_key():
    """Klucz API do testów"""
    return "test-api-key-12345678901234567890123456789012"


@pytest.fixture
def api_headers(api_key):
    """Nagłówki HTTP z kluczem API"""
    return {
        "X-API-Key": api_key,
        "Content-Type": "application/json"
    }


@pytest.fixture
def invalid_api_headers():
    """Nagłówki HTTP z nieprawidłowym kluczem API"""
    return {
        "X-API-Key": "invalid-key",
        "Content-Type": "application/json"
    }


# ===== UTILITY FIXTURES =====

@pytest.fixture
def freeze_time():
    """
    Fixture do "zamrożenia" czasu w testach
    
    Zwraca funkcję, która ustawia stały timestamp dla testów.
    """
    frozen_time = datetime(2026, 1, 16, 12, 0, 0)
    
    def get_frozen_time():
        return frozen_time
    
    return get_frozen_time


@pytest.fixture
def sample_symbols():
    """Lista przykładowych symboli do testów"""
    return [
        "EUR/USD",
        "GBP/USD",
        "USD/JPY",
        "AUD/USD",
        "XAU/USD"
    ]


@pytest.fixture
def sample_timeframes():
    """Lista przykładowych timeframe'ów"""
    return ["1m", "5m", "15m", "30m", "1h", "4h", "1d"]


# ===== CLEANUP FIXTURES =====

@pytest.fixture(autouse=True)
def cleanup_after_test():
    """
    Automatyczne czyszczenie po każdym teście
    
    Uruchamia się automatycznie po każdym teście (autouse=True).
    """
    yield
    # Cleanup code tutaj (jeśli potrzebny)


# ===== HELPER FUNCTIONS =====

def create_mock_analysis_result(
    symbol: str = "EUR/USD",
    final_signal: str = "BUY",
    agreement_score: int = 75
) -> Dict[str, Any]:
    """
    Helper do tworzenia mock wyników analiz
    
    Args:
        symbol: Symbol do analizy
        final_signal: Finalny sygnał (BUY/SELL/HOLD)
        agreement_score: Scoring zgodności (0-100)
    
    Returns:
        Słownik z danymi analizy
    """
    return {
        "symbol": symbol,
        "timeframe": "1h",
        "ai_recommendation": final_signal,
        "ai_confidence": 80,
        "ai_reasoning": f"Test reasoning for {symbol}",
        "technical_signal": final_signal,
        "technical_confidence": 70,
        "technical_details": json.dumps({"rsi": 35}),
        "macro_signal": "HOLD",
        "macro_impact": "neutral",
        "news_sentiment": "positive" if final_signal == "BUY" else "negative",
        "news_score": 65,
        "final_signal": final_signal,
        "agreement_score": agreement_score,
        "voting_details": json.dumps({}),
        "decision_reason": f"Test decision for {symbol}",
        "tokens_used": 1000,
        "estimated_cost": 0.001
    }


# Eksportuj helper functions
pytest.create_mock_analysis_result = create_mock_analysis_result
