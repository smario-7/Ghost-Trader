"""
Router dla endpointów danych wykresów i danych makro
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from slowapi import Limiter
from slowapi.util import get_remote_address
from typing import Dict, Any

from .dependencies import verify_api_key, get_data_collection_service, settings
from ..utils.logger import setup_logger

limiter = Limiter(key_func=get_remote_address)
logger = setup_logger(name="trading_bot", log_file=settings.log_file, level=settings.log_level)

router = APIRouter(tags=["Chart Data"])


@router.get("/chart-data", dependencies=[Depends(verify_api_key)])
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def get_chart_data(
    request: Request,
    symbol: str = Query(..., description="Symbol (np. EUR/USD, AAPL/USD)"),
    timeframe: str = Query("1h", description="Timeframe (1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w)"),
    period: str = Query("1mo", description="Okres danych (1d, 5d, 1mo, 3mo, 6mo, 1y)")
) -> Dict[str, Any]:
    """
    Pobiera dane OHLCV oraz wskaźniki techniczne dla wykresów
    """
    try:
        from ..services.market_data_service import MarketDataService
        
        logger.info(f"Fetching chart data: {symbol} ({timeframe}, {period})")
        
        valid_timeframes = ['1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w']
        if timeframe not in valid_timeframes:
            raise HTTPException(
                status_code=400,
                detail=f"Nieprawidłowy timeframe. Dozwolone: {', '.join(valid_timeframes)}"
            )
        
        valid_periods = ['1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y']
        if period not in valid_periods:
            raise HTTPException(
                status_code=400,
                detail=f"Nieprawidłowy period. Dozwolone: {', '.join(valid_periods)}"
            )
        
        market_service = MarketDataService()
        
        data = await market_service.get_historical_data(
            symbol=symbol,
            timeframe=timeframe,
            period=period
        )
        
        if data is None or data.empty:
            logger.warning(f"No data available for {symbol}")
            raise HTTPException(
                status_code=404,
                detail=f"Brak danych dla symbolu {symbol}. Sprawdź czy symbol jest prawidłowy."
            )
        
        logger.info(f"Retrieved {len(data)} candles for {symbol}")
        
        candles = []
        for index, row in data.iterrows():
            timestamp = int(index.timestamp())
            
            candles.append({
                "time": timestamp,
                "open": float(row['Open']),
                "high": float(row['High']),
                "low": float(row['Low']),
                "close": float(row['Close'])
            })
        
        indicators = {
            "rsi": [],
            "macd": {
                "macd_line": [],
                "signal_line": [],
                "histogram": []
            },
            "bollinger": {
                "upper": [],
                "middle": [],
                "lower": []
            },
            "sma50": [],
            "sma200": []
        }
        
        try:
            for i in range(14, len(data)):
                subset = data.iloc[max(0, i-14):i+1]
                rsi_value = market_service.calculate_rsi(subset, period=14)
                
                if rsi_value is not None:
                    timestamp = int(data.index[i].timestamp())
                    indicators["rsi"].append({
                        "time": timestamp,
                        "value": float(rsi_value)
                    })
        except Exception as e:
            logger.warning(f"Error calculating RSI: {e}")
        
        try:
            for i in range(35, len(data)):
                subset = data.iloc[:i+1]
                macd_data = market_service.calculate_macd(
                    subset,
                    fast_period=12,
                    slow_period=26,
                    signal_period=9
                )
                
                if macd_data:
                    timestamp = int(data.index[i].timestamp())
                    indicators["macd"]["macd_line"].append({
                        "time": timestamp,
                        "value": float(macd_data['value'])
                    })
                    indicators["macd"]["signal_line"].append({
                        "time": timestamp,
                        "value": float(macd_data['signal'])
                    })
                    indicators["macd"]["histogram"].append({
                        "time": timestamp,
                        "value": float(macd_data['histogram'])
                    })
        except Exception as e:
            logger.warning(f"Error calculating MACD: {e}")
        
        try:
            for i in range(20, len(data)):
                subset = data.iloc[max(0, i-20):i+1]
                bb_data = market_service.calculate_bollinger_bands(
                    subset,
                    period=20,
                    std_dev=2.0
                )
                
                if bb_data:
                    timestamp = int(data.index[i].timestamp())
                    indicators["bollinger"]["upper"].append({
                        "time": timestamp,
                        "value": float(bb_data['upper'])
                    })
                    indicators["bollinger"]["middle"].append({
                        "time": timestamp,
                        "value": float(bb_data['middle'])
                    })
                    indicators["bollinger"]["lower"].append({
                        "time": timestamp,
                        "value": float(bb_data['lower'])
                    })
        except Exception as e:
            logger.warning(f"Error calculating Bollinger Bands: {e}")
        
        try:
            for i in range(50, len(data)):
                subset = data.iloc[max(0, i-50):i+1]
                close_prices = subset['Close']
                sma50_value = float(close_prices.mean())
                
                timestamp = int(data.index[i].timestamp())
                indicators["sma50"].append({
                    "time": timestamp,
                    "value": sma50_value
                })
            
            for i in range(200, len(data)):
                subset = data.iloc[max(0, i-200):i+1]
                close_prices = subset['Close']
                sma200_value = float(close_prices.mean())
                
                timestamp = int(data.index[i].timestamp())
                indicators["sma200"].append({
                    "time": timestamp,
                    "value": sma200_value
                })
        except Exception as e:
            logger.warning(f"Error calculating Moving Averages: {e}")
        
        current_price = float(data['Close'].iloc[-1])
        
        result = {
            "symbol": symbol,
            "timeframe": timeframe,
            "period": period,
            "candles": candles,
            "indicators": indicators,
            "current_price": current_price,
            "data_points": len(candles)
        }
        
        logger.info(f"Chart data prepared: {len(candles)} candles, {len(indicators['rsi'])} RSI points")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching chart data for {symbol}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Błąd pobierania danych wykresu: {str(e)}"
        )


@router.get("/macro-data", dependencies=[Depends(verify_api_key)])
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def get_macro_data(
    request: Request,
    data_service=Depends(get_data_collection_service)
) -> Dict[str, Any]:
    """Pobiera dane makroekonomiczne (Fed, inflacja, PKB, zatrudnienie)"""
    try:
        macro_data = await data_service.get_all_macro_data()
        return macro_data
    except Exception as e:
        logger.error(f"Error getting macro data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
