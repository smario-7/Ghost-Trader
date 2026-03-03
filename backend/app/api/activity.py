"""
Router dla endpointów activity-logs
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from typing import Optional, Dict, Any

from .dependencies import verify_api_key, get_database, settings
from ..config import get_polish_time
from ..utils.logger import setup_logger

limiter = Limiter(key_func=get_remote_address)
logger = setup_logger(name="trading_bot", log_file=settings.log_file, level=settings.log_level)

router = APIRouter(prefix="/activity-logs", tags=["Activity Logs"])


@router.get("", dependencies=[Depends(verify_api_key)])
async def get_activity_logs(
    request: Request,
    limit: int = Query(100, ge=1, le=1000),
    log_type: Optional[str] = Query(None),
    db=Depends(get_database)
) -> Dict[str, Any]:
    """
    Pobiera logi aktywności bota
    
    Args:
        limit: Maksymalna liczba logów (domyślnie 100)
        log_type: Opcjonalny filtr po typie logu (market_data, analysis, signal, telegram)
    
    Returns:
        Lista logów aktywności posortowanych od najnowszych
    """
    logger.info(f"get_activity_logs called with limit={limit}, log_type={log_type}")
    try:
        if log_type:
            logs = db.get_activity_logs_by_type(log_type, limit)
        else:
            logs = db.get_recent_activity_logs(limit)
        
        logger.info(f"Returning {len(logs)} activity logs")
        return {"logs": logs, "count": len(logs)}
    except Exception as e:
        logger.error(f"Error getting activity logs: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/new", dependencies=[Depends(verify_api_key)])
@limiter.limit("60/minute")
async def get_new_activity_logs(
    request: Request,
    last_id: int = Query(0, ge=0, description="Ostatnie znane ID logu"),
    log_type: Optional[str] = Query(None, description="Filtr po typie logu"),
    limit: int = Query(100, ge=1, le=500, description="Maksymalna liczba logów"),
    db=Depends(get_database)
) -> Dict[str, Any]:
    """
    Pobiera nowe logi aktywności od określonego ID (dla polling)
    
    Używane przez frontend do real-time aktualizacji logów.
    Frontend powinien wywoływać ten endpoint co 2-3 sekundy z ostatnim znanym ID.
    
    Args:
        last_id: Ostatnie znane ID (pobiera logi o ID > last_id)
        log_type: Opcjonalny filtr po typie logu (llm, telegram, market_data, etc.)
        limit: Maksymalna liczba logów
    
    Returns:
        Lista nowych logów posortowanych od najstarszych do najnowszych
    """
    try:
        logs = db.get_activity_logs_since(last_id=last_id, log_type=log_type, limit=limit)
        
        return {
            "logs": logs,
            "count": len(logs),
            "last_id": logs[-1]['id'] if logs else last_id
        }
    except Exception as e:
        logger.error(f"Error getting new activity logs: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
