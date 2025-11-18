# Troubleshooting Guide

This guide helps you resolve common issues when using CryptoBot Python.

## Authentication Issues

### Invalid API Token

**Problem:** Getting authentication errors when making API calls.

```python
CryptoBotError: code=401, name="UNAUTHORIZED"
```

**Solutions:**

1. **Verify your token is correct:**
   ```python
   from cryptobot import CryptoBotClient

   client = CryptoBotClient("YOUR_API_TOKEN")
   try:
       app = client.get_me()
       print(f"Connected successfully as: {app.name}")
   except Exception as e:
       print(f"Authentication failed: {e}")
   ```

2. **Check environment variables:**
   ```python
   import os

   token = os.getenv("CRYPTOBOT_TOKEN")
   if not token:
       print("ERROR: CRYPTOBOT_TOKEN environment variable not set")
   ```

3. **Verify you're using the correct token for the environment:**
   - Mainnet tokens start with specific prefixes
   - Testnet tokens are different from mainnet tokens
   - Don't mix testnet and mainnet tokens

### Wrong Environment (Mainnet vs Testnet)

**Problem:** API calls fail because you're using a testnet token with mainnet client or vice versa.

**Solution:**

```python
from cryptobot import CryptoBotClient

# For testnet
testnet_client = CryptoBotClient("YOUR_TESTNET_TOKEN", is_mainnet=False)

# For mainnet
mainnet_client = CryptoBotClient("YOUR_MAINNET_TOKEN", is_mainnet=True)

# Verify environment
try:
    app = testnet_client.get_me()
    print("Successfully connected to testnet")
except Exception as e:
    print(f"Testnet connection failed: {e}")
```

## Invoice Issues

### Minimum Amount Errors

**Problem:** Invoice creation fails with amount too small error.

```python
CryptoBotError: code=400, name="AMOUNT_TOO_SMALL"
```

**Solution:** Each cryptocurrency has a minimum amount. Check supported minimums:

```python
from cryptobot import CryptoBotClient
from cryptobot.models import Asset

client = CryptoBotClient("YOUR_API_TOKEN")

# Get currency information
currencies = client.get_currencies()

# Display minimum amounts (typically based on network fees)
minimum_amounts = {
    Asset.BTC: 0.000001,   # 1 satoshi
    Asset.TON: 0.01,       # 0.01 TON
    Asset.ETH: 0.000001,   # 1 gwei
    Asset.USDT: 0.01,      # $0.01
    Asset.USDC: 0.01,      # $0.01
    Asset.BNB: 0.001,      # 0.001 BNB
}

# Always check minimum before creating invoice
asset = Asset.USDT
amount = 0.001  # Too small

if amount < minimum_amounts[asset]:
    print(f"Amount too small. Minimum for {asset.name}: {minimum_amounts[asset]}")
else:
    invoice = client.create_invoice(asset=asset, amount=amount, description="Test")
```

### Invoice Expiration

**Problem:** Invoice expires before payment is completed.

**Solutions:**

1. **Set appropriate expiration time:**
   ```python
   # Set longer expiration (in seconds)
   invoice = client.create_invoice(
       asset=Asset.USDT,
       amount=10.0,
       description="Test",
       expires_in=3600  # 1 hour instead of default
   )
   ```

2. **Check invoice status regularly:**
   ```python
   from cryptobot.models import Status

   invoices = client.get_invoices(invoice_ids=str(invoice.invoice_id))
   if invoices:
       invoice = invoices[0]
       if invoice.status == Status.expired:
           # Create a new invoice
           new_invoice = client.create_invoice(
               asset=Asset.USDT,
               amount=10.0,
               description="Replacement invoice"
           )
   ```

3. **Implement invoice renewal:**
   ```python
   def renew_expired_invoice(client, old_invoice):
       """Create a new invoice with the same parameters"""
       return client.create_invoice(
           asset=old_invoice.asset,
           amount=float(old_invoice.amount),
           description=old_invoice.description,
           payload=old_invoice.payload,
           expires_in=3600
       )
   ```

### Invoice Not Found

