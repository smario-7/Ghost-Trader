# Etap 3: AI Strategy Comprehensive Analysis

## Przegląd

Etap 3 rozbudowuje `AIStrategy` o metodę `comprehensive_analysis()`, która zbiera dane z 4 różnych źródeł i przygotowuje je do agregacji sygnałów.

## Główne komponenty

### 1. `comprehensive_analysis()` - Główna metoda

Zbiera dane z wszystkich źródeł i zwraca ustandaryzowany format:

```python
strategy = AIStrategy(telegram_service=telegram)
result = await strategy.comprehensive_analysis("EUR/USD", "1h")

# Wynik zawiera:
# - ai_analysis: Analiza OpenAI GPT
# - technical_analysis: Wskaźniki techniczne
# - macro_analysis: Dane makroekonomiczne
# - news_analysis: Sentiment wiadomości
```

### 2. Liczenie tokenów i kosztów

System automatycznie liczy tokeny OpenAI i szacuje koszty:

```python
# Metoda _count_tokens() szacuje tokeny
tokens = strategy._count_tokens(prompt_text)

# Metoda _estimate_cost() szacuje koszt
cost = strategy._estimate_cost(tokens, "gpt-4o")
```

**Szacowane koszty miesięczne:**

| Scenariusz | Analiz/miesiąc | gpt-4o | gpt-4o-mini |
|------------|----------------|--------|-------------|
| 5 symboli, co 30 min | 7,200 | $162 | $16 |
| 10 symboli, co 15 min | 28,800 | $648 | $65 |
| 25 symboli, co 15 min | 72,000 | $1,620 | $162 |
| 25 symboli, co 1h | 18,000 | $405 | $41 |

💡 **Rekomendacja**: Użyj `gpt-4o-mini` dla oszczędności (10x taniej) lub ogranicz liczbę symboli/częstotliwość.

### 3. Analiza wskaźników technicznych

Metoda `_analyze_technical_signal()` interpretuje:

- **RSI** (Relative Strength Index)
  - < 30: Oversold → sygnał BUY
  - > 70: Overbought → sygnał SELL
  - 30-70: Neutral → HOLD

- **MACD** (Moving Average Convergence Divergence)
  - MACD > Signal: Bullish → BUY
  - MACD < Signal: Bearish → SELL

- **Moving Averages**
  - Golden Cross (MA50 > MA200) → BUY
  - Death Cross (MA50 < MA200) → SELL

- **Bollinger Bands**
  - Cena przy dolnej wstędze → BUY
  - Cena przy górnej wstędze → SELL

### 4. Analiza makroekonomiczna

Metoda `_analyze_macro_signal()` ocenia:

- **Stopy procentowe Fed**
- **Inflacja (CPI)**
- **Wzrost PKB**
- **Bezrobocie**

Zwraca sygnał BUY/SELL/HOLD z oceną wpływu (positive/negative/neutral).

### 5. Analiza sentimentu wiadomości

Metoda `_analyze_news_sentiment()` analizuje:

- Sentiment wiadomości (positive/negative/neutral)
- Score 0-100%
- Liczba wiadomości

## Integracja z Signal Aggregator

Wyniki z `comprehensive_analysis()` są przekazywane do `SignalAggregatorService`:

```python
# Krok 1: Comprehensive analysis
analysis = await ai_strategy.comprehensive_analysis("EUR/USD", "1h")

# Krok 2: Agregacja sygnałów
result = await aggregator.aggregate_signals(
    symbol=analysis['symbol'],
    timeframe=analysis['timeframe'],
    ai_result=analysis['ai_analysis'],
    technical_result=analysis['technical_analysis'],
    macro_result=analysis['macro_analysis'],
    news_result=analysis['news_analysis']
)

# Krok 3: Sprawdź wynik
if result['should_notify']:
    # Wyślij powiadomienie Telegram
    await telegram.send_message(...)
```

## Uruchamianie demo

### Demo Etapu 3

```bash
cd backend
python3 demo_etap3.py
```

Demo pokazuje:
1. Liczenie tokenów i szacowanie kosztów
2. Analizę wskaźników technicznych
3. Analizę danych makroekonomicznych
4. Analizę sentimentu wiadomości
5. Pełny pipeline: comprehensive_analysis + agregacja

