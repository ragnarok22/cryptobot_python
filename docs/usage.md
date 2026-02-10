# Usage

## Quick Start

Import the client, core models, and error types:

```python
import os

from cryptobot import CryptoBotClient
from cryptobot.errors import CryptoBotError
from cryptobot.models import Asset, ButtonName, Status
```

Create a client instance with your API token:

```python
client = CryptoBotClient(
    api_token=os.environ["CRYPTOBOT_API_TOKEN"],
    is_mainnet=True,
    timeout=5.0,
)
```

## Basic Operations

### Getting App Information

Get basic information about your app:

```python
app = client.get_me()
print(f"App ID: {app.app_id}")
print(f"App Name: {app.name}")
print(f"Bot Username: {app.payment_processing_bot_username}")
```

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
    paid_btn_name=ButtonName.callback,  # Enum value for paid invoice button
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
    print(f"Transfer failed: {e.code} - {e.name}")
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

You can also filter for specific currencies:

```python
# Find USD exchange rate for Bitcoin
btc_usd_rate = next((r for r in rates if r.source.name == "BTC" and r.target == "USD"), None)
if btc_usd_rate:
    print(f"1 BTC = ${btc_usd_rate.rate} USD")
```

### Getting Supported Currencies

Get information about all supported currencies:

```python
currencies = client.get_currencies()
for currency in currencies:
    print(f"{currency.name} ({currency.code})")
    print(f"  Blockchain: {currency.is_blockchain}")
    print(f"  Stablecoin: {currency.is_stablecoin}")
    print(f"  Decimals: {currency.decimals}")
    if currency.url:
        print(f"  URL: {currency.url}")
```

Filter by type:

```python
# Get only blockchain currencies
blockchain_currencies = [c for c in currencies if c.is_blockchain]

# Get only stablecoins
stablecoins = [c for c in currencies if c.is_stablecoin]

# Get only fiat currencies
fiat_currencies = [c for c in currencies if c.is_fiat]
```

### Getting Invoice Information

Retrieve information about existing invoices:

```python
# Get all invoices
invoices = client.get_invoices()

# Get invoices with filters
paid_invoices = client.get_invoices(
    asset=Asset.USDT,
    invoice_ids="123,456",
    status=Status.paid,
    offset=0,
    count=50
)
```

## Environment Configuration

### Testnet vs Mainnet

By default, the client uses the mainnet environment. To target the testnet (with a testnet token), set `is_mainnet=False`:

```python
client = CryptoBotClient(os.environ["CRYPTOBOT_TESTNET_TOKEN"], is_mainnet=False)
```

### Custom Timeout

Configure request timeout (default is 5 seconds):

```python
client = CryptoBotClient(os.environ["CRYPTOBOT_API_TOKEN"], timeout=60)
```

### Swap Incoming Payments

Automatically convert payments to a different asset by using `swap_to`:

```python
invoice = client.create_invoice(
    asset=Asset.TON,
    amount=20,
    description="Swap TON to USDT on receipt",
    swap_to="USDT",
)
print(invoice.bot_invoice_url)
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
```

## Webhook Integration

### Using the Built-in Webhook Server

CryptoBot Python includes a FastAPI-based webhook listener for handling payment notifications:

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

The listener automatically verifies signatures and provides a startup banner.

### Custom Webhook Handler

You can also create your own webhook handler and verify signatures with `check_signature`:

```python
import json
import os

from cryptobot.webhook import check_signature
from fastapi import FastAPI, Request, HTTPException

app = FastAPI()
api_token = os.environ["CRYPTOBOT_API_TOKEN"]

@app.post("/webhook")
async def webhook_handler(request: Request):
    # Read the raw body first (required for signature verification)
    raw_body = await request.body()
    raw_body_str = raw_body.decode("utf-8")

    if not check_signature(api_token, raw_body_str, request.headers):
        raise HTTPException(status_code=400, detail="Invalid signature")

    data = json.loads(raw_body_str)
    # Process the verified webhook data
    # ...

    return {"ok": True}
```

## Available Assets

The library supports these assets (see {class}`cryptobot.models.Asset` for the canonical list):

```python
from cryptobot.models import Asset

# Available assets
Asset.BTC     # Bitcoin
Asset.TON     # Toncoin
Asset.ETH     # Ethereum
Asset.USDT    # Tether
Asset.USDC    # USD Coin
Asset.BUSD    # Binance USD
Asset.BNB     # Binance Coin
Asset.TRX     # TRON
```

