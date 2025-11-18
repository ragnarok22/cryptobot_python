# Real-World Examples

This page provides complete, real-world examples of using CryptoBot Python in various scenarios.

## E-Commerce Integration

### Simple Online Store

Here's a complete example of integrating cryptocurrency payments into an online store:

```python
from cryptobot import CryptoBotClient
from cryptobot.models import Asset, Status
from cryptobot.errors import CryptoBotError
import os
from decimal import Decimal

class CryptoStore:
    def __init__(self):
        self.client = CryptoBotClient(os.getenv("CRYPTOBOT_TOKEN"))
        self.orders = {}

    def create_order(self, user_id, items, total_usd):
        """Create an order and generate payment invoice"""
        order_id = f"ORDER_{user_id}_{len(self.orders) + 1}"

        # Create invoice for USDT (1:1 with USD)
        try:
            invoice = self.client.create_invoice(
                asset=Asset.USDT,
                amount=total_usd,
                description=f"Order {order_id}",
                payload=order_id,
                expires_in=1800,  # 30 minutes
                paid_btn_name="callback",
                paid_btn_url=f"https://mystore.com/order/{order_id}/complete"
            )

            self.orders[order_id] = {
                "user_id": user_id,
                "items": items,
                "total": total_usd,
                "invoice_id": invoice.invoice_id,
                "status": "pending"
            }

            return {
                "order_id": order_id,
                "payment_url": invoice.bot_invoice_url,
                "expires_at": invoice.expiration_date
            }
        except CryptoBotError as e:
            print(f"Failed to create invoice: {e.name} - {e.description}")
            return None

    def check_payment(self, order_id):
        """Check if order has been paid"""
        if order_id not in self.orders:
            return {"status": "not_found"}

        order = self.orders[order_id]
        invoice_id = order["invoice_id"]

        try:
            invoices = self.client.get_invoices(invoice_ids=str(invoice_id))
            if invoices:
                invoice = invoices[0]
                if invoice.status == Status.paid:
                    order["status"] = "paid"
                    return {
                        "status": "paid",
                        "paid_amount": invoice.paid_amount,
                        "paid_asset": invoice.paid_asset
                    }
                elif invoice.status == Status.expired:
                    order["status"] = "expired"
                    return {"status": "expired"}

            return {"status": "pending"}
        except CryptoBotError as e:
            return {"status": "error", "message": str(e)}

# Usage
store = CryptoStore()

# Customer places order
order = store.create_order(
    user_id=12345,
    items=["T-Shirt", "Mug"],
    total_usd=29.99
)

if order:
    print(f"Order created: {order['order_id']}")
    print(f"Payment URL: {order['payment_url']}")
    print(f"Expires at: {order['expires_at']}")

    # Later, check payment status
    status = store.check_payment(order["order_id"])
    print(f"Payment status: {status}")
```

## Subscription Service

### Monthly Subscription Manager

Handle recurring subscription payments:

