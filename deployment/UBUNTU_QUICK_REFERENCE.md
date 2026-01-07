# 🐧 Ubuntu Quick Reference Card

## ⚡ Super Quick Start

```bash
# 1. Zainstaluj Docker (jeśli nie masz)
curl -fsSL https://get.docker.com -o get-docker.sh && sudo sh get-docker.sh
sudo usermod -aG docker $USER
newgrp docker

# 2. Deploy Trading Bot
cd ~/n8n
tar -xzf trading-bot-n8n-integrated.tar.gz
cd trading-bot && cp .env.example .env && nano .env && cd ..
./trading-bot/deployment/option2-path/install.sh  # Opcja 2 (prostsze)

# 3. Done! ✅
```

---

## 📋 Wymagania Systemowe

| Komponent | Minimum | Zalecane |
|-----------|---------|----------|
| **OS** | Ubuntu 20.04 | Ubuntu 22.04+ |
| **RAM** | 2GB | 4GB+ |
| **CPU** | 2 cores | 4 cores |
| **Dysk** | 10GB wolne | 20GB+ |
| **Docker** | 20.10+ | Latest |

---

## 🔧 Instalacja Zależności

```bash
# Ubuntu 20.04/22.04/24.04
sudo apt update
sudo apt install -y curl git nano

# Docker + Docker Compose
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker

# Sprawdź
docker --version
docker-compose --version
```

---

## 🚀 Deployment

### OPCJA 1: Subdomain
```bash
cd ~/n8n
tar -xzf trading-bot-n8n-integrated.tar.gz
cd trading-bot
cp .env.example .env
nano .env  # Wypełnij: TELEGRAM_*, OPENAI_*, API_KEY
cd ..
chmod +x trading-bot/deployment/option1-subdomain/install.sh
./trading-bot/deployment/option1-subdomain/install.sh
```

### OPCJA 2: Path (prostsze)
```bash
cd ~/n8n
tar -xzf trading-bot-n8n-integrated.tar.gz
cd trading-bot
cp .env.example .env
nano .env  # Wypełnij: TELEGRAM_*, OPENAI_*, API_KEY
cd ..
chmod +x trading-bot/deployment/option2-path/install.sh
./trading-bot/deployment/option2-path/install.sh
```

---

## 🔑 Zmienne .env

```bash
# Wymagane:
TELEGRAM_BOT_TOKEN=123:ABC...      # @BotFather
TELEGRAM_CHAT_ID=123456789         # getUpdates
OPENAI_API_KEY=sk-proj-...         # platform.openai.com
API_KEY=$(openssl rand -hex 32)    # Auto-generate

# Opcjonalne (możesz zostawić domyślne):
OPENAI_MODEL=gpt-4o
CHECK_INTERVAL=15
LOG_LEVEL=INFO
```

---

## 🎯 Komendy Docker

```bash
# Status
docker-compose ps

# Logi (wszystkie)
docker-compose logs -f

# Logi (tylko trading bot)
docker-compose logs -f trading-bot-backend

# Restart
docker-compose restart

# Rebuild
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Stop
docker-compose down

# Start
docker-compose up -d

# Sprawdź zużycie zasobów
docker stats
```

---

## 🧪 Testy

```bash
# Health check
curl http://localhost:8000/health

# Test Telegram
export API_KEY="<z_pliku_.env>"
curl -X POST http://localhost:8000/test-telegram \
  -H "X-API-Key: $API_KEY"

# Test AI
curl -X POST http://localhost:8000/ai/analyze \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"symbol":"BTC/USDT","timeframe":"1h"}'

# Dashboard (przeglądarka)
# OPCJA 1: https://trading.twojadomena-n8n.pl
# OPCJA 2: https://twojadomena-n8n.pl/trading
```

---

## 🛠️ Troubleshooting

### Port zajęty
```bash
sudo lsof -i :8000  # Co używa portu?
# Zmień port w docker-compose.yml
```

### Permission denied (Docker)
```bash
sudo usermod -aG docker $USER
newgrp docker
```

### Container nie startuje
```bash
docker-compose logs trading-bot-backend
docker-compose down && docker-compose up -d
```

### Brak pamięci
```bash
free -h  # Sprawdź RAM
# Zwiększ swap:
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### .env nie działa
```bash
cat trading-bot/.env | grep OPENAI_API_KEY
# Sprawdź brak spacji: KEY=value (nie KEY = value)
chmod 600 trading-bot/.env
```

---

## 🔥 Firewall (UFW)

```bash
# Otwórz porty
sudo ufw allow 8000/tcp   # API
sudo ufw allow 8080/tcp   # Frontend
sudo ufw allow 8443/tcp   # n8n
sudo ufw enable
sudo ufw status
```

---

## 🔄 Auto-start (Systemd)

```bash
sudo nano /etc/systemd/system/trading-bot.service
```

```ini
[Unit]
Description=Trading Bot
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/TWOJA_NAZWA/n8n
ExecStart=/usr/bin/docker-compose up -d
ExecStop=/usr/bin/docker-compose down
User=TWOJA_NAZWA

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable trading-bot
sudo systemctl start trading-bot
```

---

## 📊 Monitoring

```bash
# Logi live
docker-compose logs -f

# Logi pliki
tail -f trading-bot/data/logs/bot.log

# Zasoby
docker stats

# Dysk
df -h

# RAM
free -h

# System logs
sudo journalctl -u docker -f
```

---

## 📍 Lokalizacje (Ubuntu)

```
~/n8n/                              # Projekt
~/n8n/trading-bot/.env              # Config (SECRET!)
~/n8n/trading-bot/data/logs/        # Logi
~/n8n/trading-bot/data/backups/     # Backupy
~/.cloudflared/config.yml           # Cloudflare
/etc/cloudflared/config.yml         # Cloudflare (system)
/var/lib/docker/volumes/            # Docker volumes
```

---

## 🆘 Help

```bash
# Dokumentacja
cat trading-bot/deployment/START_TUTAJ.md
cat trading-bot/deployment/OPCJE_DEPLOYMENT.md

# Status wszystkiego
docker-compose ps
sudo systemctl status cloudflared
sudo systemctl status docker

# Sprawdź porty
sudo netstat -tulpn | grep -E ':(8000|8080|8443)'
```

---

## ✅ Checklist

- [ ] Docker zainstalowany i działa
- [ ] n8n działa na 8443
- [ ] .env wypełniony (TELEGRAM, OPENAI, API_KEY)
- [ ] `install.sh` wykonany pomyślnie
- [ ] `docker-compose ps` - wszystkie UP
- [ ] `curl localhost:8000/health` - działa
- [ ] Dashboard otwiera się w przeglądarce
- [ ] Telegram test przeszedł (dostałeś wiadomość)
- [ ] AI analysis działa (GPT odpowiada)

---

## 🚀 Gotowe!

**Dashboard:** https://trading.twojadomena-n8n.pl (opcja 1)  
**lub:** https://twojadomena-n8n.pl/trading (opcja 2)

**n8n:** https://twojadomena-n8n.pl (działa bez zmian)

**Szczęśliwego tradingu! 📈🤖**
