# Etap 4: AutoAnalysisScheduler - Automatyczne Analizy AI

## Przegląd

Etap 4 implementuje automatyczny system analiz AI, który uruchamia kompleksowe analizy dla konfigurowalnej listy symboli w regularnych interwałach (domyślnie co 30 minut).

## Główne komponenty

### 1. AutoAnalysisScheduler

Główna klasa odpowiedzialna za automatyczne analizy AI.

**Lokalizacja**: `backend/app/services/auto_analysis_scheduler.py`

**Funkcje**:
- Pobiera listę symboli z konfiguracji (tabela `analysis_config`)
- Uruchamia `comprehensive_analysis()` dla każdego symbolu
- Agreguje sygnały przez `SignalAggregatorService`
- Zapisuje wyniki do bazy (`ai_analysis_results`)
- Wysyła powiadomienia Telegram dla sygnałów >= threshold
- Monitoruje tokeny i koszty OpenAI

### 2. Integracja z Schedulerem

AutoAnalysisScheduler jest zintegrowany z istniejącym schedulerem w `backend/app/scheduler.py`.

**Przepływ**:
1. Scheduler uruchamia `run_auto_analysis()` co X minut (domyślnie 30)
2. AutoAnalysisScheduler pobiera listę symboli
3. Dla każdego symbolu:
   - Uruchamia comprehensive_analysis (4 źródła: AI, Technical, Macro, News)
   - Agreguje sygnały (głosowanie większościowe)
   - Zapisuje do bazy
   - Wysyła powiadomienie jeśli spełnia kryteria
4. Loguje statystyki (tokeny, koszt, czas)

## Konfiguracja

### Zmienne środowiskowe (.env)

```env
# Interwał automatycznych analiz AI (w minutach)
ANALYSIS_INTERVAL=30

# Czy automatyczne analizy AI są włączone (true/false)
ANALYSIS_ENABLED=true

# Maksymalna liczba symboli do analizy
ANALYSIS_SYMBOLS_LIMIT=10

# Timeout dla pojedynczej analizy (w sekundach)
ANALYSIS_TIMEOUT=60

# Pauza między analizami symboli (w sekundach)
ANALYSIS_PAUSE_BETWEEN_SYMBOLS=2
```

### Domyślna lista symboli

Jeśli brak konfiguracji w bazie, używana jest domyślna lista 10 symboli:

**Forex (4)**:
- EUR/USD
- GBP/USD
- USD/JPY
- AUD/USD

**Indeksy (2)**:
- SPX/USD
- DJI/USD

**Akcje (3)**:
- AAPL/USD
- MSFT/USD
- TSLA/USD

**Metale (1)**:
- XAU/USD

## Uruchamianie

### 1. Uruchom scheduler z automatycznymi analizami

```bash
cd backend
python -m app.scheduler
```

Scheduler automatycznie:
- Uruchomi pierwsze sprawdzenie sygnałów strategii
- Zaplanuje automatyczne analizy AI co 30 minut
- Poczeka 30 minut przed pierwszą analizą AI

### 2. Test integracji (bez czekania 30 minut)

```bash
cd backend
python test_etap4_integration.py
```

Ten test:
- Inicjalizuje wszystkie serwisy
- Uruchamia analizę dla 2 symboli (EUR/USD, GBP/USD)
- Wyświetla wyniki i statystyki
- Nie wysyła powiadomień Telegram (test mode)

## Przepływ danych

```
Scheduler (co 30 min)
    ↓
AutoAnalysisScheduler.run_analysis_cycle()
    ↓
Dla każdego symbolu:
    ↓
    1. AIStrategy.comprehensive_analysis()
       ├─ AI Analysis (OpenAI GPT)
       ├─ Technical Analysis (RSI, MACD, MA, Bollinger)
       ├─ Macro Analysis (Fed, inflacja, PKB)
       └─ News Analysis (sentiment wiadomości)
    ↓
    2. SignalAggregatorService.aggregate_signals()
       └─ Głosowanie większościowe (wagi: AI=40%, Tech=30%, Macro=20%, News=10%)
    ↓
    3. Database.create_ai_analysis_result()
       └─ Zapis do tabeli ai_analysis_results
    ↓
    4. Jeśli agreement_score >= 60% AND signal = BUY/SELL:
       └─ TelegramService.send_message()
```

