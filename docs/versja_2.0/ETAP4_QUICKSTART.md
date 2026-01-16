# Etap 4: Szybki Start

## 🚀 Uruchomienie w 5 krokach

### Krok 1: Zainstaluj zależności

```bash
cd backend
pip install -r requirements.txt
```

### Krok 2: Zaktualizuj .env

Dodaj do pliku `.env` (lub skopiuj z `.env.example`):

```env
# Automatyczne analizy AI (Etap 4)
ANALYSIS_INTERVAL=30
ANALYSIS_ENABLED=true
ANALYSIS_SYMBOLS_LIMIT=10
ANALYSIS_TIMEOUT=60
ANALYSIS_PAUSE_BETWEEN_SYMBOLS=2

# Użyj gpt-4o-mini dla oszczędności (10x taniej)
OPENAI_MODEL=gpt-4o-mini
```

### Krok 3: Uruchom scheduler

```bash
cd backend
python -m app.scheduler
```

### Krok 4: Sprawdź logi

```bash
tail -f backend/data/logs/scheduler.log
```

Powinieneś zobaczyć:
```
[INFO] 🤖 Auto AI analysis scheduled (every 30 minutes)
[INFO] ⏰ Starting auto AI analysis cycle... (po 30 minutach)
```

### Krok 5: Test (opcjonalnie)

Jeśli nie chcesz czekać 30 minut, uruchom test:

```bash
cd backend
python test_etap4_integration.py
```

## ✅ Gotowe!

System automatycznie:
- ✅ Uruchamia analizy AI co 30 minut
- ✅ Analizuje 10 symboli (EUR/USD, GBP/USD, etc.)
- ✅ Zapisuje wyniki do bazy danych
- ✅ Wysyła powiadomienia Telegram dla sygnałów >= 60%
- ✅ Monitoruje tokeny i koszty OpenAI

## 💰 Szacowane koszty

**Z gpt-4o-mini** (rekomendowane):
- ~$32/miesiąc (10 symboli, co 30 min)
- ~$8/miesiąc (5 symboli, co 1h)

**Z gpt-4o** (droższe):
- ~$324/miesiąc (10 symboli, co 30 min)

## 📊 Sprawdź wyniki

### W bazie danych

```bash
sqlite3 backend/data/trading_bot.db "
SELECT symbol, final_signal, agreement_score, timestamp 
FROM ai_analysis_results 
ORDER BY timestamp DESC 
LIMIT 10;
"
```

### W logach

```bash
grep "Auto analysis completed" backend/data/logs/scheduler.log
```

## ⚙️ Konfiguracja

### Zmień interwał na 1 godzinę

W `.env`:
```env
ANALYSIS_INTERVAL=60
```

### Ogranicz do 5 symboli

W `.env`:
```env
ANALYSIS_SYMBOLS_LIMIT=5
```

### Wyłącz automatyczne analizy

W `.env`:
```env
ANALYSIS_ENABLED=false
```

## 🆘 Problemy?

### Analizy nie uruchamiają się
- Sprawdź `ANALYSIS_ENABLED=true` w `.env`
- Sprawdź logi: `tail -f backend/data/logs/scheduler.log`

### Wysokie koszty
- Zmień na `gpt-4o-mini` w `.env`
- Ogranicz liczbę symboli (5-10)
- Zwiększ interwał (60 min)

### Timeout
- Zwiększ `ANALYSIS_TIMEOUT=90` w `.env`

## 📚 Więcej informacji

- **Pełna dokumentacja**: `backend/ETAP4_README.md`
- **Podsumowanie**: `ETAP4_SUMMARY.md`
- **Test**: `backend/test_etap4_integration.py`
