"""
Serwis Telegram Bot
"""
import aiohttp
from typing import Optional, Dict, Any
import logging


class TelegramService:
    """Serwis do komunikacji z Telegram Bot API"""
    
    def __init__(self, bot_token: str, chat_id: str):
        """
        Inicjalizacja serwisu Telegram
        
        Args:
            bot_token: Token bota z @BotFather
            chat_id: ID czatu do wysyłania wiadomości
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.logger = logging.getLogger("trading_bot.telegram")
    
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
            symbol: Symbol (np. BTC/USDT)
            price: Cena
            indicator_values: Wartości wskaźników
        
        Returns:
            True jeśli wysłano pomyślnie
        """
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
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message += f"\n<i>Time: {timestamp}</i>"
        
        return await self.send_message(message)
    
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
                symbol="BTC/USDT",
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
