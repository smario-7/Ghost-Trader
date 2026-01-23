"""
Serwis Telegram Bot
"""
import aiohttp
from typing import Optional, Dict, Any
import logging
from ..config import get_polish_time


class TelegramService:
    """Serwis do komunikacji z Telegram Bot API"""
    
    def __init__(self, bot_token: str, chat_id: str, database=None):
        """
        Inicjalizacja serwisu Telegram
        
        Args:
            bot_token: Token bota z @BotFather
            chat_id: ID czatu do wysyłania wiadomości
            database: Instancja bazy danych (opcjonalne, do logowania aktywności)
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.logger = logging.getLogger("trading_bot.telegram")
        self.database = database
    
    def should_send_notification(self) -> tuple:
        """
        Sprawdza czy można wysłać powiadomienie na podstawie ustawień
        
        Returns:
            tuple: (can_send: bool, reason: str) - czy wysłać i powód
        """
        if not self.database:
            return True, "OK - brak bazy danych"
        
        try:
            settings = self.database.get_telegram_settings()
            
            if not settings.get('notifications_enabled', True):
                return False, "Powiadomienia wyłączone"
            
            muted_until = settings.get('muted_until')
            if muted_until:
                from datetime import datetime
                try:
                    muted_date = datetime.fromisoformat(muted_until.replace('Z', '+00:00'))
                    if get_polish_time() < muted_date:
                        return False, f"Wyciszone do {muted_until}"
                except:
                    pass
            
            from datetime import datetime
            now_time = get_polish_time().time()
            
            try:
                start_time = datetime.strptime(settings.get('allowed_hours_start', '00:00'), '%H:%M').time()
                end_time = datetime.strptime(settings.get('allowed_hours_end', '23:59'), '%H:%M').time()
                
                if not (start_time <= now_time <= end_time):
                    return False, f"Poza godzinami ({start_time.strftime('%H:%M')}-{end_time.strftime('%H:%M')})"
            except:
                pass
            
            today = get_polish_time().isoweekday()
            allowed_days_str = settings.get('allowed_days', '1,2,3,4,5,6,7')
            
            try:
                allowed_days = [int(d.strip()) for d in allowed_days_str.split(',') if d.strip()]
                if today not in allowed_days:
                    days_names = ['Pn', 'Wt', 'Śr', 'Czw', 'Pt', 'Sb', 'Nd']
                    return False, f"Dzień tygodnia nie dozwolony ({days_names[today-1]})"
            except:
                pass
            
            return True, "OK"
            
        except Exception as e:
            self.logger.error(f"Błąd sprawdzania ustawień powiadomień: {e}")
            return True, "OK - błąd sprawdzania ustawień"
    
    async def send_message(
        self,
        text: str,
        parse_mode: str = "HTML",
        disable_notification: bool = False
    ) -> bool:
        """
        Wysyła wiadomość przez Telegram
        
        Args:
            text: Treść wiadomości
            parse_mode: Format parsowania (HTML, Markdown, MarkdownV2)
            disable_notification: Czy wyłączyć powiadomienie
        
        Returns:
            True jeśli wysłano pomyślnie
        """
        url = f"{self.base_url}/sendMessage"
        
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_notification": disable_notification
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=10) as response:
                    if response.status == 200:
                        self.logger.info(f"📱 Message sent: {text[:50]}...")
                        return True
                    else:
                        error_text = await response.text()
                        self.logger.error(
                            f"Telegram API error: {response.status} - {error_text}"
                        )
                        return False
        except aiohttp.ClientError as e:
            self.logger.error(f"Network error sending message: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error sending message: {e}")
            return False
    
    async def send_signal(
        self,
        signal_type: str,
        strategy_name: str,
        symbol: str,
        price: float,
        indicator_values: Dict[str, Any] = None
    ) -> bool:
        """
        Wysyła sygnał tradingowy
        
        Args:
            signal_type: BUY, SELL, HOLD
            strategy_name: Nazwa strategii
            symbol: Symbol (np. EUR/USD)
            price: Cena
            indicator_values: Wartości wskaźników
        
        Returns:
            True jeśli wysłano pomyślnie
        """
        can_send, reason = self.should_send_notification()
        
        if not can_send:
            self.logger.info(f"Pominięto powiadomienie Telegram: {reason}")
            if self.database:
                self.database.create_activity_log(
                    log_type='telegram',
                    message=f"Powiadomienie pominięte: {reason}",
                    symbol=symbol,
                    strategy_name=strategy_name,
                    details={'signal_type': signal_type, 'reason': reason},
                    status='info'
                )
            return True
        
        # Emoji dla różnych typów sygnałów
        emoji_map = {
            "BUY": "🟢",
            "SELL": "🔴",
            "HOLD": "⚪"
        }
        emoji = emoji_map.get(signal_type, "⚪")
        
        # Formatuj wiadomość
        message = f"""
{emoji} <b>{signal_type} SIGNAL</b>

