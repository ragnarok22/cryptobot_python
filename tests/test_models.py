#!/usr/bin/env python

"""Tests for data models in `cryptobot` package."""

import pytest

from cryptobot.models import (
    App,
    Asset,
    Balance,
    ButtonName,
    Currency,
    ExchangeRate,
    Invoice,
    Status,
    Transfer,
)


class TestEnums:
    """Tests for enum models."""

    def test_asset_enum_values(self):
        """Test Asset enum has correct values."""
        assert Asset.BTC.value == "BTC"
        assert Asset.TON.value == "TON"
        assert Asset.ETH.value == "ETH"
        assert Asset.USDT.value == "USDT"
        assert Asset.USDC.value == "USDC"
        assert Asset.BUSD.value == "BUSD"
        assert Asset.BNB.value == "BNB"
        assert Asset.TRX.value == "TRX"

    def test_asset_enum_membership(self):
        """Test Asset enum membership."""
        assert Asset.BTC in Asset
        assert Asset.TON in Asset
        assert "INVALID_ASSET" not in [asset.value for asset in Asset]

    def test_status_enum_values(self):
        """Test Status enum has correct values."""
        assert Status.active.value == "active"
        assert Status.paid.value == "paid"
        assert Status.expired.value == "expired"

    def test_button_name_enum_values(self):
        """Test ButtonName enum has correct values."""
        assert ButtonName.viewItem.value == "viewItem"
        assert ButtonName.openChannel.value == "openChannel"
        assert ButtonName.callback.value == "callback"

    def test_enum_string_representation(self):
        """Test string representation of enums."""
        assert str(Asset.BTC) == "Asset.BTC"
        assert str(Status.active) == "Status.active"
        assert str(ButtonName.viewItem) == "ButtonName.viewItem"


class TestApp:
    """Tests for App dataclass."""

    def test_app_creation(self):
        """Test creating App instance."""
        app = App(
            app_id=12345, name="Test App", payment_processing_bot_username="TestBot"
        )
        assert app.app_id == 12345
        assert app.name == "Test App"
        assert app.payment_processing_bot_username == "TestBot"

    def test_app_required_fields(self):
        """Test App requires all fields."""
        with pytest.raises(TypeError):
            App(app_id=12345)  # Missing required fields


class TestInvoice:
    """Tests for Invoice dataclass."""

    def test_invoice_minimal_creation(self):
        """Test creating Invoice with minimal required fields."""
        invoice = Invoice(
            invoice_id=123,
            status=Status.active,
            hash="abc123",
            amount="10.50",
            asset=Asset.USDT,
        )
        assert invoice.invoice_id == 123
        assert invoice.status == Status.active
        assert invoice.hash == "abc123"
        assert invoice.amount == "10.50"
        assert invoice.asset == Asset.USDT
        # Test default values
        assert invoice.allow_comments is True
        assert invoice.allow_anonymous is True
        assert invoice.paid_anonymously is True

    def test_invoice_full_creation(self):
        """Test creating Invoice with all fields."""
        invoice = Invoice(
            invoice_id=456,
            status=Status.paid,
            hash="def456",
            amount="25.00",
            asset=Asset.BTC,
            currency_type="crypto",
            description="Test invoice",
            comment="User comment",
            hidden_message="Secret message",
            payload="custom_payload",
            created_at="2023-01-01T00:00:00Z",
            expiration_date="2023-01-02T00:00:00Z",
            paid_at="2023-01-01T12:00:00Z",
            fiat="USD",
            accepted_assets=[Asset.BTC, Asset.ETH],
            fee_asset="BTC",
            fee_amount="0.001",
            paid_anonymously=False,
            paid_amount="25.00",
            paid_fiat_rate="50000.00",
            paid_usd_rate="50000.00",
            paid_asset="BTC",
            paid_btn_name=ButtonName.viewItem,
            paid_btn_url="https://example.com",
            bot_invoice_url="https://t.me/bot",
            allow_comments=False,
            allow_anonymous=False,
            swap_to="USDT",
        )
        assert invoice.description == "Test invoice"
        assert invoice.comment == "User comment"
        assert invoice.paid_btn_name == ButtonName.viewItem
        assert invoice.allow_comments is False
        assert invoice.allow_anonymous is False

    def test_invoice_deprecated_fields(self):
        """Test Invoice deprecated fields."""
        invoice = Invoice(
            invoice_id=789,
            status=Status.expired,
            hash="ghi789",
            amount="5.00",
            asset=Asset.ETH,
            fee="0.01",
            pay_url="https://pay.example.com",
            usd_rate="3000.00",
        )
        assert invoice.fee == "0.01"
        assert invoice.pay_url == "https://pay.example.com"
        assert invoice.usd_rate == "3000.00"


