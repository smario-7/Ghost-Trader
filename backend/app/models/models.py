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
    symbol: str = Field(..., min_length=1, max_length=20, description="Symbol (np. EUR/USD)")
    timeframe: str = Field(default="1h", description="Interwał czasowy")
    is_active: bool = Field(default=True, description="Czy strategia jest aktywna")
    
    @validator('symbol')
    def validate_symbol(cls, v):
        """Walidacja symbolu"""
        v = v.upper().strip()
        if '/' not in v:
            raise ValueError('Symbol musi zawierać "/" (np. EUR/USD)')
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
    ai_analysis_id: Optional[int] = Field(None, description="ID powiązanej analizy AI")
    agreement_score: Optional[int] = Field(None, ge=0, le=100, description="Scoring zgodności")
    decision_reason: Optional[str] = Field(None, description="Uzasadnienie decyzji")
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


class SchedulerConfigUpdate(BaseModel):
    """Model aktualizacji konfiguracji schedulera (wszystkie pola opcjonalne)."""
    signal_check_enabled: Optional[bool] = None
    ai_analysis_enabled: Optional[bool] = None
    signal_check_interval: Optional[int] = Field(None, ge=1, le=1440, description="Interwał sprawdzania sygnałów (minuty)")
    ai_analysis_interval: Optional[int] = Field(None, ge=5, le=1440, description="Interwał analiz AI (minuty)")
    signal_hours_start: Optional[str] = Field(None, pattern=r"^([01]\d|2[0-3]):([0-5]\d)$", description="Godzina startu okna sygnałów (HH:MM)")
    signal_hours_end: Optional[str] = Field(None, pattern=r"^([01]\d|2[0-3]):([0-5]\d)$", description="Godzina końca okna sygnałów (HH:MM)")
    ai_hours_start: Optional[str] = Field(None, pattern=r"^([01]\d|2[0-3]):([0-5]\d)$", description="Godzina startu okna analiz AI (HH:MM)")
    ai_hours_end: Optional[str] = Field(None, pattern=r"^([01]\d|2[0-3]):([0-5]\d)$", description="Godzina końca okna analiz AI (HH:MM)")
    signal_active_days: Optional[str] = Field(None, description="Dni aktywności sygnałów: 1,2,3,4,5,6,7 (1=poniedziałek)")
    ai_active_days: Optional[str] = Field(None, description="Dni aktywności analiz AI: 1,2,3,4,5,6,7")

    @validator("signal_active_days", "ai_active_days")
    def validate_days_format(cls, v):
        if v is None or v == "":
            return v
        try:
            days = [int(d.strip()) for d in v.split(",")]
            if not all(1 <= d <= 7 for d in days):
                raise ValueError("Każdy dzień musi być od 1 do 7")
            return v
        except (ValueError, AttributeError):
            raise ValueError("Format: '1,2,3,4,5,6,7' (dni 1-7)")


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


class AIAnalysisResult(BaseModel):
    """Model wyniku analizy AI"""
    id: Optional[int] = None
    symbol: str = Field(..., description="Symbol (np. EUR/USD)")
    timeframe: str = Field(..., description="Interwał czasowy")
    timestamp: Optional[datetime] = None
    
    ai_recommendation: Optional[str] = Field(None, description="Rekomendacja AI (BUY/SELL/HOLD)")
    ai_confidence: Optional[int] = Field(None, ge=0, le=100, description="Pewność AI (0-100)")
    ai_reasoning: Optional[str] = Field(None, description="Uzasadnienie AI")
    
    technical_signal: Optional[str] = Field(None, description="Sygnał techniczny")
    technical_confidence: Optional[int] = Field(None, ge=0, le=100, description="Pewność wskaźników")
    technical_details: Optional[str] = Field(None, description="Szczegóły wskaźników (JSON)")
    
    macro_signal: Optional[str] = Field(None, description="Sygnał makro")
    macro_impact: Optional[str] = Field(None, description="Wpływ makro")
    
    news_sentiment: Optional[str] = Field(None, description="Sentiment newsów")
    news_score: Optional[int] = Field(None, ge=0, le=100, description="Scoring newsów")
    
    final_signal: Optional[str] = Field(None, description="Finalny sygnał (BUY/SELL/HOLD/NO_SIGNAL)")
    agreement_score: Optional[int] = Field(None, ge=0, le=100, description="Scoring zgodności (%)")
    voting_details: Optional[str] = Field(None, description="Szczegóły głosowania (JSON)")
    
    tokens_used: Optional[int] = Field(None, ge=0, description="Użyte tokeny OpenAI")
    estimated_cost: Optional[float] = Field(None, ge=0, description="Szacowany koszt ($)")
    
    decision_reason: Optional[str] = Field(None, description="Uzasadnienie decyzji")
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class AnalysisConfig(BaseModel):
    """Model konfiguracji analiz"""
    id: Optional[int] = None
    analysis_interval: int = Field(
        default=15,
        ge=5,
        le=1440,
        description="Interwał analiz (minuty)"
    )
    enabled_symbols: Optional[List[str]] = Field(
        default_factory=list,
        description="Lista włączonych symboli"
    )
    notification_threshold: int = Field(
        default=60,
        ge=0,
        le=100,
        description="Próg powiadomień (min agreement_score)"
    )
    is_active: bool = Field(default=True, description="Czy automatyczne analizy są włączone")
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class TokenStatistics(BaseModel):
    """Model statystyk tokenów OpenAI"""
    total_tokens: int = Field(default=0, description="Łączna liczba tokenów")
    total_cost: float = Field(default=0.0, description="Łączny koszt ($)")
    analyses_count: int = Field(default=0, description="Liczba analiz")
    avg_tokens_per_analysis: int = Field(default=0, description="Średnia tokenów/analiza")
    today_tokens: int = Field(default=0, description="Tokeny dzisiaj")
    today_cost: float = Field(default=0.0, description="Koszt dzisiaj ($)")
    today_analyses: int = Field(default=0, description="Analiz dzisiaj")
    
    class Config:
        from_attributes = True


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


