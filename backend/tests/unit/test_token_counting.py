"""
Test liczenia tokenów i szacowania kosztów (moduł app.services.ai.tokenizer).
"""
import sys

from app.services.ai import tokenizer


def test_token_counting():
    """Test liczenia tokenów dla różnych rozmiarów promptów."""

    print("\n" + "=" * 80)
    print("TEST LICZENIA TOKENÓW I SZACOWANIA KOSZTÓW")
    print("=" * 80)

    short_prompt = "Analyze EUR/USD"
    tokens_short = tokenizer.count_tokens(short_prompt)

    print("\n--- Test 1: Krótki prompt ---")
    print(f"Tekst: '{short_prompt}'")
    print(f"Długość: {len(short_prompt)} znaków")
    print(f"Szacowane tokeny: {tokens_short}")
    print(f"Przybliżenie: {len(short_prompt) // 4} tokenów (bez bufora)")

    medium_prompt = """
    Analyze EUR/USD with the following data:
    - Technical indicators: RSI=45, MACD=bullish, MA=golden_cross
    - Macro: Fed rate=5.5%, Inflation=2.3%, GDP=2.8%
    - News: 5 articles (3 positive, 1 negative, 1 neutral)
    """
    tokens_medium = tokenizer.count_tokens(medium_prompt)

    print("\n--- Test 2: Średni prompt ---")
    print(f"Długość: {len(medium_prompt)} znaków")
    print(f"Szacowane tokeny: {tokens_medium}")

    long_prompt = ("A" * 10000) + " analyze"
    tokens_long = tokenizer.count_tokens(long_prompt)

    print("\n--- Test 3: Długi prompt ---")
    print(f"Długość: {len(long_prompt)} znaków")
    print(f"Szacowane tokeny: {tokens_long}")

    print("\n--- Test 4: Szacowanie kosztów ---")
    models = ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"]
    for model in models:
        cost = tokenizer.estimate_cost(tokens_long, model)
        print(f"{model:20s}: ${cost:.6f} za analizę")

    print("\n" + "=" * 80)
    print("TEST ZAKOŃCZONY")
    print("=" * 80)

    assert tokens_short > 0
    assert tokens_medium > tokens_short
    assert tokens_long > 2500
    assert tokenizer.count_tokens("") == 0
    for model in models:
        assert tokenizer.estimate_cost(1000, model) > 0


if __name__ == "__main__":
    try:
        test_token_counting()
        print("\nWszystkie testy liczenia tokenów przeszły pomyślnie!")
    except Exception as e:
        print(f"\nBłąd w testach: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
