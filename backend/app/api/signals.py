"""
Router dla endpointów sygnałów
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from slowapi import Limiter
from slowapi.util import get_remote_address
from typing import Dict, Any

from .dependencies import verify_api_key, get_strategy_service, settings
from ..utils.logger import setup_logger

limiter = Limiter(key_func=get_remote_address)
logger = setup_logger(name="trading_bot", log_file=settings.log_file, level=settings.log_level)

router = APIRouter(tags=["Signals"])


@router.post("/check-signals", dependencies=[Depends(verify_api_key)])
@limiter.limit("10/minute")
async def check_signals(
    request: Request,
    service=Depends(get_strategy_service)
) -> Dict[str, Any]:
    """Sprawdza sygnały dla wszystkich aktywnych strategii"""
    try:
        results = await service.check_all_signals()
        logger.info(f"Signals checked: {len(results)} strategies")
        return {"results": results}
    except Exception as e:
        logger.error(f"Error checking signals: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/signals/recent", dependencies=[Depends(verify_api_key)])
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def get_recent_signals(
    request: Request,
    limit: int = Query(50, ge=1, le=500),
    service=Depends(get_strategy_service)
) -> Dict[str, Any]:
    """Pobiera ostatnie sygnały"""
    try:
        signals = service.get_recent_signals(limit)
        return {"signals": signals}
    except Exception as e:
        logger.error(f"Error getting recent signals: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/signals/strategy/{strategy_id}", dependencies=[Depends(verify_api_key)])
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def get_strategy_signals(
    request: Request,
    strategy_id: int,
    limit: int = Query(100, ge=1, le=500),
    service=Depends(get_strategy_service)
) -> Dict[str, Any]:
    """Pobiera sygnały dla konkretnej strategii"""
    try:
        signals = service.get_strategy_signals(strategy_id, limit)
        return {"signals": signals}
    except Exception as e:
        logger.error(f"Error getting signals for strategy {strategy_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
