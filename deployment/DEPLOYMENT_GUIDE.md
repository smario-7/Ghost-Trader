# 🚀 DEPLOYMENT TRADING BOT z n8n - Instrukcja Krok po Kroku

## 📋 Przegląd

Integrujesz Trading Bot z istniejącym n8n, który już działa na:
- **Domain:** n8n-mario.space
- **Port:** 8443 (n8n)
- **Database:** PostgreSQL
- **Tunnel:** Cloudflare

Po deployment będziesz mieć:
- **n8n:** https://n8n-mario.space (bez zmian)
- **Trading Dashboard:** https://trading.n8n-mario.space (NOWY)
- **Trading API:** https://api.n8n-mario.space (NOWY - opcjonalny)

---

## ⚙️ KROK 1: Przygotowanie plików

### SSH do Raspberry Pi

```bash
ssh twoja_nazwa_użytkownika@raspberry.local
# lub
ssh twoja_nazwa_użytkownika@IP_ADRES
```

### Struktura katalogów

```bash
# Przejdź do katalogu gdzie masz n8n
cd ~/n8n

# Sprawdź strukturę
ls -la
# Powinieneś widzieć: docker-compose.yml

# Utwórz katalog dla trading bot
mkdir -p trading-bot
cd trading-bot

# Utwórz strukturę
mkdir -p backend/app
mkdir -p frontend
mkdir -p data/logs
mkdir -p data/backups
mkdir -p deployment
```

### Skopiuj pliki projektu

**Opcja A: Z archiwum**
```bash
# Jeśli masz archiwum trading-bot-openai.tar.gz
cd ~/n8n
tar -xzf trading-bot-openai.tar.gz

# Struktura powinna wyglądać:
# ~/n8n/
# ├── docker-compose.yml (istniejący n8n)
# ├── trading-bot/ (nowy)
# │   ├── backend/
# │   ├── frontend/
# │   ├── data/
# │   └── deployment/
```

**Opcja B: Ręczne kopiowanie**
```bash
# Skopiuj pliki z projektu do odpowiednich katalogów
# (szczegóły zależą od tego jak dostarczysz pliki)
```

---

## 🔑 KROK 2: Konfiguracja zmiennych środowiskowych

### Utwórz plik .env

```bash
cd ~/n8n/trading-bot
cp deployment/.env.example .env
nano .env
```

### Wypełnij .env

```bash
# ===== WYMAGANE - MUSISZ UZUPEŁNIĆ =====

# 1. Telegram Bot Token (z @BotFather)
TELEGRAM_BOT_TOKEN=TUTAJ_WKLEJ_TOKEN

# 2. Telegram Chat ID (z getUpdates)
TELEGRAM_CHAT_ID=TUTAJ_WKLEJ_CHAT_ID

# 3. OpenAI API Key (z platform.openai.com)
OPENAI_API_KEY=sk-proj-TUTAJ_WKLEJ_KEY

# 4. API Key (wygeneruj: openssl rand -hex 32)
API_KEY=TUTAJ_WKLEJ_WYGENEROWANY_KEY

# ===== OPCJONALNE (możesz zostawić domyślne) =====

OPENAI_MODEL=gpt-4o
ENVIRONMENT=production
CHECK_INTERVAL=15
LOG_LEVEL=INFO
AUTO_BACKUP=true
CORS_ORIGINS=http://localhost:8080,https://trading.n8n-mario.space
```

**Zapisz:** `Ctrl+O`, `Enter`, `Ctrl+X`

### Sprawdź uprawnienia

```bash
# .env musi być zabezpieczony!
chmod 600 .env
```

---

## 🐳 KROK 3: Aktualizacja docker-compose.yml

### Backup istniejącego docker-compose

```bash
cd ~/n8n
cp docker-compose.yml docker-compose.yml.backup
```

### Zastąp docker-compose.yml

```bash
# Skopiuj nowy zintegrowany docker-compose
cp trading-bot/deployment/docker-compose.integrated.yml docker-compose.yml

# LUB edytuj ręcznie:
nano docker-compose.yml
```

