"""
Moduł wskaźników technicznych i generowania sygnału technicznego.
"""
import logging
from typing import Dict, Any

from ..market_data_service import MarketDataService


logger = logging.getLogger("trading_bot.ai.indicators")

INDICATORS_CONFIG = {
    "period": 14,
    "fast_period": 12,
    "slow_period": 26,
    "signal_period": 9,
    "std_dev": 2.0,
    "short_period": 50,
    "long_period": 200,
}

DEFAULT_INDICATORS = {
    "price": 0.0,
    "rsi": 50.0,
    "macd": {"value": 0.0, "signal": 0.0, "histogram": 0.0},
    "bollinger": {"upper": 0.0, "middle": 0.0, "lower": 0.0},
    "sma_50": 0.0,
    "sma_200": 0.0,
    "volume_24h": 0.0,
    "volatility": 0.0,
}


async def calculate_technical_indicators(
    symbol: str,
    timeframe: str,
    market_data: MarketDataService,
) -> Dict[str, Any]:
    """
    Oblicza wskaźniki techniczne na podstawie danych z market_data.
    """
    try:
        indicators = await market_data.get_technical_indicators(
            symbol=symbol,
            timeframe=timeframe,
            indicators_config=INDICATORS_CONFIG,
        )
        data = await market_data.get_historical_data(symbol, timeframe, "1mo")
        if data is not None and not data.empty:
            returns = data["Close"].pct_change().dropna()
            volatility = returns.std() * 100
            volume = data["Volume"].iloc[-1] if "Volume" in data.columns else 0
            indicators["volatility"] = round(float(volatility), 2)
            indicators["volume_24h"] = float(volume) if volume > 0 else 0
        else:
            indicators["volatility"] = 0.0
            indicators["volume_24h"] = 0
        return indicators
    except Exception as e:
        logger.error(
            "Błąd obliczania wskaźników technicznych dla %s: %s",
            symbol,
            e,
            exc_info=True,
        )
        return dict(DEFAULT_INDICATORS)


def summarize_technical(indicators: Dict[str, Any]) -> str:
    """Podsumowuje wskaźniki techniczne."""
    if not indicators:
        return "Brak wskaźników"
    rsi = indicators.get("rsi", 0)
    price = indicators.get("price", 0)
    return f"Cena: ${price:,.2f}, RSI: {rsi:.1f}"


def analyze_technical_signal(indicators: Dict[str, Any]) -> Dict[str, Any]:
    """
    Interpretuje wskaźniki techniczne (RSI, MACD, MA, Bollinger) i generuje sygnał.
    Zwraca słownik: signal (BUY/SELL/HOLD), confidence (0-100), indicators.
    """
    if not indicators:
        return {"signal": "HOLD", "confidence": 0, "indicators": {}}

    signals = []
    rsi = indicators.get("rsi", 50)
    if rsi < 30:
        signals.append(("BUY", 70))
    elif rsi > 70:
        signals.append(("SELL", 70))
    else:
        signals.append(("HOLD", 50))

    macd_data = indicators.get("macd", {})
    if isinstance(macd_data, dict):
        macd_value = macd_data.get("value", 0)
        macd_signal = macd_data.get("signal", 0)
        if macd_value > macd_signal:
            signals.append(("BUY", 65))
        elif macd_value < macd_signal:
            signals.append(("SELL", 65))
        else:
            signals.append(("HOLD", 50))

    sma_50 = indicators.get("sma_50", 0)
    sma_200 = indicators.get("sma_200", 0)
    if sma_50 > 0 and sma_200 > 0:
        if sma_50 > sma_200:
            signals.append(("BUY", 60))
        elif sma_50 < sma_200:
            signals.append(("SELL", 60))
        else:
            signals.append(("HOLD", 50))

    bollinger = indicators.get("bollinger", {})
    price = indicators.get("price", 0)
    if isinstance(bollinger, dict):
        lower = bollinger.get("lower", 0)
        upper = bollinger.get("upper", 0)
        if price > 0 and lower > 0 and upper > 0:
            if price <= lower:
                signals.append(("BUY", 65))
            elif price >= upper:
                signals.append(("SELL", 65))

    if not signals:
        return {"signal": "HOLD", "confidence": 50, "indicators": indicators}

    buy_score = sum(conf for sig, conf in signals if sig == "BUY")
    sell_score = sum(conf for sig, conf in signals if sig == "SELL")
    hold_score = sum(conf for sig, conf in signals if sig == "HOLD")
    total = buy_score + sell_score + hold_score

    if buy_score > sell_score and buy_score > hold_score:
        final_signal = "BUY"
        confidence = int((buy_score / total) * 100) if total > 0 else 50
    elif sell_score > buy_score and sell_score > hold_score:
        final_signal = "SELL"
        confidence = int((sell_score / total) * 100) if total > 0 else 50
    else:
        final_signal = "HOLD"
        confidence = int((hold_score / total) * 100) if total > 0 else 50

    return {
        "signal": final_signal,
        "confidence": min(100, confidence),
        "indicators": indicators,
    }
