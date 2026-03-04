"""
Demo Etapu 2 - Signal Aggregator Service
Pokazuje jak używać nowych komponentów razem.

Uruchomienie z katalogu backend: cd backend && PYTHONPATH=. python tests/demos/demo_etap2.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.services.signal_aggregator_service import SignalAggregatorService
from app.services.ai_strategy import AIStrategy
from app.utils.database import Database


class MockTelegramService:
    """Mock serwisu Telegram dla demo"""
    
    async def send_message(self, message: str):
        print(f"\n{'='*60}")
        print("TELEGRAM NOTIFICATION:")
        print(f"{'='*60}")
        print(message)
        print(f"{'='*60}\n")
        return True


async def demo_manual_signals():
    """
    Demo 1: Ręczne tworzenie sygnałów i agregacja
    """
    print("\n" + "="*80)
    print("DEMO 1: Ręczna agregacja sygnałów")
    print("="*80)
    
    # Inicjalizacja (z mock database)
    class MockDB:
        def get_analysis_config(self):
            return {"notification_threshold": 60, "is_active": True}
    
    aggregator = SignalAggregatorService(database=MockDB())
    
    # Scenariusz 1: Większość wskazuje BUY
    print("\n--- Scenariusz 1: Większość wskazuje BUY ---")
    
    ai_result = {"recommendation": "BUY", "confidence": 85}
    technical_result = {"signal": "BUY", "confidence": 75}
    macro_result = {"signal": "HOLD", "confidence": 50, "impact": "neutral"}
    news_result = {"sentiment": "positive", "score": 70}
    
    result = await aggregator.aggregate_signals(
        symbol="EUR/USD",
        timeframe="1h",
        ai_result=ai_result,
        technical_result=technical_result,
        macro_result=macro_result,
        news_result=news_result
    )
    
    print(f"\nFinal Signal: {result['final_signal']}")
    print(f"Agreement Score: {result['agreement_score']}%")
    print(f"Weighted Score: {result['weighted_score']:.1f}")
    print(f"Should Notify: {result['should_notify']}")
    print(f"\nVoting Details:")
    for source, details in result['voting_details'].items():
        print(f"  {source:12s}: {details['vote']:4s} ({details['confidence']:3d}%) [weight: {details['weight']}%]")
    print(f"\nDecision Reason:\n{result['decision_reason']}")
    
    # Scenariusz 2: Sprzeczne sygnały
    print("\n\n--- Scenariusz 2: Sprzeczne sygnały ---")
    
    ai_result2 = {"recommendation": "BUY", "confidence": 60}
    technical_result2 = {"signal": "SELL", "confidence": 70}
    macro_result2 = {"signal": "SELL", "confidence": 55}
    news_result2 = {"sentiment": "negative", "score": 45}
    
    result2 = await aggregator.aggregate_signals(
        symbol="GBP/USD",
        timeframe="4h",
        ai_result=ai_result2,
        technical_result=technical_result2,
        macro_result=macro_result2,
        news_result=news_result2
    )
    
    print(f"\nFinal Signal: {result2['final_signal']}")
    print(f"Agreement Score: {result2['agreement_score']}%")
    print(f"Should Notify: {result2['should_notify']}")
    print(f"\nDecision Reason:\n{result2['decision_reason']}")
    
    # Scenariusz 3: Niestandardowe wagi
    print("\n\n--- Scenariusz 3: Niestandardowe wagi (AI=50%, Technical=30%, Macro=10%, News=10%) ---")
    
    custom_weights = {"ai": 50, "technical": 30, "macro": 10, "news": 10}
    aggregator_custom = SignalAggregatorService(database=MockDB(), weights=custom_weights)
    
    result3 = await aggregator_custom.aggregate_signals(
        symbol="USD/JPY",
        timeframe="1h",
        ai_result=ai_result,
        technical_result=technical_result,
        macro_result=macro_result,
        news_result=news_result
    )
    
    print(f"\nFinal Signal: {result3['final_signal']}")
    print(f"Agreement Score: {result3['agreement_score']}%")
    print(f"Weighted Score: {result3['weighted_score']:.1f}")
    print(f"\nCustom Weights: {custom_weights}")


async def demo_comprehensive_analysis():
    """
    Demo 2: Użycie AIStrategy.comprehensive_analysis()
    """
    print("\n\n" + "="*80)
    print("DEMO 2: Comprehensive Analysis + Agregacja")
    print("="*80)
    
    # Inicjalizacja
    telegram = MockTelegramService()
    ai_strategy = AIStrategy(telegram_service=telegram)
    
    # Mock database
    class MockDB:
        def get_analysis_config(self):
            return {"notification_threshold": 60, "is_active": True}
    
    aggregator = SignalAggregatorService(database=MockDB())
    
    print("\nUruchamiam comprehensive_analysis dla EUR/USD...")
    print("(To może potrwać chwilę i może zawieść jeśli brak API keys)")
    
    try:
        # Krok 1: Comprehensive analysis
        analysis = await ai_strategy.comprehensive_analysis("EUR/USD", "1h")
        
        print("\n--- Wyniki Comprehensive Analysis ---")
        print(f"Symbol: {analysis['symbol']}")
        print(f"Timeframe: {analysis['timeframe']}")
        print(f"\nAI Analysis:")
        print(f"  Recommendation: {analysis['ai_analysis']['recommendation']}")
        print(f"  Confidence: {analysis['ai_analysis']['confidence']}%")
        print(f"  Tokens Used: {analysis['ai_analysis']['tokens_used']}")
        print(f"  Estimated Cost: ${analysis['ai_analysis']['estimated_cost']:.6f}")
        
        print(f"\nTechnical Analysis:")
        print(f"  Signal: {analysis['technical_analysis']['signal']}")
        print(f"  Confidence: {analysis['technical_analysis']['confidence']}%")
        
        print(f"\nMacro Analysis:")
        print(f"  Signal: {analysis['macro_analysis']['signal']}")
        print(f"  Impact: {analysis['macro_analysis']['impact']}")
        print(f"  Summary: {analysis['macro_analysis']['summary']}")
        
        print(f"\nNews Analysis:")
        print(f"  Sentiment: {analysis['news_analysis']['sentiment']}")
        print(f"  Score: {analysis['news_analysis']['score']}%")
        print(f"  News Count: {analysis['news_analysis']['news_count']}")
        
        # Krok 2: Agregacja
        print("\n--- Agregacja Sygnałów ---")
        
        result = await aggregator.aggregate_signals(
            symbol=analysis['symbol'],
            timeframe=analysis['timeframe'],
            ai_result=analysis['ai_analysis'],
            technical_result=analysis['technical_analysis'],
            macro_result=analysis['macro_analysis'],
            news_result=analysis['news_analysis']
        )
        
        print(f"\nFinal Signal: {result['final_signal']}")
        print(f"Agreement Score: {result['agreement_score']}%")
        print(f"Weighted Score: {result['weighted_score']:.1f}")
        print(f"Should Notify: {result['should_notify']}")
        print(f"\nDecision Reason:\n{result['decision_reason']}")
        
        # Jeśli powinno być powiadomienie, wyślij je
        if result['should_notify']:
            message = f"""
