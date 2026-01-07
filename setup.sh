#!/bin/bash

# Trading Bot Setup Script
# Automatyczny setup aplikacji

set -e

echo "============================================"
echo "🤖 TRADING BOT - AUTOMATIC SETUP"
echo "============================================"
echo ""

# Kolory
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Funkcje
print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${YELLOW}ℹ${NC} $1"
}

# Sprawdź wymagania
check_requirements() {
    echo "Sprawdzam wymagania..."
    
    # Docker
    if command -v docker &> /dev/null; then
        print_success "Docker zainstalowany"
    else
        print_error "Docker nie jest zainstalowany!"
        echo "Zainstaluj Docker: https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    # Docker Compose
    if command -v docker-compose &> /dev/null; then
        print_success "Docker Compose zainstalowany"
    else
        print_error "Docker Compose nie jest zainstalowany!"
        echo "Zainstaluj Docker Compose: https://docs.docker.com/compose/install/"
        exit 1
    fi
    
    echo ""
}

# Konfiguracja .env
setup_env() {
    echo "Konfiguracja zmiennych środowiskowych..."
    
    if [ -f .env ]; then
        print_info ".env już istnieje"
        read -p "Czy nadpisać? (t/N): " overwrite
        if [[ ! $overwrite =~ ^[Tt]$ ]]; then
            print_info "Pomijam konfigurację .env"
            return
        fi
    fi
    
    cp .env.example .env
    print_success "Skopiowano .env.example → .env"
    
    echo ""
    echo "============================================"
    echo "KONFIGURACJA TELEGRAM BOT"
    echo "============================================"
    echo ""
    echo "1. Otwórz Telegram i znajdź @BotFather"
    echo "2. Wyślij: /newbot"
    echo "3. Podaj nazwę i username bota"
    echo "4. Zapisz otrzymany TOKEN"
    echo ""
    
    read -p "Telegram Bot Token: " bot_token
    
    echo ""
    echo "5. Wyślij wiadomość do swojego bota"
    echo "6. Otwórz: https://api.telegram.org/bot<TOKEN>/getUpdates"
    echo "7. Znajdź 'chat':{'id': YOUR_ID}"
    echo ""
    
    read -p "Telegram Chat ID: " chat_id
    
    echo ""
    print_info "Generuję API Key..."
    api_key=$(openssl rand -hex 32)
    print_success "API Key wygenerowany"
    
    # Zapisz do .env
    sed -i.bak "s|TELEGRAM_BOT_TOKEN=.*|TELEGRAM_BOT_TOKEN=$bot_token|" .env
    sed -i.bak "s|TELEGRAM_CHAT_ID=.*|TELEGRAM_CHAT_ID=$chat_id|" .env
    sed -i.bak "s|API_KEY=.*|API_KEY=$api_key|" .env
    rm .env.bak 2>/dev/null || true
    
    print_success "Konfiguracja zapisana w .env"
    echo ""
    echo "API Key: $api_key"
    echo "ZAPISZ TEN KLUCZ! Będzie potrzebny do wywołań API."
    echo ""
}

# Utwórz katalogi
create_directories() {
    echo "Tworzenie katalogów..."
    
    mkdir -p data/logs
    mkdir -p data/backups
    
    print_success "Katalogi utworzone"
    echo ""
}

# Build i uruchomienie
start_services() {
    echo "Uruchamiam usługi..."
    
    docker-compose build
    print_success "Obrazy zbudowane"
    
    docker-compose up -d
    print_success "Usługi uruchomione"
    
    echo ""
    echo "Czekam na inicjalizację (10s)..."
    sleep 10
}

# Health check
check_health() {
    echo ""
    echo "Sprawdzam stan systemu..."
    
    if curl -s http://localhost:8000/health > /dev/null; then
        print_success "Backend działa (http://localhost:8000)"
    else
        print_error "Backend nie odpowiada"
        echo "Sprawdź logi: docker-compose logs backend"
        return 1
    fi
    
    if curl -s http://localhost:8080 > /dev/null; then
        print_success "Frontend działa (http://localhost:8080)"
    else
        print_error "Frontend nie odpowiada"
    fi
    
    echo ""
}

# Podsumowanie
show_summary() {
    echo "============================================"
    echo "✅ SETUP ZAKOŃCZONY POMYŚLNIE!"
    echo "============================================"
    echo ""
    echo "📡 URLs:"
    echo "  - Frontend: http://localhost:8080"
    echo "  - Backend API: http://localhost:8000"
    echo "  - API Docs: http://localhost:8000/docs"
    echo "  - Health Check: http://localhost:8000/health"
    echo ""
    echo "🔑 API Key (zapisz!): $(grep API_KEY .env | cut -d= -f2)"
    echo ""
    echo "📊 Sprawdź logi:"
    echo "  docker-compose logs -f"
    echo ""
    echo "🚀 Kolejne kroki:"
    echo "  1. Otwórz http://localhost:8080"
    echo "  2. Przeczytaj README.md"
    echo "  3. Utwórz pierwszą strategię"
    echo "  4. Sprawdź powiadomienia na Telegramie"
    echo ""
    echo "📚 Dokumentacja:"
    echo "  - README.md - Pełna dokumentacja"
    echo "  - docs/QUICKSTART.md - Quick start guide"
    echo "  - docs/SECURITY.md - Bezpieczeństwo"
    echo ""
}

# Główny flow
main() {
    check_requirements
    setup_env
    create_directories
    start_services
    check_health
    show_summary
}

# Uruchom
main

echo "Gotowe! 🎉"
