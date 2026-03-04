"""
Demo Etapu 3 - AIStrategy.comprehensive_analysis() z liczeniem tokenów
Pokazuje pełną funkcjonalność rozbudowanej analizy AI.

Uruchomienie z katalogu backend: cd backend && PYTHONPATH=. python tests/demos/demo_etap3.py
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.services.ai_strategy import AIStrategy
from app.services.signal_aggregator_service import SignalAggregatorService


class MockTelegramService:
    """Mock serwisu Telegram dla demo"""
    
    async def send_message(self, message: str):
        print(f"\n{'='*80}")
        print("📱 TELEGRAM NOTIFICATION:")
        print(f"{'='*80}")
        print(message)
        print(f"{'='*80}\n")
        return True


class MockDatabase:
    """Mock bazy danych dla demo"""
    
    def get_analysis_config(self):
        return {
            "notification_threshold": 60,
            "is_active": True,
            "analysis_interval": 15
        }


def print_section(title: str):
    """Wyświetla nagłówek sekcji"""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")


def print_subsection(title: str):
    """Wyświetla podsekcję"""
    print(f"\n--- {title} ---\n")


async def demo_token_counting():
    """Demo 1: Liczenie tokenów i szacowanie kosztów"""
    print_section("DEMO 1: Liczenie Tokenów i Szacowanie Kosztów")
    
    strategy = AIStrategy(telegram_service=None)
    
    # Przykładowe prompty różnej długości
    prompts = {
        "Krótki": "Analyze EUR/USD",
        "Średni": "Analyze EUR/USD with technical indicators: RSI=45, MACD=bullish, MA=golden_cross. Macro: Fed rate=5.5%, Inflation=2.3%, GDP=2.8%. News: 5 articles (3 positive, 1 negative, 1 neutral).",
        "Długi": """
Analyze EUR/USD with comprehensive data:

Technical Indicators:
- RSI: 45.2 (neutral zone)
- MACD: value=0.0012, signal=0.0008, histogram=0.0004 (bullish crossover)
- Moving Averages: SMA50=1.0850, SMA200=1.0800 (golden cross)
- Bollinger Bands: upper=1.0900, middle=1.0850, lower=1.0800
- Price: 1.0875 (above middle band)

Macro Data:
- Federal Reserve: Current rate 5.50%, next meeting 2025-02-01
- Inflation: CPI annual 3.2%, monthly 0.3%
- GDP: Current growth 2.1%, previous quarter 2.4%

News Analysis (last 24h):
1. "Fed Chair Powell Signals Cautious Approach" - Reuters - Neutral
2. "US Inflation Eases to 3.2%, Below Expectations" - CNBC - Positive
3. "Tech Stocks Rally on Strong Earnings" - WSJ - Positive

