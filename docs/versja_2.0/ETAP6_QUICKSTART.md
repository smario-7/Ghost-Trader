# Etap 6 - Quick Start Guide

## 🚀 Szybki Start

### 1. Uruchom System
```bash
# Z katalogu głównego projektu
docker-compose up -d

# Sprawdź status
docker-compose ps
```

### 2. Otwórz Dashboard
```
http://localhost:8080
```

### 3. Nowe Funkcjonalności

#### 🤖 Panel Wyników Analiz AI
- **Lokalizacja**: Sekcja po "Aktywność Bota"
- **Funkcje**:
  - Filtrowanie po symbolu i typie sygnału
  - Wyświetlanie voting details (AI, Technical, Macro, News)
  - Kliknięcie otwiera modal z pełnymi szczegółami
  - Real-time aktualizacje przez SSE

**Jak używać:**
1. Wybierz symbol z dropdown (lub zostaw "Wszystkie symbole")
2. Wybierz typ sygnału (BUY/SELL/HOLD/NO_SIGNAL) lub zostaw "Wszystkie"
3. Kliknij na wynik aby zobaczyć szczegóły
4. W modalu przełączaj zakładki: AI | Technical | Macro | News

#### 📊 Statystyki Tokenów OpenAI
- **Lokalizacja**: Sekcja obok "Panel Wyników Analiz AI"
- **Wyświetla**:
  - Tokeny dzisiaj
  - Koszt dzisiaj ($)
  - Liczba analiz dzisiaj
  - Średnia tokenów na analizę
  - Łączne tokeny i koszt (all-time)

**Monitorowanie kosztów:**
- Sprawdzaj regularnie koszt dzisiaj
- Śledź średnią tokenów/analiza
- Dostosuj interwał analiz jeśli koszty rosną

#### ⚙️ Konfiguracja Analiz
- **Lokalizacja**: Sekcja obok "Statystyki Tokenów"
- **Ustawienia**:
  - **Interwał analiz**: 5, 15, 30, 60 minut
  - **Próg powiadomień**: 0-100% (min agreement_score)
  - **Symbole do analizy**: Multi-select z 4 grup
    - 💱 Forex (7 symboli)
    - 📈 Indeksy (4 symbole)
    - 🏢 Akcje (7 symboli)
    - 🥇 Metale (4 symbole)
  - **Automatyczne analizy**: Włącz/wyłącz

**Jak skonfigurować:**
1. Wybierz interwał analiz (np. 15 minut)
2. Ustaw próg powiadomień (np. 60% - wyślij gdy zgodność >= 60%)
3. Zaznacz symbole do analizy:
   - Kliknij "Wszystkie symbole" aby zaznaczyć wszystkie
   - Lub wybierz konkretne symbole z list
4. Włącz "Automatyczne analizy włączone"
5. Kliknij "Uruchom analizę ręcznie" aby przetestować

## 🎯 Przykładowe Scenariusze

### Scenariusz 1: Podstawowa Konfiguracja
```
Interwał: 15 minut
Próg: 60%
Symbole: EUR/USD, GBP/USD, USD/JPY (główne pary forex)
Automatyczne: TAK
```

**Rezultat**: Analizy co 15 minut dla 3 par, powiadomienia gdy zgodność >= 60%

### Scenariusz 2: Oszczędna Konfiguracja (niskie koszty)
```
Interwał: 60 minut
Próg: 75%
Symbole: EUR/USD, XAU/USD (tylko 2 symbole)
Automatyczne: TAK
```

**Rezultat**: Mniej analiz = niższe koszty, tylko silne sygnały (75%+)

### Scenariusz 3: Agresywna Konfiguracja (więcej sygnałów)
```
Interwał: 5 minut
Próg: 50%
Symbole: Wszystkie (22 symbole)
Automatyczne: TAK
```

**Rezultat**: Maksymalna liczba analiz i sygnałów, wysokie koszty OpenAI

## 📊 Interpretacja Wyników

### Agreement Score (Zgodność)
- **75-100%** 🟢 Wysoka zgodność - silny sygnał
- **50-74%** 🟡 Średnia zgodność - umiarkowany sygnał
- **0-49%** 🔴 Niska zgodność - słaby sygnał

### Voting Details
Każda analiza pokazuje głosy z 4 źródeł:
- **AI**: Rekomendacja z OpenAI GPT (confidence 0-100%)
- **Technical**: Wskaźniki techniczne (RSI, MACD, MA, Bollinger)
- **Macro**: Dane makroekonomiczne (Fed, inflacja, PKB)
- **News**: Sentiment z wiadomości finansowych

