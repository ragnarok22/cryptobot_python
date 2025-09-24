# Repository Guidelines

## Project Structure & Module Organization
- `cryptobot/` contains the core package; async clients live beside `_sync/` wrappers, and `models/` defines request/response DTOs.
- `cryptobot/webhook.py` exposes the FastAPI webhook entrypoint used by the sample service.
- Tests reside under `tests/`, notably `tests/test_sync_client.py`; add new regression coverage here.
- Documentation sources live in `docs/`; rebuild when API signatures or examples change.
- Build artifacts (`dist/`, `htmlcov/`) should remain untracked.

## Build, Test, and Development Commands
- `poetry install` resolves runtime and dev dependencies pinned in `poetry.lock`.
- `poetry run python -m cryptobot.webhook` starts the demo webhook for local validation.
- `make lint` wraps `poetry run flake8` to enforce style gates.
- `make test` runs pytest with coverage; use `make test-all` for the tox matrix when touching cross-version code paths.
- `make docs` regenerates the Sphinx site (`docs/_build/html/index.html`).

## Coding Style & Naming Conventions
- Target Python 3.9+ with 4-space indentation and keep lines ≤127 characters.
- Prefer snake_case for modules, functions, and variables; classes (especially in `models/`) use PascalCase matching CryptoBot entities.
- Run `poetry run flake8 cryptobot tests` before submitting to catch import or complexity issues.

## Testing Guidelines
- Tests use pytest; name files `tests/test_*.py` and functions `test_*`.
- Maintain coverage near the existing ~90% target by extending fixtures and using httpx `MockTransport` for network isolation.
- Execute `make test` before commits and `make test-all` when modifying compatibility-sensitive code.

## Commit & Pull Request Guidelines
- Follow Conventional Commit prefixes used in history, e.g., `feat(sync): add transfer helper` or `fix: handle webhook timeouts`.
- PRs should summarize changes, link issues, and note `make lint`/`make test` results; include screenshots for docs or webhook response updates.

## Security & Configuration Tips
- Store secrets in `.env` and load them via `python-dotenv`; never hard-code tokens.
- After dependency bumps (FastAPI, Uvicorn, httpx), verify the webhook boots with `poetry run uvicorn cryptobot.webhook:app --reload`.
