#!/usr/bin/env python

"""Tests for AsyncCryptoBotClient with mocked HTTP responses."""

from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from cryptobot import AsyncCryptoBotClient
from cryptobot.errors import CryptoBotError
from cryptobot.models import (
    App,
    AppStats,
    Asset,
    Balance,
    ButtonName,
    Check,
    CheckStatus,
    Currency,
    ExchangeRate,
    Invoice,
    Status,
    Transfer,
)


def make_response(status_code, payload, headers=None):
    response = Mock()
    response.status_code = status_code
    response.headers = headers or {}
    response.json.return_value = payload
    return response


class TestAsyncCryptoBotClientInitialization:
    """Tests for AsyncCryptoBotClient initialization."""

    @pytest.mark.asyncio
    async def test_client_creation_mainnet(self):
        client = AsyncCryptoBotClient("test_token", is_mainnet=True)
        assert client.api_token == "test_token"
        assert client.timeout == 5.0
        assert "pay.crypt.bot" in str(client._http_client.base_url)
        await client.close()

    @pytest.mark.asyncio
    async def test_client_creation_testnet(self):
        client = AsyncCryptoBotClient("test_token", is_mainnet=False)
        assert "testnet-pay.crypt.bot" in str(client._http_client.base_url)
        await client.close()

    @pytest.mark.asyncio
    async def test_retry_configuration_defaults(self):
        client = AsyncCryptoBotClient("test_token")
        assert client.max_retries == 0
        assert client.retry_backoff == 0.5
        assert client.retryable_status_codes == {429, 500, 502, 503, 504}
        await client.close()

    @pytest.mark.asyncio
    async def test_retry_delay_uses_retry_after_header(self):
        client = AsyncCryptoBotClient("test_token", retry_backoff=0.5)
        response = make_response(429, {"error": {"code": 429, "name": "TOO_MANY_REQUESTS"}}, headers={"Retry-After": "2"})
        assert client._retry_delay(0, response) == 2.0
        await client.close()

    @pytest.mark.asyncio
    async def test_retry_delay_ignores_invalid_retry_after(self):
        client = AsyncCryptoBotClient("test_token", retry_backoff=0.5)
        response = make_response(429, {"error": {"code": 429, "name": "TOO_MANY_REQUESTS"}}, headers={"Retry-After": "abc"})
        assert client._retry_delay(0, response) == 0.5
        await client.close()

    @pytest.mark.asyncio
    async def test_async_context_manager_closes_http_client(self):
        async with AsyncCryptoBotClient("test_token") as client:
            assert not client._http_client.is_closed
        assert client._http_client.is_closed