Please provide trading recommendation with confidence level.
""" * 3  # Potrójnie dla większego promptu
    }
    
    for prompt_type, prompt_text in prompts.items():
        print_subsection(f"Prompt {prompt_type}")
        
        tokens = strategy._count_tokens(prompt_text)
        
        print(f"Długość tekstu: {len(prompt_text)} znaków")
        print(f"Szacowane tokeny: {tokens}")
        print(f"\nKoszty dla różnych modeli:")
        
        for model in ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"]:
            cost = strategy._estimate_cost(tokens, model)
            print(f"  {model:20s}: ${cost:.6f}")
    
    # Miesięczne szacowanie
    print_subsection("Miesięczne Szacowanie Kosztów")
    
    # Użyj długiego promptu jako przykład
    long_prompt_tokens = strategy._count_tokens(prompts["Długi"])
    
    scenarios = [
        ("5 symboli, co 30 min", 5, 48),
        ("10 symboli, co 15 min", 10, 96),
        ("25 symboli, co 15 min", 25, 96),
        ("25 symboli, co 1h", 25, 24),
    ]
    
    print(f"Założenia: {long_prompt_tokens} tokenów na analizę\n")
    
    for scenario_name, symbols, analyses_per_day in scenarios:
        monthly_analyses = analyses_per_day * 30 * symbols
        cost_4o = strategy._estimate_cost(long_prompt_tokens, "gpt-4o") * monthly_analyses
        cost_mini = strategy._estimate_cost(long_prompt_tokens, "gpt-4o-mini") * monthly_analyses
        
        print(f"{scenario_name}:")
        print(f"  Analiz/miesiąc: {monthly_analyses:,}")
        print(f"  gpt-4o: ${cost_4o:.2f}/miesiąc")
        print(f"  gpt-4o-mini: ${cost_mini:.2f}/miesiąc")
        print(f"  Oszczędności z mini: ${cost_4o - cost_mini:.2f} ({((cost_4o - cost_mini) / cost_4o * 100):.1f}%)")
        print()
    
    print("💡 Rekomendacja: Użyj gpt-4o-mini dla znacznych oszczędności")
    print("   lub ogranicz liczbę symboli/częstotliwość analiz\n")


async def demo_technical_analysis():
    """Demo 2: Analiza wskaźników technicznych"""
    print_section("DEMO 2: Analiza Wskaźników Technicznych")
    
    strategy = AIStrategy(telegram_service=None)
    
    # Scenariusz 1: Sygnał BUY
    print_subsection("Scenariusz 1: Silny Sygnał BUY")
    
    indicators_buy = {
        "rsi": 28,  # Oversold
        "macd": {
            "value": 0.5,
            "signal": 0.3,
            "histogram": 0.2
        },  # Bullish crossover
        "sma_50": 1.1000,
        "sma_200": 1.0900,  # Golden cross
        "price": 1.1050,
        "bollinger": {
            "upper": 1.1100,
            "middle": 1.1000,
            "lower": 1.0900
        }
    }
    
    result_buy = strategy._analyze_technical_signal(indicators_buy)
    
    print(f"Wskaźniki:")
    print(f"  RSI: {indicators_buy['rsi']} (oversold - sygnał kupna)")
    print(f"  MACD: Bullish crossover (histogram > 0)")
    print(f"  MA: Golden Cross (SMA50 > SMA200)")
    print(f"  Cena: {indicators_buy['price']} (powyżej SMA)")
    print(f"\nWynik analizy:")
    print(f"  Sygnał: {result_buy['signal']}")
    print(f"  Confidence: {result_buy['confidence']}%")
    
    # Scenariusz 2: Sygnał SELL
    print_subsection("Scenariusz 2: Silny Sygnał SELL")
    
    indicators_sell = {
        "rsi": 75,  # Overbought
        "macd": {
            "value": -0.3,
            "signal": -0.1,
            "histogram": -0.2
        },  # Bearish crossover
        "sma_50": 1.0900,
        "sma_200": 1.1000,  # Death cross
        "price": 1.0850,
        "bollinger": {
            "upper": 1.1100,
            "middle": 1.1000,
            "lower": 1.0900
        }
    }
    
    result_sell = strategy._analyze_technical_signal(indicators_sell)
    
    print(f"Wskaźniki:")
    print(f"  RSI: {indicators_sell['rsi']} (overbought - sygnał sprzedaży)")
    print(f"  MACD: Bearish crossover (histogram < 0)")
    print(f"  MA: Death Cross (SMA50 < SMA200)")
    print(f"  Cena: {indicators_sell['price']} (poniżej SMA)")
    print(f"\nWynik analizy:")
    print(f"  Sygnał: {result_sell['signal']}")
    print(f"  Confidence: {result_sell['confidence']}%")
    
    # Scenariusz 3: Neutralny
    print_subsection("Scenariusz 3: Neutralny/HOLD")
    
    indicators_hold = {
        "rsi": 50,  # Neutral
        "macd": {
            "value": 0.0,
            "signal": 0.0,
            "histogram": 0.0
        },
        "sma_50": 1.1000,
        "sma_200": 1.1000,
        "price": 1.1000,
        "bollinger": {
            "upper": 1.1100,
            "middle": 1.1000,
            "lower": 1.0900
        }
    }
    
    result_hold = strategy._analyze_technical_signal(indicators_hold)
    
    print(f"Wskaźniki:")
    print(f"  RSI: {indicators_hold['rsi']} (neutral)")
    print(f"  MACD: Flat (brak trendu)")
    print(f"  MA: Równe (brak crossover)")
    print(f"  Cena: {indicators_hold['price']} (na middle band)")
    print(f"\nWynik analizy:")
    print(f"  Sygnał: {result_hold['signal']}")
    print(f"  Confidence: {result_hold['confidence']}%")


async def demo_macro_analysis():
    """Demo 3: Analiza danych makroekonomicznych"""
    print_section("DEMO 3: Analiza Danych Makroekonomicznych")
    
    strategy = AIStrategy(telegram_service=None)
    
    # Scenariusz 1: Pozytywne otoczenie makro
    print_subsection("Scenariusz 1: Pozytywne Otoczenie Makro")
    
    macro_positive = {
        "fed": {"current_rate": 5.5},
        "inflation": {"cpi_annual": 2.0},  # Niska inflacja
        "gdp": {"growth_rate": 3.0}  # Silny wzrost
    }
    
    result_pos = strategy._analyze_macro_signal(macro_positive)
    
    print(f"Dane makro:")
    print(f"  Fed Rate: {macro_positive['fed']['current_rate']}%")
    print(f"  Inflacja CPI: {macro_positive['inflation']['cpi_annual']}% (niska)")
    print(f"  Wzrost PKB: {macro_positive['gdp']['growth_rate']}% (silny)")
    print(f"\nWynik analizy:")
    print(f"  Sygnał: {result_pos['signal']}")
    print(f"  Impact: {result_pos['impact']}")
    print(f"  Confidence: {result_pos['confidence']}%")
    print(f"  Summary: {result_pos['summary']}")
    
    # Scenariusz 2: Negatywne otoczenie makro
    print_subsection("Scenariusz 2: Negatywne Otoczenie Makro")
    
    macro_negative = {
        "fed": {"current_rate": 1.5},  # Niskie stopy
        "inflation": {"cpi_annual": 5.0},  # Wysoka inflacja
        "gdp": {"growth_rate": 0.5}  # Słaby wzrost
    }
    
    result_neg = strategy._analyze_macro_signal(macro_negative)
    
    print(f"Dane makro:")
    print(f"  Fed Rate: {macro_negative['fed']['current_rate']}% (niskie)")
    print(f"  Inflacja CPI: {macro_negative['inflation']['cpi_annual']}% (wysoka)")
    print(f"  Wzrost PKB: {macro_negative['gdp']['growth_rate']}% (słaby)")
    print(f"\nWynik analizy:")
    print(f"  Sygnał: {result_neg['signal']}")
    print(f"  Impact: {result_neg['impact']}")
    print(f"  Confidence: {result_neg['confidence']}%")
    print(f"  Summary: {result_neg['summary']}")


async def demo_news_analysis():
    """Demo 4: Analiza sentimentu wiadomości"""
    print_section("DEMO 4: Analiza Sentimentu Wiadomości")
    
    strategy = AIStrategy(telegram_service=None)
    
    # Scenariusz 1: Pozytywny sentiment
    print_subsection("Scenariusz 1: Pozytywny Sentiment")
    
    news_positive = [
        {"sentiment": "positive", "title": "Strong economic growth reported"},
        {"sentiment": "positive", "title": "Market rally continues on optimism"},
        {"sentiment": "positive", "title": "Tech stocks surge to new highs"},
        {"sentiment": "neutral", "title": "Fed maintains current policy"},
        {"sentiment": "negative", "title": "Minor concerns about inflation"}
    ]
    
    result_pos = strategy._analyze_news_sentiment(news_positive)
    
    print(f"Wiadomości ({len(news_positive)} artykułów):")
    for i, news in enumerate(news_positive, 1):
        emoji = "✅" if news["sentiment"] == "positive" else "❌" if news["sentiment"] == "negative" else "⚪"
        print(f"  {i}. {emoji} {news['title']}")
    
    print(f"\nWynik analizy:")
    print(f"  Sentiment: {result_pos['sentiment']}")
    print(f"  Score: {result_pos['score']}%")
    print(f"  Summary: {result_pos['summary']}")
    
    # Scenariusz 2: Negatywny sentiment
    print_subsection("Scenariusz 2: Negatywny Sentiment")
    
    news_negative = [
        {"sentiment": "negative", "title": "Market crash fears grow"},
        {"sentiment": "negative", "title": "Recession warnings issued"},
        {"sentiment": "negative", "title": "Corporate earnings disappoint"},
        {"sentiment": "neutral", "title": "Central bank meeting scheduled"},
        {"sentiment": "positive", "title": "Some sectors show resilience"}
    ]
    
    result_neg = strategy._analyze_news_sentiment(news_negative)
    
    print(f"Wiadomości ({len(news_negative)} artykułów):")
    for i, news in enumerate(news_negative, 1):
        emoji = "✅" if news["sentiment"] == "positive" else "❌" if news["sentiment"] == "negative" else "⚪"
        print(f"  {i}. {emoji} {news['title']}")
    
    print(f"\nWynik analizy:")
    print(f"  Sentiment: {result_neg['sentiment']}")
    print(f"  Score: {result_neg['score']}%")
    print(f"  Summary: {result_neg['summary']}")


async def demo_comprehensive_with_aggregator():
    """Demo 5: Comprehensive Analysis + Signal Aggregator"""
    print_section("DEMO 5: Comprehensive Analysis + Signal Aggregator")
    
    telegram = MockTelegramService()
    strategy = AIStrategy(telegram_service=telegram)
    aggregator = SignalAggregatorService(database=MockDatabase())
    
    print("🔍 Uruchamiam comprehensive_analysis dla EUR/USD...")
    print("⚠️  Uwaga: To może zawieść jeśli brak API keys lub połączenia\n")
    
    try:
        # Krok 1: Comprehensive Analysis
        analysis = await strategy.comprehensive_analysis("EUR/USD", "1h")
        
        print_subsection("Wyniki Comprehensive Analysis")
        
        print(f"Symbol: {analysis['symbol']}")
        print(f"Timeframe: {analysis['timeframe']}")
        print(f"Timestamp: {analysis['timestamp']}")
        
        print(f"\n🤖 AI Analysis:")
        print(f"  Recommendation: {analysis['ai_analysis']['recommendation']}")
        print(f"  Confidence: {analysis['ai_analysis']['confidence']}%")
        print(f"  Tokens Used: {analysis['ai_analysis']['tokens_used']}")
        print(f"  Estimated Cost: ${analysis['ai_analysis']['estimated_cost']:.6f}")
        if analysis['ai_analysis'].get('reasoning'):
            print(f"  Reasoning: {analysis['ai_analysis']['reasoning'][:200]}...")
        
        print(f"\n📊 Technical Analysis:")
        print(f"  Signal: {analysis['technical_analysis']['signal']}")
        print(f"  Confidence: {analysis['technical_analysis']['confidence']}%")
        
        print(f"\n🌍 Macro Analysis:")
        print(f"  Signal: {analysis['macro_analysis']['signal']}")
        print(f"  Impact: {analysis['macro_analysis']['impact']}")
        print(f"  Confidence: {analysis['macro_analysis']['confidence']}%")
        print(f"  Summary: {analysis['macro_analysis']['summary'][:150]}...")
        
        print(f"\n📰 News Analysis:")
        print(f"  Sentiment: {analysis['news_analysis']['sentiment']}")
        print(f"  Score: {analysis['news_analysis']['score']}%")
        print(f"  News Count: {analysis['news_analysis']['news_count']}")
        
        # Krok 2: Agregacja sygnałów
        print_subsection("Agregacja Sygnałów")
        
        result = await aggregator.aggregate_signals(
            symbol=analysis['symbol'],
            timeframe=analysis['timeframe'],
            ai_result=analysis['ai_analysis'],
            technical_result=analysis['technical_analysis'],
            macro_result=analysis['macro_analysis'],
            news_result=analysis['news_analysis']
        )
        
        print(f"🎯 Final Signal: {result['final_signal']}")
        print(f"📈 Agreement Score: {result['agreement_score']}%")
        print(f"⚖️  Weighted Score: {result['weighted_score']:.1f}")
        print(f"🔔 Should Notify: {'YES' if result['should_notify'] else 'NO'}")
        
        print(f"\n📋 Voting Details:")
        for source, details in result['voting_details'].items():
            print(f"  {source:12s}: {details['vote']:4s} ({details['confidence']:3d}%) [weight: {details['weight']}%]")
        
        print(f"\n💡 Decision Reason:")
        print(result['decision_reason'])
        
        # Jeśli powinno być powiadomienie
        if result['should_notify']:
            print("\n📱 Wysyłam powiadomienie Telegram...")
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
        print("\nDemo kontynuuje z przykładowymi danymi...\n")
        
        # Użyj przykładowych danych
        print_subsection("Przykładowe Dane (Mock)")
        
        mock_analysis = {
            "symbol": "EUR/USD",
            "timeframe": "1h",
            "timestamp": datetime.now().isoformat(),
            "ai_analysis": {
                "recommendation": "BUY",
                "confidence": 75,
                "reasoning": "Techniczne wskaźniki wskazują na oversold, makro wspiera wzrost",
                "tokens_used": 2500,
                "estimated_cost": 0.0225
            },
            "technical_analysis": {
                "signal": "BUY",
                "confidence": 70,
                "indicators": {"rsi": 28, "macd": "bullish"}
            },
            "macro_analysis": {
                "signal": "HOLD",
                "confidence": 50,
                "impact": "neutral",
                "summary": "Fed utrzymuje stopy, inflacja stabilna"
            },
            "news_analysis": {
                "sentiment": "positive",
                "score": 65,
                "news_count": 5,
                "summary": "3 pozytywne, 1 negatywna, 1 neutralna"
            }
        }
        
        result = await aggregator.aggregate_signals(
            symbol=mock_analysis['symbol'],
            timeframe=mock_analysis['timeframe'],
            ai_result=mock_analysis['ai_analysis'],
            technical_result=mock_analysis['technical_analysis'],
            macro_result=mock_analysis['macro_analysis'],
            news_result=mock_analysis['news_analysis']
        )
        
        print(f"🎯 Final Signal: {result['final_signal']}")
        print(f"📈 Agreement Score: {result['agreement_score']}%")
        print(f"⚖️  Weighted Score: {result['weighted_score']:.1f}")
        print(f"\n💡 Decision Reason:")
        print(result['decision_reason'])


async def main():
    """Główna funkcja demo"""
    print("\n" + "="*80)
    print("  ETAP 3: AI STRATEGY COMPREHENSIVE ANALYSIS - DEMO")
    print("="*80)
    print("\nDemo pokazuje:")
    print("  1. Liczenie tokenów i szacowanie kosztów OpenAI")
    print("  2. Analizę wskaźników technicznych")
    print("  3. Analizę danych makroekonomicznych")
    print("  4. Analizę sentimentu wiadomości")
    print("  5. Comprehensive analysis + agregację sygnałów")
    
    try:
        # Demo 1: Token counting
        await demo_token_counting()
        
        # Demo 2: Technical analysis
        await demo_technical_analysis()
        
        # Demo 3: Macro analysis
        await demo_macro_analysis()
        
        # Demo 4: News analysis
        await demo_news_analysis()
        
        # Demo 5: Full pipeline
        await demo_comprehensive_with_aggregator()
        
        print("\n" + "="*80)
        print("  DEMO ZAKOŃCZONE")
        print("="*80)
        print("\n✅ Etap 3 został pomyślnie zaimplementowany!")
        print("\nKomponenty:")
        print("  1. ✅ comprehensive_analysis() - kompleksowa analiza ze wszystkich źródeł")
        print("  2. ✅ _count_tokens() - liczenie tokenów OpenAI")
        print("  3. ✅ _estimate_cost() - szacowanie kosztów dla różnych modeli")
        print("  4. ✅ _analyze_technical_signal() - analiza wskaźników technicznych")
        print("  5. ✅ _analyze_macro_signal() - analiza danych makro")
        print("  6. ✅ _analyze_news_sentiment() - analiza sentimentu wiadomości")
        print("  7. ✅ Integracja z SignalAggregatorService")
        print("\n💡 Następny krok: Etap 4 - AutoAnalysisScheduler")
        
    except KeyboardInterrupt:
        print("\n\nDemo przerwane przez użytkownika")
    except Exception as e:
        print(f"\n\n❌ Błąd w demo: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
