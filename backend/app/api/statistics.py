"""
Router dla endpointów statystyk
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from typing import Dict, Any

from .dependencies import verify_api_key, get_strategy_service, get_telegram_service, settings
from ..utils.logger import setup_logger

limiter = Limiter(key_func=get_remote_address)
logger = setup_logger(name="trading_bot", log_file=settings.log_file, level=settings.log_level)

router = APIRouter(tags=["Statistics"])


@router.get("/statistics", dependencies=[Depends(verify_api_key)])
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def get_statistics(
    request: Request,
    service=Depends(get_strategy_service)
) -> Dict[str, Any]:
    """Pobiera statystyki systemu (strategie, sygnały, uptime).

    Returns:
        Słownik ze statystykami.

    Raises:
        HTTPException: 500 przy błędzie serwera.
    """
    try:
        stats = service.get_statistics()
        return stats
    except Exception as e:
        logger.error(f"Error getting statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test-telegram", dependencies=[Depends(verify_api_key)])
@limiter.limit("5/minute")
async def test_telegram(
    request: Request,
    telegram=Depends(get_telegram_service)
) -> Dict[str, Any]:
    """Wysyła testową wiadomość na Telegram.

    Returns:
        Słownik z "success" i "message".

    Raises:
        HTTPException: 500 przy błędzie wysyłki.
    """
    try:
        result = await telegram.send_message("🧪 Test połączenia - Trading Bot")
        return {"success": result, "message": "Wiadomość wysłana"}
    except Exception as e:
        logger.error(f"Error testing telegram: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