class TestAsyncCryptoBotClientRetryPolicy:
    """Tests for async retry/backoff behavior."""

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get", new_callable=AsyncMock)
    async def test_retry_on_retryable_status_then_success(self, mock_get):
        retry_response = make_response(
            429,
            {"error": {"code": 429, "name": "TOO_MANY_REQUESTS"}},
        )
        ok_response = make_response(
            200,
            {
                "result": {
                    "app_id": 1,
                    "name": "Retry App",
                    "payment_processing_bot_username": "RetryBot",
                }
            },
        )

        mock_get.side_effect = [retry_response, ok_response]
        client = AsyncCryptoBotClient("test_token", max_retries=1, retry_backoff=0)
        app = await client.get_me()

        assert app.app_id == 1
        assert mock_get.await_count == 2
        await client.close()

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get", new_callable=AsyncMock)
    async def test_no_retry_on_non_retryable_status(self, mock_get):
        bad_request = make_response(400, {"error": {"code": 400, "name": "BAD_REQUEST"}})
        mock_get.return_value = bad_request

        client = AsyncCryptoBotClient("test_token", max_retries=3, retry_backoff=0)
        with pytest.raises(CryptoBotError) as exc_info:
            await client.get_me()

        assert exc_info.value.code == 400
        assert mock_get.await_count == 1
        await client.close()

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get", new_callable=AsyncMock)
    async def test_retry_on_timeout_exception_then_success(self, mock_get):
        ok_response = make_response(
            200,
            {
                "result": {
                    "app_id": 2,
                    "name": "Recovered App",
                    "payment_processing_bot_username": "RecoveredBot",
                }
            },
        )
        mock_get.side_effect = [httpx.TimeoutException("timeout"), ok_response]

        client = AsyncCryptoBotClient("test_token", max_retries=1, retry_backoff=0)
        app = await client.get_me()

        assert app.app_id == 2
        assert mock_get.await_count == 2
        await client.close()

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get", new_callable=AsyncMock)
    async def test_retry_timeout_exhausted_raises(self, mock_get):
        mock_get.side_effect = httpx.TimeoutException("timeout")
        client = AsyncCryptoBotClient("test_token", max_retries=0, retry_backoff=0.1)

        with pytest.raises(httpx.TimeoutException):
            await client.get_me()

        await client.close()

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get", new_callable=AsyncMock)
    @patch("cryptobot.client.asyncio.sleep", new_callable=AsyncMock)
    async def test_retry_timeout_sleep_called(self, mock_sleep, mock_get):
        ok_response = make_response(
            200,
            {"result": {"app_id": 3, "name": "Sleep App", "payment_processing_bot_username": "SleepBot"}},
        )
        mock_get.side_effect = [httpx.TimeoutException("timeout"), ok_response]

        client = AsyncCryptoBotClient("test_token", max_retries=1, retry_backoff=0.1)
        app = await client.get_me()

        assert app.app_id == 3
        mock_sleep.assert_awaited_once()
        await client.close()

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get", new_callable=AsyncMock)
    @patch("cryptobot.client.asyncio.sleep", new_callable=AsyncMock)
    async def test_retry_status_sleep_called(self, mock_sleep, mock_get):
        retry_response = make_response(
            429,
            {"error": {"code": 429, "name": "TOO_MANY_REQUESTS"}},
            headers={"Retry-After": "1"},
        )
        ok_response = make_response(
            200,
            {"result": {"app_id": 4, "name": "RetryAfter App", "payment_processing_bot_username": "RetryAfterBot"}},
        )
        mock_get.side_effect = [retry_response, ok_response]

        client = AsyncCryptoBotClient("test_token", max_retries=1, retry_backoff=0.1)
        app = await client.get_me()

        assert app.app_id == 4
        mock_sleep.assert_awaited_once()
        await client.close()


