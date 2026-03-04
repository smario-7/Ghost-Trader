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

from .config import get_settings, get_polish_time
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
    logger.info(f"Database: {settings.database_path}")
    logger.info("=" * 60)

    db = Database(settings.database_path)
    db.initialize()
    scheduler_config = db.get_scheduler_config()
    logger.info(
        f"Interwały z DB: sygnały={scheduler_config['signal_check_interval']} min, "
        f"AI={scheduler_config['ai_analysis_interval']} min"
    )

    telegram = TelegramService(
        bot_token=settings.telegram_bot_token,
        chat_id=settings.telegram_chat_id,
        database=db
    )

    strategy_service = StrategyService(db, telegram)

    auto_scheduler = AutoAnalysisScheduler(
        database=db,
        telegram=telegram,
        interval_minutes=scheduler_config["ai_analysis_interval"],
        timeout=settings.analysis_timeout if hasattr(settings, 'analysis_timeout') else 60,
        pause_between_symbols=settings.analysis_pause_between_symbols if hasattr(settings, 'analysis_pause_between_symbols') else 2
    )
    
    async def check_signals_task():
        """Task sprawdzający sygnały"""
        try:
            logger.info("⏰ Starting signal check...")
            start_time = get_polish_time()
            
            # Sprawdź sygnały
            # Scheduler wykonuje prawdziwy check: zapisuje sygnały i wysyła powiadomienia.
            results = await strategy_service.check_all_signals(persist=True, notify=True)
            
            # Policz sygnały
            buy_count = sum(1 for r in results if r.get('signal') == 'BUY')
            sell_count = sum(1 for r in results if r.get('signal') == 'SELL')
            hold_count = sum(1 for r in results if r.get('signal') == 'HOLD')
            
            duration = (get_polish_time() - start_time).total_seconds()
            
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
    
    def should_run_task(task_type: str) -> bool:
        """
        Sprawdza czy zadanie powinno się wykonać na podstawie konfiguracji
        
        Args:
            task_type: Typ zadania ('signal' lub 'ai')
        
        Returns:
            True jeśli zadanie powinno się wykonać
        """
        try:
            config = db.get_scheduler_config()
            now = get_polish_time()
            
            # Sprawdź ON/OFF
            if task_type == 'signal' and not config['signal_check_enabled']:
                return False
            if task_type == 'ai' and not config['ai_analysis_enabled']:
                return False
            
            # Sprawdź harmonogram godzin
            start = config[f'{task_type}_hours_start']
            end = config[f'{task_type}_hours_end']
            current_time = now.strftime('%H:%M')
            if not (start <= current_time <= end):
                return False
            
            # Sprawdź dni tygodnia (1=Pn, 7=Nd)
            weekday = str(now.isoweekday())
            active_days = [d.strip() for d in config[f'{task_type}_active_days'].split(',')]
            if weekday not in active_days:
                return False
            
            return True
        except Exception as e:
            logger.error(f"Error checking task conditions: {e}")
            # W przypadku błędu, pozwól zadaniu się wykonać (fail-safe)
            return True
    
    def run_async_task():
        """Wrapper do uruchamiania async tasków"""
        if not should_run_task('signal'):
            logger.debug("⏸️  Signal check skipped (disabled or outside schedule)")
            return
        asyncio.run(check_signals_task())
    
    async def auto_analysis_task():
        """Task uruchamiający automatyczne analizy AI"""
        try:
            logger.info("⏰ Starting auto AI analysis cycle...")
            start_time = get_polish_time()
            
            results = await auto_scheduler.run_analysis_cycle()
            
            # Statystyki
            signals_count = sum(1 for r in results if r.get('final_signal') in ['BUY', 'SELL'])
            total_cost = sum(r.get('estimated_cost', 0) for r in results)
            
            duration = (get_polish_time() - start_time).total_seconds()
            
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
        if not should_run_task('ai'):
            logger.debug("⏸️  AI analysis skipped (disabled or outside schedule)")
            return
        asyncio.run(auto_analysis_task())
    
    async def backup_task():
        """Task backupu bazy danych"""
        if not settings.auto_backup:
            return
        
        try:
            logger.info("💾 Starting database backup...")
            
            # Utwórz nazwę pliku backup
            timestamp = get_polish_time().strftime("%Y%m%d_%H%M%S")
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
    
    last_scheduler_config = {
        'signal_check_interval': None,
        'ai_analysis_interval': None,
        'signal_check_enabled': None,
        'ai_analysis_enabled': None,
    }

    def update_scheduler_intervals():
        """
        Aktualizuje interwały schedulerów na podstawie konfiguracji z bazy danych
        tylko gdy konfiguracja się zmieniła (bez resetowania odliczania co 60s).
        """
        try:
            config = db.get_scheduler_config()
            prev = last_scheduler_config
            if (
                prev['signal_check_interval'] == config['signal_check_interval']
                and prev['ai_analysis_interval'] == config['ai_analysis_interval']
                and prev['signal_check_enabled'] == config['signal_check_enabled']
                and prev['ai_analysis_enabled'] == config['ai_analysis_enabled']
            ):
                return
            last_scheduler_config['signal_check_interval'] = config['signal_check_interval']
            last_scheduler_config['ai_analysis_interval'] = config['ai_analysis_interval']
            last_scheduler_config['signal_check_enabled'] = config['signal_check_enabled']
            last_scheduler_config['ai_analysis_enabled'] = config['ai_analysis_enabled']

            schedule.clear('signal_check')
            schedule.clear('ai_analysis')
            schedule.every(config['signal_check_interval']).minutes.do(run_async_task).tag('signal_check')
            schedule.every(config['ai_analysis_interval']).minutes.do(run_auto_analysis).tag('ai_analysis')
            logger.debug(
                f"📊 Intervals updated from DB: "
                f"signals={config['signal_check_interval']}min, "
                f"AI={config['ai_analysis_interval']}min"
            )
        except Exception as e:
            logger.error(f"Error updating scheduler intervals: {e}")
    
    # Pobierz konfigurację z bazy danych
    scheduler_config = db.get_scheduler_config()
    last_scheduler_config['signal_check_interval'] = scheduler_config['signal_check_interval']
    last_scheduler_config['ai_analysis_interval'] = scheduler_config['ai_analysis_interval']
    last_scheduler_config['signal_check_enabled'] = scheduler_config['signal_check_enabled']
    last_scheduler_config['ai_analysis_enabled'] = scheduler_config['ai_analysis_enabled']

    # Zaplanuj sprawdzanie sygnałów z interwałem z bazy
    schedule.every(scheduler_config['signal_check_interval']).minutes.do(run_async_task).tag('signal_check')
    logger.info(
        f"📊 Signal check scheduled (every {scheduler_config['signal_check_interval']} minutes, "
        f"enabled: {scheduler_config['signal_check_enabled']})"
    )
    
    # Pokaż informacje o aktywnych strategiach
    active_strategies = db.get_active_strategies()
    if active_strategies:
        logger.info(f"📋 Aktywne strategie ({len(active_strategies)}):")
        for strategy in active_strategies:
            timeframe = strategy.get('timeframe', '1h')
            logger.info(f"   - {strategy.get('name', 'Unknown')}: {timeframe}")
    else:
        logger.info("⚠️  Brak aktywnych strategii")
    
    # Zaplanuj backup
    if settings.auto_backup:
        schedule.every(settings.backup_interval).hours.do(run_backup).tag('backup')
        logger.info(f"💾 Automatic backup enabled (every {settings.backup_interval}h)")
    
    # Zaplanuj automatyczne analizy AI
    schedule.every(scheduler_config['ai_analysis_interval']).minutes.do(run_auto_analysis).tag('ai_analysis')
    logger.info(
        f"🤖 Auto AI analysis scheduled (every {scheduler_config['ai_analysis_interval']} minutes, "
        f"enabled: {scheduler_config['ai_analysis_enabled']})"
    )
    
    # Zaplanuj okresową aktualizację interwałów (co 60 sekund sprawdza czy konfiguracja się zmieniła)
    schedule.every(60).seconds.do(update_scheduler_intervals).tag('config_check')
    logger.info("🔄 Config auto-refresh enabled (checks every 60s)")
    
    # Wyślij powiadomienie o starcie
    async def send_startup_notification():
        try:
            active_strategies = db.get_active_strategies()
            signal_interval = scheduler_config['signal_check_interval']
            ai_interval = scheduler_config['ai_analysis_interval']
            
            if active_strategies:
                timeframes = [s.get('timeframe', '1h') for s in active_strategies]
                timeframes_str = ', '.join(set(timeframes))
                message = (
                    f"Trading Bot Scheduler is now running\n"
                    f"Signal check: {signal_interval} min\n"
                    f"AI analysis: {ai_interval} min\n"
                    f"Aktywne strategie: {len(active_strategies)}\n"
                    f"Timeframes: {timeframes_str}"
                )
            else:
                message = (
                    f"Trading Bot Scheduler is now running\n"
                    f"Signal check: {signal_interval} min\n"
                    f"AI analysis: {ai_interval} min\n"
                    f"Brak aktywnych strategii"
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
