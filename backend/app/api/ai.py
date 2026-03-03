"""
Router dla endpointów AI
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from slowapi import Limiter
from slowapi.util import get_remote_address
import json
import re
import asyncio
import time
from datetime import datetime
from typing import Optional, Dict, Any

from .dependencies import verify_api_key, get_database, get_telegram_service, get_signal_aggregator, settings
from ..config import get_polish_time
from ..utils.logger import setup_logger

limiter = Limiter(key_func=get_remote_address)
logger = setup_logger(name="trading_bot", log_file=settings.log_file, level=settings.log_level)

router = APIRouter(prefix="/ai", tags=["AI Analysis"])


@router.post("/analyze", dependencies=[Depends(verify_api_key)])
@limiter.limit("60/hour")
async def ai_analyze(
    request: Request,
    symbol: str,
    timeframe: str = "1h",
    db=Depends(get_database),
    telegram=Depends(get_telegram_service),
    aggregator=Depends(get_signal_aggregator)
) -> Dict[str, Any]:
    """Kompleksowa analiza AI z agregacją sygnałów"""
    try:
        from ..services.ai_strategy import AIStrategy
        
        logger.info(f"Starting comprehensive AI analysis for {symbol} ({timeframe})")
        
        ai_strategy = AIStrategy(telegram_service=telegram, database=db)
        
        analysis = await ai_strategy.comprehensive_analysis(
            symbol=symbol,
            timeframe=timeframe
        )
        
        aggregated = await aggregator.aggregate_signals(
            symbol=symbol,
            timeframe=timeframe,
            ai_result=analysis["ai_analysis"],
            technical_result=analysis["technical_analysis"],
            macro_result=analysis["macro_analysis"],
            news_result=analysis["news_analysis"]
        )
        
        analysis_id = db.create_ai_analysis_result({
            "symbol": symbol,
            "timeframe": timeframe,
            "ai_recommendation": analysis["ai_analysis"]["recommendation"],
            "ai_confidence": analysis["ai_analysis"]["confidence"],
            "ai_reasoning": analysis["ai_analysis"]["reasoning"],
            "technical_signal": analysis["technical_analysis"]["signal"],
            "technical_confidence": analysis["technical_analysis"]["confidence"],
            "technical_details": json.dumps(analysis["technical_analysis"]["indicators"]),
            "macro_signal": analysis["macro_analysis"]["signal"],
            "macro_impact": analysis["macro_analysis"]["impact"],
            "news_sentiment": analysis["news_analysis"]["sentiment"],
            "news_score": analysis["news_analysis"]["score"],
            "final_signal": aggregated["final_signal"],
            "agreement_score": aggregated["agreement_score"],
            "voting_details": json.dumps(aggregated["voting_details"]),
            "decision_reason": aggregated["decision_reason"],
            "tokens_used": analysis["ai_analysis"]["tokens_used"],
            "estimated_cost": analysis["ai_analysis"]["estimated_cost"]
        })
        
        logger.info(f"AI analysis completed for {symbol}: {aggregated['final_signal']} ({aggregated['agreement_score']}%)")
        
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "timestamp": analysis["timestamp"],
            "analysis": {
                "ai": analysis["ai_analysis"],
                "technical": analysis["technical_analysis"],
                "macro": analysis["macro_analysis"],
                "news": analysis["news_analysis"]
            },
            "aggregated": aggregated,
            "tokens_used": analysis["ai_analysis"]["tokens_used"],
            "estimated_cost": analysis["ai_analysis"]["estimated_cost"],
            "analysis_id": analysis_id
        }
        
    except Exception as e:
        logger.error(f"Error in AI analysis: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market-overview/{symbol}", dependencies=[Depends(verify_api_key)])
@limiter.limit("60/hour")
async def ai_market_overview(
    request: Request,
    symbol: str,
    db=Depends(get_database),
    telegram=Depends(get_telegram_service)
) -> Dict[str, Any]:
    """Pełny przegląd rynku dla symbolu"""
    try:
        from ..services.ai_strategy import AIStrategy
        
        logger.info(f"Generating market overview for {symbol}")
        
        ai_strategy = AIStrategy(telegram_service=telegram, database=db)
        
        analysis = await ai_strategy.comprehensive_analysis(
            symbol=symbol,
            timeframe="1h"
        )
        
        last_analysis = None
        try:
            results = db.get_ai_analysis_results(symbol=symbol, limit=1)
            if results:
                last_analysis = {
                    "id": results[0].get("id"),
                    "timestamp": results[0].get("timestamp"),
                    "final_signal": results[0].get("final_signal"),
                    "agreement_score": results[0].get("agreement_score")
                }
        except:
            pass
        
        logger.info(f"Market overview generated for {symbol}")
        
        return {
            "symbol": symbol,
            "timestamp": analysis["timestamp"],
            "comprehensive_analysis": {
                "ai": analysis["ai_analysis"],
                "technical": analysis["technical_analysis"],
                "macro": analysis["macro_analysis"],
                "news": analysis["news_analysis"]
            },
            "last_saved_analysis": last_analysis
        }
        
    except Exception as e:
        logger.error(f"Error generating market overview: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sentiment", dependencies=[Depends(verify_api_key)])
@limiter.limit("60/hour")
async def ai_sentiment(
    request: Request,
    symbol: str,
    hours_back: int = 24
) -> Dict[str, Any]:
    """Analiza sentymentu z wiadomości dla symbolu"""
    try:
        from ..services.ai_analysis_service import AIAnalysisService
        from ..services.data_collection_service import NewsService
        
        ai_service = AIAnalysisService()
        news_service = NewsService()
        
        news = await news_service.get_financial_news(
            symbol=symbol.split('/')[0],
            hours_back=hours_back,
            limit=20
        )
        
        sentiment = await ai_service.get_sentiment_analysis(symbol, news)
        
        return {
            "symbol": symbol,
            "hours_analyzed": hours_back,
            "news_count": len(news),
            "sentiment": sentiment
        }
        
    except Exception as e:
        logger.error(f"Error in sentiment analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/event-impact", dependencies=[Depends(verify_api_key)])
@limiter.limit("60/hour")
async def ai_event_impact(
    request: Request,
    event: str,
    symbol: str,
    context: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Analizuje wpływ konkretnego wydarzenia na rynek"""
    try:
        from ..services.ai_analysis_service import AIAnalysisService
        
        ai_service = AIAnalysisService()
        
        if context is None:
            context = {}
        
        impact = await ai_service.analyze_event_impact(
            event=event,
            symbol=symbol,
            context=context
        )
        
        return {
            "event": event,
            "symbol": symbol,
            "impact": impact
        }
        
    except Exception as e:
        logger.error(f"Error analyzing event impact: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analysis-results", dependencies=[Depends(verify_api_key)])