class TestAsyncCryptoBotClientMethods:
    """Tests for async client methods and parsing."""

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get", new_callable=AsyncMock)
    async def test_get_me_success(self, mock_get):
        mock_get.return_value = make_response(
            200,
            {"result": {"app_id": 12345, "name": "Test App", "payment_processing_bot_username": "TestBot"}},
        )

        client = AsyncCryptoBotClient("test_token")
        app = await client.get_me()

        assert isinstance(app, App)
        assert app.app_id == 12345
        assert app.name == "Test App"
        await client.close()

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get", new_callable=AsyncMock)
    async def test_get_me_invalid_json_error(self, mock_get):
        bad_response = Mock()
        bad_response.status_code = 500
        bad_response.text = "bad json"
        bad_response.json.side_effect = ValueError("invalid")
        mock_get.return_value = bad_response

        client = AsyncCryptoBotClient("test_token")
        with pytest.raises(CryptoBotError) as exc_info:
            await client.get_me()

        assert "Invalid JSON response" in exc_info.value.name
        await client.close()

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get", new_callable=AsyncMock)
    async def test_get_me_malformed_success_error(self, mock_get):
        mock_get.return_value = make_response(200, {"unexpected": "structure"})
        client = AsyncCryptoBotClient("test_token")

        with pytest.raises(CryptoBotError) as exc_info:
            await client.get_me()

        assert exc_info.value.code == 200
        assert exc_info.value.name == "Malformed success response: missing 'result'"
        await client.close()

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get", new_callable=AsyncMock)
    async def test_get_me_http_error_fallback(self, mock_get):
        mock_get.return_value = make_response(502, {"detail": "gateway"})
        client = AsyncCryptoBotClient("test_token")

        with pytest.raises(CryptoBotError) as exc_info:
            await client.get_me()

        assert exc_info.value.code == 502
        assert exc_info.value.name.startswith("HTTPError:")
        await client.close()

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post", new_callable=AsyncMock)
    async def test_create_invoice_validates_expires_in_range(self, mock_post):
        client = AsyncCryptoBotClient("test_token")

        with pytest.raises(ValueError, match="expires_in must be between 1 and 2678400 seconds"):
            await client.create_invoice(1, asset=Asset.TON, expires_in=0)

        with pytest.raises(ValueError, match="expires_in must be between 1 and 2678400 seconds"):
            await client.create_invoice(1, asset=Asset.TON, expires_in=2678401)

        mock_post.assert_not_awaited()
        await client.close()

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post", new_callable=AsyncMock)
    async def test_create_invoice_success_with_paid_button(self, mock_post):
        mock_post.return_value = make_response(
            200,
            {
                "result": {
                    "invoice_id": 10,
                    "status": "active",
                    "hash": "hash10",
                    "amount": "1.0",
                    "asset": "USDT",
                    "paid_btn_name": "viewItem",
                }
            },
        )
        client = AsyncCryptoBotClient("test_token")
        invoice = await client.create_invoice(
            asset=Asset.USDT,
            amount=1.0,
            description="test",
            paid_btn_name=ButtonName.viewItem,
        )
        assert isinstance(invoice, Invoice)

        sent_json = mock_post.call_args.kwargs["json"]
        assert sent_json["paid_btn_name"] == "viewItem"
        assert sent_json["description"] == "test"
        await client.close()

    @pytest.mark.asyncio
    async def test_create_invoice_validates_amount(self):
        client = AsyncCryptoBotClient("test_token")
        with pytest.raises(ValueError, match="Amount must be greater than 0"):
            await client.create_invoice(0, asset=Asset.USDT)
        await client.close()

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get", new_callable=AsyncMock)
    async def test_get_invoices_accepts_list_invoice_ids(self, mock_get):
        mock_get.return_value = make_response(200, {"result": {"items": []}})

        client = AsyncCryptoBotClient("test_token")
        await client.get_invoices(invoice_ids=[123, 456], count=10)

        params = mock_get.call_args.kwargs["params"]
        assert params["invoice_ids"] == "123,456"
        assert params["count"] == 10
        await client.close()

    @pytest.mark.asyncio
    async def test_get_invoices_validates_count_range(self):
        client = AsyncCryptoBotClient("test_token")

        with pytest.raises(ValueError, match="count must be between 1 and 1000"):
            await client.get_invoices(count=0)

        with pytest.raises(ValueError, match="count must be between 1 and 1000"):
            await client.get_invoices(count=1001)

        await client.close()

    @pytest.mark.asyncio
    async def test_get_invoices_validates_offset(self):
        client = AsyncCryptoBotClient("test_token")
        with pytest.raises(ValueError, match="offset must be greater than or equal to 0"):
            await client.get_invoices(offset=-1)
        await client.close()

    @pytest.mark.asyncio
    async def test_get_invoices_validates_invoice_ids_input(self):
        client = AsyncCryptoBotClient("test_token")

        with pytest.raises(ValueError, match="invoice_ids string cannot be empty"):
            await client.get_invoices(invoice_ids=" , ")
        with pytest.raises(ValueError, match="invoice_ids string must contain positive integer IDs"):
            await client.get_invoices(invoice_ids="1,-2")
        with pytest.raises(ValueError, match="invoice_ids list cannot be empty"):
            await client.get_invoices(invoice_ids=[])
        with pytest.raises(ValueError, match="invoice_ids list must contain positive integers"):
            await client.get_invoices(invoice_ids=[1, -2])
        with pytest.raises(TypeError, match="invoice_ids must be a comma-separated string or list of integers"):
            await client.get_invoices(invoice_ids=123)  # type: ignore[arg-type]

        await client.close()

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get", new_callable=AsyncMock)
    async def test_get_invoices_sets_asset_filter(self, mock_get):
        mock_get.return_value = make_response(200, {"result": {"items": []}})
        client = AsyncCryptoBotClient("test_token")
        await client.get_invoices(asset=Asset.USDT, count=5)
        params = mock_get.call_args.kwargs["params"]
        assert params["asset"] == "USDT"
        await client.close()

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get", new_callable=AsyncMock)
    async def test_get_balances_success(self, mock_get):
        mock_get.return_value = make_response(
            200,
            {"result": [{"currency_code": "BTC", "available": "1.5", "onhold": "0.1"}]},
        )
        client = AsyncCryptoBotClient("test_token")
        balances = await client.get_balances()

        assert len(balances) == 1
        assert isinstance(balances[0], Balance)
        assert balances[0].currency_code == "BTC"
        await client.close()

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get", new_callable=AsyncMock)
    async def test_get_exchange_rates_success(self, mock_get):
        mock_get.return_value = make_response(
            200,
            {
                "result": [
                    {
                        "is_valid": True,
                        "is_crypto": True,
                        "is_fiat": False,
                        "source": "BTC",
                        "target": "USD",
                        "rate": "50000.00",
                    }
                ]
            },
        )
        client = AsyncCryptoBotClient("test_token")
        rates = await client.get_exchange_rates()

        assert len(rates) == 1
        assert isinstance(rates[0], ExchangeRate)
        assert rates[0].source == "BTC"
        await client.close()

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get", new_callable=AsyncMock)
    async def test_get_currencies_success(self, mock_get):
        mock_get.return_value = make_response(
            200,
            {
                "result": [
                    {
                        "is_blockchain": True,
                        "is_stablecoin": False,
                        "is_fiat": False,
                        "name": "Bitcoin",
                        "code": "BTC",
                        "decimals": 8,
                    }
                ]
            },
        )
        client = AsyncCryptoBotClient("test_token")
        currencies = await client.get_currencies()

        assert len(currencies) == 1
        assert isinstance(currencies[0], Currency)
        assert currencies[0].code == "BTC"
        await client.close()

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post", new_callable=AsyncMock)
    async def test_transfer_success(self, mock_post):
        mock_post.return_value = make_response(
            200,
            {
                "result": {
                    "transfer_id": 789,
                    "user_id": 12345,
                    "asset": "TON",
                    "amount": "5.0",
                    "status": "completed",
                    "completed_at": "2023-01-01T12:00:00Z",
                }
            },
        )
        client = AsyncCryptoBotClient("test_token")
        transfer = await client.transfer(user_id=12345, asset=Asset.TON, amount=5.0, spend_id="spend_123")

        assert isinstance(transfer, Transfer)
        assert transfer.transfer_id == 789
        assert transfer.asset == Asset.TON
        await client.close()

    @pytest.mark.asyncio
    async def test_transfer_validates_amount(self):
        client = AsyncCryptoBotClient("test_token")
        with pytest.raises(ValueError, match="Amount must be greater than 0"):
            await client.transfer(user_id=1, asset=Asset.TON, amount=0, spend_id="spend")
        await client.close()

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get", new_callable=AsyncMock)
    async def test_iter_invoice_pages(self, mock_get):
        page1 = make_response(
            200,
            {
                "result": {
                    "items": [
                        {"invoice_id": 1, "status": "active", "hash": "h1", "amount": "1", "asset": "TON"},
                        {"invoice_id": 2, "status": "active", "hash": "h2", "amount": "1", "asset": "TON"},
                    ]
                }
            },
        )
        page2 = make_response(
            200,
            {"result": {"items": [{"invoice_id": 3, "status": "paid", "hash": "h3", "amount": "2", "asset": "TON"}]}},
        )
        mock_get.side_effect = [page1, page2]

        client = AsyncCryptoBotClient("test_token")
        pages = []
        async for page in client.iter_invoice_pages(page_size=2):
            pages.append(page)

        assert len(pages) == 2
        assert [invoice.invoice_id for invoice in pages[0]] == [1, 2]
        assert [invoice.invoice_id for invoice in pages[1]] == [3]
        await client.close()

    @pytest.mark.asyncio
    async def test_iter_invoice_pages_validates_start_offset(self):
        client = AsyncCryptoBotClient("test_token")
        with pytest.raises(ValueError, match="start_offset must be greater than or equal to 0"):
            async for _ in client.iter_invoice_pages(start_offset=-1):
                pass
        await client.close()

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get", new_callable=AsyncMock)
    async def test_iter_invoices_flattens_pages(self, mock_get):
        page1 = make_response(
            200,
            {
                "result": {
                    "items": [
                        {"invoice_id": 10, "status": "active", "hash": "a", "amount": "1", "asset": "USDT"},
                        {"invoice_id": 11, "status": "active", "hash": "b", "amount": "1", "asset": "USDT"},
                    ]
                }
            },
        )
        page2 = make_response(200, {"result": {"items": []}})
        mock_get.side_effect = [page1, page2]

        client = AsyncCryptoBotClient("test_token")
        invoice_ids = []
        async for invoice in client.iter_invoices(page_size=2):
            invoice_ids.append(invoice.invoice_id)

        assert invoice_ids == [10, 11]
        await client.close()

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get", new_callable=AsyncMock)
    async def test_get_invoices_returns_models(self, mock_get):
        mock_get.return_value = make_response(
            200,
            {
                "result": {
                    "items": [
                        {"invoice_id": 123, "status": "paid", "hash": "abc123", "amount": "10.0", "asset": "USDT"},
                    ]
                }
            },
        )
        client = AsyncCryptoBotClient("test_token")
        invoices = await client.get_invoices(status=Status.paid)

        assert len(invoices) == 1
        assert isinstance(invoices[0], Invoice)
        assert invoices[0].status == Status.paid
        await client.close()