```python
from cryptobot import CryptoBotClient
from cryptobot.models import Asset, Status
from datetime import datetime, timedelta
import os

class SubscriptionManager:
    def __init__(self):
        self.client = CryptoBotClient(os.getenv("CRYPTOBOT_TOKEN"))
        self.subscriptions = {}

    def create_subscription(self, user_id, plan_name, monthly_price):
        """Create a new subscription and generate first payment invoice"""
        sub_id = f"SUB_{user_id}_{len(self.subscriptions) + 1}"

        invoice = self.client.create_invoice(
            asset=Asset.USDT,
            amount=monthly_price,
            description=f"{plan_name} - Monthly Subscription",
            payload=sub_id,
            expires_in=86400,  # 24 hours to complete first payment
            allow_anonymous=False
        )

        self.subscriptions[sub_id] = {
            "user_id": user_id,
            "plan_name": plan_name,
            "monthly_price": monthly_price,
            "status": "pending",
            "created_at": datetime.now(),
            "current_invoice_id": invoice.invoice_id
        }

        return {
            "subscription_id": sub_id,
            "payment_url": invoice.bot_invoice_url
        }

    def activate_subscription(self, sub_id):
        """Activate subscription after first payment"""
        sub = self.subscriptions.get(sub_id)
        if not sub:
            return False

        invoice_id = sub["current_invoice_id"]
        invoices = self.client.get_invoices(invoice_ids=str(invoice_id))

        if invoices and invoices[0].status == Status.paid:
            sub["status"] = "active"
            sub["activated_at"] = datetime.now()
            sub["next_billing_date"] = datetime.now() + timedelta(days=30)
            return True

        return False

    def generate_renewal_invoice(self, sub_id):
        """Generate invoice for subscription renewal"""
        sub = self.subscriptions.get(sub_id)
        if not sub or sub["status"] != "active":
            return None

        invoice = self.client.create_invoice(
            asset=Asset.USDT,
            amount=sub["monthly_price"],
            description=f"{sub['plan_name']} - Renewal",
            payload=f"{sub_id}_RENEWAL",
            expires_in=259200,  # 3 days
            allow_anonymous=False
        )

        sub["current_invoice_id"] = invoice.invoice_id
        return invoice.bot_invoice_url

# Usage
manager = SubscriptionManager()

# User subscribes
subscription = manager.create_subscription(
    user_id=12345,
    plan_name="Premium Plan",
    monthly_price=9.99
)
print(f"Subscription created: {subscription['subscription_id']}")
print(f"Payment URL: {subscription['payment_url']}")

# After payment, activate subscription
if manager.activate_subscription(subscription["subscription_id"]):
    print("Subscription activated!")
```

## Donation Platform

### Crowdfunding Campaign

Manage donations for a crowdfunding campaign:

```python
from cryptobot import CryptoBotClient
from cryptobot.models import Asset, Status
from decimal import Decimal
import os

class CrowdfundingCampaign:
    def __init__(self, campaign_name, goal_usd):
        self.client = CryptoBotClient(os.getenv("CRYPTOBOT_TOKEN"))
        self.campaign_name = campaign_name
        self.goal_usd = Decimal(str(goal_usd))
        self.donations = []

    def create_donation(self, donor_name, amount_usd, asset=Asset.USDT):
        """Create a donation invoice"""
        invoice = self.client.create_invoice(
            asset=asset,
            amount=amount_usd,
            description=f"Donation to {self.campaign_name}",
            payload=f"DONOR_{donor_name}",
            allow_comments=True,
            allow_anonymous=True,
            expires_in=3600
        )

        donation = {
            "donor_name": donor_name,
            "amount": amount_usd,
            "asset": asset.name,
            "invoice_id": invoice.invoice_id,
            "status": "pending"
        }
        self.donations.append(donation)

        return invoice.bot_invoice_url

    def update_donations(self):
        """Update status of all pending donations"""
        pending = [d for d in self.donations if d["status"] == "pending"]

        for donation in pending:
            invoices = self.client.get_invoices(
                invoice_ids=str(donation["invoice_id"])
            )
            if invoices:
                invoice = invoices[0]
                if invoice.status == Status.paid:
                    donation["status"] = "completed"
                    donation["paid_amount"] = invoice.paid_amount
                    donation["paid_asset"] = invoice.paid_asset
                elif invoice.status == Status.expired:
                    donation["status"] = "expired"

    def get_progress(self):
        """Calculate campaign progress"""
        self.update_donations()

        # Get exchange rates for conversion
        rates = self.client.get_exchange_rates()
        usd_rates = {r.source.name: float(r.rate) for r in rates if r.target == "USD"}

        total_usd = Decimal("0")
        for donation in self.donations:
            if donation["status"] == "completed":
                amount = Decimal(donation["paid_amount"])
                asset = donation["paid_asset"]

                # Convert to USD
                if asset == "USDT" or asset == "USDC":
                    total_usd += amount
                elif asset in usd_rates:
                    total_usd += amount * Decimal(str(usd_rates[asset]))

        percentage = (total_usd / self.goal_usd * 100) if self.goal_usd > 0 else 0

        return {
            "total_raised": float(total_usd),
            "goal": float(self.goal_usd),
            "percentage": float(percentage),
            "total_donations": len([d for d in self.donations if d["status"] == "completed"])
        }

    def get_top_donors(self, limit=10):
        """Get list of top donors"""
        completed = [d for d in self.donations if d["status"] == "completed"]
        sorted_donors = sorted(
            completed,
            key=lambda x: float(x["paid_amount"]),
            reverse=True
        )
        return sorted_donors[:limit]

# Usage
campaign = CrowdfundingCampaign("Open Source Project", 10000.0)

# Accept donations
payment_url = campaign.create_donation("Alice", 50.0, Asset.USDT)
print(f"Donation URL: {payment_url}")

# Check progress
progress = campaign.get_progress()
print(f"Raised: ${progress['total_raised']:.2f} of ${progress['goal']:.2f}")
print(f"Progress: {progress['percentage']:.1f}%")

# View top donors
top_donors = campaign.get_top_donors(5)
for i, donor in enumerate(top_donors, 1):
    print(f"{i}. {donor['donor_name']}: {donor['paid_amount']} {donor['paid_asset']}")
```