## Przykładowy log

```
⏰ Starting auto AI analysis cycle...
📊 Analyzing EUR/USD...
  ✓ EUR/USD: BUY (75% agreement)
📊 Analyzing GBP/USD...
  ✓ GBP/USD: SELL (68% agreement)
📊 Analyzing USD/JPY...
  ✓ USD/JPY: HOLD (45% agreement)
...
✅ Auto analysis completed in 45.2s | Analyzed: 10, Signals: 3, Cost: $0.2250
💰 Token usage: 25000 tokens, Estimated cost: $0.2250
```

## Monitorowanie kosztów

### Szacunki miesięczne

**Scenariusz 1: 10 symboli, co 30 minut**
- Analiz/dzień: 48 cykli × 10 symboli = 480 analiz
- Analiz/miesiąc: 480 × 30 = 14,400 analiz
- Tokeny/miesiąc: 14,400 × 2,500 = 36,000,000 tokenów
- **Koszt gpt-4o**: ~$324/miesiąc
- **Koszt gpt-4o-mini**: ~$32/miesiąc ✅ Rekomendowane

**Scenariusz 2: 5 symboli, co 1 godzina**
- Analiz/dzień: 24 cykli × 5 symboli = 120 analiz
- Analiz/miesiąc: 120 × 30 = 3,600 analiz
- **Koszt gpt-4o**: ~$81/miesiąc
- **Koszt gpt-4o-mini**: ~$8/miesiąc ✅ Bardzo ekonomiczne

### Rekomendacje oszczędności

1. **Użyj gpt-4o-mini** (10x taniej):
   ```env
   OPENAI_MODEL=gpt-4o-mini
   ```

2. **Ogranicz liczbę symboli** (5-10 zamiast 25)

3. **Zwiększ interwał** (60 min zamiast 30 min)

4. **Monitoruj koszty** przez dashboard (Etap 6)

## Obsługa błędów

System jest odporny na błędy:

### 1. Błąd pojedynczego symbolu
- Loguje błąd
- Kontynuuje z następnym symbolem
- Nie przerywa całego cyklu

### 2. Timeout analizy
- Domyślnie 60 sekund
- Po timeout loguje warning
- Kontynuuje z następnym symbolem

### 3. Brak klucza OpenAI
- AI analysis zwraca HOLD z confidence=0
- Pozostałe źródła (technical, macro, news) działają normalnie
- Agregator radzi sobie z niepełnymi danymi

### 4. Błąd całego cyklu
- Loguje błąd do pliku
- Wysyła alert Telegram (jeśli możliwe)
- Scheduler kontynuuje i spróbuje ponownie za X minut

## Baza danych

### Tabela: ai_analysis_results

Przechowuje wszystkie wyniki analiz AI (nie tylko sygnały).

**Główne kolumny**:
- `symbol` - Symbol (EUR/USD, AAPL/USD, etc.)
- `timeframe` - Interwał czasowy (1h, 4h, 1d)
- `ai_recommendation` - Rekomendacja AI (BUY/SELL/HOLD)
- `ai_confidence` - Pewność AI (0-100%)
- `technical_signal` - Sygnał techniczny
- `macro_signal` - Sygnał makro
- `news_sentiment` - Sentiment wiadomości
- `final_signal` - Finalny sygnał po agregacji
- `agreement_score` - Zgodność źródeł (0-100%)
- `tokens_used` - Zużyte tokeny OpenAI
- `estimated_cost` - Szacowany koszt w USD
- `timestamp` - Czas analizy

### Tabela: analysis_config

Konfiguracja automatycznych analiz.

**Kolumny**:
- `analysis_interval` - Interwał w minutach
- `enabled_symbols` - Lista symboli (JSON)
- `notification_threshold` - Próg powiadomień (%)
- `is_active` - Czy analizy są włączone

## Statystyki

Po każdym cyklu, AutoAnalysisScheduler zapisuje statystyki:

