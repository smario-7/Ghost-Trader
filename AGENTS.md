# AGENTS.md

## Build & Test Commands

### Docker (Recommended)
```bash
docker-compose up -d                    # Start all services
docker-compose logs -f                  # View all logs
docker-compose logs -f backend          # Backend logs only
docker-compose up -d --build            # Rebuild and start
docker-compose restart backend          # Restart single service
```

### Manual Development
```bash
cd backend
python3.11 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000  # Terminal 1
python -m app.scheduler                     # Terminal 2
```

### Testing
```bash
# Run all tests
make test                                   # or: cd backend && pytest tests/ -v

# Run single test file
cd backend && pytest tests/test_api_ai_endpoints.py -v

# Run single test function
cd backend && pytest tests/test_api_ai_endpoints.py::test_get_analysis_results -v

# Run by markers
cd backend && pytest -m unit               # Fast, isolated tests
cd backend && pytest -m integration        # Component interaction tests
cd backend && pytest -m api                # API endpoint tests
cd backend && pytest -m database           # Database operation tests
cd backend && pytest -m e2e                # End-to-end tests
cd backend && pytest -m "not slow"         # Exclude slow tests

# Run with coverage
cd backend && pytest --cov=app tests/

# Run specific test with markers
cd backend && pytest -m "api and not slow" -v
```

### Code Quality
```bash
# Clean cache and temp files
make clean

# Verify configuration
docker-compose exec backend python -c "from app.config import get_settings; print('Config OK')"

# Check Python syntax
python -m py_compile app/main.py

# Run with verbose output
pytest -vv --tb=short
```

## Code Style Guidelines

### Import Organization
- Standard library imports first
- Third-party imports second  
- Local application imports third
- Use absolute imports for app modules: `from app.config import get_settings`
- Group imports with blank lines between sections
- Avoid wildcard imports (`from module import *`)

### Type Hints
- All functions must have type hints for parameters and return values
- Use `Optional[T]` for nullable types
- Use `Dict[str, Any]` for flexible dictionaries
- Use `List[T]` for arrays
- Enums must inherit from `str` and `Enum`: `class SignalType(str, Enum)`

### Naming Conventions
- **Variables/Functions**: `snake_case`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_SNAKE_CASE`
- **Private methods**: `_private_method`
- **Files**: `snake_case.py`
- **Database tables**: `snake_case_plural`

### Error Handling
- Use specific exception types (ValueError, KeyError, etc.)
- HTTP exceptions via `raise HTTPException(status_code=400, detail="Message")`
- Always include descriptive error messages in Polish
- Use `logger.error()` for logging errors with context
- Database operations should handle connection errors gracefully

### Documentation
- All modules start with `"""Module description"""`
- Classes and public methods must have docstrings
- Complex logic should have inline comments in Polish
- Use Pydantic `Field(description="...")` for API documentation

### FastAPI Specific
- All API endpoints require `X-API-Key` header authentication
- Use dependency injection: `def get_current_user(api_key: str = Depends(api_key_auth))`
- Return Pydantic models, not raw dicts
- Use `@limiter.limit("rate")` for rate limiting
- Implement proper status codes (200, 201, 400, 401, 403, 404, 422, 500)

### Database
- Use `app.utils.database.Database` class for all DB operations
- Always use prepared statements via parameterized queries
- Transactions should be committed explicitly or use context managers
- Handle database migrations manually with SQL scripts
- Use `with db.get_connection() as conn:` pattern for connection management

### Configuration
- All settings in `app.config.Settings` with Pydantic validation
- Environment variables in `.env` file (never commit)
- Use `get_settings()` singleton for access
- Sensible defaults for all optional values
- Validation constraints via Pydantic `Field()`

### Testing Patterns
- Use fixtures from `conftest.py` for database setup
- Mock external services (OpenAI, Telegram, Yahoo Finance)
- Test both happy path and error scenarios
- Use descriptive test names: `test_create_strategy_returns_201`
- Mark tests with appropriate markers: `@pytest.mark.unit`, `@pytest.mark.api`

### Security
- Never log or return sensitive data (API keys, tokens)
- Validate all input via Pydantic models
- Use parameterized queries to prevent SQL injection
- Rate limit API endpoints, especially AI endpoints
- Sanitize all user-provided content before processing

### AI/ML Integration
- Token counting is mandatory for OpenAI API calls
- Cost tracking for all AI operations
- Rate limiting between AI requests (2 second pause)
- Fallback behavior when AI services are unavailable
- Cache AI responses when appropriate to reduce costs

### Asynchronous Operations
- Use `async def` for I/O bound operations
- Database calls should use async patterns where possible
- Use `asyncio.gather()` for concurrent operations
- Proper error handling with `try/except` in async functions

### Logging
- Use Polish language for all log messages
- Levels: DEBUG (detailed info), INFO (normal flow), WARNING (recoverable issues), ERROR (failures)
- Include context: `logger.info(f"Processed {strategy.name} for {symbol}")`
- Structured logging for production debugging

### Frontend (Alpine.js)
- Follow Alpine.js documentation: https://alpinejs.dev/start-here
- Use vanilla JS components in `frontend/js/components/`
- Components communicate via custom events
- Dashboard at `/` serves the UI

## Known Issues

### Yahoo Finance API
- Czasami Yahoo Finance nie zwraca danych (rate limiting lub niedostępność)
- Objawia się jako "No price data found, symbol may be delisted"
- Wykresy mogą nie działać, ale reszta aplikacji działa
- Rozwiązanie: poczekaj lub użyj VPN

### Local Development vs Docker
- Lokalnie: frontend na `http://localhost:8081`, backend na `http://localhost:8000`
- Docker: frontend na `http://localhost:8080`, backend przez nginx proxy
- Kod frontendowy automatycznie wykrywa tryb przez `window.location.hostname`