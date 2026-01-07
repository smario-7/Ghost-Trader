"""
Modele danych z walidacją Pydantic
"""
from pydantic import BaseModel, Field, validator
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum


class SignalType(str, Enum):
    """Typy sygnałów"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class StrategyType(str, Enum):
    """Typy strategii"""
    RSI = "RSI"
    MACD = "MACD"
    BOLLINGER = "BOLLINGER_BANDS"
    MOVING_AVERAGE = "MOVING_AVERAGE"
    CUSTOM = "CUSTOM"


class StrategyBase(BaseModel):
    """Bazowy model strategii"""
    name: str = Field(..., min_length=1, max_length=100, description="Nazwa strategii")
    strategy_type: StrategyType = Field(..., description="Typ strategii")
    parameters: Dict[str, Any] = Field(..., description="Parametry strategii")
    symbol: str = Field(..., min_length=1, max_length=20, description="Symbol (np. BTC/USDT)")
    timeframe: str = Field(default="1h", description="Interwał czasowy")
    is_active: bool = Field(default=True, description="Czy strategia jest aktywna")
    
    @validator('symbol')
    def validate_symbol(cls, v):
        """Walidacja symbolu"""
        v = v.upper().strip()
        if '/' not in v:
            raise ValueError('Symbol musi zawierać "/" (np. BTC/USDT)')
        parts = v.split('/')
        if len(parts) != 2:
            raise ValueError('Nieprawidłowy format symbolu')
        if not all(part.isalnum() for part in parts):
            raise ValueError('Symbol może zawierać tylko litery i cyfry')
        return v
    
    @validator('timeframe')
    def validate_timeframe(cls, v):
        """Walidacja timeframe"""
        valid_timeframes = ['1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w']
        if v not in valid_timeframes:
            raise ValueError(f'Timeframe musi być jednym z: {valid_timeframes}')
        return v
    
    @validator('parameters')
    def validate_parameters(cls, v, values):
        """Walidacja parametrów w zależności od typu strategii"""
        if 'strategy_type' not in values:
            return v
        
        strategy_type = values['strategy_type']
        
        if strategy_type == StrategyType.RSI:
            required = ['period', 'overbought', 'oversold']
            if not all(key in v for key in required):
                raise ValueError(f'RSI wymaga: {required}')
            if not (0 < v.get('overbought', 0) <= 100):
                raise ValueError('overbought musi być między 0 a 100')
            if not (0 < v.get('oversold', 0) <= 100):
                raise ValueError('oversold musi być między 0 a 100')
            if v.get('oversold', 0) >= v.get('overbought', 0):
                raise ValueError('oversold musi być mniejsze niż overbought')
        
        elif strategy_type == StrategyType.MACD:
            required = ['fast_period', 'slow_period', 'signal_period']
            if not all(key in v for key in required):
                raise ValueError(f'MACD wymaga: {required}')
        
        elif strategy_type == StrategyType.BOLLINGER:
            required = ['period', 'std_dev']
            if not all(key in v for key in required):
                raise ValueError(f'Bollinger Bands wymaga: {required}')
        
        elif strategy_type == StrategyType.MOVING_AVERAGE:
            required = ['short_period', 'long_period']
            if not all(key in v for key in required):
                raise ValueError(f'Moving Average wymaga: {required}')
        
        return v


class StrategyCreate(StrategyBase):
    """Model do tworzenia strategii"""
    pass


class StrategyUpdate(BaseModel):
    """Model do aktualizacji strategii"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    strategy_type: Optional[StrategyType] = None
    parameters: Optional[Dict[str, Any]] = None
    symbol: Optional[str] = Field(None, min_length=1, max_length=20)
    timeframe: Optional[str] = None
    is_active: Optional[bool] = None


