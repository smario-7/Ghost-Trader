"""
Migracje schematu bazy danych SQLite.
Funkcja run_migrations(conn) tworzy tabele, indeksy i domyślne wpisy.
"""
import sqlite3


def run_migrations(conn: sqlite3.Connection) -> None:
    """Wykonuje pełną inicjalizację schematu bazy (tabele, indeksy, domyślne dane)."""
    cursor = conn.cursor()

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

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_activity_logs_timestamp 
        ON activity_logs(timestamp DESC)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_activity_logs_type 
        ON activity_logs(log_type)
    """)

    cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS update_strategy_timestamp 
        AFTER UPDATE ON strategies
        FOR EACH ROW
        BEGIN
            UPDATE strategies SET updated_at = CURRENT_TIMESTAMP
            WHERE id = NEW.id;
        END
    """)

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

    cursor.execute("PRAGMA table_info(signals)")
    existing_columns = [row[1] for row in cursor.fetchall()]
    if 'ai_analysis_id' not in existing_columns:
        cursor.execute("ALTER TABLE signals ADD COLUMN ai_analysis_id INTEGER")
    if 'agreement_score' not in existing_columns:
        cursor.execute("ALTER TABLE signals ADD COLUMN agreement_score INTEGER")
    if 'decision_reason' not in existing_columns:
        cursor.execute("ALTER TABLE signals ADD COLUMN decision_reason TEXT")

    cursor.execute("SELECT COUNT(*) FROM analysis_config")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO analysis_config 
            (analysis_interval, notification_threshold, is_active)
            VALUES (15, 60, 1)
        """)

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

    cursor.execute("SELECT COUNT(*) FROM telegram_settings")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO telegram_settings 
            (notifications_enabled, allowed_hours_start, allowed_hours_end, allowed_days)
            VALUES (1, '00:00', '23:59', '1,2,3,4,5,6,7')
        """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scheduler_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_check_enabled BOOLEAN DEFAULT 1,
            ai_analysis_enabled BOOLEAN DEFAULT 1,
            signal_check_interval INTEGER DEFAULT 15,
            ai_analysis_interval INTEGER DEFAULT 30,
            signal_hours_start TEXT DEFAULT '00:00',
            signal_hours_end TEXT DEFAULT '23:59',
            ai_hours_start TEXT DEFAULT '00:00',
            ai_hours_end TEXT DEFAULT '23:59',
            signal_active_days TEXT DEFAULT '1,2,3,4,5,6,7',
            ai_active_days TEXT DEFAULT '1,2,3,4,5,6,7',
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("SELECT COUNT(*) FROM scheduler_config")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO scheduler_config 
            (signal_check_enabled, ai_analysis_enabled, signal_check_interval, ai_analysis_interval,
             signal_hours_start, signal_hours_end, ai_hours_start, ai_hours_end,
             signal_active_days, ai_active_days)
            VALUES (1, 1, 15, 30, '00:00', '23:59', '00:00', '23:59', '1,2,3,4,5,6,7', '1,2,3,4,5,6,7')
        """)
