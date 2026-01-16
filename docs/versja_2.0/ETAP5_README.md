# Etap 5: Nowe Endpointy API - Dokumentacja

## Przegląd

Etap 5 rozszerza API backendu o nowe endpointy umożliwiające:
- Pobieranie wyników analiz AI z bazy danych
- Monitorowanie statystyk tokenów i kosztów OpenAI
- Zarządzanie konfiguracją automatycznych analiz
- Ręczne uruchamianie analiz
- Ulepszone endpointy AI z comprehensive_analysis

## Nowe Endpointy

### 1. Wyniki Analiz AI

#### GET /ai/analysis-results

Pobiera listę wyników analiz AI z opcjonalnym filtrowaniem.

**Parametry zapytania:**
- `symbol` (opcjonalny) - Filtruj po symbolu (np. "EUR/USD")
- `limit` (opcjonalny, domyślnie 50) - Maksymalna liczba wyników (1-200)
- `signal_type` (opcjonalny) - Filtruj po typie sygnału (BUY/SELL/HOLD/NO_SIGNAL)
- `min_agreement` (opcjonalny) - Minimalny agreement_score (0-100)

**Przykład:**
```bash
curl -X GET "http://localhost:8000/ai/analysis-results?symbol=EUR/USD&limit=10" \
  -H "X-API-Key: your-api-key"
```

**Odpowiedź:**
```json
{
  "results": [
    {
      "id": 1,
      "symbol": "EUR/USD",
      "timeframe": "1h",
      "timestamp": "2026-01-16T20:00:00",
      "ai_recommendation": "BUY",
      "ai_confidence": 85,
      "technical_signal": "BUY",
      "technical_confidence": 75,
      "macro_signal": "HOLD",
      "news_sentiment": "positive",
      "news_score": 70,
      "final_signal": "BUY",
      "agreement_score": 86,
      "tokens_used": 2500,
      "estimated_cost": 0.025,
      "decision_reason": "Sygnał BUY: AI (85%), Technical (75%), News (70%)..."
    }
  ],
  "count": 1,
  "filters_applied": {
    "symbol": "EUR/USD",
    "limit": 10
  }
}
```

**Rate limit:** 60 zapytań/godzinę

---

#### GET /ai/analysis-results/{analysis_id}

Pobiera szczegółowe informacje o pojedynczej analizie.

**Parametry ścieżki:**
- `analysis_id` - ID analizy

**Przykład:**
```bash
curl -X GET "http://localhost:8000/ai/analysis-results/1" \
  -H "X-API-Key: your-api-key"
```

**Odpowiedź:**
```json
{
  "id": 1,
  "symbol": "EUR/USD",
  "timeframe": "1h",
  "timestamp": "2026-01-16T20:00:00",
  "ai_recommendation": "BUY",
  "ai_confidence": 85,
  "ai_reasoning": "Analiza techniczna wskazuje na silny trend wzrostowy...",
  "technical_signal": "BUY",
  "technical_confidence": 75,
  "technical_details": {
    "rsi": 35,
    "macd": "bullish",
    "ma_cross": "golden_cross"
  },
  "macro_signal": "HOLD",
  "macro_impact": "neutral",
  "news_sentiment": "positive",
  "news_score": 70,
  "final_signal": "BUY",
  "agreement_score": 86,
  "voting_details": {
    "ai": {"vote": "BUY", "confidence": 85},
    "technical": {"vote": "BUY", "confidence": 75},
    "macro": {"vote": "HOLD", "confidence": 50},
    "news": {"vote": "BUY", "confidence": 70}
  },
  "tokens_used": 2500,
  "estimated_cost": 0.025,
  "decision_reason": "Sygnał BUY: AI (85%), Technical (75%), News (70%)...",
  "created_at": "2026-01-16T20:00:00"
}
```

**Błędy:**
- `404` - Analiza nie została znaleziona

**Rate limit:** 60 zapytań/godzinę

---

### 2. Statystyki Tokenów OpenAI

#### GET /ai/token-statistics

Pobiera statystyki użycia tokenów OpenAI i szacowane koszty.

**Parametry zapytania:**
- `start_date` (opcjonalny) - Data początkowa (format: YYYY-MM-DD)
- `end_date` (opcjonalny) - Data końcowa (format: YYYY-MM-DD)

**Przykład:**
```bash
curl -X GET "http://localhost:8000/ai/token-statistics?start_date=2026-01-01&end_date=2026-01-16" \
  -H "X-API-Key: your-api-key"
```

**Odpowiedź:**
```json
{
  "total_tokens": 125000,
  "total_cost": 1.25,
  "analyses_count": 50,
  "avg_tokens_per_analysis": 2500,
  "today_tokens": 15000,
  "today_cost": 0.15,
  "today_analyses": 6,
  "period": {
    "start_date": "2026-01-01",
    "end_date": "2026-01-16"
  }
}
```

**Błędy:**
- `400` - Nieprawidłowy format daty

**Rate limit:** 60 zapytań/godzinę