class StrategyResponse(StrategyBase):
    """Model odpowiedzi strategii"""
    id: int
    created_at: datetime
    updated_at: datetime
    last_signal: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class SignalCreate(BaseModel):
    """Model do tworzenia sygnału"""
    strategy_id: int = Field(..., gt=0)
    signal_type: SignalType
    price: float = Field(..., gt=0)
    indicator_values: Dict[str, Any] = Field(default_factory=dict)
    message: Optional[str] = None


class SignalResponse(BaseModel):
    """Model odpowiedzi sygnału"""
    id: int
    strategy_id: int
    strategy_name: str
    signal_type: SignalType
    price: float
    symbol: str
    indicator_values: Dict[str, Any]
    message: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class HealthResponse(BaseModel):
    """Model odpowiedzi health check"""
    status: str = Field(..., description="healthy lub unhealthy")
    timestamp: datetime
    database: bool = Field(..., description="Status bazy danych")
    telegram: bool = Field(..., description="Status Telegram Bot")
    environment: str = Field(..., description="Środowisko")
    
    @validator('status')
    def validate_status(cls, v):
        if v not in ['healthy', 'unhealthy']:
            raise ValueError('Status musi być: healthy lub unhealthy')
        return v


class BackupResponse(BaseModel):
    """Model odpowiedzi backupu"""
    success: bool
    backup_file: Optional[str] = None
    timestamp: datetime
    size_bytes: Optional[int] = None
    message: str


class TelegramMessage(BaseModel):
    """Model wiadomości Telegram"""
    text: str = Field(..., min_length=1, max_length=4096, description="Treść wiadomości")
    parse_mode: Optional[str] = Field(default="HTML", description="Format parsowania")
    
    @validator('parse_mode')
    def validate_parse_mode(cls, v):
        valid_modes = ['HTML', 'Markdown', 'MarkdownV2', None]
        if v not in valid_modes:
            raise ValueError(f'parse_mode musi być jednym z: {valid_modes}')
        return v


class ErrorResponse(BaseModel):
    """Model odpowiedzi błędu"""
    detail: str
    error_code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_schema_extra = {
            "example": {
                "detail": "Nieprawidłowy klucz API",
                "error_code": "AUTH_001",
                "timestamp": "2025-01-07T22:00:00"
            }
        }


class StatisticsResponse(BaseModel):
    """Model statystyk"""
    total_strategies: int
    active_strategies: int
    total_signals: int
    signals_today: int
    buy_signals: int
    sell_signals: int
    last_signal_time: Optional[datetime]
    uptime: str


# Presety strategii
class StrategyPresets:
    """Gotowe presety strategii"""
    
    RSI_CONSERVATIVE = {
        "name": "RSI Conservative",
        "strategy_type": StrategyType.RSI,
        "parameters": {
            "period": 14,
            "overbought": 70,
            "oversold": 30
        },
        "timeframe": "1h"
    }
    
    RSI_AGGRESSIVE = {
        "name": "RSI Aggressive",
        "strategy_type": StrategyType.RSI,
        "parameters": {
            "period": 14,
            "overbought": 80,
            "oversold": 20
        },
        "timeframe": "15m"
    }
    
    MACD_DEFAULT = {
        "name": "MACD Standard",
        "strategy_type": StrategyType.MACD,
        "parameters": {
            "fast_period": 12,
            "slow_period": 26,
            "signal_period": 9
        },
        "timeframe": "1h"
    }
    
    BOLLINGER_DEFAULT = {
        "name": "Bollinger Bands Standard",
        "strategy_type": StrategyType.BOLLINGER,
        "parameters": {
            "period": 20,
            "std_dev": 2
        },
        "timeframe": "1h"
    }
    
    @classmethod
    def get_all_presets(cls) -> List[Dict[str, Any]]:
        """Zwraca wszystkie presety"""
        return [
            cls.RSI_CONSERVATIVE,
            cls.RSI_AGGRESSIVE,
            cls.MACD_DEFAULT,
            cls.BOLLINGER_DEFAULT
        ]
