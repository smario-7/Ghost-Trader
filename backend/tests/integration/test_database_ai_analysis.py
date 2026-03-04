"""
Testy jednostkowe dla operacji bazodanowych AI Analysis
"""
import pytest
from datetime import datetime, timedelta
import json

from app.utils.database import Database


@pytest.mark.unit
@pytest.mark.database
class TestDatabaseAIAnalysisResults:
    """Testy CRUD dla tabeli ai_analysis_results"""
    
    def test_create_ai_analysis_result(self, test_db):
        """Test tworzenia nowego wyniku analizy AI"""
        data = {
            "symbol": "EUR/USD",
            "timeframe": "1h",
            "ai_recommendation": "BUY",
            "ai_confidence": 80,
            "ai_reasoning": "Strong bullish signals",
            "technical_signal": "BUY",
            "technical_confidence": 70,
            "technical_details": json.dumps({"rsi": 35}),
            "macro_signal": "HOLD",
            "macro_impact": "neutral",
            "news_sentiment": "positive",
            "news_score": 65,
            "final_signal": "BUY",
            "agreement_score": 75,
            "voting_details": json.dumps({}),
            "decision_reason": "Test decision",
            "tokens_used": 1250,
            "estimated_cost": 0.0025
        }
        
        result_id = test_db.create_ai_analysis_result(data)
        
        assert result_id is not None
        assert result_id > 0
    
    def test_create_ai_analysis_result_with_all_fields(self, test_db):
        """Test tworzenia wyniku z wszystkimi polami"""
        data = pytest.create_mock_analysis_result(
            symbol="GBP/USD",
            final_signal="SELL",
            agreement_score=85
        )
        
        result_id = test_db.create_ai_analysis_result(data)
        
        # Sprawdź czy został zapisany
        result = test_db.get_ai_analysis_by_id(result_id)
        assert result is not None
        assert result["symbol"] == "GBP/USD"
        assert result["final_signal"] == "SELL"
        assert result["agreement_score"] == 85
    
    def test_get_ai_analysis_results_all(self, test_db_with_data):
        """Test pobierania wszystkich wyników analiz"""
        results = test_db_with_data.get_ai_analysis_results()
        
        assert len(results) > 0
        assert all("symbol" in r for r in results)
        assert all("final_signal" in r for r in results)
    
    def test_get_ai_analysis_results_by_symbol(self, test_db):
        """Test filtrowania wyników po symbolu"""
        # Dodaj wyniki dla różnych symboli
        for symbol in ["EUR/USD", "GBP/USD", "EUR/USD"]:
            data = pytest.create_mock_analysis_result(symbol=symbol)
            test_db.create_ai_analysis_result(data)
        
        # Pobierz tylko EUR/USD
        results = test_db.get_ai_analysis_results(symbol="EUR/USD")
        
        assert len(results) == 2
        assert all(r["symbol"] == "EUR/USD" for r in results)
    
    def test_get_ai_analysis_results_with_limit(self, test_db):
        """Test limitowania liczby wyników"""
        # Dodaj 10 wyników
        for i in range(10):
            data = pytest.create_mock_analysis_result(symbol=f"TEST{i}/USD")
            test_db.create_ai_analysis_result(data)
        
        # Pobierz tylko 5
        results = test_db.get_ai_analysis_results(limit=5)
        
        assert len(results) == 5
    
    def test_get_ai_analysis_by_id_exists(self, test_db):
        """Test pobierania analizy po ID - istnieje"""
        data = pytest.create_mock_analysis_result()
        result_id = test_db.create_ai_analysis_result(data)
        
        result = test_db.get_ai_analysis_by_id(result_id)
        
        assert result is not None
        assert result["id"] == result_id
        assert result["symbol"] == "EUR/USD"
    
    def test_get_ai_analysis_by_id_not_found(self, test_db):
        """Test pobierania analizy po ID - nie istnieje"""
        result = test_db.get_ai_analysis_by_id(99999)
        
        assert result is None
    
    def test_ai_analysis_results_ordering(self, test_db):
        """Test sortowania wyników - najnowsze pierwsze"""
        # Dodaj wyniki w określonej kolejności
        ids = []
        for i in range(3):
            data = pytest.create_mock_analysis_result(symbol=f"TEST{i}/USD")
            result_id = test_db.create_ai_analysis_result(data)
            ids.append(result_id)
        
        results = test_db.get_ai_analysis_results()
        
        # Najnowszy (ostatni dodany) powinien być pierwszy
        assert results[0]["id"] == ids[-1]
        assert results[-1]["id"] == ids[0]


