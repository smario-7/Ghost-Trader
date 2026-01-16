"""
Prosty test Etapu 2 bez zewnętrznych zależności
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.services.signal_aggregator_service import SignalAggregatorService


class MockDatabase:
    """Mock bazy danych"""
    
    def get_analysis_config(self):
        return {
            "notification_threshold": 60,
            "is_active": True
        }


async def test_aggregator():
    """Test podstawowej funkcjonalności agregatora"""
    
    print("\n" + "="*80)
    print("TEST ETAPU 2: Signal Aggregator Service")
    print("="*80)
    
    # Inicjalizacja
    db = MockDatabase()
    aggregator = SignalAggregatorService(database=db)
    
    print("\n✅ SignalAggregatorService zainicjalizowany")
    print(f"Wagi: {aggregator.get_weights()}")
    
    # Test 1: Większość wskazuje BUY
    print("\n" + "-"*80)
    print("TEST 1: Większość wskazuje BUY")
    print("-"*80)
    
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
    
    print(f"\n📊 Wyniki:")
    print(f"  Final Signal: {result['final_signal']}")
    print(f"  Agreement Score: {result['agreement_score']}%")
    print(f"  Weighted Score: {result['weighted_score']:.1f}")
    print(f"  Should Notify: {result['should_notify']}")
    
    print(f"\n🗳️  Voting Details:")
    for source, details in result['voting_details'].items():
        print(f"  {source:12s}: {details['vote']:4s} ({details['confidence']:3d}%) [weight: {details['weight']}%]")
    
    print(f"\n📝 Decision Reason:")
    print(result['decision_reason'])
    
    assert result['final_signal'] == 'BUY', "Oczekiwano sygnału BUY"
    assert result['should_notify'] == True, "Powinno być powiadomienie"
    print("\n✅ Test 1 PASSED")
    
    # Test 2: Sprzeczne sygnały
    print("\n" + "-"*80)
    print("TEST 2: Sprzeczne sygnały")
    print("-"*80)
    
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
    
    print(f"\n📊 Wyniki:")
    print(f"  Final Signal: {result2['final_signal']}")
    print(f"  Agreement Score: {result2['agreement_score']}%")
    print(f"  Weighted Score: {result2['weighted_score']:.1f}")
    print(f"  Should Notify: {result2['should_notify']}")
    
    print(f"\n🗳️  Voting Details:")
    for source, details in result2['voting_details'].items():
        print(f"  {source:12s}: {details['vote']:4s} ({details['confidence']:3d}%) [weight: {details['weight']}%]")
    
    print(f"\n📝 Decision Reason:")
    print(result2['decision_reason'])
    
    assert result2['final_signal'] == 'SELL', "Oczekiwano sygnału SELL"
    print("\n✅ Test 2 PASSED")
    
    # Test 3: Niestandardowe wagi
    print("\n" + "-"*80)
    print("TEST 3: Niestandardowe wagi")
    print("-"*80)
    
    custom_weights = {"ai": 50, "technical": 30, "macro": 10, "news": 10}
    aggregator_custom = SignalAggregatorService(database=db, weights=custom_weights)
    
    print(f"Niestandardowe wagi: {custom_weights}")
    
    result3 = await aggregator_custom.aggregate_signals(
        symbol="USD/JPY",
        timeframe="1h",
        ai_result=ai_result,
        technical_result=technical_result,
        macro_result=macro_result,
        news_result=news_result
    )
    
    print(f"\n📊 Wyniki:")
    print(f"  Final Signal: {result3['final_signal']}")
    print(f"  Agreement Score: {result3['agreement_score']}%")
    print(f"  Weighted Score: {result3['weighted_score']:.1f}")
    
    assert result3['final_signal'] == 'BUY', "Oczekiwano sygnału BUY"
    print("\n✅ Test 3 PASSED")
    
    # Test 4: Aktualizacja wag
    print("\n" + "-"*80)
    print("TEST 4: Aktualizacja wag")
    print("-"*80)
    
    new_weights = {"ai": 60, "technical": 20, "macro": 10, "news": 10}
    success = aggregator.update_weights(new_weights)
    
    assert success == True, "Aktualizacja wag powinna się udać"
    assert aggregator.get_weights() == new_weights, "Wagi nie zostały zaktualizowane"
    
    print(f"Wagi zaktualizowane: {aggregator.get_weights()}")
    print("✅ Test 4 PASSED")
    
    # Test 5: Nieprawidłowa suma wag
    print("\n" + "-"*80)
    print("TEST 5: Nieprawidłowa suma wag")
    print("-"*80)
    
    invalid_weights = {"ai": 50, "technical": 30, "macro": 20, "news": 10}  # suma = 110
    success = aggregator.update_weights(invalid_weights)
    
    assert success == False, "Aktualizacja z nieprawidłową sumą powinna zawieść"
    print("✅ Test 5 PASSED - nieprawidłowa suma została odrzucona")
    
    # Podsumowanie
    print("\n" + "="*80)
    print("WSZYSTKIE TESTY ZAKOŃCZONE POMYŚLNIE! ✅")
    print("="*80)
    
    print("\n📦 Zaimplementowane komponenty:")
    print("  1. ✅ SignalAggregatorService")
    print("     - aggregate_signals()")
    print("     - _normalize_signal()")
    print("     - _calculate_agreement()")
    print("     - _generate_decision_reason()")
    print("     - _should_generate_signal()")
    print("     - update_weights()")
    print("     - get_weights()")
    
    print("\n  2. ✅ AIStrategy rozszerzenia")
    print("     - comprehensive_analysis()")
    print("     - _count_tokens()")
    print("     - _estimate_cost()")
    print("     - _analyze_technical_signal()")
    print("     - _analyze_macro_signal()")
    print("     - _analyze_news_sentiment()")
    
    print("\n  3. ✅ Config rozszerzenia")
    print("     - aggregator_weight_ai")
    print("     - aggregator_weight_technical")
    print("     - aggregator_weight_macro")
    print("     - aggregator_weight_news")
    print("     - notification_threshold")
    print("     - validate_weights_sum()")
    print("     - get_aggregator_weights()")
    
    print("\n  4. ✅ Testy")
    print("     - test_signal_aggregator.py (testy jednostkowe)")
    print("     - test_integration.py (testy integracyjne)")
    
    print("\n🎉 ETAP 2 UKOŃCZONY!")


if __name__ == "__main__":
    try:
        asyncio.run(test_aggregator())
    except Exception as e:
        print(f"\n❌ Błąd: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