## Freelancer Marketplace

### Escrow Payment System

Implement an escrow system for freelancer payments:

```python
from cryptobot import CryptoBotClient
from cryptobot.models import Asset, Status
from cryptobot.errors import CryptoBotError
import os
from datetime import datetime

class EscrowSystem:
    def __init__(self):
        self.client = CryptoBotClient(os.getenv("CRYPTOBOT_TOKEN"))
        self.escrows = {}

    def create_escrow(self, client_id, freelancer_id, project_name, amount, asset=Asset.USDT):
        """Create an escrow for a project"""
        escrow_id = f"ESCROW_{len(self.escrows) + 1}"

        try:
            invoice = self.client.create_invoice(
                asset=asset,
                amount=amount,
                description=f"Escrow for {project_name}",
                payload=escrow_id,
                expires_in=86400,  # 24 hours
                allow_anonymous=False
            )

            self.escrows[escrow_id] = {
                "client_id": client_id,
                "freelancer_id": freelancer_id,
                "project_name": project_name,
                "amount": amount,
                "asset": asset.name,
                "invoice_id": invoice.invoice_id,
                "status": "awaiting_payment",
                "created_at": datetime.now()
            }

            return {
                "escrow_id": escrow_id,
                "payment_url": invoice.bot_invoice_url
            }
        except CryptoBotError as e:
            print(f"Error creating escrow: {e.name}")
            return None

    def check_escrow_funded(self, escrow_id):
        """Check if escrow has been funded"""
        escrow = self.escrows.get(escrow_id)
        if not escrow:
            return False

        invoices = self.client.get_invoices(invoice_ids=str(escrow["invoice_id"]))
        if invoices and invoices[0].status == Status.paid:
            escrow["status"] = "funded"
            escrow["funded_at"] = datetime.now()
            return True

        return False

    def release_payment(self, escrow_id, spend_id):
        """Release payment to freelancer"""
        escrow = self.escrows.get(escrow_id)
        if not escrow or escrow["status"] != "funded":
            return {"success": False, "error": "Escrow not funded"}

        try:
            transfer = self.client.transfer(
                user_id=escrow["freelancer_id"],
                asset=Asset[escrow["asset"]],
                amount=float(escrow["amount"]),
                spend_id=spend_id,
                comment=f"Payment for {escrow['project_name']}"
            )

            escrow["status"] = "completed"
            escrow["completed_at"] = datetime.now()
            escrow["transfer_id"] = transfer.transfer_id

            return {
                "success": True,
                "transfer_id": transfer.transfer_id
            }
        except CryptoBotError as e:
            return {
                "success": False,
                "error": f"{e.name}: {e.description}"
            }

    def refund_escrow(self, escrow_id, spend_id):
        """Refund payment to client"""
        escrow = self.escrows.get(escrow_id)
        if not escrow or escrow["status"] != "funded":
            return {"success": False, "error": "Escrow not funded"}

        try:
            transfer = self.client.transfer(
                user_id=escrow["client_id"],
                asset=Asset[escrow["asset"]],
                amount=float(escrow["amount"]),
                spend_id=spend_id,
                comment=f"Refund for {escrow['project_name']}"
            )

            escrow["status"] = "refunded"
            escrow["refunded_at"] = datetime.now()
            escrow["transfer_id"] = transfer.transfer_id

            return {
                "success": True,
                "transfer_id": transfer.transfer_id
            }
        except CryptoBotError as e:
            return {
                "success": False,
                "error": f"{e.name}: {e.description}"
            }

# Usage
escrow_system = EscrowSystem()

# Client creates escrow for project
escrow = escrow_system.create_escrow(
    client_id=11111,
    freelancer_id=22222,
    project_name="Website Design",
    amount=500.0,
    asset=Asset.USDT
)

if escrow:
    print(f"Escrow created: {escrow['escrow_id']}")
    print(f"Payment URL: {escrow['payment_url']}")

    # Check if funded
    if escrow_system.check_escrow_funded(escrow["escrow_id"]):
        print("Escrow funded!")

        # Work completed, release payment
        result = escrow_system.release_payment(
            escrow["escrow_id"],
            f"RELEASE_{escrow['escrow_id']}"
        )
        if result["success"]:
            print(f"Payment released! Transfer ID: {result['transfer_id']}")
```

