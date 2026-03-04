"""
Re-eksport AIStrategy z pakietu ai (kompatybilność wsteczna).
"""
from app.services.ai import AIStrategy

__all__ = ["AIStrategy"]


if __name__ == "__main__":
    import asyncio

    async def _run_test() -> None:
        strategy = AIStrategy()
        result = await strategy.analyze_and_generate_signal(
            symbol="EUR/USD", timeframe="1h"
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

    asyncio.run(_run_test())
