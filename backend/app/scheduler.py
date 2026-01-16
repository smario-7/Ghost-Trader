"""
Scheduler - automatyczne sprawdzanie sygnałów
"""
import asyncio
import schedule
import time
from datetime import datetime
import logging
from pathlib import Path
from typing import Optional

from .config import get_settings
from .utils.logger import setup_logger
from .utils.database import Database
from .services.telegram_service import TelegramService
from .services.strategy_service import StrategyService
from .services.auto_analysis_scheduler import AutoAnalysisScheduler


def timeframe_to_minutes(timeframe: str) -> int:
    """
    Konwertuje timeframe string na minuty
    
    Args:
        timeframe: String timeframe (np. '1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w')
    
    Returns:
        Liczba minut
    """
    timeframe = timeframe.lower().strip()
    
    if timeframe.endswith('m'):
        return int(timeframe[:-1])
    elif timeframe.endswith('h'):
        return int(timeframe[:-1]) * 60
    elif timeframe.endswith('d'):
        return int(timeframe[:-1]) * 1440
    elif timeframe.endswith('w'):
        return int(timeframe[:-1]) * 10080
    else:
        raise ValueError(f"Nieprawidłowy format timeframe: {timeframe}")


def calculate_dynamic_interval(db: Database, default_interval: int) -> int:
    """
    Oblicza dynamiczny interwał na podstawie najkrótszego timeframe aktywnych strategii
    
    Args:
        db: Instancja bazy danych
        default_interval: Domyślny interwał w minutach (używany gdy brak aktywnych strategii)
    
    Returns:
        Interwał w minutach
    """
    try:
        active_strategies = db.get_active_strategies()
        
        if not active_strategies:
            return default_interval
        
        timeframes_minutes = []
        for strategy in active_strategies:
            timeframe = strategy.get('timeframe', '1h')
            try:
                minutes = timeframe_to_minutes(timeframe)
                timeframes_minutes.append(minutes)
            except (ValueError, AttributeError) as e:
                continue
        
        if not timeframes_minutes:
            return default_interval
        
        min_interval = min(timeframes_minutes)
        
        return min_interval
    
    except Exception as e:
        logging.getLogger("trading_bot.scheduler").warning(
            f"Błąd podczas obliczania dynamicznego interwału: {e}. Używam domyślnego."
        )
        return default_interval