---

### 3. Konfiguracja Analiz

#### GET /ai/analysis-config

Pobiera aktualną konfigurację automatycznych analiz.

**Przykład:**
```bash
curl -X GET "http://localhost:8000/ai/analysis-config" \
  -H "X-API-Key: your-api-key"
```

**Odpowiedź:**
```json
{
  "id": 1,
  "analysis_interval": 30,
  "enabled_symbols": ["EUR/USD", "GBP/USD", "USD/JPY"],
  "notification_threshold": 60,
  "is_active": true,
  "updated_at": "2026-01-16T19:00:00"
}
```

**Rate limit:** 60 zapytań/godzinę

---

#### PUT /ai/analysis-config

Aktualizuje konfigurację automatycznych analiz.

**Body (wszystkie pola opcjonalne):**
```json
{
  "analysis_interval": 60,
  "enabled_symbols": ["EUR/USD", "GBP/USD"],
  "notification_threshold": 70,
  "is_active": false
}
```

**Walidacja:**
- `analysis_interval`: 5-1440 minut
- `enabled_symbols`: lista stringów, max 50 symboli, każdy musi zawierać "/"
- `notification_threshold`: 0-100
- `is_active`: boolean

**Przykład:**
```bash
curl -X PUT "http://localhost:8000/ai/analysis-config" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "analysis_interval": 60,
    "notification_threshold": 70
  }'
```

**Odpowiedź:**
```json
{
  "message": "Konfiguracja zaktualizowana pomyślnie",
  "updated_config": {
    "id": 1,
    "analysis_interval": 60,
    "enabled_symbols": ["EUR/USD", "GBP/USD"],
    "notification_threshold": 70,
    "is_active": true,
    "updated_at": "2026-01-16T20:30:00"
  }
}
```

**Błędy:**
- `400` - Brak danych do aktualizacji
- `422` - Nieprawidłowe wartości pól

**Rate limit:** 60 zapytań/godzinę

---

### 4. Ręczne Uruchomienie Analiz

#### POST /ai/trigger-analysis

Ręcznie uruchamia cykl analiz AI dla wybranych symboli.

**UWAGA:** To kosztowna operacja - każda analiza wykorzystuje tokeny OpenAI.

**Body (opcjonalny):**
```json
{
  "symbols": ["EUR/USD", "GBP/USD"],
  "timeframe": "1h"
}
```

Jeśli nie podasz `symbols`, użyta zostanie domyślna lista z konfiguracji.

**Walidacja:**
- `symbols`: lista stringów, max 50 symboli, każdy musi zawierać "/"
- `timeframe`: 1m, 5m, 15m, 30m, 1h, 4h, 1d

**Przykład:**
```bash
curl -X POST "http://localhost:8000/ai/trigger-analysis" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["EUR/USD", "GBP/USD"],
    "timeframe": "1h"
  }'
```

**Odpowiedź:**
```json
{
  "message": "Analiza zakończona dla 2 symboli",
  "results": [
    {
      "analysis_id": 123,
      "symbol": "EUR/USD",
      "final_signal": "BUY",
      "agreement_score": 86
    },
    {
      "analysis_id": 124,
      "symbol": "GBP/USD",
      "final_signal": "SELL",
      "agreement_score": 72
    }
  ],
  "statistics": {
    "total_symbols": 2,
    "successful": 2,
    "failed": 0,
    "total_tokens": 5000,
    "total_cost": 0.05,
    "duration_seconds": 15.3
  }
}
```

**Błędy:**
- `422` - Nieprawidłowe parametry
- `500` - Timeout (300s) lub błąd analizy

**Rate limit:** 10 zapytań/godzinę (kosztowna operacja)

**Timeout:** 300 sekund (5 minut)

---

## Zrefaktoryzowane Endpointy

### POST /ai/analyze

Zrefaktoryzowany endpoint używa teraz `comprehensive_analysis()` i `SignalAggregatorService`.

**Zmiany:**
- Używa comprehensive_analysis zamiast analyze_and_generate_signal
- Agreguje sygnały z głosowaniem większościowym
- Zapisuje wynik do bazy danych
- Zwraca rozszerzony format odpowiedzi
- **Rate limit zmieniony z 10/h na 60/h**

**Nowy format odpowiedzi:**
```json
{
  "symbol": "EUR/USD",
  "timeframe": "1h",
  "timestamp": "2026-01-16T20:00:00",
  "analysis": {
    "ai": {
      "recommendation": "BUY",
      "confidence": 85,
      "reasoning": "..."
    },
    "technical": {
      "signal": "BUY",
      "confidence": 75,
      "indicators": {...}
    },
    "macro": {
      "signal": "HOLD",
      "impact": "neutral"
    },
    "news": {
      "sentiment": "positive",
      "score": 70
    }
  },
  "aggregated": {
    "final_signal": "BUY",
    "agreement_score": 86,
    "decision_reason": "...",
    "should_notify": true
  },
  "tokens_used": 2500,
  "estimated_cost": 0.025,
  "analysis_id": 123
}
```

