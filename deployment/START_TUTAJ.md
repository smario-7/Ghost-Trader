# 🚀 START TUTAJ - Trading Bot Deployment (Ubuntu)

## 📖 Co masz?

Otrzymałeś **Trading Bot z OpenAI GPT** do integracji z Twoim n8n na **Ubuntu Server**.

---

## 📋 Wymagania (Ubuntu)

### System:
- Ubuntu 20.04 / 22.04 / 24.04 LTS
- 2GB RAM (minimum), 4GB+ zalecane
- 10GB wolnego miejsca
- Dostęp sudo

### Oprogramowanie:
```bash
# Sprawdź czy masz:
docker --version          # Docker 20.10+
docker-compose --version  # Docker Compose 2.0+
curl --version           # curl
nano --version           # nano lub vim

# Jeśli brakuje, zainstaluj:
# Docker + Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
# Wyloguj się i zaloguj ponownie

# curl i nano (jeśli brakuje)
sudo apt update
sudo apt install -y curl nano
```

---

## ⚡ SZYBKI START (5 minut)

### 1. Wybierz opcję deployment

Masz **2 opcje** (przeczytaj `OPCJE_DEPLOYMENT.md` dla szczegółów):

**🔵 OPCJA 1: Subdomain** (ZALECANE)
- Dashboard: `https://trading.twojadomena-n8n.pl`
- Wymaga dodania DNS w Cloudflare

**🟢 OPCJA 2: Path** (PROSTSZE)
- Dashboard: `https://twojadomena-n8n.pl/trading`
- Bez zmian w Cloudflare DNS

### 2. Przygotuj dane

Potrzebujesz:
- ✅ **OpenAI API Key** → https://platform.openai.com/api-keys
- ✅ **Telegram Bot Token** → @BotFather w Telegram
- ✅ **Telegram Chat ID** → Wyślij wiadomość do bota, potem sprawdź getUpdates

### 3. Instalacja na Ubuntu

```bash
# 1. SSH do Ubuntu Server
ssh twoja_nazwa@ubuntu-server
# lub
ssh twoja_nazwa@IP_ADRES

# 2. Przejdź do katalogu n8n (dostosuj ścieżkę!)
cd ~/n8n
# lub
cd /opt/n8n
# lub
cd /home/twoja_nazwa/n8n

# 3. Rozpakuj trading bot
tar -xzf trading-bot-n8n-integrated.tar.gz

# 4. Utwórz .env
cd trading-bot
cp .env.example .env

# 5. Edytuj .env (nano lub vim)
nano .env
# Wklej swoje dane:
# - TELEGRAM_BOT_TOKEN
# - TELEGRAM_CHAT_ID
# - OPENAI_API_KEY
# - API_KEY (wygeneruj: openssl rand -hex 32)
# Zapisz: Ctrl+O, Enter, Wyjdź: Ctrl+X

cd ..

# 6. Uruchom instalator
# DLA OPCJI 1 (subdomain):
chmod +x trading-bot/deployment/option1-subdomain/install.sh
./trading-bot/deployment/option1-subdomain/install.sh

# LUB DLA OPCJI 2 (path):
chmod +x trading-bot/deployment/option2-path/install.sh
./trading-bot/deployment/option2-path/install.sh

# 7. Gotowe! 🎉
```

### 4. Test

```bash
# Sprawdź status
docker-compose ps

# Powinieneś widzieć:
# - postgres (running)
# - n8n (running)
# - trading-bot-backend (running, healthy)
# - trading-bot-scheduler (running)
# - trading-bot-frontend (running)

# Test Telegram
export API_KEY="<twój_key_z_env>"
curl -X POST http://localhost:8000/test-telegram \
  -H "X-API-Key: $API_KEY"

# Powinieneś dostać wiadomość na Telegram!

# Test AI analysis
curl -X POST http://localhost:8000/ai/analyze \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"symbol": "BTC/USDT", "timeframe": "1h"}'

# Otwórz dashboard w przeglądarce:
# OPCJA 1: https://trading.twojadomena-n8n.pl
# OPCJA 2: https://twojadomena-n8n.pl/trading
```

---

## 🐧 Ubuntu-Specific Tips

