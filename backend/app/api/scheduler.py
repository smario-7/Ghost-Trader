"""
Router dla endpointów schedulera
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
import re
from typing import Dict, Any

from .dependencies import verify_api_key, get_database, settings
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
    """Pobiera konfigurację schedulera"""
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
    db=Depends(get_database)
) -> Dict[str, Any]:
    """Aktualizuje konfigurację schedulera"""
    try:
        body = await request.json()
        updates = {}
        
        if 'signal_check_enabled' in body:
            if not isinstance(body['signal_check_enabled'], bool):
                raise HTTPException(status_code=400, detail="signal_check_enabled musi być boolean")
            updates['signal_check_enabled'] = body['signal_check_enabled']
        
        if 'ai_analysis_enabled' in body:
            if not isinstance(body['ai_analysis_enabled'], bool):
                raise HTTPException(status_code=400, detail="ai_analysis_enabled musi być boolean")
            updates['ai_analysis_enabled'] = body['ai_analysis_enabled']
        
        if 'signal_check_interval' in body:
            interval = body['signal_check_interval']
            if not isinstance(interval, int) or interval < 1 or interval > 1440:
                raise HTTPException(
                    status_code=400,
                    detail="signal_check_interval musi być liczbą całkowitą 1-1440"
                )
            updates['signal_check_interval'] = interval
        
        if 'ai_analysis_interval' in body:
            interval = body['ai_analysis_interval']
            if not isinstance(interval, int) or interval < 5 or interval > 1440:
                raise HTTPException(
                    status_code=400,
                    detail="ai_analysis_interval musi być liczbą całkowitą 5-1440"
                )
            updates['ai_analysis_interval'] = interval
        
        time_pattern = re.compile(r'^([01]\d|2[0-3]):([0-5]\d)$')
        
        for field in ['signal_hours_start', 'signal_hours_end', 'ai_hours_start', 'ai_hours_end']:
            if field in body:
                value = body[field]
                if not isinstance(value, str) or not time_pattern.match(value):
                    raise HTTPException(
                        status_code=400,
                        detail=f"{field} musi być w formacie HH:MM (00:00-23:59)"
                    )
                updates[field] = value
        
        for field in ['signal_active_days', 'ai_active_days']:
            if field in body:
                value = body[field]
                if not isinstance(value, str):
                    raise HTTPException(
                        status_code=400,
                        detail=f"{field} musi być stringiem"
                    )
                try:
                    days = [int(d.strip()) for d in value.split(',')]
                    if not all(1 <= d <= 7 for d in days):
                        raise ValueError
                except:
                    raise HTTPException(
                        status_code=400,
                        detail=f"{field} musi być w formacie '1,2,3,4,5,6,7' (dni 1-7)"
                    )
                updates[field] = value
        
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
    """Zwraca bieżący status schedulerów"""
    try:
        status = db.get_scheduler_status()
        
        return {
            'success': True,
            'status': status
        }
            
    except Exception as e:
        logger.error(f"Error getting scheduler status: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
