# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CryptoBot Python is an unofficial Python client library for the Crypto Bot (Crypto Pay API) for Telegram. It enables cryptocurrency payment integration with support for creating invoices, transfers, balance management, and webhook handling.

## Common Development Commands

### Package Management
```bash
poetry install              # Install dependencies
poetry install --no-dev     # Install production dependencies only
```

### Testing
```bash
make test                   # Run pytest with coverage
make test-all              # Run tests across all Python versions with tox
make coverage              # Generate HTML coverage report
poetry run pytest         # Direct pytest execution
```

### Code Quality
```bash
make lint                  # Run flake8 linting
poetry run flake8         # Direct flake8 execution
```

### Documentation
```bash
make docs                  # Generate Sphinx documentation
make servedocs            # Watch and rebuild docs on changes
```

### Build and Release
```bash
make dist                  # Build source and wheel packages
poetry build              # Build with Poetry
make release              # Publish to PyPI
```

### Webhook Development
```bash
poetry run uvicorn cryptobot.webhook:app --reload    # Run webhook server with hot reload
```

## Architecture Overview

### Core Components

**CryptoBotClient** (`cryptobot/_sync/client.py`): Main synchronous API client using httpx for HTTP requests. Supports both mainnet and testnet environments with methods for invoices, transfers, balances, and exchange rates.

**Data Models** (`cryptobot/models/__init__.py`): Dataclass-based models including:
- `Asset` enum for supported cryptocurrencies (BTC, TON, ETH, USDT, etc.)
- `Invoice`, `Transfer`, `Balance`, `ExchangeRate`, `Currency` data structures

**Webhook Handler** (`cryptobot/webhook.py`): FastAPI-based webhook listener with signature verification for secure payment notifications.

**Error Handling** (`cryptobot/errors.py`): Custom exception classes with `CryptoBotError` as the base exception.

### Project Structure
```
cryptobot/
├── __init__.py           # Exports CryptoBotClient
├── _sync/client.py       # Main client implementation
├── models/__init__.py    # Data models and enums
├── errors.py            # Exception classes
├── webhook.py           # FastAPI webhook handler
└── _utils.py            # Utility functions
```

## Environment Configuration

### API Setup
- API tokens obtained from `@CryptoBot` in Telegram
- Environment variables stored in `.env` file
- Supports both mainnet and testnet environments
- Configurable HTTP timeouts

### Development Dependencies
- **Testing**: pytest with coverage reporting
- **Linting**: flake8 with max line length 127, max complexity 10
- **Formatting**: black, isort via pre-commit hooks
- **Fast Linting**: ruff with auto-fix capabilities

## Testing Framework

Tests are located in `tests/` directory using pytest with unittest classes. The main test file is `test_sync_client.py` which covers:
- Both mainnet and testnet environments
- Error handling validation
- Invoice creation and management
- Client authentication

Environment variables for testing should be configured in `.env` file.

## Code Quality Standards

### Pre-commit Configuration
- black: Code formatting
- isort: Import sorting
- ruff: Fast linting with auto-fix
- Standard hooks: trailing whitespace, end-of-file-fixer

### Flake8 Configuration
- Max line length: 127 characters
- Max complexity: 10
- Excludes: `__pycache__`, `.venv`, `.git`, `docs`, `dist`

## CI/CD Integration

### GitHub Actions
- **python-tests.yml**: Matrix testing across Python 3.9.12-3.13 with Poetry caching, linting, and Codecov integration
- **python-publish.yml**: Automated PyPI publishing
- **Dependabot**: Automated dependency updates
- **pre-commit.ci**: Automated code formatting

### Documentation
- Sphinx-based documentation hosted on Read the Docs
- ReStructuredText format (.rst files)
- Auto-generated API docs with `sphinx-apidoc`

## Security Considerations

- API tokens stored in environment variables (never hardcoded)
- Webhook signature verification using HMAC-SHA256
- Secure HTTP headers for API authentication
- Custom exception handling with proper error codes