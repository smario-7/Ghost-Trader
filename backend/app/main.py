"""
Główna aplikacja FastAPI Trading Bot
"""
from fastapi import FastAPI, HTTPException, Security, Depends, Request
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import logging
from datetime import datetime
from typing import Dict, Any
import uvicorn

from .config import get_settings
from .utils.logger import setup_logger
from .utils.database import Database
from .services.telegram_service import TelegramService
from .services.strategy_service import StrategyService
from .models.models import (
    StrategyCreate,
    StrategyUpdate,
    SignalResponse,
    HealthResponse
)

# Wczytaj konfigurację
settings = get_settings()

# Setup logowania
logger = setup_logger(
    name="trading_bot",
    log_file=settings.log_file,
    level=settings.log_level
)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# FastAPI app
app = FastAPI(
    title="Trading Bot API",
    description="API do zarządzania strategiami tradingowymi",
    version="2.0.0",
    docs_url="/docs" if settings.is_development() else None,
    redoc_url="/redoc" if settings.is_development() else None
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Key Security
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Security(api_key_header)):
    """Weryfikacja klucza API"""
    if not api_key:
        logger.warning("Brak klucza API w żądaniu")
        raise HTTPException(
            status_code=403,
            detail="Brak klucza API. Dodaj header: X-API-Key"
        )
    if api_key != settings.api_key:
        logger.warning(f"Nieprawidłowy klucz API: {api_key[:10]}...")
        raise HTTPException(
            status_code=403,
            detail="Nieprawidłowy klucz API"
        )
    return api_key


# Dependency injection
def get_database() -> Database:
    """Zwraca instancję bazy danych"""
    return Database(settings.database_path)


def get_telegram_service() -> TelegramService:
    """Zwraca instancję serwisu Telegram"""
    return TelegramService(
        bot_token=settings.telegram_bot_token,
        chat_id=settings.telegram_chat_id
    )


def get_strategy_service(
    db: Database = Depends(get_database),
    telegram: TelegramService = Depends(get_telegram_service)
) -> StrategyService:
    """Zwraca instancję serwisu strategii"""
    return StrategyService(db, telegram)


# Middleware do logowania requestów
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Loguje wszystkie requesty"""
    start_time = datetime.now()
    
    # Log request
    logger.info(
        f"Request: {request.method} {request.url.path}",
        extra={
            "method": request.method,
            "path": request.url.path,
            "client": request.client.host if request.client else "unknown"
        }
    )
    
    # Process request
    try:
        response = await call_next(request)
        
        # Log response
        duration = (datetime.now() - start_time).total_seconds()
        logger.info(
            f"Response: {response.status_code} ({duration:.3f}s)",
            extra={
                "status_code": response.status_code,
                "duration": duration
            }
        )
        
        return response
    except Exception as e:
        logger.error(f"Request error: {str(e)}", exc_info=True)
        raise


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Obsługa globalnych wyjątków"""
    logger.error(
        f"Unhandled exception: {str(exc)}",
        exc_info=True,
        extra={
            "path": request.url.path,
            "method": request.method
        }
    )
    
    # W produkcji nie pokazuj szczegółów błędu
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


# Endpoints

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Trading Bot API",
        "version": "2.0.0",
        "status": "running"
    }


@app.get("/health", response_model=HealthResponse)
@limiter.limit("10/minute")
async def health_check(request: Request):
    """Health check endpoint"""
    try:
        db = get_database()
        db_status = db.check_connection()
        
        telegram = get_telegram_service()
        telegram_status = await telegram.check_connection()
        
        return HealthResponse(
            status="healthy" if (db_status and telegram_status) else "unhealthy",
            timestamp=datetime.now(),
            database=db_status,
            telegram=telegram_status,
            environment=settings.environment
        )
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return HealthResponse(
            status="unhealthy",
            timestamp=datetime.now(),
            database=False,
            telegram=False,
            environment=settings.environment
        )


@app.get("/strategies", dependencies=[Depends(verify_api_key)])
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def get_strategies(
    request: Request,
    service: StrategyService = Depends(get_strategy_service)
):
    """Pobiera wszystkie strategie"""
    try:
        strategies = service.get_all_strategies()
        return {"strategies": strategies}
    except Exception as e:
        logger.error(f"Error getting strategies: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/strategies", dependencies=[Depends(verify_api_key)])
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def create_strategy(
    request: Request,
    strategy: StrategyCreate,
    service: StrategyService = Depends(get_strategy_service)
):
    """Tworzy nową strategię"""
    try:
        result = service.create_strategy(strategy)
        logger.info(f"Strategy created: {strategy.name}")
        return result
    except Exception as e:
        logger.error(f"Error creating strategy: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/strategies/{strategy_id}", dependencies=[Depends(verify_api_key)])
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def update_strategy(
    request: Request,
    strategy_id: int,
    strategy: StrategyUpdate,
    service: StrategyService = Depends(get_strategy_service)
):
    """Aktualizuje strategię"""
    try:
        result = service.update_strategy(strategy_id, strategy)
        logger.info(f"Strategy updated: {strategy_id}")
        return result
    except Exception as e:
        logger.error(f"Error updating strategy: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/strategies/{strategy_id}", dependencies=[Depends(verify_api_key)])
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def delete_strategy(
    request: Request,
    strategy_id: int,
    service: StrategyService = Depends(get_strategy_service)
):
    """Usuwa strategię"""
    try:
        result = service.delete_strategy(strategy_id)
        logger.info(f"Strategy deleted: {strategy_id}")
        return result
    except Exception as e:
        logger.error(f"Error deleting strategy: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/check-signals", dependencies=[Depends(verify_api_key)])
