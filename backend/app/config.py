"""
Konfiguracja aplikacji - wszystkie zmienne środowiskowe
"""
from pydantic_settings import BaseSettings
from pydantic import Field, validator
from typing import List, Optional, Dict
from datetime import datetime, timezone, timedelta
import os
import pytz


class Settings(BaseSettings):
    """Konfiguracja aplikacji z walidacją"""
    
    # Telegram Bot
    telegram_bot_token: str = Field(..., description="Token bota z @BotFather")
    telegram_chat_id: str = Field(..., description="ID czatu dla powiadomień")
    
    # OpenAI API (opcjonalne - tylko dla funkcji AI)
    openai_api_key: Optional[str] = Field(
        default=None,
        description="Klucz OpenAI API (opcjonalne - tylko dla funkcji AI)"
    )
    openai_model: str = Field(
        default="gpt-4o-mini",
        description="Model OpenAI (gpt-4o, gpt-4o-mini, gpt-4-turbo, gpt-3.5-turbo)"
    )
    
    # Baza danych
    database_path: str = Field(
        default="/app/data/trading_bot.db",
        description="Ścieżka do bazy SQLite"
    )
    
    # API Security
    api_key: str = Field(..., min_length=32, description="Klucz API (min 32 znaki)")
    
    # Aplikacja
    environment: str = Field(default="production", description="Środowisko: development/production")
    api_host: str = Field(default="0.0.0.0", description="Host API")
    api_port: int = Field(default=8000, ge=1, le=65535, description="Port API")
    check_interval: int = Field(default=15, ge=1, le=1440, description="Interwał sprawdzania (minuty)")
    
    # Logowanie
    log_level: str = Field(default="INFO", description="Poziom logów")
    log_file: str = Field(
        default="/app/data/logs/bot.log",
        description="Ścieżka do pliku logów"
    )
    
    # Backup
    backup_dir: str = Field(
        default="/app/data/backups",
        description="Katalog backupów"
    )
    auto_backup: bool = Field(default=True, description="Automatyczny backup")
    backup_interval: int = Field(default=24, ge=1, description="Interwał backupu (godziny)")
    
    # Rate Limiting
    rate_limit_per_minute: int = Field(
        default=60,
        ge=1,
        le=1000,
        description="Max requestów/minutę"
    )
    
    # CORS
    cors_origins: str = Field(
        default="http://localhost:8080,http://localhost:8081",
        description="Dozwolone origins (oddzielone przecinkiem)"
    )
    
    # Monitoring
    health_check_url: Optional[str] = Field(
        default=None,
        description="URL webhook do healthcheck"
    )
    health_check_interval: int = Field(
        default=300,
        ge=60,
        description="Interwał healthcheck (sekundy)"
    )
    
    # Signal Aggregator - wagi dla źródeł analiz (suma musi wynosić 100)
    aggregator_weight_ai: int = Field(
        default=40,
        ge=0,
        le=100,
        description="Waga dla AI analysis (0-100)"
    )
    aggregator_weight_technical: int = Field(
        default=30,
        ge=0,
        le=100,
        description="Waga dla technical indicators (0-100)"
    )
    aggregator_weight_macro: int = Field(
        default=20,
        ge=0,
        le=100,
        description="Waga dla macro data (0-100)"
    )
    aggregator_weight_news: int = Field(
        default=10,
        ge=0,
        le=100,
        description="Waga dla news sentiment (0-100)"
    )
    
    # Próg zgodności dla powiadomień
    notification_threshold: int = Field(
        default=60,
        ge=0,
        le=100,
        description="Minimalny agreement_score do wysłania powiadomienia (%)"
    )
    
    # Automatyczne analizy AI (Etap 4)
    analysis_interval: int = Field(
        default=30,
        ge=5,
        le=1440,
        description="Interwał automatycznych analiz AI (minuty)"
    )
    analysis_enabled: bool = Field(
        default=True,
        description="Czy automatyczne analizy AI są włączone"
    )
    analysis_symbols_limit: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maksymalna liczba symboli do analizy"
    )
    analysis_timeout: int = Field(
        default=60,
        ge=30,
        le=300,
        description="Timeout dla pojedynczej analizy (sekundy)"
    )
    analysis_pause_between_symbols: int = Field(
        default=2,
        ge=0,
        le=10,
        description="Pauza między analizami symboli (sekundy)"
    )
    
    @validator('log_level')
    def validate_log_level(cls, v):
        """Walidacja poziomu logów"""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'log_level musi być jednym z: {valid_levels}')
        return v.upper()
    
    @validator('environment')
    def validate_environment(cls, v):
        """Walidacja środowiska"""
        valid_envs = ['development', 'production', 'staging']
        if v.lower() not in valid_envs:
            raise ValueError(f'environment musi być jednym z: {valid_envs}')
        return v.lower()
    
    @validator('telegram_bot_token')
    def validate_telegram_token(cls, v):
        """Walidacja formatu tokenu Telegram"""
        if not v or len(v) < 40:
            raise ValueError('telegram_bot_token jest nieprawidłowy')
        if ':' not in v:
            raise ValueError('telegram_bot_token musi zawierać ":"')
        return v
    
    @validator('api_key')
    def validate_api_key(cls, v):
        """Walidacja klucza API"""
        if len(v) < 32:
            raise ValueError('api_key musi mieć minimum 32 znaki. Wygeneruj: openssl rand -hex 32')
        return v
    
    @validator('openai_model')
    def validate_openai_model(cls, v):
        """Walidacja modelu OpenAI"""
        valid_models = [
            'gpt-4o',
            'gpt-4o-mini', 
            'gpt-4-turbo',
            'gpt-4',
            'gpt-3.5-turbo'
        ]
        if v not in valid_models:
            raise ValueError(f'openai_model musi być jednym z: {valid_models}')
        return v
    
    @validator('openai_api_key')
    def validate_openai_key(cls, v):
        """Walidacja klucza OpenAI (opcjonalne)"""
        if v is None or v == '':
            return None
        if not v.startswith('sk-'):
            raise ValueError('openai_api_key musi zaczynać się od "sk-"')
        if len(v) < 20:
            raise ValueError('openai_api_key jest nieprawidłowy (za krótki)')
        return v
    
    @validator('aggregator_weight_news')
    def validate_weights_sum(cls, v, values):
        """Sprawdza czy suma wag dla agregacji wynosi 100"""
        ai_weight = values.get('aggregator_weight_ai', 40)
        tech_weight = values.get('aggregator_weight_technical', 30)
        macro_weight = values.get('aggregator_weight_macro', 20)
        news_weight = v
        
        total = ai_weight + tech_weight + macro_weight + news_weight
        
        if total != 100:
            raise ValueError(
                f'Suma wag dla agregacji musi wynosić 100, obecnie: {total}. '
                f'AI={ai_weight}, Technical={tech_weight}, Macro={macro_weight}, News={news_weight}'
            )
        
        return v
    
    def get_cors_origins_list(self) -> List[str]:
        """Zwraca listę dozwolonych origins"""
        return [origin.strip() for origin in self.cors_origins.split(',')]
    
    def is_development(self) -> bool:
        """Sprawdza czy środowisko developerskie"""
        return self.environment == 'development'
    
    def is_production(self) -> bool:
        """Sprawdza czy środowisko produkcyjne"""
        return self.environment == 'production'
    
    def get_aggregator_weights(self) -> Dict[str, int]:
        """Zwraca wagi dla signal aggregator jako słownik"""
        return {
            "ai": self.aggregator_weight_ai,
            "technical": self.aggregator_weight_technical,
            "macro": self.aggregator_weight_macro,
            "news": self.aggregator_weight_news
        }
    
    class Config:
        env_file = ['.env', '../.env']
        env_file_encoding = 'utf-8'
        case_sensitive = False


# Singleton instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Pobiera singleton instancję ustawień"""
    global _settings
    if _settings is None:
        try:
            _settings = Settings()
        except Exception as e:
            print(f"❌ BŁĄD KONFIGURACJI: {e}")
            print("\n💡 Upewnij się, że:")
            print("1. Plik .env istnieje w katalogu głównym")
            print("2. Wszystkie wymagane zmienne są ustawione")
            print("3. Skopiuj .env.example do .env i uzupełnij wartości")
            raise
    return _settings


# Wczytaj ustawienia przy starcie
try:
    settings = get_settings()
    print(f"✅ Konfiguracja wczytana: {settings.environment}")
except Exception:
    print("⚠️  Konfiguracja nie może zostać wczytana")
    settings = None


def get_polish_time() -> datetime:
    """Zwraca aktualny czas w strefie czasowej Warszawy (Europe/Warsaw)
    
    Automatycznie uwzględnia czas letni (CEST, UTC+2) i zimowy (CET, UTC+1)
    """
    warsaw_tz = pytz.timezone('Europe/Warsaw')
    return datetime.now(warsaw_tz)
