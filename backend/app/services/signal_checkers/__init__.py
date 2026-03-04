"""Checkery sygnałów per typ strategii. Fabryka SIGNAL_CHECKERS."""
from typing import Dict, Type

from ...models.models import StrategyType
from .base import BaseSignalChecker, SignalEvaluation
from .rsi import RSISignalChecker
from .macd import MACDSignalChecker
from .bollinger import BollingerSignalChecker
from .moving_average import MASignalChecker

SIGNAL_CHECKERS: Dict[StrategyType, Type[BaseSignalChecker]] = {
    StrategyType.RSI: RSISignalChecker,
    StrategyType.MACD: MACDSignalChecker,
    StrategyType.BOLLINGER: BollingerSignalChecker,
    StrategyType.MOVING_AVERAGE: MASignalChecker,
}

__all__ = [
    "BaseSignalChecker",
    "SignalEvaluation",
    "SIGNAL_CHECKERS",
    "RSISignalChecker",
    "MACDSignalChecker",
    "BollingerSignalChecker",
    "MASignalChecker",
]
