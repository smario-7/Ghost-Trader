"""
Główna aplikacja FastAPI Trading Bot
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import logging
from typing import Any, Dict

from .config import get_settings
from .utils.logger import setup_logger
from .exceptions import (
    StrategyNotFoundException,
    SignalGenerationException,
    AnalysisNotFoundException,
)

settings = get_settings()

logger = setup_logger(
    name="trading_bot",
    log_file=settings.log_file,
    level=settings.log_level
)

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Trading Bot API",
    description="API do zarządzania strategiami tradingowymi",
    version="2.0.0",
    docs_url="/docs" if settings.is_development() else None,
    redoc_url="/redoc" if settings.is_development() else None
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(StrategyNotFoundException)
async def strategy_not_found_handler(
    request: Any, exc: StrategyNotFoundException
) -> JSONResponse:
    """Mapuje StrategyNotFoundException na HTTP 404."""
    return JSONResponse(
        status_code=404,
        content={"detail": str(exc)},
    )


@app.exception_handler(AnalysisNotFoundException)
async def analysis_not_found_handler(
    request: Any, exc: AnalysisNotFoundException
) -> JSONResponse:
    """Mapuje AnalysisNotFoundException na HTTP 404."""
    return JSONResponse(
        status_code=404,
        content={"detail": str(exc)},
    )


@app.exception_handler(SignalGenerationException)
async def signal_generation_handler(
    request: Any, exc: SignalGenerationException
) -> JSONResponse:
    """Mapuje SignalGenerationException na HTTP 500."""
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc) or "Błąd generowania sygnału"},
    )


@app.middleware("http")
async def cors_preflight_bypass(request: Any, call_next: Any) -> Response:
    if request.method == "OPTIONS":
        return Response(
            status_code=200,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "*",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Allow-Credentials": "true",
            }
        )
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Any, call_next: Any) -> Response:
    """Loguje wszystkie requesty"""
    from .config import get_polish_time
    from .utils.database import Database
    
    start_time = get_polish_time()
    
    logger.info(
        f"Request: {request.method} {request.url.path}",
        extra={
            "method": request.method,
            "path": request.url.path,
            "client": request.client.host if request.client else "unknown"
        }
    )
    
    if "activity-logs" in request.url.path:
        logger.info(f"🔍 Activity-logs request detected: {request.method} {request.url.path}")
        all_routes = [r.path for r in app.routes if hasattr(r, 'path')]
        activity_routes = [r for r in all_routes if 'activity' in r]
        logger.info(f"🔍 All routes count: {len(all_routes)}")
        logger.info(f"🔍 Activity routes: {activity_routes}")
    
    try:
        response = await call_next(request)
        
        duration = (get_polish_time() - start_time).total_seconds()
        logger.info(
            f"Response: {response.status_code} ({duration:.3f}s)",
            extra={
                "status_code": response.status_code,
                "duration": duration
            }
        )
        
        if "activity-logs" in request.url.path:
            logger.info(f"🔍 Activity-logs response: {response.status_code}")
        
        return response
    except Exception as e:
        logger.error(f"Request error: {str(e)}", exc_info=True)
        if "activity-logs" in request.url.path:
            logger.error(f"🔍 Activity-logs error: {str(e)}", exc_info=True)
        raise


@app.exception_handler(Exception)
async def global_exception_handler(
    request: Any, exc: Exception
) -> JSONResponse:
    """Obsługa globalnych wyjątków"""
    logger.error(
        f"Unhandled exception: {str(exc)}",
        exc_info=True,
        extra={
            "path": request.url.path,
            "method": request.method
        }
    )
    
    if settings.is_production():
        return JSONResponse(
            status_code=500,
            content={"detail": "Wewnętrzny błąd serwera"}
        )
    else:
        return JSONResponse(
            status_code=500,
            content={
                "detail": str(exc),
                "type": type(exc).__name__
            }
        )


from .api import health, activity, telegram, scheduler, strategies, signals, chart_data, ai, streams, statistics

app.include_router(health.router)
app.include_router(activity.router)
app.include_router(telegram.router)
app.include_router(scheduler.router)
app.include_router(strategies.router)
app.include_router(signals.router)
app.include_router(chart_data.router)
app.include_router(ai.router)
app.include_router(streams.router)
app.include_router(statistics.router)


@app.on_event("startup")
async def startup_event() -> None:
    """Inicjalizacja przy starcie"""
    logger.info(f"🚀 Starting Trading Bot API")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Database: {settings.database_path}")
    logger.info(f"Check interval: {settings.check_interval} min")
    
    routes = [f"{route.methods} {route.path}" for route in app.routes if hasattr(route, 'path')]
    logger.info(f"📋 Zarejestrowane route'y: {len(routes)}")
    for route in routes[:30]:
        logger.info(f"  - {route}")
    activity_logs_routes = [r for r in routes if 'activity-logs' in r]
    if activity_logs_routes:
        logger.info(f"✅ Endpoint /activity-logs zarejestrowany: {activity_logs_routes}")
    else:
        logger.warning("⚠️ Endpoint /activity-logs NIE został zarejestrowany!")
    
    from .utils.database import Database
    db = Database(settings.database_path)
    db.initialize()
    logger.info("✅ Database initialized")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Cleanup przy zamknięciu"""
    logger.info("🛑 Shutting down Trading Bot API")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.is_development()
    )