@limiter.limit("10/minute")
async def check_signals(
    request: Request,
    service: StrategyService = Depends(get_strategy_service)
):
    """Sprawdza sygnały dla wszystkich aktywnych strategii"""
    try:
        results = await service.check_all_signals()
        logger.info(f"Signals checked: {len(results)} strategies")
        return {"results": results}
    except Exception as e:
        logger.error(f"Error checking signals: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/test-telegram", dependencies=[Depends(verify_api_key)])
@limiter.limit("5/minute")
async def test_telegram(
    request: Request,
    telegram: TelegramService = Depends(get_telegram_service)
):
    """Testuje połączenie z Telegram"""
    try:
        result = await telegram.send_message("🧪 Test połączenia - Trading Bot")
        return {"success": result, "message": "Wiadomość wysłana"}
    except Exception as e:
        logger.error(f"Error testing telegram: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== AI ENDPOINTS =====

@app.post("/ai/analyze", dependencies=[Depends(verify_api_key)])
@limiter.limit("10/hour")  # Lower limit for AI (expensive)
async def ai_analyze(
    request: Request,
    symbol: str,
    timeframe: str = "1h",
    telegram: TelegramService = Depends(get_telegram_service)
):
    """
    Kompleksowa analiza AI łącząca makro + news + technical
    
    UWAGA: Ten endpoint wykorzystuje Claude API i może generować koszty
    """
    try:
        from .services.ai_strategy import AIStrategy
        
        ai_strategy = AIStrategy(telegram_service=telegram)
        result = await ai_strategy.analyze_and_generate_signal(
            symbol=symbol,
            timeframe=timeframe
        )
        
        logger.info(f"AI analysis completed for {symbol}: {result.get('recommendation')}")
        return result
        
    except Exception as e:
        logger.error(f"Error in AI analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/ai/market-overview/{symbol}", dependencies=[Depends(verify_api_key)])
@limiter.limit("20/hour")
async def ai_market_overview(
    request: Request,
    symbol: str
):
    """
    Pełny przegląd rynku dla symbolu (makro + news + technical + sentiment)
    """
    try:
        from .services.ai_strategy import AIStrategy
        
        ai_strategy = AIStrategy()
        overview = await ai_strategy.get_market_overview(symbol)
        
        return overview
        
    except Exception as e:
        logger.error(f"Error generating market overview: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ai/sentiment", dependencies=[Depends(verify_api_key)])
@limiter.limit("30/hour")
async def ai_sentiment(
    request: Request,
    symbol: str,
    hours_back: int = 24
):
    """
    Analiza sentymentu z wiadomości dla symbolu
    """
    try:
        from .services.ai_analysis_service import AIAnalysisService
        from .services.data_collection_service import NewsService
        
        ai_service = AIAnalysisService()
        news_service = NewsService()
        
        # Pobierz wiadomości
        news = await news_service.get_financial_news(
            symbol=symbol.split('/')[0],
            hours_back=hours_back,
            limit=20
        )
        
        # Analiza sentymentu
        sentiment = await ai_service.get_sentiment_analysis(symbol, news)
        
        return {
            "symbol": symbol,
            "hours_analyzed": hours_back,
            "news_count": len(news),
            "sentiment": sentiment
        }
        
    except Exception as e:
        logger.error(f"Error in sentiment analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ai/event-impact", dependencies=[Depends(verify_api_key)])
@limiter.limit("30/hour")
async def ai_event_impact(
    request: Request,
    event: str,
    symbol: str,
    context: Dict[str, Any] = None
):
    """
    Analizuje wpływ konkretnego wydarzenia na rynek
    """
    try:
        from .services.ai_analysis_service import AIAnalysisService
        
        ai_service = AIAnalysisService()
        
        if context is None:
            context = {}
        
        impact = await ai_service.analyze_event_impact(
            event=event,
            symbol=symbol,
            context=context
        )
        
        return {
            "event": event,
            "symbol": symbol,
            "impact": impact
        }
        
    except Exception as e:
        logger.error(f"Error analyzing event impact: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Startup
@app.on_event("startup")
async def startup_event():
    """Inicjalizacja przy starcie"""
    logger.info(f"🚀 Starting Trading Bot API")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Database: {settings.database_path}")
    logger.info(f"Check interval: {settings.check_interval} min")
    
    # Inicjalizuj bazę danych
    db = get_database()
    db.initialize()
    logger.info("✅ Database initialized")


# Shutdown
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup przy zamknięciu"""
    logger.info("🛑 Shutting down Trading Bot API")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.is_development()
    )
