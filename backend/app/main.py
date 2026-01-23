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

from .config import get_settings, get_polish_time
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


async def verify_api_key(
    api_key: str = Security(api_key_header),
    api_key_query: Optional[str] = Query(None, alias="api_key")
):
    """
    Weryfikacja klucza API z nagłówka lub parametru URL.
    Parametr URL jest używany dla SSE (EventSource nie obsługuje custom headers).
    """
    # Sprawdź klucz z nagłówka lub z parametru URL
    key = api_key or api_key_query
    
    if not key:
        logger.warning("Brak klucza API w żądaniu (header i query)")
        raise HTTPException(
            status_code=403,
            detail="Brak klucza API. Dodaj header X-API-Key lub parametr ?api_key="
        )
    if key != settings.api_key:
        logger.warning(f"Nieprawidłowy klucz API: {key[:10]}...")
        raise HTTPException(
            status_code=403,
            detail="Nieprawidłowy klucz API"
        )
    return key


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
    start_time = get_polish_time()
    
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
        duration = (get_polish_time() - start_time).total_seconds()
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
        "timestamp": get_polish_time().isoformat()
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
        "timestamp": get_polish_time().isoformat()
    }


@app.post("/telegram/test-message", dependencies=[Depends(verify_api_key)])
@limiter.limit("5/minute")
async def test_telegram_message(
    request: Request,
    telegram: TelegramService = Depends(get_telegram_service),
    db: Database = Depends(get_database)
):
    """
    Testowe wysłanie wiadomości na Telegram
    
    Wysyła testowy sygnał BUY dla EUR/USD z przykładowymi wskaźnikami.
    Przydatne do weryfikacji działania integracji z Telegram.
    """
    try:
        logger.info("Sending test Telegram message")
        
        success = await telegram.send_signal(
            signal_type="BUY",
            strategy_name="Test Strategy",
            symbol="EUR/USD",
            price=1.0850,
            indicator_values={"RSI": 35.5, "MACD": 0.0012}
        )
        
        if success:
            logger.info("Test message sent successfully")
            return {
                "success": True,
                "message": "Testowa wiadomość została wysłana na Telegram",
                "timestamp": get_polish_time().isoformat()
            }
        else:
            logger.error("Failed to send test message")
            raise HTTPException(
                status_code=500,
                detail="Nie udało się wysłać wiadomości na Telegram"
            )
    except Exception as e:
        logger.error(f"Error sending test message: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/telegram/get-chat-id")
@limiter.limit("10/minute")
async def get_chat_id_instructions(request: Request):
    """
    Wyświetla instrukcje jak uzyskać Telegram CHAT_ID
    
    Ten endpoint nie wymaga autoryzacji, aby ułatwić konfigurację.
    """
    instructions = {
        "message": "Jak uzyskać Telegram CHAT_ID",
        "steps": [
            "1. Napisz wiadomość do swojego bota na Telegramie (np. /start)",
            "2. Użyj endpointu GET /telegram/get-updates (wymaga API key)",
            "3. Znajdź w odpowiedzi pole 'from' -> 'id' - to jest Twój CHAT_ID",
            "4. Zmień wartość TELEGRAM_CHAT_ID w pliku .env na ten ID",
            "5. Zrestartuj aplikację (docker compose restart)",
            "6. Przetestuj przez endpoint POST /telegram/test-message"
        ],
        "example_chat_id": 123456789,
        "note": "CHAT_ID to liczba identyfikująca Ciebie jako użytkownika, NIE ID bota"
    }
    return instructions