### Firewall (UFW)
```bash
# Jeśli używasz UFW:
sudo ufw allow 8000/tcp   # Trading Bot API
sudo ufw allow 8080/tcp   # Trading Bot Frontend
sudo ufw allow 8443/tcp   # n8n (jeśli już nie masz)
sudo ufw status
```

### Docker bez sudo
```bash
# Jeśli dostajesz błąd "permission denied":
sudo usermod -aG docker $USER
newgrp docker
# lub wyloguj się i zaloguj ponownie
```

### Systemd service (opcjonalnie)
```bash
# Automatyczny start przy reboot
cd ~/n8n
sudo nano /etc/systemd/system/trading-bot.service

# Wklej (dostosuj ścieżki!):
[Unit]
Description=Trading Bot with n8n
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

# Aktywuj:
sudo systemctl enable trading-bot
sudo systemctl start trading-bot
sudo systemctl status trading-bot
```

### Logi systemowe
```bash
# Logi dockera
sudo journalctl -u docker -f

# Logi trading bot
docker-compose logs -f trading-bot-backend
docker-compose logs -f trading-bot-scheduler

# Logi w plikach
tail -f trading-bot/data/logs/bot.log
```

### Monitoring zasobów
```bash
# CPU/Memory usage
docker stats

# Dysk
df -h

# Free memory
free -h
```

---

## 📁 Struktura plików

```
deployment-files/
├── OPCJE_DEPLOYMENT.md          ← PRZECZYTAJ TO!
├── START_TUTAJ.md              ← Ten plik
├── option1-subdomain/
│   ├── docker-compose.yml      ← Zintegrowany z n8n
│   ├── cloudflared-config.yml  ← Config Cloudflare
│   └── install.sh              ← Automatyczny instalator
└── option2-path/
    ├── docker-compose.yml      ← Zintegrowany z n8n + nginx
    ├── nginx.conf              ← Reverse proxy config
    ├── cloudflared-config.yml  ← Bez zmian
    └── install.sh              ← Automatyczny instalator

trading-bot/
├── backend/                    ← Python/FastAPI
├── frontend/                   ← Dashboard HTML
├── data/                       ← Baza danych, logi, backupy
├── .env.example               ← Template konfiguracji
└── deployment/                 ← To samo co deployment-files/
```

---

## 🎯 Która opcja?

### OPCJA 1 (Subdomain) - jeśli chcesz:
- ✅ Profesjonalny setup
- ✅ Najlepszą wydajność
- ✅ Łatwe zarządzanie subdomenami
- ⏱️ 10 minut instalacji

### OPCJA 2 (Path) - jeśli chcesz:
- ✅ Najprostsze rozwiązanie
- ✅ Zero zmian w Cloudflare DNS
- ✅ Szybki test
- ⏱️ 7 minut instalacji

**Nie wiesz?** → Zacznij od **OPCJI 2** (prostsze), później możesz zmienić na 1.

---

## 📚 Pełna dokumentacja

1. **OPCJE_DEPLOYMENT.md** - Porównanie opcji ← **PRZECZYTAJ NAJPIERW**
2. **option1-subdomain/install.sh** - Automatyczny instalator (opcja 1)
3. **option2-path/install.sh** - Automatyczny instalator (opcja 2)
4. **DEPLOYMENT_GUIDE.md** - Szczegółowy manual (jeśli skrypty nie działają)
5. **PARAMETERS_VERIFICATION.md** - Weryfikacja parametrów trading
6. **FINAL_SUMMARY_OPENAI.md** - Pełne podsumowanie projektu

---

## 🆘 Problemy? (Ubuntu)

### "Port already in use"
```bash
# Sprawdź co używa portu
sudo netstat -tulpn | grep :8000
# lub
sudo lsof -i :8000

# Zatrzymaj konfliktujący proces
sudo systemctl stop <service_name>

# Lub zmień port w docker-compose.yml
nano docker-compose.yml
# ports: "8001:8000" zamiast "8000:8000"
```

### "Permission denied" (Docker)
```bash
# Dodaj użytkownika do grupy docker
sudo usermod -aG docker $USER

# Zastosuj zmiany (bez wylogowania)
newgrp docker

# Sprawdź
docker ps
# Teraz powinno działać bez sudo
```

