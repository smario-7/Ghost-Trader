# Trading Bot - Rozbudowana Wersja 2.0

## Spis treści

- [Przegląd](#przegląd)
- [Nowe funkcje](#nowe-funkcje)
- [Wymagania](#wymagania)
- [Instalacja](#instalacja)
- [Konfiguracja](#konfiguracja)
- [Uruchomienie](#uruchomienie)
- [Deployment](#deployment)
- [API](#api)
- [AI Signal Integration](#ai-signal-integration)
- [Bezpieczeństwo](#bezpieczeństwo)
- [Troubleshooting](#troubleshooting)

## Przegląd

Trading Bot to system automatycznego generowania sygnałów tradingowych z integracją Telegram. Wersja 2.0 wprowadza kompleksowe zabezpieczenia, walidację danych i profesjonalną strukturę kodu.

### Architektura

```
┌─────────────┐      ┌─────────────┐      ┌──────────────┐
│   Backend   │◄────►│  Scheduler  │◄────►│   Database   │
│  (FastAPI)  │      │  (Signals)  │      │   (SQLite)   │
└──────┬──────┘      └──────┬──────┘      └──────────────┘
       │                    │
       └────────┬───────────┘
                ▼
        ┌───────────────┐
        │   Telegram    │
        │      Bot      │
        └───────────────┘
```

## Nowe funkcje v2.0

### Bezpieczeństwo

- **Zmienne środowiskowe** - zero hardkodowanych wartości
- **API Key authentication** - zabezpieczone endpointy
- **Rate limiting** - ochrona przed flood
- **Walidacja Pydantic** - bezpieczne dane wejściowe
- **Prepared statements** - ochrona przed SQL injection
- **CORS konfiguracja** - kontrolowane origins

### Funkcjonalność

- **Strukturalne logowanie** - rotacja plików, poziomy
- **Health checks** - monitoring stanu systemu
- **Automatyczne backupy** - zabezpieczenie danych
- **Error handling** - globalna obsługa błędów
- **Statistics API** - metryki i statystyki

### Kod

- **Dependency injection** - czysta architektura
- **Type hints** - pełna typizacja
- **Modularny design** - separacja warstw
- **Docker ready** - łatwy deployment

## Wymagania

### Minimalne

- **Python**: 3.11.13 (zarządzany przez conda)
- **Conda**: Miniconda lub Anaconda
- **Docker**: 20.10+ (opcjonalnie, dla produkcji)
- **Docker Compose**: 2.0+ (opcjonalnie)
- **RAM**: 512MB (Raspberry Pi compatible!)
- **Dysk**: 1GB

> **Środowisko conda**: Utwórz środowisko z pliku `environment.yml` (conda env create -f environment.yml), aktywuj: `conda activate ghost-trader`.

### Raspberry Pi 4

- **Kompatybilny** z ARM64
- **Niskoprzekładny** (~5W)
- **Stabilny 24/7**

## Instalacja

### Metoda 1: Docker (zalecana)

```bash
# 1. Sklonuj projekt
git clone <repo-url> trading-bot
cd trading-bot

# 2. Skopiuj przykładowy .env
cp .env.example .env

# 3. Edytuj .env (WAŻNE!)
nano .env

# 4. Wygeneruj API Key
openssl rand -hex 32

# 5. Uruchom
docker-compose up -d

# 6. Sprawdź logi
docker-compose logs -f
```

### Metoda 2: Conda (zalecana dla development)

```bash
# 1. Sklonuj projekt
git clone <repo-url> trading-bot
cd trading-bot

# 2. Utwórz środowisko conda
conda env create -f environment.yml

# 3. Aktywuj środowisko
conda activate ghost-trader
# LUB użyj skryptu:
source activate.sh

# 4. Skopiuj i edytuj .env
cp .env.example .env
nano .env

# 5. Uruchom backend
cd backend
python -m app.main
```

**Automatyczna aktywacja środowiska:**

```bash
# Zainstaluj direnv
sudo apt install direnv  # Ubuntu/Debian
brew install direnv      # macOS

# Dodaj do ~/.bashrc
echo 'eval "$(direnv hook bash)"' >> ~/.bashrc
source ~/.bashrc

# Zezwól na automatyczną aktywację
direnv allow

# Od teraz środowisko aktywuje się automatycznie!
```

### Metoda 3: Bezpośrednio z venv (alternatywa)

```bash
# 1. Utwórz venv
python3.11 -m venv venv
source venv/bin/activate  # Linux/Mac
# lub
venv\Scripts\activate  # Windows

# 2. Zainstaluj zależności
cd backend
pip install -r requirements.txt

# 3. Konfiguracja .env
cp ../.env.example ../.env
nano ../.env

# 4. Uruchom backend
uvicorn app.main:app --reload

# W osobnym terminalu - scheduler
python -m app.scheduler
```

## Konfiguracja

### 1. Telegram Bot

```bash
# Utwórz bota przez @BotFather
1. Napisz do @BotFather w Telegram
2. Wyślij: /newbot
3. Podaj nazwę i username
4. Zapisz otrzymany TOKEN

# Pobierz CHAT_ID
1. Wyślij wiadomość do swojego bota
2. Odwiedź: https://api.telegram.org/bot<TOKEN>/getUpdates
3. Znajdź "chat":{"id": TWOJE_ID}
```

### 2. Plik .env

```bash
# ===== WYMAGANE =====
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=123456789
API_KEY=<wygeneruj: openssl rand -hex 32>

# ===== OPCJONALNE =====
# Baza danych
DATABASE_PATH=/app/data/trading_bot.db

# API
API_HOST=0.0.0.0
API_PORT=8000
CHECK_INTERVAL=15  # minuty

# Logowanie
LOG_LEVEL=INFO
LOG_FILE=/app/data/logs/bot.log

# Backup
AUTO_BACKUP=true
BACKUP_INTERVAL=24  # godziny

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60

# CORS
CORS_ORIGINS=http://localhost:8080,http://localhost:3000

# ----- AI Signal Integration -----
ANALYSIS_INTERVAL=30
ANALYSIS_ENABLED=true
ANALYSIS_SYMBOLS_LIMIT=10
NOTIFICATION_THRESHOLD=60
# Wagi agregatora (suma=100): AI, Technical, Macro, News – patrz .env.example
AGGREGATOR_WEIGHT_AI=40
AGGREGATOR_WEIGHT_TECHNICAL=30
AGGREGATOR_WEIGHT_MACRO=20
AGGREGATOR_WEIGHT_NEWS=10
```

### 3. Walidacja konfiguracji

```bash
# Sprawdź czy wszystko OK
docker-compose exec backend python -c "from app.config import get_settings; print('Config OK')"
```

## Uruchomienie

### Docker

```bash
# Start
docker-compose up -d

# Status
docker-compose ps

# Logi
docker-compose logs -f backend
docker-compose logs -f scheduler

# Stop
docker-compose down

# Restart
docker-compose restart

# Rebuild (po zmianach w kodzie)
docker-compose up -d --build
```

### Ręcznie

```bash
# Terminal 1 - Backend (venv w katalogu backend)
cd backend
python3.11 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Terminal 2 - Scheduler
cd backend
source venv/bin/activate
python -m app.scheduler

# Terminal 3 - Frontend (dev)
cd frontend
python -m http.server 8081
# W Dockerze dashboard jest na http://localhost:8080 (nginx)
```

## Deployment

Wdrożenie w produkcji (np. integracja z n8n, osobna domena): w folderze **deployment/** znajdziesz [DEPLOYMENT_GUIDE.md](deployment/DEPLOYMENT_GUIDE.md) (instrukcja krok po kroku), `docker-compose.integrated.yml` oraz przykładowy `.env` do konfiguracji.

## API

### Endpoints

#### Public

- `GET /` - Info o API
- `GET /health` - Health check

#### Protected (wymagają X-API-Key header)

- **Strategie:** `GET/POST/PUT/DELETE /strategies`, `/strategies/{id}`
- **Sygnały:** `POST /check-signals`, `GET /signals/recent`, `GET /signals/strategy/{id}`
- **AI:** `GET/PUT /ai/analysis-results`, `/ai/analysis-config`, `POST /ai/trigger-analysis`, `GET /ai/token-statistics`
- **Stream:** `GET /stream/updates`, `GET /stream/ai-updates` (SSE)
- **Telegram:** `/telegram/*` (test, ustawienia, mute)
- **Scheduler:** `GET/PUT /scheduler/config`, `GET /scheduler/status`
- **Inne:** `/activity-logs`, `/statistics`, `POST /test-telegram`, `/chart-data`, `/macro-data`

Pełna lista endpointów: **Swagger UI** po uruchomieniu – `http://localhost:8000/docs`

### Przykłady użycia

```bash
# Ustaw API Key
export API_KEY="twoj_api_key_tutaj"

# Health check (bez auth)
curl http://localhost:8000/health

# Lista strategii
curl -H "X-API-Key: $API_KEY" http://localhost:8000/strategies

# Utwórz strategię RSI
curl -X POST http://localhost:8000/strategies \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "BTC RSI Conservative",
    "strategy_type": "RSI",
    "symbol": "BTC/USDT",
    "timeframe": "1h",
    "parameters": {
      "period": 14,
      "overbought": 70,
      "oversold": 30
    }
  }'

# Sprawdź sygnały
curl -X POST http://localhost:8000/check-signals \
  -H "X-API-Key: $API_KEY"

# Test Telegram
curl -X POST http://localhost:8000/test-telegram \
  -H "X-API-Key: $API_KEY"
```

### Dokumentacja interaktywna

Po uruchomieniu (tylko development):

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## AI Signal Integration

System **AI Signal Integration** łączy 4 źródła analiz (AI, Technical, Macro, News) w jeden sygnał tradingowy używając głosowania większościowego.

### Kluczowe cechy

- **Głosowanie większościowe** - sygnał tylko gdy >= 60% źródeł się zgadza
- **Automatyczne analizy** - konfigurowalne interwały (5-1440 minut)
- **Wszystkie symbole** - forex, indeksy, akcje, metale
- **Monitoring kosztów** - śledzenie tokenów OpenAI
- **Dashboard** - wizualizacja wyników wszystkich analiz

### Quick Start

```bash
# 1. Dodaj do .env
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
ANALYSIS_INTERVAL=30
NOTIFICATION_THRESHOLD=60

# 2. Uruchom
docker-compose up -d

# 3. Sprawdź wyniki w dashboard
http://localhost:8080

# 4. Lub przez API
curl -H "X-API-Key: $API_KEY" \
  "http://localhost:8000/ai/analysis-results"
```

### Dokumentacja

**Pełna dokumentacja: [docs/README_AI.md](docs/README_AI.md)**

Kompleksowy przewodnik zawierający:

- Szczegółowy opis architektury i algorytmu głosowania większościowego
- Wszystkie API endpoints z przykładami użycia
- Konfigurację i zmienne środowiskowe
- Szczegółowe szacunki kosztów OpenAI
- Best practices i optymalizację
- Troubleshooting i rozwiązywanie problemów
- Testy i przykłady kodu

### Koszty OpenAI


| Model       | Koszt/analiza | 10 symboli (30 min) |
| ----------- | ------------- | ------------------- |
| GPT-4o      | $0.025        | $360/miesiąc        |
| GPT-4o-mini | $0.0025       | $36/miesiąc         |


**Rekomendacja:** Użyj GPT-4o-mini (10x taniej, nadal bardzo dobra jakość)

## Bezpieczeństwo

### Checklist

- .env w .gitignore
- API Key wygenerowany (min 32 znaki)
- CORS origins skonfigurowane
- Rate limiting włączony
- Logowanie działa
- Backupy włączone
- HTTPS w produkcji (Caddy/Nginx)
- Firewall skonfigurowany

### Generowanie bezpiecznego API Key

```bash
# Linux/Mac
openssl rand -hex 32

# lub Python
python3 -c "import secrets; print(secrets.token_hex(32))"
```

## Troubleshooting

### Problem: "Config error"

```bash
# Sprawdź .env
cat .env | grep -v "^#"

# Sprawdź czy wszystkie wymagane zmienne są ustawione
docker-compose exec backend python -c "from app.config import get_settings; s=get_settings(); print(s)"
```

### Problem: "Telegram nie wysyła"

```bash
# Sprawdź token
curl https://api.telegram.org/bot<TOKEN>/getMe

# Test manuall
curl -X POST http://localhost:8000/test-telegram \
  -H "X-API-Key: $API_KEY"

# Sprawdź logi
docker-compose logs backend | grep telegram
```

### Problem: "Database locked"

```bash
# Zatrzymaj scheduler przed ręcznymi operacjami
docker-compose stop scheduler

# Wykonaj operację
# ...

# Uruchom ponownie
docker-compose start scheduler
```

### Problem: "Rate limit exceeded"

```bash
# Zwiększ limit w .env
RATE_LIMIT_PER_MINUTE=120

# Restart
docker-compose restart backend
```

### Problem: "Port already in use"

```bash
# Zmień port w .env
API_PORT=8001

# lub docker-compose.yml
ports:
  - "8001:8000"
```

## Struktura projektu

```
trading-bot/
├── backend/
│   ├── app/
│   │   ├── api/                   # Routery HTTP
│   │   │   ├── health.py, strategies.py, signals.py
│   │   │   ├── telegram.py, scheduler.py, ai.py
│   │   │   ├── streams.py, statistics.py, activity.py
│   │   │   └── chart_data.py
│   │   ├── models/
│   │   │   └── models.py          # Modele Pydantic
│   │   ├── services/
│   │   │   ├── strategy_service.py
│   │   │   ├── market_data_service.py
│   │   │   ├── telegram_service.py
│   │   │   ├── ai_strategy.py
│   │   │   ├── auto_analysis_scheduler.py
│   │   │   └── signal_aggregator_service.py
│   │   ├── utils/
│   │   │   ├── database.py
│   │   │   └── logger.py
│   │   ├── config.py              # Konfiguracja
│   │   ├── main.py                # FastAPI app
│   │   └── scheduler.py           # Scheduler
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── dashboard.html
│   ├── js/components/             # Alpine.js
│   └── css/
├── deployment/
│   ├── DEPLOYMENT_GUIDE.md        # Instrukcja wdrożenia (n8n, produkcja)
│   ├── docker-compose.integrated.yml
│   └── .env.example
├── data/                          # Persistent data (gitignored)
│   ├── trading_bot.db
│   ├── logs/
│   └── backups/
├── docs/
│   ├── README_AI.md               # Dokumentacja AI
│   └── STRUKTURA.txt
├── .env                           # Konfiguracja (gitignored)
├── .env.example                   # Przykład konfiguracji
├── docker-compose.yml
└── README.md
```

## Monitoring

### Logi

```bash
# Real-time logs
docker-compose logs -f

# Tylko backend
docker-compose logs -f backend

# Ostatnie 100 linii
docker-compose logs --tail=100 backend

# Z grep
docker-compose logs backend | grep ERROR
```

### Metryki

```bash
# Statystyki
curl -H "X-API-Key: $API_KEY" http://localhost:8000/statistics

# Health check
watch -n 10 'curl -s http://localhost:8000/health | jq'
```

### Backup

```bash
# Lista backupów
ls -lh data/backups/

# Przywróć z backupu
docker-compose stop backend scheduler
cp data/backups/trading_bot_YYYYMMDD_HHMMSS.db data/trading_bot.db
docker-compose start backend scheduler
```

## Aktualizacje

```bash
# Zatrzymaj
docker-compose down

# Pull nowy kod
git pull

# Rebuild
docker-compose build

# Uruchom
docker-compose up -d

# Sprawdź logi
docker-compose logs -f
```

## Wsparcie

### Problemy?

1. Sprawdź logi: `docker-compose logs`
2. Zobacz [Troubleshooting](#troubleshooting)

### Pytania?

- Email: [support@yourdomain.com](mailto:support@yourdomain.com)
- Issues: GitHub Issues

## Licencja

MIT License - użyj jak chcesz!

## Gotowe!

```bash
# Quick start
cp .env.example .env
nano .env  # Uzupełnij TOKEN, CHAT_ID, API_KEY
docker-compose up -d
docker-compose logs -f

# Done!
```

**Szczęśliwego tradingu!**