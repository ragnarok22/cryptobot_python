# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CryptoBot Python is an unofficial Python client library for the Crypto Bot (Crypto Pay API) for Telegram. It enables cryptocurrency payment integration with support for creating invoices, transfers, balance management, and webhook handling.

## Common Development Commands

### Package Management
```bash
poetry install                          # Install all dependencies including dev
poetry install --no-dev                 # Install production dependencies only
poetry install --extras docs            # Install with documentation extras
```

### Testing
```bash
make test                               # Run pytest with coverage report and XML output
make test-all                          # Run tests across all Python versions with tox
make coverage                          # Generate HTML coverage report and open in browser
poetry run pytest                     # Direct pytest execution
poetry run coverage run -m pytest     # Run tests with coverage
```

### Code Quality
```bash
make lint                              # Run flake8 linting (uses max-line-length=127, max-complexity=10)
poetry run flake8 cryptobot tests     # Direct flake8 execution
```

### Documentation
```bash
make docs                              # Generate Sphinx HTML documentation with API docs
make servedocs                         # Watch and rebuild docs on changes (requires watchdog)
```

### Build and Release
```bash
make dist                              # Clean build artifacts and create source/wheel packages
make release                           # Build and publish to PyPI
poetry build                           # Build with Poetry
poetry publish                         # Publish to PyPI
```

### Webhook Development
```bash
poetry run uvicorn cryptobot.webhook:app --reload    # Run webhook server with hot reload
```

### Cleanup
```bash
make clean                             # Remove all build, test, coverage and Python artifacts
make clean-build                       # Remove build artifacts only
make clean-test                        # Remove test and coverage artifacts only
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

### Development Dependencies (pyproject.toml)
- **Testing**: pytest (8.4.2+), coverage (7.2.2+)
- **Linting**: flake8 (6.0.0+) with max line length 127, max complexity 10
- **Documentation**: sphinx (7.1.2+), sphinx-rtd-theme (1.3.0+), watchdog (2.2.1+)
- **Formatting**: black, isort via pre-commit hooks
- **Fast Linting**: ruff with auto-fix capabilities
- **Python Support**: 3.9.12+ to 3.13

### Poetry Extras
```bash
poetry install --extras docs           # Install documentation dependencies
```

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

### GitHub Actions (.github/workflows/)
- **python-tests.yml**: Matrix testing across Python 3.9.12-3.13 with Poetry caching, flake8 linting, pytest execution, and Codecov integration
- **python-publish.yml**: Automated PyPI publishing on releases
- **Dependabot**: Automated dependency updates (pip dependencies)
- **pre-commit.ci**: Automated code formatting and linting

### Documentation
- Sphinx-based documentation hosted on Read the Docs
- Configuration: `.readthedocs.yaml` with Python 3.12
- ReStructuredText format (.rst files) in `docs/` directory
- Auto-generated API docs with `sphinx-apidoc`
- Built documentation available at: https://cryptobot-python.readthedocs.io/

## Security Considerations

- API tokens stored in environment variables (never hardcoded)
- Webhook signature verification using HMAC-SHA256
- Secure HTTP headers for API authentication
- Custom exception handling with proper error codes
