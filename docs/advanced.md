# Advanced Topics

This guide covers advanced patterns, optimizations, and best practices for production deployments.

## Connection Management

### Custom HTTP Client Configuration

Configure the underlying httpx client for production use:

```python
import httpx
from cryptobot import CryptoBotClient

# Create a custom client with connection pooling
class ProductionCryptoBotClient(CryptoBotClient):
    def __init__(self, api_token, is_mainnet=True, timeout=30.0, max_connections=100):
        super().__init__(api_token, is_mainnet, timeout)

        # Override the HTTP client with custom settings
        self._CryptoBotClient__http_client = httpx.Client(
            base_url=self._CryptoBotClient__base_url,
            timeout=timeout,
            headers={"Crypto-Pay-API-Token": self.api_token},
            limits=httpx.Limits(
                max_keepalive_connections=max_connections,
                max_connections=max_connections,
                keepalive_expiry=30.0
            )
        )

# Usage
client = ProductionCryptoBotClient(
    "YOUR_API_TOKEN",
    timeout=60.0,
    max_connections=50
)
```

### Retry Logic with Exponential Backoff

Implement robust retry logic for transient failures:

```python
import time
from cryptobot import CryptoBotClient
from cryptobot.errors import CryptoBotError

class ResilientClient:
    def __init__(self, api_token, max_retries=3):
        self.client = CryptoBotClient(api_token)
        self.max_retries = max_retries

    def _retry_with_backoff(self, func, *args, **kwargs):
        """Execute function with exponential backoff retry"""
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except CryptoBotError as e:
                # Only retry on server errors (5xx) or rate limits
                if e.code >= 500 or e.code == 429:
                    if attempt < self.max_retries - 1:
                        wait_time = (2 ** attempt) + (0.1 * attempt)
                        time.sleep(wait_time)
                        continue
                raise

    def create_invoice(self, **kwargs):
        """Create invoice with retry logic"""
        return self._retry_with_backoff(
            self.client.create_invoice,
            **kwargs
        )

    def transfer(self, **kwargs):
        """Transfer with retry logic"""
        return self._retry_with_backoff(
            self.client.transfer,
            **kwargs
        )

# Usage
resilient_client = ResilientClient("YOUR_API_TOKEN", max_retries=3)
invoice = resilient_client.create_invoice(
    asset=Asset.USDT,
    amount=10.0,
    description="Resilient invoice"
)
```

## Rate Limiting

### Token Bucket Rate Limiter

Implement rate limiting to avoid API throttling:

```python
import time
import threading
from cryptobot import CryptoBotClient
from cryptobot.models import Asset

class RateLimitedClient:
    def __init__(self, api_token, requests_per_second=10):
        self.client = CryptoBotClient(api_token)
        self.requests_per_second = requests_per_second
        self.tokens = requests_per_second
        self.max_tokens = requests_per_second
        self.last_update = time.time()
        self.lock = threading.Lock()

    def _acquire_token(self):
        """Acquire a token using token bucket algorithm"""
        with self.lock:
            now = time.time()
            elapsed = now - self.last_update

            # Add tokens based on elapsed time
            self.tokens = min(
                self.max_tokens,
                self.tokens + elapsed * self.requests_per_second
            )
            self.last_update = now

            if self.tokens < 1:
                # Wait until we have a token
                wait_time = (1 - self.tokens) / self.requests_per_second
                time.sleep(wait_time)
                self.tokens = 0
            else:
                self.tokens -= 1

    def create_invoice(self, **kwargs):
        """Rate-limited invoice creation"""
        self._acquire_token()
        return self.client.create_invoice(**kwargs)

    def get_invoices(self, **kwargs):
        """Rate-limited invoice retrieval"""
        self._acquire_token()
        return self.client.get_invoices(**kwargs)

# Usage
rate_limited_client = RateLimitedClient("YOUR_API_TOKEN", requests_per_second=5)

# Make multiple requests without overwhelming the API
for i in range(20):
    invoice = rate_limited_client.create_invoice(
        asset=Asset.USDT,
        amount=1.0,
        description=f"Invoice {i}"
    )
    print(f"Created invoice {i}: {invoice.invoice_id}")
```

## Caching Strategies

### Exchange Rate Caching

Cache exchange rates to reduce API calls:

