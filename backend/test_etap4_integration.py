"""
Test integracji Etapu 4 - AutoAnalysisScheduler
"""
import asyncio
import sys
from pathlib import Path

# Dodaj ścieżkę do modułu app
sys.path.insert(0, str(Path(__file__).parent))

from app.utils.database import Database
from app.services.telegram_service import TelegramService
from app.services.auto_analysis_scheduler import AutoAnalysisScheduler
from app.config import get_settings


async def test_auto_scheduler():
    """Test AutoAnalysisScheduler z 2 symbolami"""
    
    print("\n" + "="*60)
    print("TEST ETAP 4: AUTO ANALYSIS SCHEDULER")
    print("="*60 + "\n")
    
    try:
        # Wczytaj konfigurację
        print("1. Wczytuję konfigurację...")
        settings = get_settings()
        print(f"   ✓ Konfiguracja wczytana: {settings.environment}")
        
        # Inicjalizuj bazę danych
        print("\n2. Inicjalizuję bazę danych...")
        db = Database(settings.database_path)
        db.initialize()
        print(f"   ✓ Baza danych: {settings.database_path}")
        
        # Inicjalizuj Telegram
        print("\n3. Inicjalizuję Telegram service...")
        telegram = TelegramService(
            bot_token=settings.telegram_bot_token,
            chat_id=settings.telegram_chat_id,
            database=db
        )
        print("   ✓ Telegram service gotowy")
        
        # Inicjalizuj AutoAnalysisScheduler
        print("\n4. Inicjalizuję AutoAnalysisScheduler...")
        scheduler = AutoAnalysisScheduler(
            database=db,
            telegram=telegram,
            interval_minutes=30,
            timeout=60,
            pause_between_symbols=2
        )
        print(f"   ✓ Scheduler gotowy z {len(scheduler.symbols)} symbolami")
        
        # Ogranicz do 2 symboli dla testu (oszczędność kosztów)
        print("\n5. Ograniczam do 2 symboli dla testu...")
        scheduler.symbols = ["EUR/USD", "GBP/USD"]
        print(f"   ✓ Test z symbolami: {scheduler.symbols}")
        
        # Uruchom cykl analiz
        print("\n6. Uruchamiam cykl analiz...")
        print("-" * 60)
        
        results = await scheduler.run_analysis_cycle()
        
        print("-" * 60)
        
        # Wyświetl wyniki
        print("\n7. Wyniki analiz:")
        print("=" * 60)
        
        if not results:
            print("   ⚠️  Brak wyników (możliwe błędy podczas analizy)")
        else:
            for i, result in enumerate(results, 1):
                print(f"\n   Symbol #{i}: {result['symbol']}")
                print(f"   ├─ Sygnał: {result['final_signal']}")
                print(f"   ├─ Zgodność: {result['agreement_score']}%")
                print(f"   ├─ Tokeny: {result['tokens_used']}")
                print(f"   ├─ Koszt: ${result['estimated_cost']:.4f}")
                print(f"   └─ ID analizy: {result['analysis_id']}")
        
        # Statystyki
        print("\n8. Statystyki cyklu:")
        print("=" * 60)
        stats = scheduler.get_statistics()
        print(f"   ├─ Czas trwania: {stats['duration_seconds']:.2f}s")
        print(f"   ├─ Przeanalizowano: {stats['analyzed_count']}/{len(scheduler.symbols)}")
        print(f"   ├─ Sygnały wygenerowane: {stats['signals_count']}")
        print(f"   ├─ Błędy: {stats['errors_count']}")
        print(f"   ├─ Łączne tokeny: {stats['total_tokens']}")
        print(f"   └─ Łączny koszt: ${stats['total_cost']:.4f}")
        
        print("\n" + "="*60)
        print("✅ TEST ZAKOŃCZONY POMYŚLNIE")
        print("="*60 + "\n")
        
        return True
        
    except Exception as e:
        print("\n" + "="*60)
        print(f"❌ TEST NIEUDANY: {e}")
        print("="*60 + "\n")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_auto_scheduler())
    sys.exit(0 if success else 1)
