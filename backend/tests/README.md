# Testy dla Ghost Trader

## Struktura

```
tests/
├── __init__.py
├── test_signal_aggregator.py    # Testy jednostkowe dla SignalAggregatorService
├── test_integration.py           # Testy integracyjne
└── README.md                     # Ten plik
```

## Uruchamianie Testów

### Wszystkie testy
```bash
cd backend
python3 -m pytest tests/ -v
```

### Konkretny plik testów
```bash
cd backend
python3 -m pytest tests/test_signal_aggregator.py -v
```

### Testy z output
```bash
cd backend
python3 -m pytest tests/ -v -s
```

### Prosty test bez zależności
```bash
cd backend
python3 test_etap2_simple.py
```

## Wymagania

Przed uruchomieniem testów zainstaluj zależności:
```bash
pip install -r requirements.txt
```

Lub tylko pytest:
```bash
pip install pytest pytest-asyncio
```

## Pokrycie Testów

### SignalAggregatorService
- ✅ Inicjalizacja z domyślnymi wagami
- ✅ Inicjalizacja z niestandardowymi wagami
- ✅ Normalizacja sygnałów AI
- ✅ Normalizacja sygnałów technicznych
- ✅ Normalizacja sygnałów makro
- ✅ Normalizacja sentimentu wiadomości
- ✅ Głosowanie większościowe (BUY)
- ✅ Głosowanie większościowe (SELL)
- ✅ Sprzeczne sygnały
- ✅ Wszystkie źródła HOLD
- ✅ Generowanie uzasadnienia decyzji
- ✅ Decyzja o powiadomieniu (powyżej progu)
- ✅ Decyzja o powiadomieniu (poniżej progu)
- ✅ Decyzja o powiadomieniu (HOLD)
- ✅ Decyzja o powiadomieniu (NO_SIGNAL)
- ✅ Pełna agregacja sygnałów
- ✅ Agregacja z błędnymi danymi
- ✅ Aktualizacja wag
- ✅ Aktualizacja wag z nieprawidłową sumą

### AIStrategy
- ✅ Comprehensive analysis
- ✅ Liczenie tokenów
- ✅ Szacowanie kosztów
- ✅ Analiza wskaźników technicznych
- ✅ Analiza danych makro
- ✅ Analiza sentimentu wiadomości

### Integracja
- ✅ Pełny pipeline (comprehensive_analysis + aggregate_signals)
- ✅ Token counting i cost estimation
- ✅ Technical signal analysis
- ✅ Macro signal analysis
- ✅ News sentiment analysis

## Uwagi

- Niektóre testy integracyjne mogą wymagać API keys (OpenAI, yfinance)
- Testy są zaprojektowane tak, aby gracefully fail jeśli brakuje API keys
- Używaj `pytest.skip()` dla testów wymagających zewnętrznych zasobów
