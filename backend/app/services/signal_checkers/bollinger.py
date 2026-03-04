"""Checker sygnału Bollinger Bands: pozycja ceny w zakresie bandów → BUY/SELL."""
from typing import Any, Dict

from ...models.models import SignalType
from .base import BaseSignalChecker, SignalEvaluation


class BollingerSignalChecker(BaseSignalChecker):
    def evaluate(self, strategy: Dict[str, Any], indicators: Dict[str, Any]) -> SignalEvaluation:
        bollinger_data = indicators.get("bollinger")
        current_price = indicators.get("price", 0.0)

        if bollinger_data is None:
            return SignalEvaluation(
                signal_type=SignalType.HOLD,
                indicator_values=None,
                message="Brak danych do obliczenia Bollinger Bands",
                price=current_price,
            )

        upper = bollinger_data.get("upper", 0.0)
        middle = bollinger_data.get("middle", 0.0)
        lower = bollinger_data.get("lower", 0.0)

        band_width = upper - lower
        price_position = (current_price - lower) / band_width if band_width > 0 else 0.5

        if price_position < 0.2:
            signal_type = SignalType.BUY
        elif price_position > 0.8:
            signal_type = SignalType.SELL
        else:
            signal_type = SignalType.HOLD

        indicator_values = {
            "Upper": round(upper, 2),
            "Middle": round(middle, 2),
            "Lower": round(lower, 2),
            "Price": round(current_price, 2),
            "Position": round(price_position * 100, 2),
        }
        if signal_type in (SignalType.BUY, SignalType.SELL):
            message = f"Bollinger {signal_type.value} signal"
        else:
            message = f"No signal (Price: {current_price:.2f})"

        return SignalEvaluation(
            signal_type=signal_type,
            indicator_values=indicator_values,
            message=message,
            price=current_price,
        )
