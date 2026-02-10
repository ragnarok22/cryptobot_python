#!/usr/bin/env python

"""Tests for CryptoBotClient with mocked HTTP responses."""

from unittest.mock import Mock, patch

import httpx
import pytest

from cryptobot import CryptoBotClient
from cryptobot.errors import CryptoBotError
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
    TransferStatus,
)


class TestCryptoBotClientInitialization:
    """Tests for CryptoBotClient initialization."""

    def test_client_creation_mainnet(self):
        """Test creating client for mainnet."""
        client = CryptoBotClient("test_token", is_mainnet=True)
        assert client.api_token == "test_token"
        assert client.timeout == 5.0

    def test_client_creation_testnet(self):
        """Test creating client for testnet."""
        client = CryptoBotClient("test_token", is_mainnet=False)
        assert client.api_token == "test_token"

    def test_client_creation_with_timeout(self):
        """Test creating client with custom timeout."""
        client = CryptoBotClient("test_token", timeout=60)
        assert client.api_token == "test_token"
        assert client.timeout == 60

    def test_client_url_construction_mainnet(self):
        """Test URL construction for mainnet."""
        client = CryptoBotClient("test_token", is_mainnet=True)
        # Access the base URL through the httpx client
        base_url = str(client._http_client.base_url)
        assert "pay.crypt.bot" in base_url

    def test_client_url_construction_testnet(self):
        """Test URL construction for testnet."""
        client = CryptoBotClient("test_token", is_mainnet=False)
        base_url = str(client._http_client.base_url)
        assert "testnet-pay.crypt.bot" in base_url

    def test_retry_configuration_defaults(self):
        client = CryptoBotClient("test_token")
        assert client.max_retries == 0
        assert client.retry_backoff == 0.5
        assert client.retryable_status_codes == {429, 500, 502, 503, 504}

    def test_client_context_manager_closes_http_client(self):
        """Test context manager support closes the underlying HTTP client."""
        with CryptoBotClient("test_token") as client:
            assert not client._http_client.is_closed
        assert client._http_client.is_closed


class TestCryptoBotClientRetryPolicy:
    """Tests for retry/backoff behavior."""

    @patch("httpx.Client.get")
    def test_retry_on_retryable_status_then_success(self, mock_get):
        retry_response = Mock()
        retry_response.status_code = 429
        retry_response.headers = {}
        retry_response.json.return_value = {"error": {"code": 429, "name": "TOO_MANY_REQUESTS"}}

        ok_response = Mock()
        ok_response.status_code = 200
        ok_response.headers = {}
        ok_response.json.return_value = {
            "result": {
                "app_id": 1,
                "name": "Retry App",
                "payment_processing_bot_username": "RetryBot",
            }
        }

        mock_get.side_effect = [retry_response, ok_response]

        client = CryptoBotClient("test_token", max_retries=1, retry_backoff=0)
        app = client.get_me()

        assert app.app_id == 1
        assert mock_get.call_count == 2

    @patch("httpx.Client.get")
    def test_no_retry_on_non_retryable_status(self, mock_get):
        bad_request = Mock()
        bad_request.status_code = 400
        bad_request.headers = {}
        bad_request.json.return_value = {"error": {"code": 400, "name": "BAD_REQUEST"}}
        mock_get.return_value = bad_request

        client = CryptoBotClient("test_token", max_retries=3, retry_backoff=0)
        with pytest.raises(CryptoBotError) as exc_info:
            client.get_me()

        assert exc_info.value.code == 400
        assert mock_get.call_count == 1

    @patch("httpx.Client.get")
    def test_retry_on_timeout_exception_then_success(self, mock_get):
        ok_response = Mock()
        ok_response.status_code = 200
        ok_response.headers = {}
        ok_response.json.return_value = {
            "result": {
                "app_id": 2,
                "name": "Recovered App",
                "payment_processing_bot_username": "RecoveredBot",
            }
        }

        mock_get.side_effect = [httpx.TimeoutException("timeout"), ok_response]

        client = CryptoBotClient("test_token", max_retries=1, retry_backoff=0)
        app = client.get_me()

        assert app.app_id == 2
        assert mock_get.call_count == 2


