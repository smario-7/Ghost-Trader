"""
Market Data Service - pobieranie prawdziwych danych o notowaniach
"""
import yfinance as yf
import pandas as pd
import numpy as np
import logging
import time
import random
import requests
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta


class MarketDataService:
    """
    Serwis pobierający prawdziwe dane o notowaniach z Yahoo Finance
    """
    
    def __init__(self, database=None):
        """
        Inicjalizacja serwisu
        
        Args:
            database: Instancja bazy danych (opcjonalne, do logowania aktywności)
        """
        self.logger = logging.getLogger("trading_bot.market_data")
        self.database = database
        self.use_mock_data = False  # Flaga czy używać danych testowych
        
        # Konfiguracja User-Agent dla Yahoo Finance
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    
    def _setup_ticker_session(self, ticker):
        """
        Konfiguruje sesję dla tickera z odpowiednimi headerami
        
        Args:
            ticker: Obiekt yfinance.Ticker
        """
        try:
            if hasattr(ticker, 'session'):
                ticker.session.headers.update(self.headers)
        except Exception as e:
            self.logger.warning(f"Nie udało się ustawić headers: {e}")
    
    def _retry_with_backoff(self, func, max_retries=3, initial_delay=1):
        """
        Wykonuje funkcję z exponential backoff retry
        
        Args:
            func: Funkcja do wykonania
            max_retries: Maksymalna liczba prób
            initial_delay: Początkowe opóźnienie w sekundach
            
        Returns:
            Wynik funkcji lub None
        """
        for attempt in range(max_retries):
            try:
                result = func()
                if result is not None and (not isinstance(result, pd.DataFrame) or not result.empty):
                    return result
            except Exception as e:
                self.logger.warning(f"Próba {attempt + 1}/{max_retries} nie powiodła się: {e}")
            
            if attempt < max_retries - 1:
                delay = initial_delay * (2 ** attempt) + random.uniform(0, 1)
                self.logger.info(f"Ponowna próba za {delay:.1f}s...")
                time.sleep(delay)
        
        return None
    
    def _generate_mock_data(self, symbol: str, timeframe: str, period: str) -> pd.DataFrame:
        """
        Generuje dane testowe gdy Yahoo Finance nie działa
        
        Args:
            symbol: Symbol
            timeframe: Timeframe
            period: Okres
            
        Returns:
            DataFrame z danymi testowymi
        """
        self.logger.warning(f"⚠️  UŻYWAM DANYCH TESTOWYCH dla {symbol} - Yahoo Finance nie działa!")
        
        # Mapowanie okresu na liczbę dni
        period_days = {
            '1d': 1, '5d': 5, '1mo': 30, '3mo': 90,
            '6mo': 180, '1y': 365, '2y': 730, '5y': 1825
        }
        days = period_days.get(period, 30)
        
        # Mapowanie timeframe na interwał
        interval_hours = {
            '1m': 1/60, '5m': 5/60, '15m': 15/60, '30m': 30/60,
            '1h': 1, '4h': 4, '1d': 24, '1w': 168
        }
        hours = interval_hours.get(timeframe, 24)
        
        # Liczba punktów danych
        num_points = int((days * 24) / hours)
        num_points = min(num_points, 1000)  # Limit
        
        # Generuj realistyczne dane
        base_price = 100.0
        if 'EUR' in symbol or 'GBP' in symbol:
            base_price = 1.1
        elif 'JPY' in symbol:
            base_price = 150.0
        elif 'AAPL' in symbol or 'MSFT' in symbol:
            base_price = 180.0
        elif 'SPX' in symbol or 'DJI' in symbol:
            base_price = 4500.0
        
        dates = pd.date_range(end=datetime.now(), periods=num_points, freq=f'{int(hours)}H')
        
        # Generuj cenę z realistic volatility
        volatility = 0.02  # 2% volatility
        returns = np.random.normal(0, volatility, num_points)
        prices = base_price * np.exp(np.cumsum(returns))
        
        # Twórz OHLCV
        data = pd.DataFrame(index=dates)
        data['Close'] = prices
        data['Open'] = prices * (1 + np.random.uniform(-0.005, 0.005, num_points))
        data['High'] = np.maximum(data['Open'], data['Close']) * (1 + np.random.uniform(0, 0.01, num_points))
        data['Low'] = np.minimum(data['Open'], data['Close']) * (1 - np.random.uniform(0, 0.01, num_points))
        data['Volume'] = np.random.randint(1000000, 10000000, num_points)
        
        return data
    
    def _convert_symbol(self, symbol: str) -> str:
        """
        Konwertuje symbol z formatu EUR/USD na format dla Yahoo Finance
        
        Args:
            symbol: Symbol w formacie EUR/USD, USD/JPY, SPX/USD, itp.
        
        Returns:
            Symbol w formacie dla Yahoo Finance
        """
        self.logger.info(f"🔍 Konwersja symbolu: {symbol}")
        
        if '/' in symbol:
            base, quote = symbol.split('/')
            self.logger.info(f"🔍  base={base}, quote={quote}")
            
            # Forex - pary gdzie USD jest bazową walutą (USD/JPY, USD/CHF, itp.)
            # TO MUSI BYĆ PIERWSZE, bo USD/JPY ma base='USD'
            if base == 'USD':
                # Dla USD/JPY -> JPY=X, USD/CHF -> CHF=X, itp.
                usd_forex_symbols = {
                    'JPY': 'JPY=X',
                    'CHF': 'CHF=X',
                    'CAD': 'CAD=X',
                    'EUR': 'EURUSD=X',  # USD/EUR nie istnieje, używamy odwrotnej pary
                    'GBP': 'GBPUSD=X',  # USD/GBP nie istnieje, używamy odwrotnej pary
                    'AUD': 'AUDUSD=X',  # USD/AUD nie istnieje, używamy odwrotnej pary
                    'NZD': 'NZDUSD=X',  # USD/NZD nie istnieje, używamy odwrotnej pary
                }
                result = usd_forex_symbols.get(quote, f'{quote}=X')
                self.logger.info(f"🔍  USD jako base -> {result}")
                return result
            
            # Forex - pary gdzie USD jest kwotowaną walutą (EUR/USD, GBP/USD, itp.)
            if quote == 'USD':
                # Dla Forex: EURUSD=X
                forex_symbols = {
                    'EUR': 'EURUSD=X',
                    'GBP': 'GBPUSD=X',
                    'JPY': 'JPY=X',  # To jest USD/JPY w Yahoo Finance
                    'CHF': 'CHF=X',  # To jest USD/CHF w Yahoo Finance
                    'AUD': 'AUDUSD=X',
                    'NZD': 'NZDUSD=X',
                    'CAD': 'CAD=X',  # To jest USD/CAD w Yahoo Finance
                }
                result = forex_symbols.get(base, f'{base}{quote}=X')
                self.logger.info(f"🔍  USD jako quote -> {result}")
                return result
            
            # Metale szlachetne
            if base in ['XAU', 'XAG', 'XPT', 'XPD']:
                metal_symbols = {
                    'XAU': 'GC=F',  # Gold futures
                    'XAG': 'SI=F',  # Silver futures
                    'XPT': 'PL=F',  # Platinum futures
                    'XPD': 'PA=F',  # Palladium futures
                }
                return metal_symbols.get(base, f'{base}-USD')
            
            # Indeksy USA
            if base in ['SPX', 'DJI', 'IXIC', 'RUT']:
                index_symbols = {
                    'SPX': '^GSPC',  # S&P 500
                    'DJI': '^DJI',   # Dow Jones
                    'IXIC': '^IXIC', # NASDAQ
                    'RUT': '^RUT',   # Russell 2000
                }
                return index_symbols.get(base, symbol)
            
            # Akcje USA - format: AAPL/USD -> AAPL
            if quote == 'USD' and len(base) <= 5:
                return base
        
        return symbol
    
    def _convert_timeframe(self, timeframe: str, symbol: str = None) -> str:
        """
        Konwertuje timeframe z formatu 1m, 1h, 1d na format Yahoo Finance
        
        Args:
            timeframe: Timeframe w formacie 1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w
            symbol: Symbol (opcjonalne, do sprawdzenia czy to Forex)
        
        Returns:
            Interval dla Yahoo Finance
        """
        timeframe_map = {
            '1m': '1m',
            '5m': '5m',
            '15m': '15m',
            '30m': '30m',
            '1h': '1h',
            '4h': '4h',
            '1d': '1d',
            '1w': '1wk',
        }
        
        interval = timeframe_map.get(timeframe, '1d')
        
        # Dla par Forex, Yahoo Finance może nie zwracać danych dla bardzo krótkich interwałów
        # Jeśli symbol wygląda jak para Forex i timeframe jest bardzo krótki, użyj dłuższego
        if symbol and '/' in symbol:
            base, quote = symbol.split('/')
            # Sprawdź czy to para Forex (nie akcja ani indeks)
            forex_pairs = ['EUR', 'GBP', 'JPY', 'CHF', 'AUD', 'NZD', 'CAD', 'USD']
            if base in forex_pairs or quote in forex_pairs:
                # Dla Forex, minimalny interval to zwykle 1h lub 1d
                if timeframe in ['1m', '5m']:
                    self.logger.warning(f"Forex {symbol} może nie mieć danych dla {timeframe}, używam 1h")
                    return '1h'
                elif timeframe == '15m':
                    self.logger.info(f"Forex {symbol} dla {timeframe}, próbuję 1h jeśli 15m nie zadziała")
                    return '15m'
        
        return interval
    
    async def get_historical_data(
        self,
        symbol: str,
        timeframe: str = '1d',
        period: str = '1mo'
    ) -> Optional[pd.DataFrame]:
        """
        Pobiera historyczne dane o notowaniach
        
        Args:
            symbol: Symbol (np. EUR/USD, AAPL/USD)
            timeframe: Timeframe (1m, 5m, 1h, 1d, itp.)
            period: Okres danych (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
        
        Returns:
            DataFrame z danymi OHLCV lub None w przypadku błędu
        """
        try:
            yf_symbol = self._convert_symbol(symbol)
            interval = self._convert_timeframe(timeframe, symbol)
            
            # Szczegółowe logowanie konwersji
            self.logger.info(f"🔍 Konwersja symbolu: {symbol} -> {yf_symbol}")
            self.logger.info(f"🔍 Konwersja timeframe: {timeframe} -> {interval}")
            self.logger.info(f"Pobieranie danych dla {symbol} -> {yf_symbol} ({timeframe} -> {interval})")
            
            # Loguj rozpoczęcie pobierania danych
            if self.database:
                self.database.create_activity_log(
                    log_type='market_data',
                    message=f"Pobieranie danych dla {symbol}",
                    symbol=symbol,
                    details={
                        'yf_symbol': yf_symbol,
                        'timeframe': timeframe,
                        'interval': interval,
                        'period': period
                    },
                    status='success'
                )
            
            ticker = yf.Ticker(yf_symbol)
            
            # Ustaw headers dla tickera
            self._setup_ticker_session(ticker)
            
            # Użyj retry logic do pobierania danych
            def fetch_data():
                try:
                    return ticker.history(period=period, interval=interval)
                except Exception as e:
                    self.logger.debug(f"Błąd w fetch_data: {e}")
                    return None
            
            data = self._retry_with_backoff(fetch_data, max_retries=3)
            
            # Jeśli nadal brak danych, spróbuj alternatywnych okresów
            if data is None or data.empty:
                self.logger.warning(f"Brak danych dla {symbol} z periodem {period}, próbuję alternatywnych...")
                
                alternative_periods = []
                if period == '1d':
                    alternative_periods = ['5d', '1mo']
                elif period == '5d':
                    alternative_periods = ['1mo', '3mo']
                else:
                    alternative_periods = ['3mo', '1y']
                
                for alt_period in alternative_periods:
                    try:
                        def fetch_alt():
                            return ticker.history(period=alt_period, interval=interval)
                        
                        data = self._retry_with_backoff(fetch_alt, max_retries=2)
                        if data is not None and not data.empty:
                            self.logger.info(f"✅ Udało się pobrać dane z alternatywnym okresem {alt_period} dla {symbol}")
                            break
                    except Exception as e2:
                        self.logger.error(f"Błąd przy alternatywnym pobieraniu danych dla {symbol}: {e2}")
                        data = pd.DataFrame()
            
            if data.empty:
                self.logger.warning(f"Brak danych dla {symbol} ({yf_symbol}) - period: {period}, interval: {interval}")
                # Spróbuj alternatywnego symbolu dla Forex
                if yf_symbol.endswith('=X') and '/' in symbol:
                    base, quote = symbol.split('/')
                    if base in ['AUD', 'EUR', 'GBP', 'JPY', 'CHF', 'NZD', 'CAD']:
                        # Dla niektórych par Forex, Yahoo Finance może wymagać innego formatu
                        alt_symbol = f"{base}{quote}" if quote != 'USD' else f"{base}USD"
                        self.logger.info(f"Próba alternatywnego symbolu: {alt_symbol}")
                        try:
                            alt_ticker = yf.Ticker(alt_symbol)
                            data = alt_ticker.history(period=period, interval=interval)
                            if not data.empty:
                                self.logger.info(f"Udało się pobrać dane z alternatywnego symbolu {alt_symbol}")
                        except Exception as e:
                            self.logger.warning(f"Alternatywny symbol {alt_symbol} też nie zadziałał: {e}")
                
                if data.empty:
                    # Ostateczność - użyj danych testowych
                    self.logger.warning(f"Wszystkie źródła danych zawiodły dla {symbol}, używam danych testowych")
                    data = self._generate_mock_data(symbol, timeframe, period)
                    self.use_mock_data = True
                    
                    if self.database:
                        self.database.create_activity_log(
                            log_type='market_data',
                            message=f"Używam danych testowych dla {symbol} - Yahoo Finance nie działa",
                            symbol=symbol,
                            details={'yf_symbol': yf_symbol, 'timeframe': timeframe, 'period': period, 'interval': interval, 'mock_data': True},
                            status='warning'
                        )
            
            # Walidacja danych - usuń wiersze z nieprawidłowymi cenami
            if data is not None and not data.empty and 'Close' in data.columns:
                invalid_mask = (data['Close'] <= 0) | data['Close'].isna()
                if invalid_mask.any():
                    self.logger.warning(f"Usunięto {invalid_mask.sum()} nieprawidłowych wierszy dla {symbol}")
                    data = data[~invalid_mask]
                if data.empty:
                    if self.database:
                        self.database.create_activity_log(
                            log_type='market_data',
                            message=f"Wszystkie dane dla {symbol} są nieprawidłowe",
                            symbol=symbol,
                            details={'yf_symbol': yf_symbol},
                            status='warning'
                        )
                    return None

            # Loguj sukces pobierania danych
            if self.database:
                self.database.create_activity_log(
                    log_type='market_data',
                    message=f"Dane pobrane pomyślnie dla {symbol}",
                    symbol=symbol,
                    details={
                        'yf_symbol': yf_symbol,
                        'timeframe': timeframe,
                        'data_points': len(data),
                        'period': period
                    },
                    status='success'
                )

            return data
            
        except Exception as e:
            self.logger.error(f"Błąd pobierania danych dla {symbol}: {e}")
            if self.database:
                self.database.create_activity_log(
                    log_type='market_data',
                    message=f"Błąd pobierania danych dla {symbol}: {str(e)}",
                    symbol=symbol,
                    details={'error': str(e)},
                    status='error'
                )
            return None
    
    async def get_current_price(self, symbol: str) -> Optional[float]:
        """
        Pobiera aktualną cenę
        
        Args:
            symbol: Symbol (np. EUR/USD, AAPL/USD)
        
        Returns:
            Aktualna cena lub None w przypadku błędu
        """
        try:
            yf_symbol = self._convert_symbol(symbol)
            ticker = yf.Ticker(yf_symbol)
            info = ticker.info
            
            # Dla różnych typów instrumentów, cena może być w różnych polach
            price = info.get('regularMarketPrice') or info.get('currentPrice') or info.get('previousClose')
            
            if price:
                return float(price)
            
            # Jeśli nie ma w info, spróbuj z ostatniej sesji
            data = await self.get_historical_data(symbol, '1d', '1d')
            if data is not None and not data.empty:
                return float(data['Close'].iloc[-1])
            
            return None
            
        except Exception as e:
            self.logger.error(f"Błąd pobierania ceny dla {symbol}: {e}")
            return None
    
    def calculate_rsi(self, data: pd.DataFrame, period: int = 14) -> Optional[float]:
        """
        Oblicza RSI (Relative Strength Index)
        
        Args:
            data: DataFrame z danymi OHLCV
            period: Okres RSI (domyślnie 14)
        
        Returns:
            Wartość RSI lub None
        """
        try:
            if data.empty or len(data) < period + 1:
                return None
            
            close = data['Close']
            delta = close.diff()

            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

            gain_value = gain.iloc[-1]
            loss_value = loss.iloc[-1]

            if pd.isna(loss_value) or pd.isna(gain_value):
                return None

            # Zabezpieczenie przed dzieleniem przez zero
            if loss_value == 0:
                return 100.0 if gain_value > 0 else 50.0
            if gain_value == 0:
                return 0.0

            rs = gain_value / loss_value
            rsi = 100 - (100 / (1 + rs))
            return float(rsi) if not pd.isna(rsi) else None
            
        except Exception as e:
            self.logger.error(f"Błąd obliczania RSI: {e}")
            return None
    
    def calculate_macd(
        self,
        data: pd.DataFrame,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9
    ) -> Optional[Dict[str, float]]:
        """
        Oblicza MACD (Moving Average Convergence Divergence)
        
        Args:
            data: DataFrame z danymi OHLCV
            fast_period: Okres szybkiej EMA (domyślnie 12)
            slow_period: Okres wolnej EMA (domyślnie 26)
            signal_period: Okres sygnału EMA (domyślnie 9)
        
        Returns:
            Słownik z wartościami MACD, signal, histogram lub None
        """
        try:
            if data.empty or len(data) < slow_period + signal_period:
                return None
            
            close = data['Close']
            
            ema_fast = close.ewm(span=fast_period, adjust=False).mean()
            ema_slow = close.ewm(span=slow_period, adjust=False).mean()
            
            macd_line = ema_fast - ema_slow
            signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
            histogram = macd_line - signal_line
            
            return {
                'value': float(macd_line.iloc[-1]) if not pd.isna(macd_line.iloc[-1]) else 0.0,
                'signal': float(signal_line.iloc[-1]) if not pd.isna(signal_line.iloc[-1]) else 0.0,
                'histogram': float(histogram.iloc[-1]) if not pd.isna(histogram.iloc[-1]) else 0.0
            }
            
        except Exception as e:
            self.logger.error(f"Błąd obliczania MACD: {e}")
            return None
    
    def calculate_bollinger_bands(
        self,
        data: pd.DataFrame,
        period: int = 20,
        std_dev: float = 2.0
    ) -> Optional[Dict[str, float]]:
        """
        Oblicza Bollinger Bands
        
        Args:
            data: DataFrame z danymi OHLCV
            period: Okres średniej (domyślnie 20)
            std_dev: Odchylenie standardowe (domyślnie 2.0)
        
        Returns:
            Słownik z wartościami upper, middle, lower lub None
        """
        try:
            if data.empty or len(data) < period:
                return None
            
            close = data['Close']
            sma = close.rolling(window=period).mean()
            std = close.rolling(window=period).std()
            
            upper = sma + (std * std_dev)
            middle = sma
            lower = sma - (std * std_dev)
            
            return {
                'upper': float(upper.iloc[-1]) if not pd.isna(upper.iloc[-1]) else 0.0,
                'middle': float(middle.iloc[-1]) if not pd.isna(middle.iloc[-1]) else 0.0,
                'lower': float(lower.iloc[-1]) if not pd.isna(lower.iloc[-1]) else 0.0
            }
            
        except Exception as e:
            self.logger.error(f"Błąd obliczania Bollinger Bands: {e}")
            return None
    
    def calculate_moving_averages(
        self,
        data: pd.DataFrame,
        short_period: int = 50,
        long_period: int = 200
    ) -> Optional[Dict[str, float]]:
        """
        Oblicza Moving Averages (SMA)
        
        Args:
            data: DataFrame z danymi OHLCV
            short_period: Okres krótkiej MA (domyślnie 50)
            long_period: Okres długiej MA (domyślnie 200)
        
        Returns:
            Słownik z wartościami SMA_short, SMA_long lub None
        """
        try:
            if data.empty or len(data) < long_period:
                return None
            
            close = data['Close']
            
            sma_short = close.rolling(window=short_period).mean()
            sma_long = close.rolling(window=long_period).mean()
            
            return {
                'sma_short': float(sma_short.iloc[-1]) if not pd.isna(sma_short.iloc[-1]) else 0.0,
                'sma_long': float(sma_long.iloc[-1]) if not pd.isna(sma_long.iloc[-1]) else 0.0
            }
            
        except Exception as e:
            self.logger.error(f"Błąd obliczania Moving Averages: {e}")
            return None
    
    async def get_technical_indicators(
        self,
        symbol: str,
        timeframe: str,
        indicators_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Pobiera dane i oblicza wszystkie wskaźniki techniczne
        
        Args:
            symbol: Symbol (np. EUR/USD, AAPL/USD)
            timeframe: Timeframe (1m, 5m, 1h, 1d, itp.)
            indicators_config: Konfiguracja wskaźników z parametrami strategii
        
        Returns:
            Słownik z wszystkimi wskaźnikami i ceną
        """
        # Określ okres danych na podstawie timeframe
        period_map = {
            '1m': '5d',
            '5m': '5d',
            '15m': '1mo',
            '30m': '1mo',
            '1h': '3mo',
            '4h': '6mo',
            '1d': '1y',
            '1w': '2y',
        }
        period = period_map.get(timeframe, '1y')
        
        data = await self.get_historical_data(symbol, timeframe, period)
        
        if data is None or data.empty:
            self.logger.warning(f"Brak danych dla {symbol}, używam wartości domyślnych")
            return {
                'price': 0.0,
                'rsi': 50.0,
                'macd': {'value': 0.0, 'signal': 0.0, 'histogram': 0.0},
                'bollinger': {'upper': 0.0, 'middle': 0.0, 'lower': 0.0},
                'sma_50': 0.0,
                'sma_200': 0.0,
            }
        
        current_price = float(data['Close'].iloc[-1])
        
        result = {
            'price': current_price,
        }
        
        # RSI
        if 'period' in indicators_config:
            rsi_period = indicators_config.get('period', 14)
            rsi = self.calculate_rsi(data, rsi_period)
            if rsi is not None:
                result['rsi'] = rsi
        
        # MACD
        if 'fast_period' in indicators_config:
            macd = self.calculate_macd(
                data,
                fast_period=indicators_config.get('fast_period', 12),
                slow_period=indicators_config.get('slow_period', 26),
                signal_period=indicators_config.get('signal_period', 9)
            )
            if macd:
                result['macd'] = macd
        
        # Bollinger Bands
        if 'period' in indicators_config and 'std_dev' in indicators_config:
            bb = self.calculate_bollinger_bands(
                data,
                period=indicators_config.get('period', 20),
                std_dev=indicators_config.get('std_dev', 2.0)
            )
            if bb:
                result['bollinger'] = bb
        
        # Moving Averages
        if 'short_period' in indicators_config:
            ma = self.calculate_moving_averages(
                data,
                short_period=indicators_config.get('short_period', 50),
                long_period=indicators_config.get('long_period', 200)
            )
            if ma:
                result['sma_short'] = ma['sma_short']
                result['sma_long'] = ma['sma_long']
        
        return result
