# ⚡ QUICK START GUIDE

## 🚀 Uruchomienie w 5 minut

### Krok 1: Przygotuj Telegram Bot

```bash
# 1. Otwórz Telegram i znajdź @BotFather
# 2. Wyślij: /newbot
# 3. Podaj nazwę: "Mój Trading Bot"
# 4. Podaj username: "moj_trading_bot"
# 5. Zapisz TOKEN (np. 1234567890:ABCdefGHIjkl...)

# 6. Pobierz CHAT_ID:
#    - Wyślij wiadomość do swojego bota
#    - Otwórz w przeglądarce:
https://api.telegram.org/bot<TWÓJ_TOKEN>/getUpdates
#    - Znajdź: "chat":{"id": 123456789}
#    - To jest twoje CHAT_ID
```

### Krok 2: Sklonuj i konfiguruj

```bash
# Sklonuj projekt
git clone <repo-url> trading-bot
cd trading-bot

# Skopiuj przykładowy .env
cp .env.example .env

# Edytuj .env
nano .env
```

### Krok 3: Uzupełnij .env

```bash
# WYMAGANE - Uzupełnij te 3 wartości:

# 1. Token z @BotFather
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz

# 2. Chat ID z getUpdates
TELEGRAM_CHAT_ID=123456789

# 3. Wygeneruj API Key (32+ znaki)
# Linux/Mac:
openssl rand -hex 32
# Windows PowerShell:
python -c "import secrets; print(secrets.token_hex(32))"
# Wklej wynik:
API_KEY=<wygenerowany_key_tutaj>

# OPCJONALNE - zostaw domyślne lub dostosuj:
ENVIRONMENT=production
CHECK_INTERVAL=15
LOG_LEVEL=INFO
```

### Krok 4: Uruchom

```bash
# Metoda 1: Docker (zalecane)
docker-compose up -d

# Metoda 2: Bez Dockera
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 &
python -m app.scheduler &
```

### Krok 5: Sprawdź

```bash
# Health check
curl http://localhost:8000/health

# Frontend
xdg-open http://localhost:8080  # Linux
open http://localhost:8080      # Mac
start http://localhost:8080     # Windows

# Logi
docker-compose logs -f  # lub
tail -f data/logs/bot.log
```

## ✅ Pierwsze kroki

### 1. Test Telegram

```bash
export API_KEY="twój_api_key_z_env"

curl -X POST http://localhost:8000/test-telegram \
  -H "X-API-Key: $API_KEY"

# Powinieneś dostać wiadomość na Telegramie!
```

### 2. Utwórz pierwszą strategię

```bash
curl -X POST http://localhost:8000/strategies \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "BTC RSI",
    "strategy_type": "RSI",
    "symbol": "BTC/USDT",
    "timeframe": "1h",
    "parameters": {
      "period": 14,
      "overbought": 70,
      "oversold": 30
    }
  }'
```

### 3. Sprawdź sygnały

```bash
curl -X POST http://localhost:8000/check-signals \
  -H "X-API-Key: $API_KEY"
```

### 4. Zobacz strategie

```bash
curl -H "X-API-Key: $API_KEY" \
  http://localhost:8000/strategies
```

## 🎯 Co dalej?

### Dokumentacja
- **README.md** - Pełna dokumentacja
- **SECURITY.md** - Bezpieczeństwo
- **API Docs** - http://localhost:8000/docs

### Konfiguracja
- Zmień interwał sprawdzania: `CHECK_INTERVAL` w .env
- Włącz/wyłącz backupy: `AUTO_BACKUP` w .env
- Dostosuj rate limit: `RATE_LIMIT_PER_MINUTE` w .env

### Monitoring
```bash
# Logi live
docker-compose logs -f

# Statystyki
curl -H "X-API-Key: $API_KEY" \
  http://localhost:8000/statistics

# Health co 10s
watch -n 10 'curl -s http://localhost:8000/health | jq'
```

## ⚠️ Troubleshooting

### "Config error"
```bash
# Sprawdź .env
cat .env

# Upewnij się że są wszystkie 3 wymagane:
# TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, API_KEY
```

### "Telegram nie działa"
```bash
# Test ręczny
curl https://api.telegram.org/bot<TOKEN>/getMe

# Sprawdź czy bot ma dostęp do czatu
# Wyślij wiadomość do bota ręcznie
```

### "Port zajęty"
```bash
# Zmień port w .env
API_PORT=8001

# Restart
docker-compose restart
```

### "Database locked"
```bash
# Restart schedulera
docker-compose restart scheduler
```

## 🎉 Gotowe!

System działa i:
- ✅ Sprawdza sygnały co 15 min (domyślnie)
- ✅ Wysyła powiadomienia przez Telegram
- ✅ Robi backup co 24h (domyślnie)
- ✅ Loguje wszystko do `data/logs/`
- ✅ Jest zabezpieczony API Key

**Miłego tradingu! 📈**

---

## 🔗 Przydatne linki

- **API Docs**: http://localhost:8000/docs
- **Frontend**: http://localhost:8080
- **Health**: http://localhost:8000/health
- **Logi**: `tail -f data/logs/bot.log`
- **Backupy**: `ls -lh data/backups/`