class TestAsyncCryptoBotClientNewMethods:
    """Tests for new async client methods."""

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post", new_callable=AsyncMock)
    async def test_create_invoice_fiat(self, mock_post):
        mock_post.return_value = make_response(
            200,
            {
                "result": {
                    "invoice_id": 500,
                    "status": "active",
                    "hash": "fiat500",
                    "amount": "10.00",
                    "currency_type": "fiat",
                    "fiat": "USD",
                    "bot_invoice_url": "https://t.me/CryptoBot?start=fiat500",
                }
            },
        )
        client = AsyncCryptoBotClient("test_token")
        invoice = await client.create_invoice(10.00, currency_type="fiat", fiat="USD")

        assert isinstance(invoice, Invoice)
        assert invoice.currency_type == "fiat"
        assert invoice.fiat == "USD"
        assert invoice.asset is None

        json_data = mock_post.call_args.kwargs["json"]
        assert json_data["currency_type"] == "fiat"
        assert json_data["fiat"] == "USD"
        assert "asset" not in json_data
        await client.close()

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post", new_callable=AsyncMock)
    async def test_delete_invoice_success(self, mock_post):
        mock_post.return_value = make_response(200, {"result": True})
        client = AsyncCryptoBotClient("test_token")
        result = await client.delete_invoice(123)

        assert result is True
        assert mock_post.call_args.kwargs["json"]["invoice_id"] == 123
        await client.close()

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post", new_callable=AsyncMock)
    async def test_create_check_success(self, mock_post):
        mock_post.return_value = make_response(
            200,
            {
                "result": {
                    "check_id": 100,
                    "hash": "check_hash",
                    "asset": "TON",
                    "amount": "5.0",
                    "bot_check_url": "https://t.me/CryptoBot?start=check_hash",
                    "status": "active",
                    "created_at": "2026-01-15T00:00:00Z",
                }
            },
        )
        client = AsyncCryptoBotClient("test_token")
        check = await client.create_check(Asset.TON, 5.0)

        assert isinstance(check, Check)
        assert check.check_id == 100
        assert check.asset == Asset.TON
        assert check.status == CheckStatus.active
        await client.close()

    @pytest.mark.asyncio
    async def test_create_check_validates_amount(self):
        client = AsyncCryptoBotClient("test_token")
        with pytest.raises(ValueError, match="Amount must be greater than 0"):
            await client.create_check(Asset.TON, 0)
        await client.close()

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post", new_callable=AsyncMock)
    async def test_create_check_with_pin(self, mock_post):
        mock_post.return_value = make_response(
            200,
            {
                "result": {
                    "check_id": 101,
                    "hash": "pinned",
                    "asset": "USDT",
                    "amount": "10.0",
                    "bot_check_url": "https://t.me/CryptoBot?start=pinned",
                    "status": "active",
                    "created_at": "2026-01-15T00:00:00Z",
                }
            },
        )
        client = AsyncCryptoBotClient("test_token")
        await client.create_check(Asset.USDT, 10.0, pin_to_user_id=12345)

        json_data = mock_post.call_args.kwargs["json"]
        assert json_data["pin_to_user_id"] == 12345
        await client.close()

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post", new_callable=AsyncMock)
    async def test_delete_check_success(self, mock_post):
        mock_post.return_value = make_response(200, {"result": True})
        client = AsyncCryptoBotClient("test_token")
        result = await client.delete_check(100)

        assert result is True
        assert mock_post.call_args.kwargs["json"]["check_id"] == 100
        await client.close()

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get", new_callable=AsyncMock)
    async def test_get_transfers_success(self, mock_get):
        mock_get.return_value = make_response(
            200,
            {
                "result": {
                    "items": [
                        {
                            "transfer_id": 1,
                            "user_id": 100,
                            "asset": "TON",
                            "amount": "5.0",
                            "status": "completed",
                            "completed_at": "2026-01-10T12:00:00Z",
                            "spend_id": "spend_1",
                        }
                    ]
                }
            },
        )
        client = AsyncCryptoBotClient("test_token")
        transfers = await client.get_transfers()

        assert len(transfers) == 1
        assert isinstance(transfers[0], Transfer)
        assert transfers[0].spend_id == "spend_1"
        await client.close()

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get", new_callable=AsyncMock)
    async def test_get_transfers_with_filters(self, mock_get):
        mock_get.return_value = make_response(200, {"result": {"items": []}})
        client = AsyncCryptoBotClient("test_token")
        await client.get_transfers(asset=Asset.TON, spend_id="test", offset=5, count=10)

        params = mock_get.call_args.kwargs["params"]
        assert params["asset"] == "TON"
        assert params["spend_id"] == "test"
        assert params["offset"] == 5
        assert params["count"] == 10
        await client.close()

    @pytest.mark.asyncio
    async def test_get_transfers_validates_count(self):
        client = AsyncCryptoBotClient("test_token")
        with pytest.raises(ValueError, match="count must be between 1 and 1000"):
            await client.get_transfers(count=0)
        await client.close()

    @pytest.mark.asyncio
    async def test_get_transfers_validates_offset(self):
        client = AsyncCryptoBotClient("test_token")
        with pytest.raises(ValueError, match="offset must be greater than or equal to 0"):
            await client.get_transfers(offset=-1)
        await client.close()

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get", new_callable=AsyncMock)
    async def test_get_checks_success(self, mock_get):
        mock_get.return_value = make_response(
            200,
            {
                "result": {
                    "items": [
                        {
                            "check_id": 1,
                            "hash": "h1",
                            "asset": "TON",
                            "amount": "5.0",
                            "bot_check_url": "https://t.me/CryptoBot?start=h1",
                            "status": "active",
                            "created_at": "2026-03-01T00:00:00Z",
                        },
                        {
                            "check_id": 2,
                            "hash": "h2",
                            "asset": "USDT",
                            "amount": "10.0",
                            "bot_check_url": "https://t.me/CryptoBot?start=h2",
                            "status": "activated",
                            "created_at": "2026-03-01T00:00:00Z",
                            "activated_at": "2026-03-02T00:00:00Z",
                        },
                    ]
                }
            },
        )
        client = AsyncCryptoBotClient("test_token")
        checks = await client.get_checks()

        assert len(checks) == 2
        assert all(isinstance(c, Check) for c in checks)
        assert checks[0].status == CheckStatus.active
        assert checks[1].status == CheckStatus.activated
        assert checks[1].activated_at == "2026-03-02T00:00:00Z"
        await client.close()

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get", new_callable=AsyncMock)
    async def test_get_checks_with_filters(self, mock_get):
        mock_get.return_value = make_response(200, {"result": {"items": []}})
        client = AsyncCryptoBotClient("test_token")
        await client.get_checks(asset=Asset.TON, status=CheckStatus.active, count=5)

        params = mock_get.call_args.kwargs["params"]
        assert params["asset"] == "TON"
        assert params["status"] == "active"
        assert params["count"] == 5
        await client.close()

    @pytest.mark.asyncio
    async def test_get_checks_validates_count(self):
        client = AsyncCryptoBotClient("test_token")
        with pytest.raises(ValueError, match="count must be between 1 and 1000"):
            await client.get_checks(count=1001)
        await client.close()

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get", new_callable=AsyncMock)
    async def test_get_stats_default(self, mock_get):
        mock_get.return_value = make_response(
            200,
            {
                "result": {
                    "volume": 1500.50,
                    "conversion": 0.45,
                    "unique_users_count": 120,
                    "created_invoice_count": 500,
                    "paid_invoice_count": 225,
                    "start_at": "2026-03-17T00:00:00Z",
                    "end_at": "2026-03-18T00:00:00Z",
                }
            },
        )
        client = AsyncCryptoBotClient("test_token")
        stats = await client.get_stats()

        assert isinstance(stats, AppStats)
        assert stats.volume == 1500.50
        assert stats.conversion == 0.45
        assert stats.unique_users_count == 120
        await client.close()

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get", new_callable=AsyncMock)
    async def test_get_stats_with_dates(self, mock_get):
        mock_get.return_value = make_response(
            200,
            {
                "result": {
                    "volume": 500.00,
                    "conversion": 0.30,
                    "unique_users_count": 50,
                    "created_invoice_count": 100,
                    "paid_invoice_count": 30,
                    "start_at": "2026-03-01T00:00:00Z",
                    "end_at": "2026-03-15T23:59:59Z",
                }
            },
        )
        client = AsyncCryptoBotClient("test_token")
        await client.get_stats(
            start_at="2026-03-01T00:00:00Z",
            end_at="2026-03-15T23:59:59Z",
        )

        params = mock_get.call_args.kwargs["params"]
        assert params["start_at"] == "2026-03-01T00:00:00Z"
        assert params["end_at"] == "2026-03-15T23:59:59Z"
        await client.close()

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get", new_callable=AsyncMock)
    async def test_get_invoices_fiat_filter(self, mock_get):
        mock_get.return_value = make_response(200, {"result": {"items": []}})
        client = AsyncCryptoBotClient("test_token")
        await client.get_invoices(fiat="USD")

        params = mock_get.call_args.kwargs["params"]
        assert params["fiat"] == "USD"
        await client.close()

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get", new_callable=AsyncMock)
    async def test_iter_transfer_pages(self, mock_get):
        page1 = make_response(
            200,
            {
                "result": {
                    "items": [
                        {
                            "transfer_id": 1,
                            "user_id": 100,
                            "asset": "TON",
                            "amount": "1",
                            "status": "completed",
                            "completed_at": "2026-01-01T00:00:00Z",
                        },
                        {
                            "transfer_id": 2,
                            "user_id": 200,
                            "asset": "TON",
                            "amount": "2",
                            "status": "completed",
                            "completed_at": "2026-01-01T00:00:00Z",
                        },
                    ]
                }
            },
        )
        page2 = make_response(
            200,
            {
                "result": {
                    "items": [
                        {
                            "transfer_id": 3,
                            "user_id": 300,
                            "asset": "TON",
                            "amount": "3",
                            "status": "completed",
                            "completed_at": "2026-01-01T00:00:00Z",
                        },
                    ]
                }
            },
        )
        mock_get.side_effect = [page1, page2]

        client = AsyncCryptoBotClient("test_token")
        pages = []
        async for page in client.iter_transfer_pages(page_size=2):
            pages.append(page)

        assert len(pages) == 2
        assert [t.transfer_id for t in pages[0]] == [1, 2]
        assert [t.transfer_id for t in pages[1]] == [3]
        await client.close()

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get", new_callable=AsyncMock)
    async def test_iter_check_pages(self, mock_get):
        page1 = make_response(
            200,
            {
                "result": {
                    "items": [
                        {
                            "check_id": 1,
                            "hash": "h1",
                            "asset": "TON",
                            "amount": "1",
                            "bot_check_url": "url1",
                            "status": "active",
                            "created_at": "2026-03-01T00:00:00Z",
                        },
                    ]
                }
            },
        )
        page2 = make_response(200, {"result": {"items": []}})
        mock_get.side_effect = [page1, page2]

        client = AsyncCryptoBotClient("test_token")
        ids = []
        async for check in client.iter_checks(page_size=2):
            ids.append(check.check_id)

        assert ids == [1]
        await client.close()
