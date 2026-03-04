"""
Router dla endpointów strategii
"""
from fastapi import APIRouter, Depends, HTTPException, Path, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from typing import Dict, Any

from .dependencies import verify_api_key, get_strategy_service, settings
from ..models.models import StrategyCreate, StrategyUpdate
from ..utils.logger import setup_logger

limiter = Limiter(key_func=get_remote_address)
logger = setup_logger(name="trading_bot", log_file=settings.log_file, level=settings.log_level)

router = APIRouter(prefix="/strategies", tags=["Strategies"])


@router.get("", dependencies=[Depends(verify_api_key)])
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def get_strategies(
    request: Request,
    service=Depends(get_strategy_service)
) -> Dict[str, Any]:
    """Pobiera listę wszystkich strategii.

    Returns:
        Słownik z kluczem "strategies" zawierającym listę strategii.

    Raises:
        HTTPException: 500 przy błędzie serwera.
    """
    try:
        strategies = service.get_all_strategies()
        return {"strategies": strategies}
    except Exception as e:
        logger.error(f"Error getting strategies: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", dependencies=[Depends(verify_api_key)])
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def create_strategy(
    request: Request,
    strategy: StrategyCreate,
    service=Depends(get_strategy_service)
) -> Dict[str, Any]:
    """Tworzy nową strategię.

    Args:
        strategy: Dane strategii (StrategyCreate) – walidowane przez Pydantic.

    Returns:
        Słownik z "id" i "message".

    Raises:
        HTTPException: 500 przy błędzie serwera.
    """
    try:
        result = service.create_strategy(strategy)
        logger.info(f"Strategy created: {strategy.name}")
        return result
    except Exception as e:
        logger.error(f"Error creating strategy: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{strategy_id}", dependencies=[Depends(verify_api_key)])
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def get_strategy(
    request: Request,
    strategy_id: int = Path(..., gt=0, description="ID strategii"),
    service=Depends(get_strategy_service)
) -> Dict[str, Any]:
    """Pobiera pojedynczą strategię po ID.

    Args:
        strategy_id: ID strategii (większe od 0).

    Returns:
        Słownik z kluczem "strategy" i danymi strategii.

    Raises:
        StrategyNotFoundException: Obsługiwany globalnie jako HTTP 404.
    """
    strategy = service.get_strategy(strategy_id)
    return {"strategy": strategy}


@router.put("/{strategy_id}", dependencies=[Depends(verify_api_key)])
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def update_strategy(
    request: Request,
    strategy_id: int = Path(..., gt=0, description="ID strategii"),
    strategy: StrategyUpdate = ...,
    service=Depends(get_strategy_service)
) -> Dict[str, Any]:
    """Aktualizuje istniejącą strategię.

    Args:
        strategy_id: ID strategii (większe od 0).
        strategy: Pola do aktualizacji (StrategyUpdate) – tylko podane pola są zmieniane.

    Returns:
        Słownik z "message".

    Raises:
        StrategyNotFoundException: Obsługiwany globalnie jako HTTP 404.
        HTTPException: 500 przy błędzie serwera.
    """
    try:
        result = service.update_strategy(strategy_id, strategy)
        logger.info(f"Strategy updated: {strategy_id}")
        return result
    except Exception as e:
        logger.error(f"Error updating strategy: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{strategy_id}", dependencies=[Depends(verify_api_key)])
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def delete_strategy(
    request: Request,
    strategy_id: int = Path(..., gt=0, description="ID strategii"),
    service=Depends(get_strategy_service)
) -> Dict[str, Any]:
    """Usuwa strategię po ID.

    Args:
        strategy_id: ID strategii (większe od 0).

    Returns:
        Słownik z "message".

    Raises:
        StrategyNotFoundException: Obsługiwany globalnie jako HTTP 404.
        HTTPException: 500 przy błędzie serwera.
    """
    try:
        result = service.delete_strategy(strategy_id)
        logger.info(f"Strategy deleted: {strategy_id}")
        return result
    except Exception as e:
        logger.error(f"Error deleting strategy: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