### Testy jednostkowe

```bash
cd backend
pytest tests/test_ai_strategy_comprehensive.py -v
```

Testy obejmują:
- Liczenie tokenów dla różnych rozmiarów promptów
- Szacowanie kosztów dla różnych modeli
- Analizę wskaźników technicznych
- Analizę makro
- Analizę news
- Format odpowiedzi comprehensive_analysis()

### Testy integracyjne

```bash
cd backend
pytest tests/test_integration.py -v
```

Testy integracyjne sprawdzają:
- Pełny pipeline: comprehensive_analysis → aggregate_signals
- Kompatybilność formatów danych
- Obsługę błędów

## Format danych

### Wejście do `comprehensive_analysis()`

```python
symbol: str = "EUR/USD"
timeframe: str = "1h"
```

### Wyjście z `comprehensive_analysis()`

```python
{
    "symbol": "EUR/USD",
    "timeframe": "1h",
    "timestamp": "2026-01-16T20:00:00",
    
    "ai_analysis": {
        "recommendation": "BUY",
        "confidence": 80,
        "reasoning": "...",
        "key_factors": [...],
        "tokens_used": 2500,
        "estimated_cost": 0.0225
    },
    
    "technical_analysis": {
        "signal": "BUY",
        "confidence": 70,
        "indicators": {
            "rsi": 45,
            "macd": {...},
            "sma_50": 1.0850,
            "sma_200": 1.0800,
            "price": 1.0875
        }
    },
    
    "macro_analysis": {
        "signal": "HOLD",
        "confidence": 50,
        "impact": "neutral",
        "summary": "Fed: 5.5%, Inflacja: 3.2%, PKB: 2.1%..."
    },
    
    "news_analysis": {
        "sentiment": "positive",
        "score": 65,
        "news_count": 5,
        "summary": "3 pozytywne, 1 negatywna, 1 neutralna"
    }
}
```

## Obsługa błędów

System ma kompleksową obsługę błędów:

1. **Brak klucza OpenAI API**
   - AI analysis zwraca HOLD z confidence=0
   - Pozostałe analizy działają normalnie

2. **Timeout przy pobieraniu danych**
   - Zwraca bezpieczne wartości domyślne
   - Loguje błąd do logów

3. **Błąd w jednym ze źródeł**
   - Pozostałe źródła działają normalnie
   - Agregator radzi sobie z brakującymi danymi

## Konfiguracja

### Model OpenAI

W pliku `.env`:

```env
OPENAI_MODEL=gpt-4o-mini  # Zalecane dla oszczędności
# lub
OPENAI_MODEL=gpt-4o       # Lepsza jakość, droższe
```

### Wagi dla agregacji

W pliku `.env`:

```env
AGGREGATOR_WEIGHT_AI=40
AGGREGATOR_WEIGHT_TECHNICAL=30
AGGREGATOR_WEIGHT_MACRO=20
AGGREGATOR_WEIGHT_NEWS=10
```

Suma wag musi wynosić 100.

## Pliki

### Główne pliki

- `backend/app/services/ai_strategy.py` - Główna implementacja
- `backend/app/services/signal_aggregator_service.py` - Agregacja sygnałów (Etap 2)
- `backend/app/utils/database.py` - Baza danych (Etap 1)

### Testy

- `backend/tests/test_ai_strategy_comprehensive.py` - Testy jednostkowe
- `backend/tests/test_integration.py` - Testy integracyjne
- `backend/test_token_counting.py` - Test liczenia tokenów

### Demo

- `backend/demo_etap3.py` - Demo Etapu 3
- `backend/demo_etap2.py` - Demo Etapu 2 (z integracją)

## Następne kroki

Po ukończeniu Etapu 3, można przejść do:

- **Etap 4**: AutoAnalysisScheduler - automatyczne analizy dla wszystkich symboli
- **Etap 5**: Nowe endpointy API
- **Etap 6**: Rozbudowa dashboard frontend

## Wsparcie

Jeśli masz pytania lub problemy:

1. Sprawdź logi w `backend/app/utils/logger.py`
2. Uruchom testy: `pytest tests/ -v`
3. Sprawdź demo: `python3 demo_etap3.py`

## Licencja

Ten projekt jest częścią Ghost-Trader.
