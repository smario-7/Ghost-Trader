# AI Signal Integration - Dokumentacja Systemu

## Spis treści

- [Przegląd systemu](#przegląd-systemu)
- [Algorytm decyzyjny](#algorytm-decyzyjny)
- [Komponenty systemu](#komponenty-systemu)
- [API Endpoints](#api-endpoints)
- [Baza danych](#baza-danych)
- [Konfiguracja środowiska](#konfiguracja-środowiska)
- [Frontend Dashboard](#frontend-dashboard)
- [Koszty OpenAI](#koszty-openai)
- [Przykłady użycia](#przykłady-użycia)
- [Testy](#testy)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Przegląd systemu

System **AI Signal Integration** to zaawansowany mechanizm generowania sygnałów tradingowych, który łączy analizy z 4 różnych źródeł i używa głosowania większościowego do podejmowania decyzji.

### Architektura

System składa się z 4 źródeł analiz:

1. **AI Analysis (40% wagi)** - Analiza OpenAI GPT-4o
   - Plik: `backend/app/services/ai_strategy.py`
   - Metoda: `AIStrategy.comprehensive_analysis()`
   - Wykorzystuje: OpenAI API do kompleksowej analizy rynku

2. **Technical Indicators (30% wagi)** - Wskaźniki techniczne
   - Plik: `backend/app/services/strategy_service.py`
   - Wskaźniki: RSI, MACD, Moving Averages, Bollinger Bands
   - Źródło danych: Yahoo Finance przez `market_data_service.py`

3. **Macro Data (20% wagi)** - Dane makroekonomiczne
   - Plik: `backend/app/services/market_data_service.py`
   - Dane: Stopy Fed, inflacja (CPI), wzrost PKB
   - Wpływ na rynki walutowe i akcyjne

4. **News Sentiment (10% wagi)** - Analiza wiadomości finansowych
   - Plik: `backend/app/services/data_collection_service.py`
   - Sentiment: positive/negative/neutral
   - Źródło: Wiadomości finansowe z ostatnich 24h

### Przepływ danych

```
┌─────────────────────────────────────────────────────────────┐
│                  AutoAnalysisScheduler                      │
│                 (co 15-30 minut, domyślnie)                 │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              AIStrategy.comprehensive_analysis()            │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ AI Analysis  │  │  Technical   │  │  Macro Data  │     │
│  │   (GPT-4o)   │  │  Indicators  │  │  (Fed, CPI)  │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
│         │                 │                 │              │
│         └─────────────────┼─────────────────┘              │
│                           │                                │
│                  ┌────────▼────────┐                       │
│                  │  News Sentiment │                       │
│                  └────────┬────────┘                       │
└───────────────────────────┼──────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│           SignalAggregatorService.aggregate_signals()       │
│                                                             │
│  Głosowanie większościowe z wagami:                        │
│  - AI: 40%                                                  │
│  - Technical: 30%                                           │
│  - Macro: 20%                                               │
│  - News: 10%                                                │
│                                                             │
│  Kryteria sygnału:                                          │
│  ✓ Agreement score >= 60% (konfigurowalne)                 │
│  ✓ Final signal = BUY lub SELL (nie HOLD)                  │
│  ✓ Co najmniej 3 z 4 źródeł wskazuje ten sam kierunek      │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    Zapis do bazy danych                     │
│              (tabela: ai_analysis_results)                  │
│                                                             │
│  Zawiera:                                                   │
│  - Wyniki z każdego źródła                                  │
│  - Finalny sygnał i agreement score                         │
│  - Statystyki tokenów i kosztów                             │
│  - Szczegóły głosowania                                     │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│            Jeśli should_notify = True                       │
│         → Powiadomienie Telegram + Dashboard                │
└─────────────────────────────────────────────────────────────┘
```

## Algorytm decyzyjny

### Głosowanie większościowe

System używa głosowania ważonego do określenia finalnego sygnału. Każde źródło "głosuje" na BUY, SELL lub HOLD z określonym poziomem pewności (confidence 0-100%).

**Wagi domyślne:**
```python
weights = {
    "ai": 40,        # Najwyższa waga - najbardziej kompleksowa analiza
    "technical": 30, # Druga waga - sprawdzone wskaźniki techniczne
    "macro": 20,     # Trzecia waga - kontekst makroekonomiczny
    "news": 10       # Najniższa waga - sentiment może być zmienny
}
```

### Obliczanie agreement score

1. **Normalizacja głosów** - każde źródło zwraca:
   ```python
   {
       "vote": "BUY" | "SELL" | "HOLD",
       "confidence": 0-100  # Pewność źródła
   }
   ```

2. **Weighted score** - dla każdego kierunku (BUY/SELL/HOLD):
   ```python
   weighted_score = (confidence * weight) / 100
   ```

3. **Wybór zwycięzcy** - kierunek z największym weighted_score

4. **Agreement score** - procent zgodności:
   ```python
   agreement_score = (winner_score / total_weighted_confidence) * 100
   ```

### Kryteria generowania sygnału

Sygnał jest generowany i wysyłane jest powiadomienie gdy:

1. **Agreement score >= threshold** (domyślnie 60%)
2. **Final signal = BUY lub SELL** (nie HOLD ani NO_SIGNAL)
3. **Co najmniej 3 z 4 źródeł** wskazuje ten sam kierunek (zalecane)

**Przykład:**
```
AI: BUY (confidence: 80%) → weighted: 32.0 (80 * 40 / 100)
Technical: BUY (confidence: 70%) → weighted: 21.0 (70 * 30 / 100)
Macro: HOLD (confidence: 50%) → weighted: 10.0 (50 * 20 / 100)
News: BUY (confidence: 65%) → weighted: 6.5 (65 * 10 / 100)

Total BUY score: 32.0 + 21.0 + 6.5 = 59.5
Total HOLD score: 10.0
Total weighted: 69.5

Final signal: BUY
Agreement score: (59.5 / 69.5) * 100 = 85.6%
Should notify: YES (85.6% >= 60% AND signal = BUY)
```

## Komponenty systemu

### 1. AutoAnalysisScheduler

**Plik:** `backend/app/services/auto_analysis_scheduler.py`

**Funkcje:**
- Automatyczne uruchamianie analiz w regularnych interwałach
- Zarządzanie listą symboli do analizy
- Rate limiting między symbolami (domyślnie 2s pauza)
- Monitorowanie kosztów i tokenów OpenAI
- Wysyłanie powiadomień Telegram

**Kluczowe metody:**

```python
class AutoAnalysisScheduler:
    async def run_analysis_cycle(self) -> List[Dict[str, Any]]:
        """
        Uruchamia pełny cykl analiz dla wszystkich symboli.
        
        Przepływ:
        1. Pobiera listę symboli z konfiguracji
        2. Dla każdego symbolu wywołuje analyze_symbol()
        3. Dodaje pauzę między symbolami (rate limiting)
        4. Zbiera statystyki (tokeny, koszty, błędy)
        
        Returns:
            Lista wyników analiz z agreement_score i kosztami
        """
    
    async def analyze_symbol(self, symbol: str, timeframe: str = "1h"):
        """
        Analizuje pojedynczy symbol:
        1. comprehensive_analysis() - zbiera dane z 4 źródeł
        2. aggregate_signals() - głosowanie większościowe
        3. Zapis do bazy danych
        4. Wysyłanie powiadomienia (jeśli spełnia kryteria)
        """
```

**Domyślna lista symboli:**
```python
DEFAULT_SYMBOLS = [
    # Forex (4)
    "EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD",
    # Indeksy (2)
    "SPX/USD", "DJI/USD",
    # Akcje (3)
    "AAPL/USD", "MSFT/USD", "TSLA/USD",
    # Metale (1)
    "XAU/USD"
]
```

### 2. SignalAggregatorService

**Plik:** `backend/app/services/signal_aggregator_service.py`

**Funkcje:**
- Agregacja sygnałów z 4 źródeł
- Głosowanie większościowe z wagami
- Obliczanie agreement score
- Generowanie uzasadnienia decyzji
- Decyzja o wysłaniu powiadomienia

**Kluczowe metody:**

```python
class SignalAggregatorService:
    async def aggregate_signals(
        self,
        symbol: str,
        timeframe: str,
        ai_result: Dict[str, Any],
        technical_result: Dict[str, Any],
        macro_result: Dict[str, Any],
        news_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Agreguje wszystkie sygnały i zwraca decyzję.
        
        Returns:
            {
                "final_signal": "BUY" | "SELL" | "HOLD" | "NO_SIGNAL",
                "agreement_score": 75,
                "weighted_score": 72.5,
                "voting_details": {...},
                "decision_reason": "...",
                "should_notify": True
            }
        """
    
    def _normalize_signal(self, source: str, result: Dict) -> Dict:
        """
        Normalizuje różne formaty wyników do wspólnego standardu:
        {"vote": "BUY/SELL/HOLD", "confidence": 0-100}
        
        Obsługuje różne formaty:
        - AI: {"recommendation": "BUY", "confidence": 80}
        - Technical: {"signal": "BUY", "confidence": 70}
        - Macro: {"signal": "HOLD", "impact": "neutral"}
        - News: {"sentiment": "positive", "score": 65}
        """
```

### 3. AIStrategy.comprehensive_analysis()

**Plik:** `backend/app/services/ai_strategy.py`

**Funkcje:**
- Zbiera dane z wszystkich 4 źródeł
- Uruchamia analizę OpenAI GPT
- Liczy tokeny i szacuje koszty
- Zwraca ustandaryzowany format wyników

**Kluczowa metoda:**

```python
class AIStrategy:
    async def comprehensive_analysis(
        self,
        symbol: str,
        timeframe: str = "1h"
    ) -> Dict[str, Any]:
        """
        Kompleksowa analiza zwracająca wyniki ze wszystkich źródeł.
        
        Przepływ:
        1. Pobiera dane makro (Fed, inflacja, PKB)
        2. Pobiera wiadomości (ostatnie 24h)
        3. Oblicza wskaźniki techniczne (RSI, MACD, MA, Bollinger)
        4. Wysyła wszystko do AI do analizy
        5. Liczy tokeny i koszt
        6. Analizuje każde źródło osobno
        
        Returns:
            {
                "symbol": "EUR/USD",
                "timeframe": "1h",
                "timestamp": "2026-01-16T20:00:00",
                
                "ai_analysis": {
                    "recommendation": "BUY",
                    "confidence": 80,
                    "reasoning": "...",
                    "tokens_used": 2500,
                    "estimated_cost": 0.0225
                },
                
                "technical_analysis": {
                    "signal": "BUY",
                    "confidence": 70,
                    "indicators": {...}
                },
                
                "macro_analysis": {
                    "signal": "HOLD",
                    "confidence": 50,
                    "impact": "neutral",
                    "summary": "..."
                },
                
                "news_analysis": {
                    "sentiment": "positive",
                    "score": 65,
                    "news_count": 5,
                    "summary": "..."
                }
            }
        """
```

**Liczenie tokenów i kosztów:**

```python
def _count_tokens(self, text: str) -> int:
    """
    Szacuje liczbę tokenów OpenAI.
    
    Przybliżenie: 1 token ≈ 4 znaki
    Dodaje buffer 300 tokenów na odpowiedź AI.
    """
    estimated_tokens = len(text) // 4
    estimated_tokens += 300  # Buffer na response
    return estimated_tokens

def _estimate_cost(self, tokens: int, model: str = "gpt-4o") -> float:
    """
    Szacuje koszt zapytania do OpenAI.
    
    Ceny (styczeń 2026):
    - gpt-4o: input $0.005/1K, output $0.015/1K
    - gpt-4o-mini: input $0.00015/1K, output $0.0006/1K
    
    Zakłada podział: 60% input, 40% output
    """
```

## API Endpoints

Wszystkie endpointy AI są zdefiniowane w `backend/app/main.py` i wymagają nagłówka `X-API-Key`.

### 1. Wyniki analiz

#### GET /ai/analysis-results

Pobiera listę wszystkich wyników analiz AI.

**Query parameters:**
- `symbol` (opcjonalny) - filtruj po symbolu (np. "EUR/USD")
- `limit` (opcjonalny, domyślnie 50) - maksymalna liczba wyników
- `signal` (opcjonalny) - filtruj po sygnale ("BUY", "SELL", "HOLD")

**Przykład:**
```bash
curl -H "X-API-Key: $API_KEY" \
  "http://localhost:8000/ai/analysis-results?symbol=EUR/USD&limit=10"
```

**Response:**
```json
{
  "results": [
    {
      "id": 123,
      "symbol": "EUR/USD",
      "timeframe": "1h",
      "timestamp": "2026-01-16T20:00:00",
      "final_signal": "BUY",
      "agreement_score": 75,
      "ai_recommendation": "BUY",
      "ai_confidence": 80,
      "technical_signal": "BUY",
      "technical_confidence": 70,
      "macro_signal": "HOLD",
      "news_sentiment": "positive",
      "tokens_used": 2500,
      "estimated_cost": 0.0225
    }
  ],
  "count": 1
}
```

#### GET /ai/analysis-results/{analysis_id}

Pobiera szczegóły pojedynczej analizy.

**Przykład:**
```bash
curl -H "X-API-Key: $API_KEY" \
  "http://localhost:8000/ai/analysis-results/123"
```

**Response:**
```json
{
  "id": 123,
  "symbol": "EUR/USD",
  "timeframe": "1h",
  "timestamp": "2026-01-16T20:00:00",
  "final_signal": "BUY",
  "agreement_score": 75,
  "voting_details": {
    "ai": {
      "vote": "BUY",
      "confidence": 80,
      "weight": 40
    },
    "technical": {
      "vote": "BUY",
      "confidence": 70,
      "weight": 30
    },
    "macro": {
      "vote": "HOLD",
      "confidence": 50,
      "weight": 20
    },
    "news": {
      "vote": "BUY",
      "confidence": 65,
      "weight": 10
    }
  },
  "decision_reason": "Sygnał BUY z 75% zgodnością:\n✓ Za: AI (80%), Technical (70%), News (65%)\n⚠ Neutralne: Macro (50%)",
  "ai_reasoning": "Silne wskaźniki techniczne wspierane przez pozytywny sentiment...",
  "technical_details": "{\"rsi\": 45.2, \"macd\": {...}}",
  "tokens_used": 2500,
  "estimated_cost": 0.0225
}
```

### 2. Statystyki tokenów

#### GET /ai/token-statistics

Zwraca statystyki użycia tokenów OpenAI.

**Query parameters:**
- `days` (opcjonalny, domyślnie 30) - liczba dni wstecz

**Przykład:**
```bash
curl -H "X-API-Key: $API_KEY" \
  "http://localhost:8000/ai/token-statistics?days=7"
```

**Response:**
```json
{
  "period_days": 7,
  "total_analyses": 2016,
  "total_tokens": 5040000,
  "total_cost": 45.36,
  "daily_average": {
    "analyses": 288,
    "tokens": 720000,
    "cost": 6.48
  },
  "per_analysis_average": {
    "tokens": 2500,
    "cost": 0.0225
  },
  "by_symbol": {
    "EUR/USD": {
      "analyses": 288,
      "tokens": 720000,
      "cost": 6.48
    }
  }
}
```

### 3. Konfiguracja

#### GET /ai/analysis-config

Pobiera aktualną konfigurację automatycznych analiz.

**Przykład:**
```bash
curl -H "X-API-Key: $API_KEY" \
  "http://localhost:8000/ai/analysis-config"
```

**Response:**
```json
{
  "enabled": true,
  "interval_minutes": 30,
  "notification_threshold": 60,
  "enabled_symbols": [
    "EUR/USD",
    "GBP/USD",
    "USD/JPY",
    "AAPL/USD",
    "XAU/USD"
  ],
  "weights": {
    "ai": 40,
    "technical": 30,
    "macro": 20,
    "news": 10
  }
}
```

#### PUT /ai/analysis-config

Aktualizuje konfigurację automatycznych analiz.

**Body:**
```json
{
  "enabled": true,
  "interval_minutes": 15,
  "notification_threshold": 70,
  "enabled_symbols": ["EUR/USD", "GBP/USD"],
  "weights": {
    "ai": 50,
    "technical": 30,
    "macro": 15,
    "news": 5
  }
}
```

**Przykład:**
```bash
curl -X PUT http://localhost:8000/ai/analysis-config \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "interval_minutes": 15,
    "notification_threshold": 70,
    "enabled_symbols": ["EUR/USD", "GBP/USD"]
  }'
```

### 4. Manualne uruchomienie

#### POST /ai/trigger-analysis

Ręcznie uruchamia analizę dla wybranych symboli.

**Body:**
```json
{
  "symbols": ["EUR/USD", "GBP/USD"],
  "timeframe": "1h"
}
```

**Przykład:**
```bash
curl -X POST http://localhost:8000/ai/trigger-analysis \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["EUR/USD", "GBP/USD"],
    "timeframe": "1h"
  }'
```

**Response:**
```json
{
  "status": "completed",
  "analyzed": 2,
  "results": [
    {
      "symbol": "EUR/USD",
      "final_signal": "BUY",
      "agreement_score": 75,
      "analysis_id": 123
    },
    {
      "symbol": "GBP/USD",
      "final_signal": "HOLD",
      "agreement_score": 45,
      "analysis_id": 124
    }
  ],
  "total_tokens": 5000,
  "total_cost": 0.045
}
```

## Baza danych

System używa SQLite z dwoma głównymi tabelami zdefiniowanymi w `backend/app/utils/database.py`.

### Tabela: ai_analysis_results

Przechowuje wszystkie wyniki analiz (nie tylko sygnały BUY/SELL, ale też HOLD).

**Struktura:**
```sql
CREATE TABLE ai_analysis_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- Wyniki AI
    ai_recommendation TEXT,
    ai_confidence INTEGER,
    ai_reasoning TEXT,
    
    -- Wyniki Technical
    technical_signal TEXT,
    technical_confidence INTEGER,
    technical_details TEXT,  -- JSON
    
    -- Wyniki Macro
    macro_signal TEXT,
    macro_impact TEXT,
    
    -- Wyniki News
    news_sentiment TEXT,
    news_score INTEGER,
    
    -- Agregacja
    final_signal TEXT NOT NULL,
    agreement_score INTEGER NOT NULL,
    voting_details TEXT,  -- JSON
    decision_reason TEXT,
    
    -- Statystyki OpenAI
    tokens_used INTEGER DEFAULT 0,
    estimated_cost REAL DEFAULT 0.0
);

CREATE INDEX idx_ai_results_symbol ON ai_analysis_results(symbol);
CREATE INDEX idx_ai_results_timestamp ON ai_analysis_results(timestamp);
CREATE INDEX idx_ai_results_signal ON ai_analysis_results(final_signal);
```

**Przykładowe zapytania:**

```python
# Pobierz ostatnie analizy dla symbolu
db.execute(
    "SELECT * FROM ai_analysis_results WHERE symbol = ? ORDER BY timestamp DESC LIMIT ?",
    (symbol, limit)
)

# Statystyki tokenów za ostatnie 7 dni
db.execute("""
    SELECT 
        COUNT(*) as analyses,
        SUM(tokens_used) as total_tokens,
        SUM(estimated_cost) as total_cost
    FROM ai_analysis_results
    WHERE timestamp >= datetime('now', '-7 days')
""")

# Analizy z wysokim agreement score
db.execute("""
    SELECT * FROM ai_analysis_results
    WHERE agreement_score >= 70
    AND final_signal IN ('BUY', 'SELL')
    ORDER BY timestamp DESC
""")
```

### Tabela: analysis_config

Przechowuje konfigurację automatycznych analiz.

**Struktura:**
```sql
CREATE TABLE analysis_config (
    id INTEGER PRIMARY KEY CHECK (id = 1),  -- Tylko 1 rekord
    enabled BOOLEAN DEFAULT 1,
    interval_minutes INTEGER DEFAULT 30,
    notification_threshold INTEGER DEFAULT 60,
    enabled_symbols TEXT,  -- JSON array
    weights TEXT,  -- JSON object
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**Metody dostępu:**

```python
# Pobierz konfigurację
config = db.get_analysis_config()

# Aktualizuj konfigurację
db.update_analysis_config({
    "interval_minutes": 15,
    "notification_threshold": 70,
    "enabled_symbols": ["EUR/USD", "GBP/USD"]
})
```

## Konfiguracja środowiska

Wszystkie zmienne środowiskowe są zdefiniowane w pliku `.env` i walidowane przez `backend/app/config.py`.

### Zmienne wymagane

```bash
# OpenAI API (wymagane dla AI analiz)
OPENAI_API_KEY=sk-...

# Telegram (wymagane dla powiadomień)
TELEGRAM_BOT_TOKEN=1234567890:ABC...
TELEGRAM_CHAT_ID=123456789

# API Security (wymagane)
API_KEY=<wygeneruj: openssl rand -hex 32>
```

### Zmienne opcjonalne dla AI

```bash
# Model OpenAI (domyślnie: gpt-4o)
OPENAI_MODEL=gpt-4o-mini  # Zalecane - 10x taniej!

# Interwał między cyklami analiz w minutach (domyślnie: 30)
# Zakres: 5-1440 (5 minut - 24 godziny)
ANALYSIS_INTERVAL=15

# Włącz/wyłącz automatyczne analizy (domyślnie: true)
ANALYSIS_ENABLED=true

# Minimalny agreement_score do wysłania powiadomienia (domyślnie: 60)
# Zakres: 0-100
NOTIFICATION_THRESHOLD=60
```

### Przykładowa konfiguracja

**Dla development (niskie koszty):**
```bash
OPENAI_MODEL=gpt-4o-mini
ANALYSIS_INTERVAL=60
NOTIFICATION_THRESHOLD=70
# Tylko 2 symbole w analysis_config
```

**Dla production (pełna analiza):**
```bash
OPENAI_MODEL=gpt-4o
ANALYSIS_INTERVAL=15
NOTIFICATION_THRESHOLD=60
# Wszystkie 10 symboli w analysis_config
```

## Frontend Dashboard

Dashboard jest zaimplementowany w `frontend/dashboard.html` i zawiera dedykowane sekcje dla AI Signal Integration.

### Sekcje AI w Dashboard

#### 1. Panel wyników analiz

**Lokalizacja:** Zakładka "AI Analysis Results"

**Funkcje:**
- Lista wszystkich wyników analiz
- Filtrowanie po symbolu
- Filtrowanie po sygnale (BUY/SELL/HOLD)
- Sortowanie po czasie (najnowsze pierwsze)
- Paginacja (50 wyników na stronę)

**Wyświetlane informacje:**
- Symbol i timeframe
- Final signal z kolorowym badge (🟢 BUY, 🔴 SELL, ⚪ HOLD)
- Agreement score z wskaźnikiem (high/medium/low)
- Szczegóły głosowania z 4 źródeł
- Decision reason (uzasadnienie)
- Tokeny i koszt
- Timestamp

#### 2. Statystyki tokenów

**Lokalizacja:** Panel "Token Statistics"

**Wyświetla:**
- Łączna liczba analiz
- Łączne tokeny i koszt
- Średnia dzienna (analizy, tokeny, koszt)
- Średnia na analizę (tokeny, koszt)
- Rozbicie po symbolach

**Aktualizacja:** Co 30 sekund (auto-refresh)

#### 3. Konfiguracja analiz

**Lokalizacja:** Panel "Analysis Configuration"

**Ustawienia:**
- Włącz/wyłącz automatyczne analizy
- Interwał między cyklami (5-1440 minut)
- Próg powiadomień (0-100%)
- Lista symboli do analizy (multi-select)
- Wagi źródeł (AI, Technical, Macro, News)

**Walidacja:**
- Suma wag musi wynosić 100%
- Interwał w dozwolonym zakresie
- Minimum 1 symbol wybrany

#### 4. Przycisk manualnego uruchomienia

**Funkcja:** Ręczne uruchomienie analizy dla wybranych symboli

**Proces:**
1. Wybierz symbole z listy
2. Kliknij "Trigger Analysis"
3. Wyświetl progress bar
4. Pokaż wyniki po zakończeniu

### Wizualizacje

**Badge dla sygnałów:**
```html
<!-- BUY - zielony -->
<span class="badge bg-success">🟢 BUY</span>

<!-- SELL - czerwony -->
<span class="badge bg-danger">🔴 SELL</span>

<!-- HOLD - szary -->
<span class="badge bg-secondary">⚪ HOLD</span>
```

**Agreement score indicator:**
```html
<!-- High (>= 70%) - zielony -->
<div class="progress">
  <div class="progress-bar bg-success" style="width: 75%">75%</div>
</div>

<!-- Medium (50-69%) - żółty -->
<div class="progress">
  <div class="progress-bar bg-warning" style="width: 60%">60%</div>
</div>

<!-- Low (< 50%) - czerwony -->
<div class="progress">
  <div class="progress-bar bg-danger" style="width: 40%">40%</div>
</div>
```

**Szczegóły głosowania:**
```html
<table class="table table-sm">
  <tr>
    <td>AI (40%)</td>
    <td><span class="badge bg-success">BUY</span></td>
    <td>80%</td>
  </tr>
  <tr>
    <td>Technical (30%)</td>
    <td><span class="badge bg-success">BUY</span></td>
    <td>70%</td>
  </tr>
  <tr>
    <td>Macro (20%)</td>
    <td><span class="badge bg-secondary">HOLD</span></td>
    <td>50%</td>
  </tr>
  <tr>
    <td>News (10%)</td>
    <td><span class="badge bg-success">BUY</span></td>
    <td>65%</td>
  </tr>
</table>
```

## Koszty OpenAI

### Ceny modeli (styczeń 2026)

| Model | Input (za 1K tokenów) | Output (za 1K tokenów) |
|-------|----------------------|------------------------|
| gpt-4o | $0.005 | $0.015 |
| gpt-4o-mini | $0.00015 | $0.0006 |
| gpt-4-turbo | $0.010 | $0.030 |
| gpt-3.5-turbo | $0.0005 | $0.0015 |

### Szacunki kosztów

**Średnie zużycie tokenów na analizę:**
- Prompt (input): ~1500 tokenów
- Response (output): ~1000 tokenów
- **Razem: ~2500 tokenów**

**Koszt pojedynczej analizy:**

| Model | Koszt/analiza |
|-------|---------------|
| gpt-4o | $0.0225 |
| gpt-4o-mini | $0.00225 |

### Miesięczne szacunki

**Dla różnych konfiguracji:**

#### 1 symbol, interwał 30 minut
- Analizy/dzień: 48
- Analizy/miesiąc: 1,440
- **gpt-4o:** ~$32/miesiąc
- **gpt-4o-mini:** ~$3.2/miesiąc

#### 10 symboli, interwał 30 minut
- Analizy/dzień: 480
- Analizy/miesiąc: 14,400
- **gpt-4o:** ~$324/miesiąc
- **gpt-4o-mini:** ~$32/miesiąc

#### 10 symboli, interwał 15 minut
- Analizy/dzień: 960
- Analizy/miesiąc: 28,800
- **gpt-4o:** ~$648/miesiąc
- **gpt-4o-mini:** ~$65/miesiąc

#### 25 symboli (wszystkie), interwał 15 minut
- Analizy/dzień: 2,400
- Analizy/miesiąc: 72,000
- **gpt-4o:** ~$1,620/miesiąc
- **gpt-4o-mini:** ~$162/miesiąc

### Rekomendacje optymalizacji

1. **Użyj GPT-4o-mini** - 10x taniej, nadal bardzo dobra jakość
2. **Wydłuż interwał** - 30-60 minut zamiast 15
3. **Ogranicz symbole** - zacznij od 5-10 najważniejszych
4. **Monitoruj koszty** - sprawdzaj `/ai/token-statistics` regularnie
5. **Dostosuj próg** - wyższy threshold = mniej powiadomień

## Przykłady użycia

### 1. Podstawowa konfiguracja

```bash
# 1. Dodaj do .env
cat >> .env << EOF
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
ANALYSIS_INTERVAL=30
NOTIFICATION_THRESHOLD=60
EOF

# 2. Uruchom
docker-compose up -d

# 3. Sprawdź logi
docker-compose logs -f scheduler
```

### 2. Manualne uruchomienie analizy

```bash
# Ustaw API Key
export API_KEY="twoj_api_key"

# Uruchom analizę dla 2 symboli
curl -X POST http://localhost:8000/ai/trigger-analysis \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["EUR/USD", "GBP/USD"],
    "timeframe": "1h"
  }'
```

### 3. Pobieranie wyników

```bash
# Wszystkie wyniki dla EUR/USD
curl -H "X-API-Key: $API_KEY" \
  "http://localhost:8000/ai/analysis-results?symbol=EUR/USD&limit=10"

# Tylko sygnały BUY
curl -H "X-API-Key: $API_KEY" \
  "http://localhost:8000/ai/analysis-results?signal=BUY&limit=20"

# Szczegóły konkretnej analizy
curl -H "X-API-Key: $API_KEY" \
  "http://localhost:8000/ai/analysis-results/123"
```

### 4. Statystyki tokenów

```bash
# Statystyki za ostatnie 7 dni
curl -H "X-API-Key: $API_KEY" \
  "http://localhost:8000/ai/token-statistics?days=7"

# Statystyki za ostatni miesiąc
curl -H "X-API-Key: $API_KEY" \
  "http://localhost:8000/ai/token-statistics?days=30"
```

### 5. Aktualizacja konfiguracji

```bash
# Zmień interwał na 15 minut
curl -X PUT http://localhost:8000/ai/analysis-config \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "interval_minutes": 15
  }'

# Zmień próg powiadomień na 70%
curl -X PUT http://localhost:8000/ai/analysis-config \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "notification_threshold": 70
  }'

# Ogranicz do 2 symboli
curl -X PUT http://localhost:8000/ai/analysis-config \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "enabled_symbols": ["EUR/USD", "GBP/USD"]
  }'
```

### 6. Zmiana wag źródeł

```bash
# Zwiększ wagę AI, zmniejsz News
curl -X PUT http://localhost:8000/ai/analysis-config \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "weights": {
      "ai": 50,
      "technical": 30,
      "macro": 15,
      "news": 5
    }
  }'
```

## Testy

System ma kompleksowy zestaw testów w katalogu `backend/tests/`.

### Testy jednostkowe

**1. test_signal_aggregator.py**
- Testuje SignalAggregatorService
- Głosowanie większościowe
- Normalizacja sygnałów
- Obliczanie agreement score

**2. test_auto_scheduler.py**
- Testuje AutoAnalysisScheduler
- Cykle analiz
- Rate limiting
- Statystyki

**3. test_ai_strategy_comprehensive.py**
- Testuje AIStrategy.comprehensive_analysis()
- Zbieranie danych z 4 źródeł
- Liczenie tokenów
- Szacowanie kosztów

### Testy integracyjne

**1. test_integration.py**
- Pełny flow: comprehensive_analysis → aggregate_signals
- Walidacja formatu danych
- Zgodność między komponentami

**2. test_e2e_full_pipeline.py**
- End-to-end z bazą danych
- Zapis wyników
- Powiadomienia Telegram
- Statystyki tokenów

**3. test_etap4_integration.py**
- Test AutoAnalysisScheduler z 2 symbolami
- Rzeczywiste API OpenAI (opcjonalnie)
- Monitoring kosztów

### Uruchamianie testów

```bash
# Wszystkie testy
cd backend
pytest

# Konkretny plik
pytest tests/test_signal_aggregator.py

# Z coverage
pytest --cov=app --cov-report=html

# Tylko testy jednostkowe (szybkie)
pytest tests/test_signal_aggregator.py tests/test_auto_scheduler.py

# Tylko testy integracyjne (wolne, używają API)
pytest tests/test_e2e_full_pipeline.py -v
```

### Przykładowe testy

**Test głosowania większościowego:**
```python
async def test_majority_buy():
    aggregator = SignalAggregatorService(database=mock_db)
    
    result = await aggregator.aggregate_signals(
        symbol="EUR/USD",
        timeframe="1h",
        ai_result={"recommendation": "BUY", "confidence": 80},
        technical_result={"signal": "BUY", "confidence": 70},
        macro_result={"signal": "HOLD", "confidence": 50},
        news_result={"sentiment": "positive", "score": 65}
    )
    
    assert result["final_signal"] == "BUY"
    assert result["agreement_score"] >= 70
    assert result["should_notify"] == True
```

## Best Practices

### 1. Monitorowanie kosztów

```bash
# Sprawdzaj statystyki codziennie
curl -H "X-API-Key: $API_KEY" \
  "http://localhost:8000/ai/token-statistics?days=1"

# Ustaw alerty w dashboardzie
# Jeśli dzienny koszt > $10 → powiadomienie
```

### 2. Optymalizacja interwałów

**Zalecenia:**
- **Development/testing:** 60 minut
- **Production (forex):** 15-30 minut
- **Production (akcje):** 30-60 minut (rynek zamknięty w nocy)
- **Long-term trading:** 120-240 minut

### 3. Wybór symboli

**Priorytetyzacja:**
1. Najpłynniejsze pary (EUR/USD, GBP/USD)
2. Główne indeksy (SPX, DJI)
3. Blue chip stocks (AAPL, MSFT)
4. Metale szlachetne (XAU/USD)

**Unikaj:**
- Egzotyczne pary walutowe (mało danych)
- Małe spółki (niska płynność)
- Kryptowaluty (wysoka zmienność, drogie analizy)

### 4. Dostrajanie wag

**Domyślne (uniwersalne):**
```python
{"ai": 40, "technical": 30, "macro": 20, "news": 10}
```

**Dla forex (makro ważniejsze):**
```python
{"ai": 35, "technical": 25, "macro": 30, "news": 10}
```

**Dla akcji (technical ważniejsze):**
```python
{"ai": 40, "technical": 35, "macro": 15, "news": 10}
```

**Dla long-term (AI dominuje):**
```python
{"ai": 50, "technical": 20, "macro": 20, "news": 10}
```

### 5. Dostrajanie progów

**Notification threshold:**
- **Konserwatywny:** 70-80% (mniej sygnałów, wyższa jakość)
- **Zbalansowany:** 60-70% (domyślnie)
- **Agresywny:** 50-60% (więcej sygnałów, niższa jakość)

### 6. Backup i monitoring

```bash
# Backup bazy danych codziennie
0 2 * * * cp /app/data/trading_bot.db /app/data/backups/trading_bot_$(date +\%Y\%m\%d).db

# Monitoruj logi
tail -f /app/data/logs/bot.log | grep -E "ERROR|WARNING"

# Sprawdzaj health
watch -n 60 'curl -s http://localhost:8000/health | jq'
```

## Troubleshooting

### Problem: Wysokie koszty OpenAI

**Objawy:**
- Miesięczny koszt > $100
- Statystyki pokazują tysiące analiz

**Rozwiązania:**
1. Zmień model na `gpt-4o-mini` (10x taniej)
2. Wydłuż interwał (30 → 60 minut)
3. Ogranicz liczbę symboli (25 → 10)
4. Podnieś próg powiadomień (60% → 70%)

```bash
# Szybka optymalizacja
curl -X PUT http://localhost:8000/ai/analysis-config \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "interval_minutes": 60,
    "enabled_symbols": ["EUR/USD", "GBP/USD", "AAPL/USD"]
  }'

# Zmień model w .env
OPENAI_MODEL=gpt-4o-mini
docker-compose restart
```

### Problem: Brak sygnałów

**Objawy:**
- Dashboard pusty
- Brak powiadomień Telegram
- Agreement score zawsze < threshold

**Rozwiązania:**
1. Obniż próg powiadomień (70% → 50%)
2. Sprawdź czy analizy działają (`/ai/analysis-results`)
3. Sprawdź logi schedulera

```bash
# Sprawdź ostatnie analizy
curl -H "X-API-Key: $API_KEY" \
  "http://localhost:8000/ai/analysis-results?limit=10"

# Obniż próg
curl -X PUT http://localhost:8000/ai/analysis-config \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"notification_threshold": 50}'

# Sprawdź logi
docker-compose logs scheduler | grep "agreement_score"
```

### Problem: Rate limiting OpenAI

**Objawy:**
- Błędy "Rate limit exceeded" w logach
- Niektóre analizy się nie wykonują

**Rozwiązania:**
1. Zwiększ pauzę między symbolami (2s → 5s)
2. Zmniejsz liczbę symboli
3. Sprawdź limity na OpenAI dashboard

```bash
# Zwiększ pauzę w kodzie
# W AutoAnalysisScheduler.__init__():
pause_between_symbols=5  # Zamiast 2

# Lub ogranicz symbole
curl -X PUT http://localhost:8000/ai/analysis-config \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "enabled_symbols": ["EUR/USD", "GBP/USD", "USD/JPY"]
  }'
```

### Problem: Błędy analizy

**Objawy:**
- Błędy w logach: "Error in comprehensive analysis"
- Niektóre symbole zawsze HOLD z confidence=0

**Rozwiązania:**
1. Sprawdź klucz OpenAI (`OPENAI_API_KEY`)
2. Sprawdź dostępność Yahoo Finance
3. Sprawdź format symboli

```bash
# Test klucza OpenAI
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# Test Yahoo Finance
python -c "import yfinance as yf; print(yf.Ticker('EURUSD=X').info)"

# Sprawdź logi szczegółowo
docker-compose logs scheduler | grep -A 10 "Error in comprehensive"
```

### Problem: Database locked

**Objawy:**
- Błąd "database is locked"
- Scheduler nie może zapisać wyników

**Rozwiązania:**
1. Zatrzymaj scheduler przed ręcznymi operacjami
2. Zwiększ timeout SQLite
3. Rozważ PostgreSQL dla produkcji

```bash
# Zatrzymaj scheduler
docker-compose stop scheduler

# Wykonaj operację
sqlite3 data/trading_bot.db "SELECT COUNT(*) FROM ai_analysis_results;"

# Uruchom ponownie
docker-compose start scheduler
```

### Problem: Brak danych makro/news

**Objawy:**
- Macro analysis zawsze "Brak danych"
- News analysis zawsze 0 wiadomości

**Rozwiązania:**
1. Sprawdź dostępność zewnętrznych API
2. Sprawdź logi data_collection_service
3. Dodaj fallback values

```bash
# Test macro service
docker-compose exec backend python -c "
from app.services.data_collection_service import MacroDataService
import asyncio
service = MacroDataService()
result = asyncio.run(service.get_all_macro_data())
print(result)
"

# Test news service
docker-compose exec backend python -c "
from app.services.data_collection_service import NewsService
import asyncio
service = NewsService()
result = asyncio.run(service.get_financial_news('EUR', hours_back=24))
print(len(result), 'news items')
"
```

---

## Podsumowanie

System **AI Signal Integration** to potężne narzędzie łączące 4 źródła analiz w jeden sygnał tradingowy. Kluczowe zalety:

✅ **Większa pewność** - głosowanie większościowe eliminuje fałszywe sygnały  
✅ **Kompleksowa analiza** - AI + Technical + Macro + News  
✅ **Konfigurowalne** - wagi, progi, symbole, interwały  
✅ **Przejrzyste** - szczegółowe uzasadnienia decyzji  
✅ **Monitorowane** - śledzenie kosztów i tokenów  

**Najważniejsze:**
1. Zacznij od `gpt-4o-mini` i 5-10 symboli
2. Monitoruj koszty codziennie
3. Dostrajaj wagi i progi na podstawie wyników
4. Używaj dashboard do analizy historycznych sygnałów

**Dokumentacja powiązana:**
- [README.md](../README.md) - Główna dokumentacja projektu
- [CLAUDE.md](../CLAUDE.md) - Przewodnik dla Claude AI
- [docs/SECURITY.md](SECURITY.md) - Bezpieczeństwo systemu

**Wsparcie:**
- GitHub Issues: [link do repo]
- Email: support@yourdomain.com

---

*Ostatnia aktualizacja: 2026-01-16*
