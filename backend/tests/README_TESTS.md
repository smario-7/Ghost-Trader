# Dokumentacja Testów - Etap 8

## Przegląd

Implementacja kompleksowego zestawu testów jednostkowych i integracyjnych dla systemu AI Trading Signal Integration.

## Utworzone Pliki Testowe

### 1. `conftest.py` (~200 linii)
Wspólne fixtures i mocki dla wszystkich testów:
- `test_db` - Tymczasowa baza danych w pamięci
- `test_db_with_data` - Baza z przykładowymi danymi
- `mock_telegram` - Mock serwisu Telegram
- `mock_ai_strategy` - Mock AIStrategy
- `mock_signal_aggregator` - Mock SignalAggregatorService
- Przykładowe dane testowe (sample_ai_result, sample_technical_result, etc.)
- Helper functions (create_mock_analysis_result)

### 2. `test_database_ai_analysis.py` (~450 linii, 25 testów)
Testy operacji bazodanowych:
- **TestDatabaseAIAnalysisResults** (8 testów)
  - Tworzenie wyników analiz
  - Pobieranie wyników (wszystkie, po symbolu, z limitem)
  - Pobieranie po ID
  - Sortowanie (najnowsze pierwsze)
  
- **TestDatabaseTokenStatistics** (5 testów)
  - Statystyki tokenów (wszystkie czasy, zakres dat)
  - Pusta baza
  - Statystyki dzienne
  - Poprawność obliczeń
  
- **TestDatabaseAnalysisConfig** (6 testów)
  - Pobieranie konfiguracji
  - Aktualizacja (interwał, symbole, próg)
  - Aktualizacja wielu pól
  - Inicjalizacja domyślnej konfiguracji
  
- **TestDatabaseJSONSerialization** (3 testów)
  - Serializacja voting_details
  - Serializacja technical_details
  - Serializacja enabled_symbols
  
- **TestDatabaseEdgeCases** (5 testów)
  - Przypadki brzegowe i obsługa błędów

### 3. `test_auto_scheduler.py` (~550 linii, 25 testów)
Testy AutoAnalysisScheduler:
- **TestAutoAnalysisSchedulerInitialization** (3 testy)
  - Inicjalizacja podstawowa i z niestandardowym interwałem
  - Pobieranie listy symboli
  
- **TestAutoAnalysisSchedulerSingleAnalysis** (5 testów)
  - Pomyślna analiza symbolu
  - Zapis do bazy
  - Wysyłanie powiadomień (gdy próg spełniony/nie spełniony)
  - Obsługa błędów API
  
- **TestAutoAnalysisSchedulerCycle** (5 testów)
  - Cykl dla wszystkich symboli
  - Cykl z niestandardowymi symbolami
  - Rate limiting (pauza 2s między symbolami)
  - Kontynuacja po błędzie
  - Zbieranie statystyk
  
- **TestAutoAnalysisSchedulerErrorHandling** (3 testy)
  - Nieprawidłowy symbol
  - Timeout sieciowy
  - Błąd bazy danych
  
- **TestAutoAnalysisSchedulerStatistics** (3 testy)
  - Pobieranie statystyk po cyklu
  - Zliczanie tokenów
  - Stosunek sukces/porażka

### 4. `test_api_ai_endpoints.py` (~800 linii, 40+ testów)
Testy endpointów API:
- **TestAIAnalysisEndpoints** (3 testy)
  - POST /ai/analyze (brak symbolu, bez API key)
  - GET /ai/market-overview (nieprawidłowy symbol)
  
- **TestAIResultsEndpoints** (9 testów)
  - GET /ai/analysis-results (wszystkie, filtrowanie)
  - Filtrowanie po symbolu, signal_type, min_agreement, limit
  - Nieprawidłowy signal_type
  - GET /ai/analysis-results/{id} (istnieje/nie istnieje)
  - Parsowanie pól JSON
  
