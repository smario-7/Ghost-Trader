"""
Serwis strategii tradingowych
"""
from typing import List, Dict, Any, Optional
import logging

from ..utils.database import Database
from .telegram_service import TelegramService
from .market_data_service import MarketDataService
from ..models.models import (
    StrategyCreate,
    StrategyUpdate,
    SignalType,
    StrategyType,
)
from ..exceptions import StrategyNotFoundException
from .signal_checkers import SIGNAL_CHECKERS


class StrategyService:
    """Serwis zarządzający strategiami tradingowymi"""
    
    def __init__(self, database: Database, telegram: TelegramService):
        """
        Inicjalizacja serwisu
        
        Args:
            database: Instancja bazy danych
            telegram: Instancja serwisu Telegram
        """
        self.db = database
        self.telegram = telegram
        # Upewnij się, że telegram ma dostęp do bazy danych
        if hasattr(telegram, 'database') and telegram.database is None:
            telegram.database = database
        self.market_data = MarketDataService(database=database)
        self.logger = logging.getLogger("trading_bot.strategy")
    
    # ===== ZARZĄDZANIE STRATEGIAMI =====
    
    def create_strategy(self, strategy: StrategyCreate) -> Dict[str, Any]:
        """Tworzy nową strategię"""
        try:
            strategy_data = strategy.model_dump()
            strategy_id = self.db.create_strategy(strategy_data)
            
            self.logger.info(f"Strategy created: {strategy.name} (ID: {strategy_id})")
            
            return {
                "id": strategy_id,
                "message": f"Strategy '{strategy.name}' created successfully"
            }
        except Exception as e:
            self.logger.error(f"Error creating strategy: {e}")
            raise
    
    def get_all_strategies(self) -> List[Dict[str, Any]]:
        """Pobiera wszystkie strategie"""
        try:
            return self.db.get_all_strategies()
        except Exception as e:
            self.logger.error(f"Error getting strategies: {e}")
            raise
    
    def get_strategy(self, strategy_id: int) -> Optional[Dict[str, Any]]:
        """Pobiera strategię po ID.

        Args:
            strategy_id: ID strategii.

        Returns:
            Słownik z danymi strategii.

        Raises:
            StrategyNotFoundException: Gdy strategia o podanym ID nie istnieje.
        """
        try:
            strategy = self.db.get_strategy(strategy_id)
            if strategy is None:
                raise StrategyNotFoundException(strategy_id)
            return strategy
        except StrategyNotFoundException:
            raise
        except Exception as e:
            self.logger.error(f"Error getting strategy {strategy_id}: {e}")
            raise
    
    def update_strategy(
        self,
        strategy_id: int,
        strategy: StrategyUpdate
    ) -> Dict[str, Any]:
        """Aktualizuje strategię. Zmienia tylko przekazane pola.

        Args:
            strategy_id: ID strategii.
            strategy: Pola do aktualizacji (StrategyUpdate).

        Returns:
            Słownik z "message".

        Raises:
            StrategyNotFoundException: Gdy strategia o podanym ID nie istnieje.
        """
        try:
            # Pobierz tylko wypełnione pola
            updates = strategy.model_dump(exclude_unset=True)
            
            if not updates:
                return {"message": "No fields to update"}
            
            success = self.db.update_strategy(strategy_id, updates)
            if not success:
                raise StrategyNotFoundException(strategy_id)
            self.logger.info(f"Strategy updated: {strategy_id}")
            return {"message": f"Strategy {strategy_id} updated successfully"}
        except StrategyNotFoundException:
            raise
        except Exception as e:
            self.logger.error(f"Error updating strategy {strategy_id}: {e}")
            raise
    
    def delete_strategy(self, strategy_id: int) -> Dict[str, Any]:
        """Usuwa strategię po ID.

        Args:
            strategy_id: ID strategii.

        Returns:
            Słownik z "message".

        Raises:
            StrategyNotFoundException: Gdy strategia o podanym ID nie istnieje.
        """
        try:
            success = self.db.delete_strategy(strategy_id)
            if not success:
                raise StrategyNotFoundException(strategy_id)
            self.logger.info(f"Strategy deleted: {strategy_id}")
            return {"message": f"Strategy {strategy_id} deleted successfully"}
        except StrategyNotFoundException:
            raise
        except Exception as e:
            self.logger.error(f"Error deleting strategy {strategy_id}: {e}")
            raise
    
    # ===== SPRAWDZANIE SYGNAŁÓW =====
    
    async def check_all_signals(
        self,
        *,
        persist: bool = True,
        notify: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Sprawdza sygnały dla wszystkich aktywnych strategii
        
        Returns:
            Lista wyników dla każdej strategii
        """
        strategies = self.db.get_active_strategies()
        results = []
        
        for strategy in strategies:
            try:
                result = await self.check_strategy_signal(strategy, persist=persist, notify=notify)
                results.append(result)
            except Exception as e:
                self.logger.error(
                    f"Error checking strategy {strategy['name']}: {e}"
                )
                results.append({
                    "strategy_id": strategy['id'],
                    "strategy_name": strategy['name'],
                    "error": str(e)
                })
        
        return results
    
    async def check_strategy_signal(
        self,
        strategy: Dict[str, Any],
        *,
        persist: bool = True,
        notify: bool = True,
    ) -> Dict[str, Any]:
        """
        Sprawdza sygnał dla pojedynczej strategii
        
        Args:
            strategy: Dane strategii
        
        Returns:
            Wynik sprawdzenia
        """
        strategy_type = strategy['strategy_type']
        strategy_name = strategy['name']
        symbol = strategy['symbol']
        
        # Loguj rozpoczęcie analizy
        self.db.create_activity_log(
            log_type='analysis',
            message=f"Rozpoczęcie analizy strategii {strategy_name}",
            symbol=symbol,
            strategy_name=strategy_name,
            details={
                'strategy_type': strategy_type,
                'strategy_id': strategy['id']
            },
            status='success'
        )
        
        if strategy_type in SIGNAL_CHECKERS:
            checker_class = SIGNAL_CHECKERS[strategy_type]
            checker = checker_class(
                self.db, self.telegram, self.market_data, self.logger
            )
            result = await checker.execute(strategy, persist=persist, notify=notify)
        else:
            result = {
                "strategy_id": strategy['id'],
                "strategy_name": strategy['name'],
                "signal": SignalType.HOLD,
                "message": "Unknown strategy type"
            }
        
        # Loguj zakończenie analizy
        signal = result.get('signal', 'HOLD')
        self.db.create_activity_log(
            log_type='analysis',
            message=f"Analiza zakończona: {signal} dla {symbol}",
            symbol=symbol,
            strategy_name=strategy_name,
            details={
                'strategy_type': strategy_type,
                'signal': signal,
                'indicators': result.get('indicators', {})
            },
            status='success' if signal != 'HOLD' else 'success'
        )
        
        return result

    # ===== STATYSTYKI =====
    
    def get_statistics(self) -> Dict[str, Any]:
        """Pobiera statystyki"""
        try:
            stats = self.db.get_statistics()
            
            # Dodaj czas działania (uptime)
            # W rzeczywistej implementacji byłby to czas od startu aplikacji
            stats['uptime'] = "N/A"
            
            return stats
        except Exception as e:
            self.logger.error(f"Error getting statistics: {e}")
            raise
    
    def get_strategy_signals(
        self,
        strategy_id: int,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Pobiera sygnały dla strategii"""
        try:
            return self.db.get_signals_by_strategy(strategy_id, limit)
        except Exception as e:
            self.logger.error(f"Error getting signals for strategy {strategy_id}: {e}")
            raise
    
    def get_recent_signals(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Pobiera ostatnie sygnały"""
        try:
            return self.db.get_recent_signals(limit)
        except Exception as e:
            self.logger.error(f"Error getting recent signals: {e}")
            raise