# ===== ETAP 5: Nowe modele dla API =====

class AnalysisResultsFilter(BaseModel):
    """Filtry dla wyników analiz AI"""
    symbol: Optional[str] = Field(None, description="Filtruj po symbolu (np. EUR/USD)")
    limit: int = Field(default=50, ge=1, le=200, description="Maksymalna liczba wyników")
    signal_type: Optional[str] = Field(
        None,
        description="Filtruj po typie sygnału (BUY/SELL/HOLD/NO_SIGNAL)"
    )
    min_agreement: Optional[int] = Field(
        None,
        ge=0,
        le=100,
        description="Minimalny agreement_score (0-100)"
    )
    
    @validator('signal_type')
    def validate_signal_type(cls, v):
        """Walidacja typu sygnału"""
        if v is not None:
            valid_types = ['BUY', 'SELL', 'HOLD', 'NO_SIGNAL']
            if v not in valid_types:
                raise ValueError(f'signal_type musi być jednym z: {valid_types}')
        return v


class AnalysisConfigUpdate(BaseModel):
    """Model do aktualizacji konfiguracji analiz"""
    analysis_interval: Optional[int] = Field(
        None,
        ge=5,
        le=1440,
        description="Interwał analiz w minutach (5-1440)"
    )
    enabled_symbols: Optional[List[str]] = Field(
        None,
        max_items=50,
        description="Lista włączonych symboli (max 50)"
    )
    notification_threshold: Optional[int] = Field(
        None,
        ge=0,
        le=100,
        description="Próg powiadomień (0-100%)"
    )
    is_active: Optional[bool] = Field(
        None,
        description="Czy automatyczne analizy są włączone"
    )
    
    @validator('enabled_symbols')
    def validate_symbols(cls, v):
        """Walidacja listy symboli"""
        if v is not None:
            for symbol in v:
                if '/' not in symbol:
                    raise ValueError(f'Symbol {symbol} musi zawierać "/" (np. EUR/USD)')
        return v


class TriggerAnalysisRequest(BaseModel):
    """Request do ręcznego uruchomienia analiz"""
    symbols: Optional[List[str]] = Field(
        None,
        max_items=50,
        description="Lista symboli do analizy (max 50)"
    )
    timeframe: str = Field(
        default="1h",
        description="Interwał czasowy (1m, 5m, 15m, 30m, 1h, 4h, 1d)"
    )
    
    @validator('symbols')
    def validate_symbols(cls, v):
        """Walidacja listy symboli"""
        if v is not None:
            for symbol in v:
                if '/' not in symbol:
                    raise ValueError(f'Symbol {symbol} musi zawierać "/" (np. EUR/USD)')
        return v
    
    @validator('timeframe')
    def validate_timeframe(cls, v):
        """Walidacja timeframe"""
        valid_timeframes = ['1m', '5m', '15m', '30m', '1h', '4h', '1d']
        if v not in valid_timeframes:
            raise ValueError(f'Timeframe musi być jednym z: {valid_timeframes}')
        return v