**Upewnij się że:**
1. Wszystkie ścieżki są poprawne (`./trading-bot/...`)
2. n8n webhook URL to: `https://n8n-mario.space`
3. CORS_ORIGINS zawiera: `https://trading.n8n-mario.space`

### Sprawdź docker-compose

```bash
# Walidacja składni
docker-compose config

# Powinno wyświetlić pełną konfigurację bez błędów
```

---

## ☁️ KROK 4: Konfiguracja Cloudflare Tunnel

### Backup istniejącej konfiguracji

```bash
cp ~/.cloudflared/config.yml ~/.cloudflared/config.yml.backup
```

### Zaktualizuj config.yml

```bash
nano ~/.cloudflared/config.yml
```

**Zastąp zawartość:**

```yaml
tunnel: TWÓJ_ID_TUNELU  # NIE ZMIENIAJ
credentials-file: /home/TWOJA_NAZWA/.cloudflared/TWÓJ_ID_TUNELU.json  # DOSTOSUJ

ingress:
  # n8n (istniejący)
  - hostname: n8n-mario.space
    service: http://localhost:8443
  
  # Trading Bot Dashboard (NOWY)
  - hostname: trading.n8n-mario.space
    service: http://localhost:8080
  
  # Trading Bot API (NOWY - opcjonalny)
  - hostname: api.n8n-mario.space
    service: http://localhost:8000
  
  # Catch-all (MUSI być ostatni)
  - service: http_status:404
```

**⚠️ WAŻNE:** 
- Zastąp `TWÓJ_ID_TUNELU` swoim rzeczywistym ID tunelu
- Zastąp `TWOJA_NAZWA` swoją nazwą użytkownika
- Zachowaj dokładne wcięcia (YAML!)

**Zapisz:** `Ctrl+O`, `Enter`, `Ctrl+X`

### Skopiuj config do /etc/cloudflared

```bash
sudo cp ~/.cloudflared/config.yml /etc/cloudflared/config.yml
sudo chown root:root /etc/cloudflared/config.yml
sudo chmod 644 /etc/cloudflared/config.yml
```

---

## 🌐 KROK 5: Konfiguracja DNS w Cloudflare Dashboard

### Dodaj nowe subdomeny

1. **Wejdź do Cloudflare Dashboard:**
   - https://dash.cloudflare.com/
   - Wybierz swoją strefę (n8n-mario.space)

2. **Przejdź do:** Zero Trust → Access → Tunnels

3. **Wybierz swój tunnel** (ten który ma ID z config.yml)

4. **Kliknij:** "Public Hostnames"

5. **Dodaj pierwszy hostname:**
   ```
   Subdomain: trading
   Domain: n8n-mario.space
   Service:
     Type: HTTP
     URL: localhost:8080
   ```
   **Save**

6. **Dodaj drugi hostname (opcjonalny - dla API):**
   ```
   Subdomain: api
   Domain: n8n-mario.space
   Service:
     Type: HTTP
     URL: localhost:8000
   ```
   **Save**

**✅ Po zapisaniu Cloudflare automatycznie utworzy DNS records!**

---

## 🚀 KROK 6: Uruchomienie

### Zatrzymaj istniejące kontenery

```bash
cd ~/n8n
docker-compose down
```

### Zbuduj i uruchom wszystko

```bash
# Build obrazów (pierwsze uruchomienie - może zająć 5-10 min)
docker-compose build

# Uruchom wszystko
docker-compose up -d

# Sprawdź status
docker-compose ps
```

**Powinieneś widzieć:**
```
NAME                        STATUS
postgres                    Up (healthy)
n8n                         Up
trading-bot-backend         Up (healthy)
trading-bot-scheduler       Up
trading-bot-frontend        Up
```

### Restart Cloudflare Tunnel

```bash
sudo systemctl restart cloudflared
sudo systemctl status cloudflared
```

**Sprawdź czy:**
- Status: `active (running)`
- Logi pokazują: "Registered tunnel connection"

