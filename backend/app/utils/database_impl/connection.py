"""
Klasa Database: połączenie do SQLite, context manager, backup i inicjalizacja schematu.
Operacje CRUD są delegowane do repozytoriów.
"""
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

from .migrations import run_migrations


class Database:
    """Klasa zarządzająca bazą danych SQLite."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        db_dir = os.path.dirname(db_path)
        if db_dir:
            Path(db_dir).mkdir(parents=True, exist_ok=True)
        from app.utils.repositories import (
            ActivityRepository,
            AnalysisRepository,
            SettingsRepository,
            SignalRepository,
            StrategyRepository,
        )
        self._strategy_repo = StrategyRepository(self)
        self._signal_repo = SignalRepository(self)
        self._analysis_repo = AnalysisRepository(self)
        self._settings_repo = SettingsRepository(self)
        self._activity_repo = ActivityRepository(self)

    @contextmanager
    def get_connection(self):
        """Context manager dla połączenia z bazą."""
        use_uri = self.db_path.startswith("file:")
        conn = sqlite3.connect(self.db_path, uri=use_uri)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def initialize(self) -> None:
        """Inicjalizuje tabele w bazie danych (wywołuje run_migrations)."""
        with self.get_connection() as conn:
            run_migrations(conn)

    def check_connection(self) -> bool:
        """Sprawdza połączenie z bazą danych."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                return True
        except Exception:
            return False

    def backup(self, backup_path: str) -> bool:
        """Tworzy backup bazy danych."""
        try:
            backup_dir = os.path.dirname(backup_path)
            if backup_dir:
                Path(backup_dir).mkdir(parents=True, exist_ok=True)
            with self.get_connection() as source:
                backup_conn = sqlite3.connect(backup_path)
                try:
                    source.backup(backup_conn)
                    return True
                finally:
                    backup_conn.close()
        except Exception as e:
            print(f"Backup failed: {e}")
            return False

    def create_strategy(self, strategy_data: Dict[str, Any]) -> int:
        return self._strategy_repo.create_strategy(strategy_data)

    def get_strategy(self, strategy_id: int) -> Optional[Dict[str, Any]]:
        return self._strategy_repo.get_strategy(strategy_id)

    def get_all_strategies(self) -> List[Dict[str, Any]]:
        return self._strategy_repo.get_all_strategies()

    def get_active_strategies(self) -> List[Dict[str, Any]]:
        return self._strategy_repo.get_active_strategies()

    def update_strategy(self, strategy_id: int, updates: Dict[str, Any]) -> bool:
        return self._strategy_repo.update_strategy(strategy_id, updates)

    def delete_strategy(self, strategy_id: int) -> bool:
        return self._strategy_repo.delete_strategy(strategy_id)

    def update_last_signal(self, strategy_id: int) -> None:
        self._strategy_repo.update_last_signal(strategy_id)

    def create_signal(self, signal_data: Dict[str, Any]) -> int:
        return self._signal_repo.create_signal(signal_data)

    def get_signals_by_strategy(self, strategy_id: int, limit: int = 100) -> List[Dict[str, Any]]:
        return self._signal_repo.get_signals_by_strategy(strategy_id, limit)

    def get_recent_signals(self, limit: int = 100) -> List[Dict[str, Any]]:
        return self._signal_repo.get_recent_signals(limit)

    def get_statistics(self) -> Dict[str, Any]:
        return self._signal_repo.get_statistics()

    def create_ai_analysis_result(self, data: Dict[str, Any]) -> int:
        return self._analysis_repo.create_ai_analysis_result(data)

    def get_ai_analysis_results(
        self, symbol: Optional[str] = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        return self._analysis_repo.get_ai_analysis_results(symbol=symbol, limit=limit)

    def get_ai_analysis_by_id(self, analysis_id: int) -> Optional[Dict[str, Any]]:
        return self._analysis_repo.get_ai_analysis_by_id(analysis_id)

    def get_token_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self._analysis_repo.get_token_statistics(
            start_date=start_date, end_date=end_date
        )

    def get_analysis_config(self) -> Dict[str, Any]:
        return self._settings_repo.get_analysis_config()

    def update_analysis_config(self, updates: Dict[str, Any]) -> bool:
        return self._settings_repo.update_analysis_config(updates)

    def initialize_default_config(self) -> int:
        return self._settings_repo.initialize_default_config()

    def get_telegram_settings(self) -> Dict[str, Any]:
        return self._settings_repo.get_telegram_settings()

    def update_telegram_settings(self, updates: Dict[str, Any]) -> bool:
        return self._settings_repo.update_telegram_settings(updates)

    def set_mute_until(self, muted_until: Optional[str]) -> bool:
        return self._settings_repo.set_mute_until(muted_until)

    def get_mute_status(self) -> Dict[str, Any]:
        return self._settings_repo.get_mute_status()

    def toggle_telegram_notifications(self) -> bool:
        return self._settings_repo.toggle_telegram_notifications()

    def get_scheduler_config(self) -> Dict[str, Any]:
        return self._settings_repo.get_scheduler_config()

    def update_scheduler_config(self, updates: Dict[str, Any]) -> bool:
        return self._settings_repo.update_scheduler_config(updates)

    def get_scheduler_status(self) -> Dict[str, Any]:
        return self._settings_repo.get_scheduler_status()

    def get_system_settings(self) -> Dict[str, Any]:
        return self._settings_repo.get_system_settings()

    def update_system_settings(self, payload: Dict[str, Any]) -> bool:
        return self._settings_repo.update_system_settings(payload)

    def create_activity_log(
        self,
        log_type: str,
        message: str,
        symbol: Optional[str] = None,
        strategy_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        status: str = "success",
    ) -> int:
        return self._activity_repo.create_activity_log(
            log_type=log_type,
            message=message,
            symbol=symbol,
            strategy_name=strategy_name,
            details=details,
            status=status,
        )

    def get_recent_activity_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        return self._activity_repo.get_recent_activity_logs(limit)

    def get_activity_logs_by_type(
        self, log_type: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        return self._activity_repo.get_activity_logs_by_type(log_type, limit)

    def get_activity_logs_since(
        self,
        last_id: int,
        log_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        return self._activity_repo.get_activity_logs_since(
            last_id=last_id, log_type=log_type, limit=limit
        )
