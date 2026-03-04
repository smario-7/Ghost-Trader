"""
Klasa bazowa i model wyniku dla checkerów sygnałów.
Wspólna logika: pobierz dane → evaluate → zapisz sygnał / powiadom → zwróć wynik.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional
import logging

from ...utils.database import Database
from ...models.models import SignalType
from ..telegram_service import TelegramService
from ..market_data_service import MarketDataService


@dataclass
class SignalEvaluation:
    """Wynik oceny sygnału zwracany przez evaluate()."""
    signal_type: SignalType
    indicator_values: Optional[Dict[str, Any]]
    message: str
    price: float


class BaseSignalChecker(ABC):
    """Abstrakcyjna klasa bazowa dla sprawdzania sygnałów. Wspólna logika w execute()."""

    def __init__(
        self,
        db: Database,
        telegram: TelegramService,
        market_data: MarketDataService,
        logger: logging.Logger,
    ):
        self.db = db
        self.telegram = telegram
        self.market_data = market_data
        self.logger = logger

    async def execute(
        self,
        strategy: Dict[str, Any],
        *,
        persist: bool = True,
        notify: bool = True,
    ) -> Dict[str, Any]:
        """
        Szablon: pobierz wskaźniki, wywołaj evaluate(), przy BUY/SELL zapisz i wyślij, zwróć słownik.
        """
        symbol = strategy["symbol"]
        timeframe = strategy["timeframe"]
        params = strategy["parameters"]
        strategy_id = strategy["id"]
        strategy_name = strategy["name"]

        try:
            indicators = await self.market_data.get_technical_indicators(
                symbol=symbol,
                timeframe=timeframe,
                indicators_config=params,
            )
            ev = self.evaluate(strategy, indicators)

            if ev.signal_type in (SignalType.BUY, SignalType.SELL):
                signal_id = None
                if persist:
                    signal_id = self.db.create_signal({
                        "strategy_id": strategy_id,
                        "signal_type": ev.signal_type.value,
                        "price": ev.price,
                        "indicator_values": ev.indicator_values or {},
                        "message": ev.message or f"{ev.signal_type.value} signal",
                    })
                    self.db.create_activity_log(
                        log_type="signal",
                        message=f"Wygenerowano sygnał {ev.signal_type.value} dla {strategy_name}",
                        symbol=symbol,
                        strategy_name=strategy_name,
                        details={
                            "signal_type": ev.signal_type.value,
                            **(ev.indicator_values or {}),
                        },
                        status="success",
                    )

                if notify:
                    await self.telegram.send_signal(
                        signal_type=ev.signal_type.value,
                        strategy_name=strategy_name,
                        symbol=symbol,
                        price=ev.price,
                        indicator_values=ev.indicator_values or {},
                    )
                self.logger.info(
                    f"Signal generated: {ev.signal_type.value} for {strategy_name} "
                    f"(Price: {ev.price:.2f})"
                )
                return {
                    "strategy_id": strategy_id,
                    "strategy_name": strategy_name,
                    "signal": ev.signal_type.value,
                    "signal_id": signal_id,
                    "price": ev.price,
                    "indicators": ev.indicator_values,
                }
            else:
                return {
                    "strategy_id": strategy_id,
                    "strategy_name": strategy_name,
                    "signal": SignalType.HOLD,
                    "message": ev.message,
                    "indicators": ev.indicator_values or {},
                }
        except Exception as e:
            self.logger.error(
                f"Błąd sprawdzania sygnału dla {strategy_name}: {e}",
                exc_info=True,
            )
            return {
                "strategy_id": strategy_id,
                "strategy_name": strategy_name,
                "signal": SignalType.HOLD,
                "message": f"Błąd: {str(e)}",
            }

    @abstractmethod
    def evaluate(self, strategy: Dict[str, Any], indicators: Dict[str, Any]) -> SignalEvaluation:
        """Określa sygnał na podstawie wskaźników. Implementacja w klasach pochodnych."""
        pass