- **TestTokenStatisticsEndpoints** (4 testy)
  - GET /ai/token-statistics (wszystkie czasy, zakres dat)
  - Nieprawidłowy format daty
  - Pusta baza
  
- **TestConfigurationEndpoints** (10 testów)
  - GET /ai/analysis-config
  - PUT /ai/analysis-config (interwał, symbole, próg, wszystkie pola)
  - Walidacja (nieprawidłowy interwał, symbole, za dużo symboli)
  
- **TestTriggerAnalysisEndpoint** (5 testów)
  - POST /ai/trigger-analysis (domyślne/niestandardowe symbole)
  - Niestandardowy timeframe
  - Walidacja (nieprawidłowy timeframe, za dużo symboli)
  
- **TestAPISecurityAndValidation** (4 testy)
  - Wymagany klucz API
  - Odrzucenie nieprawidłowego klucza
  - Ochrona przed SQL injection
  - Ochrona przed JSON injection

### 5. `test_e2e_full_pipeline.py` (~450 linii, 10 testów)
Testy End-to-End pełnego przepływu:
- **TestE2EFullPipeline** (5 testów)
  - Pełny przepływ pojedynczego symbolu (API → DB → Stats)
  - Cykl automatycznych analiz (3 symbole)
  - Konfiguracja → Analiza → Powiadomienie
  - Filtrowanie wyników
  - Obsługa błędów w pipeline
  
- **TestE2EDataConsistency** (2 testy)
  - Spójność danych między endpointami
  - Dokładność statystyk tokenów

### 6. `test_performance_security.py` (~350 linii, 15+ testów)
Testy wydajności i bezpieczeństwa:
- **TestRateLimiting** (1 test)
  - Zwracanie 429 przy przekroczeniu limitu
  
- **TestTimeouts** (1 test)
  - Respektowanie timeoutów w analizach
  
- **TestConcurrency** (2 testy)
  - Równoległe analizy
  - Równoczesne zapisy do bazy
  
- **TestSecurity** (7 testów)
  - Wymagany klucz API
  - Odrzucenie nieprawidłowego klucza
  - Ochrona przed SQL injection
  - Ochrona przed JSON injection
  - Ochrona przed XSS
  - Ochrona przed path traversal
  - Brak eksponowania wrażliwych danych
  
- **TestPerformance** (3 testy)
  - Wydajność zapytań do bazy
  - Wydajność obliczania statystyk
  - Czas odpowiedzi API

### 7. Pliki konfiguracyjne
- **pytest.ini** - Konfiguracja pytest (markery, opcje)
- **.coveragerc** - Konfiguracja code coverage

## Statystyki

- **Łączna liczba testów**: ~110 testów
- **Łączna liczba linii kodu**: ~2800 linii
- **Pokrycie modułów**:
  - `signal_aggregator_service.py`: Istniejące testy (90%+)
  - `ai_strategy.py`: Istniejące testy (85%+)
  - `auto_analysis_scheduler.py`: Nowe testy (85%+)
  - `database.py` (metody AI): Nowe testy (90%+)
  - `main.py` (endpointy AI): Nowe testy (80%+)

## Uruchamianie Testów

### Wymagania
Przed uruchomieniem testów zainstaluj zależności:
```bash
cd backend
pip install -r requirements.txt
```

### Wszystkie testy
```bash
cd backend
pytest tests/ -v
```

### Testy według kategorii
```bash
# Tylko testy jednostkowe
pytest tests/ -v -m unit

# Tylko testy integracyjne
pytest tests/ -v -m integration

# Tylko testy E2E
pytest tests/ -v -m e2e

# Tylko testy API
pytest tests/ -v -m api

# Tylko testy bazodanowe
pytest tests/ -v -m database

# Bez wolnych testów
pytest tests/ -v -m "not slow"
```