**Problem:** Can't retrieve invoice after creation.

**Solution:**

```python
import time

# Wait a moment after creation
invoice = client.create_invoice(
    asset=Asset.USDT,
    amount=10.0,
    description="Test"
)

# Give the API a moment to index the invoice
time.sleep(1)

# Retrieve invoice
invoices = client.get_invoices(invoice_ids=str(invoice.invoice_id))
if not invoices:
    print("Invoice not found yet, trying again...")
    time.sleep(2)
    invoices = client.get_invoices(invoice_ids=str(invoice.invoice_id))
```

## Transfer Issues

### Insufficient Balance

**Problem:** Transfer fails due to insufficient funds.

```python
CryptoBotError: code=400, name="INSUFFICIENT_FUNDS"
```

**Solution:**

```python
from cryptobot.models import Asset
from decimal import Decimal

def can_transfer(client, asset, amount):
    """Check if transfer is possible"""
    balances = client.get_balances()

    for balance in balances:
        if balance.currency_code == asset.name:
            available = Decimal(balance.available)
            required = Decimal(str(amount))

            if available >= required:
                return True, f"Available: {available}"
            else:
                return False, f"Insufficient funds. Available: {available}, Required: {required}"

    return False, f"Asset {asset.name} not found in balances"

# Check before transfer
asset = Asset.USDT
amount = 100.0

can_proceed, message = can_transfer(client, asset, amount)
if can_proceed:
    transfer = client.transfer(
        user_id=12345,
        asset=asset,
        amount=amount,
        spend_id="unique_id"
    )
else:
    print(f"Cannot transfer: {message}")
```

### Duplicate spend_id

**Problem:** Transfer fails due to duplicate spend_id.

```python
CryptoBotError: code=400, name="SPEND_ID_ALREADY_USED"
```

**Solution:** Always use unique spend_ids:

```python
import uuid
from datetime import datetime

def generate_unique_spend_id(user_id, purpose=""):
    """Generate a unique spend ID"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    return f"{purpose}_{user_id}_{timestamp}_{unique_id}"

# Usage
spend_id = generate_unique_spend_id(12345, "PAYOUT")
transfer = client.transfer(
    user_id=12345,
    asset=Asset.USDT,
    amount=10.0,
    spend_id=spend_id
)
```

### Invalid User ID

**Problem:** Transfer fails because user hasn't interacted with CryptoBot.

**Solution:**

```python
from cryptobot.errors import CryptoBotError

def safe_transfer(client, user_id, asset, amount, spend_id):
    """Transfer with error handling"""
    try:
        return client.transfer(
            user_id=user_id,
            asset=asset,
            amount=amount,
            spend_id=spend_id,
            comment="Payment"
        )
    except CryptoBotError as e:
        if "USER_NOT_FOUND" in e.name or "INVALID_USER" in e.name:
            # User hasn't started the bot
            return {
                "success": False,
                "error": "User must start @CryptoBot first",
                "user_id": user_id
            }
        raise

# Usage
result = safe_transfer(client, 12345, Asset.USDT, 10.0, "unique_spend_id")
```

## Connection Issues

### Timeout Errors

**Problem:** API requests are timing out.

**Solution:**

```python
from cryptobot import CryptoBotClient
import httpx

# Increase timeout
client = CryptoBotClient("YOUR_API_TOKEN", timeout=60.0)

# Or handle timeouts gracefully
try:
    invoice = client.create_invoice(
        asset=Asset.USDT,
        amount=10.0,
        description="Test"
    )
except httpx.TimeoutException:
    print("Request timed out, please try again")
```

### Connection Errors

**Problem:** Can't connect to the API.

**Solution:**

```python
import httpx
from cryptobot.errors import CryptoBotError

def create_invoice_with_retry(client, max_retries=3, **kwargs):
    """Create invoice with retry logic"""
    for attempt in range(max_retries):
        try:
            return client.create_invoice(**kwargs)
        except httpx.ConnectError as e:
            if attempt < max_retries - 1:
                print(f"Connection failed, retrying... ({attempt + 1}/{max_retries})")
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                raise Exception("Failed to connect after multiple attempts")

# Usage
invoice = create_invoice_with_retry(
    client,
    asset=Asset.USDT,
    amount=10.0,
    description="Resilient invoice"
)
```

