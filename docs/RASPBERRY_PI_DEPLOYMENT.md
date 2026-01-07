# 🍓 Deployment na Raspberry Pi z n8n

## 📋 Twoja aktualna konfiguracja

```
Raspberry Pi 4
├─ Docker + Docker Compose ✅
├─ n8n running on Docker ✅
├─ Cloudflare Tunnel ✅
└─ Domain: https://n8n-mario.space ✅
```

## 🎯 Co dodajemy

```
Trading Bot
├─ Backend (FastAPI) na porcie 8000
├─ Frontend (Dashboard) na porcie 8080
├─ Scheduler (sprawdzanie sygnałów)
└─ Cloudflare Tunnel (opcjonalnie: trading.n8n-mario.space)
```

## 📦 Dane które potrzebuję

### 1. **Aktualna struktura Cloudflare Tunnel**

Wyślij mi zawartość twojego pliku konfiguracji:

```bash
# Pokaż mi config Cloudflare
cat ~/.cloudflared/config.yml

# Lub jeśli używasz docker-compose dla n8n:
cat /path/to/n8n/docker-compose.yml
```

**Potrzebuję:**
- Jak masz skonfigurowany tunnel?
- Jaki hostname używasz? (n8n-mario.space)
- Czy masz multiple services w jednym tunnelu?

### 2. **Ścieżki na Raspberry Pi**

```bash
# Gdzie masz n8n?
# Przykład: /home/pi/n8n/ lub /opt/n8n/

# Sprawdź:
docker ps | grep n8n
# Pokaż mi OUTPUT
```

**Potrzebuję:**
- Gdzie chcesz zainstalować trading bot? (np. `/home/pi/trading-bot/`)
- Czy masz osobny katalog dla docker projektów?

### 3. **Ports już używane**

```bash
# Sprawdź zajęte porty
sudo netstat -tulpn | grep LISTEN

# Lub
docker ps --format "table {{.Names}}\t{{.Ports}}"
```

**Potrzebuję:**
- Lista używanych portów
- Czy 8000 i 8080 są wolne?

### 4. **Telegram Bot Info**

**Musisz podać:**
- `TELEGRAM_BOT_TOKEN` (z @BotFather)
- `TELEGRAM_CHAT_ID` (twój ID czatu)

Jak uzyskać:
```bash
# 1. Token - wyślij @BotFather:
/newbot

# 2. Chat ID - wyślij wiadomość do bota, potem:
curl https://api.telegram.org/bot<TOKEN>/getUpdates
# Znajdź "chat":{"id": TWOJE_ID}
```

### 5. **OpenAI API Key**

