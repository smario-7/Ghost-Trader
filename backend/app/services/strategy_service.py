"""
Serwis strategii tradingowych
"""
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

from ..utils.database import Database
from .telegram_service import TelegramService
from ..models.models import (
    StrategyCreate,
    StrategyUpdate,
    SignalType,
    StrategyType
)


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
        """Pobiera strategię po ID"""
        try:
            return self.db.get_strategy(strategy_id)
        except Exception as e:
            self.logger.error(f"Error getting strategy {strategy_id}: {e}")
            raise
    
    def update_strategy(
        self,
        strategy_id: int,
        strategy: StrategyUpdate
    ) -> Dict[str, Any]:
        """Aktualizuje strategię"""
        try:
            # Pobierz tylko wypełnione pola
            updates = strategy.model_dump(exclude_unset=True)
            
            if not updates:
                return {"message": "No fields to update"}
            
            success = self.db.update_strategy(strategy_id, updates)
            
            if success:
                self.logger.info(f"Strategy updated: {strategy_id}")
                return {"message": f"Strategy {strategy_id} updated successfully"}
            else:
                return {"message": f"Strategy {strategy_id} not found"}
        except Exception as e:
            self.logger.error(f"Error updating strategy {strategy_id}: {e}")
            raise
    
    def delete_strategy(self, strategy_id: int) -> Dict[str, Any]:
        """Usuwa strategię"""
        try:
            success = self.db.delete_strategy(strategy_id)
            
            if success:
                self.logger.info(f"Strategy deleted: {strategy_id}")
                return {"message": f"Strategy {strategy_id} deleted successfully"}
            else:
                return {"message": f"Strategy {strategy_id} not found"}
        except Exception as e:
            self.logger.error(f"Error deleting strategy {strategy_id}: {e}")
            raise
    
    # ===== SPRAWDZANIE SYGNAŁÓW =====
    
    async def check_all_signals(self) -> List[Dict[str, Any]]:
        """
        Sprawdza sygnały dla wszystkich aktywnych strategii
        
        Returns:
            Lista wyników dla każdej strategii
        """
        strategies = self.db.get_active_strategies()
        results = []
        
        for strategy in strategies:
            try:
                result = await self.check_strategy_signal(strategy)
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
        strategy: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Sprawdza sygnał dla pojedynczej strategii
        
        Args:
            strategy: Dane strategii
        
        Returns:
            Wynik sprawdzenia
        """
        strategy_type = strategy['strategy_type']
        
        # Wybierz odpowiednią funkcję sprawdzającą
        if strategy_type == StrategyType.RSI:
            return await self._check_rsi_signal(strategy)
        elif strategy_type == StrategyType.MACD:
            return await self._check_macd_signal(strategy)
        elif strategy_type == StrategyType.BOLLINGER:
            return await self._check_bollinger_signal(strategy)
        elif strategy_type == StrategyType.MOVING_AVERAGE:
            return await self._check_ma_signal(strategy)
        else:
            return {
                "strategy_id": strategy['id'],
                "strategy_name": strategy['name'],
                "signal": SignalType.HOLD,
                "message": "Unknown strategy type"
            }
    
    async def _check_rsi_signal(
        self,
        strategy: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Sprawdza sygnał RSI
        
        Logika:
        - RSI < oversold (np. 30) → BUY
        - RSI > overbought (np. 70) → SELL
        - Inaczej → HOLD
        """
        params = strategy['parameters']
        
        # W rzeczywistej implementacji tutaj byłoby pobieranie danych z API
        # i obliczanie RSI. Na potrzeby demo, symulujemy:
        import random
        rsi_value = random.uniform(20, 80)
        current_price = random.uniform(40000, 50000)
        
        oversold = params.get('oversold', 30)
        overbought = params.get('overbought', 70)
        
        # Określ sygnał
        if rsi_value < oversold:
            signal_type = SignalType.BUY
        elif rsi_value > overbought:
            signal_type = SignalType.SELL
        else:
            signal_type = SignalType.HOLD
        
        # Jeśli jest sygnał BUY lub SELL, zapisz i wyślij
        if signal_type in [SignalType.BUY, SignalType.SELL]:
            indicator_values = {
                'RSI': round(rsi_value, 2),
                'oversold': oversold,
                'overbought': overbought,
                'price': current_price
            }
            
            # Zapisz sygnał do bazy
            signal_id = self.db.create_signal({
                'strategy_id': strategy['id'],
                'signal_type': signal_type.value,
                'price': current_price,
                'indicator_values': indicator_values,
                'message': f"RSI {signal_type.value} signal"
            })
            
            # Wyślij przez Telegram
            await self.telegram.send_signal(
                signal_type=signal_type.value,
                strategy_name=strategy['name'],
                symbol=strategy['symbol'],
                price=current_price,
                indicator_values=indicator_values
            )
            
            self.logger.info(
                f"Signal generated: {signal_type.value} for {strategy['name']}"
            )
            
            return {
                "strategy_id": strategy['id'],
                "strategy_name": strategy['name'],
                "signal": signal_type.value,
                "signal_id": signal_id,
                "price": current_price,
                "indicators": indicator_values
            }
        else:
            return {
                "strategy_id": strategy['id'],
                "strategy_name": strategy['name'],
                "signal": SignalType.HOLD,
                "message": "No signal"
            }
    
    async def _check_macd_signal(
        self,
        strategy: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Sprawdza sygnał MACD"""
        # Placeholder - implementacja podobna do RSI
        return {
            "strategy_id": strategy['id'],
            "strategy_name": strategy['name'],
            "signal": SignalType.HOLD,
            "message": "MACD checking not implemented yet"
        }
    
    async def _check_bollinger_signal(
        self,
        strategy: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Sprawdza sygnał Bollinger Bands"""
        # Placeholder - implementacja podobna do RSI
        return {
            "strategy_id": strategy['id'],
            "strategy_name": strategy['name'],
            "signal": SignalType.HOLD,
            "message": "Bollinger checking not implemented yet"
        }
    
    async def _check_ma_signal(
        self,
        strategy: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Sprawdza sygnał Moving Average"""
        # Placeholder - implementacja podobna do RSI
        return {
            "strategy_id": strategy['id'],
            "strategy_name": strategy['name'],
            "signal": SignalType.HOLD,
            "message": "MA checking not implemented yet"
        }
    
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
