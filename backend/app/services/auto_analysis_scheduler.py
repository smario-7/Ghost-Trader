"""
AutoAnalysisScheduler - automatyczne analizy AI dla konfigurowalnej listy symboli
"""
import asyncio
import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from .ai_strategy import AIStrategy
from ..config import get_polish_time
from .signal_aggregator_service import SignalAggregatorService
from ..utils.database import Database
from .telegram_service import TelegramService


# Domyślna lista symboli (10 symboli dla oszczędności kosztów)
DEFAULT_SYMBOLS = [
    # Forex (4)
    "EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD",
    # Indeksy (2)
    "SPX/USD", "DJI/USD",
    # Akcje (3)
    "AAPL/USD", "MSFT/USD", "TSLA/USD",
    # Metale (1)
    "XAU/USD"
]


class AutoAnalysisScheduler:
    """
    Scheduler automatycznych analiz AI dla konfigurowalnej listy symboli.
    
    Ten scheduler automatycznie uruchamia kompleksowe analizy AI dla wybranych symboli
    w regularnych interwałach (domyślnie co 30 minut).
    
    Funkcje:
    --------
    - Pobiera listę symboli z konfiguracji (tabela analysis_config)
    - Uruchamia comprehensive_analysis dla każdego symbolu (AIStrategy)
    - Agreguje sygnały przez SignalAggregatorService (głosowanie większościowe)
    - Zapisuje wszystkie wyniki do bazy (tabela ai_analysis_results)
    - Wysyła powiadomienia Telegram tylko dla sygnałów >= threshold
    - Monitoruje tokeny i koszty OpenAI
    
    Przepływ danych:
    ---------------
    1. Scheduler wywołuje run_analysis_cycle() co X minut
    2. Dla każdego symbolu:
       - comprehensive_analysis() → zbiera dane z 4 źródeł (AI, Technical, Macro, News)
       - aggregate_signals() → głosowanie większościowe
       - create_ai_analysis_result() → zapis do bazy
       - Jeśli should_notify=True → wysyła powiadomienie Telegram
    3. Loguje statystyki (ile analiz, ile sygnałów, łączny koszt)
    
    Przykład użycia:
    ---------------
    >>> scheduler = AutoAnalysisScheduler(database=db, telegram=telegram)
    >>> results = await scheduler.run_analysis_cycle()
    >>> print(f"Analyzed {len(results)} symbols, cost: ${sum(r['estimated_cost'] for r in results):.4f}")
    """
    
    def __init__(
        self,
        database: Database,
        telegram: TelegramService,
        interval_minutes: int = 30,
        timeout: int = 60,
        pause_between_symbols: int = 2
    ):
        """
        Inicjalizuje AutoAnalysisScheduler
        
        Args:
            database: Instancja Database do zapisu wyników
            telegram: Instancja TelegramService do powiadomień
            interval_minutes: Interwał między cyklami analiz (domyślnie 30 min)
            timeout: Timeout dla pojedynczej analizy w sekundach (domyślnie 60s)
            pause_between_symbols: Pauza między analizami symboli w sekundach (domyślnie 2s)
        """
        self.db = database
        self.telegram = telegram
        self.interval = interval_minutes
        self.timeout = timeout
        self.pause = pause_between_symbols
        self.logger = logging.getLogger("trading_bot.auto_scheduler")
        
        # Inicjalizuj serwisy
        self.ai_strategy = AIStrategy(telegram_service=telegram, database=database)
        self.aggregator = SignalAggregatorService(database=database)
        
        # Lista symboli do analizy (będzie wczytana z konfiguracji)
        self.symbols = self._get_enabled_symbols()
        
        # Statystyki z ostatniego cyklu
        self.last_cycle_stats = {
            "timestamp": None,
            "analyzed_count": 0,
            "signals_count": 0,
            "errors_count": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "duration_seconds": 0.0
        }
        
        self.logger.info(
            f"AutoAnalysisScheduler initialized: "
            f"{len(self.symbols)} symbols, {interval_minutes} min interval"
        )
    
    def _get_enabled_symbols(self) -> List[str]:
        """
        Pobiera listę symboli z konfiguracji lub zwraca domyślną listę
        
        Próbuje pobrać listę symboli z tabeli analysis_config.
        Jeśli brak konfiguracji lub lista jest pusta, zwraca DEFAULT_SYMBOLS.
        
        Returns:
            Lista symboli do analizy (np. ["EUR/USD", "GBP/USD", ...])
        """
        try:
            # Pobierz konfigurację z bazy
            config = self.db.get_analysis_config()
            
            # Sprawdź czy konfiguracja zawiera listę symboli
            enabled_symbols = config.get("enabled_symbols", [])
            
            if enabled_symbols and len(enabled_symbols) > 0:
                self.logger.debug(f"Loaded {len(enabled_symbols)} symbols from config")
                return enabled_symbols
            else:
                self.logger.debug(f"No symbols in config, using default list ({len(DEFAULT_SYMBOLS)} symbols)")
                return DEFAULT_SYMBOLS.copy()
                
        except Exception as e:
            self.logger.warning(f"Could not load symbols from config: {e}. Using default list.")
            return DEFAULT_SYMBOLS.copy()
    
    async def run_analysis_cycle(self) -> List[Dict[str, Any]]:
        """
        Uruchamia pełny cykl analiz dla wszystkich symboli
        
        To jest główna metoda wywoływana przez scheduler co X minut.
        Analizuje wszystkie symbole z listy i zwraca wyniki.
        
        Przepływ:
        ---------
        1. Pobiera aktualną listę symboli (może się zmienić przez API)
        2. Dla każdego symbolu wywołuje analyze_symbol()
        3. Dodaje pauzę między symbolami (rate limiting)
        4. Zbiera wszystkie wyniki
        5. Loguje podsumowanie (statystyki)
        
        Returns:
            Lista wyników analiz, każdy wynik zawiera:
            {
                "analysis_id": 123,
                "symbol": "EUR/USD",
                "final_signal": "BUY",
                "agreement_score": 75,
                "tokens_used": 2500,
                "estimated_cost": 0.0225
            }
        
        Uwagi:
            - Jeśli analiza jednego symbolu się nie powiedzie, kontynuuje z następnym
            - Błędy są logowane ale nie przerywają całego cyklu
            - Statystyki są zapisywane w self.last_cycle_stats
        """
        self.logger.debug(f"Starting analysis cycle for {len(self.symbols)} symbols")
        start_time = get_polish_time()
        
        # Odśwież listę symboli (może się zmienić przez API)
        self.symbols = self._get_enabled_symbols()
        
        results = []
        errors_count = 0
        
        for symbol in self.symbols:
            try:
                self.logger.debug(f"Analyzing {symbol}...")
                
                result = await asyncio.wait_for(
                    self.analyze_symbol(symbol, timeframe="1h"),
                    timeout=self.timeout
                )
                
                results.append(result)
                self.logger.debug(
                    f"{symbol}: {result.get('final_signal', 'N/A')} "
                    f"({result.get('agreement_score', 0)}% agreement)"
                )
                
                # Pauza między symbolami (rate limiting)
                if self.pause > 0:
                    await asyncio.sleep(self.pause)
                
            except asyncio.TimeoutError:
                self.logger.error(f"  ✗ {symbol}: Timeout after {self.timeout}s")
                errors_count += 1
                
            except Exception as e:
                self.logger.error(f"  ✗ {symbol}: Error - {e}", exc_info=True)
                errors_count += 1
        
        # Oblicz statystyki
        duration = (get_polish_time() - start_time).total_seconds()
        signals_count = sum(1 for r in results if r.get('final_signal') in ['BUY', 'SELL'])
        total_tokens = sum(r.get('tokens_used', 0) for r in results)
        total_cost = sum(r.get('estimated_cost', 0.0) for r in results)
        
        # Zapisz statystyki
        self.last_cycle_stats = {
            "timestamp": datetime.now().isoformat(),
            "analyzed_count": len(results),
            "signals_count": signals_count,
            "errors_count": errors_count,
            "total_tokens": total_tokens,
            "total_cost": total_cost,
            "duration_seconds": duration
        }
        
        # Loguj podsumowanie
        self.logger.info(
            f"✅ Analysis cycle completed in {duration:.2f}s | "
            f"Analyzed: {len(results)}/{len(self.symbols)}, "
            f"Signals: {signals_count}, "
            f"Errors: {errors_count}, "
            f"Tokens: {total_tokens}, "
            f"Cost: ${total_cost:.4f}"
        )
        
        return results
    
    async def analyze_symbol(
        self,
        symbol: str,
        timeframe: str = "1h"
    ) -> Dict[str, Any]:
        """
        Analizuje pojedynczy symbol i zapisuje wynik do bazy
        
        To jest główna metoda dla pojedynczego symbolu. Wykonuje:
        1. Comprehensive analysis (AIStrategy) - zbiera dane z 4 źródeł
        2. Agregację sygnałów (SignalAggregatorService) - głosowanie większościowe
        3. Zapis do bazy (ai_analysis_results)
        4. Wysyłanie powiadomienia Telegram (jeśli spełnia kryteria)
        
        Args:
            symbol: Symbol do analizy (np. "EUR/USD", "AAPL/USD")
            timeframe: Interwał czasowy (domyślnie "1h")
        
        Returns:
            Słownik z wynikiem analizy:
            {
                "analysis_id": 123,
                "symbol": "EUR/USD",
                "final_signal": "BUY",
                "agreement_score": 75,
                "tokens_used": 2500,
                "estimated_cost": 0.0225
            }
        
        Raises:
            Exception: Jeśli wystąpi błąd podczas analizy
        """
        try:
            # 1. Uruchom kompleksową analizę (4 źródła: AI, Technical, Macro, News)
            analysis = await self.ai_strategy.comprehensive_analysis(symbol, timeframe)
            
            # 2. Agreguj sygnały (głosowanie większościowe)
            aggregated = await self.aggregator.aggregate_signals(
                symbol=symbol,
                timeframe=timeframe,
                ai_result=analysis["ai_analysis"],
                technical_result=analysis["technical_analysis"],
                macro_result=analysis["macro_analysis"],
                news_result=analysis["news_analysis"]
            )
            
            # 3. Przygotuj dane do zapisu w bazie
            analysis_data = {
                "symbol": symbol,
                "timeframe": timeframe,
                
                # Wyniki AI
                "ai_recommendation": analysis["ai_analysis"]["recommendation"],
                "ai_confidence": analysis["ai_analysis"]["confidence"],
                "ai_reasoning": analysis["ai_analysis"]["reasoning"],
                
                # Wyniki Technical
                "technical_signal": analysis["technical_analysis"]["signal"],
                "technical_confidence": analysis["technical_analysis"]["confidence"],
                "technical_details": json.dumps(analysis["technical_analysis"]["indicators"]),
                
                # Wyniki Macro
                "macro_signal": analysis["macro_analysis"]["signal"],
                "macro_impact": analysis["macro_analysis"]["impact"],
                
                # Wyniki News
                "news_sentiment": analysis["news_analysis"]["sentiment"],
                "news_score": analysis["news_analysis"]["score"],
                
                # Agregacja
                "final_signal": aggregated["final_signal"],
                "agreement_score": aggregated["agreement_score"],
                "voting_details": json.dumps(aggregated["voting_details"]),
                "decision_reason": aggregated["decision_reason"],
                
                # Statystyki OpenAI
                "tokens_used": analysis["ai_analysis"]["tokens_used"],
                "estimated_cost": analysis["ai_analysis"]["estimated_cost"]
            }
            
            # 4. Zapisz wynik do bazy
            analysis_id = self.db.create_ai_analysis_result(analysis_data)
            
            # 5. Jeśli sygnał spełnia kryteria - wyślij powiadomienie
            if aggregated["should_notify"]:
                await self._send_signal_notification(symbol, aggregated, analysis_id)
            
            # 6. Zwróć wynik
            return {
                "analysis_id": analysis_id,
                "symbol": symbol,
                "final_signal": aggregated["final_signal"],
                "agreement_score": aggregated["agreement_score"],
                "tokens_used": analysis["ai_analysis"]["tokens_used"],
                "estimated_cost": analysis["ai_analysis"]["estimated_cost"]
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing {symbol}: {e}", exc_info=True)
            raise
    
    async def _send_signal_notification(
        self,
        symbol: str,
        aggregated: Dict[str, Any],
        analysis_id: int
    ):
        """
        Wysyła powiadomienie Telegram o sygnale tradingowym
        
        Powiadomienie jest wysyłane tylko gdy:
        - agreement_score >= threshold (domyślnie 60%)
        - final_signal to BUY lub SELL (nie HOLD ani NO_SIGNAL)
        
        Args:
            symbol: Symbol (np. "EUR/USD")
            aggregated: Wynik agregacji sygnałów
            analysis_id: ID analizy w bazie danych
        
        Wiadomość zawiera:
        - Symbol i sygnał (BUY/SELL)
        - Agreement score (% zgodności źródeł)
        - Decision reason (uzasadnienie)
        - ID analizy (do szczegółów)
        """
        try:
            final_signal = aggregated["final_signal"]
            agreement_score = aggregated["agreement_score"]
            decision_reason = aggregated["decision_reason"]
            
            # Emoji dla sygnału
            emoji = "🟢" if final_signal == "BUY" else "🔴"
            
            # Formatuj wiadomość
            message = f"""
{emoji} <b>SYGNAŁ TRADINGOWY AI</b>

<b>Symbol:</b> {symbol}
<b>Sygnał:</b> {final_signal}
<b>Zgodność:</b> {agreement_score}%

<b>Uzasadnienie:</b>
{decision_reason}

<b>ID Analizy:</b> #{analysis_id}
<i>Czas: {get_polish_time().strftime("%Y-%m-%d %H:%M:%S")}</i>
"""
            
            # Wyślij wiadomość
            await self.telegram.send_message(message)
            
            self.logger.info(f"✉️  Notification sent for {symbol} ({final_signal})")
            
        except Exception as e:
            self.logger.error(f"Error sending notification for {symbol}: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Zwraca statystyki z ostatniego cyklu analiz
        
        Returns:
            Słownik ze statystykami:
            {
                "timestamp": "2026-01-16T20:00:00",
                "analyzed_count": 10,
                "signals_count": 3,
                "errors_count": 0,
                "total_tokens": 25000,
                "total_cost": 0.225,
                "duration_seconds": 45.2
            }
        """
        return self.last_cycle_stats.copy()
    
    def update_symbols(self, symbols: List[str]):
        """
        Aktualizuje listę symboli do analizy
        
        Args:
            symbols: Nowa lista symboli (np. ["EUR/USD", "GBP/USD"])
        """
        self.symbols = symbols
        self.logger.info(f"Symbols updated: {len(symbols)} symbols")


# Test
if __name__ == "__main__":
    import asyncio
    from ..utils.database import Database
    from ..config import get_settings
    
    async def test_auto_scheduler():
        """Test AutoAnalysisScheduler z 2 symbolami"""
        
        print("\n=== TEST AUTO ANALYSIS SCHEDULER ===\n")
        
        # Inicjalizuj
        settings = get_settings()
        db = Database(settings.database_path)
        db.initialize()
        
        telegram = TelegramService(
            bot_token=settings.telegram_bot_token,
            chat_id=settings.telegram_chat_id,
            database=db
        )
        
        scheduler = AutoAnalysisScheduler(
            database=db,
            telegram=telegram,
            interval_minutes=30
        )
        
        # Test z 2 symbolami (oszczędność kosztów)
        scheduler.symbols = ["EUR/USD", "GBP/USD"]
        
        print(f"Testing with {len(scheduler.symbols)} symbols: {scheduler.symbols}\n")
        
        # Uruchom cykl analiz
        results = await scheduler.run_analysis_cycle()
        
        # Wyświetl wyniki
        print(f"\n=== RESULTS ===")
        print(f"Analyzed: {len(results)} symbols\n")
        
        for result in results:
            print(f"Symbol: {result['symbol']}")
            print(f"  Signal: {result['final_signal']}")
            print(f"  Agreement: {result['agreement_score']}%")
            print(f"  Tokens: {result['tokens_used']}")
            print(f"  Cost: ${result['estimated_cost']:.4f}")
            print()
        
        # Statystyki
        stats = scheduler.get_statistics()
        print(f"=== STATISTICS ===")
        print(f"Duration: {stats['duration_seconds']:.2f}s")
        print(f"Signals generated: {stats['signals_count']}")
        print(f"Total tokens: {stats['total_tokens']}")
        print(f"Total cost: ${stats['total_cost']:.4f}")
    
    asyncio.run(test_auto_scheduler())
