"""
Moduł analizy danych makroekonomicznych i wydarzeń kalendarza.
"""
from typing import Dict, Any, List


def summarize_macro(macro_data: Dict[str, Any]) -> str:
    """Podsumowuje dane makro."""
    if not macro_data:
        return "Brak danych makro"
    fed = macro_data.get("fed", {})
    inflation = macro_data.get("inflation", {})
    return (
        f"Fed: {fed.get('current_rate', 'N/A')}%, "
        f"Inflacja: {inflation.get('cpi_annual', 'N/A')}%, "
        f"Następne posiedzenie: {fed.get('next_meeting', 'N/A')}"
    )


def score_macro(macro_data: Dict[str, Any]) -> str:
    """Ocenia otoczenie makroekonomiczne (positive/negative/neutral)."""
    if not macro_data:
        return "neutral"
    inflation = macro_data.get("inflation", {}).get("cpi_annual", 3.0)
    fed_rate = macro_data.get("fed", {}).get("current_rate", 5.0)
    if inflation < 3.0 and fed_rate > 5.0:
        return "positive"
    if inflation > 4.0:
        return "negative"
    return "neutral"


def summarize_events(events: List[Dict[str, Any]]) -> str:
    """Podsumowuje nadchodzące wydarzenia ekonomiczne."""
    if not events:
        return "Brak ważnych wydarzeń"
    high_impact = [e for e in events if e.get("importance") == "high"]
    return f"{len(high_impact)} ważnych wydarzeń w najbliższych dniach"


def assess_event_risk(events: List[Dict[str, Any]]) -> str:
    """Ocenia ryzyko z nadchodzących wydarzeń (low/medium/high)."""
    if not events:
        return "low"
    high_impact_count = sum(1 for e in events if e.get("impact_level", 0) >= 8)
    if high_impact_count >= 3:
        return "high"
    if high_impact_count >= 1:
        return "medium"
    return "low"


def analyze_macro_signal(macro_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Interpretuje dane makroekonomiczne i generuje sygnał.
    Zwraca słownik: signal, confidence, impact, summary.
    """
    if not macro_data:
        return {
            "signal": "HOLD",
            "confidence": 50,
            "impact": "neutral",
            "summary": "Brak danych makroekonomicznych",
        }
    fed = macro_data.get("fed", {})
    inflation = macro_data.get("inflation", {})
    gdp = macro_data.get("gdp", {})
    fed_rate = fed.get("current_rate", 5.0)
    cpi_annual = inflation.get("cpi_annual", 3.0)
    gdp_growth = gdp.get("growth_rate", 2.0)

    score = 0
    factors = []
    if cpi_annual < 2.5:
        score += 1
        factors.append("Niska inflacja")
    elif cpi_annual > 4.0:
        score -= 1
        factors.append("Wysoka inflacja")
    if fed_rate > 5.0 and cpi_annual < 3.0:
        score += 1
        factors.append("Wysokie stopy przy niskiej inflacji")
    elif fed_rate < 2.0:
        score -= 1
        factors.append("Niskie stopy")
    if gdp_growth > 2.5:
        score += 1
        factors.append("Silny wzrost PKB")
    elif gdp_growth < 1.0:
        score -= 1
        factors.append("Słaby wzrost PKB")

    if score > 0:
        signal, impact, confidence = "BUY", "positive", 60
    elif score < 0:
        signal, impact, confidence = "SELL", "negative", 60
    else:
        signal, impact, confidence = "HOLD", "neutral", 50

    summary = f"Fed: {fed_rate}%, Inflacja: {cpi_annual}%, PKB: {gdp_growth}%. " + ", ".join(factors)
    return {
        "signal": signal,
        "confidence": confidence,
        "impact": impact,
        "summary": summary,
    }
