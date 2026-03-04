"""Checker sygnału MACD: histogram i relacja MACD/signal → BUY/SELL."""
from typing import Any, Dict

from ...models.models import SignalType
from .base import BaseSignalChecker, SignalEvaluation


class MACDSignalChecker(BaseSignalChecker):
    def evaluate(self, strategy: Dict[str, Any], indicators: Dict[str, Any]) -> SignalEvaluation:
        macd_data = indicators.get("macd")
        current_price = indicators.get("price", 0.0)

        if macd_data is None:
            return SignalEvaluation(
                signal_type=SignalType.HOLD,
                indicator_values=None,
                message="Brak danych do obliczenia MACD",
                price=current_price,
            )

        macd_value = macd_data.get("value", 0.0)
        signal_value = macd_data.get("signal", 0.0)
        histogram = macd_data.get("histogram", 0.0)

        if histogram > 0 and macd_value > signal_value:
            signal_type = SignalType.BUY
        elif histogram < 0 and macd_value < signal_value:
            signal_type = SignalType.SELL
        else:
            signal_type = SignalType.HOLD

        indicator_values = {
            "MACD": round(macd_value, 2),
            "Signal": round(signal_value, 2),
            "Histogram": round(histogram, 2),
            "price": round(current_price, 2),
        }
        if signal_type in (SignalType.BUY, SignalType.SELL):
            message = f"MACD {signal_type.value} signal"
        else:
            message = f"No signal (MACD: {macd_value:.2f}, Signal: {signal_value:.2f})"

        return SignalEvaluation(
            signal_type=signal_type,
            indicator_values=indicator_values,
            message=message,
            price=current_price,
        )