```python
from cryptobot import CryptoBotClient
from datetime import datetime, timedelta
import threading

class CachedRatesClient:
    def __init__(self, api_token, cache_ttl_seconds=300):
        self.client = CryptoBotClient(api_token)
        self.cache_ttl = timedelta(seconds=cache_ttl_seconds)
        self._rates_cache = None
        self._cache_timestamp = None
        self._cache_lock = threading.Lock()

    def get_exchange_rates(self, force_refresh=False):
        """Get exchange rates with caching"""
        with self._cache_lock:
            now = datetime.now()

            # Check if cache is valid
            if (not force_refresh and
                self._rates_cache is not None and
                self._cache_timestamp is not None and
                now - self._cache_timestamp < self.cache_ttl):
                return self._rates_cache

            # Fetch fresh rates
            self._rates_cache = self.client.get_exchange_rates()
            self._cache_timestamp = now
            return self._rates_cache

    def convert_amount(self, amount, from_asset, to_currency):
        """Convert amount using cached rates"""
        rates = self.get_exchange_rates()

        for rate in rates:
            if rate.source.name == from_asset and rate.target == to_currency:
                return float(amount) * float(rate.rate)

        return None

# Usage
cached_client = CachedRatesClient("YOUR_API_TOKEN", cache_ttl_seconds=300)

# First call fetches from API
rates1 = cached_client.get_exchange_rates()

# Subsequent calls use cache (within TTL)
rates2 = cached_client.get_exchange_rates()

# Convert amounts using cached rates
usd_amount = cached_client.convert_amount(1.0, "BTC", "USD")
print(f"1 BTC = ${usd_amount} USD")
```

## Webhook Security

### Enhanced Webhook Verification

Implement comprehensive webhook security:

```python
from fastapi import FastAPI, Request, HTTPException, Header
import hmac
import hashlib
import json
import time
from typing import Optional

app = FastAPI()

# Store processed webhook IDs to prevent replay attacks
processed_webhooks = set()
webhook_expiry_seconds = 300  # 5 minutes

def verify_webhook_signature(
    body: bytes,
    signature: str,
    secret: str
) -> bool:
    """Verify webhook signature using HMAC-SHA256"""
    expected_signature = hmac.new(
        secret.encode(),
        body,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(signature, expected_signature)

def check_replay_attack(webhook_id: str, timestamp: int) -> bool:
    """Check if webhook is a replay attack"""
    now = int(time.time())

    # Check if webhook is too old
    if now - timestamp > webhook_expiry_seconds:
        return True

    # Check if we've already processed this webhook
    if webhook_id in processed_webhooks:
        return True

    return False

@app.post("/webhook")
async def secure_webhook_handler(
    request: Request,
    crypto_pay_api_signature: Optional[str] = Header(None)
):
    """Secure webhook handler with multiple security checks"""
    # Check signature header exists
    if not crypto_pay_api_signature:
        raise HTTPException(status_code=401, detail="Missing signature")

    # Read body
    body = await request.body()

    # Verify signature
    webhook_secret = "YOUR_WEBHOOK_SECRET"
    if not verify_webhook_signature(body, crypto_pay_api_signature, webhook_secret):
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Parse payload
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # Extract webhook metadata
    webhook_id = payload.get("update_id")
    webhook_type = payload.get("update_type")

    # Check for replay attack
    timestamp = payload.get("request_date", int(time.time()))
    if check_replay_attack(str(webhook_id), timestamp):
        raise HTTPException(status_code=400, detail="Replay attack detected")

    # Mark webhook as processed
    processed_webhooks.add(str(webhook_id))

    # Process webhook based on type
    if webhook_type == "invoice_paid":
        invoice_data = payload.get("payload")
        # Process paid invoice
        process_paid_invoice(invoice_data)

    return {"status": "ok"}

def process_paid_invoice(invoice_data):
    """Process a paid invoice"""
    invoice_id = invoice_data.get("invoice_id")
    amount = invoice_data.get("amount")
    asset = invoice_data.get("asset")

    print(f"Invoice {invoice_id} paid: {amount} {asset}")
    # Add your business logic here
```

### Webhook Queue Processing

Use a queue for asynchronous webhook processing:

```python
from fastapi import FastAPI, Request, BackgroundTasks
import asyncio
from queue import Queue
import threading
import hmac
import hashlib

app = FastAPI()
webhook_queue = Queue()

def verify_signature(body: bytes, signature: str, secret: str) -> bool:
    """Verify webhook signature"""
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, expected)

def webhook_processor():
    """Background worker to process webhooks"""
    while True:
        try:
            webhook_data = webhook_queue.get(timeout=1)
            # Process webhook
            process_webhook(webhook_data)
            webhook_queue.task_done()
        except:
            pass

def process_webhook(data):
    """Process webhook data"""
    # Add your processing logic here
    print(f"Processing webhook: {data}")

# Start background worker
worker_thread = threading.Thread(target=webhook_processor, daemon=True)
worker_thread.start()

@app.post("/webhook")
async def webhook_handler(
    request: Request,
    background_tasks: BackgroundTasks
):
    """Webhook handler with queue processing"""
    signature = request.headers.get("crypto-pay-api-signature")
    body = await request.body()

    # Quick signature verification
    if not verify_signature(body, signature, "YOUR_SECRET"):
        return {"error": "Invalid signature"}, 401

    # Parse payload
    import json
    payload = json.loads(body)

    # Add to queue for async processing
    webhook_queue.put(payload)

    # Return immediately
    return {"status": "queued"}
```

