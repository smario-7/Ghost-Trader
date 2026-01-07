"""
Serwis bazy danych SQLite z zabezpieczeniami
"""
import sqlite3
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import os
from pathlib import Path
from contextlib import contextmanager


class Database:
    """Klasa zarządzająca bazą danych SQLite"""
    
    def __init__(self, db_path: str):
        """
        Inicjalizacja bazy danych
        
        Args:
            db_path: Ścieżka do pliku bazy danych
        """
        self.db_path = db_path
        
        # Utwórz katalog jeśli nie istnieje
        db_dir = os.path.dirname(db_path)
        if db_dir:
            Path(db_dir).mkdir(parents=True, exist_ok=True)
    
    @contextmanager
    def get_connection(self):
        """Context manager dla połączenia z bazą"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Zwraca wiersze jako dict-like
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def initialize(self):
        """Inicjalizuje tabele w bazie danych"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Tabela strategii
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS strategies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    strategy_type TEXT NOT NULL,
                    parameters TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL DEFAULT '1h',
                    is_active BOOLEAN NOT NULL DEFAULT 1,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    last_signal TIMESTAMP
                )
            """)
            
            # Tabela sygnałów
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy_id INTEGER NOT NULL,
                    signal_type TEXT NOT NULL,
                    price REAL NOT NULL,
                    indicator_values TEXT,
                    message TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (strategy_id) REFERENCES strategies (id) ON DELETE CASCADE
                )
            """)
            
            # Indeksy dla lepszej wydajności
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_strategies_active 
                ON strategies(is_active)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_signals_strategy 
                ON signals(strategy_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_signals_created 
                ON signals(created_at DESC)
            """)
            
            # Trigger do aktualizacji updated_at
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS update_strategy_timestamp 
                AFTER UPDATE ON strategies
                FOR EACH ROW
                BEGIN
                    UPDATE strategies SET updated_at = CURRENT_TIMESTAMP
                    WHERE id = NEW.id;
                END
            """)
    
    def check_connection(self) -> bool:
        """Sprawdza połączenie z bazą danych"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                return True
        except Exception:
            return False
    
    # ===== OPERACJE NA STRATEGIACH =====
    
    def create_strategy(self, strategy_data: Dict[str, Any]) -> int:
        """
        Tworzy nową strategię
        
        Args:
            strategy_data: Dane strategii
        
        Returns:
            ID utworzonej strategii
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Prepared statement - bezpieczne przed SQL injection
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
        """Pobiera strategię po ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM strategies WHERE id = ?
            """, (strategy_id,))
            
            row = cursor.fetchone()
            if row:
                return self._row_to_strategy_dict(row)
            return None
    
    def get_all_strategies(self) -> List[Dict[str, Any]]:
        """Pobiera wszystkie strategie"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM strategies ORDER BY created_at DESC
            """)
            
            return [self._row_to_strategy_dict(row) for row in cursor.fetchall()]
    
    def get_active_strategies(self) -> List[Dict[str, Any]]:
        """Pobiera tylko aktywne strategie"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM strategies WHERE is_active = 1
                ORDER BY created_at DESC
            """)
            
            return [self._row_to_strategy_dict(row) for row in cursor.fetchall()]
    
    def update_strategy(
        self,
        strategy_id: int,
        updates: Dict[str, Any]
    ) -> bool:
        """
        Aktualizuje strategię
        
        Args:
            strategy_id: ID strategii
            updates: Słownik z polami do aktualizacji
        
        Returns:
            True jeśli zaktualizowano
        """
        if not updates:
            return False
        
        # Serializuj parameters jeśli jest w updates
        if 'parameters' in updates:
            updates['parameters'] = json.dumps(updates['parameters'])
        
        # Buduj query dynamicznie (ale bezpiecznie!)
        set_clause = ", ".join([f"{key} = ?" for key in updates.keys()])
        values = list(updates.values()) + [strategy_id]
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute(f"""
                UPDATE strategies SET {set_clause}
                WHERE id = ?
            """, values)
            
            return cursor.rowcount > 0
    
    def delete_strategy(self, strategy_id: int) -> bool:
        """Usuwa strategię"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                DELETE FROM strategies WHERE id = ?
            """, (strategy_id,))
            
            return cursor.rowcount > 0
    
    def update_last_signal(self, strategy_id: int):
        """Aktualizuje czas ostatniego sygnału"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE strategies SET last_signal = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (strategy_id,))
    
    # ===== OPERACJE NA SYGNAŁACH =====
    
    def create_signal(self, signal_data: Dict[str, Any]) -> int:
        """Tworzy nowy sygnał"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO signals 
                (strategy_id, signal_type, price, indicator_values, message)
                VALUES (?, ?, ?, ?, ?)
            """, (
                signal_data['strategy_id'],
                signal_data['signal_type'],
                signal_data['price'],
                json.dumps(signal_data.get('indicator_values', {})),
                signal_data.get('message')
            ))
            
            # Aktualizuj last_signal w strategii
            self.update_last_signal(signal_data['strategy_id'])
            
            return cursor.lastrowid
    
    def get_signals_by_strategy(
        self,
        strategy_id: int,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Pobiera sygnały dla strategii"""
        with self.get_connection() as conn:
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
        """Pobiera ostatnie sygnały"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT s.*, st.name as strategy_name, st.symbol
                FROM signals s
                JOIN strategies st ON s.strategy_id = st.id
                ORDER BY s.created_at DESC
                LIMIT ?
            """, (limit,))
            
            return [self._row_to_signal_dict(row) for row in cursor.fetchall()]
    
    # ===== STATYSTYKI =====
    
    def get_statistics(self) -> Dict[str, Any]:
        """Zwraca statystyki"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Liczba strategii
            cursor.execute("SELECT COUNT(*) FROM strategies")
            total_strategies = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM strategies WHERE is_active = 1")
            active_strategies = cursor.fetchone()[0]
            
            # Liczba sygnałów
            cursor.execute("SELECT COUNT(*) FROM signals")
            total_signals = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT COUNT(*) FROM signals 
                WHERE DATE(created_at) = DATE('now')
            """)
            signals_today = cursor.fetchone()[0]
            
            # Sygnały BUY/SELL
            cursor.execute("""
                SELECT signal_type, COUNT(*) 
                FROM signals 
                GROUP BY signal_type
            """)
            signal_counts = dict(cursor.fetchall())
            
            # Ostatni sygnał
            cursor.execute("""
                SELECT MAX(created_at) FROM signals
            """)
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
    
    # ===== POMOCNICZE =====
    
    def _row_to_strategy_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Konwertuje wiersz na słownik strategii"""
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
    
    def _row_to_signal_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Konwertuje wiersz na słownik sygnału"""
        return {
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
    
    def backup(self, backup_path: str) -> bool:
        """
        Tworzy backup bazy danych
        
        Args:
            backup_path: Ścieżka do pliku backup
        
        Returns:
            True jeśli backup się powiódł
        """
        try:
            # Utwórz katalog jeśli nie istnieje
            backup_dir = os.path.dirname(backup_path)
            if backup_dir:
                Path(backup_dir).mkdir(parents=True, exist_ok=True)
            
            # Użyj sqlite backup API
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
