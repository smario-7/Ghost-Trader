"""
Moduł analizy wiadomości i sentimentu.
"""
from typing import Dict, Any, List


def summarize_news(news: List[Dict[str, Any]]) -> str:
    """Podsumowuje wiadomości (liczba i rozkład sentimentu)."""
    if not news:
        return "Brak wiadomości"
    positive = sum(1 for n in news if n.get("sentiment") == "positive")
    negative = sum(1 for n in news if n.get("sentiment") == "negative")
    return f"{len(news)} wiadomości (+ {positive}, - {negative})"


def analyze_news_sentiment(news: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analizuje sentiment wiadomości.
    Zwraca słownik: sentiment (positive/negative/neutral), score (0-100), news_count, summary.
    """
    if not news:
        return {
            "sentiment": "neutral",
            "score": 50,
            "news_count": 0,
            "summary": "Brak wiadomości",
        }
    positive = sum(1 for n in news if n.get("sentiment") == "positive")
    negative = sum(1 for n in news if n.get("sentiment") == "negative")
    neutral = len(news) - positive - negative
    total = len(news)
    if total > 0:
        score = int(((positive - negative) / total) * 50 + 50)
        score = max(0, min(100, score))
    else:
        score = 50
    if positive > negative and positive > neutral:
        sentiment = "positive"
    elif negative > positive and negative > neutral:
        sentiment = "negative"
    else:
        sentiment = "neutral"
    summary = f"{positive} pozytywnych, {negative} negatywnych, {neutral} neutralnych wiadomości"
    return {
        "sentiment": sentiment,
        "score": score,
        "news_count": total,
        "summary": summary,
    }
