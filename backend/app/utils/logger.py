"""
System logowania z rotacją plików
"""
import logging
from logging.handlers import RotatingFileHandler
import os
import sys
from datetime import datetime
from pathlib import Path


class ColoredFormatter(logging.Formatter):
    """Formatter z kolorami dla konsoli"""
    
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }
    
    def format(self, record):
        if sys.stdout.isatty():  # Tylko jeśli output to terminal
            levelname = record.levelname
            record.levelname = (
                f"{self.COLORS.get(levelname, '')}"
                f"{levelname}"
                f"{self.COLORS['RESET']}"
            )
        return super().format(record)


def setup_logger(
    name: str = "trading_bot",
    log_file: str = None,
    level: str = "INFO",
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> logging.Logger:
    """
    Konfiguruje logger z rotacją plików
    
    Args:
        name: Nazwa loggera
        log_file: Ścieżka do pliku logów
        level: Poziom logowania
        max_bytes: Maksymalny rozmiar pliku przed rotacją
        backup_count: Liczba backupów
    
    Returns:
        Skonfigurowany logger
    """
    
    # Utwórz logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Usuń istniejące handlery
    logger.handlers.clear()
    
    # Format logów
    log_format = (
        '%(asctime)s | %(levelname)-8s | %(name)s | '
        '%(funcName)s:%(lineno)d | %(message)s'
    )
    date_format = '%Y-%m-%d %H:%M:%S'
    
    # Console handler z kolorami
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_formatter = ColoredFormatter(log_format, datefmt=date_format)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler z rotacją (jeśli podano ścieżkę)
    if log_file:
        # Utwórz katalog jeśli nie istnieje
        log_dir = os.path.dirname(log_file)
        if log_dir:
            Path(log_dir).mkdir(parents=True, exist_ok=True)
        
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(log_format, datefmt=date_format)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        
        logger.info(f"Logowanie do pliku: {log_file}")
    
    # Nie propaguj do root loggera
    logger.propagate = False
    
    return logger


class RequestLogger:
    """Logger dla HTTP requestów"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def log_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration: float,
        client_ip: str = None
    ):
        """Loguje request HTTP"""
        log_data = {
            'method': method,
            'path': path,
            'status': status_code,
            'duration': f'{duration:.3f}s',
            'client': client_ip or 'unknown'
        }
        
        if status_code >= 500:
            self.logger.error(f"Request failed", extra=log_data)
        elif status_code >= 400:
            self.logger.warning(f"Client error", extra=log_data)
        else:
            self.logger.info(f"Request completed", extra=log_data)
    
    def log_error(
        self,
        error: Exception,
        method: str = None,
        path: str = None,
        client_ip: str = None
    ):
        """Loguje błąd podczas requestu"""
        log_data = {
            'error': str(error),
            'error_type': type(error).__name__,
            'method': method,
            'path': path,
            'client': client_ip or 'unknown'
        }
        
        self.logger.error(
            f"Request exception: {str(error)}",
            exc_info=True,
            extra=log_data
        )


class TradingLogger:
    """Logger dla operacji tradingowych"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def log_signal(
        self,
        signal_type: str,
        strategy_name: str,
        symbol: str,
        price: float,
        indicator_values: dict = None
    ):
        """Loguje sygnał tradingowy"""
        log_data = {
            'signal': signal_type,
            'strategy': strategy_name,
            'symbol': symbol,
            'price': price,
            'indicators': indicator_values or {}
        }
        
        emoji = "🟢" if signal_type == "BUY" else "🔴" if signal_type == "SELL" else "⚪"
        
        self.logger.info(
            f"{emoji} Signal: {signal_type} | {symbol} @ {price}",
            extra=log_data
        )
    
    def log_strategy_update(
        self,
        action: str,
        strategy_name: str,
        strategy_id: int = None
    ):
        """Loguje operacje na strategiach"""
        log_data = {
            'action': action,
            'strategy': strategy_name,
            'strategy_id': strategy_id
        }
        
        self.logger.info(
            f"Strategy {action}: {strategy_name}",
            extra=log_data
        )
    
    def log_telegram_send(
        self,
        success: bool,
        message_preview: str,
        error: str = None
    ):
        """Loguje wysyłkę wiadomości Telegram"""
        log_data = {
            'success': success,
            'preview': message_preview[:50],
            'error': error
        }
        
        if success:
            self.logger.info("📱 Telegram message sent", extra=log_data)
        else:
            self.logger.error("📱 Telegram send failed", extra=log_data)


# Przykład użycia
if __name__ == "__main__":
    # Setup
    logger = setup_logger(
        name="test_logger",
        log_file="/tmp/test.log",
        level="DEBUG"
    )
    
    # Test różnych poziomów
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")
    logger.critical("Critical message")
    
    # Test z extra data
    logger.info(
        "User action",
        extra={
            'user_id': 123,
            'action': 'login',
            'ip': '192.168.1.1'
        }
    )
    
    # Test trading logger
    trading_logger = TradingLogger(logger)
    trading_logger.log_signal(
        signal_type="BUY",
        strategy_name="RSI Conservative",
        symbol="BTC/USDT",
        price=45000.00,
        indicator_values={'rsi': 25, 'price': 45000}
    )
