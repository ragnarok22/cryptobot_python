# Real-World Examples

This page shows complete integration patterns built on top of `CryptoBotClient` and `AsyncCryptoBotClient`.

## Shared Setup

```python
import os

from cryptobot import CryptoBotClient
from cryptobot.errors import CryptoBotError
from cryptobot.models import Asset, ButtonName, Status

client = CryptoBotClient(api_token=os.environ["CRYPTOBOT_API_TOKEN"])
```

## Async Invoice Scanner

Use async pagination helpers to process large paid-invoice sets without loading everything at once.

```python
import asyncio
import os

from cryptobot import AsyncCryptoBotClient
from cryptobot.models import Asset, Status


async def scan_paid_invoices():
    async with AsyncCryptoBotClient(
        api_token=os.environ["CRYPTOBOT_API_TOKEN"],
        max_retries=2,
        retry_backoff=0.5,
    ) as client:
        async for invoice in client.iter_invoices(
            asset=Asset.USDT,
            status=Status.paid,
            page_size=100,
            start_offset=0,
        ):
            print("paid invoice:", invoice.invoice_id, invoice.paid_amount or invoice.amount)


asyncio.run(scan_paid_invoices())
```

## E-Commerce Checkout

Create an invoice during checkout, then poll status for order fulfillment.

```python
from dataclasses import dataclass
from typing import Dict


@dataclass
class Order:
    order_id: str
    amount_usdt: float
    invoice_id: int
    status: str


class CheckoutService:
    def __init__(self, client: CryptoBotClient):
        self.client = client
        self.orders: Dict[str, Order] = {}

    def create_checkout(self, order_id: str, amount_usdt: float) -> str:
        invoice = self.client.create_invoice(
            asset=Asset.USDT,
            amount=amount_usdt,
            description=f"Order {order_id}",
            payload=order_id,
            expires_in=1800,
            paid_btn_name=ButtonName.callback,
            paid_btn_url=f"https://shop.example/orders/{order_id}",
        )

        self.orders[order_id] = Order(
            order_id=order_id,
            amount_usdt=amount_usdt,
            invoice_id=invoice.invoice_id,
            status="pending",
        )
        return invoice.bot_invoice_url

    def sync_order(self, order_id: str) -> str:
        order = self.orders[order_id]
        invoices = self.client.get_invoices(invoice_ids=str(order.invoice_id))
        if not invoices:
            return order.status

        invoice = invoices[0]
        if invoice.status == Status.paid:
            order.status = "paid"
        elif invoice.status == Status.expired:
            order.status = "expired"

        return order.status


service = CheckoutService(client)
payment_url = service.create_checkout("ORDER-1001", 29.99)
print("Pay here:", payment_url)
print("Current status:", service.sync_order("ORDER-1001"))
```

## Payout Workflow

Use unique `spend_id` values to keep transfers idempotent.

```python
from datetime import datetime
import uuid


def make_spend_id(prefix: str, user_id: int) -> str:
    stamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    return f"{prefix}_{user_id}_{stamp}_{uuid.uuid4().hex[:8]}"


def send_reward(client: CryptoBotClient, user_id: int, amount: float):
    spend_id = make_spend_id("reward", user_id)
    try:
        transfer = client.transfer(
            user_id=user_id,
            asset=Asset.TON,
            amount=amount,
            spend_id=spend_id,
            comment="Referral reward",
        )
        return {"ok": True, "transfer_id": transfer.transfer_id, "spend_id": spend_id}
    except CryptoBotError as exc:
        return {"ok": False, "code": exc.code, "name": exc.name, "spend_id": spend_id}


print(send_reward(client, user_id=123456789, amount=0.5))
```

## Donation Tracker

Track donation progress from paid invoices.

```python
from decimal import Decimal


class DonationTracker:
    def __init__(self, client: CryptoBotClient, goal_usd: Decimal):
        self.client = client
        self.goal_usd = goal_usd

    def create_donation_invoice(self, donor: str, amount_usdt: float) -> str:
        invoice = self.client.create_invoice(
            asset=Asset.USDT,
            amount=amount_usdt,
            description="Open-source donation",
            payload=f"donor:{donor}",
            allow_comments=True,
            allow_anonymous=True,
            expires_in=3600,
        )
        return invoice.bot_invoice_url

    def progress(self):
        invoices = self.client.get_invoices(status=Status.paid, count=100)
        total = Decimal("0")

        for invoice in invoices:
            amount = Decimal(invoice.paid_amount or invoice.amount)
            paid_asset = invoice.paid_asset or invoice.asset.name

            # Simple handling for stablecoins; convert non-USD assets as needed.
            if paid_asset in {"USDT", "USDC"}:
                total += amount

        pct = (total / self.goal_usd * Decimal("100")) if self.goal_usd > 0 else Decimal("0")
        return {"raised_usd": str(total), "goal_usd": str(self.goal_usd), "percent": str(round(pct, 2))}


tracker = DonationTracker(client, goal_usd=Decimal("10000"))
print("Donate:", tracker.create_donation_invoice("alice", 25))
print("Progress:", tracker.progress())
```

## Webhook-Driven Fulfillment

Use the listener to mark orders as paid without polling.

```python
import os

from cryptobot.webhook import InMemoryReplayKeyStore, Listener


def handle_webhook(headers, data):
    if data.get("update_type") != "invoice_paid":
        return

    payload = data.get("payload", {})
    invoice_id = payload.get("invoice_id")
    order_id = payload.get("payload")  # value passed during create_invoice(payload=...)

    print("Fulfill order", order_id, "from invoice", invoice_id)


listener = Listener(
    host="0.0.0.0",
    callback=handle_webhook,
    api_token=os.environ["CRYPTOBOT_API_TOKEN"],
    replay_store=InMemoryReplayKeyStore(),
    replay_ttl_seconds=3600,
    port=2203,
    url="/webhook",
    log_level="info",
)
listener.listen()
```

## Testnet Smoke Check

Quick validation script for non-production environments.

```python
import os

from cryptobot import CryptoBotClient
from cryptobot.models import Asset


def smoke_check_testnet() -> bool:
    client = CryptoBotClient(
        api_token=os.environ["CRYPTOBOT_TESTNET_TOKEN"],
        is_mainnet=False,
        timeout=10.0,
    )

    try:
        app = client.get_me()
        balances = client.get_balances()
        rates = client.get_exchange_rates()
        invoice = client.create_invoice(asset=Asset.USDT, amount=1, description="testnet smoke")

        print("App:", app.name)
        print("Balances:", len(balances))
        print("Rates:", len(rates))
        print("Invoice:", invoice.invoice_id)
        return True
    except Exception as exc:
        print("Smoke check failed:", exc)
        return False


if __name__ == "__main__":
    smoke_check_testnet()
```

## Next Steps

- Use [Advanced Topics](advanced) for retry, caching, and persistence patterns.
- Use [Troubleshooting](troubleshooting) when integration behavior is unexpected.
- Use [API Reference](modules) for complete method signatures.