🚨 SYGNAŁ TRADINGOWY 🚨

Symbol: {analysis['symbol']}
Sygnał: {result['final_signal']}
Zgodność: {result['agreement_score']}%

{result['decision_reason']}

Tokens: {analysis['ai_analysis']['tokens_used']}
Cost: ${analysis['ai_analysis']['estimated_cost']:.6f}
"""
            await telegram.send_message(message)
        
    except Exception as e:
        print(f"\n⚠️  Błąd podczas comprehensive_analysis: {e}")
        print("To może być spowodowane brakiem API keys lub problemami z połączeniem")
        print("Demo kontynuuje z przykładowymi danymi...")


async def demo_technical_indicators():
    """
    Demo 3: Analiza wskaźników technicznych
    """
    print("\n\n" + "="*80)
    print("DEMO 3: Analiza Wskaźników Technicznych")
    print("="*80)
    
    ai_strategy = AIStrategy(telegram_service=MockTelegramService())
    
    # Scenariusz 1: Sygnał BUY (RSI oversold, golden cross)
    print("\n--- Scenariusz 1: Sygnał BUY ---")
    indicators_buy = {
        "rsi": 28,  # Oversold
        "macd": {"value": 0.5, "signal": 0.3, "histogram": 0.2},  # Bullish
        "sma_50": 1.1000,
        "sma_200": 1.0900,  # Golden cross
        "price": 1.1050,
        "bollinger": {"upper": 1.1100, "middle": 1.1000, "lower": 1.0900}
    }
    
    result_buy = ai_strategy._analyze_technical_signal(indicators_buy)
    print(f"Signal: {result_buy['signal']}")
    print(f"Confidence: {result_buy['confidence']}%")
    print(f"RSI: {indicators_buy['rsi']} (oversold)")
    print(f"MA: Golden Cross (SMA50 > SMA200)")
    
    # Scenariusz 2: Sygnał SELL (RSI overbought, death cross)
    print("\n--- Scenariusz 2: Sygnał SELL ---")
    indicators_sell = {
        "rsi": 75,  # Overbought
        "macd": {"value": -0.3, "signal": -0.1, "histogram": -0.2},  # Bearish
        "sma_50": 1.0900,
        "sma_200": 1.1000,  # Death cross
        "price": 1.0850,
        "bollinger": {"upper": 1.1100, "middle": 1.1000, "lower": 1.0900}
    }
    
    result_sell = ai_strategy._analyze_technical_signal(indicators_sell)
    print(f"Signal: {result_sell['signal']}")
    print(f"Confidence: {result_sell['confidence']}%")
    print(f"RSI: {indicators_sell['rsi']} (overbought)")
    print(f"MA: Death Cross (SMA50 < SMA200)")


async def demo_cost_estimation():
    """
    Demo 4: Szacowanie kosztów OpenAI
    """
    print("\n\n" + "="*80)
    print("DEMO 4: Szacowanie Kosztów OpenAI")
    print("="*80)
    
    ai_strategy = AIStrategy(telegram_service=MockTelegramService())
    
    # Przykładowy prompt
    prompt = """
    Analyze EUR/USD with the following data:
    - Technical indicators: RSI=45, MACD=bullish, MA=golden_cross
    - Macro: Fed rate=5.5%, Inflation=2.3%, GDP=2.8%
    - News: 5 articles (3 positive, 1 negative, 1 neutral)
    """ * 10  # Powtórz dla większego promptu
    
    tokens = ai_strategy._count_tokens(prompt)
    
    print(f"\nPrompt length: {len(prompt)} characters")
    print(f"Estimated tokens: {tokens}")
    
    print("\nCost estimates:")
    for model in ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"]:
        cost = ai_strategy._estimate_cost(tokens, model)
        print(f"  {model:20s}: ${cost:.6f}")
    
    # Szacowanie miesięcznych kosztów
    print("\n--- Miesięczne Szacowanie Kosztów ---")
    analyses_per_day = 96  # Co 15 minut = 96 analiz/dzień
    analyses_per_month = analyses_per_day * 30
    
    print(f"Założenia: {analyses_per_day} analiz/dzień, {analyses_per_month} analiz/miesiąc")
    
    for model in ["gpt-4o", "gpt-4o-mini"]:
        cost_per_analysis = ai_strategy._estimate_cost(tokens, model)
        monthly_cost = cost_per_analysis * analyses_per_month
        print(f"\n{model}:")
        print(f"  Koszt/analiza: ${cost_per_analysis:.6f}")
        print(f"  Koszt/miesiąc: ${monthly_cost:.2f}")


async def main():
    """Główna funkcja demo"""
    print("\n" + "="*80)
    print("ETAP 2: SIGNAL AGGREGATOR SERVICE - DEMO")
    print("="*80)
    
    try:
        # Demo 1: Ręczna agregacja
        await demo_manual_signals()
        
        # Demo 2: Comprehensive analysis (może zawieść bez API keys)
        await demo_comprehensive_analysis()
        
        # Demo 3: Analiza techniczna
        await demo_technical_indicators()
        
        # Demo 4: Szacowanie kosztów
        await demo_cost_estimation()
        
        print("\n" + "="*80)
        print("DEMO ZAKOŃCZONE")
        print("="*80)
        print("\n✅ Etap 2 został pomyślnie zaimplementowany!")
        print("\nKomponenty:")
        print("  1. SignalAggregatorService - agregacja sygnałów z 4 źródeł")
        print("  2. AIStrategy.comprehensive_analysis() - kompleksowa analiza")
        print("  3. Config - konfigurowalne wagi i próg powiadomień")
        print("  4. Testy jednostkowe i integracyjne")
        
    except KeyboardInterrupt:
        print("\n\nDemo przerwane przez użytkownika")
    except Exception as e:
        print(f"\n\n❌ Błąd w demo: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