@app.get("/telegram/get-updates", dependencies=[Depends(verify_api_key)])
@limiter.limit("10/minute")
async def get_telegram_updates(
    request: Request,
    telegram: TelegramService = Depends(get_telegram_service)
):
    """
    Pobiera ostatnie wiadomości od użytkowników (do znalezienia CHAT_ID)
    
    Wysyła zapytanie getUpdates do Telegram API i zwraca ostatnie wiadomości.
    Użyj tego aby znaleźć swój CHAT_ID po wysłaniu wiadomości do bota.
    """
    try:
        updates = await telegram.get_updates(limit=10)
        
        if updates is None:
            raise HTTPException(
                status_code=500,
                detail="Nie udało się pobrać wiadomości z Telegram API"
            )
        
        if not updates:
            return {
                "success": True,
                "message": "Brak wiadomości. Napisz /start do bota i spróbuj ponownie.",
                "updates": []
            }
        
        chat_ids = []
        for update in updates:
            if "message" in update:
                msg = update["message"]
                if "from" in msg:
                    chat_ids.append({
                        "chat_id": msg["from"]["id"],
                        "username": msg["from"].get("username", "brak"),
                        "first_name": msg["from"].get("first_name", ""),
                        "text": msg.get("text", "")[:50]
                    })
        
        return {
            "success": True,
            "message": f"Znaleziono {len(chat_ids)} wiadomości",
            "chat_ids": chat_ids,
            "raw_updates": updates,
            "instructions": "Skopiuj 'chat_id' z powyższej listy do .env jako TELEGRAM_CHAT_ID"
        }
        
    except Exception as e:
        logger.error(f"Error getting updates: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Błąd pobierania wiadomości: {str(e)}"
        )


@app.post("/telegram/test-connection", dependencies=[Depends(verify_api_key)])
@limiter.limit("5/minute")
async def test_telegram_connection(
    request: Request,
    telegram: TelegramService = Depends(get_telegram_service)
):
    """
    Testuje połączenie z botem i możliwość wysyłania wiadomości
    
    Sprawdza czy bot działa i czy może wysłać wiadomość do podanego CHAT_ID.
    """
    try:
        result = await telegram.test_connection_with_chat()
        
        if not result["bot_connected"]:
            raise HTTPException(
                status_code=500,
                detail="Bot nie jest połączony. Sprawdź TELEGRAM_BOT_TOKEN."
            )
        
        return {
            "success": True,
            "bot_connected": result["bot_connected"],
            "bot_info": result["bot_info"],
            "chat_test_sent": result["chat_test"],
            "error": result["error"],
            "message": "Test połączenia zakończony" if result["chat_test"] else "Błąd wysyłki do CHAT_ID"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing connection: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Błąd testowania połączenia: {str(e)}"
        )


@app.get("/telegram/statistics", dependencies=[Depends(verify_api_key)])
@limiter.limit("30/minute")
async def get_telegram_statistics(
    request: Request,
    db: Database = Depends(get_database),
    telegram: TelegramService = Depends(get_telegram_service)
):
    """
    Pobiera statystyki wysłanych wiadomości Telegram
    
    Returns:
        - today: Liczba wiadomości wysłanych dzisiaj
        - week: Liczba wiadomości z ostatnich 7 dni
        - botConnected: Status połączenia z botem
        - lastMessage: Ostatnia wysłana wiadomość (timestamp i treść)
    """
    try:
        from datetime import timedelta
        
        logger.info("Getting Telegram statistics")
        
        # Sprawdź połączenie z botem
        bot_connected = await telegram.check_connection()
        
        # Pobierz logi telegram z ostatnich 7 dni
        all_logs = db.get_activity_logs_by_type('telegram', limit=1000)
        
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = now - timedelta(days=7)
        
        today_count = 0
        week_count = 0
        last_message = None
        
        for log in all_logs:
            log_time = datetime.fromisoformat(log['timestamp'])
            
            if log_time >= today_start:
                today_count += 1
            if log_time >= week_ago:
                week_count += 1
            
            if not last_message and log['status'] == 'success':
                last_message = {
                    'timestamp': log['timestamp'],
                    'message': log['message']
                }
        
        logger.info(f"Telegram statistics: today={today_count}, week={week_count}, connected={bot_connected}")
        
        return {
            'today': today_count,
            'week': week_count,
            'botConnected': bot_connected,
            'lastMessage': last_message
        }
    except Exception as e:
        logger.error(f"Error getting Telegram statistics: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/telegram/settings", dependencies=[Depends(verify_api_key)])
@limiter.limit("30/minute")
async def get_telegram_settings(
    request: Request,
    db: Database = Depends(get_database)
):
    """
    Pobiera aktualne ustawienia powiadomień Telegram
    
    Returns:
        Dict z ustawieniami powiadomień
    """
    try:
        settings = db.get_telegram_settings()
        mute_status = db.get_mute_status()
        
        return {
            'success': True,
            'settings': settings,
            'mute_status': mute_status
        }
    except Exception as e:
        logger.error(f"Error getting telegram settings: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/telegram/settings", dependencies=[Depends(verify_api_key)])
