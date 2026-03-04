"""
Router dla endpointów schedulera
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from typing import Dict, Any

from .dependencies import verify_api_key, get_database, settings
from ..models.models import SchedulerConfigUpdate
from ..utils.logger import setup_logger

limiter = Limiter(key_func=get_remote_address)
logger = setup_logger(name="trading_bot", log_file=settings.log_file, level=settings.log_level)

router = APIRouter(prefix="/scheduler", tags=["Scheduler"])


@router.get("/config", dependencies=[Depends(verify_api_key)])
@limiter.limit("60/minute")
async def get_scheduler_config(
    request: Request,
    db=Depends(get_database)
) -> Dict[str, Any]:
    """Pobiera konfigurację i status schedulera.

    Returns:
        Słownik z "success", "config" i "status".

    Raises:
        HTTPException: 500 przy błędzie serwera.
    """
    try:
        config = db.get_scheduler_config()
        status = db.get_scheduler_status()
        
        return {
            'success': True,
            'config': config,
            'status': status
        }
            
    except Exception as e:
        logger.error(f"Error getting scheduler config: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/config", dependencies=[Depends(verify_api_key)])
@limiter.limit("30/minute")
async def update_scheduler_config(
    request: Request,
    body: SchedulerConfigUpdate,
    db=Depends(get_database)
) -> Dict[str, Any]:
    """Aktualizuje konfigurację schedulera.

    Args:
        body: Pola do aktualizacji (SchedulerConfigUpdate) – walidowane przez Pydantic.

    Returns:
        Słownik z "success", "message" i "config".

    Raises:
        HTTPException: 400 gdy brak danych do aktualizacji, 500 przy błędzie serwera.
    """
    try:
        updates = body.model_dump(exclude_unset=True)
        if not updates:
            raise HTTPException(
                status_code=400,
                detail="Brak danych do aktualizacji"
            )
        success = db.update_scheduler_config(updates)
        
        if success:
            new_config = db.get_scheduler_config()
            return {
                'success': True,
                'message': 'Konfiguracja zaktualizowana',
                'config': new_config
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Nie udało się zaktualizować konfiguracji"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating scheduler config: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status", dependencies=[Depends(verify_api_key)])
@limiter.limit("60/minute")
async def get_scheduler_status(
    request: Request,
    db=Depends(get_database)
) -> Dict[str, Any]:
    """Zwraca bieżący status schedulerów (sygnały, analizy AI).

    Returns:
        Słownik z "success" i "status".

    Raises:
        HTTPException: 500 przy błędzie serwera.
    """
    try:
        status = db.get_scheduler_status()
        
        return {
            'success': True,
            'status': status
        }
            
    except Exception as e:
        logger.error(f"Error getting scheduler status: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