---

### GET /ai/market-overview/{symbol}

Zrefaktoryzowany endpoint używa `comprehensive_analysis()` jako podstawy.

**Zmiany:**
- Używa comprehensive_analysis
- Dodaje link do ostatniej zapisanej analizy
- **Rate limit zmieniony z 20/h na 60/h**

**Nowy format odpowiedzi:**
```json
{
  "symbol": "EUR/USD",
  "timestamp": "2026-01-16T20:00:00",
  "comprehensive_analysis": {
    "ai": {...},
    "technical": {...},
    "macro": {...},
    "news": {...}
  },
  "last_saved_analysis": {
    "id": 123,
    "timestamp": "2026-01-16T19:30:00",
    "final_signal": "BUY",
    "agreement_score": 86
  }
}
```

---

### Pozostałe endpointy AI

**POST /ai/sentiment** i **POST /ai/event-impact**:
- Bez zmian funkcjonalnych
- **Rate limit zaktualizowany na 60/h** (poprzednio 30/h)

---

## Kody Błędów

### 400 Bad Request
Nieprawidłowe parametry zapytania (np. zły format daty).

```json
{
  "detail": "Nieprawidłowy format daty. Użyj YYYY-MM-DD"
}
```

### 404 Not Found
Zasób nie został znaleziony.

```json
{
  "detail": "Analiza o ID 123 nie została znaleziona"
}
```

### 422 Validation Error
Błąd walidacji danych wejściowych.

```json
{
  "detail": [
    {
      "loc": ["body", "analysis_interval"],
      "msg": "ensure this value is greater than or equal to 5",
      "type": "value_error.number.not_ge"
    }
  ]
}
```

### 429 Too Many Requests
Przekroczono limit rate limiting.

```json
{
  "detail": "Rate limit exceeded"
}
```

### 500 Internal Server Error
Błąd serwera.

```json
{
  "detail": "Błąd podczas uruchamiania analizy: timeout"
}
```

---

## Rate Limiting

### Nowe limity:

| Endpoint | Limit | Uwagi |
|----------|-------|-------|
| GET /ai/analysis-results | 60/h | - |
| GET /ai/analysis-results/{id} | 60/h | - |
| GET /ai/token-statistics | 60/h | - |
| GET /ai/analysis-config | 60/h | - |
| PUT /ai/analysis-config | 60/h | - |
| POST /ai/trigger-analysis | 10/h | Kosztowna operacja |
| POST /ai/analyze | 60/h | ⬆️ Zmienione z 10/h |
| GET /ai/market-overview/{symbol} | 60/h | ⬆️ Zmienione z 20/h |
| POST /ai/sentiment | 60/h | ⬆️ Zmienione z 30/h |
| POST /ai/event-impact | 60/h | ⬆️ Zmienione z 30/h |

---

## Uwagi Bezpieczeństwa

1. **Wszystkie endpointy wymagają klucza API** w headerze `X-API-Key`
2. **Rate limiting** chroni przed nadużyciami
3. **Walidacja danych** przez Pydantic
4. **Prepared statements** w bazie danych

---

## Przykłady Użycia

### Scenariusz 1: Monitorowanie wyników analiz

```bash
# Pobierz ostatnie analizy dla EUR/USD
curl -X GET "http://localhost:8000/ai/analysis-results?symbol=EUR/USD&limit=5" \
  -H "X-API-Key: your-api-key"

# Pobierz szczegóły konkretnej analizy
curl -X GET "http://localhost:8000/ai/analysis-results/123" \
  -H "X-API-Key: your-api-key"
```

### Scenariusz 2: Sprawdzenie kosztów OpenAI

```bash
# Statystyki z ostatniego tygodnia
curl -X GET "http://localhost:8000/ai/token-statistics?start_date=2026-01-10&end_date=2026-01-16" \
  -H "X-API-Key: your-api-key"
```

### Scenariusz 3: Zmiana konfiguracji

```bash
# Zwiększ interwał analiz do 1 godziny
curl -X PUT "http://localhost:8000/ai/analysis-config" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"analysis_interval": 60}'

# Ogranicz symbole do 5 najważniejszych
curl -X PUT "http://localhost:8000/ai/analysis-config" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "enabled_symbols": ["EUR/USD", "GBP/USD", "USD/JPY", "AAPL/USD", "XAU/USD"]
  }'
```

### Scenariusz 4: Ręczna analiza

```bash
# Uruchom analizę dla wybranych symboli
curl -X POST "http://localhost:8000/ai/trigger-analysis" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["EUR/USD", "GBP/USD"],
    "timeframe": "1h"
  }'
```

---

## Dokumentacja OpenAPI/Swagger

Pełna dokumentacja API dostępna pod adresem:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## Wsparcie

W razie problemów:
1. Sprawdź logi: `docker-compose logs -f backend`
2. Sprawdź status: `curl http://localhost:8000/health`
3. Sprawdź dokumentację: http://localhost:8000/docs
