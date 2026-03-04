"""Checker sygnału RSI: RSI < oversold → BUY, RSI > overbought → SELL."""
from typing import Any, Dict

from ...models.models import SignalType
from .base import BaseSignalChecker, SignalEvaluation


class RSISignalChecker(BaseSignalChecker):
    def evaluate(self, strategy: Dict[str, Any], indicators: Dict[str, Any]) -> SignalEvaluation:
        rsi_value = indicators.get("rsi")
        current_price = indicators.get("price", 0.0)
        params = strategy["parameters"]
        oversold = params.get("oversold", 30)
        overbought = params.get("overbought", 70)

        if rsi_value is None:
            return SignalEvaluation(
                signal_type=SignalType.HOLD,
                indicator_values=None,
                message="Brak danych do obliczenia RSI",
                price=current_price,
            )

        if rsi_value < oversold:
            signal_type = SignalType.BUY
        elif rsi_value > overbought:
            signal_type = SignalType.SELL
        else:
            signal_type = SignalType.HOLD

        indicator_values = {
            "RSI": round(rsi_value, 2),
            "oversold": oversold,
            "overbought": overbought,
            "price": round(current_price, 2),
        }
        if signal_type in (SignalType.BUY, SignalType.SELL):
            message = f"RSI {signal_type.value} signal (RSI: {rsi_value:.2f})"
        else:
            message = f"No signal (RSI: {rsi_value:.2f})"

        return SignalEvaluation(
            signal_type=signal_type,
            indicator_values=indicator_values,
            message=message,
            price=current_price,
        )