## Tip Jar / Content Creator

### Simple Tip Bot

Create a tip bot for content creators:

```python
from cryptobot import CryptoBotClient
from cryptobot.models import Asset
import os

class TipBot:
    def __init__(self, creator_name):
        self.client = CryptoBotClient(os.getenv("CRYPTOBOT_TOKEN"))
        self.creator_name = creator_name
        self.tip_history = []

    def generate_tip_link(self, amount=None, asset=Asset.USDT, custom_message=""):
        """Generate a tip link for supporters"""
        description = f"Tip for {self.creator_name}"
        if custom_message:
            description += f" - {custom_message}"

        # If no amount specified, use a default minimum
        if amount is None:
            amount = 1.0

        invoice = self.client.create_invoice(
            asset=asset,
            amount=amount,
            description=description,
            allow_comments=True,
            allow_anonymous=True,
            paid_btn_name="callback",
            paid_btn_url=f"https://creator.com/{self.creator_name}/thanks"
        )

        self.tip_history.append({
            "invoice_id": invoice.invoice_id,
            "amount": amount,
            "asset": asset.name
        })

        return invoice.bot_invoice_url

    def get_total_tips(self):
        """Calculate total tips received"""
        invoices = self.client.get_invoices(status="paid")

        tips_by_asset = {}
        for invoice in invoices:
            asset = invoice.paid_asset or invoice.asset.name
            amount = float(invoice.paid_amount or invoice.amount)

            tips_by_asset[asset] = tips_by_asset.get(asset, 0) + amount

        return tips_by_asset

    def generate_qr_tip_amounts(self):
        """Generate multiple tip amount options"""
        amounts = [1, 5, 10, 25, 50, 100]
        tip_links = {}

        for amount in amounts:
            url = self.generate_tip_link(amount)
            tip_links[f"${amount}"] = url

        return tip_links

# Usage
tip_bot = TipBot("JohnDoeCreator")

# Generate tip links
quick_tips = tip_bot.generate_qr_tip_amounts()
for amount, url in quick_tips.items():
    print(f"Tip {amount}: {url}")

# Custom tip
custom_tip = tip_bot.generate_tip_link(15.0, Asset.USDT, "Love your content!")
print(f"Custom tip link: {custom_tip}")

# Check total tips
total_tips = tip_bot.get_total_tips()
print("\nTotal tips received:")
for asset, total in total_tips.items():
    print(f"  {asset}: {total}")
```

## Gaming / Virtual Goods

### In-Game Currency Purchase

Handle in-game currency purchases:

