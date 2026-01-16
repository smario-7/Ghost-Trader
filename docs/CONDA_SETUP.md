# Konfiguracja środowiska Conda dla Ghost-Trader

Ten projekt używa środowiska conda o nazwie `ghost-trader` z Pythonem 3.11.13.

## Automatyczna aktywacja środowiska

Projekt jest skonfigurowany do automatycznej aktywacji środowiska conda na kilka sposobów:

### 1. Używając skryptu activate.sh

```bash
source activate.sh
```

Skrypt automatycznie:
- Sprawdzi czy conda jest zainstalowana
- Sprawdzi czy środowisko ghost-trader istnieje
- Utworzy środowisko jeśli nie istnieje (z pliku environment.yml)
- Aktywuje środowisko

### 2. Używając direnv (zalecane dla automatyzacji)

Plik `.envrc` automatycznie aktywuje środowisko przy wejściu do katalogu projektu.

**Instalacja direnv:**

Ubuntu/Debian:
```bash
sudo apt install direnv
echo 'eval "$(direnv hook bash)"' >> ~/.bashrc
source ~/.bashrc
```

macOS:
```bash
brew install direnv
echo 'eval "$(direnv hook bash)"' >> ~/.bashrc
source ~/.bashrc
```

**Aktywacja w projekcie:**
```bash
cd /home/mario/workspace/Ghost-Trader
direnv allow
```

Od teraz środowisko będzie aktywowane automatycznie przy wejściu do katalogu!

### 3. VS Code / Cursor IDE

Plik `.vscode/settings.json` jest skonfigurowany aby:
- Używać interpretera Python ze środowiska ghost-trader
- Automatycznie aktywować środowisko w terminalu
- Ustawić odpowiednie ścieżki dla autouzupełniania

## Ręczne zarządzanie środowiskiem

### Utworzenie środowiska z pliku environment.yml

```bash
conda env create -f environment.yml
```

### Aktywacja środowiska

```bash
conda activate ghost-trader
```

### Deaktywacja środowiska

```bash
conda deactivate
```

### Aktualizacja środowiska

```bash
conda env update -f environment.yml --prune
```

### Usunięcie środowiska

```bash
conda env remove -n ghost-trader
```

## Dodawanie nowych pakietów

### Przez pip (zalecane dla pakietów Python)

```bash
conda activate ghost-trader
pip install nazwa-pakietu
pip freeze > backend/requirements.txt
```

### Przez conda

```bash
conda activate ghost-trader
conda install nazwa-pakietu
conda env export > environment.yml
```

## Eksport środowiska

### Dla innych użytkowników (z wersjami)

```bash
conda env export > environment.yml
```

### Bez wersji (bardziej elastyczne)

```bash
conda env export --from-history > environment.yml
```

## Weryfikacja konfiguracji

Sprawdź czy wszystko działa poprawnie:

```bash
# Sprawdź aktywne środowisko
conda info --envs

# Sprawdź wersję Pythona
python --version

# Sprawdź ścieżkę do Pythona
which python

# Sprawdź zainstalowane pakiety
pip list
```

Powinieneś zobaczyć:
- Python 3.11.13
- Ścieżka: `/home/mario/miniconda3/envs/ghost-trader/bin/python`
- Wszystkie pakiety z requirements.txt

## Rozwiązywanie problemów

### Środowisko nie aktywuje się automatycznie

1. Sprawdź czy direnv jest zainstalowany: `which direnv`
2. Sprawdź czy hook jest w .bashrc: `grep direnv ~/.bashrc`
3. Zezwól na .envrc: `direnv allow`

### Python nie jest znaleziony

```bash
conda activate ghost-trader
which python
```

Jeśli zwraca błąd, przeinstaluj środowisko:
```bash
conda env remove -n ghost-trader
conda env create -f environment.yml
```

### Pakiety nie są zainstalowane

```bash
conda activate ghost-trader
pip install -r backend/requirements.txt
```

## Pliki konfiguracyjne

Projekt zawiera następujące pliki konfiguracyjne dla środowiska:

- `.envrc` - Automatyczna aktywacja przez direnv
- `.vscode/settings.json` - Konfiguracja VS Code/Cursor
- `.python-version` - Wersja Pythona dla narzędzi
- `environment.yml` - Definicja środowiska conda
- `activate.sh` - Skrypt aktywacji
- `.editorconfig` - Ustawienia edytora
- `.gitattributes` - Normalizacja plików w git

## Dodatkowe informacje

- Środowisko używa Python 3.11.13
- Wszystkie zależności są w `backend/requirements.txt`
- Środowisko jest izolowane od systemowego Pythona
- Conda zarządza zarówno Pythonem jak i pakietami