class TestCryptoBotClientGetMe:
    """Tests for get_me method."""

    @patch("httpx.Client.get")
    def test_get_me_success(self, mock_get):
        """Test successful get_me request."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "result": {
                "app_id": 12345,
                "name": "Test App",
                "payment_processing_bot_username": "TestBot",
            }
        }
        mock_get.return_value = mock_response

        client = CryptoBotClient("test_token")
        app = client.get_me()

        assert isinstance(app, App)
        assert app.app_id == 12345
        assert app.name == "Test App"
        assert app.payment_processing_bot_username == "TestBot"

    @patch("httpx.Client.get")
    def test_get_me_error(self, mock_get):
        """Test get_me request with error response."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": {"code": 401, "name": "UNAUTHORIZED"}}
        mock_get.return_value = mock_response

        client = CryptoBotClient("test_token")

        with pytest.raises(CryptoBotError) as exc_info:
            client.get_me()

        error = exc_info.value
        assert error.code == 401
        assert error.name == "UNAUTHORIZED"


class TestCryptoBotClientCreateInvoice:
    """Tests for create_invoice method."""

    @patch("httpx.Client.post")
    def test_create_invoice_minimal(self, mock_post):
        """Test creating invoice with minimal parameters."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "result": {
                "invoice_id": 123,
                "status": "active",
                "hash": "abc123",
                "amount": "10.50",
                "asset": "USDT",
                "currency_type": "crypto",
                "allow_comments": True,
                "allow_anonymous": True,
                "paid_anonymously": True,
            }
        }
        mock_post.return_value = mock_response

        client = CryptoBotClient("test_token")
        invoice = client.create_invoice(Asset.USDT, 10.50)

        assert isinstance(invoice, Invoice)
        assert invoice.invoice_id == 123
        assert invoice.status == Status.active
        assert invoice.amount == "10.50"
        assert invoice.asset == Asset.USDT

        # Check that post was called with correct parameters
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "/createInvoice"
        assert call_args[1]["json"]["asset"] == "USDT"
        assert call_args[1]["json"]["amount"] == "10.5"

    @patch("httpx.Client.post")
    def test_create_invoice_full_parameters(self, mock_post):
        """Test creating invoice with all parameters."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "result": {
                "invoice_id": 456,
                "status": "active",
                "hash": "def456",
                "amount": "25.00",
                "asset": "BTC",
                "description": "Test invoice",
                "hidden_message": "Secret",
                "paid_btn_name": "viewItem",
                "paid_btn_url": "https://example.com",
                "payload": "custom_payload",
                "allow_comments": False,
                "allow_anonymous": False,
                "swap_to": "USDT",
            }
        }
        mock_post.return_value = mock_response

        client = CryptoBotClient("test_token")
        invoice = client.create_invoice(
            asset=Asset.BTC,
            amount=25.00,
            description="Test invoice",
            hidden_message="Secret",
            paid_btn_name=ButtonName.viewItem,
            paid_btn_url="https://example.com",
            payload="custom_payload",
            allow_comments=False,
            allow_anonymous=False,
            expires_in=3600,
            swap_to="USDT",
        )

        assert invoice.description == "Test invoice"
        assert invoice.paid_btn_name == ButtonName.viewItem
        assert invoice.allow_comments is False

        # Verify request parameters
        call_args = mock_post.call_args
        json_data = call_args[1]["json"]
        assert json_data["description"] == "Test invoice"
        assert json_data["paid_btn_name"] == "viewItem"
        assert json_data["expires_in"] == 3600

    @patch("httpx.Client.post")
    def test_create_invoice_error(self, mock_post):
        """Test create_invoice with error response."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": {
                "code": 400,
                "name": "BAD_REQUEST",
                "description": "Invalid amount",
            }
        }
        mock_post.return_value = mock_response

        client = CryptoBotClient("test_token")

        with pytest.raises(CryptoBotError) as exc_info:
            client.create_invoice(Asset.BTC, 0.00001)  # Too small amount

        error = exc_info.value
        assert error.code == 400
        assert error.name == "BAD_REQUEST"

    @patch("httpx.Client.post")
    def test_create_invoice_validates_expires_in_range(self, mock_post):
        client = CryptoBotClient("test_token")

        with pytest.raises(ValueError, match="expires_in must be between 1 and 2678400 seconds"):
            client.create_invoice(Asset.TON, 1, expires_in=0)

        with pytest.raises(ValueError, match="expires_in must be between 1 and 2678400 seconds"):
            client.create_invoice(Asset.TON, 1, expires_in=2678401)

        mock_post.assert_not_called()


class TestCryptoBotClientTransfer:
    """Tests for transfer method."""

    @patch("httpx.Client.post")
    def test_transfer_success(self, mock_post):
        """Test successful transfer."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "result": {
                "transfer_id": 789,
                "user_id": 12345,
                "asset": "TON",
                "amount": "5.0",
                "status": "completed",
                "completed_at": "2023-01-01T12:00:00Z",
                "comment": "Payment for services",
            }
        }
        mock_post.return_value = mock_response

        client = CryptoBotClient("test_token")
        transfer = client.transfer(
            user_id=12345,
            asset=Asset.TON,
            amount=5.0,
            spend_id="unique_id_123",
            comment="Payment for services",
        )

        assert isinstance(transfer, Transfer)
        assert transfer.transfer_id == 789
        assert transfer.user_id == 12345
        assert transfer.asset == Asset.TON
        assert transfer.amount == "5.0"
        assert transfer.status == TransferStatus.completed
        assert transfer.comment == "Payment for services"

    @patch("httpx.Client.post")
    def test_transfer_insufficient_funds(self, mock_post):
        """Test transfer with insufficient funds error."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": {
                "code": 400,
                "name": "INSUFFICIENT_FUNDS",
                "description": "Not enough balance",
            }
        }
        mock_post.return_value = mock_response

        client = CryptoBotClient("test_token")

        with pytest.raises(CryptoBotError) as exc_info:
            client.transfer(user_id=12345, asset=Asset.BTC, amount=100.0, spend_id="test_id")

        error = exc_info.value
        assert error.name == "INSUFFICIENT_FUNDS"


class TestCryptoBotClientGetInvoices:
    """Tests for get_invoices method."""

    @patch("httpx.Client.get")
    def test_get_invoices_all(self, mock_get):
        """Test getting all invoices."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "result": {
                "items": [
                    {
                        "invoice_id": 123,
                        "status": "paid",
                        "hash": "abc123",
                        "amount": "10.0",
                        "asset": "USDT",
                    },
                    {
                        "invoice_id": 456,
                        "status": "active",
                        "hash": "def456",
                        "amount": "25.0",
                        "asset": "BTC",
                    },
                ]
            }
        }
        mock_get.return_value = mock_response

        client = CryptoBotClient("test_token")
        invoices = client.get_invoices()

        assert len(invoices) == 2
        assert all(isinstance(invoice, Invoice) for invoice in invoices)
        assert invoices[0].invoice_id == 123
        assert invoices[1].invoice_id == 456

    @patch("httpx.Client.get")
    def test_get_invoices_with_filters(self, mock_get):
        """Test getting invoices with filters."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "result": {
                "items": [
                    {
                        "invoice_id": 789,
                        "status": "paid",
                        "hash": "ghi789",
                        "amount": "50.0",
                        "asset": "USDT",
                    }
                ]
            }
        }
        mock_get.return_value = mock_response

        client = CryptoBotClient("test_token")
        invoices = client.get_invoices(asset=Asset.USDT, status=Status.paid, offset=10, count=5)

        assert len(invoices) == 1
        assert invoices[0].status == Status.paid

        # Check request parameters
        call_args = mock_get.call_args
        params = call_args[1]["params"]
        assert params["asset"] == "USDT"
        assert params["status"] == "paid"
        assert params["offset"] == 10
        assert params["count"] == 5

    @patch("httpx.Client.get")
    def test_get_invoices_accepts_list_invoice_ids(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": {"items": []}}
        mock_get.return_value = mock_response

        client = CryptoBotClient("test_token")
        client.get_invoices(invoice_ids=[123, 456, 789], count=10)

        params = mock_get.call_args[1]["params"]
        assert params["invoice_ids"] == "123,456,789"
        assert params["count"] == 10

    def test_get_invoices_validates_count_range(self):
        client = CryptoBotClient("test_token")

        with pytest.raises(ValueError, match="count must be between 1 and 1000"):
            client.get_invoices(count=0)

        with pytest.raises(ValueError, match="count must be between 1 and 1000"):
            client.get_invoices(count=1001)

    def test_get_invoices_validates_offset(self):
        client = CryptoBotClient("test_token")

        with pytest.raises(ValueError, match="offset must be greater than or equal to 0"):
            client.get_invoices(offset=-1)

    def test_get_invoices_validates_invoice_ids(self):
        client = CryptoBotClient("test_token")

        with pytest.raises(ValueError, match="invoice_ids string must contain positive integer IDs"):
            client.get_invoices(invoice_ids="1,-2,3")

        with pytest.raises(ValueError, match="invoice_ids list must contain positive integers"):
            client.get_invoices(invoice_ids=[1, -2, 3])

        with pytest.raises(TypeError, match="invoice_ids must be a comma-separated string or list of integers"):
            client.get_invoices(invoice_ids=123)  # type: ignore[arg-type]


class TestCryptoBotClientInvoiceIterators:
    """Tests for paginated invoice helpers."""

    @patch("httpx.Client.get")
    def test_iter_invoice_pages(self, mock_get):
        page1 = Mock()
        page1.status_code = 200
        page1.json.return_value = {
            "result": {
                "items": [
                    {"invoice_id": 1, "status": "active", "hash": "h1", "amount": "1", "asset": "TON"},
                    {"invoice_id": 2, "status": "active", "hash": "h2", "amount": "1", "asset": "TON"},
                ]
            }
        }
        page2 = Mock()
        page2.status_code = 200
        page2.json.return_value = {
            "result": {
                "items": [
                    {"invoice_id": 3, "status": "paid", "hash": "h3", "amount": "2", "asset": "TON"},
                ]
            }
        }
        mock_get.side_effect = [page1, page2]

        client = CryptoBotClient("test_token")
        pages = list(client.iter_invoice_pages(page_size=2))

        assert len(pages) == 2
        assert [invoice.invoice_id for invoice in pages[0]] == [1, 2]
        assert [invoice.invoice_id for invoice in pages[1]] == [3]

    @patch("httpx.Client.get")
    def test_iter_invoices_flattens_pages(self, mock_get):
        page1 = Mock()
        page1.status_code = 200
        page1.json.return_value = {
            "result": {
                "items": [
                    {"invoice_id": 10, "status": "active", "hash": "a", "amount": "1", "asset": "USDT"},
                    {"invoice_id": 11, "status": "active", "hash": "b", "amount": "1", "asset": "USDT"},
                ]
            }
        }
        page2 = Mock()
        page2.status_code = 200
        page2.json.return_value = {"result": {"items": []}}
        mock_get.side_effect = [page1, page2]

        client = CryptoBotClient("test_token")
        invoice_ids = [invoice.invoice_id for invoice in client.iter_invoices(page_size=2)]

        assert invoice_ids == [10, 11]


class TestCryptoBotClientGetBalances:
    """Tests for get_balances method."""

    @patch("httpx.Client.get")
    def test_get_balances_success(self, mock_get):
        """Test successful get_balances request."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "result": [
                {"currency_code": "BTC", "available": "1.5", "onhold": "0.1"},
                {"currency_code": "USDT", "available": "1000.0", "onhold": "50.0"},
            ]
        }
        mock_get.return_value = mock_response

        client = CryptoBotClient("test_token")
        balances = client.get_balances()

        assert len(balances) == 2
        assert all(isinstance(balance, Balance) for balance in balances)
        assert balances[0].currency_code == "BTC"
        assert balances[0].available == "1.5"
        assert balances[1].currency_code == "USDT"


