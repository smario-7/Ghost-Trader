"""
Główna aplikacja FastAPI Trading Bot
"""
from fastapi import FastAPI, HTTPException, Security, Depends, Request, Query
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import logging
from datetime import datetime
from typing import Dict, Any, Optional
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
    db = Database(settings.database_path)
    return TelegramService(
        bot_token=settings.telegram_bot_token,
        chat_id=settings.telegram_chat_id,
        database=db
    )


def get_strategy_service(
    db: Database = Depends(get_database),
    telegram: TelegramService = Depends(get_telegram_service)
) -> StrategyService:
    """Zwraca instancję serwisu strategii"""
    return StrategyService(db, telegram)


def get_auto_scheduler(
    db: Database = Depends(get_database),
    telegram: TelegramService = Depends(get_telegram_service)
):
    """Zwraca instancję AutoAnalysisScheduler"""
    from .services.auto_analysis_scheduler import AutoAnalysisScheduler
    return AutoAnalysisScheduler(
        database=db,
        telegram=telegram,
        interval_minutes=settings.analysis_interval
    )


def get_signal_aggregator(
    db: Database = Depends(get_database)
):
    """Zwraca instancję SignalAggregatorService"""
    from .services.signal_aggregator_service import SignalAggregatorService
    return SignalAggregatorService(database=db)


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
    
    # Szczegółowe logowanie dla activity-logs
    if "activity-logs" in request.url.path:
        logger.info(f"🔍 Activity-logs request detected: {request.method} {request.url.path}")
        all_routes = [r.path for r in app.routes if hasattr(r, 'path')]
        activity_routes = [r for r in all_routes if 'activity' in r]
        logger.info(f"🔍 All routes count: {len(all_routes)}")
        logger.info(f"🔍 Activity routes: {activity_routes}")
        logger.info(f"🔍 Full route list: {all_routes[:20]}")
    
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
        
        # Szczegółowe logowanie dla activity-logs
        if "activity-logs" in request.url.path:
            logger.info(f"🔍 Activity-logs response: {response.status_code}")
        
        return response
    except Exception as e:
        logger.error(f"Request error: {str(e)}", exc_info=True)
        if "activity-logs" in request.url.path:
            logger.error(f"🔍 Activity-logs error: {str(e)}", exc_info=True)
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


