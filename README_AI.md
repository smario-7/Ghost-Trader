# 🤖 Trading Bot 2.0 + AI - Production Ready

## 🌟 NOWOŚĆ: AI-Powered Analysis!

Bot teraz wykorzystuje **Claude AI** do kompleksowej analizy rynków:

```
📊 Dane makro (Fed, inflacja, PKB)
    +
📰 Wiadomości (Reuters, Bloomberg)
    +
📈 Wskaźniki techniczne (RSI, MACD)
    +
📅 Wydarzenia światowe
    ⬇
🧠 Claude AI Analysis
    ⬇
💡 Inteligentny sygnał BUY/SELL/HOLD
   + szczegółowe uzasadnienie
```

👉 **[Zobacz dokumentację AI Features](docs/AI_FEATURES.md)**

---

## 📋 Spis treści
- [Przegląd](#przegląd)
- [Nowe funkcje AI](#nowe-funkcje-ai)
- [Wymagania](#wymagania)
- [Quick Start](#quick-start)
- [API](#api)
- [AI Endpoints](#ai-endpoints)
- [Dokumentacja](#dokumentacja)

## 🎯 Przegląd

Trading Bot to system automatycznego generowania sygnałów tradingowych z:
- ✅ **Wskaźniki techniczne** (RSI, MACD, Bollinger, MA)
- ✅ **Claude AI analysis** (makro + news + sentiment)
- ✅ **Telegram integration** (powiadomienia)
- ✅ **Production-ready** (bezpieczny, udokumentowany)

## 🧠 Nowe funkcje AI

### Co AI dodaje do bota?

#### 1. Analiza makroekonomiczna
- Stopy Fed, inflacja, PKB, bezrobocie
- Kalendarz ekonomiczny (FOMC, NFP, CPI)
- Wpływ polityki monetarnej

#### 2. Analiza newsów i sentymentu
- Reuters, Bloomberg, CNBC, CoinDesk
- Sentiment analysis (positive/neutral/negative)
- Breaking news alerts

#### 3. Analiza wydarzeń światowych
- Wydarzenia geopolityczne
- Publikacje danych ekonomicznych
- Wpływ na rynki

#### 4. Natural Language Reasoning
- **Nie tylko** "BUY" ale **DLACZEGO** BUY
- Lista kluczowych czynników
- Identyfikacja ryzyk
- Confidence score (0-100%)

### Przykład AI sygnału:

```json
{
  "recommendation": "BUY",
  "confidence": 78,
  "reasoning": "Fed sygnalizuje obniżki stóp w 2025, inflacja spadła do 3.2%. RSI w strefie neutralnej (45) daje przestrzeń do wzrostu. Pozytywny sentiment w wiadomościach (70%) z rosnącymi napływami do BTC ETF.",
  "key_factors": [
    "Fed sygnalizuje obniżki stóp",
    "Inflacja poniżej prognozy",
    "Pozytywny sentiment w newsach",
    "Rosnące napływy instytucjonalne"
  ],
  "risks": [
    "Napięcia geopolityczne",
    "Nadchodzące dane makro za 3 dni"
  ]
}
```

## 📦 Wymagania

### Minimalne
- **Python**: 3.11+
- **Docker**: 20.10+ (opcjonalnie)
- **RAM**: 512MB
- **Dysk**: 1GB

### Kompatybilność
- ✅ **Raspberry Pi 4** compatible
- ✅ **ARM64** support
- ✅ **Low-power** (~5W)

## 🚀 Quick Start

### Metoda 1: Automatyczny setup (zalecane)

```bash
# 1. Rozpakuj i wejdź
tar -xzf trading-bot.tar.gz
cd trading-bot

# 2. Uruchom automatyczny setup
chmod +x setup.sh
./setup.sh

# 3. Gotowe! Bot działa
# Frontend: http://localhost:8080
# API: http://localhost:8000
```

### Metoda 2: Ręczny setup

```bash
# 1. Skopiuj .env
cp .env.example .env

# 2. Edytuj .env (WAŻNE!)
nano .env
# Uzupełnij:
# - TELEGRAM_BOT_TOKEN (z @BotFather)
# - TELEGRAM_CHAT_ID (z getUpdates)
# - API_KEY (wygeneruj: openssl rand -hex 32)

# 3. Uruchom
docker-compose up -d

# 4. Sprawdź
docker-compose logs -f
```

## 📡 API

### Standard endpoints

```bash
# Health check
curl http://localhost:8000/health

# Lista strategii
curl -H "X-API-Key: $API_KEY" \
  http://localhost:8000/strategies

# Sprawdź sygnały
curl -X POST -H "X-API-Key: $API_KEY" \
  http://localhost:8000/check-signals
```

### 🧠 AI Endpoints (NOWE!)

#### 1. Kompleksowa analiza AI

```bash
curl -X POST http://localhost:8000/ai/analyze \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "BTC/USDT",
    "timeframe": "1h"
  }'
```

**Zwraca:**
- Rekomendacja (BUY/SELL/HOLD)
- Confidence (0-100%)
- Szczegółowe uzasadnienie
- Kluczowe czynniki
- Lista ryzyk
- Komponenty decyzji (makro, news, technical, events)

#### 2. Market Overview

```bash
curl -H "X-API-Key: $API_KEY" \
  http://localhost:8000/ai/market-overview/BTC/USDT
```

**Zwraca:** Pełny przegląd rynku (makro + news + technical + sentiment)

#### 3. Sentiment Analysis

```bash
curl -X POST http://localhost:8000/ai/sentiment \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "BTC/USDT",
    "hours_back": 24
  }'
```

**Zwraca:** Analiza sentymentu z wiadomości

#### 4. Event Impact

```bash
curl -X POST http://localhost:8000/ai/event-impact \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "event": "Fed podniósł stopy o 0.25%",
    "symbol": "BTC/USDT"
  }'
```

**Zwraca:** Analiza wpływu wydarzenia na rynek

## 📚 Dokumentacja

### Główne dokumenty:
- **[AI_FEATURES.md](docs/AI_FEATURES.md)** - Pełna dokumentacja AI
- **[QUICKSTART.md](docs/QUICKSTART.md)** - Uruchomienie w 5 minut
- **[SECURITY.md](docs/SECURITY.md)** - Bezpieczeństwo
- **[ANALYSIS.md](docs/ANALYSIS.md)** - Analiza techniczna

### Konfiguracja AI

```bash
# W .env

# Włącz AI Strategy
AI_STRATEGY_ENABLED=true
AI_CHECK_INTERVAL=60  # minuty

# Opcjonalne API keys (dla prawdziwych danych)
FRED_API_KEY=           # Federal Reserve data
NEWS_API_KEY=           # NewsAPI.org
ALPHA_VANTAGE_KEY=      # Alpha Vantage
CRYPTOCOMPARE_KEY=      # CryptoCompare
```

**Demo mode:** Działa od razu bez API keys (przykładowe dane)
**Production mode:** Z API keys (prawdziwe dane)

## 🎯 Use Cases

### 1. Trading decyzje
```
Tech indicators: HOLD (RSI: 50)
AI Analysis: BUY (confidence: 85%)
  Reasoning: Fed sygnalizuje obniżki + pozytywny sentiment
  
→ Finalnie: BUY (AI ma wyższy priorytet)
```

### 2. Risk management
```
Masz pozycję LONG
AI wykrywa: "Geopolityczne napięcia eskalują"
AI: recommendation: SELL, immediate_impact: negative

→ Alert na Telegram: "Rozważ zamknięcie pozycji"
```

### 3. Market overview
```
Codziennie rano: curl /ai/market-overview/BTC/USDT
  
Otrzymujesz:
- Makro environment (Fed, inflacja)
- Sentiment (z newsów)
- Technical overview
- Upcoming events
- Event risk level

→ Planujesz strategię na dzień
```

## 🔐 Bezpieczeństwo

System jest **production-ready** z:
- ✅ API Key authentication
- ✅ Rate limiting (różne dla AI i tech endpoints)
- ✅ Input validation (Pydantic)
- ✅ SQL injection protection
- ✅ CORS configuration
- ✅ Structured logging
- ✅ Automatic backups

## 📊 Architektura

### Tradycyjne strategie
```
Price Data → RSI/MACD/Bollinger → Signal
```

### AI Strategy
```
Price Data ──┐
Macro Data ──┤
News ────────┼──► Claude AI ──► Signal + Reasoning
Events ──────┤
Technical ───┘
```

## 🎉 Features

### Wskaźniki techniczne (v1.0)
- ✅ RSI (Relative Strength Index)
- ✅ MACD
- ✅ Bollinger Bands
- ✅ Moving Averages

### AI Analysis (v2.0 - NOWE!)
- ✅ Claude AI integration
- ✅ Macro data analysis (Fed, CPI, GDP)
- ✅ News sentiment analysis
- ✅ Event impact assessment
- ✅ Natural language reasoning
- ✅ Risk identification
- ✅ Multi-factor decision making

### Infrastruktura
- ✅ FastAPI backend
- ✅ SQLite database
- ✅ Telegram notifications
- ✅ Docker deployment
- ✅ Automatic backups
- ✅ Health checks
- ✅ Structured logging

## ⚠️ Ważne uwagi

### AI Rate limiting
```
Tech indicators: 60 req/min
AI endpoints: 10-30 req/hour (niższy limit - API kosztowne)
```

### Koszty AI
- Claude API może generować koszty
- Używaj rozważnie (co 30-60 min, nie co 5 min)
- Monitoruj usage

### Nie jest wyrocznią!
- AI to **narzędzie wspomagające**, nie zastępstwo
- Zawsze własna analiza + risk management
- Nie ślepo follow sygnałów

## 📈 Przykłady

### Test AI analysis

```bash
# 1. Sprawdź co AI myśli o BTC
curl -X POST http://localhost:8000/ai/analyze \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"symbol": "BTC/USDT", "timeframe": "4h"}'

# 2. Zobacz reasoning
# AI wyjaśni dlaczego BUY/SELL/HOLD

# 3. Sprawdź confidence
# Jeśli > 70% → rozważ sygnał
```

### Monitor wydarzeń

```bash
# Po ważnym wydarzeniu (np. Fed decision)
curl -X POST http://localhost:8000/ai/event-impact \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "event": "Fed utrzymał stopy na 5.5%",
    "symbol": "BTC/USDT"
  }'

# AI przeanalizuje: immediate/short/medium term impact
```

### Dzienny przegląd

```bash
# Codziennie rano
curl http://localhost:8000/ai/market-overview/BTC/USDT \
  -H "X-API-Key: $API_KEY"

# Otrzymujesz kompletny market overview
```

## 🛠️ Troubleshooting

### "AI analysis failed"
```bash
# Sprawdź logi
docker-compose logs backend | grep AI

# Zwykle: timeout lub rate limit
# Rozwiązanie: Poczekaj 1h i spróbuj ponownie
```

### "No macro data"
```bash
# Demo mode: używa przykładowych danych (OK!)
# Production mode: dodaj API keys do .env
```

### Inne problemy
Zobacz **[QUICKSTART.md](docs/QUICKSTART.md)** - sekcja Troubleshooting

## 🔄 Aktualizacje

```bash
# Pull nowy kod
git pull

# Rebuild
docker-compose down
docker-compose up -d --build

# Sprawdź
docker-compose logs -f
```

## 📞 Wsparcie

### Problemy?
1. Sprawdź [QUICKSTART.md](docs/QUICKSTART.md)
2. Zobacz [AI_FEATURES.md](docs/AI_FEATURES.md)
3. Przeczytaj logi: `docker-compose logs`

### Pytania o AI?
- Przeczytaj [AI_FEATURES.md](docs/AI_FEATURES.md)
- Przykłady użycia w docs/

## 📝 Licencja

MIT License - użyj jak chcesz!

## 🎉 Podsumowanie

### Otrzymujesz:
- ✅ **Tradycyjne wskaźniki** (RSI, MACD, Bollinger)
- ✅ **AI-powered analysis** (Claude + makro + news + sentiment)
- ✅ **Production-ready** (bezpieczny, udokumentowany)
- ✅ **Easy deployment** (setup.sh)
- ✅ **Raspberry Pi compatible**

### Quick commands:

```bash
# Setup
./setup.sh

# Test AI
curl -X POST http://localhost:8000/ai/analyze \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"symbol": "BTC/USDT"}'

# Monitor
docker-compose logs -f
```

**Szczęśliwego tradingu z AI! 🚀🤖**
