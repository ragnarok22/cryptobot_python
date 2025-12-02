# Welcome to CryptoBot Python's documentation!

CryptoBot Python is an unofficial, but friendly Python client library for the [Crypto Bot](https://pay.crypt.bot/) API.
It provides Pythonic models, sane defaults, and synchronous helpers so you can issue invoices or payouts with minimal boilerplate.

## Features

* **Lean synchronous client** powered by `httpx`
* **Dataclass models** for invoices, balances, currencies, and exchange rates
* **Enum-based guard rails** for assets, statuses, and button names
* **Optional testnet support** and configurable request timeout
* **FastAPI webhook example** to bootstrap integrations
* **Comprehensive error handling** with custom exception classes

## Quick Example

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

## Contents

```{toctree}
:maxdepth: 2
:caption: User Guide

installation
usage
examples
```

```{toctree}
:maxdepth: 2
:caption: Advanced Topics

advanced
webhook_security
troubleshooting
```

```{toctree}
:maxdepth: 2
:caption: API Reference

modules
```

```{toctree}
:maxdepth: 1
:caption: Development

contributing
TRANSLATING
authors
history
```

## Indices and Tables

* {ref}`genindex`
* {ref}`modindex`
* {ref}`search`
