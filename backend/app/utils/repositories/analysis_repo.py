"""Repozytorium operacji na tabeli ai_analysis_results i statystyk tokenów."""
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.utils.database_impl.connection import Database


class AnalysisRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def _row_to_ai_analysis_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        return {
            'id': row['id'],
            'symbol': row['symbol'],
            'timeframe': row['timeframe'],
            'timestamp': row['timestamp'],
            'ai_recommendation': row['ai_recommendation'],
            'ai_confidence': row['ai_confidence'],
            'ai_reasoning': row['ai_reasoning'],
            'technical_signal': row['technical_signal'],
            'technical_confidence': row['technical_confidence'],
            'technical_details': row['technical_details'],
            'macro_signal': row['macro_signal'],
            'macro_impact': row['macro_impact'],
            'news_sentiment': row['news_sentiment'],
            'news_score': row['news_score'],
            'final_signal': row['final_signal'],
            'agreement_score': row['agreement_score'],
            'voting_details': row['voting_details'],
            'tokens_used': row['tokens_used'],
            'estimated_cost': row['estimated_cost'],
            'decision_reason': row['decision_reason'],
            'created_at': row['created_at']
        }

    def create_ai_analysis_result(self, data: Dict[str, Any]) -> int:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO ai_analysis_results 
                (symbol, timeframe, timestamp, ai_recommendation, ai_confidence, 
                 ai_reasoning, technical_signal, technical_confidence, technical_details,
                 macro_signal, macro_impact, news_sentiment, news_score,
                 final_signal, agreement_score, voting_details,
                 tokens_used, estimated_cost, decision_reason)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data['symbol'],
                data['timeframe'],
                data.get('timestamp') or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                data.get('ai_recommendation'),
                data.get('ai_confidence'),
                data.get('ai_reasoning'),
                data.get('technical_signal'),
                data.get('technical_confidence'),
                data.get('technical_details'),
                data.get('macro_signal'),
                data.get('macro_impact'),
                data.get('news_sentiment'),
                data.get('news_score'),
                data.get('final_signal'),
                data.get('agreement_score'),
                data.get('voting_details'),
                data.get('tokens_used'),
                data.get('estimated_cost'),
                data.get('decision_reason')
            ))
            return cursor.lastrowid

    def get_ai_analysis_results(
        self,
        symbol: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            if symbol:
                cursor.execute("""
                    SELECT * FROM ai_analysis_results
                    WHERE symbol = ?
                    ORDER BY id DESC
                    LIMIT ?
                """, (symbol, limit))
            else:
                cursor.execute("""
                    SELECT * FROM ai_analysis_results
                    ORDER BY id DESC
                    LIMIT ?
                """, (limit,))
            return [self._row_to_ai_analysis_dict(row) for row in cursor.fetchall()]

    def get_ai_analysis_by_id(self, analysis_id: int) -> Optional[Dict[str, Any]]:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM ai_analysis_results WHERE id = ?", (analysis_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_ai_analysis_dict(row)
            return None

    def get_token_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            if start_date and end_date:
                cursor.execute("""
                    SELECT 
                        COUNT(*) as analyses_count,
                        COALESCE(SUM(tokens_used), 0) as total_tokens,
                        COALESCE(SUM(estimated_cost), 0) as total_cost
                    FROM ai_analysis_results
                    WHERE date(timestamp) >= date(?) AND date(timestamp) <= date(?)
                """, (start_date, end_date))
            else:
                cursor.execute("""
                    SELECT 
                        COUNT(*) as analyses_count,
                        COALESCE(SUM(tokens_used), 0) as total_tokens,
                        COALESCE(SUM(estimated_cost), 0) as total_cost
                    FROM ai_analysis_results
                """)
            row = cursor.fetchone()
            total_analyses = row['analyses_count']
            total_tokens = row['total_tokens']
            total_cost = row['total_cost']
            cursor.execute("""
                SELECT 
                    COUNT(*) as today_analyses,
                    COALESCE(SUM(tokens_used), 0) as today_tokens,
                    COALESCE(SUM(estimated_cost), 0) as today_cost
                FROM ai_analysis_results
                WHERE DATE(timestamp) = DATE('now')
            """)
            today_row = cursor.fetchone()
            avg_tokens = int(total_tokens / total_analyses) if total_analyses > 0 else 0
            return {
                'total_tokens': int(total_tokens),
                'total_cost': float(total_cost),
                'analyses_count': total_analyses,
                'avg_tokens_per_analysis': avg_tokens,
                'today_tokens': int(today_row['today_tokens']),
                'today_cost': float(today_row['today_cost']),
                'today_analyses': today_row['today_analyses']
            }