class TestCryptoBotClientGetExchangeRates:
    """Tests for get_exchange_rates method."""

    @patch("httpx.Client.get")
    def test_get_exchange_rates_success(self, mock_get):
        """Test successful get_exchange_rates request."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "result": [
                {
                    "is_valid": True,
                    "is_crypto": True,
                    "is_fiat": False,
                    "source": "BTC",
                    "target": "USD",
                    "rate": "50000.00",
                },
                {
                    "is_valid": True,
                    "is_crypto": True,
                    "is_fiat": False,
                    "source": "ETH",
                    "target": "USD",
                    "rate": "3000.00",
                },
            ]
        }
        mock_get.return_value = mock_response

        client = CryptoBotClient("test_token")
        rates = client.get_exchange_rates()

        assert len(rates) == 2
        assert all(isinstance(rate, ExchangeRate) for rate in rates)
        assert rates[0].source == Asset.BTC
        assert rates[0].target == "USD"
        assert rates[0].rate == "50000.00"


class TestCryptoBotClientGetCurrencies:
    """Tests for get_currencies method."""

    @patch("httpx.Client.get")
    def test_get_currencies_success(self, mock_get):
        """Test successful get_currencies request."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "result": [
                {
                    "is_blockchain": True,
                    "is_stablecoin": False,
                    "is_fiat": False,
                    "name": "Bitcoin",
                    "code": "BTC",
                    "decimals": 8,
                },
                {
                    "is_blockchain": True,
                    "is_stablecoin": True,
                    "is_fiat": False,
                    "name": "Tether",
                    "code": "USDT",
                    "decimals": 6,
                    "url": "https://tether.to",
                },
            ]
        }
        mock_get.return_value = mock_response

        client = CryptoBotClient("test_token")
        currencies = client.get_currencies()

        assert len(currencies) == 2
        assert all(isinstance(currency, Currency) for currency in currencies)
        assert currencies[0].name == "Bitcoin"
        assert currencies[0].code == "BTC"
        assert currencies[1].is_stablecoin is True


