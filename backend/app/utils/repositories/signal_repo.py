"""Repozytorium operacji na tabeli signals oraz statystyk (strategies + signals)."""
import json
import sqlite3
from typing import Any, Dict, List

from app.utils.database_impl.connection import Database


class SignalRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def _row_to_signal_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        result = {
            'id': row['id'],
            'strategy_id': row['strategy_id'],
            'strategy_name': row['strategy_name'],
            'symbol': row['symbol'],
            'signal_type': row['signal_type'],
            'price': row['price'],
            'indicator_values': json.loads(row['indicator_values'] or '{}'),
            'message': row['message'],
            'created_at': row['created_at']
        }
        if 'ai_analysis_id' in row.keys():
            result['ai_analysis_id'] = row['ai_analysis_id']
        if 'agreement_score' in row.keys():
            result['agreement_score'] = row['agreement_score']
        if 'decision_reason' in row.keys():
            result['decision_reason'] = row['decision_reason']
        return result

    def create_signal(self, signal_data: Dict[str, Any]) -> int:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO signals 
                (strategy_id, signal_type, price, indicator_values, message,
                 ai_analysis_id, agreement_score, decision_reason)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                signal_data['strategy_id'],
                signal_data['signal_type'],
                signal_data['price'],
                json.dumps(signal_data.get('indicator_values', {})),
                signal_data.get('message'),
                signal_data.get('ai_analysis_id'),
                signal_data.get('agreement_score'),
                signal_data.get('decision_reason')
            ))
            signal_id = cursor.lastrowid
            cursor.execute("""
                UPDATE strategies SET last_signal = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (signal_data['strategy_id'],))
            return signal_id

    def get_signals_by_strategy(self, strategy_id: int, limit: int = 100) -> List[Dict[str, Any]]:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT s.*, st.name as strategy_name, st.symbol
                FROM signals s
                JOIN strategies st ON s.strategy_id = st.id
                WHERE s.strategy_id = ?
                ORDER BY s.created_at DESC
                LIMIT ?
            """, (strategy_id, limit))
            return [self._row_to_signal_dict(row) for row in cursor.fetchall()]

    def get_recent_signals(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT s.*, st.name as strategy_name, st.symbol
                FROM signals s
                JOIN strategies st ON s.strategy_id = st.id
                ORDER BY s.created_at DESC
                LIMIT ?
            """, (limit,))
            return [self._row_to_signal_dict(row) for row in cursor.fetchall()]

    def get_statistics(self) -> Dict[str, Any]:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM strategies")
            total_strategies = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM strategies WHERE is_active = 1")
            active_strategies = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM signals")
            total_signals = cursor.fetchone()[0]
            cursor.execute("""
                SELECT COUNT(*) FROM signals 
                WHERE DATE(created_at) = DATE('now')
            """)
            signals_today = cursor.fetchone()[0]
            cursor.execute("""
                SELECT signal_type, COUNT(*) 
                FROM signals 
                GROUP BY signal_type
            """)
            signal_counts = dict(cursor.fetchall())
            cursor.execute("SELECT MAX(created_at) FROM signals")
            last_signal = cursor.fetchone()[0]
            return {
                'total_strategies': total_strategies,
                'active_strategies': active_strategies,
                'total_signals': total_signals,
                'signals_today': signals_today,
                'buy_signals': signal_counts.get('BUY', 0),
                'sell_signals': signal_counts.get('SELL', 0),
                'last_signal_time': last_signal
            }