**Musisz podać:**
- `OPENAI_API_KEY` (z https://platform.openai.com/api-keys)

Utwórz:
1. Wejdź: https://platform.openai.com/api-keys
2. Kliknij: "Create new secret key"
3. Skopiuj klucz (zaczyna się od `sk-proj-...`)

## 🚀 Instrukcja Deployment

### Krok 1: Przygotowanie

```bash
# SSH do Raspberry Pi
ssh pi@raspberry.local
# lub ssh pi@<IP_ADRES>

# Przejdź do katalogu projektów (dostosuj do swojego)
cd ~
# lub cd /opt/

# Sklonuj/rozpakuj trading bot
mkdir trading-bot
cd trading-bot

# Rozpakuj archiwum (jeśli masz)
tar -xzf trading-bot-openai.tar.gz
```

### Krok 2: Konfiguracja .env

```bash
# Skopiuj przykładowy .env
cp .env.example .env

# Edytuj .env
nano .env
```

**Wklej swoje dane:**

```bash
# ===== WYMAGANE =====

# Telegram (z @BotFather)
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=123456789

# OpenAI (z platform.openai.com)
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_MODEL=gpt-4o

# API Key dla bota (wygeneruj: openssl rand -hex 32)
API_KEY=<TUTAJ_WKLEJ_WYGENEROWANY_KEY>

# ===== OPCJONALNE (zostaw domyślne) =====

DATABASE_PATH=/app/data/trading_bot.db
API_HOST=0.0.0.0
API_PORT=8000
CHECK_INTERVAL=15
LOG_LEVEL=INFO
AUTO_BACKUP=true
```

Zapisz: `Ctrl+O`, `Enter`, `Ctrl+X`

### Krok 3: Docker Compose - Integracja z n8n

Masz 2 opcje:

#### Opcja A: Osobny docker-compose (ZALECANE)

```bash
# Uruchom trading bot osobno
docker-compose up -d

# Sprawdź status
docker-compose ps
```

#### Opcja B: Dodaj do istniejącego docker-compose z n8n

```bash
# Edytuj istniejący docker-compose z n8n
nano /path/to/n8n/docker-compose.yml
```

Dodaj na końcu (przed `networks:`):

```yaml
  # Trading Bot
  trading-bot-backend:
    build: /home/pi/trading-bot/backend
    container_name: trading-bot-backend
    ports:
      - "8000:8000"
    volumes:
      - /home/pi/trading-bot/data:/app/data
      - /home/pi/trading-bot/.env:/app/.env:ro
    environment:
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - OPENAI_MODEL=${OPENAI_MODEL}
      - API_KEY=${API_KEY}
    restart: unless-stopped
    networks:
      - n8n-network

  trading-bot-scheduler:
    build: /home/pi/trading-bot/backend
    container_name: trading-bot-scheduler
    volumes:
      - /home/pi/trading-bot/data:/app/data
      - /home/pi/trading-bot/.env:/app/.env:ro
    command: python -m app.scheduler
    restart: unless-stopped
    networks:
      - n8n-network
    depends_on:
      - trading-bot-backend

  trading-bot-frontend:
    image: nginx:alpine
    container_name: trading-bot-frontend
    ports:
      - "8080:80"
    volumes:
      - /home/pi/trading-bot/frontend:/usr/share/nginx/html:ro
    restart: unless-stopped
    networks:
      - n8n-network
```

Potem:
```bash
# Restart całego stacka
docker-compose down
docker-compose up -d
```

### Krok 4: Cloudflare Tunnel - Dodaj Trading Bot

Masz 2 opcje:

#### Opcja A: Nowy subdomain (trading.n8n-mario.space)

1. **Wejdź do Cloudflare Dashboard:**
   - https://dash.cloudflare.com/
   - Zero Trust → Access → Tunnels
   - Wybierz swój istniejący tunnel

2. **Dodaj nową Public Hostname:**
   ```
   Subdomain: trading
   Domain: n8n-mario.space
   Service:
     Type: HTTP
     URL: localhost:8080  (trading bot frontend)
   ```

3. **Dodaj drugą Public Hostname dla API:**
   ```
   Subdomain: trading-api
   Domain: n8n-mario.space
   Service:
     Type: HTTP
     URL: localhost:8000  (trading bot API)
   ```

4. **Save**

Teraz dostępne:
- Dashboard: https://trading.n8n-mario.space
- API: https://trading-api.n8n-mario.space

#### Opcja B: Przez n8n (jeśli chcesz integrację)

Możesz też wywoływać Trading Bot API bezpośrednio z n8n workflows!

W n8n dodaj HTTP Request node:
```
URL: http://trading-bot-backend:8000/ai/analyze
Method: POST
Headers: X-API-Key: <TWOJ_API_KEY>
Body:
{
  "symbol": "BTC/USDT",
  "timeframe": "1h"
}
```

### Krok 5: Test

```bash
# 1. Sprawdź czy kontenery działają
docker ps | grep trading

# 2. Test lokalne
# Health check
curl http://localhost:8000/health

# Frontend
curl http://localhost:8080

# 3. Test przez Cloudflare (jeśli skonfigurowałeś)
curl https://trading.n8n-mario.space
curl https://trading-api.n8n-mario.space/health

# 4. Test Telegram
export API_KEY="<twój_api_key>"
curl -X POST http://localhost:8000/test-telegram \
  -H "X-API-Key: $API_KEY"

# Powinieneś dostać wiadomość na Telegramie!

# 5. Test AI analysis
curl -X POST http://localhost:8000/ai/analyze \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"symbol": "BTC/USDT", "timeframe": "1h"}'
```

### Krok 6: Monitoring

```bash
# Logi real-time
docker-compose logs -f

# Tylko backend
docker-compose logs -f trading-bot-backend

# Tylko scheduler
docker-compose logs -f trading-bot-scheduler

# Logi w plikach
tail -f data/logs/bot.log
tail -f data/logs/scheduler.log
```

## 📊 Struktura po instalacji

```
/home/pi/
├── n8n/
│   ├── docker-compose.yml
│   └── ...
└── trading-bot/
    ├── backend/
    │   ├── app/
    │   ├── Dockerfile
    │   └── requirements.txt
    ├── frontend/
    │   └── dashboard.html
    ├── data/
    │   ├── logs/
    │   │   ├── bot.log
    │   │   └── scheduler.log
    │   ├── backups/
    │   └── trading_bot.db
    ├── .env  (gitignored!)
    └── docker-compose.yml
```

## 🔐 Cloudflare Tunnel - Bezpieczeństwo

Jeśli wystawiasz przez Cloudflare, dodaj zabezpieczenie:

### Option 1: Cloudflare Access (ZALECANE)

1. Zero Trust → Access → Applications
2. Add application:
   - Name: Trading Bot
   - Domain: trading.n8n-mario.space
3. Add Policy:
   - Allow only your email/IP

### Option 2: IP Whitelist w Cloudflare

1. Security → WAF → Custom Rules
2. Add rule:
   - Field: IP Source Address
   - Operator: is in list
   - Value: <twój_IP>
   - Action: Allow

## 🔄 Auto-update

Opcjonalnie możesz dodać automatyczne pull z git:

```bash
# Utwórz skrypt
nano /home/pi/trading-bot/update.sh
```

```bash
#!/bin/bash
cd /home/pi/trading-bot
git pull
docker-compose down
docker-compose up -d --build
```

```bash
# Uprawnienia
chmod +x update.sh

# Dodaj do cron (codziennie o 3:00)
crontab -e
# Dodaj:
0 3 * * * /home/pi/trading-bot/update.sh >> /home/pi/trading-bot/update.log 2>&1
```

## 🆘 Troubleshooting

### Port już zajęty

```bash
# Zmień port w docker-compose.yml
ports:
  - "8001:8000"  # Zamiast 8000:8000

# Lub zatrzymaj konfliktujący service
docker ps | grep 8000
docker stop <container_id>
```

### Brak pamięci na RPi

```bash
# Sprawdź pamięć
free -h

# Zwiększ swap
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
# CONF_SWAPSIZE=2048
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

### Timeout OpenAI API

```bash
# W .env zmień model na szybszy
OPENAI_MODEL=gpt-4o-mini
```

### Logi nie działają

```bash
# Utwórz katalogi
mkdir -p data/logs data/backups
chmod 777 data/logs data/backups
```

## 📞 Potrzebne dane - Podsumowanie

**Wyślij mi:**

1. ✅ **Cloudflare config**
   ```bash
   cat ~/.cloudflared/config.yml
   ```

2. ✅ **n8n docker-compose**
   ```bash
   cat /path/to/n8n/docker-compose.yml
   ```

3. ✅ **Używane porty**
   ```bash
   docker ps --format "table {{.Names}}\t{{.Ports}}"
   ```

4. ✅ **Preferowana ścieżka instalacji**
   - np. `/home/pi/trading-bot/`
   - lub `/opt/trading-bot/`

5. ✅ **Telegram & OpenAI keys** (przygotuj, nie wysyłaj!)
   - TELEGRAM_BOT_TOKEN
   - TELEGRAM_CHAT_ID
   - OPENAI_API_KEY

## 🎉 Po instalacji

Dostęp:
- **Dashboard**: https://trading.n8n-mario.space (jeśli skonfigurujesz)
- **API**: https://trading-api.n8n-mario.space
- **Telegram**: Powiadomienia o sygnałach

Komendy:
```bash
# Status
docker-compose ps

# Restart
docker-compose restart

# Stop
docker-compose down

# Update
git pull && docker-compose up -d --build
```

**Gotowe! 🚀**