## Database Integration

### Invoice Tracking with SQLAlchemy

Track invoices in a database:

```python
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from cryptobot import CryptoBotClient
from cryptobot.models import Asset, Status

Base = declarative_base()

class InvoiceRecord(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True)
    invoice_id = Column(Integer, unique=True, index=True)
    user_id = Column(Integer, index=True)
    asset = Column(String)
    amount = Column(Float)
    description = Column(String)
    status = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    paid_at = Column(DateTime, nullable=True)
    payload = Column(String, nullable=True)

class InvoiceManager:
    def __init__(self, api_token, database_url):
        self.client = CryptoBotClient(api_token)
        self.engine = create_engine(database_url)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def create_and_track_invoice(self, user_id, asset, amount, description, payload=None):
        """Create invoice and save to database"""
        # Create invoice via API
        invoice = self.client.create_invoice(
            asset=asset,
            amount=amount,
            description=description,
            payload=payload
        )

        # Save to database
        session = self.Session()
        try:
            record = InvoiceRecord(
                invoice_id=invoice.invoice_id,
                user_id=user_id,
                asset=asset.name,
                amount=amount,
                description=description,
                status=invoice.status.name,
                payload=payload
            )
            session.add(record)
            session.commit()
        finally:
            session.close()

        return invoice

    def update_invoice_status(self, invoice_id):
        """Update invoice status from API"""
        # Fetch from API
        invoices = self.client.get_invoices(invoice_ids=str(invoice_id))
        if not invoices:
            return None

        invoice = invoices[0]

        # Update database
        session = self.Session()
        try:
            record = session.query(InvoiceRecord).filter_by(
                invoice_id=invoice_id
            ).first()

            if record:
                record.status = invoice.status.name
                if invoice.status == Status.paid:
                    record.paid_at = datetime.utcnow()
                session.commit()
                return record
        finally:
            session.close()

    def get_user_invoices(self, user_id):
        """Get all invoices for a user"""
        session = self.Session()
        try:
            return session.query(InvoiceRecord).filter_by(
                user_id=user_id
            ).all()
        finally:
            session.close()

# Usage
manager = InvoiceManager(
    "YOUR_API_TOKEN",
    "sqlite:///invoices.db"
)

# Create and track invoice
invoice = manager.create_and_track_invoice(
    user_id=12345,
    asset=Asset.USDT,
    amount=10.0,
    description="Test invoice",
    payload="ORDER_123"
)

# Update status
manager.update_invoice_status(invoice.invoice_id)

# Get user's invoices
user_invoices = manager.get_user_invoices(12345)
```

## Logging and Monitoring

### Comprehensive Logging

Implement detailed logging for production:

```python
import logging
from cryptobot import CryptoBotClient
from cryptobot.errors import CryptoBotError
from cryptobot.models import Asset

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('cryptobot.log'),
        logging.StreamHandler()
    ]
)

class LoggedCryptoBotClient:
    def __init__(self, api_token, is_mainnet=True):
        self.client = CryptoBotClient(api_token, is_mainnet)
        self.logger = logging.getLogger('CryptoBot')

    def create_invoice(self, **kwargs):
        """Create invoice with logging"""
        self.logger.info(f"Creating invoice: {kwargs}")
        try:
            invoice = self.client.create_invoice(**kwargs)
            self.logger.info(
                f"Invoice created successfully: {invoice.invoice_id}"
            )
            return invoice
        except CryptoBotError as e:
            self.logger.error(
                f"Failed to create invoice: {e.code} - {e.name} - {e.description}"
            )
            raise

    def transfer(self, **kwargs):
        """Transfer with logging"""
        self.logger.info(f"Initiating transfer: {kwargs}")
        try:
            transfer = self.client.transfer(**kwargs)
            self.logger.info(
                f"Transfer completed: {transfer.transfer_id}"
            )
            return transfer
        except CryptoBotError as e:
            self.logger.error(
                f"Transfer failed: {e.code} - {e.name} - {e.description}"
            )
            raise

# Usage
logged_client = LoggedCryptoBotClient("YOUR_API_TOKEN")
invoice = logged_client.create_invoice(
    asset=Asset.USDT,
    amount=10.0,
    description="Logged invoice"
)
```

## Testing Strategies

### Mock Client for Unit Tests