```python
from cryptobot import CryptoBotClient
from cryptobot.models import Asset, Status
import os

class GameStore:
    def __init__(self):
        self.client = CryptoBotClient(os.getenv("CRYPTOBOT_TOKEN"))
        self.packages = {
            "small": {"gems": 100, "price": 0.99},
            "medium": {"gems": 500, "price": 4.99},
            "large": {"gems": 1200, "price": 9.99},
            "mega": {"gems": 2500, "price": 19.99}
        }

    def purchase_gems(self, player_id, package_name):
        """Create invoice for gem package purchase"""
        if package_name not in self.packages:
            return None

        package = self.packages[package_name]

        invoice = self.client.create_invoice(
            asset=Asset.USDT,
            amount=package["price"],
            description=f"{package['gems']} Gems Package",
            payload=f"PLAYER_{player_id}_{package_name}",
            expires_in=600,  # 10 minutes
            paid_btn_name="callback",
            paid_btn_url=f"https://game.com/player/{player_id}/gems"
        )

        return {
            "package": package_name,
            "gems": package["gems"],
            "price": package["price"],
            "payment_url": invoice.bot_invoice_url,
            "invoice_id": invoice.invoice_id
        }

    def verify_and_deliver(self, invoice_id, player_id):
        """Verify payment and deliver gems to player"""
        invoices = self.client.get_invoices(invoice_ids=str(invoice_id))

        if not invoices:
            return {"success": False, "error": "Invoice not found"}

        invoice = invoices[0]
        if invoice.status == Status.paid:
            # Extract package info from payload
            payload = invoice.payload
            package_name = payload.split("_")[-1]

            if package_name in self.packages:
                gems = self.packages[package_name]["gems"]
                # Here you would add gems to player account
                return {
                    "success": True,
                    "gems_delivered": gems,
                    "message": f"{gems} gems added to your account!"
                }

        return {"success": False, "error": "Payment not completed"}

# Usage
store = GameStore()

# Player wants to buy gems
purchase = store.purchase_gems(player_id=12345, package_name="medium")
if purchase:
    print(f"Purchase {purchase['gems']} gems for ${purchase['price']}")
    print(f"Payment URL: {purchase['payment_url']}")

    # After payment, verify and deliver
    result = store.verify_and_deliver(purchase["invoice_id"], 12345)
    if result["success"]:
        print(result["message"])
```

## Testing Helpers

### Test Data Generator

Useful utilities for testing:

```python
from cryptobot import CryptoBotClient
from cryptobot.models import Asset
import os
import random

class TestHelper:
    def __init__(self, testnet=True):
        self.client = CryptoBotClient(
            os.getenv("CRYPTOBOT_TEST_TOKEN"),
            is_mainnet=not testnet
        )

    def create_test_invoices(self, count=5):
        """Create multiple test invoices"""
        invoices = []
        assets = [Asset.USDT, Asset.BTC, Asset.ETH, Asset.TON]

        for i in range(count):
            asset = random.choice(assets)
            amount = round(random.uniform(1.0, 100.0), 2)

            invoice = self.client.create_invoice(
                asset=asset,
                amount=amount,
                description=f"Test Invoice #{i+1}",
                payload=f"TEST_{i+1}"
            )
            invoices.append(invoice)

        return invoices

    def verify_integration(self):
        """Verify API integration is working"""
        try:
            # Test get_me
            app = self.client.get_me()
            print(f"✓ Connected as: {app.name}")

            # Test get_balances
            balances = self.client.get_balances()
            print(f"✓ Retrieved {len(balances)} balance(s)")

            # Test get_exchange_rates
            rates = self.client.get_exchange_rates()
            print(f"✓ Retrieved {len(rates)} exchange rate(s)")

            # Test create_invoice
            invoice = self.client.create_invoice(
                asset=Asset.USDT,
                amount=1.0,
                description="Integration test"
            )
            print(f"✓ Created test invoice: {invoice.invoice_id}")

            return True
        except Exception as e:
            print(f"✗ Integration test failed: {e}")
            return False

# Usage
helper = TestHelper(testnet=True)

# Verify integration
if helper.verify_integration():
    print("\nAll integration tests passed!")

# Create test data
test_invoices = helper.create_test_invoices(3)
print(f"\nCreated {len(test_invoices)} test invoices:")
for inv in test_invoices:
    print(f"  - {inv.invoice_id}: {inv.amount} {inv.asset.name}")
```

## Next Steps

- Explore the [Advanced Topics](advanced) for more complex patterns
- Check the [Troubleshooting Guide](troubleshooting) for common issues
- Review the [API Reference](modules) for complete documentation
