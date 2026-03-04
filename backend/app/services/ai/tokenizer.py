"""
Moduł liczenia tokenów, szacowania kosztów i budowy promptu dla analizy AI.
"""
from typing import Dict, Any, List, Optional


def build_analysis_prompt(
    symbol: str,
    macro_data: Dict[str, Any],
    news: List[Dict[str, Any]],
    technical_indicators: Dict[str, Any],
) -> str:
    """
    Buduje prompt dla AI (do liczenia tokenów).

    Args:
        symbol: Symbol
        macro_data: Dane makro
        news: Lista wiadomości
        technical_indicators: Wskaźniki techniczne

    Returns:
        Pełny tekst promptu
    """
    prompt = f"Analyze {symbol}\n\n"
    prompt += f"Macro: {str(macro_data)}\n"
    prompt += f"News: {str(news)}\n"
    prompt += f"Technical: {str(technical_indicators)}\n"
    return prompt


def count_tokens(text: str) -> int:
    """
    Szacuje liczbę tokenów OpenAI.

    Tokeny to jednostki tekstu używane przez modele AI (ok. 4 znaki na token).
    Używamy przybliżenia: 1 token ≈ 4 znaki + buffer 300 na odpowiedź.

    Args:
        text: Tekst do policzenia (prompt wysyłany do AI)

    Returns:
        Przybliżona liczba tokenów (input + buffer na output)
    """
    if not text:
        return 0
    estimated_tokens = len(text) // 4
    estimated_tokens += 300
    return estimated_tokens


def estimate_cost(
    tokens: int,
    model: Optional[str] = None,
    settings: Any = None,
) -> float:
    """
    Szacuje koszt zapytania do OpenAI (ceny za input/output tokeny).

    Args:
        tokens: Liczba tokenów (input + output razem)
        model: Model OpenAI (jeśli None, brany z settings.openai_model)
        settings: Obiekt ustawień z atrybutem openai_model

    Returns:
        Szacowany koszt w USD (zaokrąglony do 6 miejsc po przecinku)
    """
    if model is None and settings is not None:
        model = getattr(settings, "openai_model", "gpt-4o-mini")
    if model is None:
        model = "gpt-4o-mini"

    prices = {
        "gpt-4o": {"input": 0.005, "output": 0.015},
        "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    }
    price = prices.get(model, prices["gpt-4o-mini"])
    input_tokens = tokens * 0.6
    output_tokens = tokens * 0.4
    cost = (
        (input_tokens * price["input"] / 1000)
        + (output_tokens * price["output"] / 1000)
    )
    return round(cost, 6)
