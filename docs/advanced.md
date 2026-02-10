# Advanced Topics

This guide covers production patterns for CryptoBot Python, including retries, local throttling, caching, webhook processing, and persistence.

## Environment Baseline

Use environment variables for all tokens:

```python
import os

API_TOKEN = os.environ["CRYPTOBOT_API_TOKEN"]
TESTNET_TOKEN = os.environ.get("CRYPTOBOT_TESTNET_TOKEN")
```

## Retry and Backoff Wrapper

Use a wrapper to retry only transient failures (`429` and `5xx`):

```python
import time

from cryptobot import CryptoBotClient
from cryptobot.errors import CryptoBotError
from cryptobot.models import Asset


class ResilientCryptoBotClient:
    def __init__(self, api_token: str, is_mainnet: bool = True, timeout: float = 5.0, max_retries: int = 3):
        self.client = CryptoBotClient(api_token, is_mainnet=is_mainnet, timeout=timeout)
        self.max_retries = max_retries

    def _run(self, fn, *args, **kwargs):
        for attempt in range(1, self.max_retries + 1):
            try:
                return fn(*args, **kwargs)
            except CryptoBotError as exc:
                is_retryable = exc.code == 429 or exc.code >= 500
                if not is_retryable or attempt == self.max_retries:
                    raise
                delay = 0.5 * (2 ** (attempt - 1))
                time.sleep(delay)

    def create_invoice(self, **kwargs):
        return self._run(self.client.create_invoice, **kwargs)

    def transfer(self, **kwargs):
        return self._run(self.client.transfer, **kwargs)


resilient = ResilientCryptoBotClient(API_TOKEN)
invoice = resilient.create_invoice(asset=Asset.USDT, amount=10, description="Retry-safe invoice")
print(invoice.invoice_id)
```

## Tuned HTTPX Client

If you need custom connection limits or transport configuration, replace the internal `httpx.Client` after initialization:

```python
import httpx

from cryptobot import CryptoBotClient


class TunedCryptoBotClient(CryptoBotClient):
    def __init__(self, api_token: str, is_mainnet: bool = True, timeout: float = 5.0, max_connections: int = 100):
        super().__init__(api_token=api_token, is_mainnet=is_mainnet, timeout=timeout)

        # Close the default client before replacing it.
        self._http_client.close()

        self._http_client = httpx.Client(
            base_url=self._base_url,
            timeout=timeout,
            headers={"Crypto-Pay-API-Token": self.api_token},
            limits=httpx.Limits(
                max_keepalive_connections=max_connections,
                max_connections=max_connections,
            ),
        )

    def close(self):
        self._http_client.close()


client = TunedCryptoBotClient(API_TOKEN, timeout=10.0, max_connections=50)
try:
    print(client.get_me().name)
finally:
    client.close()
```

## Local Rate Limiting

Use a token bucket in-process to smooth bursts:

```python
import threading
import time

from cryptobot import CryptoBotClient
from cryptobot.models import Asset


class TokenBucket:
    def __init__(self, rate_per_second: float, capacity: float):
        self.rate = rate_per_second
        self.capacity = capacity
        self.tokens = capacity
        self.last = time.monotonic()
        self.lock = threading.Lock()

    def acquire(self):
        while True:
            with self.lock:
                now = time.monotonic()
                elapsed = now - self.last
                self.last = now
                self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)

                if self.tokens >= 1:
                    self.tokens -= 1
                    return

                wait_for = (1 - self.tokens) / self.rate
            time.sleep(wait_for)


class RateLimitedCryptoBotClient:
    def __init__(self, api_token: str, requests_per_second: float = 5):
        self.client = CryptoBotClient(api_token)
        self.bucket = TokenBucket(rate_per_second=requests_per_second, capacity=requests_per_second)

    def create_invoice(self, **kwargs):
        self.bucket.acquire()
        return self.client.create_invoice(**kwargs)


limited = RateLimitedCryptoBotClient(API_TOKEN, requests_per_second=3)
for i in range(5):
    inv = limited.create_invoice(asset=Asset.USDT, amount=1, description=f"Burst #{i}")
    print(inv.invoice_id)
```

## Exchange-Rate Caching

Cache exchange rates with a TTL to reduce API calls:

```python
from datetime import datetime, timedelta
from threading import Lock
from typing import List

from cryptobot import CryptoBotClient
from cryptobot.models import ExchangeRate


class ExchangeRateCache:
    def __init__(self, client: CryptoBotClient, ttl_seconds: int = 60):
        self.client = client
        self.ttl = timedelta(seconds=ttl_seconds)
        self._rates: List[ExchangeRate] = []
        self._fetched_at: datetime | None = None
        self._lock = Lock()

    def get_rates(self, force_refresh: bool = False) -> List[ExchangeRate]:
        with self._lock:
            now = datetime.utcnow()
            is_fresh = self._fetched_at and now - self._fetched_at < self.ttl
            if self._rates and is_fresh and not force_refresh:
                return self._rates

            self._rates = self.client.get_exchange_rates()
            self._fetched_at = now
            return self._rates


client = CryptoBotClient(API_TOKEN)
cache = ExchangeRateCache(client, ttl_seconds=120)
rates = cache.get_rates()
print(len(rates))
```

