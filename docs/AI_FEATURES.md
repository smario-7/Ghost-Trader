# 🧠 AI-POWERED TRADING BOT - Dokumentacja

## 🎯 Przegląd

Trading Bot 2.0 wykorzystuje **Claude AI** do kompleksowej analizy rynków finansowych, łącząc:

### 📊 Źródła danych

1. **Dane makroekonomiczne**
   - Stopy procentowe Fed
   - Inflacja (CPI, PCE)
   - PKB
   - Bezrobocie
   - Kalendarz ekonomiczny

2. **Wiadomości finansowe**
   - Reuters, Bloomberg, CNBC
   - CoinDesk, CoinTelegraph (crypto)
   - Breaking news
   - Sentiment analysis

3. **Wskaźniki techniczne**
   - RSI, MACD, Bollinger Bands
   - Moving Averages
   - Volume, Volatility

4. **Wydarzenia światowe**
   - Posiedzenia Fed/ECB
   - Publikacje danych
   - Ważne wydarzenia geopolityczne

## 🤖 Jak działa AI Strategy

```
┌─────────────────┐
│  Dane Makro     │ ──┐
│  (Fed, CPI...)  │   │
└─────────────────┘   │
                      │
┌─────────────────┐   │
│  Wiadomości     │ ──┤
│  (Reuters...)   │   │     ┌──────────────┐
└─────────────────┘   ├────►│  Claude AI   │
                      │     │   Analysis   │
┌─────────────────┐   │     └──────┬───────┘
│  Wskaźniki      │ ──┤            │
│  Techniczne     │   │            │
└─────────────────┘   │            ▼
                      │     ┌──────────────┐
┌─────────────────┐   │     │  BUY/SELL/   │
│  Wydarzenia     │ ──┘     │     HOLD     │
│  (kalendarz)    │         │  + Reasoning │
└─────────────────┘         └──────────────┘
```

## 🚀 Użycie

### 1. Dodaj strategię AI do .env

```bash
# Włącz AI Strategy
AI_STRATEGY_ENABLED=true
```

### 2. Wywołaj AI analysis

```bash
# Analiza dla BTC
curl -X POST http://localhost:8000/ai/analyze \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "BTC/USDT",
    "timeframe": "1h"
  }'
```

### 3. Przykładowa odpowiedź

```json
{
  "symbol": "BTC/USDT",
  "recommendation": "BUY",
  "confidence": 78,
  "ai_analysis": {
    "reasoning": "Analiza wskazuje na pozytywne perspektywy dla BTC w krótkim terminie. Fed sygnalizuje możliwość obniżek stóp w 2025, co historycznie wspierało aktywa ryzykowne. Wskaźniki techniczne (RSI 45) sugerują przestrzeń do wzrostu. Sentiment w wiadomościach jest pozytywny (70%), z rosnącym zainteresowaniem instytucjonalnym.",
    "key_factors": [
      "Fed sygnalizuje obniżki stóp w 2025",
      "Inflacja spadła do 3.2% (poniżej prognozy)",
      "RSI w strefie neutralnej (45) - przestrzeń do wzrostu",
      "Pozytywny sentiment w wiadomościach (70%)",
      "Rosnące napływy do BTC ETF"
    ],
    "risks": [
      "Wysokie napięcia geopolityczne na Bliskim Wschodzie",
      "Możliwe opóźnienie obniżek stóp jeśli inflacja pozostanie wysoka",
      "Nadchodzące publikacje danych makro (NFP za 3 dni)"
    ],
    "time_horizon": "short",
    "sentiment_score": 70,
    "macro_impact": "positive",
    "news_impact": "positive",
    "technical_signal": "neutral"
  },
  "macro_summary": "Fed: 5.5%, Inflacja: 3.2%, Następne posiedzenie: 2025-02-01",
  "news_summary": "10 wiadomości (+ 6, - 2)",
  "technical_summary": "Cena: $48,500.00, RSI: 45.0",
  "events_summary": "2 ważnych wydarzeń w najbliższych dniach",
  "decision_components": {
    "macro_score": "positive",
    "news_sentiment": "positive",
    "technical_signal": "neutral",
    "event_risk": "medium"
  }
}
```

## 📡 Nowe endpointy API

### 1. AI Analysis

```bash
POST /ai/analyze
```

**Body:**
```json
{
  "symbol": "BTC/USDT",
  "timeframe": "1h"
}
```

**Response:** Kompleksowa analiza AI z rekomendacją

### 2. Market Overview

```bash
GET /ai/market-overview/{symbol}
```

**Response:** Pełny przegląd rynku (makro + news + technical + sentiment)

### 3. Sentiment Analysis

```bash
POST /ai/sentiment
```

**Body:**
```json
{
  "symbol": "BTC/USDT",
  "hours_back": 24
}
```

**Response:** Analiza sentymentu z wiadomości

### 4. Event Impact Analysis

```bash
POST /ai/event-impact
```

**Body:**
```json
{
  "event": "Fed podniósł stopy o 0.25%",
  "symbol": "BTC/USDT"
}
```

**Response:** Analiza wpływu konkretnego wydarzenia

## 🔧 Konfiguracja

### Zmienne środowiskowe

```bash
# AI Strategy
AI_STRATEGY_ENABLED=true
AI_CHECK_INTERVAL=60  # minuty (rzadziej niż tech indicators)

# Data Sources (opcjonalne API keys dla prawdziwych danych)
FRED_API_KEY=your_fred_key              # Federal Reserve data
NEWS_API_KEY=your_newsapi_key           # NewsAPI.org
ALPHA_VANTAGE_KEY=your_av_key          # Alpha Vantage
CRYPTOCOMPARE_KEY=your_cc_key          # CryptoCompare
```

