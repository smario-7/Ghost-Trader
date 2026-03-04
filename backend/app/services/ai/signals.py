"""
Moduł wysyłania powiadomień Telegram o sygnałach AI.
"""
import logging
from typing import Any, Callable, Dict

from ...config import get_polish_time


async def send_ai_signal_notification(
    result: Dict[str, Any],
    telegram_service: Any,
    logger: logging.Logger,
    get_time_fn: Callable[[], Any] = None,
) -> None:
    """
    Wysyła powiadomienie o sygnale AI do Telegrama (jeśli telegram_service nie jest None).
    """
    if not telegram_service:
        return
    get_time = get_time_fn or get_polish_time
    try:
        recommendation = result["recommendation"]
        confidence = result["confidence"]
        symbol = result["symbol"]
        emoji = "🟢" if recommendation == "BUY" else "🔴"
        ai_analysis = result.get("ai_analysis", {})
        reasoning = ai_analysis.get("reasoning", "")
        key_factors = ai_analysis.get("key_factors", [])

        message = f"""
{emoji} <b>AI SIGNAL: {recommendation}</b>

<b>Symbol:</b> {symbol}
<b>Confidence:</b> {confidence}%
<b>Timeframe:</b> {result.get('timeframe', 'N/A')}

<b>🧠 AI Reasoning:</b>
{reasoning[:300]}{"..." if len(reasoning) > 300 else ""}

<b>📊 Key Factors:</b>
"""
        for factor in key_factors[:3]:
            message += f"  • {factor}\n"
        components = result.get("decision_components", {})
        message += f"""
<b>📈 Decision Components:</b>
  • Macro: {components.get('macro_score', 'N/A')}
  • News: {components.get('news_sentiment', 'N/A')}
  • Technical: {components.get('technical_signal', 'N/A')}
  • Event Risk: {components.get('event_risk', 'N/A')}

<i>Powered by Claude AI Analysis</i>
<i>Time: {get_time().strftime("%Y-%m-%d %H:%M:%S")}</i>
"""
        await telegram_service.send_message(message)
        logger.info("AI signal notification sent")
    except Exception as e:
        logger.error("Error sending AI notification: %s", e)
