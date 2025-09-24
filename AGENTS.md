# Repository Guidelines

## Project Structure & Module Organization
- `cryptobot/` hosts the package; `_sync/` provides synchronous client wrappers; `models/` collects request/response types; `webhook.py` exposes the FastAPI webhook entrypoint.
- `tests/` contains the pytest suite (see `tests/test_sync_client.py`) and is the home for any new regression coverage.
- `docs/` holds Sphinx sources; regenerate when API signatures or examples change.
- Build artifacts appear in `dist/` or `htmlcov/`; keep them out of commits.

## Build, Test, and Development Commands
- `poetry install` installs runtime and dev dependencies pinned in `poetry.lock`.
- `poetry run python -m cryptobot.webhook` launches the sample webhook service for local validation.
- `make lint` (wrapper for `poetry run flake8`) enforces the configured style gates.
- `make test` runs coverage-instrumented pytest; use `make test-all` to execute the tox matrix when touching cross-version code.
- `make docs` rebuilds the Sphinx site; open `docs/_build/html/index.html` to verify rendered changes.

## Coding Style & Naming Conventions
- Target Python 3.9+ with 4-space indentation and keep lines ≤127 characters to satisfy `flake8`.
- Modules and functions stay snake_case; classes (especially under `models/`) use PascalCase mirroring CryptoBot entities.
- Match synchronous helper names in `_sync/` with their async counterparts to reduce ambiguity.
- Run `poetry run flake8 cryptobot tests` before submitting to catch import and complexity violations early.

## Testing Guidelines
- Add tests under `tests/` using filenames `test_*.py` and function names `test_*`.
- `make test` prints a coverage report; uphold existing coverage levels (~90%) when introducing features.
- Prefer pytest fixtures and httpx `MockTransport` to isolate network logic; mark coroutine tests with `@pytest.mark.asyncio`.

## Commit & Pull Request Guidelines
- Follow Conventional Commit prefixes already in history (`build:`, `chore:`, `fix:`, `feat:`) and scope where helpful, e.g., `feat(sync): add transfer helper`.
- Each PR should include a concise summary, linked issue, and a note on `make lint`/`make test` results; attach screenshots when altering docs or webhook responses.
- Update docs and type hints whenever public APIs change, and ensure CI passes before requesting review.

## Security & Configuration Tips
- Keep bot tokens and secrets in `.env`; load them via `python-dotenv` rather than hard-coding.
- After dependency bumps (FastAPI/Uvicorn/httpx), run `poetry run uvicorn cryptobot.webhook:app --reload` to confirm the webhook still boots cleanly.
