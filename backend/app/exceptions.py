"""
Dedykowane wyjątki aplikacji – używane w serwisach i mapowane na kody HTTP w routerach.
"""


class StrategyNotFoundException(Exception):
    """Podnoszony, gdy strategia o podanym ID nie istnieje w bazie."""

    def __init__(self, strategy_id: int, message: str | None = None):
        self.strategy_id = strategy_id
        super().__init__(message or f"Strategia o ID {strategy_id} nie została znaleziona")


class SignalGenerationException(Exception):
    """Podnoszony przy błędzie generowania sygnału (np. w checkerze)."""


class AnalysisNotFoundException(Exception):
    """Podnoszony, gdy analiza AI o podanym ID nie istnieje."""

    def __init__(self, analysis_id: int, message: str | None = None):
        self.analysis_id = analysis_id
        super().__init__(message or f"Analiza o ID {analysis_id} nie została znaleziona")