## Advanced Patterns

### Pagination with get_invoices

When dealing with many invoices, use pagination to retrieve them in batches:

```python
def get_all_paid_invoices(client, asset=None):
    """Retrieve all paid invoices using pagination"""
    all_invoices = []
    offset = 0
    batch_size = 100

    while True:
        batch = client.get_invoices(
            asset=asset,
            status=Status.paid,
            offset=offset,
            count=batch_size
        )

        if not batch:
            break

        all_invoices.extend(batch)
        offset += batch_size

        # If we got fewer than batch_size, we're done
        if len(batch) < batch_size:
            break

    return all_invoices

# Usage
paid_invoices = get_all_paid_invoices(client, asset=Asset.USDT)
print(f"Total paid invoices: {len(paid_invoices)}")
```

### Invoice Status Checking

Create a helper function to check invoice status:

```python
def wait_for_payment(client, invoice_id, max_attempts=60, delay=5):
    """Poll invoice status until paid or timeout"""
    import time

    for attempt in range(max_attempts):
        invoices = client.get_invoices(invoice_ids=str(invoice_id))
        if invoices and invoices[0].status == Status.paid:
            return invoices[0]

        if invoices and invoices[0].status == Status.expired:
            raise Exception("Invoice expired")

        time.sleep(delay)

    raise TimeoutError("Payment timeout")

# Usage
invoice = client.create_invoice(asset=Asset.USDT, amount=10)
print(f"Waiting for payment: {invoice.bot_invoice_url}")

try:
    paid_invoice = wait_for_payment(client, invoice.invoice_id)
    print(f"Payment received! Amount: {paid_invoice.paid_amount}")
except Exception as e:
    print(f"Payment failed: {e}")
```

### Calculating Total Revenue

Calculate total revenue from paid invoices:

```python
from decimal import Decimal

def calculate_revenue(client, asset=None):
    """Calculate total revenue from paid invoices"""
    invoices = client.get_invoices(status=Status.paid, asset=asset)

    revenue_by_asset = {}
    for invoice in invoices:
        asset_name = invoice.paid_asset or invoice.asset.name
        amount = Decimal(invoice.paid_amount or invoice.amount)

        if asset_name in revenue_by_asset:
            revenue_by_asset[asset_name] += amount
        else:
            revenue_by_asset[asset_name] = amount

    return revenue_by_asset

# Usage
revenue = calculate_revenue(client)
for asset, total in revenue.items():
    print(f"{asset}: {total}")
```

### Multi-Currency Pricing

Create invoices that allow users to pay in different currencies:

```python
def create_flexible_invoice(client, amount_usd, description):
    """Create an invoice with multiple payment options"""
    # Get exchange rates
    rates = client.get_exchange_rates()

    # Find cryptocurrencies and their rates
    available_assets = [Asset.USDT, Asset.BTC, Asset.ETH, Asset.TON]

    # Create invoice (USDT is 1:1 with USD for simplicity)
    invoice = client.create_invoice(
        asset=Asset.USDT,
        amount=amount_usd,
        description=description,
        allow_comments=True,
        expires_in=3600  # 1 hour
    )

    # Show equivalent amounts in other currencies
    print(f"Invoice created: {invoice.bot_invoice_url}")
    print(f"\nPayment options:")
    print(f"  USDT: ${amount_usd}")

    for rate in rates:
        if rate.target == "USD" and any(a.name == rate.source.name for a in available_assets):
            crypto_amount = amount_usd / float(rate.rate)
            print(f"  {rate.source.name}: {crypto_amount:.8f}")

    return invoice

# Usage
invoice = create_flexible_invoice(client, 50.0, "Premium subscription")
```

## Best Practices

1. **Always handle exceptions** when making API calls
2. **Use unique spend_ids** for transfers to prevent duplicates
3. **Validate user input** before creating invoices or transfers
4. **Store API tokens securely** using environment variables
5. **Use a dedicated testnet token** with `is_mainnet=False` during development
6. **Implement proper webhook signature verification** for security
7. **Set appropriate invoice expiration times** to avoid stale invoices
8. **Use pagination** when retrieving large numbers of invoices
9. **Check invoice status** before processing orders
10. **Log all transactions** for audit trails and debugging
