.PHONY: help setup activate install update clean test test-cov lint format docker-up docker-down docker-logs

# Domyślny cel - wyświetla pomoc
help:
	@echo "Ghost-Trader - Dostępne komendy:"
	@echo ""
	@echo "  make setup       - Utwórz środowisko conda i zainstaluj zależności"
	@echo "  make activate    - Aktywuj środowisko conda"
	@echo "  make install     - Zainstaluj/zaktualizuj zależności"
	@echo "  make update      - Zaktualizuj środowisko z environment.yml"
	@echo "  make clean       - Wyczyść pliki cache i tymczasowe"
	@echo "  make test        - Uruchom testy"
	@echo "  make test-cov    - Uruchom testy z raportem pokrycia kodu"
	@echo "  make lint        - Sprawdź kod (ruff check)"
	@echo "  make format      - Sformatuj kod (ruff format)"
	@echo "  make docker-up   - Uruchom aplikację w Docker"
	@echo "  make docker-down - Zatrzymaj Docker"
	@echo "  make docker-logs - Pokaż logi Docker"
	@echo ""

# Utwórz środowisko conda
setup:
	@echo "Tworzę środowisko conda ghost-trader..."
	conda env create -f environment.yml
	@echo "✅ Środowisko utworzone!"
	@echo "Aktywuj przez: conda activate ghost-trader"

# Aktywuj środowisko (informacja)
activate:
	@echo "Aby aktywować środowisko, uruchom:"
	@echo "  source activate.sh"
	@echo "lub:"
	@echo "  conda activate ghost-trader"

# Zainstaluj zależności
install:
	@echo "Instaluję zależności..."
	pip install -r backend/requirements.txt
	@echo "✅ Zależności zainstalowane!"

# Zaktualizuj środowisko
update:
	@echo "Aktualizuję środowisko..."
	conda env update -f environment.yml --prune
	@echo "✅ Środowisko zaktualizowane!"

# Wyczyść pliki cache
clean:
	@echo "Czyszczę pliki cache..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.log" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Cache wyczyszczony!"

# Uruchom testy
test:
	@echo "Uruchamiam testy..."
	cd backend && python -m pytest tests/ -v

# Uruchom testy z raportem pokrycia kodu
test-cov:
	@echo "Uruchamiam testy z pokryciem..."
	cd backend && python -m pytest tests/ --cov=app --cov-report=term-missing -v

# Lint (wymaga: pip install ruff)
lint:
	@echo "Sprawdzam kod (ruff)..."
	cd backend && python -m ruff check app/ tests/

# Format (wymaga: pip install ruff)
format:
	@echo "Formatuję kod (ruff)..."
	cd backend && python -m ruff format app/ tests/

# Docker - uruchom
docker-up:
	@echo "Uruchamiam Docker..."
	docker-compose up -d
	@echo "✅ Docker uruchomiony!"
	@echo "Frontend: http://localhost:8080"
	@echo "Backend: http://localhost:8000"

# Docker - zatrzymaj
docker-down:
	@echo "Zatrzymuję Docker..."
	docker-compose down
	@echo "✅ Docker zatrzymany!"

# Docker - logi
docker-logs:
	docker-compose logs -f
