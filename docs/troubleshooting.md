# Troubleshooting Guide

This guide covers common integration problems and concrete fixes.

## Authentication Errors

### Symptom

```text
CryptoBotError: code=401, name=UNAUTHORIZED
```

### Checks

```python
import os

from cryptobot import CryptoBotClient
from cryptobot.models import Asset

client = CryptoBotClient(api_token=os.environ["CRYPTOBOT_API_TOKEN"])
print(client.get_me().name)
```

If that fails:

1. Confirm token is present and non-empty.
2. Confirm the token belongs to the intended environment.
3. If using testnet token, set `is_mainnet=False`.

## Mainnet vs Testnet Mismatch

```python
import os

from cryptobot import CryptoBotClient

mainnet = CryptoBotClient(api_token=os.environ["CRYPTOBOT_API_TOKEN"], is_mainnet=True)
testnet = CryptoBotClient(api_token=os.environ["CRYPTOBOT_TESTNET_TOKEN"], is_mainnet=False)
```

Use one token per environment and do not mix them.

## Amount Validation Failures

### Symptom

```text
CryptoBotError: code=400, name=AMOUNT_TOO_SMALL
```

### Fix

Validate amount before API calls:

```python
from decimal import Decimal

from cryptobot.models import Asset


MIN_AMOUNTS = {
    Asset.USDT: Decimal("0.01"),
    Asset.USDC: Decimal("0.01"),
    Asset.TON: Decimal("0.01"),
    Asset.BTC: Decimal("0.000001"),
}


def validate_amount(asset: Asset, amount: float):
    value = Decimal(str(amount))
    minimum = MIN_AMOUNTS.get(asset)
    if minimum is not None and value < minimum:
        raise ValueError(f"Amount too small for {asset.name}. Minimum is {minimum}")
```

## Invoice Status Not Updating

If an invoice appears stuck:

1. Query by invoice ID.
2. Check for `Status.paid` or `Status.expired`.
3. Create a replacement invoice if expired.

```python
from cryptobot.models import Asset, Status


def refresh_invoice(client, invoice_id: int):
    invoices = client.get_invoices(invoice_ids=str(invoice_id))
    return invoices[0] if invoices else None


def renew_if_expired(client, invoice):
    if invoice.status != Status.expired:
        return invoice

    return client.create_invoice(
        asset=invoice.asset,
        amount=float(invoice.amount),
        description=invoice.description,
        payload=invoice.payload,
        expires_in=3600,
    )
```

## Transfer Problems

### Insufficient balance

```text
CryptoBotError: code=400, name=INSUFFICIENT_FUNDS
```

```python
from decimal import Decimal


def has_balance(client, asset, amount: float) -> bool:
    required = Decimal(str(amount))
    for bal in client.get_balances():
        if bal.currency_code == asset.name:
            return Decimal(bal.available) >= required
    return False
```

### Duplicate `spend_id`

```text
CryptoBotError: code=400, name=SPEND_ID_ALREADY_USED
```

```python
from datetime import datetime
import uuid


def unique_spend_id(prefix: str, user_id: int) -> str:
    return f"{prefix}_{user_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"
```

## Timeout and Connection Issues

Increase timeout and enable built-in retry/backoff for transient transport errors:

```python
import os

from cryptobot import CryptoBotClient

client = CryptoBotClient(
    api_token=os.environ["CRYPTOBOT_API_TOKEN"],
    timeout=30.0,
    max_retries=3,
    retry_backoff=0.5,
)

invoice = client.create_invoice(asset=Asset.USDT, amount=5, description="network-safe")
```

## Webhook Signature Failures

Most signature bugs come from verifying parsed JSON instead of the raw body.

```python
import json
import os

from fastapi import FastAPI, HTTPException, Request

from cryptobot.webhook import check_signature

app = FastAPI()
api_token = os.environ["CRYPTOBOT_API_TOKEN"]


@app.post("/webhook")
async def webhook(request: Request):
    raw = await request.body()
    raw_str = raw.decode("utf-8")

    if not check_signature(api_token, raw_str, request.headers):
        raise HTTPException(status_code=400, detail="Invalid signature")

    data = json.loads(raw_str)
    return {"ok": True, "update_type": data.get("update_type")}
```

## Webhooks Not Received

Checklist:

1. Endpoint is publicly reachable over HTTPS.
2. Webhook URL in Crypto Bot is correct.
3. Your service is listening on expected path/port.
4. Reverse proxy forwards request body and headers unchanged.

For local tests, run your listener script and expose it with ngrok:

```bash
ngrok http 2203
```

## Enum Parsing Errors

When converting user input to enums, normalize and validate:

```python
from cryptobot.models import Asset, Status


def parse_asset(text: str) -> Asset:
    try:
        return Asset[text.upper()]
    except KeyError as exc:
        raise ValueError(f"Unsupported asset: {text}") from exc


def parse_status(text: str) -> Status:
    try:
        return Status[text.lower()]
    except KeyError as exc:
        raise ValueError(f"Unsupported status: {text}") from exc
```

## Rate Limit Errors

### Symptom

```text
CryptoBotError: code=429, name=TOO_MANY_REQUESTS
```

### Fix

```python
import os

from cryptobot import CryptoBotClient

client = CryptoBotClient(
    api_token=os.environ["CRYPTOBOT_API_TOKEN"],
    max_retries=4,
    retry_backoff=0.5,
    retryable_status_codes={429},
)

app = client.get_me()
print(app.name)
```

## Testnet Smoke Test

```python
import os

from cryptobot import CryptoBotClient
from cryptobot.models import Asset


def smoke_test() -> bool:
    client = CryptoBotClient(
        api_token=os.environ["CRYPTOBOT_TESTNET_TOKEN"],
        is_mainnet=False,
    )

    try:
        client.get_me()
        client.get_balances()
        client.get_exchange_rates()
        client.create_invoice(asset=Asset.USDT, amount=1, description="smoke")
        return True
    except Exception:
        return False
```

## Getting Help

1. [Crypto Bot API docs](https://help.crypt.bot/crypto-pay-api)
2. [Examples](examples)
3. [Advanced Topics](advanced)
4. [GitHub issues](https://github.com/ragnarok22/cryptobot_python/issues)
