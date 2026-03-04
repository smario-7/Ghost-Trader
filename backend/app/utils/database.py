"""
Fasada: re-eksport Database z database_impl dla kompatybilności importów.
Wszystkie wywołania from app.utils.database import Database działają bez zmian.
"""
from app.utils.database_impl.connection import Database

__all__ = ["Database"]
