"""Repozytorium operacji na analysis_config, telegram_settings i scheduler_config."""
import json
from typing import Any, Dict

from app.config import get_polish_time
from app.utils.database_impl.connection import Database


class SettingsRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def get_analysis_config(self) -> Dict[str, Any]:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM analysis_config ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            if row:
                return {
                    'id': row['id'],
                    'analysis_interval': row['analysis_interval'],
                    'enabled_symbols': json.loads(row['enabled_symbols']) if row['enabled_symbols'] else [],
                    'notification_threshold': row['notification_threshold'],
                    'is_active': bool(row['is_active']),
                    'updated_at': row['updated_at']
                }
            return {
                'id': None,
                'analysis_interval': 15,
                'enabled_symbols': [],
                'notification_threshold': 60,
                'is_active': True,
                'updated_at': None
            }

    def update_analysis_config(self, updates: Dict[str, Any]) -> bool:
        if not updates:
            return False
        if 'enabled_symbols' in updates:
            updates['enabled_symbols'] = json.dumps(updates['enabled_symbols'])
        updates['updated_at'] = get_polish_time().isoformat()
        set_clause = ", ".join([f"{key} = ?" for key in updates.keys()])
        values = list(updates.values())
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM analysis_config ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            if row:
                values.append(row['id'])
                cursor.execute(f"UPDATE analysis_config SET {set_clause} WHERE id = ?", values)
            else:
                columns = ", ".join(updates.keys())
                placeholders = ", ".join(["?" for _ in updates])
                cursor.execute(f"INSERT INTO analysis_config ({columns}) VALUES ({placeholders})", list(updates.values()))
            return True

    def initialize_default_config(self) -> int:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO analysis_config 
                (analysis_interval, notification_threshold, is_active)
                VALUES (15, 60, 1)
            """)
            return cursor.lastrowid

    def get_telegram_settings(self) -> Dict[str, Any]:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM telegram_settings ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            if row:
                return {
                    'id': row['id'],
                    'notifications_enabled': bool(row['notifications_enabled']),
                    'muted_until': row['muted_until'],
                    'allowed_hours_start': row['allowed_hours_start'],
                    'allowed_hours_end': row['allowed_hours_end'],
                    'allowed_days': row['allowed_days'],
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at']
                }
            return {
                'notifications_enabled': True,
                'muted_until': None,
                'allowed_hours_start': '00:00',
                'allowed_hours_end': '23:59',
                'allowed_days': '1,2,3,4,5,6,7'
            }

    def update_telegram_settings(self, updates: Dict[str, Any]) -> bool:
        if not updates:
            return False
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM telegram_settings ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            if row:
                set_clause = ", ".join([f"{key} = ?" for key in updates.keys()])
                set_clause += ", updated_at = CURRENT_TIMESTAMP"
                values = list(updates.values()) + [row['id']]
                cursor.execute(f"UPDATE telegram_settings SET {set_clause} WHERE id = ?", values)
            else:
                columns = list(updates.keys())
                placeholders = ", ".join(["?" for _ in columns])
                column_names = ", ".join(columns)
                cursor.execute(f"INSERT INTO telegram_settings ({column_names}) VALUES ({placeholders})", list(updates.values()))
            return True

    def set_mute_until(self, muted_until: Any) -> bool:
        return self.update_telegram_settings({'muted_until': muted_until})

    def get_mute_status(self) -> Dict[str, Any]:
        settings = self.get_telegram_settings()
        is_muted = False
        muted_until = settings.get('muted_until')
        if muted_until:
            try:
                from datetime import datetime
                muted_date = datetime.fromisoformat(muted_until.replace('Z', '+00:00'))
                is_muted = get_polish_time() < muted_date
            except Exception:
                is_muted = False
        return {
            'is_muted': is_muted,
            'muted_until': muted_until,
            'notifications_enabled': settings.get('notifications_enabled', True)
        }

    def toggle_telegram_notifications(self) -> bool:
        settings = self.get_telegram_settings()
        new_state = not settings.get('notifications_enabled', True)
        self.update_telegram_settings({'notifications_enabled': new_state})
        return new_state

    def get_scheduler_config(self) -> Dict[str, Any]:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM scheduler_config ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            if row:
                return {
                    'id': row['id'],
                    'signal_check_enabled': bool(row['signal_check_enabled']),
                    'ai_analysis_enabled': bool(row['ai_analysis_enabled']),
                    'signal_check_interval': row['signal_check_interval'],
                    'ai_analysis_interval': row['ai_analysis_interval'],
                    'signal_hours_start': row['signal_hours_start'],
                    'signal_hours_end': row['signal_hours_end'],
                    'ai_hours_start': row['ai_hours_start'],
                    'ai_hours_end': row['ai_hours_end'],
                    'signal_active_days': row['signal_active_days'],
                    'ai_active_days': row['ai_active_days'],
                    'updated_at': row['updated_at'],
                    'created_at': row['created_at']
                }
            return {
                'signal_check_enabled': True,
                'ai_analysis_enabled': True,
                'signal_check_interval': 15,
                'ai_analysis_interval': 30,
                'signal_hours_start': '00:00',
                'signal_hours_end': '23:59',
                'ai_hours_start': '00:00',
                'ai_hours_end': '23:59',
                'signal_active_days': '1,2,3,4,5,6,7',
                'ai_active_days': '1,2,3,4,5,6,7'
            }

    def update_scheduler_config(self, updates: Dict[str, Any]) -> bool:
        if not updates:
            return False
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM scheduler_config ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            if row:
                set_clause = ", ".join([f"{key} = ?" for key in updates.keys()])
                set_clause += ", updated_at = CURRENT_TIMESTAMP"
                values = list(updates.values()) + [row['id']]
                cursor.execute(f"UPDATE scheduler_config SET {set_clause} WHERE id = ?", values)
            else:
                columns = list(updates.keys())
                placeholders = ", ".join(["?" for _ in columns])
                column_names = ", ".join(columns)
                cursor.execute(f"INSERT INTO scheduler_config ({column_names}) VALUES ({placeholders})", list(updates.values()))
            return True

    def get_scheduler_status(self) -> Dict[str, Any]:
        config = self.get_scheduler_config()
        now = get_polish_time()
        current_time = now.strftime('%H:%M')
        weekday = str(now.isoweekday())
        signal_in_time_window = config['signal_hours_start'] <= current_time <= config['signal_hours_end']
        signal_active_days_list = [d.strip() for d in config['signal_active_days'].split(',')]
        signal_in_active_days = weekday in signal_active_days_list
        signal_should_run = (
            config['signal_check_enabled'] and
            signal_in_time_window and
            signal_in_active_days
        )
        ai_in_time_window = config['ai_hours_start'] <= current_time <= config['ai_hours_end']
        ai_active_days_list = [d.strip() for d in config['ai_active_days'].split(',')]
        ai_in_active_days = weekday in ai_active_days_list
        ai_should_run = (
            config['ai_analysis_enabled'] and
            ai_in_time_window and
            ai_in_active_days
        )
        return {
            'signal_check': {
                'enabled': config['signal_check_enabled'],
                'in_time_window': signal_in_time_window,
                'in_active_days': signal_in_active_days,
                'should_run': signal_should_run,
                'interval': config['signal_check_interval']
            },
            'ai_analysis': {
                'enabled': config['ai_analysis_enabled'],
                'in_time_window': ai_in_time_window,
                'in_active_days': ai_in_active_days,
                'should_run': ai_should_run,
                'interval': config['ai_analysis_interval']
            },
            'current_time': current_time,
            'current_weekday': weekday,
            'timestamp': now.isoformat()
        }

    def get_system_settings(self) -> Dict[str, Any]:
        """Zwraca wszystkie ustawienia runtime w jednym obiekcie (scheduler, ai, telegram)."""
        return {
            "scheduler": self.get_scheduler_config(),
            "ai": self.get_analysis_config(),
            "telegram": self.get_telegram_settings(),
        }

    def update_system_settings(self, payload: Dict[str, Any]) -> bool:
        """Aktualizuje wiele sekcji ustawień w jednej transakcji."""
        if not payload:
            return False
        scheduler_updates = payload.get("scheduler")
        ai_updates = payload.get("ai")
        telegram_updates = payload.get("telegram")

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            now_iso = get_polish_time().isoformat()

            if scheduler_updates:
                self._apply_scheduler_updates(cursor, scheduler_updates, now_iso)
            if ai_updates:
                self._apply_analysis_config_updates(cursor, ai_updates, now_iso)
            if telegram_updates:
                self._apply_telegram_updates(cursor, telegram_updates)

        return True

    def _apply_scheduler_updates(
        self, cursor: Any, updates: Dict[str, Any], updated_at: str
    ) -> None:
        if not updates:
            return
        cursor.execute("SELECT id FROM scheduler_config ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        set_parts = [f"{k} = ?" for k in updates.keys()]
        set_parts.append("updated_at = ?")
        values = list(updates.values()) + [updated_at]
        if row:
            values.append(row["id"])
            cursor.execute(
                f"UPDATE scheduler_config SET {', '.join(set_parts)} WHERE id = ?",
                values,
            )
        else:
            cols = list(updates.keys()) + ["updated_at"]
            placeholders = ", ".join(["?" for _ in cols])
            cursor.execute(
                f"INSERT INTO scheduler_config ({', '.join(cols)}) VALUES ({placeholders})",
                list(updates.values()) + [updated_at],
            )

    def _apply_analysis_config_updates(
        self, cursor: Any, updates: Dict[str, Any], updated_at: str
    ) -> None:
        if not updates:
            return
        prepared = dict(updates)
        if "enabled_symbols" in prepared:
            prepared["enabled_symbols"] = json.dumps(prepared["enabled_symbols"])
        prepared["updated_at"] = updated_at
        set_parts = [f"{k} = ?" for k in prepared.keys()]
        values = list(prepared.values())
        cursor.execute("SELECT id FROM analysis_config ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        if row:
            values.append(row["id"])
            cursor.execute(
                f"UPDATE analysis_config SET {', '.join(set_parts)} WHERE id = ?",
                values,
            )
        else:
            cols = ", ".join(prepared.keys())
            placeholders = ", ".join(["?" for _ in prepared])
            cursor.execute(
                f"INSERT INTO analysis_config ({cols}) VALUES ({placeholders})",
                list(prepared.values()),
            )

    def _apply_telegram_updates(self, cursor: Any, updates: Dict[str, Any]) -> None:
        if not updates:
            return
        cursor.execute("SELECT id FROM telegram_settings ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        set_parts = [f"{k} = ?" for k in updates.keys()]
        set_parts.append("updated_at = CURRENT_TIMESTAMP")
        values = list(updates.values())
        if row:
            values.append(row["id"])
            cursor.execute(
                f"UPDATE telegram_settings SET {', '.join(set_parts)} WHERE id = ?",
                values,
            )
        else:
            cols = list(updates.keys())
            placeholders = ", ".join(["?" for _ in cols])
            cursor.execute(
                f"INSERT INTO telegram_settings ({', '.join(cols)}) VALUES ({placeholders})",
                list(updates.values()),
            )
