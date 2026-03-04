"""
Router dla endpointów Telegram
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from datetime import datetime, timedelta
from typing import Dict, Any

from .dependencies import verify_api_key, get_database, get_telegram_service, settings
from ..config import get_polish_time
from ..utils.logger import setup_logger

limiter = Limiter(key_func=get_remote_address)
logger = setup_logger(name="trading_bot", log_file=settings.log_file, level=settings.log_level)

router = APIRouter(prefix="/telegram", tags=["Telegram"])


@router.post("/test-message", dependencies=[Depends(verify_api_key)])
@limiter.limit("5/minute")
async def test_telegram_message(
    request: Request,
    telegram=Depends(get_telegram_service),
    db=Depends(get_database)
) -> Dict[str, Any]:
    """Wysyła testową wiadomość sygnału na skonfigurowany chat Telegram.

    Returns:
        Słownik z success, message, timestamp.

    Raises:
        HTTPException: 500 przy błędzie wysyłki.
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


@router.get("/get-chat-id")
@limiter.limit("10/minute")
async def get_chat_id_instructions(request: Request) -> Dict[str, Any]:
    """Zwraca instrukcję jak uzyskać Telegram CHAT_ID (bez API key).

    Returns:
        Słownik z message, steps, example_chat_id, note.
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


@router.get("/get-updates", dependencies=[Depends(verify_api_key)])
@limiter.limit("10/minute")
async def get_telegram_updates(
    request: Request,
    telegram=Depends(get_telegram_service)
) -> Dict[str, Any]:
    """Pobiera ostatnie wiadomości z Telegram API (do znalezienia CHAT_ID).

    Returns:
        Słownik z success, message, updates, chat_ids.

    Raises:
        HTTPException: 500 gdy nie udało się pobrać updates.
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


@router.post("/test-connection", dependencies=[Depends(verify_api_key)])
@limiter.limit("5/minute")
async def test_telegram_connection(
    request: Request,
    telegram=Depends(get_telegram_service)
) -> Dict[str, Any]:
    """Testuje połączenie z botem Telegram i wysyłkę do skonfigurowanego CHAT_ID.

    Returns:
        Słownik z success, bot_connected, bot_info, chat_test_sent, error, message.

    Raises:
        HTTPException: 500 gdy bot nie połączony lub błąd testu.
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


@router.get("/statistics", dependencies=[Depends(verify_api_key)])
@limiter.limit("30/minute")
async def get_telegram_statistics(
    request: Request,
    db=Depends(get_database),
    telegram=Depends(get_telegram_service)
) -> Dict[str, Any]:
    """Pobiera statystyki wysłanych wiadomości Telegram (dzisiaj, tydzień, ostatnia).

    Returns:
        Słownik z today, week, botConnected, lastMessage.

    Raises:
        HTTPException: 500 przy błędzie.
    """
    try:
        logger.info("Getting Telegram statistics")
        
        bot_connected = await telegram.check_connection()
        
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


@router.get("/settings", dependencies=[Depends(verify_api_key)])
@limiter.limit("30/minute")
async def get_telegram_settings(
    request: Request,
    db=Depends(get_database)
) -> Dict[str, Any]:
    """Pobiera aktualne ustawienia powiadomień Telegram i status wyciszenia.

    Returns:
        Słownik z success, settings, mute_status.

    Raises:
        HTTPException: 500 przy błędzie.
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


@router.put("/settings", dependencies=[Depends(verify_api_key)])
@limiter.limit("10/minute")
async def update_telegram_settings(
    request: Request,
    settings: Dict[str, Any],
    db=Depends(get_database)
) -> Dict[str, Any]:
    """Aktualizuje ustawienia powiadomień Telegram (notifications_enabled, parse_mode, itd.).

    Args:
        settings: Słownik z polami do aktualizacji.

    Returns:
        Słownik z success, message, settings.

    Raises:
        HTTPException: 400 przy nieprawidłowych polach, 500 przy błędzie.
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


@router.post("/mute", dependencies=[Depends(verify_api_key)])
@limiter.limit("10/minute")
async def mute_telegram_notifications(
    request: Request,
    db=Depends(get_database)
) -> Dict[str, Any]:
    """Wycisza powiadomienia Telegram na wybrany czas (1h, 4h, 8h, 12h, 24h, 1d).

    Returns:
        Słownik z success, message, muted_until.

    Raises:
        HTTPException: 400 przy nieprawidłowym duration, 500 przy błędzie.
    """
    try:
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


@router.post("/unmute", dependencies=[Depends(verify_api_key)])
@limiter.limit("10/minute")
async def unmute_telegram_notifications(
    request: Request,
    db=Depends(get_database)
) -> Dict[str, Any]:
    """Wyłącza wyciszenie – przywraca wysyłanie powiadomień Telegram.

    Returns:
        Słownik z success, message.

    Raises:
        HTTPException: 500 przy błędzie.
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


@router.post("/toggle", dependencies=[Depends(verify_api_key)])
@limiter.limit("10/minute")
async def toggle_telegram_notifications(
    request: Request,
    db=Depends(get_database)
) -> Dict[str, Any]:
    """Przełącza globalne włącz/wyłącz powiadomień Telegram.

    Returns:
        Słownik z success, enabled, message.

    Raises:
        HTTPException: 500 przy błędzie.
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