## Webhook Queue Pattern

Keep webhook HTTP handlers fast and push business work to a queue worker:

```python
import os
from queue import Queue
from threading import Thread

from cryptobot.webhook import Listener


queue: Queue[dict] = Queue(maxsize=1000)


def process_update(update: dict):
    if update.get("update_type") == "invoice_paid":
        payload = update.get("payload", {})
        print("Process paid invoice", payload.get("invoice_id"))


def worker():
    while True:
        item = queue.get()
        try:
            process_update(item)
        finally:
            queue.task_done()


def on_webhook(headers, data):
    # Signature validation is already handled by Listener.
    queue.put_nowait(data)


Thread(target=worker, daemon=True).start()

listener = Listener(
    host="0.0.0.0",
    callback=on_webhook,
    api_token=os.environ["CRYPTOBOT_API_TOKEN"],
    port=2203,
    url="/webhook",
    log_level="info",
)
listener.listen()
```

## Persisting Invoices with SQLAlchemy

Persist created invoices and sync status from the API:

```python
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from cryptobot import CryptoBotClient
from cryptobot.models import Asset


Base = declarative_base()


class InvoiceRecord(Base):
    __tablename__ = "invoice_records"

    id = Column(Integer, primary_key=True)
    invoice_id = Column(Integer, unique=True, nullable=False)
    status = Column(String, nullable=False)
    asset = Column(String, nullable=False)
    amount = Column(String, nullable=False)
    payload = Column(String, nullable=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class InvoiceStore:
    def __init__(self, api_token: str, db_url: str):
        self.client = CryptoBotClient(api_token)
        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def create_invoice(self, asset: Asset, amount: float, payload: str):
        invoice = self.client.create_invoice(asset=asset, amount=amount, payload=payload)
        session = self.Session()
        try:
            session.add(
                InvoiceRecord(
                    invoice_id=invoice.invoice_id,
                    status=invoice.status.name,
                    asset=invoice.asset.name,
                    amount=invoice.amount,
                    payload=invoice.payload,
                )
            )
            session.commit()
        finally:
            session.close()
        return invoice

    def sync_invoice(self, invoice_id: int):
        invoices = self.client.get_invoices(invoice_ids=str(invoice_id))
        if not invoices:
            return None

        latest = invoices[0]
        session = self.Session()
        try:
            row = session.query(InvoiceRecord).filter_by(invoice_id=invoice_id).first()
            if row:
                row.status = latest.status.name
                row.updated_at = datetime.utcnow()
                session.commit()
            return latest
        finally:
            session.close()
```

## Structured Logging Wrapper

Log operations with request context and API error fields:

```python
import logging

from cryptobot import CryptoBotClient
from cryptobot.errors import CryptoBotError
from cryptobot.models import Asset


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("cryptobot")


class LoggedCryptoBotClient:
    def __init__(self, api_token: str):
        self.client = CryptoBotClient(api_token)

    def create_invoice(self, *, asset: Asset, amount: float, description: str):
        logger.info("create_invoice start asset=%s amount=%s", asset.name, amount)
        try:
            invoice = self.client.create_invoice(asset=asset, amount=amount, description=description)
            logger.info("create_invoice ok invoice_id=%s status=%s", invoice.invoice_id, invoice.status.name)
            return invoice
        except CryptoBotError as exc:
            logger.error("create_invoice failed code=%s name=%s", exc.code, exc.name)
            raise
```

## Testing with MockTransport

For deterministic unit tests, replace the internal HTTP client transport:

```python
import httpx

from cryptobot import CryptoBotClient
from cryptobot.models import Asset


def handler(request: httpx.Request) -> httpx.Response:
    if request.url.path.endswith("/createInvoice"):
        return httpx.Response(
            200,
            json={
                "ok": True,
                "result": {
                    "invoice_id": 1,
                    "status": "active",
                    "hash": "mock_hash",
                    "amount": "1",
                    "asset": "USDT",
                    "bot_invoice_url": "https://t.me/CryptoBot?start=mock",
                },
            },
        )
    return httpx.Response(404, json={"ok": False, "error": {"code": 404, "name": "NOT_FOUND"}})


transport = httpx.MockTransport(handler)
client = CryptoBotClient("test_token")
client._http_client.close()
client._http_client = httpx.Client(
    base_url=client._base_url,
    headers={"Crypto-Pay-API-Token": client.api_token},
    transport=transport,
)

invoice = client.create_invoice(asset=Asset.USDT, amount=1)
assert invoice.invoice_id == 1
```

## Next Steps

- Review [Examples](examples) for complete flows.
- Read [Webhook Security](webhook_security) before production rollout.
- Keep [Troubleshooting](troubleshooting) open while integrating.
