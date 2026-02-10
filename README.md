# CryptoBot Python

[![PyPI version](https://img.shields.io/pypi/v/cryptobot_python.svg)](https://pypi.org/project/cryptobot-python/)
[![Python tests](https://github.com/ragnarok22/cryptobot_python/actions/workflows/python-tests.yml/badge.svg)](https://github.com/ragnarok22/cryptobot_python/actions/workflows/python-tests.yml)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/ragnarok22/cryptobot_python/main.svg)](https://results.pre-commit.ci/latest/github/ragnarok22/cryptobot_python/main)
[![Documentation Status](https://readthedocs.org/projects/cryptobot-python/badge/?version=latest)](https://cryptobot-python.readthedocs.io/en/latest/?version=latest)
[![codecov](https://codecov.io/gh/ragnarok22/cryptobot_python/graph/badge.svg?token=ZsuusfJ2NJ)](https://codecov.io/gh/ragnarok22/cryptobot_python)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/ragnarok22/cryptobot_python)

Unofficial but friendly Python client for the [Crypto Bot](https://pay.crypt.bot/) API. It provides typed models, sane defaults,
and a synchronous client for invoices, transfers, balances, exchange rates, and webhook handling.

## Features

- Synchronous `httpx`-based API client (`CryptoBotClient`)
- Dataclass models for API responses (`Invoice`, `Transfer`, `Balance`, `ExchangeRate`, `Currency`)
- Enum guard rails for assets, statuses, and paid button names
- Mainnet/testnet support and configurable timeouts
- FastAPI-powered webhook listener with signature verification helpers
- Custom exception model (`CryptoBotError`) with API code/name fields

## Installation

CryptoBot Python supports Python `>=3.9.12`.

```bash
pip install cryptobot-python
```

## Quick Start

```python
import os

from cryptobot import CryptoBotClient
from cryptobot.models import Asset

client = CryptoBotClient(
    api_token=os.environ["CRYPTOBOT_API_TOKEN"],
    is_mainnet=True,
    timeout=5.0,
)

app = client.get_me()
print(app.name)

invoice = client.create_invoice(
    asset=Asset.USDT,
    amount=5.25,
    description="Coffee order #42",
)

print(invoice.invoice_id, invoice.bot_invoice_url)
```

To use testnet instead of mainnet:

```python
client = CryptoBotClient(api_token=os.environ["CRYPTOBOT_TESTNET_TOKEN"], is_mainnet=False)
```

## Core API

`CryptoBotClient` methods:

- `get_me()`
- `create_invoice(...)`
- `get_invoices(...)`
- `transfer(...)`
- `get_balances()`
- `get_exchange_rates()`
- `get_currencies()`

Example transfer with idempotency via `spend_id`:

```python
from cryptobot.errors import CryptoBotError
from cryptobot.models import Asset

try:
    transfer = client.transfer(
        user_id=123456789,
        asset=Asset.TON,
        amount=0.5,
        spend_id="reward_2026_02_10_user_123456789",
        comment="Cashback reward",
    )
    print(transfer.transfer_id, transfer.status)
except CryptoBotError as exc:
    print(exc.code, exc.name)
```

## Webhooks

Use the built-in listener to validate incoming signatures and process updates:

```python
import os

from cryptobot.webhook import Listener


def handle_webhook(headers, data):
    if data.get("update_type") == "invoice_paid":
        payload = data.get("payload", {})
        print("Paid invoice:", payload.get("invoice_id"))


listener = Listener(
    host="0.0.0.0",
    callback=handle_webhook,
    api_token=os.environ["CRYPTOBOT_API_TOKEN"],
    port=2203,
    url="/webhook",
    log_level="info",
)
listener.listen()
```

For custom webhook stacks, use `cryptobot.webhook.check_signature(...)` to verify
`crypto-pay-api-signature` against the raw request body.

## Development

```bash
poetry install
make lint
make test
make docs
```

## Documentation

- Docs: https://cryptobot-python.readthedocs.io/
- API reference: https://cryptobot-python.readthedocs.io/en/latest/modules.html
- Webhook security guide: https://cryptobot-python.readthedocs.io/en/latest/webhook_security.html

## Contributing

Issues and pull requests are welcome. Before opening a PR:

```bash
make lint
make test
```

See `CONTRIBUTING.md` and `AGENTS.md` for project workflow and coding standards.

## Credits

This project started with [Cookiecutter](https://github.com/audreyr/cookiecutter) and the
[audreyr/cookiecutter-pypackage](https://github.com/audreyr/cookiecutter-pypackage) template.