```python
{
    "timestamp": "2026-01-16T20:00:00",
    "analyzed_count": 10,
    "signals_count": 3,
    "errors_count": 0,
    "total_tokens": 25000,
    "total_cost": 0.225,
    "duration_seconds": 45.2
}
```

Dostęp przez:
```python
stats = scheduler.get_statistics()
```

## Testowanie

### Test 1: Integracja (2 symbole)

```bash
cd backend
python test_etap4_integration.py
```

Testuje:
- Inicjalizację wszystkich serwisów
- Uruchomienie cyklu analiz
- Zapis do bazy
- Statystyki

### Test 2: Pojedynczy symbol

```python
import asyncio
from app.services.auto_analysis_scheduler import AutoAnalysisScheduler

async def test():
    scheduler = AutoAnalysisScheduler(db, telegram)
    result = await scheduler.analyze_symbol("EUR/USD", "1h")
    print(f"Signal: {result['final_signal']}")
    print(f"Agreement: {result['agreement_score']}%")

asyncio.run(test())
```

### Test 3: Sprawdź bazę danych

```bash
sqlite3 backend/data/trading_bot.db "
SELECT 
    symbol, 
    final_signal, 
    agreement_score, 
    tokens_used,
    estimated_cost,
    timestamp 
FROM ai_analysis_results 
ORDER BY timestamp DESC 
LIMIT 10;
"
```

## Logi

Logi są zapisywane w:
- `backend/data/logs/scheduler.log` - Główny log schedulera
- `backend/data/logs/bot.log` - Log aplikacji

**Przykładowe logi**:
```
[2026-01-16 20:00:00] INFO - ⏰ Starting auto AI analysis cycle...
[2026-01-16 20:00:05] INFO - 📊 Analyzing EUR/USD...
[2026-01-16 20:00:10] INFO -   ✓ EUR/USD: BUY (75% agreement)
[2026-01-16 20:00:45] INFO - ✅ Auto analysis completed in 45.2s
```

## Następne kroki

Po ukończeniu Etapu 4:

- **Etap 5**: Nowe endpointy API
  - `/ai/analysis-results` - Lista wyników analiz
  - `/ai/token-statistics` - Statystyki tokenów
  - `/ai/trigger-analysis` - Ręczne uruchomienie
  
- **Etap 6**: Dashboard frontend
  - Panel wyników analiz
  - Statystyki tokenów i kosztów
  - Konfiguracja symboli i interwału

## Rozwiązywanie problemów

### Problem: Analizy nie uruchamiają się

**Rozwiązanie**:
1. Sprawdź czy `ANALYSIS_ENABLED=true` w `.env`
2. Sprawdź logi: `tail -f backend/data/logs/scheduler.log`
3. Sprawdź czy scheduler działa: `ps aux | grep scheduler`

### Problem: Wysokie koszty OpenAI

**Rozwiązanie**:
1. Zmień model na `gpt-4o-mini` w `.env`
2. Ogranicz liczbę symboli (5-10)
3. Zwiększ interwał (60 min zamiast 30 min)
4. Monitoruj tokeny w logach

### Problem: Timeout analiz

**Rozwiązanie**:
1. Zwiększ `ANALYSIS_TIMEOUT` w `.env` (np. 90)
2. Sprawdź połączenie internetowe
3. Sprawdź czy OpenAI API działa

### Problem: Brak powiadomień Telegram

**Rozwiązanie**:
1. Sprawdź czy `agreement_score >= 60%`
2. Sprawdź czy `final_signal` to BUY lub SELL (nie HOLD)
3. Sprawdź konfigurację Telegram w `.env`

## Pliki

### Nowe pliki
- `backend/app/services/auto_analysis_scheduler.py` - Główna implementacja
- `backend/test_etap4_integration.py` - Test integracji
- `backend/ETAP4_README.md` - Ta dokumentacja

### Zmodyfikowane pliki
- `backend/app/scheduler.py` - Integracja z AutoAnalysisScheduler
- `backend/app/config.py` - Nowe zmienne konfiguracyjne
- `.env.example` - Przykładowa konfiguracja

## Licencja

Ten projekt jest częścią Ghost-Trader.