@app.get("/test")
async def test_endpoint():
    """Testowy endpoint do weryfikacji połączenia"""
    return {
        "status": "ok",
        "message": "Backend odpowiada poprawnie",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/activity-logs", dependencies=[Depends(verify_api_key)])
async def get_activity_logs(
    request: Request,
    limit: int = Query(100, ge=1, le=1000),
    log_type: Optional[str] = Query(None),
    db: Database = Depends(get_database)
):
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


@app.get("/test-activity-logs", dependencies=[Depends(verify_api_key)])
async def test_activity_logs_endpoint(request: Request):
    """Testowy endpoint do weryfikacji routingu activity-logs"""
    return {
        "status": "ok",
        "message": "Activity logs endpoint routing works",
        "timestamp": datetime.now().isoformat()
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


@app.get("/strategies/{strategy_id}", dependencies=[Depends(verify_api_key)])
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def get_strategy(
    request: Request,
    strategy_id: int,
    service: StrategyService = Depends(get_strategy_service)
):
    """Pobiera pojedynczą strategię"""
    try:
        strategy = service.get_strategy(strategy_id)
        if not strategy:
            raise HTTPException(status_code=404, detail=f"Strategy {strategy_id} not found")
        return {"strategy": strategy}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting strategy {strategy_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/statistics", dependencies=[Depends(verify_api_key)])
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def get_statistics(
    request: Request,
    service: StrategyService = Depends(get_strategy_service)
):
    """Pobiera statystyki systemu"""
    try:
        stats = service.get_statistics()
        return stats
    except Exception as e:
        logger.error(f"Error getting statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/signals/recent", dependencies=[Depends(verify_api_key)])
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def get_recent_signals(
    request: Request,
    limit: int = 50,
    service: StrategyService = Depends(get_strategy_service)
):
    """Pobiera ostatnie sygnały"""
    try:
        signals = service.get_recent_signals(limit)
        return {"signals": signals}
    except Exception as e:
        logger.error(f"Error getting recent signals: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/signals/strategy/{strategy_id}", dependencies=[Depends(verify_api_key)])
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def get_strategy_signals(
    request: Request,
    strategy_id: int,
    limit: int = 100,
    service: StrategyService = Depends(get_strategy_service)
):
    """Pobiera sygnały dla konkretnej strategii"""
    try:
        signals = service.get_strategy_signals(strategy_id, limit)
        return {"signals": signals}
    except Exception as e:
        logger.error(f"Error getting signals for strategy {strategy_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== AI ANALYSIS ENDPOINTS (REFACTORED) =====

@app.post(
    "/ai/analyze",
    dependencies=[Depends(verify_api_key)],
    summary="Kompleksowa analiza AI",
    description="""
    Kompleksowa analiza AI łącząca wszystkie źródła:
    - AI Analysis (OpenAI GPT)
    - Technical Indicators (RSI, MACD, MA, Bollinger)
    - Macro Data (Fed, inflacja, PKB)
    - News Sentiment
    
    Używa głosowania większościowego do wygenerowania finalnego sygnału.
    Zapisuje wynik do bazy danych.
    
    UWAGA: Ten endpoint wykorzystuje OpenAI API i może generować koszty.
    """,
    response_description="Pełna analiza ze wszystkich źródeł + agregacja",
    tags=["AI Analysis"]
)
@limiter.limit("60/hour")
async def ai_analyze(
    request: Request,
    symbol: str,
    timeframe: str = "1h",
    db: Database = Depends(get_database),
    telegram: TelegramService = Depends(get_telegram_service),
    aggregator = Depends(get_signal_aggregator)
):
    """
    Kompleksowa analiza AI z agregacją sygnałów
    """
    try:
        from .services.ai_strategy import AIStrategy
        import json
        
        logger.info(f"Starting comprehensive AI analysis for {symbol} ({timeframe})")
        
        # Utwórz instancję AIStrategy
        ai_strategy = AIStrategy(telegram_service=telegram)
        
        # Uruchom kompleksową analizę
        analysis = await ai_strategy.comprehensive_analysis(
            symbol=symbol,
            timeframe=timeframe
        )
        
        # Agreguj sygnały
        aggregated = await aggregator.aggregate_signals(
            symbol=symbol,
            timeframe=timeframe,
            ai_result=analysis["ai_analysis"],
            technical_result=analysis["technical_analysis"],
            macro_result=analysis["macro_analysis"],
            news_result=analysis["news_analysis"]
        )
        
        # Zapisz wynik do bazy
        analysis_id = db.create_ai_analysis_result({
            "symbol": symbol,
            "timeframe": timeframe,
            "ai_recommendation": analysis["ai_analysis"]["recommendation"],
            "ai_confidence": analysis["ai_analysis"]["confidence"],
            "ai_reasoning": analysis["ai_analysis"]["reasoning"],
            "technical_signal": analysis["technical_analysis"]["signal"],
            "technical_confidence": analysis["technical_analysis"]["confidence"],
            "technical_details": json.dumps(analysis["technical_analysis"]["indicators"]),
            "macro_signal": analysis["macro_analysis"]["signal"],
            "macro_impact": analysis["macro_analysis"]["impact"],
            "news_sentiment": analysis["news_analysis"]["sentiment"],
            "news_score": analysis["news_analysis"]["score"],
            "final_signal": aggregated["final_signal"],
            "agreement_score": aggregated["agreement_score"],
            "voting_details": json.dumps(aggregated["voting_details"]),
            "decision_reason": aggregated["decision_reason"],
            "tokens_used": analysis["ai_analysis"]["tokens_used"],
            "estimated_cost": analysis["ai_analysis"]["estimated_cost"]
        })
        
        logger.info(f"AI analysis completed for {symbol}: {aggregated['final_signal']} ({aggregated['agreement_score']}%)")
        
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "timestamp": analysis["timestamp"],
            "analysis": {
                "ai": analysis["ai_analysis"],
                "technical": analysis["technical_analysis"],
                "macro": analysis["macro_analysis"],
                "news": analysis["news_analysis"]
            },
            "aggregated": aggregated,
            "tokens_used": analysis["ai_analysis"]["tokens_used"],
            "estimated_cost": analysis["ai_analysis"]["estimated_cost"],
            "analysis_id": analysis_id
        }
        
    except Exception as e:
        logger.error(f"Error in AI analysis: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/ai/market-overview/{symbol}",
    dependencies=[Depends(verify_api_key)],
    summary="Przegląd rynku dla symbolu",
    description="""
    Pełny przegląd rynku dla symbolu z wykorzystaniem comprehensive_analysis.
    
    Zwraca:
    - Kompleksową analizę ze wszystkich źródeł
    - Link do ostatniej zapisanej analizy (jeśli istnieje)
    """,
    response_description="Przegląd rynku z comprehensive analysis",
    tags=["AI Analysis"]
)
@limiter.limit("60/hour")
async def ai_market_overview(
    request: Request,
    symbol: str,
    db: Database = Depends(get_database),
    telegram: TelegramService = Depends(get_telegram_service)
):
    """
    Pełny przegląd rynku dla symbolu
    """
    try:
        from .services.ai_strategy import AIStrategy
        
        logger.info(f"Generating market overview for {symbol}")
        
        ai_strategy = AIStrategy(telegram_service=telegram)
        
        # Użyj comprehensive_analysis jako podstawy
        analysis = await ai_strategy.comprehensive_analysis(
            symbol=symbol,
            timeframe="1h"
        )
        
        # Pobierz ostatnią zapisaną analizę z bazy (jeśli istnieje)
        last_analysis = None
        try:
            results = db.get_ai_analysis_results(symbol=symbol, limit=1)
            if results:
                last_analysis = {
                    "id": results[0].get("id"),
                    "timestamp": results[0].get("timestamp"),
                    "final_signal": results[0].get("final_signal"),
                    "agreement_score": results[0].get("agreement_score")
                }
        except:
            pass
        
        logger.info(f"Market overview generated for {symbol}")
        
        return {
            "symbol": symbol,
            "timestamp": analysis["timestamp"],
            "comprehensive_analysis": {
                "ai": analysis["ai_analysis"],
                "technical": analysis["technical_analysis"],
                "macro": analysis["macro_analysis"],
                "news": analysis["news_analysis"]
            },
            "last_saved_analysis": last_analysis
        }
        
    except Exception as e:
        logger.error(f"Error generating market overview: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ai/sentiment", dependencies=[Depends(verify_api_key)])
@limiter.limit("60/hour")
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
@limiter.limit("60/hour")
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


# ===== AI ANALYSIS RESULTS ENDPOINTS =====

@app.get(
    "/ai/analysis-results",
    dependencies=[Depends(verify_api_key)],
    summary="Pobierz wyniki analiz AI",
    description="""
    Pobiera listę wyników analiz AI z opcjonalnym filtrowaniem.
    
    Parametry filtrowania:
    - symbol: Filtruj po symbolu (np. EUR/USD)
    - limit: Maksymalna liczba wyników (1-200, domyślnie 50)
    - signal_type: Filtruj po typie sygnału (BUY/SELL/HOLD/NO_SIGNAL)
    - min_agreement: Minimalny agreement_score (0-100)
    
    Wyniki są sortowane od najnowszych.
    """,
    response_description="Lista wyników analiz z zastosowanymi filtrami",
    tags=["AI Analysis Results"]
)
@limiter.limit("60/hour")
async def get_ai_analysis_results(
    request: Request,
    symbol: Optional[str] = Query(None, description="Filtruj po symbolu"),
    limit: int = Query(50, ge=1, le=200, description="Maksymalna liczba wyników"),
    signal_type: Optional[str] = Query(None, description="Filtruj po typie sygnału"),
    min_agreement: Optional[int] = Query(None, ge=0, le=100, description="Minimalny agreement_score"),
    db: Database = Depends(get_database)
):
    """
    Pobiera wyniki analiz AI z bazy danych
    """
    try:
        logger.info(f"Fetching AI analysis results: symbol={symbol}, limit={limit}, signal_type={signal_type}, min_agreement={min_agreement}")
        
        # Walidacja signal_type
        if signal_type and signal_type not in ['BUY', 'SELL', 'HOLD', 'NO_SIGNAL']:
            raise HTTPException(
                status_code=400,
                detail=f"Nieprawidłowy signal_type. Dozwolone: BUY, SELL, HOLD, NO_SIGNAL"
            )
        
        # Pobierz wyniki z bazy
        results = db.get_ai_analysis_results(symbol=symbol, limit=limit)
        
        # Filtruj po signal_type (jeśli podano)
        if signal_type:
            results = [r for r in results if r.get('final_signal') == signal_type]
        
        # Filtruj po min_agreement (jeśli podano)
        if min_agreement is not None:
            results = [r for r in results if r.get('agreement_score', 0) >= min_agreement]
        
        logger.info(f"Found {len(results)} AI analysis results")
        
        return {
            "results": results,
            "count": len(results),
            "filters_applied": {
                "symbol": symbol,
                "limit": limit,
                "signal_type": signal_type,
                "min_agreement": min_agreement
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching AI analysis results: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/ai/analysis-results/{analysis_id}",
    dependencies=[Depends(verify_api_key)],
    summary="Pobierz szczegóły analizy AI",
    description="""
    Pobiera szczegółowe informacje o pojedynczej analizie AI.
    
    Zwraca pełne dane analizy włącznie z:
    - Wynikami ze wszystkich źródeł (AI, Technical, Macro, News)
    - Szczegółami głosowania
    - Uzasadnieniem decyzji
    - Statystykami tokenów i kosztów
    """,
    response_description="Szczegóły pojedynczej analizy AI",
    tags=["AI Analysis Results"]
)
@limiter.limit("60/hour")
async def get_ai_analysis_by_id(
    request: Request,
    analysis_id: int,
    db: Database = Depends(get_database)
):
    """
    Pobiera szczegóły pojedynczej analizy AI
    """
    try:
        logger.info(f"Fetching AI analysis by ID: {analysis_id}")
        
        result = db.get_ai_analysis_by_id(analysis_id)
        
        if not result:
            logger.warning(f"AI analysis not found: {analysis_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Analiza o ID {analysis_id} nie została znaleziona"
            )
        
        # Parse JSON fields do obiektów
        import json
        if result.get('technical_details'):
            try:
                result['technical_details'] = json.loads(result['technical_details'])
            except:
                pass
        
        if result.get('voting_details'):
            try:
                result['voting_details'] = json.loads(result['voting_details'])
            except:
                pass
        
        logger.info(f"Successfully fetched AI analysis: {analysis_id}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching AI analysis {analysis_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ===== AI TOKEN STATISTICS ENDPOINTS =====

@app.get(
    "/ai/token-statistics",
    dependencies=[Depends(verify_api_key)],
    summary="Pobierz statystyki tokenów OpenAI",
    description="""
    Pobiera statystyki użycia tokenów OpenAI i szacowane koszty.
    
    Parametry:
    - start_date: Data początkowa (format: YYYY-MM-DD, opcjonalnie)
    - end_date: Data końcowa (format: YYYY-MM-DD, opcjonalnie)
    
    Zwraca:
    - Łączne tokeny i koszt
    - Średnią tokenów na analizę
    - Statystyki dzienne (tokeny, koszt, liczba analiz)
    """,
    response_description="Statystyki tokenów i kosztów OpenAI",
    tags=["AI Token Statistics"]
)
@limiter.limit("60/hour")
async def get_token_statistics(
    request: Request,
    start_date: Optional[str] = Query(None, description="Data początkowa (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Data końcowa (YYYY-MM-DD)"),
    db: Database = Depends(get_database)
):
    """
    Pobiera statystyki użycia tokenów OpenAI
    """
    try:
        logger.info(f"Fetching token statistics: start_date={start_date}, end_date={end_date}")
        
        # Walidacja formatu dat
        import re
        date_pattern = r'^\d{4}-\d{2}-\d{2}$'
        
        if start_date and not re.match(date_pattern, start_date):
            raise HTTPException(
                status_code=400,
                detail="Nieprawidłowy format daty start_date. Użyj YYYY-MM-DD"
            )
        
        if end_date and not re.match(date_pattern, end_date):
            raise HTTPException(
                status_code=400,
                detail="Nieprawidłowy format daty end_date. Użyj YYYY-MM-DD"
            )
        
        # Pobierz statystyki z bazy
        stats = db.get_token_statistics(start_date=start_date, end_date=end_date)
        
        # Dodaj informacje o okresie
        stats['period'] = {
            'start_date': start_date,
            'end_date': end_date
        }
        
        logger.info(f"Token statistics: {stats.get('total_tokens', 0)} tokens, ${stats.get('total_cost', 0):.4f}")
        
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching token statistics: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ===== AI CONFIGURATION ENDPOINTS =====

@app.get(
    "/ai/analysis-config",
    dependencies=[Depends(verify_api_key)],
    summary="Pobierz konfigurację automatycznych analiz",
    description="""
    Pobiera aktualną konfigurację automatycznych analiz AI.
    
    Zwraca:
    - Interwał analiz (w minutach)
    - Lista włączonych symboli
    - Próg powiadomień (min agreement_score)
    - Status aktywności (włączone/wyłączone)
    """,
    response_description="Aktualna konfiguracja analiz",
    tags=["AI Configuration"]
)
@limiter.limit("60/hour")
async def get_analysis_config(
    request: Request,
    db: Database = Depends(get_database)
):
    """
    Pobiera konfigurację automatycznych analiz
    """
    try:
        logger.info("Fetching analysis configuration")
        
        config = db.get_analysis_config()
        
        # Parse enabled_symbols z JSON do listy
        import json
        if config.get('enabled_symbols'):
            try:
                config['enabled_symbols'] = json.loads(config['enabled_symbols'])
            except:
                config['enabled_symbols'] = []
        else:
            config['enabled_symbols'] = []
        
        logger.info(f"Analysis config: interval={config.get('analysis_interval')}min, symbols={len(config.get('enabled_symbols', []))}")
        
        return config
        
    except Exception as e:
        logger.error(f"Error fetching analysis config: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.put(
    "/ai/analysis-config",
    dependencies=[Depends(verify_api_key)],
    summary="Aktualizuj konfigurację automatycznych analiz",
    description="""
    Aktualizuje konfigurację automatycznych analiz AI.
    
    Wszystkie pola są opcjonalne - aktualizowane są tylko podane pola.
    
    Parametry:
    - analysis_interval: Interwał analiz w minutach (5-1440)
    - enabled_symbols: Lista symboli do analizy (max 50)
    - notification_threshold: Próg powiadomień w % (0-100)
    - is_active: Czy analizy są włączone (true/false)
    """,
    response_description="Zaktualizowana konfiguracja",
    tags=["AI Configuration"]
)
@limiter.limit("60/hour")
async def update_analysis_config(
    request: Request,
    config_update: Dict[str, Any],
    db: Database = Depends(get_database)
):
    """
    Aktualizuje konfigurację automatycznych analiz
    """
    try:
        logger.info(f"Updating analysis config: {config_update}")
        
        # Walidacja danych wejściowych
        updates = {}
        
        if 'analysis_interval' in config_update:
            interval = config_update['analysis_interval']
            if not isinstance(interval, int) or interval < 5 or interval > 1440:
                raise HTTPException(
                    status_code=422,
                    detail="analysis_interval musi być liczbą całkowitą między 5 a 1440"
                )
            updates['analysis_interval'] = interval
        
        if 'enabled_symbols' in config_update:
            symbols = config_update['enabled_symbols']
            if not isinstance(symbols, list):
                raise HTTPException(
                    status_code=422,
                    detail="enabled_symbols musi być listą"
                )
            if len(symbols) > 50:
                raise HTTPException(
                    status_code=422,
                    detail="enabled_symbols może zawierać maksymalnie 50 symboli"
                )
            # Walidacja symboli
            for symbol in symbols:
                if '/' not in symbol:
                    raise HTTPException(
                        status_code=422,
                        detail=f"Symbol {symbol} musi zawierać '/' (np. EUR/USD)"
                    )
            import json
            updates['enabled_symbols'] = json.dumps(symbols)
        
        if 'notification_threshold' in config_update:
            threshold = config_update['notification_threshold']
            if not isinstance(threshold, int) or threshold < 0 or threshold > 100:
                raise HTTPException(
                    status_code=422,
                    detail="notification_threshold musi być liczbą całkowitą między 0 a 100"
                )
            updates['notification_threshold'] = threshold
        
        if 'is_active' in config_update:
            is_active = config_update['is_active']
            if not isinstance(is_active, bool):
                raise HTTPException(
                    status_code=422,
                    detail="is_active musi być wartością boolean"
                )
            updates['is_active'] = is_active
        
        if not updates:
            raise HTTPException(
                status_code=400,
                detail="Brak danych do aktualizacji"
            )
        
        # Aktualizuj konfigurację
        db.update_analysis_config(updates)
        
        # Pobierz zaktualizowaną konfigurację
        updated_config = db.get_analysis_config()
        
        # Parse enabled_symbols
        import json
        if updated_config.get('enabled_symbols'):
            try:
                updated_config['enabled_symbols'] = json.loads(updated_config['enabled_symbols'])
            except:
                updated_config['enabled_symbols'] = []
        
        logger.info(f"Analysis config updated successfully")
        
        return {
            "message": "Konfiguracja zaktualizowana pomyślnie",
            "updated_config": updated_config
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating analysis config: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ===== AI ANALYSIS TRIGGER ENDPOINTS =====

@app.post(
    "/ai/trigger-analysis",
    dependencies=[Depends(verify_api_key)],
    summary="Uruchom ręczną analizę AI",
    description="""
    Ręcznie uruchamia cykl analiz AI dla wybranych symboli.
    
    UWAGA: To kosztowna operacja - każda analiza wykorzystuje tokeny OpenAI.
    
    Parametry (opcjonalne):
    - symbols: Lista symboli do analizy (jeśli brak - użyje domyślnej listy z konfiguracji)
    - timeframe: Interwał czasowy (domyślnie: 1h)
    
    Timeout: 300 sekund (5 minut)
    """,
    response_description="Wyniki analiz i statystyki",
    tags=["AI Analysis Trigger"]
)
@limiter.limit("10/hour")
async def trigger_manual_analysis(
    request: Request,
    trigger_request: Optional[Dict[str, Any]] = None,
    db: Database = Depends(get_database),
    telegram: TelegramService = Depends(get_telegram_service)
):
    """
    Ręcznie uruchamia cykl analiz AI
    """
    import asyncio
    import time
    from datetime import datetime
    
    try:
        # Parse request body
        symbols = None
        timeframe = "1h"
        
        if trigger_request:
            symbols = trigger_request.get('symbols')
            timeframe = trigger_request.get('timeframe', '1h')
        
        logger.info(f"Manual analysis triggered: symbols={symbols}, timeframe={timeframe}")
        
        # Walidacja timeframe
        valid_timeframes = ['1m', '5m', '15m', '30m', '1h', '4h', '1d']
        if timeframe not in valid_timeframes:
            raise HTTPException(
                status_code=422,
                detail=f"Nieprawidłowy timeframe. Dozwolone: {valid_timeframes}"
            )
        
        # Walidacja symboli
        if symbols:
            if not isinstance(symbols, list):
                raise HTTPException(
                    status_code=422,
                    detail="symbols musi być listą"
                )
            if len(symbols) > 50:
                raise HTTPException(
                    status_code=422,
                    detail="Maksymalnie 50 symboli"
                )
            for symbol in symbols:
                if '/' not in symbol:
                    raise HTTPException(
                        status_code=422,
                        detail=f"Symbol {symbol} musi zawierać '/' (np. EUR/USD)"
                    )
        
        # Utwórz scheduler
        from .services.auto_analysis_scheduler import AutoAnalysisScheduler
        
        scheduler = AutoAnalysisScheduler(
            database=db,
            telegram=telegram,
            interval_minutes=settings.analysis_interval
        )
        
        # Jeśli podano symbole, użyj ich zamiast domyślnych
        if symbols:
            scheduler.symbols = symbols
            logger.info(f"Using custom symbols list: {len(symbols)} symbols")
        else:
            logger.info(f"Using default symbols list: {len(scheduler.symbols)} symbols")
        
        # Uruchom analizę z timeoutem
        start_time = time.time()
        
        try:
            # Timeout 300 sekund (5 minut)
            results = await asyncio.wait_for(
                scheduler.run_analysis_cycle(),
                timeout=300.0
            )
        except asyncio.TimeoutError:
            logger.error("Analysis cycle timeout (300s)")
            raise HTTPException(
                status_code=500,
                detail="Analiza przekroczyła limit czasu (300s). Spróbuj z mniejszą liczbą symboli."
            )
        
        duration = time.time() - start_time
        
        # Pobierz statystyki
        stats = scheduler.get_statistics()
        
        logger.info(f"Manual analysis completed: {len(results)} results in {duration:.1f}s")
        
        return {
            "message": f"Analiza zakończona dla {len(results)} symboli",
            "results": results,
            "statistics": {
                "total_symbols": len(results),
                "successful": stats.get('successful_analyses', 0),
                "failed": stats.get('failed_analyses', 0),
                "total_tokens": stats.get('total_tokens', 0),
                "total_cost": stats.get('total_cost', 0.0),
                "duration_seconds": round(duration, 2)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in manual analysis trigger: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ===== SSE STREAM ENDPOINTS =====

# Global event queue dla SSE
sse_queues = []

async def broadcast_sse_event(event_type: str, data: dict):
    """
    Wysyła event do wszystkich połączonych klientów SSE
    
    Args:
        event_type: Typ eventu (new_analysis, token_update, config_change)
        data: Dane do wysłania
    """
    import json
    import asyncio
    
    message = {
        "event": event_type,
        "data": json.dumps(data)
    }
    
    # Wyślij do wszystkich połączonych klientów
    for queue in sse_queues[:]:  # Kopia listy aby uniknąć modyfikacji podczas iteracji
        try:
            await queue.put(message)
        except Exception as e:
            logger.error(f"Error broadcasting SSE event: {str(e)}")
            # Usuń niedziałające kolejki
            if queue in sse_queues:
                sse_queues.remove(queue)


@app.get("/stream/updates", dependencies=[Depends(verify_api_key)])
async def stream_updates(
    request: Request,
    service: StrategyService = Depends(get_strategy_service),
    db: Database = Depends(get_database)
):
    """
    Server-Sent Events (SSE) endpoint do pushowania aktualizacji danych w czasie rzeczywistym
    Wysyła aktualizacje statystyk, sygnałów i aktywności bez odświeżania strony
    """
    import asyncio
    import json
    
    async def event_generator():
        """Generator zdarzeń SSE"""
        try:
            while True:
                # Sprawdź czy klient nadal jest połączony
                if await request.is_disconnected():
                    break
                
                try:
                    # Pobierz aktualne dane
                    stats = service.get_statistics()
                    signals = service.get_recent_signals(limit=20)
                    activity_logs = db.get_recent_activity_logs(limit=10)
                    
                    # Wyślij dane jako JSON
                    data = {
                        "type": "update",
                        "timestamp": datetime.now().isoformat(),
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
                        "timestamp": datetime.now().isoformat()
                    }
                    yield f"data: {json.dumps(error_data)}\n\n"
                
                # Czekaj 5 sekund przed następną aktualizacją
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
            "X-Accel-Buffering": "no"
        }
    )


@app.get(
    "/stream/ai-updates",
    dependencies=[Depends(verify_api_key)],
    summary="SSE stream dla aktualizacji AI",
    description="""
    Server-Sent Events stream dla real-time aktualizacji analiz AI.
    
    Eventy:
    - new_analysis: Nowa analiza została zapisana
    - token_update: Aktualizacja statystyk tokenów
    - config_change: Zmiana konfiguracji analiz
    
    Połączenie jest utrzymywane do momentu rozłączenia klienta.
    """,
    response_description="SSE stream z eventami AI",
    tags=["SSE Streams"]
)
async def stream_ai_updates(
    request: Request,
    db: Database = Depends(get_database)
):
    """
    Server-Sent Events stream dla real-time aktualizacji AI analiz
    """
    import asyncio
    import json
    
    async def sse_generator():
        """Generator dla Server-Sent Events"""
        queue = asyncio.Queue()
        sse_queues.append(queue)
        
        try:
            # Wyślij początkowe dane
            try:
                token_stats = db.get_token_statistics()
                config = db.get_analysis_config()
                
                # Parse enabled_symbols
                if config.get('enabled_symbols'):
                    try:
                        config['enabled_symbols'] = json.loads(config['enabled_symbols'])
                    except:
                        config['enabled_symbols'] = []
                
                # Wyślij początkowe statystyki
                yield f"event: token_update\ndata: {json.dumps(token_stats)}\n\n"
                yield f"event: config_change\ndata: {json.dumps(config)}\n\n"
                
            except Exception as e:
                logger.error(f"Error sending initial SSE data: {str(e)}")
            
            # Główna pętla - czekaj na eventy
            while True:
                # Sprawdź czy klient nadal jest połączony
                if await request.is_disconnected():
                    break
                
                try:
                    # Czekaj na event z timeout
                    data = await asyncio.wait_for(queue.get(), timeout=30.0)
                    
                    # Wyślij event
                    yield f"event: {data['event']}\ndata: {data['data']}\n\n"
                    
                except asyncio.TimeoutError:
                    # Wyślij heartbeat co 30 sekund
                    yield f": heartbeat\n\n"
                    
                except Exception as e:
                    logger.error(f"Error in SSE generator: {str(e)}")
                    
        except asyncio.CancelledError:
            logger.info("SSE AI stream cancelled")
        except Exception as e:
            logger.error(f"SSE AI stream error: {str(e)}", exc_info=True)
        finally:
            # Cleanup - usuń kolejkę z listy
            if queue in sse_queues:
                sse_queues.remove(queue)
    
    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# Startup
@app.on_event("startup")
async def startup_event():
    """Inicjalizacja przy starcie"""
    logger.info(f"🚀 Starting Trading Bot API")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Database: {settings.database_path}")
    logger.info(f"Check interval: {settings.check_interval} min")
    
    # Loguj zarejestrowane route'y dla debugowania
    routes = [f"{route.methods} {route.path}" for route in app.routes if hasattr(route, 'path')]
    logger.info(f"📋 Zarejestrowane route'y: {len(routes)}")
    for route in routes[:30]:
        logger.info(f"  - {route}")
    activity_logs_routes = [r for r in routes if 'activity-logs' in r]
    if activity_logs_routes:
        logger.info(f"✅ Endpoint /activity-logs zarejestrowany: {activity_logs_routes}")
    else:
        logger.warning("⚠️ Endpoint /activity-logs NIE został zarejestrowany!")
        logger.warning(f"⚠️ Szukam w wszystkich route'ach: {[r for r in routes if 'activity' in r.lower()]}")
    
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