<b>Symbol:</b> {symbol}
<b>Price:</b> ${price:,.2f}
<b>Strategy:</b> {strategy_name}
"""
        
        # Dodaj wskaźniki jeśli są dostępne
        if indicator_values:
            message += "\n<b>Indicators:</b>\n"
            for key, value in indicator_values.items():
                # Formatuj wartości
                if isinstance(value, float):
                    formatted_value = f"{value:.2f}"
                else:
                    formatted_value = str(value)
                message += f"  • {key}: {formatted_value}\n"
        
        # Dodaj timestamp
        timestamp = get_polish_time().strftime("%Y-%m-%d %H:%M:%S")
        message += f"\n<i>Time: {timestamp}</i>"
        
        # Loguj przed wysyłką
        if self.database:
            self.database.create_activity_log(
                log_type='telegram',
                message=f"Wysyłanie sygnału {signal_type} na Telegram",
                symbol=symbol,
                strategy_name=strategy_name,
                details={
                    'signal_type': signal_type,
                    'price': price,
                    'indicator_values': indicator_values or {}
                },
                status='success'
            )
        
        result = await self.send_message(message)
        
        # Loguj po wysyłce
        if self.database:
            if result:
                self.database.create_activity_log(
                    log_type='telegram',
                    message=f"Sygnał {signal_type} wysłany pomyślnie na Telegram",
                    symbol=symbol,
                    strategy_name=strategy_name,
                    details={'signal_type': signal_type},
                    status='success'
                )
            else:
                self.database.create_activity_log(
                    log_type='telegram',
                    message=f"Błąd wysyłki sygnału {signal_type} na Telegram",
                    symbol=symbol,
                    strategy_name=strategy_name,
                    details={'signal_type': signal_type},
                    status='error'
                )
        
        return result
    
    async def send_alert(
        self,
        title: str,
        message: str,
        level: str = "INFO"
    ) -> bool:
        """
        Wysyła alert/powiadomienie
        
        Args:
            title: Tytuł alertu
            message: Treść
            level: Poziom (INFO, WARNING, ERROR)
        
        Returns:
            True jeśli wysłano pomyślnie
        """
        emoji_map = {
            "INFO": "ℹ️",
            "WARNING": "⚠️",
            "ERROR": "❌",
            "SUCCESS": "✅"
        }
        emoji = emoji_map.get(level, "ℹ️")
        
        formatted_message = f"""
{emoji} <b>{title}</b>