**Przykład:**
```
AI: BUY (80%)
Technical: BUY (75%)
Macro: HOLD (50%)
News: BUY (70%)

Final Signal: BUY (75% zgodności)
Uzasadnienie: 3 z 4 źródeł wskazuje BUY
```

## 🔍 Monitorowanie

### Real-time Updates (SSE)
Dashboard automatycznie odbiera aktualizacje:
- ✅ Nowe analizy pojawiają się natychmiast
- ✅ Statystyki tokenów aktualizują się na bieżąco
- ✅ Zmiany konfiguracji synchronizują się

**Sprawdzenie połączenia:**
1. Otwórz DevTools (F12)
2. Przejdź do zakładki Console
3. Szukaj: "SSE connection established"

### Logi Backend
```bash
# Sprawdź logi w czasie rzeczywistym
docker-compose logs -f backend

# Szukaj analiz AI
docker-compose logs backend | grep "AI analysis"

# Szukaj błędów
docker-compose logs backend | grep "ERROR"
```

## 🛠️ Rozwiązywanie Problemów

### Problem: Brak wyników analiz
**Rozwiązanie:**
1. Sprawdź czy automatyczne analizy są włączone
2. Sprawdź czy wybrano symbole do analizy
3. Uruchom analizę ręcznie: "Uruchom analizę ręcznie"
4. Sprawdź logi: `docker-compose logs backend`

### Problem: SSE nie działa
**Rozwiązanie:**
1. Odśwież stronę (F5)
2. Sprawdź Console w DevTools
3. Sprawdź czy backend działa: `docker-compose ps`
4. Restart backendu: `docker-compose restart backend`

### Problem: Wysokie koszty OpenAI
**Rozwiązanie:**
1. Zwiększ interwał analiz (np. z 15 do 60 minut)
2. Zmniejsz liczbę symboli (wybierz tylko najważniejsze)
3. Podnieś próg powiadomień (np. z 60% do 75%)
4. Monitoruj koszty w sekcji "Statystyki OpenAI"

### Problem: Modal nie otwiera się
**Rozwiązanie:**
1. Sprawdź Console w DevTools
2. Sprawdź czy API Key jest poprawny
3. Sprawdź czy backend odpowiada: `curl http://localhost:8000/health`

## 📈 Optymalizacja Kosztów

### Szacowane Koszty (GPT-4o)
```
1 analiza ≈ 2500 tokenów ≈ $0.025

Scenariusze miesięczne:
- 1 symbol, 60min: ~720 analiz = ~$18/miesiąc
- 5 symboli, 15min: ~14,400 analiz = ~$360/miesiąc
- 22 symbole, 5min: ~190,080 analiz = ~$4,752/miesiąc
```

### Rekomendacje:
1. **Start**: 3-5 symboli, 15min interwał
2. **Monitoruj**: Sprawdzaj "Koszt dzisiaj" codziennie
3. **Dostosuj**: Zwiększ interwał jeśli koszty rosną
4. **Alternatywa**: Użyj GPT-4o-mini (10x taniej)

## 🎓 Najlepsze Praktyki

### Konfiguracja
- ✅ Zacznij od małej liczby symboli (3-5)
- ✅ Użyj interwału 15-30 minut
- ✅ Ustaw próg 60-70% dla balansowanych sygnałów
- ✅ Monitoruj koszty przez pierwsze dni

### Analiza Wyników
- ✅ Sprawdzaj voting details przed działaniem
- ✅ Czytaj AI reasoning w modalu
- ✅ Porównuj z technical indicators
- ✅ Śledź agreement score w czasie

### Bezpieczeństwo
- ✅ Nie inwestuj tylko na podstawie AI
- ✅ Zawsze przeprowadzaj własną analizę
- ✅ Używaj stop loss i take profit
- ✅ Zarządzaj ryzykiem (max 2-3% kapitału na trade)

## 📞 Wsparcie

### Dokumentacja
- `ETAP6_SUMMARY.md` - Pełna dokumentacja techniczna
- `CLAUDE.md` - Przegląd projektu
- `README.md` - Główny README projektu

### Logi
```bash
# Backend
docker-compose logs -f backend

# Scheduler
docker-compose logs -f scheduler

# Wszystkie serwisy
docker-compose logs -f
```

### Testy
```bash
# Test bazy danych
cd backend && python3 test_etap6_integration.py

# Test składni Python
python3 -m py_compile backend/app/main.py
```

---

**Powodzenia z Etapem 6!** 🚀

Jeśli masz pytania lub problemy, sprawdź `ETAP6_SUMMARY.md` lub logi backendu.
