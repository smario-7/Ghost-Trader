"""Checker sygnału Moving Average: SMA short vs long → BUY/SELL."""
from typing import Any, Dict

from ...models.models import SignalType
from .base import BaseSignalChecker, SignalEvaluation


class MASignalChecker(BaseSignalChecker):
    def evaluate(self, strategy: Dict[str, Any], indicators: Dict[str, Any]) -> SignalEvaluation:
        params = strategy["parameters"]
        short_period = params.get("short_period", 50)
        long_period = params.get("long_period", 200)

        sma_short = indicators.get("sma_short")
        sma_long = indicators.get("sma_long")
        current_price = indicators.get("price", 0.0)

        if sma_short is None or sma_long is None:
            return SignalEvaluation(
                signal_type=SignalType.HOLD,
                indicator_values=None,
                message="Brak danych do obliczenia Moving Averages",
                price=current_price,
            )

        if sma_short > sma_long:
            signal_type = SignalType.BUY
        elif sma_short < sma_long:
            signal_type = SignalType.SELL
        else:
            signal_type = SignalType.HOLD

        diff_pct = ((sma_short - sma_long) / sma_long * 100) if sma_long else 0.0
        indicator_values = {
            f"SMA_{short_period}": round(sma_short, 2),
            f"SMA_{long_period}": round(sma_long, 2),
            "Price": round(current_price, 2),
            "Difference": round(diff_pct, 2),
        }
        if signal_type == SignalType.BUY:
            message = f"MA {signal_type.value} signal (Golden Cross)"
        elif signal_type == SignalType.SELL:
            message = f"MA {signal_type.value} signal (Death Cross)"
        else:
            message = f"No signal (SMA_{short_period}: {sma_short:.2f}, SMA_{long_period}: {sma_long:.2f})"

        return SignalEvaluation(
            signal_type=signal_type,
            indicator_values=indicator_values,
            message=message,
            price=current_price,
        )
