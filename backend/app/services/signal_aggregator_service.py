"""
Signal Aggregator Service - agregacja sygnałów z wielu źródeł
"""
from typing import Dict, Any, Tuple, Optional
import logging
from datetime import datetime


class SignalAggregatorService:
    """
    Serwis agregujący sygnały z różnych źródeł analiz:
    - AI Analysis (OpenAI GPT)
    - Technical Indicators (RSI, MACD, MA, Bollinger)
    - Macro Data (Fed, inflacja, PKB)
    - News Sentiment
    
    Używa systemu głosowania większościowego z konfigurowalnymi wagami.
    """
    
    def __init__(
        self,
        database,
        weights: Optional[Dict[str, int]] = None
    ):
        """
        Inicjalizacja serwisu agregacji
        
        Args:
            database: Instancja Database do pobierania konfiguracji
            weights: Opcjonalne wagi dla źródeł (suma musi wynosić 100)
                    Domyślnie: {"ai": 40, "technical": 30, "macro": 20, "news": 10}
        """
        self.db = database
        self.logger = logging.getLogger("trading_bot.aggregator")
        
        # Domyślne wagi dla różnych źródeł (suma = 100)
        self.weights = weights or {
            "ai": 40,
            "technical": 30,
            "macro": 20,
            "news": 10
        }
        
        # Walidacja wag
        total_weight = sum(self.weights.values())
        if total_weight != 100:
            self.logger.warning(
                f"Suma wag wynosi {total_weight}, normalizuję do 100"
            )
            # Normalizuj wagi
            factor = 100 / total_weight
            self.weights = {k: int(v * factor) for k, v in self.weights.items()}
        
        self.logger.info(f"SignalAggregator initialized with weights: {self.weights}")
    
    async def aggregate_signals(
        self,
        symbol: str,
        timeframe: str,
        ai_result: Dict[str, Any],
        technical_result: Dict[str, Any],
        macro_result: Dict[str, Any],
        news_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Agreguje wszystkie sygnały i zwraca decyzję
        
        Args:
            symbol: Symbol (np. EUR/USD)
            timeframe: Timeframe (1h, 4h, 1d)
            ai_result: Wynik analizy AI
            technical_result: Wynik analizy technicznej
            macro_result: Wynik analizy makro
            news_result: Wynik analizy wiadomości
        
        Returns:
            Słownik z agregowanym sygnałem:
            {
                "final_signal": "BUY" | "SELL" | "HOLD" | "NO_SIGNAL",
                "agreement_score": 75,
                "voting_details": {...},
                "decision_reason": "...",
                "should_notify": True,
                "weighted_score": 72.5
            }
        """
        self.logger.info(f"Aggregating signals for {symbol}")
        
        try:
            # 1. Normalizuj wszystkie sygnały do wspólnego formatu
            normalized_votes = {
                "ai": self._normalize_signal("ai", ai_result),
                "technical": self._normalize_signal("technical", technical_result),
                "macro": self._normalize_signal("macro", macro_result),
                "news": self._normalize_signal("news", news_result)
            }
            
            self.logger.debug(f"Normalized votes: {normalized_votes}")
            
            # 2. Oblicz zgodność i finalny sygnał
            final_signal, agreement_score, weighted_score = self._calculate_agreement(
                normalized_votes
            )
            
            # 3. Dodaj wagi do voting_details
            voting_details = {}
            for source, vote_data in normalized_votes.items():
                voting_details[source] = {
                    **vote_data,
                    "weight": self.weights[source]
                }
            
            # 4. Wygeneruj uzasadnienie decyzji
            decision_reason = self._generate_decision_reason(
                normalized_votes,
                final_signal,
                agreement_score,
                weighted_score
            )
            
            # 5. Sprawdź czy należy wysłać powiadomienie
            should_notify = self._should_generate_signal(
                agreement_score,
                final_signal
            )
            
            result = {
                "final_signal": final_signal,
                "agreement_score": agreement_score,
                "weighted_score": weighted_score,
                "voting_details": voting_details,
                "decision_reason": decision_reason,
                "should_notify": should_notify
            }
            
            self.logger.info(
                f"Aggregation complete: {final_signal} "
                f"(agreement: {agreement_score}%, weighted: {weighted_score:.1f})"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error aggregating signals: {e}", exc_info=True)
            # Zwróć bezpieczny wynik w przypadku błędu
            return {
                "final_signal": "NO_SIGNAL",
                "agreement_score": 0,
                "weighted_score": 0.0,
                "voting_details": {},
                "decision_reason": f"Błąd agregacji: {str(e)}",
                "should_notify": False,
                "error": str(e)
            }
    
    def _normalize_signal(
        self,
        source: str,
        result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Normalizuje różne formaty wyników do wspólnego standardu
        
        Args:
            source: Źródło sygnału (ai, technical, macro, news)
            result: Wynik analizy w oryginalnym formacie
        
        Returns:
            Znormalizowany sygnał: {"vote": "BUY/SELL/HOLD", "confidence": 0-100}
        """
        if not result:
            return {"vote": "HOLD", "confidence": 0}
        
        try:
            if source == "ai":
                # AI: {"recommendation": "BUY", "confidence": 80}
                vote = result.get("recommendation", "HOLD").upper()
                confidence = result.get("confidence", 50)
                
            elif source == "technical":
                # Technical: {"signal": "BUY", "confidence": 70}
                vote = result.get("signal", "HOLD").upper()
                confidence = result.get("confidence", 50)
                
            elif source == "macro":
                # Macro: {"signal": "HOLD", "impact": "neutral"}
                signal = result.get("signal", "HOLD").upper()
                impact = result.get("impact", "neutral").lower()
                
                vote = signal
                # Mapuj impact na confidence
                impact_to_confidence = {
                    "positive": 70,
                    "bullish": 70,
                    "negative": 30,
                    "bearish": 30,
                    "neutral": 50
                }
                confidence = result.get("confidence", impact_to_confidence.get(impact, 50))
                
            elif source == "news":
                # News: {"sentiment": "positive", "score": 65}
                sentiment = result.get("sentiment", "neutral").lower()
                score = result.get("score", 50)
                
                # Mapuj sentiment na vote
                sentiment_to_vote = {
                    "positive": "BUY",
                    "bullish": "BUY",
                    "negative": "SELL",
                    "bearish": "SELL",
                    "neutral": "HOLD"
                }
                vote = sentiment_to_vote.get(sentiment, "HOLD")
                confidence = score
                
            else:
                vote = "HOLD"
                confidence = 0
            
            # Walidacja
            if vote not in ["BUY", "SELL", "HOLD"]:
                self.logger.warning(f"Invalid vote '{vote}' from {source}, defaulting to HOLD")
                vote = "HOLD"
            
            confidence = max(0, min(100, confidence))  # Ogranicz do 0-100
            
            return {
                "vote": vote,
                "confidence": confidence
            }
            
        except Exception as e:
            self.logger.error(f"Error normalizing {source} signal: {e}")
            return {"vote": "HOLD", "confidence": 0}
    
    def _calculate_agreement(
        self,
        votes: Dict[str, Dict[str, Any]]
    ) -> Tuple[str, int, float]:
        """
        Oblicza zgodność głosów i finalny sygnał
        
        Args:
            votes: Znormalizowane głosy ze wszystkich źródeł
        
        Returns:
            Tuple: (final_signal, agreement_score, weighted_score)
        """
        # Oblicz weighted score dla każdego kierunku
        direction_scores = {
            "BUY": 0.0,
            "SELL": 0.0,
            "HOLD": 0.0
        }
        
        total_weighted_confidence = 0.0
        
        for source, vote_data in votes.items():
            vote = vote_data["vote"]
            confidence = vote_data["confidence"]
            weight = self.weights.get(source, 0)
            
            # Weighted score = confidence * weight / 100
            weighted_confidence = (confidence * weight) / 100
            direction_scores[vote] += weighted_confidence
            total_weighted_confidence += weighted_confidence
        
        # Znajdź kierunek z największym score
        final_signal = max(direction_scores, key=direction_scores.get)
        winner_score = direction_scores[final_signal]
        
        # Oblicz agreement_score
        # Agreement = (score_zwycięzcy / suma_wszystkich) * 100
        if total_weighted_confidence > 0:
            agreement_score = int((winner_score / total_weighted_confidence) * 100)
        else:
            agreement_score = 0
            final_signal = "NO_SIGNAL"
        
        # Jeśli wszystkie głosy to HOLD i confidence < 30, to NO_SIGNAL
        if final_signal == "HOLD" and winner_score < 30:
            final_signal = "NO_SIGNAL"
        
        self.logger.debug(
            f"Direction scores: {direction_scores}, "
            f"Winner: {final_signal} ({winner_score:.1f})"
        )
        
        return final_signal, agreement_score, winner_score
    
    def _generate_decision_reason(
        self,
        votes: Dict[str, Dict[str, Any]],
        final_signal: str,
        agreement_score: int,
        weighted_score: float
    ) -> str:
        """
        Generuje czytelne uzasadnienie decyzji w języku polskim
        
        Args:
            votes: Znormalizowane głosy
            final_signal: Finalny sygnał
            agreement_score: Scoring zgodności
            weighted_score: Ważony score
        
        Returns:
            Sformatowane uzasadnienie decyzji
        """
        if final_signal == "NO_SIGNAL":
            return "Brak wystarczających danych do wygenerowania sygnału"
        
        # Podziel źródła na zgodne i niezgodne
        supporting = []
        opposing = []
        neutral = []
        
        source_names = {
            "ai": "AI",
            "technical": "Technical",
            "macro": "Macro",
            "news": "News"
        }
        
        for source, vote_data in votes.items():
            vote = vote_data["vote"]
            confidence = vote_data["confidence"]
            name = source_names.get(source, source)
            
            if vote == final_signal:
                supporting.append(f"{name} ({confidence}%)")
            elif vote == "HOLD":
                neutral.append(f"{name} ({confidence}%)")
            else:
                opposing.append(f"{name} ({confidence}%)")
        
        # Buduj uzasadnienie
        lines = [f"Sygnał {final_signal} z {agreement_score}% zgodnością:"]
        
        if supporting:
            lines.append("✓ Za: " + ", ".join(supporting))
        
        if opposing:
            lines.append("✗ Przeciw: " + ", ".join(opposing))
        
        if neutral:
            lines.append("⚠ Neutralne: " + ", ".join(neutral))
        
        lines.append(f"\nWeighted score: {weighted_score:.1f}/100")
        
        return "\n".join(lines)
    
    def _should_generate_signal(
        self,
        agreement_score: int,
        final_signal: str
    ) -> bool:
        """
        Decyduje czy wygenerować sygnał i powiadomienie
        
        Args:
            agreement_score: Scoring zgodności (0-100)
            final_signal: Finalny sygnał
        
        Returns:
            True jeśli należy wysłać powiadomienie
        """
        # Pobierz próg z konfiguracji
        try:
            config = self.db.get_analysis_config()
            threshold = config.get("notification_threshold", 60)
        except Exception as e:
            self.logger.warning(f"Could not get config, using default threshold: {e}")
            threshold = 60
        
        # Kryteria powiadomienia:
        # 1. Agreement score >= threshold
        # 2. Final signal to BUY lub SELL (nie HOLD ani NO_SIGNAL)
        should_notify = (
            agreement_score >= threshold and
            final_signal in ["BUY", "SELL"]
        )
        
        self.logger.debug(
            f"Should notify: {should_notify} "
            f"(agreement: {agreement_score} >= {threshold}, signal: {final_signal})"
        )
        
        return should_notify
    
    def update_weights(self, new_weights: Dict[str, int]) -> bool:
        """
        Aktualizuje wagi źródeł
        
        Args:
            new_weights: Nowe wagi (suma musi wynosić 100)
        
        Returns:
            True jeśli zaktualizowano pomyślnie
        """
        total = sum(new_weights.values())
        if total != 100:
            self.logger.error(f"Invalid weights sum: {total}, expected 100")
            return False
        
        self.weights = new_weights
        self.logger.info(f"Weights updated: {self.weights}")
        return True
    
    def get_weights(self) -> Dict[str, int]:
        """Zwraca aktualne wagi"""
        return self.weights.copy()


# Test
if __name__ == "__main__":
    import asyncio
    
    async def test_aggregator():
        # Mock database
        class MockDB:
            def get_analysis_config(self):
                return {"notification_threshold": 60}
        
        aggregator = SignalAggregatorService(database=MockDB())
        
        # Test case 1: Większość wskazuje BUY
        ai_result = {"recommendation": "BUY", "confidence": 80}
        technical_result = {"signal": "BUY", "confidence": 70}
        macro_result = {"signal": "HOLD", "confidence": 50, "impact": "neutral"}
        news_result = {"sentiment": "positive", "score": 65}
        
        result = await aggregator.aggregate_signals(
            symbol="EUR/USD",
            timeframe="1h",
            ai_result=ai_result,
            technical_result=technical_result,
            macro_result=macro_result,
            news_result=news_result
        )
        
        print("\n=== TEST 1: Majority BUY ===")
        print(f"Final Signal: {result['final_signal']}")
        print(f"Agreement Score: {result['agreement_score']}%")
        print(f"Weighted Score: {result['weighted_score']:.1f}")
        print(f"Should Notify: {result['should_notify']}")
        print(f"\nDecision Reason:\n{result['decision_reason']}")
        
        # Test case 2: Sprzeczne sygnały
        ai_result2 = {"recommendation": "BUY", "confidence": 60}
        technical_result2 = {"signal": "SELL", "confidence": 65}
        macro_result2 = {"signal": "HOLD", "confidence": 50}
        news_result2 = {"sentiment": "negative", "score": 55}
        
        result2 = await aggregator.aggregate_signals(
            symbol="GBP/USD",
            timeframe="4h",
            ai_result=ai_result2,
            technical_result=technical_result2,
            macro_result=macro_result2,
            news_result=news_result2
        )
        
        print("\n=== TEST 2: Conflicting Signals ===")
        print(f"Final Signal: {result2['final_signal']}")
        print(f"Agreement Score: {result2['agreement_score']}%")
        print(f"Should Notify: {result2['should_notify']}")
        print(f"\nDecision Reason:\n{result2['decision_reason']}")
    
    asyncio.run(test_aggregator())
