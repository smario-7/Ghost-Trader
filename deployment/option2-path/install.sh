#!/bin/bash

# ============================================
# Trading Bot Deployment - Opcja 2 (Path)
# Ubuntu / Debian / Raspberry Pi
# ============================================

set -e  # Exit on error

echo "=========================================="
echo "Trading Bot Installation - Path Mode"
echo "=========================================="
echo ""
echo "System: $(uname -s) $(uname -m)"
echo "Dashboard będzie dostępny na: https://twojadomena-n8n.pl/trading"
echo "API będzie dostępne na: https://twojadomena-n8n.pl/api"
echo "n8n pozostaje na: https://twojadomena-n8n.pl/"
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

# Kopiuj nowy docker-compose.yml
echo "🐳 Instalowanie nowego docker-compose.yml..."
if [ -f "trading-bot/deployment/option2-path/docker-compose.yml" ]; then
    cp trading-bot/deployment/option2-path/docker-compose.yml docker-compose.yml
    echo "✅ Skopiowano nowy docker-compose.yml"
else
    echo "❌ BŁĄD: Nie znaleziono trading-bot/deployment/option2-path/docker-compose.yml"
    exit 1
fi

# Kopiuj nginx.conf
echo "⚙️ Instalowanie nginx.conf..."
if [ -f "trading-bot/deployment/option2-path/nginx.conf" ]; then
    cp trading-bot/deployment/option2-path/nginx.conf nginx.conf
    echo "✅ Skopiowano nginx.conf"
else
    echo "❌ BŁĄD: Nie znaleziono trading-bot/deployment/option2-path/nginx.conf"
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
echo "ℹ️  Cloudflare Configuration"
echo "=========================================="
echo ""
echo "W tej opcji NIE MUSISZ zmieniać Cloudflare config!"
echo ""
echo "Cloudflare nadal kieruje tylko na:"
echo "  twojadomena-n8n.pl → localhost:8443"
echo ""
echo "Nginx wewnętrznie routuje:"
echo "  /         → n8n"
echo "  /trading  → Trading Dashboard"
echo "  /api      → Trading API"
echo ""

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

# Test lokalnie (wewnątrz sieci docker)
if docker-compose exec -T trading-bot-backend curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Trading Bot Backend: OK"
else
    echo "❌ Trading Bot Backend: FAIL"
fi

# Test przez nginx
if curl -f http://localhost:8443/trading > /dev/null 2>&1; then
    echo "✅ Nginx → Trading Frontend: OK"
else
    echo "❌ Nginx → Trading Frontend: FAIL"
fi

if curl -f http://localhost:8443/api/health > /dev/null 2>&1; then
    echo "✅ Nginx → Trading API: OK"
else
    echo "❌ Nginx → Trading API: FAIL"
fi

if curl -f http://localhost:8443 > /dev/null 2>&1; then
    echo "✅ Nginx → n8n: OK"
else
    echo "❌ Nginx → n8n: FAIL"
fi

# Podsumowanie
echo ""
echo "=========================================="
echo "✅ INSTALACJA ZAKOŃCZONA!"
echo "=========================================="
echo ""
echo "📍 Dostęp (lokalnie):"
echo "  n8n:            http://localhost:8443/"
echo "  Trading Bot:    http://localhost:8443/trading"
echo "  Trading API:    http://localhost:8443/api"
echo ""
echo "📍 Dostęp (przez Cloudflare):"
echo "  n8n:            https://twojadomena-n8n.pl/"
echo "  Trading Bot:    https://twojadomena-n8n.pl/trading"
echo "  Trading API:    https://twojadomena-n8n.pl/api"
echo ""
echo "📝 Logi:"
echo "  docker-compose logs -f"
echo "  docker-compose logs -f nginx"
echo "  docker-compose logs -f trading-bot-backend"
echo "  tail -f trading-bot/data/logs/bot.log"
echo ""
echo "🔄 Komendy:"
echo "  Status:   docker-compose ps"
echo "  Restart:  docker-compose restart"
echo "  Stop:     docker-compose down"
echo ""
echo "✅ Gotowe!"
