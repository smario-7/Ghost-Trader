#!/bin/bash

# ============================================
# Trading Bot Deployment - Opcja 1 (Subdomain)
# Ubuntu / Debian / Raspberry Pi
# ============================================

set -e  # Exit on error

echo "=========================================="
echo "Trading Bot Installation - Subdomain Mode"
echo "=========================================="
echo ""
echo "System: $(uname -s) $(uname -m)"
echo "Dashboard będzie dostępny na: https://trading.twojadomena-n8n.pl"
echo "API będzie dostępne na: https://api.twojadomena-n8n.pl"
echo ""

# Sprawdź czy jesteś w katalogu n8n
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ BŁĄD: Nie znaleziono docker-compose.yml"
    echo "Uruchom ten skrypt z katalogu ~/n8n/"
    exit 1
fi

# Backup istniejącego docker-compose.yml
echo "📦 Backup istniejącego docker-compose.yml..."
cp docker-compose.yml docker-compose.yml.backup.$(date +%Y%m%d_%H%M%S)

# Sprawdź czy katalog trading-bot istnieje
if [ ! -d "trading-bot" ]; then
    echo "❌ BŁĄD: Katalog trading-bot/ nie istnieje"
    echo "Proszę rozpakować archiwum trading-bot-openai.tar.gz"
    exit 1
fi

# Sprawdź czy .env istnieje
if [ ! -f "trading-bot/.env" ]; then
    echo "⚙️ Tworzenie pliku .env..."
    
    if [ -f "trading-bot/.env.example" ]; then
        cp trading-bot/.env.example trading-bot/.env
        echo "✅ Skopiowano .env.example do .env"
        echo ""
        echo "⚠️  WAŻNE: Teraz musisz wypełnić trading-bot/.env!"
        echo ""
        echo "Wymagane dane:"
        echo "  - TELEGRAM_BOT_TOKEN (z @BotFather)"
        echo "  - TELEGRAM_CHAT_ID (z getUpdates)"
        echo "  - OPENAI_API_KEY (z platform.openai.com)"
        echo "  - API_KEY (wygeneruj: openssl rand -hex 32)"
        echo ""
        read -p "Czy chcesz edytować .env teraz? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            nano trading-bot/.env
        else
            echo "⚠️  Pamiętaj aby wypełnić trading-bot/.env przed uruchomieniem!"
            exit 0
        fi
    else
        echo "❌ BŁĄD: Nie znaleziono trading-bot/.env.example"
        exit 1
    fi
fi

# Sprawdź katalogi data
echo "📁 Tworzenie katalogów data..."
mkdir -p trading-bot/data/logs
mkdir -p trading-bot/data/backups
chmod -R 755 trading-bot/data

# Backup Cloudflare config
echo "☁️ Backup Cloudflare config..."
cp ~/.cloudflared/config.yml ~/.cloudflared/config.yml.backup.$(date +%Y%m%d_%H%M%S)

# Kopiuj nowy docker-compose.yml
echo "🐳 Instalowanie nowego docker-compose.yml..."
# Zakładam że masz nowy plik w trading-bot/deployment/
if [ -f "trading-bot/deployment/option1-subdomain/docker-compose.yml" ]; then
    cp trading-bot/deployment/option1-subdomain/docker-compose.yml docker-compose.yml
    echo "✅ Skopiowano nowy docker-compose.yml"
else
    echo "❌ BŁĄD: Nie znaleziono trading-bot/deployment/option1-subdomain/docker-compose.yml"
    exit 1
fi

# Walidacja docker-compose
echo "✅ Walidacja docker-compose..."
docker-compose config > /dev/null
if [ $? -eq 0 ]; then
    echo "✅ docker-compose.yml jest poprawny"
else
    echo "❌ BŁĄD w docker-compose.yml"
    exit 1
fi

# Informacja o Cloudflare
echo ""
echo "=========================================="
echo "⚠️  WAŻNE - Cloudflare Configuration"
echo "=========================================="
echo ""
echo "Musisz zaktualizować ~/.cloudflared/config.yml:"
echo ""
echo "1. Backup został stworzony automatycznie"
echo "2. Edytuj plik:"
echo "   nano ~/.cloudflared/config.yml"
echo ""
echo "3. Dodaj nowe hostnamy:"
echo ""
cat << 'EOF'
ingress:
  - hostname: twojadomena-n8n.pl
    service: http://localhost:8443
  - hostname: trading.twojadomena-n8n.pl
    service: http://localhost:8080
  - hostname: api.twojadomena-n8n.pl
    service: http://localhost:8000
  - service: http_status:404
EOF
echo ""
echo "4. Następnie w Cloudflare Dashboard:"
echo "   - Zero Trust → Tunnels → Twój tunnel"
echo "   - Public Hostnames → Add public hostname"
echo "   - Dodaj: trading.twojadomena-n8n.pl → localhost:8080"
echo "   - Dodaj: api.twojadomena-n8n.pl → localhost:8000"
echo ""
read -p "Czy zaktualizowałeś Cloudflare config? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "⚠️  Pamiętaj aby zaktualizować przed restartem!"
fi

# Zatrzymaj istniejące kontenery
echo ""
echo "🛑 Zatrzymywanie istniejących kontenerów..."
docker-compose down

# Build
echo "🔨 Building kontenerów (może zająć 5-10 min)..."
docker-compose build

# Start
echo "🚀 Uruchamianie wszystkich serwisów..."
docker-compose up -d

# Sprawdź status
echo ""
echo "⏳ Czekam 10s na start kontenerów..."
sleep 10

echo ""
echo "📊 Status kontenerów:"
docker-compose ps

# Test health
echo ""
echo "🏥 Test health checks..."
sleep 5

if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Trading Bot Backend: OK"
else
    echo "❌ Trading Bot Backend: FAIL"
fi

if curl -f http://localhost:8080 > /dev/null 2>&1; then
    echo "✅ Trading Bot Frontend: OK"
else
    echo "❌ Trading Bot Frontend: FAIL"
fi

if curl -f http://localhost:8443 > /dev/null 2>&1; then
    echo "✅ n8n: OK"
else
    echo "❌ n8n: FAIL"
fi

# Restart Cloudflare
echo ""
read -p "Czy zrestartować Cloudflare Tunnel? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🔄 Restart Cloudflare Tunnel..."
    sudo cp ~/.cloudflared/config.yml /etc/cloudflared/config.yml
    sudo systemctl restart cloudflared
    sleep 3
    sudo systemctl status cloudflared --no-pager
fi

# Podsumowanie
echo ""
echo "=========================================="
echo "✅ INSTALACJA ZAKOŃCZONA!"
echo "=========================================="
echo ""
echo "📍 Dostęp:"
echo "  n8n:            https://twojadomena-n8n.pl"
echo "  Trading Bot:    https://trading.twojadomena-n8n.pl"
echo "  Trading API:    https://api.twojadomena-n8n.pl"
echo ""
echo "📝 Logi:"
echo "  docker-compose logs -f"
echo "  docker-compose logs -f trading-bot-backend"
echo "  tail -f trading-bot/data/logs/bot.log"
echo ""
echo "🔄 Komendy:"
echo "  Status:   docker-compose ps"
echo "  Restart:  docker-compose restart"
echo "  Stop:     docker-compose down"
echo ""
echo "✅ Gotowe!"
