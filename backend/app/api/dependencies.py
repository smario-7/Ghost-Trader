"""
Wspólne zależności dla API routerów
"""
from fastapi import Depends, HTTPException, Security, Query, Request
from fastapi.security import APIKeyHeader
from typing import Optional

from ..config import get_settings
from ..utils.logger import setup_logger
from ..utils.database import Database
from ..services.telegram_service import TelegramService
from ..services.strategy_service import StrategyService


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
    """Zwraca instancję bazy danych"""
    return Database(settings.database_path)


def get_telegram_service() -> TelegramService:
    """Zwraca instancję serwisu Telegram"""
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
    """Zwraca instancję serwisu strategii"""
    return StrategyService(db, telegram)


def get_auto_scheduler(
    db: Database = Depends(get_database),
    telegram: TelegramService = Depends(get_telegram_service)):
    """Zwraca instancję AutoAnalysisScheduler"""
    from ..services.auto_analysis_scheduler import AutoAnalysisScheduler
    return AutoAnalysisScheduler(
        database=db,
        telegram=telegram,
        interval_minutes=settings.analysis_interval
    )


def get_data_collection_service():
    """Zwraca instancję MacroDataService"""
    from ..services.data_collection_service import MacroDataService
    return MacroDataService()


def get_signal_aggregator(
    db: Database = Depends(get_database)):
    """Zwraca instancję SignalAggregatorService"""
    from ..services.signal_aggregator_service import SignalAggregatorService
    return SignalAggregatorService(database=db)
