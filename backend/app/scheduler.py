"""
Scheduler - automatyczne sprawdzanie sygnałów
"""
import asyncio
import schedule
import time
from datetime import datetime
import logging
from pathlib import Path

from .config import get_settings
from .utils.logger import setup_logger
from .utils.database import Database
from .services.telegram_service import TelegramService
from .services.strategy_service import StrategyService


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
        chat_id=settings.telegram_chat_id
    )
    
    strategy_service = StrategyService(db, telegram)
    
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
    
    # Zaplanuj sprawdzanie sygnałów
    schedule.every(settings.check_interval).minutes.do(run_async_task)
    
    # Zaplanuj backup
    if settings.auto_backup:
        schedule.every(settings.backup_interval).hours.do(run_backup)
        logger.info(f"💾 Automatic backup enabled (every {settings.backup_interval}h)")
    
    # Wyślij powiadomienie o starcie
    async def send_startup_notification():
        try:
            await telegram.send_alert(
                title="Bot Started",
                message=f"Trading Bot Scheduler is now running\n"
                        f"Check interval: {settings.check_interval} min",
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
