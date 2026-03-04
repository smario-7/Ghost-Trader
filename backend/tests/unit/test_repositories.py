"""
Testy jednostkowe repozytoriów (przez fasadę Database).
Używają realnej bazy w pamięci (test_db z tmp_path).
"""
import json
import pytest

from app.utils.database import Database


@pytest.mark.unit
@pytest.mark.database
class TestStrategyRepository:
    """Testy repozytorium strategii (przez db.create_strategy, get_strategy, itd.)."""

    def test_create_strategy(self, test_db):
        data = {
            "name": "Test RSI",
            "strategy_type": "RSI",
            "parameters": {"period": 14, "overbought": 70, "oversold": 30},
            "symbol": "EUR/USD",
            "timeframe": "1h",
        }
        sid = test_db.create_strategy(data)
        assert sid > 0

    def test_get_strategy(self, test_db):
        data = {
            "name": "Get Test",
            "strategy_type": "MACD",
            "parameters": {},
            "symbol": "GBP/USD",
        }
        sid = test_db.create_strategy(data)
        row = test_db.get_strategy(sid)
        assert row is not None
        assert row["name"] == "Get Test"
        assert row["strategy_type"] == "MACD"
        assert row["symbol"] == "GBP/USD"
        assert isinstance(row["parameters"], dict)

    def test_get_all_strategies(self, test_db):
        for i in range(3):
            test_db.create_strategy({
                "name": f"S{i}",
                "strategy_type": "RSI",
                "parameters": {},
                "symbol": "X",
            })
        all_ = test_db.get_all_strategies()
        assert len(all_) >= 3

    def test_get_active_strategies(self, test_db):
        test_db.create_strategy({
            "name": "Active",
            "strategy_type": "RSI",
            "parameters": {},
            "symbol": "A",
            "is_active": True,
        })
        test_db.create_strategy({
            "name": "Inactive",
            "strategy_type": "RSI",
            "parameters": {},
            "symbol": "B",
            "is_active": False,
        })
        active = test_db.get_active_strategies()
        names = [s["name"] for s in active]
        assert "Active" in names
        assert "Inactive" not in names

    def test_update_strategy(self, test_db):
        sid = test_db.create_strategy({
            "name": "Orig",
            "strategy_type": "RSI",
            "parameters": {},
            "symbol": "X",
        })
        ok = test_db.update_strategy(sid, {"name": "Updated", "symbol": "Y"})
        assert ok is True
        row = test_db.get_strategy(sid)
        assert row["name"] == "Updated"
        assert row["symbol"] == "Y"

    def test_delete_strategy(self, test_db):
        sid = test_db.create_strategy({
            "name": "ToDelete",
            "strategy_type": "RSI",
            "parameters": {},
            "symbol": "X",
        })
        ok = test_db.delete_strategy(sid)
        assert ok is True
        assert test_db.get_strategy(sid) is None

    def test_update_last_signal(self, test_db):
        sid = test_db.create_strategy({
            "name": "Last",
            "strategy_type": "RSI",
            "parameters": {},
            "symbol": "X",
        })
        row = test_db.get_strategy(sid)
        assert row["last_signal"] is None
        test_db.update_last_signal(sid)
        row2 = test_db.get_strategy(sid)
        assert row2["last_signal"] is not None


@pytest.mark.unit
@pytest.mark.database
class TestSignalRepository:
    """Testy repozytorium sygnałów."""

    def test_create_signal_and_get_by_strategy(self, test_db):
        sid = test_db.create_strategy({
            "name": "S",
            "strategy_type": "RSI",
            "parameters": {},
            "symbol": "EUR/USD",
        })
        sig_id = test_db.create_signal({
            "strategy_id": sid,
            "signal_type": "BUY",
            "price": 1.05,
            "message": "Test",
        })
        assert sig_id > 0
        signals = test_db.get_signals_by_strategy(sid)
        assert len(signals) == 1
        assert signals[0]["signal_type"] == "BUY"
        assert signals[0]["price"] == 1.05

    def test_get_recent_signals(self, test_db):
        sid = test_db.create_strategy({
            "name": "S",
            "strategy_type": "RSI",
            "parameters": {},
            "symbol": "X",
        })
        for _ in range(3):
            test_db.create_signal({
                "strategy_id": sid,
                "signal_type": "BUY",
                "price": 1.0,
                "message": "m",
            })
        recent = test_db.get_recent_signals(limit=10)
        assert len(recent) >= 3

    def test_get_statistics(self, test_db):
        stats = test_db.get_statistics()
        assert "total_signals" in stats
        assert "active_strategies" in stats


@pytest.mark.unit
@pytest.mark.database
class TestActivityRepository:
    """Testy repozytorium logów aktywności."""

    def test_create_activity_log(self, test_db):
        log_id = test_db.create_activity_log(
            log_type="test",
            message="Test message",
            symbol="EUR/USD",
        )
        assert log_id > 0

    def test_get_recent_activity_logs(self, test_db):
        test_db.create_activity_log("test", "A")
        test_db.create_activity_log("test", "B")
        logs = test_db.get_recent_activity_logs(limit=10)
        assert len(logs) >= 2
        messages = [l["message"] for l in logs]
        assert "A" in messages
        assert "B" in messages

    def test_get_activity_logs_by_type(self, test_db):
        test_db.create_activity_log("llm", "LLM call")
        test_db.create_activity_log("signal", "Signal")
        llm_logs = test_db.get_activity_logs_by_type("llm", limit=10)
        assert any(l["message"] == "LLM call" for l in llm_logs)

    def test_get_activity_logs_since(self, test_db):
        id1 = test_db.create_activity_log("test", "First")
        test_db.create_activity_log("test", "Second")
        since = test_db.get_activity_logs_since(last_id=id1, limit=10)
        assert len(since) >= 1
        assert any(l["message"] == "Second" for l in since)
