"""Repozytorium operacji na tabeli activity_logs."""
import json
from typing import Any, Dict, List, Optional

from app.config import get_polish_time
from app.utils.database_impl.connection import Database


def _row_to_activity_log(row: Any) -> Dict[str, Any]:
    log = {
        'id': row['id'],
        'timestamp': row['timestamp'],
        'log_type': row['log_type'],
        'message': row['message'],
        'symbol': row['symbol'],
        'strategy_name': row['strategy_name'],
        'status': row['status']
    }
    if row['details']:
        try:
            log['details'] = json.loads(row['details'])
        except Exception:
            log['details'] = {}
    else:
        log['details'] = {}
    return log


class ActivityRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def create_activity_log(
        self,
        log_type: str,
        message: str,
        symbol: Optional[str] = None,
        strategy_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        status: str = 'success'
    ) -> int:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            timestamp = get_polish_time().isoformat()
            details_json = json.dumps(details) if details else None
            cursor.execute("""
                INSERT INTO activity_logs 
                (timestamp, log_type, message, symbol, strategy_name, details, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (timestamp, log_type, message, symbol, strategy_name, details_json, status))
            return cursor.lastrowid

    def get_recent_activity_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, timestamp, log_type, message, symbol, strategy_name, details, status
                FROM activity_logs
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
            return [_row_to_activity_log(row) for row in cursor.fetchall()]

    def get_activity_logs_by_type(self, log_type: str, limit: int = 50) -> List[Dict[str, Any]]:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, timestamp, log_type, message, symbol, strategy_name, details, status
                FROM activity_logs
                WHERE log_type = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (log_type, limit))
            return [_row_to_activity_log(row) for row in cursor.fetchall()]

    def get_activity_logs_since(
        self,
        last_id: int,
        log_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            if log_type:
                cursor.execute("""
                    SELECT id, timestamp, log_type, message, symbol, strategy_name, details, status
                    FROM activity_logs
                    WHERE id > ? AND log_type = ?
                    ORDER BY id ASC
                    LIMIT ?
                """, (last_id, log_type, limit))
            else:
                cursor.execute("""
                    SELECT id, timestamp, log_type, message, symbol, strategy_name, details, status
                    FROM activity_logs
                    WHERE id > ?
                    ORDER BY id ASC
                    LIMIT ?
                """, (last_id, limit))
            return [_row_to_activity_log(row) for row in cursor.fetchall()]
