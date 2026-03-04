"""
Router dla endpointów SSE (Server-Sent Events)
"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from typing import Dict, Any
import json
import asyncio

from .dependencies import verify_api_key, get_database, get_strategy_service, settings
from ..config import get_polish_time
from ..utils.logger import setup_logger

logger = setup_logger(name="trading_bot", log_file=settings.log_file, level=settings.log_level)

router = APIRouter(prefix="/stream", tags=["SSE Streams"])

sse_queues = []


async def broadcast_sse_event(event_type: str, data: dict) -> None:
    """Wysyła event do wszystkich połączonych klientów SSE.

    Args:
        event_type: Typ zdarzenia (np. "signal", "update").
        data: Dane do wysłania (będą zserializowane do JSON).
    """
    message = {
        "event": event_type,
        "data": json.dumps(data)
    }
    
    for queue in sse_queues[:]:
        try:
            await queue.put(message)
        except Exception as e:
            logger.error(f"Error broadcasting SSE event: {str(e)}")
            if queue in sse_queues:
                sse_queues.remove(queue)


@router.get("/updates", dependencies=[Depends(verify_api_key)])
async def stream_updates(
    request: Request,
    service=Depends(get_strategy_service),
    db=Depends(get_database)
) -> StreamingResponse:
    """Server-Sent Events – strumień aktualizacji sygnałów i logów w czasie rzeczywistym.

    Returns:
        StreamingResponse z media_type text/event-stream.
    """

    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                
                try:
                    stats = service.get_statistics()
                    signals = service.get_recent_signals(limit=20)
                    activity_logs = db.get_recent_activity_logs(limit=10)
                    
                    data = {
                        "type": "update",
                        "timestamp": get_polish_time().isoformat(),
                        "data": {
                            "statistics": stats,
                            "signals": signals,
                            "activity_logs": activity_logs
                        }
                    }
                    
                    yield f"data: {json.dumps(data)}\n\n"
                    
                except Exception as e:
                    logger.error(f"Error in SSE stream: {str(e)}", exc_info=True)
                    error_data = {
                        "type": "error",
                        "message": str(e),
                        "timestamp": get_polish_time().isoformat()
                    }
                    yield f"data: {json.dumps(error_data)}\n\n"
                
                await asyncio.sleep(5)
                
        except asyncio.CancelledError:
            logger.info("SSE stream cancelled")
        except Exception as e:
            logger.error(f"SSE stream error: {str(e)}", exc_info=True)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*"
        }
    )


@router.get("/ai-updates", dependencies=[Depends(verify_api_key)])
async def stream_ai_updates(
    request: Request,
    db=Depends(get_database)
) -> StreamingResponse:
    """Server-Sent Events – strumień aktualizacji analiz AI i konfiguracji w czasie rzeczywistym.

    Returns:
        StreamingResponse z media_type text/event-stream.
    """

    async def sse_generator():
        queue = asyncio.Queue()
        sse_queues.append(queue)
        
        try:
            try:
                token_stats = db.get_token_statistics()
                config = db.get_analysis_config()
                symbols = config.get("enabled_symbols")
                if isinstance(symbols, list):
                    config["enabled_symbols"] = symbols
                elif isinstance(symbols, str) and symbols:
                    try:
                        config["enabled_symbols"] = json.loads(symbols)
                    except Exception:
                        config["enabled_symbols"] = []
                else:
                    config["enabled_symbols"] = []
                yield f"event: token_update\ndata: {json.dumps(token_stats)}\n\n"
                yield f"event: config_change\ndata: {json.dumps(config)}\n\n"
                
            except Exception as e:
                logger.error(f"Error sending initial SSE data: {str(e)}")
            
            while True:
                if await request.is_disconnected():
                    break
                
                try:
                    data = await asyncio.wait_for(queue.get(), timeout=30.0)
                    
                    yield f"event: {data['event']}\ndata: {data['data']}\n\n"
                    
                except asyncio.TimeoutError:
                    yield f": heartbeat\n\n"
                    
                except Exception as e:
                    logger.error(f"Error in SSE generator: {str(e)}")
                    
        except asyncio.CancelledError:
            logger.info("SSE AI stream cancelled")
        except Exception as e:
            logger.error(f"SSE AI stream error: {str(e)}", exc_info=True)
        finally:
            if queue in sse_queues:
                sse_queues.remove(queue)
    
    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*"
        }
    )