@pytest.mark.unit
@pytest.mark.database
class TestDatabaseTokenStatistics:
    """Testy statystyk tokenów OpenAI"""
    
    def test_get_token_statistics_all_time(self, test_db):
        """Test pobierania statystyk dla wszystkich analiz"""
        # Dodaj 3 analizy z różną liczbą tokenów
        for i in range(3):
            data = pytest.create_mock_analysis_result()
            data["tokens_used"] = 1000 * (i + 1)
            data["estimated_cost"] = 0.001 * (i + 1)
            test_db.create_ai_analysis_result(data)
        
        stats = test_db.get_token_statistics()
        
        assert stats["total_tokens"] == 6000  # 1000 + 2000 + 3000
        assert stats["total_cost"] == 0.006  # 0.001 + 0.002 + 0.003
        assert stats["analyses_count"] == 3
        assert stats["avg_tokens_per_analysis"] == 2000  # 6000 / 3
    
    def test_get_token_statistics_with_date_range(self, test_db):
        """Test statystyk z zakresem dat"""
        # Dodaj analizy
        for i in range(5):
            data = pytest.create_mock_analysis_result()
            data["tokens_used"] = 1000
            data["estimated_cost"] = 0.001
            test_db.create_ai_analysis_result(data)
        
        # Pobierz statystyki (wszystkie powinny być z dzisiaj)
        today = datetime.now().strftime("%Y-%m-%d")
        stats = test_db.get_token_statistics(start_date=today, end_date=today)
        
        assert stats["total_tokens"] == 5000
        assert stats["analyses_count"] == 5
    
    def test_get_token_statistics_empty_database(self, test_db):
        """Test statystyk dla pustej bazy"""
        stats = test_db.get_token_statistics()
        
        assert stats["total_tokens"] == 0
        assert stats["total_cost"] == 0.0
        assert stats["analyses_count"] == 0
        assert stats["avg_tokens_per_analysis"] == 0
    
    def test_get_token_statistics_today_only(self, test_db):
        """Test statystyk tylko dla dzisiejszych analiz"""
        # Dodaj analizy dzisiaj
        for i in range(3):
            data = pytest.create_mock_analysis_result()
            data["tokens_used"] = 1000
            test_db.create_ai_analysis_result(data)
        
        stats = test_db.get_token_statistics()
        
        # Sprawdź czy today_tokens jest obliczony
        assert "today_tokens" in stats
        assert stats["today_tokens"] >= 0
        assert "today_cost" in stats
        assert "today_analyses" in stats
    
    def test_token_statistics_calculations(self, test_db):
        """Test poprawności obliczeń statystyk"""
        # Dodaj analizy z różnymi wartościami
        test_data = [
            (1000, 0.001),
            (2000, 0.002),
            (3000, 0.003),
            (4000, 0.004)
        ]
        
        for tokens, cost in test_data:
            data = pytest.create_mock_analysis_result()
            data["tokens_used"] = tokens
            data["estimated_cost"] = cost
            test_db.create_ai_analysis_result(data)
        
        stats = test_db.get_token_statistics()
        
        # Sprawdź sumy
        assert stats["total_tokens"] == 10000
        assert abs(stats["total_cost"] - 0.010) < 0.0001
        
        # Sprawdź średnią
        assert stats["avg_tokens_per_analysis"] == 2500  # 10000 / 4


@pytest.mark.unit
@pytest.mark.database
class TestDatabaseAnalysisConfig:
    """Testy konfiguracji automatycznych analiz"""
    
    def test_get_analysis_config_default(self, test_db):
        """Test pobierania domyślnej konfiguracji"""
        # Inicjalizuj domyślną konfigurację
        test_db.initialize_default_config()
        
        config = test_db.get_analysis_config()
        
        assert config is not None
        assert "analysis_interval" in config
        assert "notification_threshold" in config
        assert "is_active" in config
        assert config["analysis_interval"] == 15
        assert config["notification_threshold"] == 60
    
    def test_update_analysis_config_interval(self, test_db):
        """Test aktualizacji interwału analiz"""
        test_db.initialize_default_config()
        
        # Aktualizuj interwał
        success = test_db.update_analysis_config({"analysis_interval": 30})
        assert success is True
        
        # Sprawdź czy zapisano
        config = test_db.get_analysis_config()
        assert config["analysis_interval"] == 30
    
    def test_update_analysis_config_symbols(self, test_db):
        """Test aktualizacji listy symboli"""
        test_db.initialize_default_config()
        
        symbols = ["EUR/USD", "GBP/USD", "USD/JPY"]
        success = test_db.update_analysis_config({
            "enabled_symbols": json.dumps(symbols)
        })
        assert success is True
        
        # Sprawdź czy zapisano
        config = test_db.get_analysis_config()
        saved_symbols = json.loads(config["enabled_symbols"])
        assert saved_symbols == symbols
    
    def test_update_analysis_config_threshold(self, test_db):
        """Test aktualizacji progu powiadomień"""
        test_db.initialize_default_config()
        
        success = test_db.update_analysis_config({"notification_threshold": 70})
        assert success is True
        
        config = test_db.get_analysis_config()
        assert config["notification_threshold"] == 70
    
    def test_update_analysis_config_multiple_fields(self, test_db):
        """Test aktualizacji wielu pól jednocześnie"""
        test_db.initialize_default_config()
        
        updates = {
            "analysis_interval": 20,
            "notification_threshold": 65,
            "is_active": False
        }
        
        success = test_db.update_analysis_config(updates)
        assert success is True
        
        config = test_db.get_analysis_config()
        assert config["analysis_interval"] == 20
        assert config["notification_threshold"] == 65
        assert config["is_active"] == 0  # SQLite zwraca 0/1 dla bool
    
    def test_initialize_default_config(self, test_db):
        """Test inicjalizacji domyślnej konfiguracji"""
        config_id = test_db.initialize_default_config()
        
        assert config_id is not None
        assert config_id > 0
        
        # Sprawdź czy konfiguracja istnieje
        config = test_db.get_analysis_config()
        assert config is not None
        assert config["id"] == config_id


