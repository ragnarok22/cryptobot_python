# CryptoBot Python

[![PyPI version](https://img.shields.io/pypi/v/cryptobot_python.svg)](https://pypi.python.org/pypi/cryptobot-python)
[![Python tests](https://github.com/ragnarok22/cryptobot_python/actions/workflows/python-tests.yml/badge.svg)](https://github.com/ragnarok22/cryptobot_python/actions/workflows/python-tests.yml)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/ragnarok22/cryptobot_python/main.svg)](https://results.pre-commit.ci/latest/github/ragnarok22/cryptobot_python/main)
[![Documentation Status](https://readthedocs.org/projects/cryptobot-python/badge/?version=latest)](https://cryptobot-python.readthedocs.io/en/latest/?version=latest)
[![codecov](https://codecov.io/gh/ragnarok22/cryptobot_python/graph/badge.svg?token=ZsuusfJ2NJ)](https://codecov.io/gh/ragnarok22/cryptobot_python)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/ragnarok22/cryptobot_python)

Unofficial, but friendly client for the [Crypto Bot](https://pay.crypt.bot/) API. Provides Pythonic models, sane defaults, and synchronous helpers so you can issue invoices or payouts with minimal boilerplate.

## Features

* Lean synchronous client powered by `httpx`
* Dataclass models for invoices, balances, currencies, and exchange rates
* Enum-based guard rails for assets, statuses, and button names
* Optional testnet support and configurable request timeout
* FastAPI webhook example to bootstrap integrations

## Installation

CryptoBot Python targets Python 3.9+. Install it from PyPI:

```bash
pip install cryptobot-python
```

## Quick Start

Grab an API token from `@CryptoBot` in Telegram, then create a client and start issuing invoices:

```python
from cryptobot import CryptoBotClient
from cryptobot.models import Asset

client = CryptoBotClient("YOUR_API_TOKEN")

invoice = client.create_invoice(
    asset=Asset.USDT,
    amount=5.25,
    description="Coffee order #42",
)

print(invoice.bot_invoice_url)
```

Invoices, balances, currencies, and transfers are returned as dataclasses, so attributes are available using dot access. For low-level control, check the [API reference](https://cryptobot-python.readthedocs.io/en/latest/).

## Handling Errors

All API failures raise `cryptobot.errors.CryptoBotError`. Inspect the error for the Crypto Bot error `code` and `name`:

```python
try:
    client.transfer(user_id=12345, asset=Asset.TON, amount=0.5, spend_id="demo")
except CryptoBotError as exc:
    print(exc.code, exc.name)
```

## Local Development

Clone the repo and install development dependencies with Poetry:

```bash
poetry install
```

Use the helper `Makefile` targets while iterating:

```bash
make lint      # flake8 checks for cryptobot/ and tests/
make test      # pytest with coverage report
make docs      # rebuild the Sphinx documentation
```

To experiment with the webhook example, run:

```bash
poetry run uvicorn cryptobot.webhook:app --reload
```

## Contributing

Bug reports, feature ideas, and pull requests are welcome. Please run `make lint` and `make test` before opening a PR, and update the docs when modifying public APIs. See `AGENTS.md` for more contributor guidance.

## Credits

This project started with [Cookiecutter](https://github.com/audreyr/cookiecutter) and the [audreyr/cookiecutter-pypackage](https://github.com/audreyr/cookiecutter-pypackage) template.
