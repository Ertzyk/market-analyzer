# Market Analyzer

A full-stack financial analytics platform that provides real-time market data, portfolio tracking, alerting, logging, export, personalization, and scheduled background tasks.

Built with:
- **FastAPI** (backend)
- **React** (frontend)
- **PostgreSQL** (database)
- **APScheduler** (scheduler)
- **SQLAlchemy** (ORM)
- **yfinance** (market data)
- **pytest** (testing)

---

## Features

### Market Data
- Live price lookup for any symbol.
- Historical OHLC price retrieval.
- Server-side caching with TTL to reduce API calls.

### Portfolio Management
- Add/update positions.
- Automatic weighted average price calculation.
- Multi-currency support.
- Portfolio valuation with FX rates.

### Alerts
- Create price alerts with conditions (`>`, `<`).
- Check alerts every 1 minute via APScheduler.
- Triggered alerts are saved in logs.

### Data Export
- Export historical prices to CSV through an API endpoint.

### Logging System
- Tracks alerts, portfolio operations, requests, and system messages.
- Filtering by type, date, symbol.
- Reset logs endpoint.

### Personalization (UC5)
- User-adjustable data layout, visible columns, etc.

### Database
- PostgreSQL for production.
- SQLite test database for pytest.
- Automatic schema creation via SQLAlchemy.

### Test Suite
Covers:
- Alerts
- Cache behavior
- FX conversion
- Error cases
- Logging
- Portfolio logic
- History and current price
- Export
- API-level validation

All tests pass.