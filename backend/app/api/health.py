"""
Router dla health check i podstawowych endpointów
"""
from fastapi import APIRouter, Depends, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from typing import Dict, Any

from .dependencies import verify_api_key, get_database, get_telegram_service, settings
from ..config import get_polish_time
from ..models.models import HealthResponse
from ..utils.logger import setup_logger

limiter = Limiter(key_func=get_remote_address)
logger = setup_logger(name="trading_bot", log_file=settings.log_file, level=settings.log_level)

router = APIRouter(tags=["Health"])


@router.get("/")
async def root() -> Dict[str, Any]:
    """Root endpoint"""
    return {
        "name": "Trading Bot API",
        "version": "2.0.0",
        "status": "running"
    }


@router.get("/test")
async def test_endpoint() -> Dict[str, Any]:
    """Testowy endpoint do weryfikacji połączenia"""
    return {
        "status": "ok",
        "message": "Backend odpowiada poprawnie",
        "timestamp": get_polish_time().isoformat()
    }


@router.get("/test-activity-logs", dependencies=[Depends(verify_api_key)])
async def test_activity_logs_endpoint() -> Dict[str, Any]:
    """Testowy endpoint do weryfikacji routingu activity-logs"""
    return {
        "status": "ok",
        "message": "Activity logs endpoint routing works",
        "timestamp": get_polish_time().isoformat()
    }


@router.get("/health", response_model=HealthResponse)
@limiter.limit("10/minute")
async def health_check(request: Request) -> HealthResponse:
    """Health check endpoint"""
    from .dependencies import get_database, get_telegram_service
    try:
        db = get_database()
        db_status = db.check_connection()
        
        telegram = get_telegram_service()
        telegram_status = await telegram.check_connection()
        
        return HealthResponse(
            status="healthy" if (db_status and telegram_status) else "unhealthy",
            timestamp=get_polish_time(),
            database=db_status,
            telegram=telegram_status,
            environment=settings.environment
        )
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return HealthResponse(
            status="unhealthy",
            timestamp=get_polish_time(),
            database=False,
            telegram=False,
            environment=settings.environment
        )
