"""
Główna klasa AIStrategy – orkiestracja analizy AI i wywołań modułów pomocniczych.
"""
import logging
from typing import Dict, Any, List, Optional

from ...config import get_settings, get_polish_time
from ..ai_analysis_service import AIAnalysisService
from ..data_collection_service import (
    MacroDataService,
    NewsService,
    EventCalendarService,
)
from ..market_data_service import MarketDataService
from ..telegram_service import TelegramService

from . import indicators as indicators_mod
from . import macro as macro_mod
from . import news as news_mod
from . import signals as signals_mod
from . import tokenizer as tokenizer_mod


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
        telegram_service: Optional[TelegramService] = None,
        database: Any = None,
    ):
        settings = get_settings()
        self.ai_service = AIAnalysisService(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
        )
        self.macro_service = MacroDataService()
        self.news_service = NewsService()
        self.calendar_service = EventCalendarService()
        self.market_data = MarketDataService()
        self.telegram = telegram_service
        self.database = database
        self.logger = logging.getLogger("trading_bot.ai_strategy")
        self.settings = settings

    async def analyze_and_generate_signal(
        self,
        symbol: str,
        timeframe: str = "1h",
        technical_indicators: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Główna metoda - kompleksowa analiza i generowanie sygnału.

        Args:
            symbol: Symbol (np. EUR/USD)
            timeframe: Timeframe (1h, 4h, 1d)
            technical_indicators: Wskaźniki techniczne (opcjonalne)

        Returns:
            Słownik z sygnałem i szczegółową analizą
        """
        self.logger.info("Starting AI analysis for %s", symbol)
        try:
            self.logger.info("Collecting macro data...")
            macro_data = await self.macro_service.get_all_macro_data()
            self.logger.info("Collecting news...")
            news = await self.news_service.get_financial_news(
                symbol=symbol.split("/")[0],
                hours_back=24,
                limit=10,
            )
            self.logger.info("Checking economic calendar...")
            upcoming_events = await self.calendar_service.get_upcoming_events(
                days_ahead=3
            )
            if technical_indicators is None:
                technical_indicators = await indicators_mod.calculate_technical_indicators(
                    symbol, timeframe, self.market_data
                )
            self.logger.info("Running AI analysis...")
            ai_analysis = await self.ai_service.analyze_macro_data(
                symbol=symbol,
                macro_data=macro_data,
                news=news,
                technical_indicators=technical_indicators,
            )
            result = {
                "symbol": symbol,
                "timeframe": timeframe,
                "timestamp": get_polish_time().isoformat(),
                "recommendation": ai_analysis.get("recommendation", "HOLD"),
                "confidence": ai_analysis.get("confidence", 50),
                "ai_analysis": ai_analysis,
                "macro_summary": macro_mod.summarize_macro(macro_data),
                "news_summary": news_mod.summarize_news(news),
                "technical_summary": indicators_mod.summarize_technical(
                    technical_indicators
                ),
                "events_summary": macro_mod.summarize_events(upcoming_events),
                "decision_components": {
                    "macro_score": macro_mod.score_macro(macro_data),
                    "news_sentiment": ai_analysis.get("news_impact", "neutral"),
                    "technical_signal": ai_analysis.get("technical_signal", "neutral"),
                    "event_risk": macro_mod.assess_event_risk(upcoming_events),
                },
            }
            if result["recommendation"] in ["BUY", "SELL"]:
                await signals_mod.send_ai_signal_notification(
                    result, self.telegram, self.logger
                )
            self.logger.info(
                "AI analysis completed: %s (confidence: %s%%)",
                result["recommendation"],
                result["confidence"],
            )
            return result
        except Exception as e:
            self.logger.error("Error in AI analysis: %s", e, exc_info=True)
            return {
                "symbol": symbol,
                "recommendation": "HOLD",
                "confidence": 0,
                "error": str(e),
            }

    async def comprehensive_analysis(
        self,
        symbol: str,
        timeframe: str = "1h",
    ) -> Dict[str, Any]:
        """
        Kompleksowa analiza zwracająca wyniki ze wszystkich źródeł
        w ustandaryzowanym formacie dla Signal Aggregator.

        Zbiera dane z 4 źródeł: AI Analysis, Technical, Macro, News,
        następnie przekazuje do SignalAggregatorService (głosowanie większościowe).
        """
        self.logger.info("Starting comprehensive analysis for %s", symbol)
        try:
            macro_data = await self.macro_service.get_all_macro_data()
            news = await self.news_service.get_financial_news(
                symbol=symbol.split("/")[0],
                hours_back=24,
                limit=10,
            )
            technical_indicators = await indicators_mod.calculate_technical_indicators(
                symbol, timeframe, self.market_data
            )
            ai_analysis_raw = await self.ai_service.analyze_macro_data(
                symbol=symbol,
                macro_data=macro_data,
                news=news,
                technical_indicators=technical_indicators,
            )
            prompt_text = tokenizer_mod.build_analysis_prompt(
                symbol, macro_data, news, technical_indicators
            )
            tokens_used = tokenizer_mod.count_tokens(prompt_text)
            estimated_cost = tokenizer_mod.estimate_cost(
                tokens_used, model=self.settings.openai_model, settings=self.settings
            )
            if self.database:
                try:
                    self.database.create_activity_log(
                        log_type="llm",
                        message=f"OpenAI API call: {self.settings.openai_model}",
                        symbol=symbol,
                        details={
                            "model": self.settings.openai_model,
                            "tokens_used": tokens_used,
                            "estimated_cost": estimated_cost,
                            "prompt_length": len(prompt_text),
                            "timeframe": timeframe,
                        },
                        status="success",
                    )
                except Exception as e:
                    self.logger.warning("Failed to log LLM request: %s", e)
            result = {
                "symbol": symbol,
                "timeframe": timeframe,
                "timestamp": get_polish_time().isoformat(),
                "ai_analysis": {
                    "recommendation": ai_analysis_raw.get("recommendation", "HOLD"),
                    "confidence": ai_analysis_raw.get("confidence", 50),
                    "reasoning": ai_analysis_raw.get("reasoning", ""),
                    "key_factors": ai_analysis_raw.get("key_factors", []),
                    "tokens_used": tokens_used,
                    "estimated_cost": estimated_cost,
                },
                "technical_analysis": indicators_mod.analyze_technical_signal(
                    technical_indicators
                ),
                "macro_analysis": macro_mod.analyze_macro_signal(macro_data),
                "news_analysis": news_mod.analyze_news_sentiment(news),
            }
            self.logger.info(
                "Comprehensive analysis completed for %s: AI=%s, Tech=%s, Macro=%s, News=%s",
                symbol,
                result["ai_analysis"]["recommendation"],
                result["technical_analysis"]["signal"],
                result["macro_analysis"]["signal"],
                result["news_analysis"]["sentiment"],
            )
            return result
        except Exception as e:
            self.logger.error("Error in comprehensive analysis: %s", e, exc_info=True)
            return {
                "symbol": symbol,
                "timeframe": timeframe,
                "timestamp": get_polish_time().isoformat(),
                "ai_analysis": {
                    "recommendation": "HOLD",
                    "confidence": 0,
                    "reasoning": f"Błąd: {str(e)}",
                    "key_factors": [],
                    "tokens_used": 0,
                    "estimated_cost": 0.0,
                },
                "technical_analysis": {
                    "signal": "HOLD",
                    "confidence": 0,
                    "indicators": {},
                },
                "macro_analysis": {
                    "signal": "HOLD",
                    "confidence": 50,
                    "impact": "neutral",
                    "summary": "Brak danych",
                },
                "news_analysis": {
                    "sentiment": "neutral",
                    "score": 50,
                    "news_count": 0,
                    "summary": "Brak wiadomości",
                },
                "error": str(e),
            }

    async def get_market_overview(self, symbol: str) -> Dict[str, Any]:
        """
        Generuje pełny przegląd rynku dla danego symbolu.
        """
        try:
            macro_data = await self.macro_service.get_all_macro_data()
            news = await self.news_service.get_financial_news(symbol, limit=20)
            events = await self.calendar_service.get_upcoming_events(7)
            technical = await indicators_mod.calculate_technical_indicators(
                symbol, "1d", self.market_data
            )
            sentiment = await self.ai_service.get_sentiment_analysis(symbol, news)
            return {
                "symbol": symbol,
                "timestamp": get_polish_time().isoformat(),
                "macro_environment": {
                    "summary": macro_mod.summarize_macro(macro_data),
                    "score": macro_mod.score_macro(macro_data),
                    "details": macro_data,
                },
                "market_sentiment": sentiment,
                "technical_overview": technical,
                "news_highlights": news[:5],
                "upcoming_events": events[:5],
                "event_risk_level": macro_mod.assess_event_risk(events),
            }
        except Exception as e:
            self.logger.error("Error generating market overview: %s", e)
            return {"error": str(e)}


if __name__ == "__main__":
    import asyncio

    async def test_ai_strategy() -> None:
        strategy = AIStrategy()
        result = await strategy.analyze_and_generate_signal(
            symbol="EUR/USD",
            timeframe="1h",
        )
        print("\n=== AI TRADING SIGNAL ===")
        print(f"Symbol: {result['symbol']}")
        print(f"Recommendation: {result['recommendation']}")
        print(f"Confidence: {result['confidence']}%")
        print(f"\nAI Reasoning: {result['ai_analysis'].get('reasoning', 'N/A')}")
        overview = await strategy.get_market_overview("BTC/USDT")
        print("\n=== MARKET OVERVIEW ===")
        print(f"Macro: {overview['macro_environment']['summary']}")
        print(f"Event Risk: {overview['event_risk_level']}")

    asyncio.run(test_ai_strategy())
