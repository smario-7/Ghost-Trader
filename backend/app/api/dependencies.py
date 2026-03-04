"""
Wspólne zależności dla API routerów
"""
from __future__ import annotations

from fastapi import Depends, HTTPException, Security, Query, Request
from fastapi.security import APIKeyHeader
from typing import TYPE_CHECKING, Optional

from ..config import get_settings
from ..utils.logger import setup_logger
from ..utils.database import Database
from ..services.telegram_service import TelegramService
from ..services.strategy_service import StrategyService

if TYPE_CHECKING:
    from ..services.auto_analysis_scheduler import AutoAnalysisScheduler
    from ..services.data_collection_service import MacroDataService
    from ..services.signal_aggregator_service import SignalAggregatorService


settings = get_settings()
logger = setup_logger(
    name="trading_bot",
    log_file=settings.log_file,
    level=settings.log_level
)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(
    request: Request = None,
    api_key: str = Security(api_key_header),
    api_key_query: Optional[str] = Query(None, alias="api_key")
) -> str:
    """
    Weryfikacja klucza API z nagłówka lub parametru URL.
    Parametr URL jest używany dla SSE (EventSource nie obsługuje custom headers).
    """
    if request and request.method == "OPTIONS":
        return api_key_query or ""
    
    key = api_key or api_key_query
    
    if not key:
        logger.warning("Brak klucza API w żądaniu (header i query)")
        raise HTTPException(
            status_code=403,
            detail="Brak klucza API. Dodaj header X-API-Key lub parametr ?api_key="
        )
    if key != settings.api_key:
        logger.warning(f"Nieprawidłowy klucz API: {key[:10]}...")
        raise HTTPException(
            status_code=403,
            detail="Nieprawidłowy klucz API"
        )
    return key


def get_database() -> Database:
    """Zwraca instancję bazy danych.

    Returns:
        Database skonfigurowana z ścieżką z ustawień.
    """
    return Database(settings.database_path)


def get_telegram_service() -> TelegramService:
    """Zwraca instancję serwisu Telegram.

    Returns:
        TelegramService z tokenem i chat_id z ustawień.
    """
    db = Database(settings.database_path)
    return TelegramService(
        bot_token=settings.telegram_bot_token,
        chat_id=settings.telegram_chat_id,
        database=db
    )


def get_strategy_service(
    db: Database = Depends(get_database),
    telegram: TelegramService = Depends(get_telegram_service)
) -> StrategyService:
    """Zwraca instancję serwisu strategii.

    Args:
        db: Instancja bazy (wstrzykiwana).
        telegram: Instancja serwisu Telegram (wstrzykiwana).

    Returns:
        StrategyService.
    """
    return StrategyService(db, telegram)


def get_auto_scheduler(
    db: Database = Depends(get_database),
    telegram: TelegramService = Depends(get_telegram_service),
) -> "AutoAnalysisScheduler":
    """Zwraca instancję AutoAnalysisScheduler z interwałem z bazy (bez restartu)."""
    from ..services.auto_analysis_scheduler import AutoAnalysisScheduler
    config = db.get_scheduler_config()
    interval = config.get("ai_analysis_interval") or settings.analysis_interval
    return AutoAnalysisScheduler(
        database=db,
        telegram=telegram,
        interval_minutes=interval
    )


def get_data_collection_service() -> "MacroDataService":
    """Zwraca instancję MacroDataService (dane makro).

    Returns:
        MacroDataService.
    """
    from ..services.data_collection_service import MacroDataService
    return MacroDataService()


def get_signal_aggregator(
    db: Database = Depends(get_database),
) -> "SignalAggregatorService":
    """Zwraca instancję SignalAggregatorService (agregacja sygnałów AI).

    Args:
        db: Instancja bazy (wstrzykiwana).

    Returns:
        SignalAggregatorService.
    """
    from ..services.signal_aggregator_service import SignalAggregatorService
    return SignalAggregatorService(database=db)