### "Container nie startuje"
```bash
# Sprawdź logi szczegółowo
docker-compose logs trading-bot-backend

# Sprawdź czy .env jest prawidłowy
cat trading-bot/.env | grep -v '^#' | grep -v '^$'

# Rebuild od zera
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### ".env nie działa"
```bash
# Sprawdź uprawnienia
ls -la trading-bot/.env
chmod 600 trading-bot/.env

# Sprawdź format (brak spacji!)
cat trading-bot/.env | grep OPENAI_API_KEY
# Powinno być: OPENAI_API_KEY=sk-proj-xxx
# NIE: OPENAI_API_KEY = sk-proj-xxx (spacje = błąd!)

# Sprawdź czy kontenery widzą .env
docker-compose exec trading-bot-backend env | grep OPENAI
```

### "Out of memory"
```bash
# Sprawdź pamięć
free -h

# Sprawdź zużycie przez Docker
docker stats

# Jeśli brakuje RAM, zwiększ swap (Ubuntu)
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Permanent swap
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# Sprawdź
free -h
```

### "Cannot connect to Docker daemon"
```bash
# Sprawdź czy Docker działa
sudo systemctl status docker

# Uruchom Docker
sudo systemctl start docker
sudo systemctl enable docker

# Sprawdź ponownie
docker ps
```

### Cloudflare nie działa
```bash
# Sprawdź status
sudo systemctl status cloudflared

# Restart
sudo systemctl restart cloudflared

# Logi
sudo journalctl -u cloudflared -f

# Sprawdź config
cat ~/.cloudflared/config.yml
# lub
sudo cat /etc/cloudflared/config.yml
```

### "Build failed" podczas instalacji
```bash
# Zwykle brak zależności systemowych
sudo apt update
sudo apt install -y build-essential python3-dev

# Lub brak Pythona 3.11+
python3 --version
# Jeśli < 3.11, zainstaluj:
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.11 python3.11-venv
```

---

## 📍 Typowe lokalizacje (Ubuntu)

```bash
# n8n zazwyczaj w:
~/n8n                    # Home directory (standardowo)
/opt/n8n                 # Opt directory (serwery)
/srv/n8n                 # Srv directory (niektóre setup)
/home/twoja_nazwa/n8n    # Full path

# Cloudflare config:
~/.cloudflared/config.yml        # User config
/etc/cloudflared/config.yml      # System config (service)

# Docker volumes:
/var/lib/docker/volumes/         # Docker volumes

# Logi systemowe:
/var/log/syslog                  # System logs
```

---

## 🔍 Sprawdzanie instalacji (Ubuntu)

```bash
# 1. Docker działa?
docker --version
docker ps

# 2. Kontenery running?
cd ~/n8n  # lub twoja ścieżka
docker-compose ps

# 3. Porty otwarte?
sudo netstat -tulpn | grep -E ':(8000|8080|8443)'

# 4. .env jest OK?
cat trading-bot/.env | grep -E 'TELEGRAM|OPENAI|API_KEY'

# 5. Cloudflare działa?
sudo systemctl status cloudflared

# 6. Logi bez błędów?
docker-compose logs --tail=50

# 7. Test lokalny
curl http://localhost:8000/health
curl http://localhost:8080

# 8. Test przez Cloudflare
curl https://twojadomena-n8n.pl
# lub
curl https://trading.twojadomena-n8n.pl
```

---

## 📞 Co dalej?

Po instalacji:
1. Otwórz dashboard w przeglądarce
2. Sprawdź czy n8n działa (bez zmian)
3. Test Telegram notifications
4. Test AI analysis
5. Konfiguruj strategie!

---

## ✅ Checklist

- [ ] Przeczytałem `OPCJE_DEPLOYMENT.md`
- [ ] Wybrałem opcję (1 lub 2)
- [ ] Przygotowałem:
  - [ ] OpenAI API Key
  - [ ] Telegram Bot Token
  - [ ] Telegram Chat ID
- [ ] Uruchomiłem `install.sh`
- [ ] Sprawdziłem `docker-compose ps`
- [ ] Przetestowałem dashboard
- [ ] Przetestowałem Telegram
- [ ] n8n działa normalnie

---

## 🎉 Gotowe!

**Wybierz opcję → Uruchom `install.sh` → Gotowe!**

Jeśli masz pytania, sprawdź pełną dokumentację w `docs/`.

**Szczęśliwego tradingu! 🚀📈**
