# Welcome to CryptoBot Python

CryptoBot Python is an unofficial, friendly client library for the [Crypto Bot](https://pay.crypt.bot/) API.
It provides typed models and a synchronous client for invoices, transfers, balances, exchange rates, and webhook handling.

## Highlights

- Synchronous API client built on `httpx`
- Dataclass response models (`Invoice`, `Transfer`, `Balance`, `ExchangeRate`, `Currency`)
- Enum safety for assets, statuses, and paid button names
- Mainnet/testnet support with configurable timeout
- FastAPI webhook listener with signature verification
- Structured API errors via `CryptoBotError` (`code`, `name`)

## Quick Example

```python
import os

from cryptobot import CryptoBotClient
from cryptobot.models import Asset

client = CryptoBotClient(api_token=os.environ["CRYPTOBOT_API_TOKEN"])

app = client.get_me()
print(app.name)

invoice = client.create_invoice(
    asset=Asset.USDT,
    amount=5.25,
    description="Coffee order #42",
)
print(invoice.invoice_id, invoice.bot_invoice_url)
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
:caption: Production Guides

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

- {ref}`genindex`
- {ref}`modindex`
- {ref}`search`
