#!/bin/bash
# Skrypt do aktywacji środowiska conda ghost-trader

# Sprawdź czy conda jest zainstalowana
if ! command -v conda &> /dev/null; then
    echo "❌ Conda nie jest zainstalowana!"
    echo "Zainstaluj Miniconda lub Anaconda: https://docs.conda.io/en/latest/miniconda.html"
    exit 1
fi

# Inicjalizacja conda dla basha
eval "$(conda shell.bash hook)"

# Sprawdź czy środowisko ghost-trader istnieje
if ! conda env list | grep -q "ghost-trader"; then
    echo "⚠️  Środowisko 'ghost-trader' nie istnieje!"
    echo "Tworzę środowisko z pliku environment.yml..."
    conda env create -f environment.yml
    if [ $? -ne 0 ]; then
        echo "❌ Nie udało się utworzyć środowiska!"
        exit 1
    fi
fi

# Aktywacja środowiska
conda activate ghost-trader

if [ $? -eq 0 ]; then
    echo "✅ Środowisko conda 'ghost-trader' zostało aktywowane"
    echo "Python: $(which python)"
    echo "Wersja: $(python --version)"
    echo ""
    echo "💡 Aby automatycznie aktywować środowisko przy wejściu do katalogu:"
    echo "   1. Zainstaluj direnv: sudo apt install direnv (Linux) lub brew install direnv (Mac)"
    echo "   2. Dodaj do ~/.bashrc: eval \"\$(direnv hook bash)\""
    echo "   3. W katalogu projektu: direnv allow"
else
    echo "❌ Nie udało się aktywować środowiska!"
    exit 1
fi