class TestCryptoBotClientErrorHandling:
    """Tests for error handling across all methods."""

    @patch("httpx.Client.get")
    def test_network_error_handling(self, mock_get):
        """Test handling of network errors."""
        mock_get.side_effect = httpx.NetworkError("Connection failed")

        client = CryptoBotClient("test_token")

        with pytest.raises(httpx.NetworkError):
            client.get_me()

    @patch("httpx.Client.post")
    def test_timeout_error_handling(self, mock_post):
        """Test handling of timeout errors."""
        mock_post.side_effect = httpx.TimeoutException("Request timed out")

        client = CryptoBotClient("test_token")

        with pytest.raises(httpx.TimeoutException):
            client.create_invoice(Asset.BTC, 1.0)

    @patch("httpx.Client.get")
    def test_json_decode_error(self, mock_get):
        """Test handling of invalid JSON responses."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_response

        client = CryptoBotClient("test_token")

        with pytest.raises(CryptoBotError) as exc_info:
            client.get_balances()
        assert exc_info.value.name.startswith("Invalid JSON response:")

    @patch("httpx.Client.get")
    def test_unexpected_response_structure(self, mock_get):
        """Test handling of unexpected response structure."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"unexpected": "structure"}
        mock_get.return_value = mock_response

        client = CryptoBotClient("test_token")

        with pytest.raises(CryptoBotError) as exc_info:
            client.get_me()
        assert exc_info.value.code == 200
        assert exc_info.value.name == "Malformed success response: missing 'result'"

    def test_invalid_asset_enum(self):
        """Test validation of asset enum values."""
        # This should work fine with valid Asset enum
        assert Asset.BTC.name == "BTC"

        # Invalid asset values would be caught at the enum level
        with pytest.raises(KeyError):
            Asset["INVALID_ASSET"]