@limiter.limit("10/minute")
async def update_telegram_settings(
    request: Request,
    settings: Dict[str, Any],
    db: Database = Depends(get_database)
):
    """
    Aktualizuje ustawienia powiadomień Telegram
    
    Body może zawierać:
    - notifications_enabled: bool
    - allowed_hours_start: str (format HH:MM)
    - allowed_hours_end: str (format HH:MM)
    - allowed_days: str (np. "1,2,3,4,5" dla Pn-Pt)
    """
    try:
        allowed_fields = [
            'notifications_enabled',
            'allowed_hours_start',
            'allowed_hours_end',
            'allowed_days'
        ]
        
        updates = {k: v for k, v in settings.items() if k in allowed_fields}
        
        if not updates:
            raise HTTPException(
                status_code=400,
                detail="Brak prawidłowych pól do aktualizacji"
            )
        
        success = db.update_telegram_settings(updates)
        
        if success:
            new_settings = db.get_telegram_settings()
            return {
                'success': True,
                'message': 'Ustawienia zaktualizowane',
                'settings': new_settings
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Nie udało się zaktualizować ustawień"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating telegram settings: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/telegram/mute", dependencies=[Depends(verify_api_key)])
@limiter.limit("10/minute")
async def mute_telegram_notifications(
    request: Request,
    db: Database = Depends(get_database)
):
    """
    Wycisza powiadomienia Telegram na określony czas
    
    Body: {"duration": "1h|4h|8h|12h|24h"}
    """
    try:
        from datetime import timedelta
        
        body = await request.json()
        duration = body.get('duration')
        
        duration_map = {
            '1h': timedelta(hours=1),
            '4h': timedelta(hours=4),
            '8h': timedelta(hours=8),
            '12h': timedelta(hours=12),
            '24h': timedelta(hours=24),
            '1d': timedelta(days=1)
        }
        
        if duration not in duration_map:
            raise HTTPException(
                status_code=400,
                detail=f"Nieprawidłowy duration. Dozwolone: {list(duration_map.keys())}"
            )
        
        muted_until = get_polish_time() + duration_map[duration]
        muted_until_str = muted_until.isoformat()
        
        success = db.set_mute_until(muted_until_str)
        
        if success:
            return {
                'success': True,
                'message': f'Powiadomienia wyciszone na {duration}',
                'muted_until': muted_until_str
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Nie udało się wyciszyć powiadomień"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error muting notifications: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/telegram/unmute", dependencies=[Depends(verify_api_key)])
@limiter.limit("10/minute")
async def unmute_telegram_notifications(
    request: Request,
    db: Database = Depends(get_database)
):
    """
    Wyłącza wyciszenie powiadomień Telegram
    """
    try:
        success = db.set_mute_until(None)
        
        if success:
            return {
                'success': True,
                'message': 'Wyciszenie wyłączone'
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Nie udało się wyłączyć wyciszenia"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unmuting notifications: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/telegram/toggle", dependencies=[Depends(verify_api_key)])
@limiter.limit("10/minute")
async def toggle_telegram_notifications(
    request: Request,
    db: Database = Depends(get_database)
):
    """
    Przełącza powiadomienia Telegram ON/OFF
    
    Returns:
        Nowy stan powiadomień
    """
    try:
        new_state = db.toggle_telegram_notifications()
        
        return {
            'success': True,
            'enabled': new_state,
            'message': f"Powiadomienia {'włączone' if new_state else 'wyłączone'}"
        }
            
    except Exception as e:
        logger.error(f"Error toggling notifications: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


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


# ===== CHART DATA ENDPOINTS =====

@app.get("/chart-data", dependencies=[Depends(verify_api_key)])
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def get_chart_data(
    request: Request,
    symbol: str = Query(..., description="Symbol (np. EUR/USD, AAPL/USD)"),
    timeframe: str = Query("1h", description="Timeframe (1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w)"),
    period: str = Query("1mo", description="Okres danych (1d, 5d, 1mo, 3mo, 6mo, 1y)")
):
    """
    Pobiera dane OHLCV oraz wskaźniki techniczne dla wykresów
    
    Ten endpoint zwraca dane w formacie kompatybilnym z TradingView Lightweight Charts:
    - Świece OHLC z Unix timestamp
    - Wskaźniki techniczne: RSI, MACD, Bollinger Bands, Moving Averages
    - Aktualną cenę
    
    Args:
        symbol: Symbol do analizy (np. EUR/USD, AAPL/USD)
        timeframe: Interwał czasowy świec (1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w)
        period: Okres historyczny danych (1d, 5d, 1mo, 3mo, 6mo, 1y)
    
    Returns:
        JSON z danymi OHLCV, wskaźnikami i aktualną ceną
    """
    try:
        # Import serwisu do pobierania danych rynkowych
        from .services.market_data_service import MarketDataService
        
        logger.info(f"Fetching chart data: {symbol} ({timeframe}, {period})")
        
        # Walidacja timeframe - sprawdzamy czy podany timeframe jest prawidłowy
        valid_timeframes = ['1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w']
        if timeframe not in valid_timeframes:
            raise HTTPException(
                status_code=400,
                detail=f"Nieprawidłowy timeframe. Dozwolone: {', '.join(valid_timeframes)}"
            )
        
        # Walidacja period - sprawdzamy czy podany okres jest prawidłowy
        valid_periods = ['1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y']
        if period not in valid_periods:
            raise HTTPException(
                status_code=400,
                detail=f"Nieprawidłowy period. Dozwolone: {', '.join(valid_periods)}"
            )
        
        # Tworzymy instancję serwisu do pobierania danych rynkowych
        market_service = MarketDataService()
        
        # Pobieramy historyczne dane OHLCV (Open, High, Low, Close, Volume)
        # await - czekamy na zakończenie asynchronicznego pobierania danych
        data = await market_service.get_historical_data(
            symbol=symbol,
            timeframe=timeframe,
            period=period
        )
        
        # Jeśli nie udało się pobrać danych, zwracamy błąd 404
        if data is None or data.empty:
            logger.warning(f"No data available for {symbol}")
            raise HTTPException(
                status_code=404,
                detail=f"Brak danych dla symbolu {symbol}. Sprawdź czy symbol jest prawidłowy."
            )
        
        logger.info(f"Retrieved {len(data)} candles for {symbol}")
        
        # ===== FORMATOWANIE DANYCH DO FORMATU LIGHTWEIGHT CHARTS =====
        
        # Konwertujemy DataFrame pandas na listę świec w formacie dla Lightweight Charts
        # Każda świeca to słownik z time (Unix timestamp) i wartościami OHLC
        candles = []
        for index, row in data.iterrows():
            # Konwertujemy datetime index na Unix timestamp (sekundy od 1970-01-01)
            # Lightweight Charts wymaga timestampu w sekundach, nie milisekundach
            timestamp = int(index.timestamp())
            
            candles.append({
                "time": timestamp,  # Unix timestamp w sekundach
                "open": float(row['Open']),    # Cena otwarcia
                "high": float(row['High']),    # Najwyższa cena
                "low": float(row['Low']),      # Najniższa cena
                "close": float(row['Close'])   # Cena zamknięcia
            })
        
        # ===== OBLICZANIE WSKAŹNIKÓW TECHNICZNYCH =====
        
        # Inicjalizujemy słownik dla wszystkich wskaźników
        indicators = {
            "rsi": [],
            "macd": {
                "macd_line": [],
                "signal_line": [],
                "histogram": []
            },
            "bollinger": {
                "upper": [],
                "middle": [],
                "lower": []
            },
            "sma50": [],
            "sma200": []
        }
        
        # --- RSI (Relative Strength Index) ---
        # RSI mierzy siłę trendu (0-100), oversold < 30, overbought > 70
        try:
            # Obliczamy RSI dla każdego punktu w czasie
            for i in range(14, len(data)):  # RSI wymaga minimum 14 świec
                # Bierzemy ostatnie 15 świec (14 + aktualna)
                subset = data.iloc[max(0, i-14):i+1]
                rsi_value = market_service.calculate_rsi(subset, period=14)
                
                if rsi_value is not None:
                    timestamp = int(data.index[i].timestamp())
                    indicators["rsi"].append({
                        "time": timestamp,
                        "value": float(rsi_value)
                    })
        except Exception as e:
            logger.warning(f"Error calculating RSI: {e}")
        
        # --- MACD (Moving Average Convergence Divergence) ---
        # MACD pokazuje momentum trendu przez różnicę między szybką i wolną EMA
        try:
            # MACD wymaga minimum 26 + 9 = 35 świec
            for i in range(35, len(data)):
                subset = data.iloc[:i+1]
                macd_data = market_service.calculate_macd(
                    subset,
                    fast_period=12,
                    slow_period=26,
                    signal_period=9
                )
                
                if macd_data:
                    timestamp = int(data.index[i].timestamp())
                    indicators["macd"]["macd_line"].append({
                        "time": timestamp,
                        "value": float(macd_data['value'])
                    })
                    indicators["macd"]["signal_line"].append({
                        "time": timestamp,
                        "value": float(macd_data['signal'])
                    })
                    indicators["macd"]["histogram"].append({
                        "time": timestamp,
                        "value": float(macd_data['histogram'])
                    })
        except Exception as e:
            logger.warning(f"Error calculating MACD: {e}")
        
        # --- Bollinger Bands ---
        # Bollinger Bands pokazują zmienność ceny (upper/middle/lower bands)
        try:
            # Bollinger wymaga minimum 20 świec
            for i in range(20, len(data)):
                subset = data.iloc[max(0, i-20):i+1]
                bb_data = market_service.calculate_bollinger_bands(
                    subset,
                    period=20,
                    std_dev=2.0
                )
                
                if bb_data:
                    timestamp = int(data.index[i].timestamp())
                    indicators["bollinger"]["upper"].append({
                        "time": timestamp,
                        "value": float(bb_data['upper'])
                    })
                    indicators["bollinger"]["middle"].append({
                        "time": timestamp,
                        "value": float(bb_data['middle'])
                    })
                    indicators["bollinger"]["lower"].append({
                        "time": timestamp,
                        "value": float(bb_data['lower'])
                    })
        except Exception as e:
            logger.warning(f"Error calculating Bollinger Bands: {e}")
        
        # --- Moving Averages (SMA 50 i SMA 200) ---
        # Moving Averages pokazują średni trend ceny
        try:
            # SMA 50 - średnia z ostatnich 50 świec
            for i in range(50, len(data)):
                subset = data.iloc[max(0, i-50):i+1]
                close_prices = subset['Close']
                sma50_value = float(close_prices.mean())
                
                timestamp = int(data.index[i].timestamp())
                indicators["sma50"].append({
                    "time": timestamp,
                    "value": sma50_value
                })
            
            # SMA 200 - średnia z ostatnich 200 świec (długoterminowy trend)
            for i in range(200, len(data)):
                subset = data.iloc[max(0, i-200):i+1]
                close_prices = subset['Close']
                sma200_value = float(close_prices.mean())
                
                timestamp = int(data.index[i].timestamp())
                indicators["sma200"].append({
                    "time": timestamp,
                    "value": sma200_value
                })
        except Exception as e:
            logger.warning(f"Error calculating Moving Averages: {e}")
        
        # Pobieramy aktualną cenę (ostatnia cena zamknięcia)
        current_price = float(data['Close'].iloc[-1])
        
        # Zwracamy kompletne dane w formacie JSON
        result = {
            "symbol": symbol,
            "timeframe": timeframe,
            "period": period,
            "candles": candles,
            "indicators": indicators,
            "current_price": current_price,
            "data_points": len(candles)
        }
        
        logger.info(f"Chart data prepared: {len(candles)} candles, {len(indicators['rsi'])} RSI points")
        
        return result
        
    except HTTPException:
        # Przepuszczamy HTTPException bez zmian (już mają odpowiedni status code)
        raise
    except Exception as e:
        # Logujemy nieoczekiwane błędy i zwracamy 500
        logger.error(f"Error fetching chart data for {symbol}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Błąd pobierania danych wykresu: {str(e)}"
        )


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
