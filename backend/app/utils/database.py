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
from ..config import get_polish_time


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
            
            # Tabela logów aktywności
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS activity_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    log_type TEXT NOT NULL,
                    message TEXT NOT NULL,
                    symbol TEXT,
                    strategy_name TEXT,
                    details TEXT,
                    status TEXT NOT NULL DEFAULT 'success',
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Indeksy dla logów aktywności
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_activity_logs_timestamp 
                ON activity_logs(timestamp DESC)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_activity_logs_type 
                ON activity_logs(log_type)
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
            
            # Tabela wyników analiz AI
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ai_analysis_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    
                    ai_recommendation TEXT,
                    ai_confidence INTEGER,
                    ai_reasoning TEXT,
                    
                    technical_signal TEXT,
                    technical_confidence INTEGER,
                    technical_details TEXT,
                    
                    macro_signal TEXT,
                    macro_impact TEXT,
                    
                    news_sentiment TEXT,
                    news_score INTEGER,
                    
                    final_signal TEXT,
                    agreement_score INTEGER,
                    voting_details TEXT,
                    
                    tokens_used INTEGER,
                    estimated_cost REAL,
                    
                    decision_reason TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Indeksy dla ai_analysis_results
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_ai_analysis_symbol 
                ON ai_analysis_results(symbol)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_ai_analysis_timestamp 
                ON ai_analysis_results(timestamp DESC)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_ai_analysis_signal 
                ON ai_analysis_results(final_signal)
            """)
            
            # Tabela konfiguracji analiz
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS analysis_config (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    analysis_interval INTEGER DEFAULT 15,
                    enabled_symbols TEXT,
                    notification_threshold INTEGER DEFAULT 60,
                    is_active BOOLEAN DEFAULT 1,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Rozszerzenie tabeli signals o nowe kolumny
            # Sprawdzamy czy kolumny już istnieją
            cursor.execute("PRAGMA table_info(signals)")
            existing_columns = [row[1] for row in cursor.fetchall()]
            
            if 'ai_analysis_id' not in existing_columns:
                cursor.execute("ALTER TABLE signals ADD COLUMN ai_analysis_id INTEGER")
            
            if 'agreement_score' not in existing_columns:
                cursor.execute("ALTER TABLE signals ADD COLUMN agreement_score INTEGER")
            
            if 'decision_reason' not in existing_columns:
                cursor.execute("ALTER TABLE signals ADD COLUMN decision_reason TEXT")
            
            # Inicjalizacja domyślnej konfiguracji jeśli nie istnieje
            cursor.execute("SELECT COUNT(*) FROM analysis_config")
            if cursor.fetchone()[0] == 0:
                cursor.execute("""
                    INSERT INTO analysis_config 
                    (analysis_interval, notification_threshold, is_active)
                    VALUES (15, 60, 1)
                """)
            
            # Tabela ustawień powiadomień Telegram
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS telegram_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    notifications_enabled BOOLEAN DEFAULT 1,
                    muted_until DATETIME NULL,
                    allowed_hours_start TEXT DEFAULT '00:00',
                    allowed_hours_end TEXT DEFAULT '23:59',
                    allowed_days TEXT DEFAULT '1,2,3,4,5,6,7',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Inicjalizacja domyślnych ustawień Telegram jeśli nie istnieją
            cursor.execute("SELECT COUNT(*) FROM telegram_settings")
            if cursor.fetchone()[0] == 0:
                cursor.execute("""
                    INSERT INTO telegram_settings 
                    (notifications_enabled, allowed_hours_start, allowed_hours_end, allowed_days)
                    VALUES (1, '00:00', '23:59', '1,2,3,4,5,6,7')
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
        """
        Tworzy nowy sygnał
        
        Args:
            signal_data: Dane sygnału zawierające:
                - strategy_id (wymagane)
                - signal_type (wymagane)
                - price (wymagane)
                - indicator_values (opcjonalne)
                - message (opcjonalne)
                - ai_analysis_id (opcjonalne) - powiązanie z analizą AI
                - agreement_score (opcjonalne) - scoring zgodności źródeł
                - decision_reason (opcjonalne) - uzasadnienie decyzji
        
        Returns:
            ID utworzonego sygnału
        """
        with self.get_connection() as conn:
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
            
            # Aktualizuj last_signal w strategii (w tej samej transakcji)
            cursor.execute("""
                UPDATE strategies SET last_signal = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (signal_data['strategy_id'],))
            
            return signal_id
    
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
    
    # ===== OPERACJE NA ANALIZACH AI =====
    
    def create_ai_analysis_result(self, data: Dict[str, Any]) -> int:
        """
        Tworzy nowy wynik analizy AI
        
        Args:
            data: Dane analizy zawierające wszystkie pola
        
        Returns:
            ID utworzonego rekordu
        """
        with self.get_connection() as conn:
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
                data.get('timestamp'),
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
        """
        Pobiera wyniki analiz AI
        
        Args:
            symbol: Opcjonalny filtr po symbolu
            limit: Maksymalna liczba wyników
        
        Returns:
            Lista wyników analiz posortowanych od najnowszych
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if symbol:
                cursor.execute("""
                    SELECT * FROM ai_analysis_results
                    WHERE symbol = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (symbol, limit))
            else:
                cursor.execute("""
                    SELECT * FROM ai_analysis_results
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (limit,))
            
            return [self._row_to_ai_analysis_dict(row) for row in cursor.fetchall()]
    
    def get_ai_analysis_by_id(self, analysis_id: int) -> Optional[Dict[str, Any]]:
        """
        Pobiera szczegóły pojedynczej analizy AI
        
        Args:
            analysis_id: ID analizy
        
        Returns:
            Słownik z danymi analizy lub None
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM ai_analysis_results WHERE id = ?
            """, (analysis_id,))
            
            row = cursor.fetchone()
            if row:
                return self._row_to_ai_analysis_dict(row)
            return None
    
    def get_token_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Oblicza statystyki użycia tokenów OpenAI
        
        Args:
            start_date: Data początkowa (format ISO)
            end_date: Data końcowa (format ISO)
        
        Returns:
            Słownik ze statystykami tokenów
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Statystyki ogólne
            if start_date and end_date:
                cursor.execute("""
                    SELECT 
                        COUNT(*) as analyses_count,
                        COALESCE(SUM(tokens_used), 0) as total_tokens,
                        COALESCE(SUM(estimated_cost), 0) as total_cost
                    FROM ai_analysis_results
                    WHERE timestamp BETWEEN ? AND ?
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
            
            # Statystyki dzisiejsze
            cursor.execute("""
                SELECT 
                    COUNT(*) as today_analyses,
                    COALESCE(SUM(tokens_used), 0) as today_tokens,
                    COALESCE(SUM(estimated_cost), 0) as today_cost
                FROM ai_analysis_results
                WHERE DATE(timestamp) = DATE('now')
            """)
            
            today_row = cursor.fetchone()
            
            # Średnia tokenów na analizę
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
    
    # ===== OPERACJE NA KONFIGURACJI ANALIZ =====
    
    def get_analysis_config(self) -> Dict[str, Any]:
        """
        Pobiera aktualną konfigurację analiz
        
        Returns:
            Słownik z konfiguracją
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM analysis_config ORDER BY id DESC LIMIT 1
            """)
            
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
            
            # Jeśli nie ma konfiguracji, zwróć domyślną
            return {
                'id': None,
                'analysis_interval': 15,
                'enabled_symbols': [],
                'notification_threshold': 60,
                'is_active': True,
                'updated_at': None
            }
    
    def update_analysis_config(self, updates: Dict[str, Any]) -> bool:
        """
        Aktualizuje konfigurację analiz
        
        Args:
            updates: Słownik z polami do aktualizacji
        
        Returns:
            True jeśli zaktualizowano
        """
        if not updates:
            return False
        
        # Serializuj enabled_symbols jeśli jest w updates
        if 'enabled_symbols' in updates:
            updates['enabled_symbols'] = json.dumps(updates['enabled_symbols'])
        
        # Dodaj updated_at
        updates['updated_at'] = get_polish_time().isoformat()
        
        # Buduj query dynamicznie
        set_clause = ", ".join([f"{key} = ?" for key in updates.keys()])
        values = list(updates.values())
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Sprawdź czy istnieje konfiguracja
            cursor.execute("SELECT id FROM analysis_config ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            
            if row:
                # Aktualizuj istniejącą
                values.append(row['id'])
                cursor.execute(f"""
                    UPDATE analysis_config SET {set_clause}
                    WHERE id = ?
                """, values)
            else:
                # Utwórz nową
                columns = ", ".join(updates.keys())
                placeholders = ", ".join(["?" for _ in updates])
                cursor.execute(f"""
                    INSERT INTO analysis_config ({columns})
                    VALUES ({placeholders})
                """, list(updates.values()))
            
            return True
    
    def initialize_default_config(self) -> int:
        """
        Tworzy domyślną konfigurację analiz
        
        Returns:
            ID utworzonej konfiguracji
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO analysis_config 
                (analysis_interval, notification_threshold, is_active)
                VALUES (15, 60, 1)
            """)
            
            return cursor.lastrowid
    
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
        
        # Dodaj nowe pola jeśli istnieją w wierszu
        if 'ai_analysis_id' in row.keys():
            result['ai_analysis_id'] = row['ai_analysis_id']
        if 'agreement_score' in row.keys():
            result['agreement_score'] = row['agreement_score']
        if 'decision_reason' in row.keys():
            result['decision_reason'] = row['decision_reason']
        
        return result
    
    def _row_to_ai_analysis_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Konwertuje wiersz na słownik analizy AI"""
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
    
    # ===== LOGI AKTYWNOŚCI =====
    
    def create_activity_log(
        self,
        log_type: str,
        message: str,
        symbol: Optional[str] = None,
        strategy_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        status: str = 'success'
    ) -> int:
        """
        Tworzy nowy log aktywności
        
        Args:
            log_type: Typ logu ('market_data', 'analysis', 'signal', 'telegram')
            message: Wiadomość logu
            symbol: Symbol (opcjonalne)
            strategy_name: Nazwa strategii (opcjonalne)
            details: Szczegóły w formacie dict (opcjonalne)
            status: Status ('success', 'error', 'warning')
        
        Returns:
            ID utworzonego logu
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            timestamp = get_polish_time().isoformat()
            details_json = json.dumps(details) if details else None
            
            cursor.execute("""
                INSERT INTO activity_logs 
                (timestamp, log_type, message, symbol, strategy_name, details, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                timestamp,
                log_type,
                message,
                symbol,
                strategy_name,
                details_json,
                status
            ))
            
            return cursor.lastrowid
    
    def get_recent_activity_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Pobiera ostatnie logi aktywności
        
        Args:
            limit: Maksymalna liczba logów
        
        Returns:
            Lista logów posortowanych od najnowszych
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, timestamp, log_type, message, symbol, strategy_name, details, status
                FROM activity_logs
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
            
            logs = []
            for row in cursor.fetchall():
                log = {
                    'id': row['id'],
                    'timestamp': row['timestamp'],
                    'log_type': row['log_type'],
                    'message': row['message'],
                    'symbol': row['symbol'],
                    'strategy_name': row['strategy_name'],
                    'status': row['status']
                }
                
                # Parsuj details z JSON
                if row['details']:
                    try:
                        log['details'] = json.loads(row['details'])
                    except:
                        log['details'] = {}
                else:
                    log['details'] = {}
                
                logs.append(log)
            
            return logs
    
    def get_activity_logs_by_type(
        self,
        log_type: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Pobiera logi aktywności filtrowane po typie
        
        Args:
            log_type: Typ logu do filtrowania
            limit: Maksymalna liczba logów
        
        Returns:
            Lista logów posortowanych od najnowszych
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, timestamp, log_type, message, symbol, strategy_name, details, status
                FROM activity_logs
                WHERE log_type = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (log_type, limit))
            
            logs = []
            for row in cursor.fetchall():
                log = {
                    'id': row['id'],
                    'timestamp': row['timestamp'],
                    'log_type': row['log_type'],
                    'message': row['message'],
                    'symbol': row['symbol'],
                    'strategy_name': row['strategy_name'],
                    'status': row['status']
                }
                
                # Parsuj details z JSON
                if row['details']:
                    try:
                        log['details'] = json.loads(row['details'])
                    except:
                        log['details'] = {}
                else:
                    log['details'] = {}
                
                logs.append(log)
            
            return logs
    
    # ===== OPERACJE NA USTAWIENIACH TELEGRAM =====
    
    def get_telegram_settings(self) -> Dict[str, Any]:
        """
        Pobiera ustawienia powiadomień Telegram
        
        Returns:
            Słownik z ustawieniami
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM telegram_settings ORDER BY id DESC LIMIT 1
            """)
            
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
        """
        Aktualizuje ustawienia powiadomień Telegram
        
        Args:
            updates: Słownik z polami do aktualizacji
        
        Returns:
            True jeśli zaktualizowano
        """
        if not updates:
            return False
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT id FROM telegram_settings ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            
            if row:
                set_clause = ", ".join([f"{key} = ?" for key in updates.keys()])
                set_clause += ", updated_at = CURRENT_TIMESTAMP"
                values = list(updates.values()) + [row['id']]
                
                cursor.execute(f"""
                    UPDATE telegram_settings SET {set_clause}
                    WHERE id = ?
                """, values)
            else:
                columns = list(updates.keys())
                placeholders = ", ".join(["?" for _ in columns])
                column_names = ", ".join(columns)
                
                cursor.execute(f"""
                    INSERT INTO telegram_settings ({column_names})
                    VALUES ({placeholders})
                """, list(updates.values()))
            
            return True
    
    def set_mute_until(self, muted_until: Optional[str]) -> bool:
        """
        Ustawia wyciszenie powiadomień do określonej daty
        
        Args:
            muted_until: Data do której wyciszyć (format ISO) lub None aby wyłączyć
        
        Returns:
            True jeśli zaktualizowano
        """
        return self.update_telegram_settings({'muted_until': muted_until})
    
    def get_mute_status(self) -> Dict[str, Any]:
        """
        Pobiera status wyciszenia
        
        Returns:
            Słownik z informacją o wyciszeniu
        """
        settings = self.get_telegram_settings()
        
        is_muted = False
        muted_until = settings.get('muted_until')
        
        if muted_until:
            try:
                from datetime import datetime
                muted_date = datetime.fromisoformat(muted_until.replace('Z', '+00:00'))
                is_muted = get_polish_time() < muted_date
            except:
                is_muted = False
        
        return {
            'is_muted': is_muted,
            'muted_until': muted_until,
            'notifications_enabled': settings.get('notifications_enabled', True)
        }
    
    def toggle_telegram_notifications(self) -> bool:
        """
        Przełącza stan powiadomień Telegram (ON/OFF)
        
        Returns:
            Nowy stan (True = włączone, False = wyłączone)
        """
        settings = self.get_telegram_settings()
        new_state = not settings.get('notifications_enabled', True)
        self.update_telegram_settings({'notifications_enabled': new_state})
        return new_state