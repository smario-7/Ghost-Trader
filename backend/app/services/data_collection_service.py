"""
Data Collection Service - zbieranie danych makroekonomicznych i newsów
"""
import aiohttp
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json


class MacroDataService:
    """
    Serwis zbierający dane makroekonomiczne:
    - Stopy procentowe Fed
    - Inflacja (CPI)
    - PKB
    - Bezrobocie
    - Kalendarz ekonomiczny
    """
    
    def __init__(self):
        self.logger = logging.getLogger("trading_bot.macro")
        # W produkcji tutaj byłyby prawdziwe API keys do źródeł danych
        self.fred_api_key = None  # FRED API (Federal Reserve)
        self.trading_economics_api = None
    
    async def get_fed_data(self) -> Dict[str, Any]:
        """
        Pobiera dane o stopach Fed i polityce monetarnej
        
        Returns:
            Słownik z danymi Fed
        """
        
        # W produkcji: prawdziwe API Fed/FRED
        # https://fred.stlouisfed.org/docs/api/
        
        # Demo data
        return {
            "current_rate": 5.5,
            "last_change": "2024-11-01",
            "last_change_amount": 0.0,
            "next_meeting": "2025-02-01",
            "expected_action": "hold",
            "dot_plot_median": 4.5,
            "inflation_target": 2.0,
            "current_inflation": 3.2,
            "source": "Federal Reserve",
            "last_updated": datetime.now().isoformat()
        }
    
    async def get_inflation_data(self) -> Dict[str, Any]:
        """
        Pobiera dane o inflacji (CPI)
        
        Returns:
            Dane o inflacji
        """
        
        # W produkcji: BLS API lub FRED
        return {
            "cpi_annual": 3.2,
            "cpi_monthly": 0.3,
            "core_cpi_annual": 3.9,
            "pce_annual": 2.8,
            "last_release": "2024-12-15",
            "next_release": "2025-01-15",
            "source": "Bureau of Labor Statistics",
            "last_updated": datetime.now().isoformat()
        }
    
    async def get_gdp_data(self) -> Dict[str, Any]:
        """
        Pobiera dane o PKB
        
        Returns:
            Dane o PKB
        """
        
        return {
            "current_gdp_growth": 2.1,
            "previous_quarter": 2.4,
            "year_over_year": 2.5,
            "last_release": "2024-12-20",
            "next_release": "2025-03-28",
            "source": "Bureau of Economic Analysis",
            "last_updated": datetime.now().isoformat()
        }
    
    async def get_employment_data(self) -> Dict[str, Any]:
        """
        Pobiera dane o zatrudnieniu
        
        Returns:
            Dane o zatrudnieniu
        """
        
        return {
            "unemployment_rate": 3.8,
            "job_changes": 150000,
            "labor_participation": 62.5,
            "last_release": "2025-01-03",
            "next_release": "2025-02-07",
            "source": "Bureau of Labor Statistics",
            "last_updated": datetime.now().isoformat()
        }
    
    async def get_all_macro_data(self) -> Dict[str, Any]:
        """
        Pobiera wszystkie dane makroekonomiczne
        
        Returns:
            Kompletny zestaw danych makro
        """
        
        try:
            # Pobierz równolegle wszystkie dane
            fed_data = await self.get_fed_data()
            inflation_data = await self.get_inflation_data()
            gdp_data = await self.get_gdp_data()
            employment_data = await self.get_employment_data()
            
            return {
                "fed": fed_data,
                "inflation": inflation_data,
                "gdp": gdp_data,
                "employment": employment_data,
                "collected_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error collecting macro data: {e}")
            return {}