class TestTransfer:
    """Tests for Transfer dataclass."""

    def test_transfer_creation(self):
        """Test creating Transfer instance."""
        transfer = Transfer(
            transfer_id=123,
            user_id=456,
            asset=Asset.TON,
            amount="10.0",
            status=Status.paid,
            completed_at="2023-01-01T12:00:00Z",
        )
        assert transfer.transfer_id == 123
        assert transfer.user_id == 456
        assert transfer.asset == Asset.TON
        assert transfer.amount == "10.0"
        assert transfer.status == Status.paid
        assert transfer.completed_at == "2023-01-01T12:00:00Z"

    def test_transfer_with_comment(self):
        """Test creating Transfer with comment."""
        transfer = Transfer(
            transfer_id=789,
            user_id=101,
            asset=Asset.USDT,
            amount="50.0",
            status=Status.active,
            completed_at="2023-01-02T15:30:00Z",
            comment="Payment for services",
        )
        assert transfer.comment == "Payment for services"


class TestBalance:
    """Tests for Balance dataclass."""

    def test_balance_creation(self):
        """Test creating Balance instance."""
        balance = Balance(currency_code="BTC", available="1.5", onhold="0.1")
        assert balance.currency_code == "BTC"
        assert balance.available == "1.5"
        assert balance.onhold == "0.1"

    def test_balance_zero_amounts(self):
        """Test Balance with zero amounts."""
        balance = Balance(currency_code="USDT", available="0.0", onhold="0.0")
        assert balance.available == "0.0"
        assert balance.onhold == "0.0"


class TestExchangeRate:
    """Tests for ExchangeRate dataclass."""

    def test_exchange_rate_crypto_to_fiat(self):
        """Test ExchangeRate for crypto to fiat."""
        rate = ExchangeRate(
            is_valid=True,
            is_crypto=True,
            is_fiat=False,
            source=Asset.BTC,
            target="USD",
            rate="50000.00",
        )
        assert rate.is_valid is True
        assert rate.is_crypto is True
        assert rate.is_fiat is False
        assert rate.source == Asset.BTC
        assert rate.target == "USD"
        assert rate.rate == "50000.00"

    def test_exchange_rate_invalid(self):
        """Test invalid ExchangeRate."""
        rate = ExchangeRate(
            is_valid=False,
            is_crypto=False,
            is_fiat=True,
            source=Asset.ETH,
            target="EUR",
            rate="0.00",
        )
        assert rate.is_valid is False


class TestCurrency:
    """Tests for Currency dataclass."""

    def test_currency_crypto(self):
        """Test Currency for cryptocurrency."""
        currency = Currency(
            is_blockchain=True,
            is_stablecoin=False,
            is_fiat=False,
            name="Bitcoin",
            code="BTC",
            decimals=8,
        )
        assert currency.is_blockchain is True
        assert currency.is_stablecoin is False
        assert currency.is_fiat is False
        assert currency.name == "Bitcoin"
        assert currency.code == "BTC"
        assert currency.decimals == 8

    def test_currency_stablecoin(self):
        """Test Currency for stablecoin."""
        currency = Currency(
            is_blockchain=True,
            is_stablecoin=True,
            is_fiat=False,
            name="Tether",
            code="USDT",
            decimals=6,
            url="https://tether.to",
        )
        assert currency.is_stablecoin is True
        assert currency.url == "https://tether.to"

    def test_currency_fiat(self):
        """Test Currency for fiat currency."""
        currency = Currency(
            is_blockchain=False,
            is_stablecoin=False,
            is_fiat=True,
            name="US Dollar",
            code="USD",
            decimals=2,
        )
        assert currency.is_fiat is True
        assert currency.decimals == 2


class TestDataclassFeatures:
    """Tests for dataclass features."""

    def test_dataclass_equality(self):
        """Test equality comparison of dataclass instances."""
        app1 = App(app_id=123, name="Test", payment_processing_bot_username="Bot")
        app2 = App(app_id=123, name="Test", payment_processing_bot_username="Bot")
        app3 = App(app_id=456, name="Different", payment_processing_bot_username="Bot")

        assert app1 == app2
        assert app1 != app3

    def test_dataclass_repr(self):
        """Test string representation of dataclass instances."""
        balance = Balance(currency_code="BTC", available="1.0", onhold="0.0")
        repr_str = repr(balance)
        assert "Balance" in repr_str
        assert "currency_code='BTC'" in repr_str
        assert "available='1.0'" in repr_str

    def test_dataclass_field_access(self):
        """Test field access in dataclass instances."""
        transfer = Transfer(
            transfer_id=1,
            user_id=2,
            asset=Asset.ETH,
            amount="5.0",
            status=Status.paid,
            completed_at="2023-01-01T00:00:00Z",
        )

        # Test field access
        assert hasattr(transfer, "transfer_id")
        assert hasattr(transfer, "asset")
        assert hasattr(transfer, "comment")

        # Test field modification
        transfer.comment = "Updated comment"
        assert transfer.comment == "Updated comment"