@pytest.mark.unit
@pytest.mark.database
class TestDatabaseJSONSerialization:
    """Testy serializacji/deserializacji JSON"""
    
    def test_voting_details_json_serialization(self, test_db):
        """Test zapisywania i odczytywania voting_details jako JSON"""
        voting_details = {
            "ai": {"vote": "BUY", "confidence": 80},
            "technical": {"vote": "BUY", "confidence": 70},
            "macro": {"vote": "HOLD", "confidence": 50},
            "news": {"vote": "BUY", "confidence": 65}
        }
        
        data = pytest.create_mock_analysis_result()
        data["voting_details"] = json.dumps(voting_details)
        
        result_id = test_db.create_ai_analysis_result(data)
        result = test_db.get_ai_analysis_by_id(result_id)
        
        # Sprawdź czy można zdekodować JSON
        saved_voting = json.loads(result["voting_details"])
        assert saved_voting == voting_details
    
    def test_technical_details_json_serialization(self, test_db):
        """Test zapisywania technical_details jako JSON"""
        technical_details = {
            "rsi": 35,
            "macd": "bullish",
            "ma_cross": "golden_cross",
            "bollinger": "lower_band_touch"
        }
        
        data = pytest.create_mock_analysis_result()
        data["technical_details"] = json.dumps(technical_details)
        
        result_id = test_db.create_ai_analysis_result(data)
        result = test_db.get_ai_analysis_by_id(result_id)
        
        saved_technical = json.loads(result["technical_details"])
        assert saved_technical == technical_details
    
    def test_enabled_symbols_json_serialization(self, test_db):
        """Test zapisywania enabled_symbols jako JSON"""
        test_db.initialize_default_config()
        
        symbols = ["EUR/USD", "GBP/USD", "USD/JPY", "XAU/USD"]
        test_db.update_analysis_config({
            "enabled_symbols": json.dumps(symbols)
        })
        
        config = test_db.get_analysis_config()
        saved_symbols = json.loads(config["enabled_symbols"])
        
        assert saved_symbols == symbols
        assert len(saved_symbols) == 4


@pytest.mark.unit
@pytest.mark.database
class TestDatabaseEdgeCases:
    """Testy przypadków brzegowych"""
    
    def test_create_analysis_with_null_optional_fields(self, test_db):
        """Test tworzenia analizy z opcjonalnymi polami NULL"""
        data = {
            "symbol": "EUR/USD",
            "timeframe": "1h",
            "final_signal": "NO_SIGNAL",
            "agreement_score": 0
        }
        
        # Powinno działać mimo braku niektórych pól
        result_id = test_db.create_ai_analysis_result(data)
        assert result_id is not None
    
    def test_get_analysis_results_with_zero_limit(self, test_db_with_data):
        """Test pobierania z limitem 0"""
        results = test_db_with_data.get_ai_analysis_results(limit=0)
        
        # Powinno zwrócić pustą listę lub wszystkie (zależnie od implementacji)
        assert isinstance(results, list)
    
    def test_update_config_with_empty_dict(self, test_db):
        """Test aktualizacji konfiguracji pustym słownikiem"""
        test_db.initialize_default_config()
        
        success = test_db.update_analysis_config({})
        
        # Powinno zwrócić False (brak danych do aktualizacji)
        assert success is False
    
    def test_get_token_statistics_with_invalid_date_range(self, test_db):
        """Test statystyk z nieprawidłowym zakresem dat"""
        # Data końcowa przed datą początkową
        stats = test_db.get_token_statistics(
            start_date="2026-12-31",
            end_date="2026-01-01"
        )
        
        # Powinno zwrócić puste statystyki
        assert stats["analyses_count"] == 0
    
    def test_multiple_configs_only_latest_returned(self, test_db):
        """Test że zwracana jest tylko najnowsza konfiguracja"""
        # Utwórz kilka konfiguracji
        test_db.initialize_default_config()
        test_db.update_analysis_config({"analysis_interval": 20})
        test_db.update_analysis_config({"analysis_interval": 30})
        
        config = test_db.get_analysis_config()
        
        # Powinna być zwrócona najnowsza
        assert config["analysis_interval"] == 30


def run_tests():
    """Uruchamia testy database"""
    pytest.main([__file__, "-v", "--tb=short", "-m", "database"])


if __name__ == "__main__":
    run_tests()