Create a mock client for testing:

```python
from unittest.mock import Mock, patch
from cryptobot.models import Invoice, Asset, Status, Balance
import pytest

class MockCryptoBotClient:
    """Mock client for testing"""
    def __init__(self, api_token, is_mainnet=True, timeout=5.0):
        self.api_token = api_token
        self.invoices = []
        self.transfers = []

    def create_invoice(self, asset, amount, **kwargs):
        """Mock invoice creation"""
        invoice = Invoice(
            invoice_id=len(self.invoices) + 1,
            status=Status.active,
            hash="mock_hash",
            amount=str(amount),
            asset=asset,
            bot_invoice_url="https://t.me/CryptoBot?start=mock",
            **kwargs
        )
        self.invoices.append(invoice)
        return invoice

    def get_invoices(self, **kwargs):
        """Mock get invoices"""
        return self.invoices

    def get_balances(self):
        """Mock get balances"""
        return [
            Balance(currency_code="USDT", available="1000.0", onhold="0.0"),
            Balance(currency_code="BTC", available="0.5", onhold="0.0")
        ]

# Usage in tests
def test_invoice_creation():
    client = MockCryptoBotClient("test_token")

    invoice = client.create_invoice(
        asset=Asset.USDT,
        amount=10.0,
        description="Test"
    )

    assert invoice.invoice_id == 1
    assert invoice.amount == "10.0"
    assert invoice.asset == Asset.USDT

def test_get_invoices():
    client = MockCryptoBotClient("test_token")

    # Create some invoices
    client.create_invoice(Asset.USDT, 10.0, description="Test 1")
    client.create_invoice(Asset.BTC, 0.001, description="Test 2")

    # Get invoices
    invoices = client.get_invoices()

    assert len(invoices) == 2
    assert invoices[0].description == "Test 1"
    assert invoices[1].description == "Test 2"
```

## Performance Optimization

### Batch Operations

Process multiple invoices efficiently:

```python
from cryptobot import CryptoBotClient
from cryptobot.models import Asset
from concurrent.futures import ThreadPoolExecutor, as_completed

class BatchProcessor:
    def __init__(self, api_token, max_workers=10):
        self.client = CryptoBotClient(api_token)
        self.max_workers = max_workers

    def create_invoices_batch(self, invoice_specs):
        """Create multiple invoices in parallel"""
        results = []
        errors = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_spec = {
                executor.submit(
                    self.client.create_invoice,
                    **spec
                ): spec
                for spec in invoice_specs
            }

            # Collect results
            for future in as_completed(future_to_spec):
                spec = future_to_spec[future]
                try:
                    invoice = future.result()
                    results.append(invoice)
                except Exception as e:
                    errors.append({"spec": spec, "error": str(e)})

        return results, errors

# Usage
processor = BatchProcessor("YOUR_API_TOKEN", max_workers=5)

# Create 100 invoices
invoice_specs = [
    {
        "asset": Asset.USDT,
        "amount": 10.0,
        "description": f"Batch invoice {i}"
    }
    for i in range(100)
]

invoices, errors = processor.create_invoices_batch(invoice_specs)
print(f"Created {len(invoices)} invoices")
print(f"Failed {len(errors)} invoices")
```

## Environment-Specific Configuration

### Configuration Management

Manage different environments:

```python
import os
from enum import Enum
from cryptobot import CryptoBotClient

class Environment(Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"

class Config:
    def __init__(self, env: Environment):
        self.env = env
        self._load_config()

    def _load_config(self):
        """Load environment-specific configuration"""
        if self.env == Environment.DEVELOPMENT:
            self.api_token = os.getenv("CRYPTOBOT_DEV_TOKEN")
            self.is_mainnet = False
            self.timeout = 60.0
            self.log_level = "DEBUG"
        elif self.env == Environment.STAGING:
            self.api_token = os.getenv("CRYPTOBOT_STAGING_TOKEN")
            self.is_mainnet = False
            self.timeout = 30.0
            self.log_level = "INFO"
        else:  # PRODUCTION
            self.api_token = os.getenv("CRYPTOBOT_PROD_TOKEN")
            self.is_mainnet = True
            self.timeout = 30.0
            self.log_level = "WARNING"

    def create_client(self):
        """Create client with environment-specific settings"""
        return CryptoBotClient(
            self.api_token,
            is_mainnet=self.is_mainnet,
            timeout=self.timeout
        )

# Usage
env = Environment(os.getenv("APP_ENV", "development"))
config = Config(env)
client = config.create_client()
```

## Next Steps

- Review the [Examples](examples) for practical implementations
- Check the [Troubleshooting Guide](troubleshooting) for common issues
- Explore the [API Reference](modules) for detailed documentation