{message}
"""
        
        return await self.send_message(formatted_message)
    
    async def check_connection(self) -> bool:
        """
        Sprawdza połączenie z Telegram Bot API
        
        Returns:
            True jeśli bot jest aktywny
        """
        url = f"{self.base_url}/getMe"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("ok"):
                            bot_info = data.get("result", {})
                            self.logger.info(
                                f"Bot connected: @{bot_info.get('username', 'unknown')}"
                            )
                            return True
                    return False
        except Exception as e:
            self.logger.error(f"Connection check failed: {e}")
            return False
    
    async def get_bot_info(self) -> Optional[Dict[str, Any]]:
        """
        Pobiera informacje o bocie
        
        Returns:
            Słownik z informacjami o bocie lub None
        """
        url = f"{self.base_url}/getMe"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("ok"):
                            return data.get("result")
        except Exception as e:
            self.logger.error(f"Failed to get bot info: {e}")
        
        return None
    
    async def send_photo(
        self,
        photo_url: str,
        caption: str = None
    ) -> bool:
        """
        Wysyła zdjęcie
        
        Args:
            photo_url: URL zdjęcia
            caption: Podpis (opcjonalnie)
        
        Returns:
            True jeśli wysłano pomyślnie
        """
        url = f"{self.base_url}/sendPhoto"
        
        payload = {
            "chat_id": self.chat_id,
            "photo": photo_url
        }
        
        if caption:
            payload["caption"] = caption
            payload["parse_mode"] = "HTML"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=10) as response:
                    return response.status == 200
        except Exception as e:
            self.logger.error(f"Failed to send photo: {e}")
            return False
    
    async def get_updates(self, limit: int = 10) -> Optional[list]:
        """
        Pobiera ostatnie wiadomości od użytkowników
        Użyteczne do znalezienia CHAT_ID
        
        Args:
            limit: Maksymalna liczba wiadomości do pobrania
        
        Returns:
            Lista wiadomości lub None
        """
        url = f"{self.base_url}/getUpdates"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params={"limit": limit}, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("ok"):
                            return data.get("result", [])
                    return None
        except Exception as e:
            self.logger.error(f"Failed to get updates: {e}")
            return None
    
    async def test_connection_with_chat(self) -> Dict[str, Any]:
        """
        Testuje połączenie z botem i chatem
        Zwraca szczegółowe informacje o statusie
        
        Returns:
            Dict z informacjami o teście
        """
        result = {
            "bot_connected": False,
            "bot_info": None,
            "chat_test": False,
            "error": None
        }
        
        try:
            bot_info = await self.get_bot_info()
            if bot_info:
                result["bot_connected"] = True
                result["bot_info"] = {
                    "username": bot_info.get("username"),
                    "first_name": bot_info.get("first_name"),
                    "id": bot_info.get("id")
                }
            
            test_sent = await self.send_message("🧪 Test połączenia - Ghost Trader Bot")
            result["chat_test"] = test_sent
            
            if not test_sent:
                result["error"] = "Nie udało się wysłać wiadomości testowej. Sprawdź CHAT_ID."
                
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    def format_markdown(self, text: str) -> str:
        """
        Escape'uje specjalne znaki dla Markdown
        
        Args:
            text: Tekst do escape'owania
        
        Returns:
            Escape'owany tekst
        """
        special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        for char in special_chars:
            text = text.replace(char, f'\\{char}')
        return text


# Test funkcji
if __name__ == "__main__":
    import asyncio
    
    async def test_telegram():
        # Pobierz z .env
        import os
        from dotenv import load_dotenv
        load_dotenv()
        
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
        
        if not bot_token or not chat_id:
            print("❌ Ustaw TELEGRAM_BOT_TOKEN i TELEGRAM_CHAT_ID w .env")
            return
        
        service = TelegramService(bot_token, chat_id)
        
        # Test połączenia
        print("Testing connection...")
        connected = await service.check_connection()
        print(f"Connected: {connected}")
        
        if connected:
            # Test wiadomości
            print("\nSending test message...")
            await service.send_message("🧪 Test message from Trading Bot")
            
            # Test sygnału
            print("\nSending test signal...")
            await service.send_signal(
                signal_type="BUY",
                strategy_name="RSI Conservative",
                symbol="EUR/USD",
                price=45000.00,
                indicator_values={
                    "RSI": 25.5,
                    "Price": 45000
                }
            )
            
            # Test alertu
            print("\nSending test alert...")
            await service.send_alert(
                title="System Started",
                message="Trading bot is now running",
                level="SUCCESS"
            )
    
    asyncio.run(test_telegram())