### Demo vs Produkcja

**Demo mode (bez API keys):**
- Używa przykładowych danych
- Działa od razu bez konfiguracji
- Idealne do testów

**Production mode (z API keys):**
- Pobiera prawdziwe dane makro
- Rzeczywiste wiadomości
- Aktualne wskaźniki
- Dokładniejsze analizy

## 📊 Przykłady użycia

### 1. Sprawdź sentiment przed tradingiem

```bash
# Przed otwarciem pozycji, sprawdź co mówi AI
curl -X POST http://localhost:8000/ai/analyze \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"symbol": "BTC/USDT", "timeframe": "4h"}'

# Jeśli confidence > 70% i recommendation = BUY -> rozważ pozycję
```

### 2. Monitoruj wpływ wydarzeń

```bash
# Po ważnym wydarzeniu (np. decyzja Fed)
curl -X POST http://localhost:8000/ai/event-impact \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "event": "Fed utrzymał stopy na 5.5%",
    "symbol": "BTC/USDT"
  }'
```

### 3. Dzienny przegląd rynku

```bash
# Codziennie rano - sprawdź co się dzieje
curl http://localhost:8000/ai/market-overview/BTC/USDT \
  -H "X-API-Key: $API_KEY"
```

## 🎯 Use Cases

### Use Case 1: Trading decyzje
```
1. Bot sprawdza wskaźniki techniczne → Sygnał HOLD
2. Bot sprawdza AI Strategy → Sygnał BUY (confidence 85%)
3. AI wykrył: Fed sygnalizuje obniżki + pozytywny sentiment
4. → Finalnie: BUY (AI ma wyższy priorytet przy wysokiej pewności)
```

### Use Case 2: Risk management
```
1. Masz otwartą pozycję LONG na BTC
2. AI wykrywa breaking news: "Geopolityczne napięcia eskalują"
3. AI analysis → immediate_impact: "negative", recommendation: "SELL"
4. → Otrzymujesz alert na Telegram: "Rozważ zamknięcie pozycji"
```

### Use Case 3: Long-term outlook
```
1. AI analizuje dane makro na najbliższe 3 miesiące
2. Fed planuje obniżki stóp + inflacja spada
3. AI: "medium_term_outlook: bullish"
4. → Strategia: Akumuluj stopniowo na spadkach
```

## 🧪 Testing

### Test AI lokalmente

```bash
cd backend
python -m app.services.ai_strategy

# Powinno wyświetlić przykładową analizę AI
```

### Test przez API

```bash
# Health check z AI
curl http://localhost:8000/ai/health \
  -H "X-API-Key: $API_KEY"

# Test analizy
curl -X POST http://localhost:8000/ai/analyze \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"symbol": "BTC/USDT", "timeframe": "1h"}'
```

## 📈 Zalety AI Strategy

### 1. Holistyczny widok
- **Nie tylko** wskaźniki techniczne
- **Ale też** makro + news + wydarzenia
- Claude łączy wszystko w spójną analizę

### 2. Kontekst rynkowy
- Rozumie *dlaczego* rynek się rusza
- Przewiduje reakcje na wydarzenia
- Identyfikuje trendy wcześniej

### 3. Natural language reasoning
- Nie tylko "BUY" ale **dlaczego** BUY
- Lista kluczowych czynników
- Identyfikacja ryzyk

### 4. Adaptacyjność
- Uczy się z nowych danych
- Rozumie kontekst bieżący
- Nie stuck w historycznych wzorcach

## ⚠️ Ograniczenia

### 1. Rate limiting
- Claude API ma limity requestów
- Używaj rozważnie (np. co 30-60 min, nie co 5 min)

### 2. Koszty
- Claude API może generować koszty
- Monitoruj użycie
- Optymalizuj prompty

### 3. Nie jest wyrocznia
- AI to **narzędzie wspomagające**, nie zastępstwo
- Zawsze własna analiza + risk management
- Nie ślepo follow sygnałów

### 4. Data quality
- W demo mode: przykładowe dane
- W produkcji: jakość zależy od źródeł API

## 🔐 Bezpieczeństwo

### API Keys
```bash
# Wszystkie API keys w .env (gitignored)
NEWS_API_KEY=xyz123
FRED_API_KEY=abc456

# NIE commituj .env!
```

### Rate limiting
```bash
# AI endpoints mają własny, niższy limit
AI_RATE_LIMIT_PER_HOUR=20  # vs 60/min dla tech indicators
```

## 📚 Dodatkowe zasoby

### Data sources w produkcji:

**Makro:**
- FRED API: https://fred.stlouisfed.org/docs/api/
- Trading Economics: https://tradingeconomics.com/api

**News:**
- NewsAPI: https://newsapi.org/
- Alpha Vantage: https://www.alphavantage.co/
- CryptoCompare: https://www.cryptocompare.com/

**Kalendarz:**
- Forex Factory: https://www.forexfactory.com/
- Investing.com: https://www.investing.com/economic-calendar/

## 🎉 Podsumowanie

AI Strategy to **game changer**:
- ✅ Claude AI analizuje dane jak profesjonalny trader
- ✅ Łączy makro + news + technical + sentiment
- ✅ Natural language reasoning
- ✅ Gotowe do użycia (demo) lub rozszerzenia (production)

**Zacznij używać już teraz:**
```bash
curl -X POST http://localhost:8000/ai/analyze \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"symbol": "BTC/USDT"}'
```

🚀 **Happy AI Trading!**