---

## 🧪 KROK 7: Testy

### Test 1: Health checks (lokalnie)

```bash
# Backend health
curl http://localhost:8000/health

# Oczekiwany output:
# {"status":"healthy","timestamp":"...","database":true,"telegram":true}

# Frontend
curl http://localhost:8080

# Oczekiwany output: HTML dashboard
```

### Test 2: Przez Cloudflare

```bash
# Dashboard (publicznie dostępny)
curl https://trading.n8n-mario.space

# API health (publicznie dostępny)
curl https://api.n8n-mario.space/health
```

**Otwórz w przeglądarce:**
- https://trading.n8n-mario.space
- Powinieneś widzieć dashboard!

### Test 3: Telegram

```bash
export API_KEY="<twój_api_key_z_env>"

# Test lokalnie
curl -X POST http://localhost:8000/test-telegram \
  -H "X-API-Key: $API_KEY"

# LUB przez Cloudflare
curl -X POST https://api.n8n-mario.space/test-telegram \
  -H "X-API-Key: $API_KEY"
```

**Sprawdź Telegram - powinieneś dostać wiadomość!** ✅

### Test 4: AI Analysis

```bash
curl -X POST https://api.n8n-mario.space/ai/analyze \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "BTC/USDT",
    "timeframe": "1h"
  }'
```

**Powinieneś dostać JSON z analizą GPT!** 🤖

---

## 📊 KROK 8: Monitoring

### Sprawdź logi

```bash
cd ~/n8n

# Wszystkie kontenery
docker-compose logs -f

# Tylko backend
docker-compose logs -f trading-bot-backend

# Tylko scheduler
docker-compose logs -f trading-bot-scheduler

# n8n (sprawdź czy działa nadal)
docker-compose logs -f n8n
```

### Sprawdź pliki logów

```bash
# Logi trading bot
tail -f trading-bot/data/logs/bot.log
tail -f trading-bot/data/logs/scheduler.log

# Rozmiar bazy danych
ls -lh trading-bot/data/trading_bot.db

# Backupy (jeśli włączone)
ls -lh trading-bot/data/backups/
```

### Sprawdź zużycie zasobów

```bash
# Kontenery
docker stats

# Pamięć Raspberry Pi
free -h

# Dysk
df -h
```

---

## 🔐 KROK 9: Zabezpieczenie (opcjonalnie)

### Opcja A: Cloudflare Access (ZALECANE)

1. Zero Trust → Access → Applications
2. Add application:
   - Name: Trading Bot
   - Domain: trading.n8n-mario.space
3. Add Policy:
   - Name: Allow My Email
   - Action: Allow
   - Include: Email equals: twój@email.com
4. Save

**Teraz tylko Ty masz dostęp do dashboardu!**

### Opcja B: IP Whitelist

1. Cloudflare Dashboard → Security → WAF
2. Custom Rules → Create Rule
3. Rule:
   ```
   Field: IP Source Address
   Operator: is in list
   Value: <twój_statyczny_IP>
   Action: Allow
   ```

---

## 🔄 KROK 10: Auto-update (opcjonalnie)

### Utwórz skrypt update

```bash
nano ~/update-trading-bot.sh
```

```bash
#!/bin/bash
cd ~/n8n
git pull  # jeśli używasz git
docker-compose down
docker-compose build --no-cache trading-bot-backend trading-bot-scheduler
docker-compose up -d
sudo systemctl restart cloudflared
```

```bash
chmod +x ~/update-trading-bot.sh
```

### Dodaj do cron (codziennie o 3:00)

```bash
crontab -e
```

Dodaj linię:
```
0 3 * * * /home/TWOJA_NAZWA/update-trading-bot.sh >> /home/TWOJA_NAZWA/update.log 2>&1
```

---

## 🎯 Finalna struktura

