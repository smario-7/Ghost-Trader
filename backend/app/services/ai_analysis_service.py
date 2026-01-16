"""
AI Analysis Service - wykorzystanie OpenAI GPT do analizy makroekonomicznej
"""
import aiohttp
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json
import os


class AIAnalysisService:
    """
    Serwis wykorzystujący OpenAI GPT do analizy:
    - Danych makroekonomicznych
    - Wiadomości rynkowych
    - Wydarzeń światowych
    - Sentymentu rynkowego
    """
    
    def __init__(self, api_key: str = None, model: str = None):
        """
        Inicjalizacja serwisu AI
        
        Args:
            api_key: Klucz OpenAI API
            model: Model GPT do użycia
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.api_url = "https://api.openai.com/v1/chat/completions"
        
        # Domyślnie GPT-4o (najnowszy, najlepszy)
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o")
        
        self.logger = logging.getLogger("trading_bot.ai")
        
        # Loguj status klucza API (bez ujawniania całego klucza)
        if self.api_key:
            key_preview = f"{self.api_key[:10]}...{self.api_key[-4:]}" if len(self.api_key) > 14 else "***"
            self.logger.info(f"✅ AI Service initialized with model: {self.model}, API key: {key_preview}")
        else:
            self.logger.warning(f"⚠️ AI Service initialized WITHOUT API key - funkcje AI nie będą działać!")
    
    async def analyze_macro_data(
        self,
        symbol: str,
        macro_data: Dict[str, Any],
        news: List[Dict[str, Any]],
        technical_indicators: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Kompleksowa analiza łącząca dane makro, news i wskaźniki techniczne
        
        Args:
            symbol: Symbol (np. EUR/USD)
            macro_data: Dane makroekonomiczne
            news: Lista wiadomości
            technical_indicators: Wskaźniki techniczne
        
        Returns:
            Słownik z analizą i rekomendacją
        """
        
        # Przygotuj prompt dla Claude
        prompt = self._create_analysis_prompt(
            symbol, macro_data, news, technical_indicators
        )
        
        try:
            # Wywołaj OpenAI API
            analysis = await self._call_openai_api(prompt)
            
            # Parsuj odpowiedź
            result = self._parse_analysis(analysis)
            
            self.logger.info(
                f"AI analysis completed for {symbol}",
                extra={
                    "symbol": symbol,
                    "recommendation": result.get("recommendation"),
                    "confidence": result.get("confidence")
                }
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"AI analysis error: {e}", exc_info=True)
            return {
                "error": str(e),
                "recommendation": "HOLD",
                "confidence": 0
            }
    
    def _create_analysis_prompt(
        self,
        symbol: str,
        macro_data: Dict[str, Any],
        news: List[Dict[str, Any]],
        technical_indicators: Dict[str, Any]
    ) -> str:
        """Tworzy szczegółowy prompt do analizy"""
        
        prompt = f"""Jesteś ekspertem analizy rynków finansowych. Przeanalizuj poniższe dane i wygeneruj rekomendację tradingową dla {symbol}.

## DANE MAKROEKONOMICZNE
{json.dumps(macro_data, indent=2, ensure_ascii=False)}

## NAJNOWSZE WIADOMOŚCI (ostatnie 24h)
"""
        
        for i, article in enumerate(news[:5], 1):
            prompt += f"\n{i}. **{article.get('title')}**\n"
            prompt += f"   Źródło: {article.get('source')}\n"
            prompt += f"   Data: {article.get('published_at')}\n"
            if article.get('summary'):
                prompt += f"   Streszczenie: {article.get('summary')}\n"
        
        prompt += f"""

## WSKAŹNIKI TECHNICZNE
{json.dumps(technical_indicators, indent=2, ensure_ascii=False)}

## ZADANIE
Przeanalizuj wszystkie powyższe dane i udziel odpowiedzi w formacie JSON:

{{
  "recommendation": "BUY" | "SELL" | "HOLD",
  "confidence": 0-100,
  "reasoning": "Szczegółowe uzasadnienie decyzji",
  "key_factors": ["Czynnik 1", "Czynnik 2", "..."],
  "risks": ["Ryzyko 1", "Ryzyko 2", "..."],
  "time_horizon": "short" | "medium" | "long",
  "sentiment_score": 0-100,
  "macro_impact": "positive" | "neutral" | "negative",
  "news_impact": "positive" | "neutral" | "negative",
  "technical_signal": "bullish" | "neutral" | "bearish",
  "stop_loss_pct": 0-20,
  "take_profit_pct": 0-50,
  "risk_reward_ratio": 0-10,
  "position_size_recommendation": "low" | "medium" | "high"
}}

WAŻNE:
- Uwzględnij zarówno dane makro, jak i techniczne
- Zwróć uwagę na sentiment w wiadomościach
- Oceń krótko i średnioterminowy wpływ wydarzeń
- Bądź obiektywny i wskaż główne ryzyka
- **STOP LOSS**: Ustaw % poniżej ceny wejścia (dla BUY) lub powyżej (dla SELL)
- **TAKE PROFIT**: Ustaw % zysku docelowego
- **RISK/REWARD**: Powinno być min 1:2 (TP/SL ratio)
- Odpowiedz TYLKO w formacie JSON, bez dodatkowego tekstu
"""
        
        return prompt
    
    async def _call_openai_api(self, prompt: str) -> str:
        """
        Wywołuje OpenAI API
        
        Args:
            prompt: Prompt do analizy
        
        Returns:
            Odpowiedź GPT jako string
        """
        
        if not self.api_key:
            raise ValueError(
                "OpenAI API key not found! "
                "Set OPENAI_API_KEY in .env file"
            )
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "Jesteś ekspertem analizy rynków finansowych i tradingu. Udzielasz precyzyjnych rekomendacji opartych na danych makroekonomicznych, wiadomościach i wskaźnikach technicznych."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7,
            "max_tokens": 2000
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url,
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self.api_key}"
                    },
                    timeout=30
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        
                        # Wyciągnij tekst z odpowiedzi
                        message = data.get("choices", [{}])[0].get("message", {})
                        content = message.get("content", "")
                        
                        return content
                    else:
                        error_text = await response.text()
                        raise Exception(f"OpenAI API error: {response.status} - {error_text}")
                        
        except Exception as e:
            self.logger.error(f"Error calling OpenAI API: {e}")
            raise
    
    def _parse_analysis(self, response: str) -> Dict[str, Any]:
        """
        Parsuje odpowiedź JSON od Claude
        
        Args:
            response: Odpowiedź tekstowa
        
        Returns:
            Sparsowany słownik
        """
        try:
            # Wyczyść ewentualne znaczniki markdown
            clean_response = response.strip()
            if clean_response.startswith("```json"):
                clean_response = clean_response[7:]
            if clean_response.endswith("```"):
                clean_response = clean_response[:-3]
            clean_response = clean_response.strip()
            
            # Parsuj JSON
            result = json.loads(clean_response)
            
            # Walidacja
            required_fields = ["recommendation", "confidence", "reasoning"]
            for field in required_fields:
                if field not in result:
                    raise ValueError(f"Missing required field: {field}")
            
            # Normalizuj recommendation
            result["recommendation"] = result["recommendation"].upper()
            if result["recommendation"] not in ["BUY", "SELL", "HOLD"]:
                result["recommendation"] = "HOLD"
            
            # Normalizuj confidence (0-100)
            result["confidence"] = max(0, min(100, int(result["confidence"])))
            
            return result
            
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON parse error: {e}")
            self.logger.error(f"Response was: {response}")
            
            # Fallback - spróbuj wyciągnąć podstawowe info
            return {
                "recommendation": "HOLD",
                "confidence": 50,
                "reasoning": "Nie udało się sparsować pełnej analizy AI",
                "raw_response": response
            }
        except Exception as e:
            self.logger.error(f"Error parsing analysis: {e}")
            return {
                "recommendation": "HOLD",
                "confidence": 50,
                "reasoning": f"Błąd parsowania: {str(e)}"
            }
    
    async def get_sentiment_analysis(
        self,
        symbol: str,
        news: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analiza sentymentu z wiadomości
        
        Args:
            symbol: Symbol
            news: Lista wiadomości
        
        Returns:
            Analiza sentymentu
        """
        
        prompt = f"""Przeanalizuj sentiment w poniższych wiadomościach dotyczących {symbol}.

WIADOMOŚCI:
"""
        
        for i, article in enumerate(news[:10], 1):
            prompt += f"\n{i}. {article.get('title')}\n"
            if article.get('summary'):
                prompt += f"   {article.get('summary')}\n"
        
        prompt += """

Odpowiedz w formacie JSON:
{
  "overall_sentiment": "bullish" | "neutral" | "bearish",
  "sentiment_score": 0-100,
  "positive_news_count": liczba,
  "negative_news_count": liczba,
  "key_themes": ["temat1", "temat2", ...],
  "summary": "Krótkie podsumowanie sentymentu"
}
"""
        
        try:
            response = await self._call_openai_api(prompt)
            return self._parse_analysis(response)
        except Exception as e:
            self.logger.error(f"Sentiment analysis error: {e}")
            return {
                "overall_sentiment": "neutral",
                "sentiment_score": 50,
                "summary": "Nie udało się przeanalizować sentymentu"
            }
    
    async def analyze_event_impact(
        self,
        event: str,
        symbol: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analizuje wpływ konkretnego wydarzenia na rynek
        
        Args:
            event: Opis wydarzenia
            symbol: Symbol
            context: Dodatkowy kontekst
        
        Returns:
            Analiza wpływu wydarzenia
        """
        
        prompt = f"""Przeanalizuj wpływ poniższego wydarzenia na {symbol}:

WYDARZENIE: {event}

KONTEKST:
{json.dumps(context, indent=2, ensure_ascii=False)}

Odpowiedz w formacie JSON:
{{
  "immediate_impact": "positive" | "neutral" | "negative",
  "short_term_outlook": "bullish" | "neutral" | "bearish",
  "medium_term_outlook": "bullish" | "neutral" | "bearish",
  "impact_strength": 0-100,
  "affected_sectors": ["sektor1", "sektor2", ...],
  "key_implications": ["implikacja1", "implikacja2", ...],
  "recommendation": "BUY" | "SELL" | "HOLD",
  "reasoning": "Szczegółowe uzasadnienie"
}}
"""
        
        try:
            response = await self._call_openai_api(prompt)
            return self._parse_analysis(response)
        except Exception as e:
            self.logger.error(f"Event analysis error: {e}")
            return {
                "immediate_impact": "neutral",
                "recommendation": "HOLD",
                "reasoning": f"Nie udało się przeanalizować wydarzenia: {str(e)}"
            }


# Przykład użycia
if __name__ == "__main__":
    import asyncio
    from dotenv import load_dotenv
    load_dotenv()
    
    async def test_ai_analysis():
        # Pobierz API key z .env
        api_key = os.getenv("OPENAI_API_KEY")
        model = os.getenv("OPENAI_MODEL", "gpt-4o")
        
        if not api_key:
            print("❌ BŁĄD: Ustaw OPENAI_API_KEY w .env")
            print("Przykład: OPENAI_API_KEY=sk-proj-...")
            return
        
        print(f"✅ Using OpenAI model: {model}")
        service = AIAnalysisService(api_key=api_key, model=model)
        
        # Przykładowe dane
        macro_data = {
            "fed_rate": 5.5,
            "inflation_rate": 3.2,
            "gdp_growth": 2.1,
            "unemployment": 3.8,
            "last_fed_meeting": "2025-01-01",
            "next_fed_meeting": "2025-02-01"
        }
        
        news = [
            {
                "title": "Fed sygnalizuje możliwe obniżki stóp w 2025",
                "source": "Reuters",
                "published_at": "2025-01-07",
                "summary": "Przedstawiciele Fed sugerują elastyczne podejście do stóp procentowych"
            },
            {
                "title": "Bitcoin osiąga nowe maksima",
                "source": "Bloomberg",
                "published_at": "2025-01-07",
                "summary": "BTC przekroczył 50,000 USD napędzany rosnącym zainteresowaniem instytucjonalnym"
            }
        ]
        
        technical_indicators = {
            "rsi": 65,
            "macd": {"value": 120, "signal": 100},
            "price": 48500,
            "sma_50": 45000,
            "sma_200": 42000
        }
        
        # Analiza
        result = await service.analyze_macro_data(
            symbol="EUR/USD",
            macro_data=macro_data,
            news=news,
            technical_indicators=technical_indicators
        )
        
        print("\n=== ANALIZA GPT ===")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    asyncio.run(test_ai_analysis())
