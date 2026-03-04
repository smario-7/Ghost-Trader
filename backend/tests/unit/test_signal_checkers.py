"""Testy jednostkowe dla signal_checkers (evaluate bez zależności zewnętrznych)."""
import pytest
from unittest.mock import MagicMock

from app.models.models import SignalType
from app.services.signal_checkers import (
    RSISignalChecker,
    MACDSignalChecker,
    BollingerSignalChecker,
    MASignalChecker,
)
from app.services.signal_checkers.base import SignalEvaluation


@pytest.fixture
def mock_deps():
    """Mock db, telegram, market_data, logger dla checkerów."""
    return {
        "db": MagicMock(),
        "telegram": MagicMock(),
        "market_data": MagicMock(),
        "logger": MagicMock(),
    }


def test_rsi_checker_evaluate_buy(mock_deps):
    """RSI poniżej oversold → BUY."""
    checker = RSISignalChecker(**mock_deps)
    strategy = {
        "id": 1,
        "name": "Test RSI",
        "symbol": "EUR/USD",
        "timeframe": "1h",
        "parameters": {"period": 14, "oversold": 30, "overbought": 70},
    }
    indicators = {"rsi": 25.0, "price": 1.08}
    ev = checker.evaluate(strategy, indicators)
    assert ev.signal_type == SignalType.BUY
    assert ev.price == 1.08
    assert ev.indicator_values["RSI"] == 25.0
    assert "BUY" in ev.message


def test_rsi_checker_evaluate_hold(mock_deps):
    """RSI w zakresie → HOLD."""
    checker = RSISignalChecker(**mock_deps)
    strategy = {
        "id": 1,
        "name": "Test RSI",
        "symbol": "EUR/USD",
        "timeframe": "1h",
        "parameters": {"period": 14, "oversold": 30, "overbought": 70},
    }
    indicators = {"rsi": 50.0, "price": 1.08}
    ev = checker.evaluate(strategy, indicators)
    assert ev.signal_type == SignalType.HOLD
    assert "No signal" in ev.message


def test_rsi_checker_evaluate_no_data(mock_deps):
    """Brak RSI w indicators → HOLD z komunikatem."""
    checker = RSISignalChecker(**mock_deps)
    strategy = {
        "id": 1,
        "name": "Test RSI",
        "symbol": "EUR/USD",
        "timeframe": "1h",
        "parameters": {"period": 14, "oversold": 30, "overbought": 70},
    }
    indicators = {"price": 1.08}
    ev = checker.evaluate(strategy, indicators)
    assert ev.signal_type == SignalType.HOLD
    assert ev.indicator_values is None
    assert "Brak danych" in ev.message


def test_macd_checker_evaluate_hold(mock_deps):
    """MACD bez wyraźnego sygnału → HOLD."""
    checker = MACDSignalChecker(**mock_deps)
    strategy = {
        "id": 1,
        "name": "Test MACD",
        "symbol": "EUR/USD",
        "timeframe": "1h",
        "parameters": {"fast_period": 12, "slow_period": 26, "signal_period": 9},
    }
    indicators = {
        "macd": {"value": 0.1, "signal": 0.1, "histogram": 0.0},
        "price": 1.08,
    }
    ev = checker.evaluate(strategy, indicators)
    assert ev.signal_type == SignalType.HOLD


def test_bollinger_checker_evaluate_buy(mock_deps):
    """Cena w dolnych 20% zakresu → BUY."""
    checker = BollingerSignalChecker(**mock_deps)
    strategy = {
        "id": 1,
        "name": "Test BB",
        "symbol": "EUR/USD",
        "timeframe": "1h",
        "parameters": {"period": 20, "std_dev": 2.0},
    }
    indicators = {
        "bollinger": {"upper": 1.10, "middle": 1.05, "lower": 1.00},
        "price": 1.01,
    }
    ev = checker.evaluate(strategy, indicators)
    assert ev.signal_type == SignalType.BUY
    assert ev.indicator_values["Position"] < 20


def test_ma_checker_evaluate_buy(mock_deps):
    """SMA short > SMA long → BUY."""
    checker = MASignalChecker(**mock_deps)
    strategy = {
        "id": 1,
        "name": "Test MA",
        "symbol": "EUR/USD",
        "timeframe": "1h",
        "parameters": {"short_period": 50, "long_period": 200},
    }
    indicators = {"sma_short": 1.06, "sma_long": 1.04, "price": 1.05}
    ev = checker.evaluate(strategy, indicators)
    assert ev.signal_type == SignalType.BUY
    assert "Golden Cross" in ev.message
