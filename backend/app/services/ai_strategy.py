"""
AI Strategy Service - strategia wykorzystująca AI do kompleksowej analizy
"""
from typing import Dict, Any, List
import logging
from datetime import datetime

from ..config import get_settings, get_polish_time
from .ai_analysis_service import AIAnalysisService
from .data_collection_service import (
    MacroDataService,
    NewsService,
    EventCalendarService
)
from .market_data_service import MarketDataService
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
        self.market_data = MarketDataService()
        self.telegram = telegram_service
        self.logger = logging.getLogger("trading_bot.ai_strategy")
        self.settings = get_settings()
    
    async def analyze_and_generate_signal(
        self,
        symbol: str,
        timeframe: str = "1h",
        technical_indicators: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Główna metoda - kompleksowa analiza i generowanie sygnału
        
        Args:
            symbol: Symbol (np. EUR/USD)
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
                symbol=symbol.split('/')[0],  # EUR z EUR/USD
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
                "analysis_timestamp": get_polish_time().isoformat()
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
                "timestamp": get_polish_time().isoformat(),
                
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
        Oblicza wskaźniki techniczne na podstawie prawdziwych danych
        """
        try:
            # Pobierz wszystkie wskaźniki techniczne
            indicators_config = {
                'period': 14,  # Dla RSI
                'fast_period': 12,  # Dla MACD
                'slow_period': 26,
                'signal_period': 9,
                'std_dev': 2.0,  # Dla Bollinger
                'short_period': 50,  # Dla MA
                'long_period': 200
            }
            
            indicators = await self.market_data.get_technical_indicators(
                symbol=symbol,
                timeframe=timeframe,
                indicators_config=indicators_config
            )
            
            # Dodaj dodatkowe informacje
            data = await self.market_data.get_historical_data(symbol, timeframe, '1mo')
            if data is not None and not data.empty:
                # Oblicz volatility (odchylenie standardowe zmian ceny)
                returns = data['Close'].pct_change().dropna()
                volatility = returns.std() * 100  # W procentach
                
                # Volume (jeśli dostępny)
                volume = data['Volume'].iloc[-1] if 'Volume' in data.columns else 0
                
                indicators['volatility'] = round(float(volatility), 2)
                indicators['volume_24h'] = float(volume) if volume > 0 else 0
            else:
                indicators['volatility'] = 0.0
                indicators['volume_24h'] = 0
            
            return indicators
            
        except Exception as e:
            self.logger.error(f"Błąd obliczania wskaźników technicznych dla {symbol}: {e}", exc_info=True)
            # Zwróć wartości domyślne w przypadku błędu
            return {
                "price": 0.0,
                "rsi": 50.0,
                "macd": {
                    "value": 0.0,
                    "signal": 0.0,
                    "histogram": 0.0
                },
                "bollinger": {
                    "upper": 0.0,
                    "middle": 0.0,
                    "lower": 0.0
                },
                "sma_50": 0.0,
                "sma_200": 0.0,
                "volume_24h": 0.0,
                "volatility": 0.0
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
<i>Time: {get_polish_time().strftime("%Y-%m-%d %H:%M:%S")}</i>
"""
            
            await self.telegram.send_message(message)
            
            self.logger.info("AI signal notification sent")
            
        except Exception as e:
            self.logger.error(f"Error sending AI notification: {e}")
    
    async def comprehensive_analysis(
        self,
        symbol: str,
        timeframe: str = "1h"
    ) -> Dict[str, Any]:
        """
        Kompleksowa analiza zwracająca wyniki ze wszystkich źródeł
        w ustandaryzowanym formacie dla Signal Aggregator
        
        Co robi ta metoda?
        ------------------
        To główna metoda Etapu 3! Zbiera dane z 4 różnych źródeł:
        1. AI Analysis - analiza OpenAI GPT (najinteligentniejsza, ale kosztowna)
        2. Technical Analysis - wskaźniki techniczne (RSI, MACD, MA, Bollinger)
        3. Macro Analysis - dane makroekonomiczne (Fed, inflacja, PKB)
        4. News Analysis - sentiment wiadomości (pozytywne/negatywne)
        
        Następnie wszystkie te analizy są przekazywane do SignalAggregatorService,
        który używa głosowania większościowego aby zdecydować czy kupić/sprzedać/czekać.
        
        Dlaczego 4 źródła?
        ------------------
        Używanie tylko jednego źródła jest ryzykowne:
        - AI może się mylić
        - Wskaźniki techniczne mogą dawać fałszywe sygnały
        - Makro może być nieaktualne
        - News może być manipulowany
        
        Ale jeśli 3 z 4 źródeł mówią "KUP", to jest większa szansa że to dobra decyzja!
        
        Przepływ danych:
        ----------------
        1. Pobierz dane makro (Fed, inflacja, PKB)
        2. Pobierz wiadomości (ostatnie 24h)
        3. Oblicz wskaźniki techniczne (RSI, MACD, etc.)
        4. Wyślij wszystko do AI do analizy
        5. Policz tokeny i koszt
        6. Przeanalizuj każde źródło osobno
        7. Zwróć wszystko w ustandaryzowanym formacie
        
        Args:
            symbol: Symbol do analizy (np. "EUR/USD", "AAPL/USD", "XAU/USD")
            timeframe: Interwał czasowy (domyślnie "1h", może być "4h", "1d")
        
        Returns:
            Słownik z wynikami wszystkich analiz w formacie:
            {
                "symbol": "EUR/USD",
                "timeframe": "1h",
                "timestamp": "2026-01-16T20:00:00",
                
                "ai_analysis": {
                    "recommendation": "BUY",  # Rekomendacja AI
                    "confidence": 80,         # Pewność 0-100%
                    "reasoning": "...",       # Uzasadnienie
                    "tokens_used": 2500,      # Ile tokenów zużyto
                    "estimated_cost": 0.0225  # Szacowany koszt w USD
                },
                
                "technical_analysis": {
                    "signal": "BUY",          # Sygnał techniczny
                    "confidence": 70,         # Pewność 0-100%
                    "indicators": {...}       # Szczegóły wskaźników
                },
                
                "macro_analysis": {
                    "signal": "HOLD",         # Sygnał makro
                    "confidence": 50,         # Pewność 0-100%
                    "impact": "neutral",      # Wpływ: positive/negative/neutral
                    "summary": "..."          # Podsumowanie
                },
                
                "news_analysis": {
                    "sentiment": "positive",  # Sentiment: positive/negative/neutral
                    "score": 65,              # Score 0-100%
                    "news_count": 5,          # Ile wiadomości
                    "summary": "..."          # Podsumowanie
                }
            }
        
        Przykład użycia:
            >>> strategy = AIStrategy()
            >>> result = await strategy.comprehensive_analysis("EUR/USD", "1h")
            >>> print(result["ai_analysis"]["recommendation"])  # "BUY"
            >>> print(result["technical_analysis"]["signal"])   # "BUY"
            >>> # Następnie przekaż do SignalAggregatorService
        
        Uwagi:
            - Metoda jest async (asynchroniczna) bo pobiera dane z API
            - Jeśli brak klucza OpenAI, AI analysis zwróci HOLD z confidence=0
            - Jeśli wystąpi błąd, zwraca bezpieczne wartości domyślne
            - Koszt jednej analizy: ~$0.02-0.03 dla gpt-4o, ~$0.002-0.003 dla gpt-4o-mini
        """
        self.logger.info(f"Starting comprehensive analysis for {symbol}")
        
        try:
            # Zbierz dane z wszystkich źródeł
            macro_data = await self.macro_service.get_all_macro_data()
            news = await self.news_service.get_financial_news(
                symbol=symbol.split('/')[0],
                hours_back=24,
                limit=10
            )
            technical_indicators = await self._calculate_technical_indicators(
                symbol, timeframe
            )
            
            # Uruchom analizę AI
            ai_analysis_raw = await self.ai_service.analyze_macro_data(
                symbol=symbol,
                macro_data=macro_data,
                news=news,
                technical_indicators=technical_indicators
            )
            
            # Przygotuj prompt dla AI i policz tokeny
            prompt_text = self._build_analysis_prompt(
                symbol, macro_data, news, technical_indicators
            )
            tokens_used = self._count_tokens(prompt_text)
            estimated_cost = self._estimate_cost(tokens_used, model=self.settings.openai_model)
            
            # Przygotuj wyniki w ustandaryzowanym formacie
            result = {
                "symbol": symbol,
                "timeframe": timeframe,
                "timestamp": get_polish_time().isoformat(),
                
                # AI Analysis
                "ai_analysis": {
                    "recommendation": ai_analysis_raw.get("recommendation", "HOLD"),
                    "confidence": ai_analysis_raw.get("confidence", 50),
                    "reasoning": ai_analysis_raw.get("reasoning", ""),
                    "key_factors": ai_analysis_raw.get("key_factors", []),
                    "tokens_used": tokens_used,
                    "estimated_cost": estimated_cost
                },
                
                # Technical Analysis
                "technical_analysis": self._analyze_technical_signal(technical_indicators),
                
                # Macro Analysis
                "macro_analysis": self._analyze_macro_signal(macro_data),
                
                # News Analysis
                "news_analysis": self._analyze_news_sentiment(news)
            }
            
            self.logger.info(
                f"Comprehensive analysis completed for {symbol}: "
                f"AI={result['ai_analysis']['recommendation']}, "
                f"Tech={result['technical_analysis']['signal']}, "
                f"Macro={result['macro_analysis']['signal']}, "
                f"News={result['news_analysis']['sentiment']}"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in comprehensive analysis: {e}", exc_info=True)
            # Zwróć bezpieczne wartości domyślne
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
                    "estimated_cost": 0.0
                },
                "technical_analysis": {
                    "signal": "HOLD",
                    "confidence": 0,
                    "indicators": {}
                },
                "macro_analysis": {
                    "signal": "HOLD",
                    "confidence": 50,
                    "impact": "neutral",
                    "summary": "Brak danych"
                },
                "news_analysis": {
                    "sentiment": "neutral",
                    "score": 50,
                    "news_count": 0,
                    "summary": "Brak wiadomości"
                },
                "error": str(e)
            }
    
    def _build_analysis_prompt(
        self,
        symbol: str,
        macro_data: Dict[str, Any],
        news: List[Dict[str, Any]],
        technical_indicators: Dict[str, Any]
    ) -> str:
        """
        Buduje prompt dla AI (do liczenia tokenów)
        
        Args:
            symbol: Symbol
            macro_data: Dane makro
            news: Lista wiadomości
            technical_indicators: Wskaźniki techniczne
        
        Returns:
            Pełny tekst promptu
        """
        prompt = f"Analyze {symbol}\n\n"
        prompt += f"Macro: {str(macro_data)}\n"
        prompt += f"News: {str(news)}\n"
        prompt += f"Technical: {str(technical_indicators)}\n"
        return prompt
    
    def _count_tokens(self, text: str) -> int:
        """
        Szacuje liczbę tokenów OpenAI
        
        Co to są tokeny?
        ----------------
        Tokeny to jednostki tekstu używane przez modele AI. Jeden token to zazwyczaj
        około 4 znaki w języku angielskim. Słowo "hello" to 1 token, a "artificial" to 2-3 tokeny.
        
        Dlaczego to ważne?
        ------------------
        OpenAI nalicza opłaty za tokeny, więc musimy wiedzieć ile tokenów zużywamy,
        aby oszacować koszty. Każde zapytanie do AI składa się z:
        - Input tokens (nasz prompt/pytanie)
        - Output tokens (odpowiedź AI)
        
        Jak działa ta metoda?
        ---------------------
        Używamy prostego przybliżenia: 1 token ≈ 4 znaki
        To nie jest dokładne (prawdziwe modele używają tokenizacji BPE), ale wystarczy
        do szacowania kosztów. Dla dokładniejszego liczenia można użyć biblioteki tiktoken.
        
        Przybliżenie: 1 token ≈ 4 znaki dla języka angielskiego
        Dla polskiego i JSON może być mniej dokładne, ale wystarczające do szacowania
        
        Args:
            text: Tekst do policzenia (prompt który wysyłamy do AI)
        
        Returns:
            Przybliżona liczba tokenów (input + buffer na output)
        
        Przykład:
            >>> strategy._count_tokens("Analyze EUR/USD")
            304  # ~4 tokeny + 300 buffer na odpowiedź
        """
        # Jeśli tekst jest pusty, zwróć 0
        if not text:
            return 0
        
        # Proste przybliżenie: 1 token ≈ 4 znaki
        # Dzielimy długość tekstu przez 4 aby dostać przybliżoną liczbę tokenów
        # Operator // to dzielenie całkowite (bez reszty)
        estimated_tokens = len(text) // 4
        
        # Dodaj buffer na response (zazwyczaj 200-500 tokenów)
        # AI musi odpowiedzieć, więc dodajemy tokeny na jego odpowiedź
        # 300 tokenów to około 1200 znaków - wystarczy na typową analizę
        estimated_tokens += 300
        
        return estimated_tokens
    
    def _estimate_cost(
        self,
        tokens: int,
        model: str = None
    ) -> float:
        """
        Szacuje koszt zapytania do OpenAI
        
        Jak działa pricing OpenAI?
        ---------------------------
        OpenAI nalicza osobne opłaty za:
        - Input tokens (nasz prompt) - tańsze
        - Output tokens (odpowiedź AI) - droższe
        
        Ceny różnią się między modelami:
        - gpt-4o: najnowszy, dobry balans ceny/jakości
        - gpt-4o-mini: 10x tańszy, dobry do prostych zadań
        - gpt-4-turbo: droższy, bardziej zaawansowany
        - gpt-3.5-turbo: najtańszy, podstawowa jakość
        
        Dlaczego to ważne?
        ------------------
        Jeśli uruchamiamy analizy co 15 minut dla 25 symboli,
        to 96 analiz/dzień × 25 symboli × 30 dni = 72,000 analiz/miesiąc!
        Przy gpt-4o może to kosztować setki dolarów, więc musimy to monitorować.
        
        Args:
            tokens: Liczba tokenów (input + output razem)
            model: Model OpenAI (domyślnie z ustawień config)
        
        Returns:
            Szacowany koszt w USD (zaokrąglony do 6 miejsc po przecinku)
        
        Przykład:
            >>> strategy._estimate_cost(1000, "gpt-4o")
            0.009  # $0.009 za 1000 tokenów
            >>> strategy._estimate_cost(1000, "gpt-4o-mini")
            0.00033  # 10x taniej!
        """
        # Jeśli model nie został podany, użyj z ustawień
        if model is None:
            model = self.settings.openai_model
        
        # Ceny na styczeń 2026 (mogą się zmienić - sprawdź openai.com/pricing)
        # Słownik z cenami dla różnych modeli
        prices = {
            "gpt-4o": {
                "input": 0.005,   # $0.005 za 1000 input tokens
                "output": 0.015   # $0.015 za 1000 output tokens
            },
            "gpt-4o-mini": {
                "input": 0.00015,  # $0.00015 za 1000 input tokens (10x taniej!)
                "output": 0.0006   # $0.0006 za 1000 output tokens
            },
            "gpt-4-turbo": {
                "input": 0.01,     # Droższy
                "output": 0.03
            },
            "gpt-3.5-turbo": {
                "input": 0.0005,   # Najtańszy
                "output": 0.0015
            }
        }
        
        # Pobierz cenę dla wybranego modelu (domyślnie gpt-4o-mini)
        price = prices.get(model, prices["gpt-4o-mini"])
        
        # Zakładamy typowy podział: 60% input (nasz prompt), 40% output (odpowiedź AI)
        # To przybliżenie oparte na rzeczywistych danych
        input_tokens = tokens * 0.6
        output_tokens = tokens * 0.4
        
        # Oblicz koszt:
        # (liczba_tokenów * cena_za_1K_tokenów / 1000)
        # Dzielimy przez 1000 bo ceny są podane za 1K tokenów
        cost = (
            (input_tokens * price["input"] / 1000) +
            (output_tokens * price["output"] / 1000)
        )
        
        # Zaokrąglij do 6 miejsc po przecinku (mikrocenty)
        return round(cost, 6)
    
    def _analyze_technical_signal(
        self,
        indicators: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Interpretuje wskaźniki techniczne i generuje sygnał
        
        Co to są wskaźniki techniczne?
        -------------------------------
        To matematyczne obliczenia na podstawie historycznych cen, które pomagają
        przewidzieć przyszłe ruchy ceny. Najpopularniejsze to:
        
        1. RSI (Relative Strength Index) - pokazuje czy instrument jest:
           - Oversold (< 30) - może być za tani, sygnał KUP
           - Overbought (> 70) - może być za drogi, sygnał SPRZEDAJ
           - Neutral (30-70) - brak wyraźnego sygnału
        
        2. MACD (Moving Average Convergence Divergence) - pokazuje trend:
           - Bullish crossover (MACD > signal) - sygnał KUP
           - Bearish crossover (MACD < signal) - sygnał SPRZEDAJ
        
        3. Moving Averages (średnie kroczące):
           - Golden Cross (MA50 > MA200) - sygnał KUP
           - Death Cross (MA50 < MA200) - sygnał SPRZEDAJ
        
        4. Bollinger Bands (wstęgi Bollingera):
           - Cena przy dolnej wstędze - może odbić w górę, sygnał KUP
           - Cena przy górnej wstędze - może spaść, sygnał SPRZEDAJ
        
        Jak działa ta metoda?
        ---------------------
        1. Sprawdza każdy wskaźnik osobno
        2. Każdy wskaźnik "głosuje" na BUY/SELL/HOLD z pewnym confidence
        3. Agreguje wszystkie głosy i wybiera najsilniejszy sygnał
        4. Zwraca finalny sygnał z confidence
        
        Args:
            indicators: Słownik ze wskaźnikami technicznymi:
                {
                    "rsi": 45.2,
                    "macd": {"value": 0.5, "signal": 0.3, "histogram": 0.2},
                    "sma_50": 1.0850,
                    "sma_200": 1.0800,
                    "price": 1.0875,
                    "bollinger": {"upper": 1.09, "middle": 1.085, "lower": 1.08}
                }
        
        Returns:
            Słownik z sygnałem technicznym:
            {
                "signal": "BUY" | "SELL" | "HOLD",
                "confidence": 0-100,  # Im wyższy, tym silniejszy sygnał
                "indicators": {...}   # Oryginalne wskaźniki
            }
        
        Przykład:
            >>> indicators = {"rsi": 25, "macd": {...}, ...}  # RSI oversold
            >>> result = strategy._analyze_technical_signal(indicators)
            >>> print(result["signal"])      # "BUY"
            >>> print(result["confidence"])  # 70
        """
        # Jeśli brak wskaźników, zwróć neutralny sygnał
        if not indicators:
            return {
                "signal": "HOLD",
                "confidence": 0,
                "indicators": {}
            }
        
        # Lista do zbierania głosów od poszczególnych wskaźników
        # Każdy głos to tuple: ("BUY"/"SELL"/"HOLD", confidence)
        signals = []
        
        # RSI Analysis
        rsi = indicators.get("rsi", 50)
        if rsi < 30:
            signals.append(("BUY", 70))  # Oversold
        elif rsi > 70:
            signals.append(("SELL", 70))  # Overbought
        else:
            signals.append(("HOLD", 50))
        
        # MACD Analysis
        macd_data = indicators.get("macd", {})
        if isinstance(macd_data, dict):
            macd_value = macd_data.get("value", 0)
            macd_signal = macd_data.get("signal", 0)
            
            if macd_value > macd_signal:
                signals.append(("BUY", 65))  # Bullish crossover
            elif macd_value < macd_signal:
                signals.append(("SELL", 65))  # Bearish crossover
            else:
                signals.append(("HOLD", 50))
        
        # Moving Average Analysis
        sma_50 = indicators.get("sma_50", 0)
        sma_200 = indicators.get("sma_200", 0)
        price = indicators.get("price", 0)
        
        if sma_50 > 0 and sma_200 > 0:
            if sma_50 > sma_200:
                signals.append(("BUY", 60))  # Golden cross
            elif sma_50 < sma_200:
                signals.append(("SELL", 60))  # Death cross
            else:
                signals.append(("HOLD", 50))
        
        # Bollinger Bands
        bollinger = indicators.get("bollinger", {})
        if isinstance(bollinger, dict):
            lower = bollinger.get("lower", 0)
            upper = bollinger.get("upper", 0)
            
            if price > 0 and lower > 0 and upper > 0:
                if price <= lower:
                    signals.append(("BUY", 65))  # Price at lower band
                elif price >= upper:
                    signals.append(("SELL", 65))  # Price at upper band
        
        # Agreguj sygnały
        if not signals:
            return {
                "signal": "HOLD",
                "confidence": 50,
                "indicators": indicators
            }
        
        # Policz głosy
        buy_score = sum(conf for sig, conf in signals if sig == "BUY")
        sell_score = sum(conf for sig, conf in signals if sig == "SELL")
        hold_score = sum(conf for sig, conf in signals if sig == "HOLD")
        
        total = buy_score + sell_score + hold_score
        
        if buy_score > sell_score and buy_score > hold_score:
            final_signal = "BUY"
            confidence = int((buy_score / total) * 100) if total > 0 else 50
        elif sell_score > buy_score and sell_score > hold_score:
            final_signal = "SELL"
            confidence = int((sell_score / total) * 100) if total > 0 else 50
        else:
            final_signal = "HOLD"
            confidence = int((hold_score / total) * 100) if total > 0 else 50
        
        return {
            "signal": final_signal,
            "confidence": min(100, confidence),
            "indicators": indicators
        }
    
    def _analyze_macro_signal(
        self,
        macro_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Interpretuje dane makroekonomiczne i generuje sygnał
        
        Args:
            macro_data: Dane makro (Fed, inflacja, PKB)
        
        Returns:
            Słownik z sygnałem makro:
            {
                "signal": "BUY" | "SELL" | "HOLD",
                "confidence": 0-100,
                "impact": "positive" | "negative" | "neutral",
                "summary": "..."
            }
        """
        if not macro_data:
            return {
                "signal": "HOLD",
                "confidence": 50,
                "impact": "neutral",
                "summary": "Brak danych makroekonomicznych"
            }
        
        # Analiza Fed
        fed = macro_data.get("fed", {})
        inflation = macro_data.get("inflation", {})
        gdp = macro_data.get("gdp", {})
        
        fed_rate = fed.get("current_rate", 5.0)
        cpi_annual = inflation.get("cpi_annual", 3.0)
        gdp_growth = gdp.get("growth_rate", 2.0)
        
        # Prosta logika makro
        score = 0
        factors = []
        
        # Inflacja
        if cpi_annual < 2.5:
            score += 1
            factors.append("Niska inflacja")
        elif cpi_annual > 4.0:
            score -= 1
            factors.append("Wysoka inflacja")
        
        # Stopy procentowe
        if fed_rate > 5.0 and cpi_annual < 3.0:
            score += 1
            factors.append("Wysokie stopy przy niskiej inflacji")
        elif fed_rate < 2.0:
            score -= 1
            factors.append("Niskie stopy")
        
        # PKB
        if gdp_growth > 2.5:
            score += 1
            factors.append("Silny wzrost PKB")
        elif gdp_growth < 1.0:
            score -= 1
            factors.append("Słaby wzrost PKB")
        
        # Określ sygnał
        if score > 0:
            signal = "BUY"
            impact = "positive"
            confidence = 60
        elif score < 0:
            signal = "SELL"
            impact = "negative"
            confidence = 60
        else:
            signal = "HOLD"
            impact = "neutral"
            confidence = 50
        
        summary = f"Fed: {fed_rate}%, Inflacja: {cpi_annual}%, PKB: {gdp_growth}%. " + ", ".join(factors)
        
        return {
            "signal": signal,
            "confidence": confidence,
            "impact": impact,
            "summary": summary
        }
    
    def _analyze_news_sentiment(
        self,
        news: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analizuje sentiment wiadomości
        
        Args:
            news: Lista wiadomości
        
        Returns:
            Słownik z analizą sentimentu:
            {
                "sentiment": "positive" | "negative" | "neutral",
                "score": 0-100,
                "news_count": 5,
                "summary": "..."
            }
        """
        if not news:
            return {
                "sentiment": "neutral",
                "score": 50,
                "news_count": 0,
                "summary": "Brak wiadomości"
            }
        
        # Policz sentiment
        positive = sum(1 for n in news if n.get("sentiment") == "positive")
        negative = sum(1 for n in news if n.get("sentiment") == "negative")
        neutral = len(news) - positive - negative
        
        total = len(news)
        
        # Oblicz score
        if total > 0:
            score = int(((positive - negative) / total) * 50 + 50)
            score = max(0, min(100, score))
        else:
            score = 50
        
        # Określ sentiment
        if positive > negative and positive > neutral:
            sentiment = "positive"
        elif negative > positive and negative > neutral:
            sentiment = "negative"
        else:
            sentiment = "neutral"
        
        summary = f"{positive} pozytywnych, {negative} negatywnych, {neutral} neutralnych wiadomości"
        
        return {
            "sentiment": sentiment,
            "score": score,
            "news_count": total,
            "summary": summary
        }
    
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
                "timestamp": get_polish_time().isoformat(),
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
            symbol="EUR/USD",
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