class NewsService:
    """
    Serwis zbierający wiadomości finansowe:
    - Bloomberg
    - Reuters
    - CNBC
    - CoinDesk (dla crypto)
    - Twitter/X sentiment
    """
    
    def __init__(self):
        self.logger = logging.getLogger("trading_bot.news")
        # W produkcji: prawdziwe API keys
        self.news_api_key = None  # newsapi.org
        self.alpha_vantage_key = None  # Alpha Vantage
        self.cryptocompare_key = None  # CryptoCompare
    
    async def get_financial_news(
        self,
        symbol: str = None,
        hours_back: int = 24,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Pobiera najnowsze wiadomości finansowe
        
        Args:
            symbol: Symbol do filtrowania (np. BTC, AAPL)
            hours_back: Ile godzin wstecz
            limit: Max liczba wiadomości
        
        Returns:
            Lista wiadomości
        """
        
        # W produkcji: prawdziwe API
        # https://newsapi.org/
        # https://www.alphavantage.co/documentation/#news-sentiment
        
        # Demo data
        demo_news = [
            {
                "title": "Fed Chair Powell Signals Cautious Approach to Rate Cuts",
                "source": "Reuters",
                "url": "https://reuters.com/...",
                "published_at": (datetime.now() - timedelta(hours=2)).isoformat(),
                "summary": "Federal Reserve Chairman Jerome Powell indicated the central bank would take a measured approach to potential interest rate reductions in 2025.",
                "sentiment": "neutral",
                "relevance": 0.9
            },
            {
                "title": "Bitcoin Surges Past $50K as Institutional Demand Grows",
                "source": "Bloomberg",
                "url": "https://bloomberg.com/...",
                "published_at": (datetime.now() - timedelta(hours=5)).isoformat(),
                "summary": "Bitcoin reached new highs driven by increasing institutional adoption and ETF inflows.",
                "sentiment": "positive",
                "relevance": 0.95
            },
            {
                "title": "US Inflation Eases to 3.2%, Below Expectations",
                "source": "CNBC",
                "url": "https://cnbc.com/...",
                "published_at": (datetime.now() - timedelta(hours=12)).isoformat(),
                "summary": "Consumer price index rose less than forecast, bolstering case for Fed rate cuts.",
                "sentiment": "positive",
                "relevance": 0.85
            },
            {
                "title": "Geopolitical Tensions Rise in Middle East",
                "source": "BBC",
                "url": "https://bbc.com/...",
                "published_at": (datetime.now() - timedelta(hours=8)).isoformat(),
                "summary": "Escalating tensions could impact oil prices and global markets.",
                "sentiment": "negative",
                "relevance": 0.7
            },
            {
                "title": "Tech Stocks Rally on Strong Earnings Reports",
                "source": "Wall Street Journal",
                "url": "https://wsj.com/...",
                "published_at": (datetime.now() - timedelta(hours=15)).isoformat(),
                "summary": "Major technology companies exceed Q4 expectations, boosting market sentiment.",
                "sentiment": "positive",
                "relevance": 0.8
            }
        ]
        
        # Filtruj po symbolu jeśli podano
        if symbol:
            symbol_keywords = {
                "BTC": ["bitcoin", "btc", "crypto"],
                "ETH": ["ethereum", "eth", "crypto"],
                "AAPL": ["apple", "aapl"],
                "TSLA": ["tesla", "tsla", "elon"]
            }
            
            keywords = symbol_keywords.get(symbol, [symbol.lower()])
            filtered_news = []
            
            for news in demo_news:
                text = (news["title"] + " " + news["summary"]).lower()
                if any(kw in text for kw in keywords):
                    filtered_news.append(news)
            
            return filtered_news[:limit]
        
        return demo_news[:limit]
    
    async def get_crypto_news(
        self,
        symbol: str = "BTC",
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Pobiera wiadomości crypto-specific
        
        Args:
            symbol: Symbol crypto (BTC, ETH, etc.)
            limit: Max liczba wiadomości
        
        Returns:
            Lista wiadomości crypto
        """
        
        # W produkcji: CryptoCompare, CoinDesk API
        
        demo_crypto_news = [
            {
                "title": f"{symbol} Network Upgrade Scheduled for Next Month",
                "source": "CoinDesk",
                "url": "https://coindesk.com/...",
                "published_at": (datetime.now() - timedelta(hours=3)).isoformat(),
                "summary": f"Major protocol upgrade for {symbol} aims to improve scalability and reduce fees.",
                "sentiment": "positive",
                "category": "technology"
            },
            {
                "title": f"Whale Activity Increases in {symbol}",
                "source": "CoinTelegraph",
                "url": "https://cointelegraph.com/...",
                "published_at": (datetime.now() - timedelta(hours=6)).isoformat(),
                "summary": f"Large {symbol} holders have been accumulating, signaling potential bullish sentiment.",
                "sentiment": "positive",
                "category": "market"
            },
            {
                "title": f"{symbol} ETF Sees Record Inflows",
                "source": "The Block",
                "url": "https://theblock.co/...",
                "published_at": (datetime.now() - timedelta(hours=10)).isoformat(),
                "summary": f"Institutional investors continue to pour capital into {symbol} exchange-traded funds.",
                "sentiment": "positive",
                "category": "institutional"
            }
        ]
        
        return demo_crypto_news[:limit]
    
    async def get_breaking_news(self) -> List[Dict[str, Any]]:
        """
        Pobiera breaking news z ostatniej godziny
        
        Returns:
            Lista pilnych wiadomości
        """
        
        # W produkcji: WebSocket feeds od Bloomberg, Reuters
        
        return [
            {
                "title": "BREAKING: Fed Announces Emergency Meeting",
                "source": "Reuters",
                "published_at": (datetime.now() - timedelta(minutes=30)).isoformat(),
                "summary": "Federal Reserve calls unscheduled meeting to discuss market conditions.",
                "severity": "high",
                "sentiment": "negative"
            }
        ]
    
    async def search_news_by_keywords(
        self,
        keywords: List[str],
        days_back: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Wyszukuje wiadomości po słowach kluczowych
        
        Args:
            keywords: Lista słów kluczowych
            days_back: Ile dni wstecz
        
        Returns:
            Lista wiadomości
        """
        
        all_news = await self.get_financial_news(hours_back=days_back * 24)
        
        # Filtruj po keywords
        matching_news = []
        for news in all_news:
            text = (news["title"] + " " + news.get("summary", "")).lower()
            if any(kw.lower() in text for kw in keywords):
                matching_news.append(news)
        
        return matching_news


class EventCalendarService:
    """
    Serwis kalendarza ekonomicznego
    - Posiedzenia Fed
    - Publikacje danych makro
    - Earnings reports
    - Ważne wydarzenia geopolityczne
    """
    
    def __init__(self):
        self.logger = logging.getLogger("trading_bot.calendar")
    
    async def get_upcoming_events(
        self,
        days_ahead: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Pobiera nadchodzące wydarzenia ekonomiczne
        
        Args:
            days_ahead: Ile dni do przodu
        
        Returns:
            Lista wydarzeń
        """
        
        # W produkcji: Trading Economics API, ForexFactory
        
        now = datetime.now()
        
        demo_events = [
            {
                "date": (now + timedelta(days=1)).isoformat(),
                "time": "14:00 EST",
                "event": "FOMC Meeting Minutes",
                "importance": "high",
                "previous": None,
                "forecast": None,
                "actual": None,
                "currency": "USD",
                "impact_level": 9
            },
            {
                "date": (now + timedelta(days=3)).isoformat(),
                "time": "08:30 EST",
                "event": "US Non-Farm Payrolls",
                "importance": "high",
                "previous": 150000,
                "forecast": 175000,
                "actual": None,
                "currency": "USD",
                "impact_level": 10
            },
            {
                "date": (now + timedelta(days=5)).isoformat(),
                "time": "10:00 EST",
                "event": "US CPI Release",
                "importance": "high",
                "previous": 3.2,
                "forecast": 3.1,
                "actual": None,
                "currency": "USD",
                "impact_level": 10
            }
        ]
        
        return demo_events
    
    async def get_todays_events(self) -> List[Dict[str, Any]]:
        """
        Pobiera dzisiejsze wydarzenia
        
        Returns:
            Lista dzisiejszych wydarzeń
        """
        
        all_events = await self.get_upcoming_events(days_ahead=1)
        today = datetime.now().date()
        
        return [
            event for event in all_events
            if datetime.fromisoformat(event["date"]).date() == today
        ]


# Test
if __name__ == "__main__":
    import asyncio
    
    async def test_services():
        # Macro data
        print("\n=== MACRO DATA ===")
        macro_service = MacroDataService()
        macro_data = await macro_service.get_all_macro_data()
        print(json.dumps(macro_data, indent=2))
        
        # News
        print("\n=== FINANCIAL NEWS ===")
        news_service = NewsService()
        news = await news_service.get_financial_news(symbol="BTC", limit=5)
        for article in news:
            print(f"\n{article['title']}")
            print(f"Source: {article['source']}")
            print(f"Sentiment: {article['sentiment']}")
        
        # Calendar
        print("\n=== UPCOMING EVENTS ===")
        calendar_service = EventCalendarService()
        events = await calendar_service.get_upcoming_events(days_ahead=7)
        for event in events:
            print(f"\n{event['date']}: {event['event']}")
            print(f"Importance: {event['importance']}")
    
    asyncio.run(test_services())
