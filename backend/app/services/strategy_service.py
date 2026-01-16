"""
Serwis strategii tradingowych
"""
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

from ..utils.database import Database
from .telegram_service import TelegramService
from .market_data_service import MarketDataService
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
        
        # Wybierz odpowiednią funkcję sprawdzającą
        if strategy_type == StrategyType.RSI:
            result = await self._check_rsi_signal(strategy)
        elif strategy_type == StrategyType.MACD:
            result = await self._check_macd_signal(strategy)
        elif strategy_type == StrategyType.BOLLINGER:
            result = await self._check_bollinger_signal(strategy)
        elif strategy_type == StrategyType.MOVING_AVERAGE:
            result = await self._check_ma_signal(strategy)
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
    
    async def _check_rsi_signal(
        self,
        strategy: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Sprawdza sygnał RSI na podstawie prawdziwych danych
        
        Logika:
        - RSI < oversold (np. 30) → BUY
        - RSI > overbought (np. 70) → SELL
        - Inaczej → HOLD
        """
        params = strategy['parameters']
        symbol = strategy['symbol']
        timeframe = strategy['timeframe']
        
        try:
            # Pobierz prawdziwe dane i oblicz wskaźniki
            indicators = await self.market_data.get_technical_indicators(
                symbol=symbol,
                timeframe=timeframe,
                indicators_config=params
            )
            
            rsi_value = indicators.get('rsi')
            current_price = indicators.get('price', 0.0)
            
            if rsi_value is None:
                self.logger.warning(f"Nie udało się obliczyć RSI dla {symbol}")
                return {
                    "strategy_id": strategy['id'],
                    "strategy_name": strategy['name'],
                    "signal": SignalType.HOLD,
                    "message": "Brak danych do obliczenia RSI"
                }
            
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
                    'price': round(current_price, 2)
                }
                
                # Zapisz sygnał do bazy
                signal_id = self.db.create_signal({
                    'strategy_id': strategy['id'],
                    'signal_type': signal_type.value,
                    'price': current_price,
                    'indicator_values': indicator_values,
                    'message': f"RSI {signal_type.value} signal (RSI: {rsi_value:.2f})"
                })
                
                # Loguj wygenerowanie sygnału
                self.db.create_activity_log(
                    log_type='signal',
                    message=f"Wygenerowano sygnał {signal_type.value} dla {strategy['name']}",
                    symbol=strategy['symbol'],
                    strategy_name=strategy['name'],
                    details={
                        'signal_type': signal_type.value,
                        'rsi': round(rsi_value, 2),
                        'price': round(current_price, 2),
                        'oversold': oversold,
                        'overbought': overbought
                    },
                    status='success'
                )
                
                # Wyślij przez Telegram
                await self.telegram.send_signal(
                    signal_type=signal_type.value,
                    strategy_name=strategy['name'],
                    symbol=strategy['symbol'],
                    price=current_price,
                    indicator_values=indicator_values
                )
                
                self.logger.info(
                    f"Signal generated: {signal_type.value} for {strategy['name']} "
                    f"(RSI: {rsi_value:.2f}, Price: {current_price:.2f})"
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
                    "message": f"No signal (RSI: {rsi_value:.2f})",
                    "indicators": {'RSI': round(rsi_value, 2), 'price': round(current_price, 2)}
                }
                
        except Exception as e:
            self.logger.error(f"Błąd sprawdzania sygnału RSI dla {strategy['name']}: {e}", exc_info=True)
            return {
                "strategy_id": strategy['id'],
                "strategy_name": strategy['name'],
                "signal": SignalType.HOLD,
                "message": f"Błąd: {str(e)}"
            }
    
    async def _check_macd_signal(
        self,
        strategy: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Sprawdza sygnał MACD na podstawie prawdziwych danych
        
        Logika:
        - MACD przecina signal od dołu → BUY
        - MACD przecina signal od góry → SELL
        - Inaczej → HOLD
        """
        params = strategy['parameters']
        symbol = strategy['symbol']
        timeframe = strategy['timeframe']
        
        try:
            # Pobierz prawdziwe dane i oblicz wskaźniki
            indicators = await self.market_data.get_technical_indicators(
                symbol=symbol,
                timeframe=timeframe,
                indicators_config=params
            )
            
            macd_data = indicators.get('macd')
            current_price = indicators.get('price', 0.0)
            
            if macd_data is None:
                self.logger.warning(f"Nie udało się obliczyć MACD dla {symbol}")
                return {
                    "strategy_id": strategy['id'],
                    "strategy_name": strategy['name'],
                    "signal": SignalType.HOLD,
                    "message": "Brak danych do obliczenia MACD"
                }
            
            macd_value = macd_data.get('value', 0.0)
            signal_value = macd_data.get('signal', 0.0)
            histogram = macd_data.get('histogram', 0.0)
            
            # Określ sygnał na podstawie histogramu (różnica między MACD a signal)
            # Histogram > 0 i rośnie → BUY
            # Histogram < 0 i maleje → SELL
            if histogram > 0 and macd_value > signal_value:
                signal_type = SignalType.BUY
            elif histogram < 0 and macd_value < signal_value:
                signal_type = SignalType.SELL
            else:
                signal_type = SignalType.HOLD
            
            # Jeśli jest sygnał BUY lub SELL, zapisz i wyślij
            if signal_type in [SignalType.BUY, SignalType.SELL]:
                indicator_values = {
                    'MACD': round(macd_value, 2),
                    'Signal': round(signal_value, 2),
                    'Histogram': round(histogram, 2),
                    'price': round(current_price, 2)
                }
                
                signal_id = self.db.create_signal({
                    'strategy_id': strategy['id'],
                    'signal_type': signal_type.value,
                    'price': current_price,
                    'indicator_values': indicator_values,
                    'message': f"MACD {signal_type.value} signal"
                })
                
                # Loguj wygenerowanie sygnału
                self.db.create_activity_log(
                    log_type='signal',
                    message=f"Wygenerowano sygnał {signal_type.value} dla {strategy['name']}",
                    symbol=strategy['symbol'],
                    strategy_name=strategy['name'],
                    details={
                        'signal_type': signal_type.value,
                        'macd': round(macd_value, 2),
                        'signal': round(signal_value, 2),
                        'histogram': round(histogram, 2),
                        'price': round(current_price, 2)
                    },
                    status='success'
                )
                
                await self.telegram.send_signal(
                    signal_type=signal_type.value,
                    strategy_name=strategy['name'],
                    symbol=strategy['symbol'],
                    price=current_price,
                    indicator_values=indicator_values
                )
                
                self.logger.info(
                    f"Signal generated: {signal_type.value} for {strategy['name']} "
                    f"(MACD: {macd_value:.2f}, Signal: {signal_value:.2f})"
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
                    "message": f"No signal (MACD: {macd_value:.2f}, Signal: {signal_value:.2f})",
                    "indicators": {
                        'MACD': round(macd_value, 2),
                        'Signal': round(signal_value, 2),
                        'Histogram': round(histogram, 2),
                        'price': round(current_price, 2)
                    }
                }
                
        except Exception as e:
            self.logger.error(f"Błąd sprawdzania sygnału MACD dla {strategy['name']}: {e}", exc_info=True)
            return {
                "strategy_id": strategy['id'],
                "strategy_name": strategy['name'],
                "signal": SignalType.HOLD,
                "message": f"Błąd: {str(e)}"
            }
    
    async def _check_bollinger_signal(
        self,
        strategy: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Sprawdza sygnał Bollinger Bands na podstawie prawdziwych danych
        
        Logika:
        - Cena dotyka dolnej bandy → BUY (oversold)
        - Cena dotyka górnej bandy → SELL (overbought)
        - Inaczej → HOLD
        """
        params = strategy['parameters']
        symbol = strategy['symbol']
        timeframe = strategy['timeframe']
        
        try:
            # Pobierz prawdziwe dane i oblicz wskaźniki
            indicators = await self.market_data.get_technical_indicators(
                symbol=symbol,
                timeframe=timeframe,
                indicators_config=params
            )
            
            bollinger_data = indicators.get('bollinger')
            current_price = indicators.get('price', 0.0)
            
            if bollinger_data is None:
                self.logger.warning(f"Nie udało się obliczyć Bollinger Bands dla {symbol}")
                return {
                    "strategy_id": strategy['id'],
                    "strategy_name": strategy['name'],
                    "signal": SignalType.HOLD,
                    "message": "Brak danych do obliczenia Bollinger Bands"
                }
            
            upper = bollinger_data.get('upper', 0.0)
            middle = bollinger_data.get('middle', 0.0)
            lower = bollinger_data.get('lower', 0.0)
            
            # Określ sygnał na podstawie pozycji ceny względem bandów
            # Cena blisko dolnej bandy → BUY
            # Cena blisko górnej bandy → SELL
            band_width = upper - lower
            price_position = (current_price - lower) / band_width if band_width > 0 else 0.5
            
            if price_position < 0.2:  # Cena w dolnych 20% zakresu
                signal_type = SignalType.BUY
            elif price_position > 0.8:  # Cena w górnych 20% zakresu
                signal_type = SignalType.SELL
            else:
                signal_type = SignalType.HOLD
            
            # Jeśli jest sygnał BUY lub SELL, zapisz i wyślij
            if signal_type in [SignalType.BUY, SignalType.SELL]:
                indicator_values = {
                    'Upper': round(upper, 2),
                    'Middle': round(middle, 2),
                    'Lower': round(lower, 2),
                    'Price': round(current_price, 2),
                    'Position': round(price_position * 100, 2)
                }
                
                signal_id = self.db.create_signal({
                    'strategy_id': strategy['id'],
                    'signal_type': signal_type.value,
                    'price': current_price,
                    'indicator_values': indicator_values,
                    'message': f"Bollinger {signal_type.value} signal"
                })
                
                # Loguj wygenerowanie sygnału
                self.db.create_activity_log(
                    log_type='signal',
                    message=f"Wygenerowano sygnał {signal_type.value} dla {strategy['name']}",
                    symbol=strategy['symbol'],
                    strategy_name=strategy['name'],
                    details={
                        'signal_type': signal_type.value,
                        'upper': round(upper, 2),
                        'middle': round(middle, 2),
                        'lower': round(lower, 2),
                        'price': round(current_price, 2),
                        'position': round(price_position * 100, 2)
                    },
                    status='success'
                )
                
                await self.telegram.send_signal(
                    signal_type=signal_type.value,
                    strategy_name=strategy['name'],
                    symbol=strategy['symbol'],
                    price=current_price,
                    indicator_values=indicator_values
                )
                
                self.logger.info(
                    f"Signal generated: {signal_type.value} for {strategy['name']} "
                    f"(Price: {current_price:.2f}, Lower: {lower:.2f}, Upper: {upper:.2f})"
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
                    "message": f"No signal (Price: {current_price:.2f})",
                    "indicators": {
                        'Upper': round(upper, 2),
                        'Middle': round(middle, 2),
                        'Lower': round(lower, 2),
                        'Price': round(current_price, 2)
                    }
                }
                
        except Exception as e:
            self.logger.error(f"Błąd sprawdzania sygnału Bollinger dla {strategy['name']}: {e}", exc_info=True)
            return {
                "strategy_id": strategy['id'],
                "strategy_name": strategy['name'],
                "signal": SignalType.HOLD,
                "message": f"Błąd: {str(e)}"
            }
    
    async def _check_ma_signal(
        self,
        strategy: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Sprawdza sygnał Moving Average na podstawie prawdziwych danych
        
        Logika:
        - SMA_short przecina SMA_long od dołu (golden cross) → BUY
        - SMA_short przecina SMA_long od góry (death cross) → SELL
        - Inaczej → HOLD
        """
        params = strategy['parameters']
        symbol = strategy['symbol']
        timeframe = strategy['timeframe']
        
        try:
            # Pobierz prawdziwe dane i oblicz wskaźniki
            indicators = await self.market_data.get_technical_indicators(
                symbol=symbol,
                timeframe=timeframe,
                indicators_config=params
            )
            
            # Pobierz parametry użytkownika
            short_period = params.get('short_period', 50)
            long_period = params.get('long_period', 200)

            sma_short = indicators.get('sma_short')
            sma_long = indicators.get('sma_long')
            current_price = indicators.get('price', 0.0)

            if sma_short is None or sma_long is None:
                self.logger.warning(f"Nie udało się obliczyć Moving Averages dla {symbol}")
                return {
                    "strategy_id": strategy['id'],
                    "strategy_name": strategy['name'],
                    "signal": SignalType.HOLD,
                    "message": "Brak danych do obliczenia Moving Averages"
                }

            # Określ sygnał na podstawie relacji między MA
            # SMA_short > SMA_long → trend wzrostowy → BUY
            # SMA_short < SMA_long → trend spadkowy → SELL
            if sma_short > sma_long:
                signal_type = SignalType.BUY
            elif sma_short < sma_long:
                signal_type = SignalType.SELL
            else:
                signal_type = SignalType.HOLD

            # Jeśli jest sygnał BUY lub SELL, zapisz i wyślij
            if signal_type in [SignalType.BUY, SignalType.SELL]:
                indicator_values = {
                    f'SMA_{short_period}': round(sma_short, 2),
                    f'SMA_{long_period}': round(sma_long, 2),
                    'Price': round(current_price, 2),
                    'Difference': round(((sma_short - sma_long) / sma_long * 100), 2)
                }
                
                signal_id = self.db.create_signal({
                    'strategy_id': strategy['id'],
                    'signal_type': signal_type.value,
                    'price': current_price,
                    'indicator_values': indicator_values,
                    'message': f"MA {signal_type.value} signal (Golden Cross)" if signal_type == SignalType.BUY else f"MA {signal_type.value} signal (Death Cross)"
                })
                
                # Loguj wygenerowanie sygnału
                self.db.create_activity_log(
                    log_type='signal',
                    message=f"Wygenerowano sygnał {signal_type.value} dla {strategy['name']}",
                    symbol=strategy['symbol'],
                    strategy_name=strategy['name'],
                    details={
                        'signal_type': signal_type.value,
                        f'sma_{short_period}': round(sma_short, 2),
                        f'sma_{long_period}': round(sma_long, 2),
                        'price': round(current_price, 2),
                        'difference': round(((sma_short - sma_long) / sma_long * 100), 2)
                    },
                    status='success'
                )

                await self.telegram.send_signal(
                    signal_type=signal_type.value,
                    strategy_name=strategy['name'],
                    symbol=strategy['symbol'],
                    price=current_price,
                    indicator_values=indicator_values
                )

                self.logger.info(
                    f"Signal generated: {signal_type.value} for {strategy['name']} "
                    f"(SMA_{short_period}: {sma_short:.2f}, SMA_{long_period}: {sma_long:.2f})"
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
                    "message": f"No signal (SMA_{short_period}: {sma_short:.2f}, SMA_{long_period}: {sma_long:.2f})",
                    "indicators": {
                        f'SMA_{short_period}': round(sma_short, 2),
                        f'SMA_{long_period}': round(sma_long, 2),
                        'Price': round(current_price, 2)
                    }
                }

        except Exception as e:
            self.logger.error(f"Błąd sprawdzania sygnału MA dla {strategy['name']}: {e}", exc_info=True)
            return {
                "strategy_id": strategy['id'],
                "strategy_name": strategy['name'],
                "signal": SignalType.HOLD,
                "message": f"Błąd: {str(e)}"
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
