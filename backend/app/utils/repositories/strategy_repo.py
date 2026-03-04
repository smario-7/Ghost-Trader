"""Repozytorium operacji na tabeli strategies."""
import json
import sqlite3
from typing import Any, Dict, List, Optional

from app.utils.database_impl.connection import Database


class StrategyRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def _row_to_strategy_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        return {
            'id': row['id'],
            'name': row['name'],
            'strategy_type': row['strategy_type'],
            'parameters': json.loads(row['parameters']),
            'symbol': row['symbol'],
            'timeframe': row['timeframe'],
            'is_active': bool(row['is_active']),
            'created_at': row['created_at'],
            'updated_at': row['updated_at'],
            'last_signal': row['last_signal']
        }

    def create_strategy(self, strategy_data: Dict[str, Any]) -> int:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO strategies 
                (name, strategy_type, parameters, symbol, timeframe, is_active)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                strategy_data['name'],
                strategy_data['strategy_type'],
                json.dumps(strategy_data['parameters']),
                strategy_data['symbol'],
                strategy_data.get('timeframe', '1h'),
                strategy_data.get('is_active', True)
            ))
            return cursor.lastrowid

    def get_strategy(self, strategy_id: int) -> Optional[Dict[str, Any]]:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM strategies WHERE id = ?", (strategy_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_strategy_dict(row)
            return None

    def get_all_strategies(self) -> List[Dict[str, Any]]:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM strategies ORDER BY created_at DESC")
            return [self._row_to_strategy_dict(row) for row in cursor.fetchall()]

    def get_active_strategies(self) -> List[Dict[str, Any]]:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM strategies WHERE is_active = 1
                ORDER BY created_at DESC
            """)
            return [self._row_to_strategy_dict(row) for row in cursor.fetchall()]

    def update_strategy(self, strategy_id: int, updates: Dict[str, Any]) -> bool:
        if not updates:
            return False
        if 'parameters' in updates:
            updates['parameters'] = json.dumps(updates['parameters'])
        set_clause = ", ".join([f"{key} = ?" for key in updates.keys()])
        values = list(updates.values()) + [strategy_id]
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE strategies SET {set_clause} WHERE id = ?", values)
            return cursor.rowcount > 0

    def delete_strategy(self, strategy_id: int) -> bool:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM strategies WHERE id = ?", (strategy_id,))
            return cursor.rowcount > 0

    def update_last_signal(self, strategy_id: int) -> None:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE strategies SET last_signal = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (strategy_id,))