def setup_scheduler():
    """Konfiguruje i uruchamia scheduler"""
    
    # Wczytaj konfigurację
    settings = get_settings()
    
    # Setup logowania
    logger = setup_logger(
        name="trading_bot.scheduler",
        log_file=settings.log_file.replace('bot.log', 'scheduler.log'),
        level=settings.log_level
    )
    
    logger.info("=" * 60)
    logger.info("🤖 TRADING BOT SCHEDULER STARTED")
    logger.info("=" * 60)
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Check interval: {settings.check_interval} minutes")
    logger.info(f"Database: {settings.database_path}")
    logger.info("=" * 60)
    
    # Inicjalizuj serwisy
    db = Database(settings.database_path)
    db.initialize()
    
    telegram = TelegramService(
        bot_token=settings.telegram_bot_token,
        chat_id=settings.telegram_chat_id,
        database=db
    )
    
    strategy_service = StrategyService(db, telegram)
    
    # Inicjalizuj AutoAnalysisScheduler (Etap 4)
    auto_scheduler = AutoAnalysisScheduler(
        database=db,
        telegram=telegram,
        interval_minutes=settings.analysis_interval if hasattr(settings, 'analysis_interval') else 30,
        timeout=settings.analysis_timeout if hasattr(settings, 'analysis_timeout') else 60,
        pause_between_symbols=settings.analysis_pause_between_symbols if hasattr(settings, 'analysis_pause_between_symbols') else 2
    )
    
    # Referencja do zadania sprawdzania sygnałów (do dynamicznej aktualizacji)
    signal_check_job = None
    
    def update_signal_check_interval():
        """Aktualizuje interwał sprawdzania sygnałów na podstawie aktywnych strategii"""
        nonlocal signal_check_job
        
        try:
            # Oblicz nowy interwał
            new_interval = calculate_dynamic_interval(db, settings.check_interval)
            
            # Jeśli zadanie już istnieje, usuń je
            if signal_check_job is not None:
                schedule.cancel_job(signal_check_job)
            
            # Utwórz nowe zadanie z nowym interwałem
            signal_check_job = schedule.every(new_interval).minutes.do(run_async_task)
            
            logger.info(f"🔄 Zaktualizowano interwał sprawdzania sygnałów: {new_interval} minut")
            
            return new_interval
        
        except Exception as e:
            logger.error(f"Błąd podczas aktualizacji interwału: {e}")
            return settings.check_interval
    
    async def check_signals_task():
        """Task sprawdzający sygnały"""
        try:
            logger.info("⏰ Starting signal check...")
            start_time = datetime.now()
            
            # Sprawdź sygnały
            results = await strategy_service.check_all_signals()
            
            # Policz sygnały
            buy_count = sum(1 for r in results if r.get('signal') == 'BUY')
            sell_count = sum(1 for r in results if r.get('signal') == 'SELL')
            hold_count = sum(1 for r in results if r.get('signal') == 'HOLD')
            
            duration = (datetime.now() - start_time).total_seconds()
            
            logger.info(
                f"✅ Signal check completed in {duration:.2f}s | "
                f"BUY: {buy_count}, SELL: {sell_count}, HOLD: {hold_count}"
            )
            
            # Po każdym sprawdzeniu sygnałów, zaktualizuj interwał
            # (na wypadek zmiany aktywnych strategii)
            update_signal_check_interval()
            
        except Exception as e:
            logger.error(f"❌ Error during signal check: {e}", exc_info=True)
            
            # Wyślij alert o błędzie
            try:
                await telegram.send_alert(
                    title="Scheduler Error",
                    message=f"Error checking signals: {str(e)}",
                    level="ERROR"
                )
            except:
                pass
    
    def run_async_task():
        """Wrapper do uruchamiania async tasków"""
        asyncio.run(check_signals_task())
    
    async def auto_analysis_task():
        """Task uruchamiający automatyczne analizy AI"""
        try:
            logger.info("⏰ Starting auto AI analysis cycle...")
            start_time = datetime.now()
            
            results = await auto_scheduler.run_analysis_cycle()
            
            # Statystyki
            signals_count = sum(1 for r in results if r.get('final_signal') in ['BUY', 'SELL'])
            total_cost = sum(r.get('estimated_cost', 0) for r in results)
            
            duration = (datetime.now() - start_time).total_seconds()
            
            logger.info(
                f"✅ Auto analysis completed in {duration:.2f}s | "
                f"Analyzed: {len(results)}, Signals: {signals_count}, "
                f"Cost: ${total_cost:.4f}"
            )
            
        except Exception as e:
            logger.error(f"❌ Error during auto analysis: {e}", exc_info=True)
            
            # Wyślij alert o błędzie
            try:
                await telegram.send_alert(
                    title="Auto Analysis Error",
                    message=f"Error during auto AI analysis: {str(e)}",
                    level="ERROR"
                )
            except:
                pass
    
    def run_auto_analysis():
        """Wrapper dla auto analysis"""
        asyncio.run(auto_analysis_task())
    
    async def backup_task():
        """Task backupu bazy danych"""
        if not settings.auto_backup:
            return
        
        try:
            logger.info("💾 Starting database backup...")
            
            # Utwórz nazwę pliku backup
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = f"{settings.backup_dir}/trading_bot_{timestamp}.db"
            
            # Wykonaj backup
            success = db.backup(backup_file)
            
            if success:
                # Sprawdź rozmiar
                file_size = Path(backup_file).stat().st_size
                logger.info(
                    f"✅ Backup completed: {backup_file} "
                    f"({file_size / 1024:.2f} KB)"
                )
                
                # Wyczyść stare backupy (zostaw ostatnie 10)
                cleanup_old_backups(settings.backup_dir, keep=10)
            else:
                logger.error("❌ Backup failed")
                
        except Exception as e:
            logger.error(f"❌ Error during backup: {e}", exc_info=True)
    
    def run_backup():
        """Wrapper dla backupu"""
        asyncio.run(backup_task())
    
    def cleanup_old_backups(backup_dir: str, keep: int = 10):
        """Usuwa stare backupy"""
        try:
            backup_path = Path(backup_dir)
            if not backup_path.exists():
                return
            
            # Pobierz wszystkie pliki backup
            backups = sorted(
                backup_path.glob("trading_bot_*.db"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            
            # Usuń nadmiarowe
            for backup in backups[keep:]:
                backup.unlink()
                logger.info(f"🗑️  Removed old backup: {backup.name}")
                
        except Exception as e:
            logger.error(f"Error cleaning backups: {e}")
    
    # Oblicz dynamiczny interwał na podstawie aktywnych strategii
    dynamic_interval = calculate_dynamic_interval(db, settings.check_interval)
    
    # Zaplanuj sprawdzanie sygnałów z dynamicznym interwałem
    signal_check_job = schedule.every(dynamic_interval).minutes.do(run_async_task)
    
    logger.info(f"📊 Dynamiczny interwał: {dynamic_interval} minut (najkrótszy timeframe aktywnych strategii)")
    
    # Pokaż informacje o aktywnych strategiach
    active_strategies = db.get_active_strategies()
    if active_strategies:
        logger.info(f"📋 Aktywne strategie ({len(active_strategies)}):")
        for strategy in active_strategies:
            timeframe = strategy.get('timeframe', '1h')
            logger.info(f"   - {strategy.get('name', 'Unknown')}: {timeframe}")
    else:
        logger.info("⚠️  Brak aktywnych strategii - używam domyślnego interwału")
    
    # Zaplanuj backup
    if settings.auto_backup:
        schedule.every(settings.backup_interval).hours.do(run_backup)
        logger.info(f"💾 Automatic backup enabled (every {settings.backup_interval}h)")
    
    # Zaplanuj automatyczne analizy AI (Etap 4)
    analysis_enabled = settings.analysis_enabled if hasattr(settings, 'analysis_enabled') else True
    if analysis_enabled:
        analysis_interval = settings.analysis_interval if hasattr(settings, 'analysis_interval') else 30
        schedule.every(analysis_interval).minutes.do(run_auto_analysis)
        logger.info(f"🤖 Auto AI analysis scheduled (every {analysis_interval} minutes)")
    else:
        logger.info("⚠️  Auto AI analysis disabled in configuration")
    
    # Wyślij powiadomienie o starcie
    async def send_startup_notification():
        try:
            active_strategies = db.get_active_strategies()
            if active_strategies:
                timeframes = [s.get('timeframe', '1h') for s in active_strategies]
                timeframes_str = ', '.join(set(timeframes))
                message = (
                    f"Trading Bot Scheduler is now running\n"
                    f"Dynamiczny interwał: {dynamic_interval} min\n"
                    f"Aktywne strategie: {len(active_strategies)}\n"
                    f"Timeframes: {timeframes_str}"
                )
            else:
                message = (
                    f"Trading Bot Scheduler is now running\n"
                    f"Interwał: {dynamic_interval} min (domyślny - brak aktywnych strategii)"
                )
            
            await telegram.send_alert(
                title="Bot Started",
                message=message,
                level="SUCCESS"
            )
        except Exception as e:
            logger.error(f"Failed to send startup notification: {e}")
    
    asyncio.run(send_startup_notification())
    
    # Pierwsz sprawdzenie od razu
    logger.info("🚀 Running first signal check...")
    run_async_task()
    
    # Główna pętla
    logger.info("🔄 Entering main loop...")
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("\n👋 Scheduler stopped by user")
    except Exception as e:
        logger.error(f"❌ Scheduler crashed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    setup_scheduler()