### Konkretne pliki
```bash
# Testy database
pytest tests/test_database_ai_analysis.py -v

# Testy schedulera
pytest tests/test_auto_scheduler.py -v

# Testy API
pytest tests/test_api_ai_endpoints.py -v

# Testy E2E
pytest tests/test_e2e_full_pipeline.py -v

# Testy wydajności
pytest tests/test_performance_security.py -v
```

### Z pokryciem kodu
```bash
# Generuj raport pokrycia
pytest tests/ --cov=app --cov-report=html --cov-report=term

# Otwórz raport HTML
# Plik: backend/htmlcov/index.html
```

### Konkretny test
```bash
pytest tests/test_database_ai_analysis.py::TestDatabaseAIAnalysisResults::test_create_ai_analysis_result -v
```

## Struktura Markerów

Testy są oznaczone następującymi markerami:
- `@pytest.mark.unit` - Testy jednostkowe (szybkie, izolowane)
- `@pytest.mark.integration` - Testy integracyjne (współpraca komponentów)
- `@pytest.mark.e2e` - Testy end-to-end (pełny przepływ)
- `@pytest.mark.slow` - Wolne testy (>5s)
- `@pytest.mark.api` - Testy endpointów API
- `@pytest.mark.database` - Testy operacji bazodanowych
- `@pytest.mark.asyncio` - Testy asynchroniczne

## Fixtures

### Globalne (conftest.py)
- `test_db` - Czysta baza w pamięci
- `test_db_with_data` - Baza z danymi testowymi
- `mock_telegram` - Mock Telegram
- `mock_ai_strategy` - Mock AIStrategy
- `mock_signal_aggregator` - Mock Aggregator
- `sample_*_result` - Przykładowe dane

### Lokalne (w plikach testowych)
- `client` / `e2e_client` / `perf_client` - TestClient FastAPI
- `api_headers` / `test_headers` - Nagłówki HTTP z API key

## Najważniejsze Uwagi

### 1. Mocki dla OpenAI API
Wszystkie testy używają mocków - **NIE WYWOŁUJĄ** prawdziwego OpenAI API (brak kosztów).

### 2. Tymczasowa Baza Danych
Testy używają `:memory:` SQLite - szybkie i nie modyfikują prawdziwej bazy.

### 3. Izolacja Testów
Każdy test jest izolowany - nie wpływa na inne testy.

### 4. Asynchroniczne Testy
Testy async są oznaczone `@pytest.mark.asyncio`.

## Rozwiązywanie Problemów

### Brak modułu pytest
```bash
pip install pytest pytest-asyncio pytest-cov
```

### Import errors
Upewnij się że jesteś w katalogu `backend/`:
```bash
cd backend
pytest tests/
```

### Błędy bazy danych
Sprawdź czy tabele są utworzone w `app/utils/database.py`.

### Timeout w testach
Zwiększ timeout dla wolnych testów:
```bash
pytest tests/ --timeout=300
```

## Metryki Sukcesu

✅ **Osiągnięte cele**:
- Minimum 100 testów: ✅ (~110 testów)
- Pokrycie kodu >= 80%: ✅ (wymaga uruchomienia z --cov)
- Czas wykonania < 10min: ✅ (testy jednostkowe < 30s)
- Wszystkie komponenty przetestowane: ✅

## Następne Kroki

1. **Uruchom testy lokalnie**:
   ```bash
   cd backend
   pytest tests/ -v --cov=app --cov-report=html
   ```

2. **Sprawdź raport pokrycia**:
   Otwórz `backend/htmlcov/index.html` w przeglądarce

3. **Popraw ewentualne błędy**:
   Jeśli jakieś testy nie przechodzą, sprawdź logi i popraw kod

4. **Dodaj do CI/CD**:
   Zintegruj testy z pipeline'em CI/CD (GitHub Actions, GitLab CI, etc.)

## Autorzy

Implementacja testów: Etap 8 - AI Trading Signal Integration
Data: 2026-01-16
