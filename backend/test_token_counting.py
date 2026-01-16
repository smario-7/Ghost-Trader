"""
Test liczenia tokenów i szacowania kosztów
"""
import sys
from pathlib import Path

# Dodaj katalog do PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent))

from app.services.ai_strategy import AIStrategy


def test_token_counting():
    """Test liczenia tokenów dla różnych rozmiarów promptów"""
    
    print("\n" + "="*80)
    print("TEST LICZENIA TOKENÓW I SZACOWANIA KOSZTÓW")
    print("="*80)
    
    strategy = AIStrategy()
    
    # Test 1: Krótki prompt
    short_prompt = "Analyze EUR/USD"
    tokens_short = strategy._count_tokens(short_prompt)
    
    print(f"\n--- Test 1: Krótki prompt ---")
    print(f"Tekst: '{short_prompt}'")
    print(f"Długość: {len(short_prompt)} znaków")
    print(f"Szacowane tokeny: {tokens_short}")
    print(f"Przybliżenie: {len(short_prompt) // 4} tokenów (bez bufora)")
    
    # Test 2: Średni prompt
    medium_prompt = """
    Analyze EUR/USD with the following data:
    - Technical indicators: RSI=45, MACD=bullish, MA=golden_cross
    - Macro: Fed rate=5.5%, Inflation=2.3%, GDP=2.8%
    - News: 5 articles (3 positive, 1 negative, 1 neutral)
    """
    tokens_medium = strategy._count_tokens(medium_prompt)
    
    print(f"\n--- Test 2: Średni prompt ---")
    print(f"Długość: {len(medium_prompt)} znaków")
    print(f"Szacowane tokeny: {tokens_medium}")
    print(f"Przybliżenie: {len(medium_prompt) // 4} tokenów (bez bufora)")
    
    # Test 3: Długi prompt (symulacja prawdziwego)
    long_prompt = """
    Analyze EUR/USD with comprehensive data:
    
    Technical Indicators:
    - RSI: 45.2 (neutral zone)
    - MACD: value=0.0012, signal=0.0008, histogram=0.0004 (bullish crossover)
    - Moving Averages: SMA50=1.0850, SMA200=1.0800 (golden cross)
    - Bollinger Bands: upper=1.0900, middle=1.0850, lower=1.0800
    - Price: 1.0875 (above middle band)
    - Volume: 125000000
    - Volatility: 0.85%
    
    Macro Data:
    - Federal Reserve: Current rate 5.50%, last change 2024-11-01, next meeting 2025-02-01
    - Inflation: CPI annual 3.2%, monthly 0.3%, core CPI 3.9%
    - GDP: Current growth 2.1%, previous quarter 2.4%, YoY 2.5%
    - Employment: Unemployment 3.8%, job changes +150k, participation 62.5%
    
    News Analysis (last 24h):
    1. "Fed Chair Powell Signals Cautious Approach" - Reuters - Neutral
    2. "US Inflation Eases to 3.2%, Below Expectations" - CNBC - Positive
    3. "Geopolitical Tensions Rise in Middle East" - BBC - Negative
    4. "Tech Stocks Rally on Strong Earnings" - WSJ - Positive
    5. "Euro Zone Manufacturing Data Disappoints" - Bloomberg - Negative
    
    Upcoming Events:
    - FOMC Meeting Minutes (tomorrow, high importance)
    - US Non-Farm Payrolls (in 3 days, high importance)
    - US CPI Release (in 5 days, high importance)
    
    Please provide:
    1. Trading recommendation (BUY/SELL/HOLD)
    2. Confidence level (0-100)
    3. Key reasoning factors
    4. Risk assessment
    """ * 2  # Podwójnie dla większego promptu
    
    tokens_long = strategy._count_tokens(long_prompt)
    
    print(f"\n--- Test 3: Długi prompt (symulacja prawdziwego) ---")
    print(f"Długość: {len(long_prompt)} znaków")
    print(f"Szacowane tokeny: {tokens_long}")
    print(f"Przybliżenie: {len(long_prompt) // 4} tokenów (bez bufora)")
    
    # Test 4: Szacowanie kosztów dla różnych modeli
    print(f"\n--- Test 4: Szacowanie kosztów dla długiego promptu ---")
    print(f"Tokeny: {tokens_long}")
    print()
    
    models = ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"]
    for model in models:
        cost = strategy._estimate_cost(tokens_long, model)
        print(f"{model:20s}: ${cost:.6f} za analizę")
    
    # Test 5: Miesięczne szacowanie kosztów
    print(f"\n--- Test 5: Miesięczne szacowanie kosztów ---")
    
    # Założenia
    analyses_per_day = 96  # Co 15 minut = 96 analiz/dzień
    symbols_count = 25  # Wszystkie symbole
    analyses_per_month = analyses_per_day * 30 * symbols_count
    
    print(f"Założenia:")
    print(f"  - Interwał: 15 minut")
    print(f"  - Analiz/dzień/symbol: {analyses_per_day}")
    print(f"  - Liczba symboli: {symbols_count}")
    print(f"  - Analiz/miesiąc: {analyses_per_month:,}")
    print()
    
    for model in ["gpt-4o", "gpt-4o-mini"]:
        cost_per_analysis = strategy._estimate_cost(tokens_long, model)
        monthly_cost = cost_per_analysis * analyses_per_month
        yearly_cost = monthly_cost * 12
        
        print(f"{model}:")
        print(f"  Koszt/analiza: ${cost_per_analysis:.6f}")
        print(f"  Koszt/miesiąc: ${monthly_cost:.2f}")
        print(f"  Koszt/rok: ${yearly_cost:.2f}")
        print()
    
    # Test 6: Rekomendacje
    print(f"\n--- Test 6: Rekomendacje ---")
    
    gpt4o_cost_month = strategy._estimate_cost(tokens_long, "gpt-4o") * analyses_per_month
    gpt4o_mini_cost_month = strategy._estimate_cost(tokens_long, "gpt-4o-mini") * analyses_per_month
    savings = gpt4o_cost_month - gpt4o_mini_cost_month
    savings_percent = (savings / gpt4o_cost_month) * 100
    
    print(f"Porównanie gpt-4o vs gpt-4o-mini:")
    print(f"  gpt-4o miesięcznie: ${gpt4o_cost_month:.2f}")
    print(f"  gpt-4o-mini miesięcznie: ${gpt4o_mini_cost_month:.2f}")
    print(f"  Oszczędności: ${savings:.2f} ({savings_percent:.1f}%)")
    print()
    print(f"💡 Rekomendacja: Użyj gpt-4o-mini dla oszczędności")
    print(f"   lub ogranicz liczbę symboli/częstotliwość analiz")
    
    # Test 7: Różne scenariusze
    print(f"\n--- Test 7: Różne scenariusze użycia ---")
    
    scenarios = [
        ("Tylko 5 głównych par Forex, co 30 min", 5, 48),
        ("10 symboli, co 15 min", 10, 96),
        ("Wszystkie 25 symboli, co 15 min", 25, 96),
        ("Wszystkie 25 symboli, co 1h", 25, 24),
    ]
    
    for scenario_name, symbols, analyses_per_day_sym in scenarios:
        monthly_analyses = analyses_per_day_sym * 30 * symbols
        cost_4o = strategy._estimate_cost(tokens_long, "gpt-4o") * monthly_analyses
        cost_mini = strategy._estimate_cost(tokens_long, "gpt-4o-mini") * monthly_analyses
        
        print(f"\n{scenario_name}:")
        print(f"  Analiz/miesiąc: {monthly_analyses:,}")
        print(f"  gpt-4o: ${cost_4o:.2f}/miesiąc")
        print(f"  gpt-4o-mini: ${cost_mini:.2f}/miesiąc")
    
    print("\n" + "="*80)
    print("TEST ZAKOŃCZONY")
    print("="*80)
    
    return True


if __name__ == "__main__":
    try:
        test_token_counting()
        print("\n✅ Wszystkie testy liczenia tokenów przeszły pomyślnie!")
    except Exception as e:
        print(f"\n❌ Błąd w testach: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
