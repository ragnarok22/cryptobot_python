# Usage

## Quick Start

To use CryptoBot Python in a project, first import the client and models:

```python
from cryptobot import CryptoBotClient
from cryptobot.models import Asset
```

Create a client instance with your API token:

```python
client = CryptoBotClient("YOUR_API_TOKEN")
```

## Basic Operations

### Creating an Invoice

Create a simple invoice for cryptocurrency payment:

```python
invoice = client.create_invoice(
    asset=Asset.USDT,
    amount=5.25,
    description="Coffee order #42"
)

print(f"Invoice URL: {invoice.bot_invoice_url}")
print(f"Invoice ID: {invoice.invoice_id}")
```

### Creating an Invoice with Custom Options

Create an invoice with additional parameters:

```python
invoice = client.create_invoice(
    asset=Asset.BTC,
    amount=0.001,
    description="Premium service subscription",
    paid_btn_name="callback",  # Button name for paid invoice
    paid_btn_url="https://example.com/success",  # URL for success callback
    payload="user_123_premium",  # Custom payload for tracking
    allow_comments=True,  # Allow user comments
    allow_anonymous=False,  # Require user identification
    expires_in=3600  # Expire after 1 hour
)
```

### Making Transfers

Transfer cryptocurrency to another user:

```python
try:
    transfer = client.transfer(
        user_id=12345,
        asset=Asset.TON,
        amount=0.5,
        spend_id="transfer_001",  # Unique spend ID to prevent duplicates
        comment="Payment for services"
    )
    print(f"Transfer completed: {transfer.transfer_id}")
except CryptoBotError as e:
    print(f"Transfer failed: {e.name} - {e.description}")
```

### Checking Balances

Get your current balances:

```python
balances = client.get_balances()
for balance in balances:
    print(f"{balance.currency_code}: {balance.available}")
```

### Getting Exchange Rates

Retrieve current exchange rates:

```python
rates = client.get_exchange_rates()
for rate in rates:
    print(f"1 {rate.source} = {rate.rate} {rate.target}")
```

### Getting Invoice Information

Retrieve information about existing invoices:

```python
# Get all invoices
invoices = client.get_invoices()

# Get invoices with filters
paid_invoices = client.get_invoices(
    asset=Asset.USDT,
    invoice_ids=["INV123", "INV456"],
    status="paid",
    offset=0,
    count=50
)
```

## Environment Configuration

### Testnet vs Mainnet

By default, the client uses the mainnet environment. To use testnet:

```python
client = CryptoBotClient("YOUR_TESTNET_TOKEN", testnet=True)
```

### Custom Timeout

Configure request timeout (default is 30 seconds):

```python
client = CryptoBotClient("YOUR_API_TOKEN", timeout=60)
```

## Error Handling

All API errors raise {class}`cryptobot.errors.CryptoBotError`:

```python
from cryptobot.errors import CryptoBotError

try:
    client.transfer(user_id=12345, asset=Asset.BTC, amount=10, spend_id="test")
except CryptoBotError as exc:
    print(f"Error code: {exc.code}")
    print(f"Error name: {exc.name}")
    print(f"Description: {exc.description}")
```

## Webhook Integration

### Using the Built-in Webhook Server

CryptoBot Python includes a FastAPI-based webhook server for handling payment notifications:

```python
from cryptobot.webhook import app
import uvicorn

# Run the webhook server
uvicorn.run(app, host="0.0.0.0", port=8000)
```

The webhook server automatically handles signature verification and provides a colorful startup banner.

### Custom Webhook Handler

You can also create your own webhook handler:

```python
from fastapi import FastAPI, Request, HTTPException
import hmac
import hashlib

app = FastAPI()

@app.post("/webhook")
async def webhook_handler(request: Request):
    # Get the signature from headers
    signature = request.headers.get("crypto-pay-api-signature")

    # Read the request body
    body = await request.body()

    # Verify signature (replace with your webhook secret)
    secret_key = "YOUR_WEBHOOK_SECRET"
    expected_signature = hmac.new(
        secret_key.encode(), body, hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(signature, expected_signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Process the webhook data
    # ...

    return {"status": "ok"}
```

## Available Assets

The library supports the following cryptocurrencies:

```python
from cryptobot.models import Asset

# Available assets
Asset.BTC     # Bitcoin
Asset.TON     # Toncoin
Asset.ETH     # Ethereum
Asset.USDT    # Tether
Asset.USDC    # USD Coin
Asset.BNB     # Binance Coin
```

## Best Practices

1. **Always handle exceptions** when making API calls
2. **Use unique spend_ids** for transfers to prevent duplicates
3. **Validate user input** before creating invoices or transfers
4. **Store API tokens securely** using environment variables
5. **Use testnet for development** and testing
6. **Implement proper webhook signature verification** for security
7. **Set appropriate invoice expiration times** to avoid stale invoices
