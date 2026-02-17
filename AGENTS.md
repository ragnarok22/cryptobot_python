# AGENTS

## Repository Guidelines
- `cryptobot/` contains the core package; async clients live beside `_sync/` wrappers, and `models/` defines request/response
  DTOs.
- `cryptobot/webhook.py` exposes the FastAPI webhook entrypoint used by the sample service.
- Tests reside under `tests/`, notably `tests/test_sync_client.py`; add new regression coverage here.
- Documentation sources live in `docs/`; rebuild when API signatures or examples change.
- Build artifacts (`dist/`, `htmlcov/`) should remain untracked.

## Build, Test, and Development Commands
- `uv sync` resolves runtime and dev dependencies pinned in `uv.lock`.
- `uv run python -m cryptobot.webhook` starts the demo webhook for local validation.
- `make lint` wraps `uv run flake8` to enforce style gates.
- `make test` runs pytest with coverage; use `make test-all` for the tox matrix when touching cross-version code paths.
- `make docs` regenerates the Sphinx site (`docs/_build/html/index.html`).

## Coding Style & Naming Conventions
- Target Python 3.9+ with 4-space indentation and keep lines ≤127 characters.
- Prefer snake_case for modules, functions, and variables; classes (especially in `models/`) use PascalCase matching
  CryptoBot entities.
- Run `uv run flake8 cryptobot tests` before submitting to catch import or complexity issues.

## Testing Guidelines
- Tests use pytest; name files `tests/test_*.py` and functions `test_*`.
- Maintain coverage near the existing ~90% target by extending fixtures and using httpx `MockTransport` for network
  isolation.
- Execute `make test` before commits and `make test-all` when modifying compatibility-sensitive code.

## Commit & Pull Request Guidelines
- Follow Conventional Commit prefixes used in history, e.g., `feat(sync): add transfer helper` or
  `fix: handle webhook timeouts`.
- PRs should summarize changes, link issues, and note `make lint`/`make test` results; include screenshots for docs or
  webhook response updates.

## Security & Configuration Tips
- Store secrets in `.env` and load them via `python-dotenv`; never hard-code tokens.
- After dependency bumps (FastAPI, Uvicorn, httpx), verify the webhook boots with
  `uv run uvicorn cryptobot.webhook:app --reload`.

## Project Overview
CryptoBot Python is an unofficial Python client library for the Crypto Bot (Crypto Pay API) for Telegram. It enables
cryptocurrency payment integration with support for invoices, transfers, balance management, exchange rates, and webhook
handling.

## Common Development Commands

### Package Management
```bash
uv sync                                    # Install all dependencies including dev
uv sync --no-group dev                     # Install production dependencies only
uv sync --extra docs                       # Install with documentation extras
```

### Testing
```bash
make test                               # Run pytest with coverage report and XML output
make test-all                           # Run tests across all Python versions with tox
make coverage                           # Generate HTML coverage report and open in browser
uv run pytest                       # Direct pytest execution
uv run coverage run -m pytest       # Run tests with coverage
```

### Code Quality
```bash
make format                             # Format code with ruff (format + auto-fix)
make lint                               # Run flake8 linting (max-line-length=127, max-complexity=10)
uv run flake8 cryptobot tests       # Direct flake8 execution
```

### Documentation
```bash
make docs                               # Generate Sphinx HTML documentation with API docs
make servedocs                          # Watch and rebuild docs on changes (requires watchdog)
```

### Build and Release
```bash
make dist                               # Clean build artifacts and create source/wheel packages
make release                            # Build and publish to PyPI
uv build                               # Build package
uv publish                          # Publish to PyPI
```

### Webhook Development
```bash
uv run uvicorn cryptobot.webhook:app --reload    # Run webhook server with hot reload
```

### Cleanup
```bash
make clean                              # Remove build, test, coverage and Python artifacts
make clean-build                        # Remove build artifacts only
make clean-test                         # Remove test and coverage artifacts only
```

## Architecture Overview
- `CryptoBotClient` (`cryptobot/_sync/client.py`): synchronous httpx client supporting mainnet/testnet; methods for
  invoices, transfers, balances, and exchange rates.
- Data models (`cryptobot/models/__init__.py`): dataclass models including `Asset` enum, `Invoice`, `Transfer`,
  `Balance`, `ExchangeRate`, `Currency`.
- Webhook handler (`cryptobot/webhook.py`): FastAPI listener with signature verification for secure payment
  notifications.
- Error handling (`cryptobot/errors.py`): custom exception classes with `CryptoBotError` as the base exception.
- Utilities (`cryptobot/_utils.py`): shared helpers.

### Project Structure
```
cryptobot/
├── __init__.py           # Exports CryptoBotClient
├── _sync/client.py       # Main client implementation
├── models/__init__.py    # Data models and enums
├── errors.py             # Exception classes
├── webhook.py            # FastAPI webhook handler
└── _utils.py             # Utility functions
```

## Environment Configuration

### API Setup
- API tokens obtained from `@CryptoBot` in Telegram.
- Environment variables stored in `.env`.
- Supports both mainnet and testnet environments.
- Configurable HTTP timeouts.

### Development Dependencies (pyproject.toml)
- Testing: pytest (8.4.2+), coverage (7.2.2+).
- Linting: flake8 (6.0.0+) max line length 127, max complexity 10.
- Documentation: sphinx (7.1.2+), sphinx-rtd-theme (1.3.0+), watchdog (2.2.1+).
- Formatting: black, isort via pre-commit hooks.
- Fast linting: ruff with auto-fix capabilities.
- Python support: 3.9.12+ to 3.13.

### Extras
```bash
uv sync --extra docs           # Install documentation dependencies
```

## Testing Framework
- Tests live in `tests/` using pytest; main coverage in `tests/test_sync_client.py`.
- Coverage includes mainnet and testnet, error handling, invoices, client authentication.
- Testing relies on `.env` configuration for environment variables.

## Code Quality Standards

### Pre-commit Configuration
- black for formatting.
- isort for import sorting.
- ruff for fast linting with auto-fix.
- Standard hooks: trailing whitespace, end-of-file fixer.

### Flake8 Configuration
- Max line length: 127 characters.
- Max complexity: 10.
- Excludes: `__pycache__`, `.venv`, `.git`, `docs`, `dist`.

## CI/CD Integration
- `python-tests.yml`: matrix across Python 3.9.12–3.13 with uv caching, flake8, pytest, Codecov.
- `python-publish.yml`: automated PyPI publishing on releases.
- Dependabot manages dependency updates.
- pre-commit.ci runs formatting and linting.

## Documentation
- Sphinx-based docs in `docs/`; config `.readthedocs.yaml` targets Python 3.12.
- ReStructuredText sources; API docs generated with `sphinx-apidoc`.
- Hosted at https://cryptobot-python.readthedocs.io/.

## Security Considerations
- API tokens stored in environment variables; never hard-coded.
- Webhook signature verification uses HMAC-SHA256.
- Secure HTTP headers used for API authentication.
- Custom exception handling with proper error codes.