## Webhook Issues

### Signature Verification Fails

**Problem:** Webhook signature verification always fails.

**Solution:**

```python
import hmac
import hashlib

def debug_webhook_signature(body: bytes, signature: str, secret: str):
    """Debug webhook signature verification"""
    # Calculate expected signature
    expected = hmac.new(
        secret.encode(),
        body,
        hashlib.sha256
    ).hexdigest()

    print(f"Received signature: {signature}")
    print(f"Expected signature: {expected}")
    print(f"Match: {hmac.compare_digest(signature, expected)}")

    # Check common issues
    if not signature:
        print("ERROR: No signature in headers")
    elif len(signature) != 64:
        print("ERROR: Signature has wrong length")
    elif not secret:
        print("ERROR: Webhook secret not configured")

    return hmac.compare_digest(signature, expected)
```

### Webhooks Not Received

**Problem:** Webhook endpoint not receiving notifications.

**Checklist:**

1. **Verify webhook URL is publicly accessible:**
   ```bash
   curl https://your-domain.com/webhook
   ```

2. **Check webhook is configured in CryptoBot:**
   - Go to @CryptoBot in Telegram
   - Configure webhook URL
   - Verify HTTPS is used (required)

3. **Test webhook locally with ngrok:**
   ```bash
   # Install ngrok
   # Run your app
   uvicorn cryptobot.webhook:app --port 8000

   # In another terminal
   ngrok http 8000
   # Use the ngrok HTTPS URL as your webhook URL
   ```

4. **Check server logs:**
   ```python
   import logging

   logging.basicConfig(level=logging.DEBUG)

   @app.post("/webhook")
   async def webhook_handler(request: Request):
       logging.info(f"Received webhook: {request.headers}")
       # ... rest of handler
   ```

## Data Parsing Issues

### Enum Value Errors

**Problem:** Can't parse asset or status from string.

**Solution:**

```python
from cryptobot.models import Asset, Status

def parse_asset_safely(asset_string):
    """Parse asset string to enum"""
    try:
        return Asset[asset_string.upper()]
    except KeyError:
        # Handle unknown asset
        print(f"Unknown asset: {asset_string}")
        return None

def parse_status_safely(status_string):
    """Parse status string to enum"""
    try:
        return Status[status_string.lower()]
    except KeyError:
        print(f"Unknown status: {status_string}")
        return None

# Usage
asset_str = "usdt"
asset = parse_asset_safely(asset_str)

if asset:
    invoice = client.create_invoice(
        asset=asset,
        amount=10.0,
        description="Test"
    )
```

### Decimal Precision Issues

**Problem:** Floating point precision errors with amounts.

**Solution:**

```python
from decimal import Decimal

# Use Decimal for precise calculations
amount = Decimal("10.123456789")

# Convert to string for API
invoice = client.create_invoice(
    asset=Asset.USDT,
    amount=float(amount),  # API accepts float
    description="Precise amount"
)

# Parse amounts from API as Decimal
if invoice.status == Status.paid:
    paid_amount = Decimal(invoice.paid_amount)
    print(f"Received: {paid_amount}")
```

## Rate Limiting

### Too Many Requests

**Problem:** Getting rate limit errors.

```python
CryptoBotError: code=429, name="TOO_MANY_REQUESTS"
```

**Solution:**

```python
import time
from cryptobot.errors import CryptoBotError

def api_call_with_rate_limit(func, *args, **kwargs):
    """Execute API call with rate limit handling"""
    max_retries = 3
    base_delay = 1

    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except CryptoBotError as e:
            if e.code == 429:  # Rate limit
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    print(f"Rate limited, waiting {delay} seconds...")
                    time.sleep(delay)
                else:
                    raise
            else:
                raise

# Usage
invoice = api_call_with_rate_limit(
    client.create_invoice,
    asset=Asset.USDT,
    amount=10.0,
    description="Test"
)
```

## Testing Issues

