"""
AI Strategy Service - strategia wykorzystująca AI do kompleksowej analizy
"""
from typing import Dict, Any, List
import logging
from datetime import datetime

from .ai_analysis_service import AIAnalysisService
from .data_collection_service import (
    MacroDataService,
    NewsService,
    EventCalendarService
)
from .telegram_service import TelegramService


class AIStrategy:
    """
    Zaawansowana strategia wykorzystująca:
    1. Wskaźniki techniczne (RSI, MACD, etc.)
    2. Dane makroekonomiczne (Fed, inflacja, PKB)
    3. Analizę wiadomości (sentiment, breaking news)
    4. Kalendarz ekonomiczny (nadchodzące wydarzenia)
    5. Claude AI do syntezy wszystkich danych
    """
    
    def __init__(
        self,
        telegram_service: TelegramService = None
    ):
        """
        Inicjalizacja strategii AI
        
        Args:
            telegram_service: Serwis Telegram do powiadomień
        """
        self.ai_service = AIAnalysisService()
        self.macro_service = MacroDataService()
        self.news_service = NewsService()
        self.calendar_service = EventCalendarService()
        self.telegram = telegram_service
        self.logger = logging.getLogger("trading_bot.ai_strategy")
    
    async def analyze_and_generate_signal(
        self,
        symbol: str,
        timeframe: str = "1h",
        technical_indicators: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Główna metoda - kompleksowa analiza i generowanie sygnału
        
        Args:
            symbol: Symbol (np. BTC/USDT)
            timeframe: Timeframe (1h, 4h, 1d)
            technical_indicators: Wskaźniki techniczne (opcjonalne)
        
        Returns:
            Słownik z sygnałem i szczegółową analizą
        """
        
        self.logger.info(f"Starting AI analysis for {symbol}")
        
        try:
            # 1. Zbierz dane makroekonomiczne
            self.logger.info("Collecting macro data...")
            macro_data = await self.macro_service.get_all_macro_data()
            
            # 2. Zbierz wiadomości
            self.logger.info("Collecting news...")
            news = await self.news_service.get_financial_news(
                symbol=symbol.split('/')[0],  # BTC z BTC/USDT
                hours_back=24,
                limit=10
            )
            
            # 3. Sprawdź kalendarz ekonomiczny
            self.logger.info("Checking economic calendar...")
            upcoming_events = await self.calendar_service.get_upcoming_events(
                days_ahead=3
            )
            
            # 4. Pobierz wskaźniki techniczne (jeśli nie podane)
            if technical_indicators is None:
                technical_indicators = await self._calculate_technical_indicators(
                    symbol, timeframe
                )
            
            # 5. Przygotuj kontekst do analizy
            context = {
                "symbol": symbol,
                "timeframe": timeframe,
                "macro_data": macro_data,
                "news": news,
                "technical_indicators": technical_indicators,
                "upcoming_events": upcoming_events,
                "analysis_timestamp": datetime.now().isoformat()
            }
            
            # 6. Wywołaj AI do kompleksowej analizy
            self.logger.info("Running AI analysis...")
            ai_analysis = await self.ai_service.analyze_macro_data(
                symbol=symbol,
                macro_data=macro_data,
                news=news,
                technical_indicators=technical_indicators
            )
            
            # 7. Przygotuj wynik
            result = {
                "symbol": symbol,
                "timeframe": timeframe,
                "timestamp": datetime.now().isoformat(),
                
                # Główna rekomendacja AI
                "recommendation": ai_analysis.get("recommendation", "HOLD"),
                "confidence": ai_analysis.get("confidence", 50),
                
                # Szczegółowa analiza
                "ai_analysis": ai_analysis,
                
                # Dane źródłowe
                "macro_summary": self._summarize_macro(macro_data),
                "news_summary": self._summarize_news(news),
                "technical_summary": self._summarize_technical(technical_indicators),
                "events_summary": self._summarize_events(upcoming_events),
                
                # Komponenty decyzji
                "decision_components": {
                    "macro_score": self._score_macro(macro_data),
                    "news_sentiment": ai_analysis.get("news_impact", "neutral"),
                    "technical_signal": ai_analysis.get("technical_signal", "neutral"),
                    "event_risk": self._assess_event_risk(upcoming_events)
                }
            }
            
            # 8. Wyślij powiadomienie jeśli sygnał BUY/SELL
            if result["recommendation"] in ["BUY", "SELL"]:
                await self._send_ai_signal_notification(result)
            
            self.logger.info(
                f"AI analysis completed: {result['recommendation']} "
                f"(confidence: {result['confidence']}%)"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in AI analysis: {e}", exc_info=True)
            return {
                "symbol": symbol,
                "recommendation": "HOLD",
                "confidence": 0,
                "error": str(e)
            }
    
    async def _calculate_technical_indicators(
        self,
        symbol: str,
        timeframe: str
    ) -> Dict[str, Any]:
        """
        Oblicza wskaźniki techniczne
        
        W produkcji: pobieranie z API giełdy i obliczanie wskaźników
        """
        
        # Demo - w produkcji tutaj byłoby prawdziwe pobieranie danych
        import random
        
        price = random.uniform(40000, 50000)
        
        return {
            "price": price,
            "rsi": random.uniform(30, 70),
            "macd": {
                "value": random.uniform(-200, 200),
                "signal": random.uniform(-200, 200),
                "histogram": random.uniform(-100, 100)
            },
            "bollinger": {
                "upper": price * 1.05,
                "middle": price,
                "lower": price * 0.95
            },
            "sma_50": price * 0.98,
            "sma_200": price * 0.95,
            "volume_24h": random.uniform(1e9, 2e9),
            "volatility": random.uniform(0.02, 0.05)
        }
    
    def _summarize_macro(self, macro_data: Dict[str, Any]) -> str:
        """Podsumowuje dane makro"""
        if not macro_data:
            return "Brak danych makro"
        
        fed = macro_data.get("fed", {})
        inflation = macro_data.get("inflation", {})
        
        return (
            f"Fed: {fed.get('current_rate', 'N/A')}%, "
            f"Inflacja: {inflation.get('cpi_annual', 'N/A')}%, "
            f"Następne posiedzenie: {fed.get('next_meeting', 'N/A')}"
        )
    
    def _summarize_news(self, news: List[Dict[str, Any]]) -> str:
        """Podsumowuje wiadomości"""
        if not news:
            return "Brak wiadomości"
        
        positive = sum(1 for n in news if n.get("sentiment") == "positive")
        negative = sum(1 for n in news if n.get("sentiment") == "negative")
        
        return f"{len(news)} wiadomości (+ {positive}, - {negative})"
    
    def _summarize_technical(self, indicators: Dict[str, Any]) -> str:
        """Podsumowuje wskaźniki techniczne"""
        if not indicators:
            return "Brak wskaźników"
        
        rsi = indicators.get("rsi", 0)
        price = indicators.get("price", 0)
        
        return f"Cena: ${price:,.2f}, RSI: {rsi:.1f}"
    
    def _summarize_events(self, events: List[Dict[str, Any]]) -> str:
        """Podsumowuje nadchodzące wydarzenia"""
        if not events:
            return "Brak ważnych wydarzeń"
        
        high_impact = [e for e in events if e.get("importance") == "high"]
        
        return f"{len(high_impact)} ważnych wydarzeń w najbliższych dniach"
    
    def _score_macro(self, macro_data: Dict[str, Any]) -> str:
        """Ocenia otoczenie makroekonomiczne"""
        if not macro_data:
            return "neutral"
        
        # Uproszczona logika
        inflation = macro_data.get("inflation", {}).get("cpi_annual", 3.0)
        fed_rate = macro_data.get("fed", {}).get("current_rate", 5.0)
        
        # Jeśli inflacja spada i stopy wysokie -> potencjalnie pozytywne
        if inflation < 3.0 and fed_rate > 5.0:
            return "positive"
        elif inflation > 4.0:
            return "negative"
        else:
            return "neutral"
    
    def _assess_event_risk(self, events: List[Dict[str, Any]]) -> str:
        """Ocenia ryzyko z nadchodzących wydarzeń"""
        if not events:
            return "low"
        
        high_impact_count = sum(
            1 for e in events
            if e.get("impact_level", 0) >= 8
        )
        
        if high_impact_count >= 3:
            return "high"
        elif high_impact_count >= 1:
            return "medium"
        else:
            return "low"
    
    async def _send_ai_signal_notification(self, result: Dict[str, Any]):
        """Wysyła powiadomienie o sygnale AI"""
        
        if not self.telegram:
            return
        
        try:
            recommendation = result["recommendation"]
            confidence = result["confidence"]
            symbol = result["symbol"]
            
            # Emoji
            emoji = "🟢" if recommendation == "BUY" else "🔴"
            
            # AI analysis
            ai_analysis = result.get("ai_analysis", {})
            reasoning = ai_analysis.get("reasoning", "")
            key_factors = ai_analysis.get("key_factors", [])
            
            # Formatuj wiadomość
            message = f"""
{emoji} <b>AI SIGNAL: {recommendation}</b>

<b>Symbol:</b> {symbol}
<b>Confidence:</b> {confidence}%
<b>Timeframe:</b> {result.get('timeframe', 'N/A')}

<b>🧠 AI Reasoning:</b>
{reasoning[:300]}{"..." if len(reasoning) > 300 else ""}

<b>📊 Key Factors:</b>
"""
            
            for factor in key_factors[:3]:
                message += f"  • {factor}\n"
            
            # Dodaj komponenty
            components = result.get("decision_components", {})
            message += f"""
<b>📈 Decision Components:</b>
  • Macro: {components.get('macro_score', 'N/A')}
  • News: {components.get('news_sentiment', 'N/A')}
  • Technical: {components.get('technical_signal', 'N/A')}
  • Event Risk: {components.get('event_risk', 'N/A')}

<i>Powered by Claude AI Analysis</i>
<i>Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</i>
"""
            
            await self.telegram.send_message(message)
            
            self.logger.info("AI signal notification sent")
            
        except Exception as e:
            self.logger.error(f"Error sending AI notification: {e}")
    
    async def get_market_overview(self, symbol: str) -> Dict[str, Any]:
        """
        Generuje pełny przegląd rynku dla danego symbolu
        
        Args:
            symbol: Symbol
        
        Returns:
            Kompleksowy przegląd rynku
        """
        
        try:
            # Zbierz wszystkie dane
            macro_data = await self.macro_service.get_all_macro_data()
            news = await self.news_service.get_financial_news(symbol, limit=20)
            events = await self.calendar_service.get_upcoming_events(7)
            technical = await self._calculate_technical_indicators(symbol, "1d")
            
            # Sentiment analysis
            sentiment = await self.ai_service.get_sentiment_analysis(symbol, news)
            
            return {
                "symbol": symbol,
                "timestamp": datetime.now().isoformat(),
                "macro_environment": {
                    "summary": self._summarize_macro(macro_data),
                    "score": self._score_macro(macro_data),
                    "details": macro_data
                },
                "market_sentiment": sentiment,
                "technical_overview": technical,
                "news_highlights": news[:5],
                "upcoming_events": events[:5],
                "event_risk_level": self._assess_event_risk(events)
            }
            
        except Exception as e:
            self.logger.error(f"Error generating market overview: {e}")
            return {"error": str(e)}


# Test
if __name__ == "__main__":
    import asyncio
    
    async def test_ai_strategy():
        strategy = AIStrategy()
        
        # Test analizy
        result = await strategy.analyze_and_generate_signal(
            symbol="BTC/USDT",
            timeframe="1h"
        )
        
        print("\n=== AI TRADING SIGNAL ===")
        print(f"Symbol: {result['symbol']}")
        print(f"Recommendation: {result['recommendation']}")
        print(f"Confidence: {result['confidence']}%")
        print(f"\nAI Reasoning: {result['ai_analysis'].get('reasoning', 'N/A')}")
        
        # Test market overview
        overview = await strategy.get_market_overview("BTC/USDT")
        print("\n=== MARKET OVERVIEW ===")
        print(f"Macro: {overview['macro_environment']['summary']}")
        print(f"Event Risk: {overview['event_risk_level']}")
    
    asyncio.run(test_ai_strategy())