```
/home/TWOJA_NAZWA/
└── n8n/
    ├── docker-compose.yml  ← Zintegrowany (n8n + trading bot)
    ├── .n8n/               ← n8n data (istniejący)
    └── trading-bot/
        ├── backend/
        │   ├── app/
        │   ├── Dockerfile
        │   └── requirements.txt
        ├── frontend/
        │   ├── dashboard.html
        │   └── index.html
        ├── data/
        │   ├── trading_bot.db
        │   ├── logs/
        │   │   ├── bot.log
        │   │   └── scheduler.log
        │   └── backups/
        ├── deployment/
        │   ├── docker-compose.integrated.yml
        │   ├── cloudflared-config.yml
        │   └── .env.example
        └── .env  ← Twoje dane (GITIGNORED!)
```

---

## ✅ Checklist

Po deployment sprawdź:

- [ ] `docker-compose ps` - wszystkie kontenery UP
- [ ] `curl http://localhost:8000/health` - backend działa
- [ ] `curl http://localhost:8080` - frontend działa
- [ ] `https://n8n-mario.space` - n8n działa (bez zmian)
- [ ] `https://trading.n8n-mario.space` - dashboard działa
- [ ] `https://api.n8n-mario.space/health` - API działa
- [ ] Telegram test - wiadomość przychodzi
- [ ] AI analysis test - GPT odpowiada
- [ ] Logi się zapisują - `tail -f trading-bot/data/logs/bot.log`
- [ ] Cloudflared działa - `sudo systemctl status cloudflared`

---

## 🆘 Troubleshooting

### Problem: Port już zajęty (8000 lub 8080)

```bash
# Sprawdź co używa portu
sudo netstat -tulpn | grep :8000
sudo netstat -tulpn | grep :8080

# Zmień port w docker-compose.yml
nano docker-compose.yml
# Zmień ports: "8001:8000" zamiast "8000:8000"
```

### Problem: Container nie startuje

```bash
# Sprawdź logi
docker-compose logs trading-bot-backend

# Rebuild bez cache
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Problem: Cloudflare nie działa

```bash
# Sprawdź konfigurację
cat ~/.cloudflared/config.yml

# Restart
sudo systemctl restart cloudflared
sudo systemctl status cloudflared

# Sprawdź logi
sudo journalctl -u cloudflared -f
```

### Problem: Brak pamięci na RPi

```bash
# Sprawdź
free -h

# Zwiększ swap
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
# CONF_SWAPSIZE=2048
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

### Problem: .env nie działa

```bash
# Sprawdź czy plik istnieje
ls -la ~/n8n/trading-bot/.env

# Sprawdź uprawnienia
chmod 600 ~/n8n/trading-bot/.env

# Sprawdź czy kontenery widzą .env
docker-compose exec trading-bot-backend env | grep OPENAI
```

---

## 🎉 Gotowe!

Teraz masz:
- ✅ n8n na https://n8n-mario.space (bez zmian)
- ✅ Trading Dashboard na https://trading.n8n-mario.space
- ✅ Trading API na https://api.n8n-mario.space
- ✅ Wszystko w jednym docker-compose
- ✅ Wszystko przez Cloudflare Tunnel
- ✅ Automatyczne backupy
- ✅ Monitoring i logi

### Dostęp:

**Dashboard:**
```
https://trading.n8n-mario.space
```

**n8n z Trading Bot integration:**
```
W n8n możesz teraz wywołać Trading Bot API:
- HTTP Request Node
- URL: http://trading-bot-backend:8000/ai/analyze
- Headers: X-API-Key: <twój_key>
```

**API (zewnętrzne):**
```
https://api.n8n-mario.space/ai/analyze
```

### Komendy użytkowe:

```bash
# Status
cd ~/n8n && docker-compose ps

# Restart wszystkiego
cd ~/n8n && docker-compose restart

# Restart tylko trading bot
cd ~/n8n && docker-compose restart trading-bot-backend trading-bot-scheduler

# Logi
cd ~/n8n && docker-compose logs -f trading-bot-backend

# Stop
cd ~/n8n && docker-compose down

# Start
cd ~/n8n && docker-compose up -d
```

**Szczęśliwego tradingu! 🚀📈**