### Testing with Testnet

**Problem:** Need to test without using real money.

**Solution:**

```python
import os
from cryptobot import CryptoBotClient
from cryptobot.models import Asset

# Use environment variable to switch environments
is_production = os.getenv("ENV") == "production"

if is_production:
    client = CryptoBotClient(
        os.getenv("CRYPTOBOT_MAINNET_TOKEN"),
        is_mainnet=True
    )
else:
    # Use testnet for development
    client = CryptoBotClient(
        os.getenv("CRYPTOBOT_TESTNET_TOKEN"),
        is_mainnet=False
    )

# Your code works the same way
invoice = client.create_invoice(
    asset=Asset.USDT,
    amount=10.0,
    description="Test invoice"
)
```

### Mocking for Unit Tests

**Problem:** Want to run tests without API calls.

**Solution:**

```python
from unittest.mock import Mock, patch
from cryptobot.models import Invoice, Asset, Status

def test_invoice_processing():
    """Test invoice processing without API calls"""
    # Create mock client
    mock_client = Mock()

    # Configure mock response
    mock_invoice = Invoice(
        invoice_id=12345,
        status=Status.paid,
        hash="test_hash",
        amount="10.0",
        asset=Asset.USDT,
        bot_invoice_url="https://t.me/test"
    )
    mock_client.create_invoice.return_value = mock_invoice

    # Your code using the mock
    invoice = mock_client.create_invoice(
        asset=Asset.USDT,
        amount=10.0,
        description="Test"
    )

    assert invoice.invoice_id == 12345
    assert invoice.status == Status.paid
```

## Debugging Tips

### Enable Debug Logging

```python
import logging
import httpx

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Enable httpx debug logs
httpx_logger = logging.getLogger("httpx")
httpx_logger.setLevel(logging.DEBUG)

# Now all API calls will be logged
client = CryptoBotClient("YOUR_API_TOKEN")
invoice = client.create_invoice(asset=Asset.USDT, amount=10.0, description="Debug")
```

### Inspect API Responses

```python
import httpx
from cryptobot import CryptoBotClient

class DebugCryptoBotClient(CryptoBotClient):
    """Client with response debugging"""

    def create_invoice(self, **kwargs):
        """Create invoice with response logging"""
        print(f"Request: {kwargs}")

        try:
            invoice = super().create_invoice(**kwargs)
            print(f"Response: {invoice}")
            return invoice
        except Exception as e:
            print(f"Error: {e}")
            raise

# Usage
debug_client = DebugCryptoBotClient("YOUR_API_TOKEN")
invoice = debug_client.create_invoice(
    asset=Asset.USDT,
    amount=10.0,
    description="Debug invoice"
)
```

## Getting Help

If you're still experiencing issues:

1. **Check the API documentation:** https://help.crypt.bot/crypto-pay-api
2. **Review the examples:** See [Examples](examples.md) for working code
3. **Check GitHub issues:** https://github.com/ragnarok22/cryptobot_python/issues
4. **Ask in Telegram:** Join the CryptoBot support channel
5. **Enable debug logging** to see detailed error messages

## Common Error Codes

| Code | Name | Description | Solution |
|------|------|-------------|----------|
| 400 | BAD_REQUEST | Invalid parameters | Check parameter types and values |
| 401 | UNAUTHORIZED | Invalid API token | Verify your API token |
| 404 | NOT_FOUND | Resource not found | Check invoice/transfer IDs |
| 429 | TOO_MANY_REQUESTS | Rate limit exceeded | Implement rate limiting |
| 500 | INTERNAL_ERROR | Server error | Retry with exponential backoff |

## Best Practices to Avoid Issues

1. **Always handle exceptions** properly
2. **Use unique spend_ids** for all transfers
3. **Implement retry logic** for transient failures
4. **Set appropriate timeouts** based on your use case
5. **Use testnet for development** and testing
6. **Validate user input** before API calls
7. **Log all API interactions** for debugging
8. **Monitor rate limits** and implement backoff
9. **Keep your library updated** to the latest version
10. **Read error messages carefully** - they usually explain the issue