@limiter.limit("60/hour")
async def get_ai_analysis_results(
    request: Request,
    symbol: Optional[str] = Query(None, description="Filtruj po symbolu"),
    limit: int = Query(50, ge=1, le=200, description="Maksymalna liczba wyników"),
    signal_type: Optional[str] = Query(None, description="Filtruj po typie sygnału"),
    min_agreement: Optional[int] = Query(None, ge=0, le=100, description="Minimalny agreement_score"),
    db=Depends(get_database)
) -> Dict[str, Any]:
    """Pobiera wyniki analiz AI z bazy danych"""
    try:
        logger.info(f"Fetching AI analysis results: symbol={symbol}, limit={limit}, signal_type={signal_type}, min_agreement={min_agreement}")
        
        if signal_type and signal_type not in ['BUY', 'SELL', 'HOLD', 'NO_SIGNAL']:
            raise HTTPException(
                status_code=400,
                detail=f"Nieprawidłowy signal_type. Dozwolone: BUY, SELL, HOLD, NO_SIGNAL"
            )
        
        results = db.get_ai_analysis_results(symbol=symbol, limit=limit)
        
        if signal_type:
            results = [r for r in results if r.get('final_signal') == signal_type]
        
        if min_agreement is not None:
            results = [r for r in results if r.get('agreement_score', 0) >= min_agreement]
        
        logger.info(f"Found {len(results)} AI analysis results")
        
        return {
            "results": results,
            "count": len(results),
            "filters_applied": {
                "symbol": symbol,
                "limit": limit,
                "signal_type": signal_type,
                "min_agreement": min_agreement
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching AI analysis results: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analysis-results/{analysis_id}", dependencies=[Depends(verify_api_key)])
@limiter.limit("60/hour")
async def get_ai_analysis_by_id(
    request: Request,
    analysis_id: int,
    db=Depends(get_database)
) -> Dict[str, Any]:
    """Pobiera szczegóły pojedynczej analizy AI"""
    try:
        logger.info(f"Fetching AI analysis by ID: {analysis_id}")
        
        result = db.get_ai_analysis_by_id(analysis_id)
        
        if not result:
            logger.warning(f"AI analysis not found: {analysis_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Analiza o ID {analysis_id} nie została znaleziona"
            )
        
        if result.get('technical_details'):
            try:
                result['technical_details'] = json.loads(result['technical_details'])
            except:
                pass
        
        if result.get('voting_details'):
            try:
                result['voting_details'] = json.loads(result['voting_details'])
            except:
                pass
        
        logger.info(f"Successfully fetched AI analysis: {analysis_id}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching AI analysis {analysis_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/token-statistics", dependencies=[Depends(verify_api_key)])
@limiter.limit("60/hour")
async def get_token_statistics(
    request: Request,
    start_date: Optional[str] = Query(None, description="Data początkowa (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Data końcowa (YYYY-MM-DD)"),
    db=Depends(get_database)
) -> Dict[str, Any]:
    """Pobiera statystyki użycia tokenów OpenAI"""
    try:
        logger.info(f"Fetching token statistics: start_date={start_date}, end_date={end_date}")
        
        date_pattern = r'^\d{4}-\d{2}-\d{2}$'
        
        if start_date and not re.match(date_pattern, start_date):
            raise HTTPException(
                status_code=400,
                detail="Nieprawidłowy format daty start_date. Użyj YYYY-MM-DD"
            )
        
        if end_date and not re.match(date_pattern, end_date):
            raise HTTPException(
                status_code=400,
                detail="Nieprawidłowy format daty end_date. Użyj YYYY-MM-DD"
            )
        
        stats = db.get_token_statistics(start_date=start_date, end_date=end_date)
        
        stats['period'] = {
            'start_date': start_date,
            'end_date': end_date
        }
        
        logger.info(f"Token statistics: {stats.get('total_tokens', 0)} tokens, ${stats.get('total_cost', 0):.4f}")
        
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching token statistics: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analysis-config", dependencies=[Depends(verify_api_key)])
@limiter.limit("60/hour")
async def get_analysis_config(
    request: Request,
    db=Depends(get_database)
) -> Dict[str, Any]:
    """Pobiera konfigurację automatycznych analiz"""
    try:
        logger.info("Fetching analysis configuration")
        
        config = db.get_analysis_config()
        
        if config.get('enabled_symbols'):
            try:
                config['enabled_symbols'] = json.loads(config['enabled_symbols'])
            except:
                config['enabled_symbols'] = []
        else:
            config['enabled_symbols'] = []
        
        logger.info(f"Analysis config: interval={config.get('analysis_interval')}min, symbols={len(config.get('enabled_symbols', []))}")
        
        return config
        
    except Exception as e:
        logger.error(f"Error fetching analysis config: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/analysis-config", dependencies=[Depends(verify_api_key)])
@limiter.limit("60/hour")
async def update_analysis_config(
    request: Request,
    config_update: Dict[str, Any],
    db=Depends(get_database)
) -> Dict[str, Any]:
    """Aktualizuje konfigurację automatycznych analiz"""
    try:
        logger.info(f"Updating analysis config: {config_update}")
        
        updates = {}
        
        if 'analysis_interval' in config_update:
            interval = config_update['analysis_interval']
            if not isinstance(interval, int) or interval < 5 or interval > 1440:
                raise HTTPException(
                    status_code=422,
                    detail="analysis_interval musi być liczbą całkowitą między 5 a 1440"
                )
            updates['analysis_interval'] = interval
        
        if 'enabled_symbols' in config_update:
            symbols = config_update['enabled_symbols']
            if not isinstance(symbols, list):
                raise HTTPException(
                    status_code=422,
                    detail="enabled_symbols musi być listą"
                )
            if len(symbols) > 50:
                raise HTTPException(
                    status_code=422,
                    detail="enabled_symbols może zawierać maksymalnie 50 symboli"
                )
            for symbol in symbols:
                if '/' not in symbol:
                    raise HTTPException(
                        status_code=422,
                        detail=f"Symbol {symbol} musi zawierać '/' (np. EUR/USD)"
                    )
            updates['enabled_symbols'] = json.dumps(symbols)
        
        if 'notification_threshold' in config_update:
            threshold = config_update['notification_threshold']
            if not isinstance(threshold, int) or threshold < 0 or threshold > 100:
                raise HTTPException(
                    status_code=422,
                    detail="notification_threshold musi być liczbą całkowitą między 0 a 100"
                )
            updates['notification_threshold'] = threshold
        
        if 'is_active' in config_update:
            is_active = config_update['is_active']
            if not isinstance(is_active, bool):
                raise HTTPException(
                    status_code=422,
                    detail="is_active musi być wartością boolean"
                )
            updates['is_active'] = is_active
        
        if not updates:
            raise HTTPException(
                status_code=400,
                detail="Brak danych do aktualizacji"
            )
        
        db.update_analysis_config(updates)
        
        updated_config = db.get_analysis_config()
        
        if updated_config.get('enabled_symbols'):
            try:
                updated_config['enabled_symbols'] = json.loads(updated_config['enabled_symbols'])
            except:
                updated_config['enabled_symbols'] = []
        
        logger.info(f"Analysis config updated successfully")
        
        return {
            "message": "Konfiguracja zaktualizowana pomyślnie",
            "updated_config": updated_config
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating analysis config: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trigger-analysis", dependencies=[Depends(verify_api_key)])
@limiter.limit("10/hour")
async def trigger_manual_analysis(
    request: Request,
    trigger_request: Optional[Dict[str, Any]] = None,
    db=Depends(get_database),
    telegram=Depends(get_telegram_service)
) -> Dict[str, Any]:
    """Ręcznie uruchamia cykl analiz AI"""
    try:
        symbols = None
        timeframe = "1h"
        
        if trigger_request:
            symbols = trigger_request.get('symbols')
            timeframe = trigger_request.get('timeframe', '1h')
        
        logger.info(f"Manual analysis triggered: symbols={symbols}, timeframe={timeframe}")
        
        valid_timeframes = ['1m', '5m', '15m', '30m', '1h', '4h', '1d']
        if timeframe not in valid_timeframes:
            raise HTTPException(
                status_code=422,
                detail=f"Nieprawidłowy timeframe. Dozwolone: {valid_timeframes}"
            )
        
        if symbols:
            if not isinstance(symbols, list):
                raise HTTPException(
                    status_code=422,
                    detail="symbols musi być listą"
                )
            if len(symbols) > 50:
                raise HTTPException(
                    status_code=422,
                    detail="Maksymalnie 50 symboli"
                )
            for symbol in symbols:
                if '/' not in symbol:
                    raise HTTPException(
                        status_code=422,
                        detail=f"Symbol {symbol} musi zawierać '/' (np. EUR/USD)"
                    )
        
        from ..services.auto_analysis_scheduler import AutoAnalysisScheduler
        
        scheduler = AutoAnalysisScheduler(
            database=db,
            telegram=telegram,
            interval_minutes=settings.analysis_interval
        )
        
        if symbols:
            scheduler.symbols = symbols
            logger.info(f"Using custom symbols list: {len(symbols)} symbols")
        else:
            logger.info(f"Using default symbols list: {len(scheduler.symbols)} symbols")
        
        start_time = time.time()
        
        try:
            results = await asyncio.wait_for(
                scheduler.run_analysis_cycle(),
                timeout=300.0
            )
        except asyncio.TimeoutError:
            logger.error("Analysis cycle timeout (300s)")
            raise HTTPException(
                status_code=500,
                detail="Analiza przekroczyła limit czasu (300s). Spróbuj z mniejszą liczbą symboli."
            )
        
        duration = time.time() - start_time
        
        stats = scheduler.get_statistics()
        
        logger.info(f"Manual analysis completed: {len(results)} results in {duration:.1f}s")
        
        return {
            "message": f"Analiza zakończona dla {len(results)} symboli",
            "results": results,
            "statistics": {
                "total_symbols": len(results),
                "successful": stats.get('successful_analyses', 0),
                "failed": stats.get('failed_analyses', 0),
                "total_tokens": stats.get('total_tokens', 0),
                "total_cost": stats.get('total_cost', 0.0),
                "duration_seconds": round(duration, 2)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in manual analysis trigger: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
