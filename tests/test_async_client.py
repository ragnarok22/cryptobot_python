#!/usr/bin/env python

"""Tests for AsyncCryptoBotClient with mocked HTTP responses."""

from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from cryptobot import AsyncCryptoBotClient
from cryptobot.errors import CryptoBotError
from cryptobot.models import App, Asset, Balance, Currency, ExchangeRate, Invoice, Status, Transfer


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
    @patch("httpx.AsyncClient.post", new_callable=AsyncMock)
    async def test_create_invoice_validates_expires_in_range(self, mock_post):
        client = AsyncCryptoBotClient("test_token")

        with pytest.raises(ValueError, match="expires_in must be between 1 and 2678400 seconds"):
            await client.create_invoice(Asset.TON, 1, expires_in=0)

        with pytest.raises(ValueError, match="expires_in must be between 1 and 2678400 seconds"):
            await client.create_invoice(Asset.TON, 1, expires_in=2678401)

        mock_post.assert_not_awaited()
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
        assert rates[0].source == Asset.BTC
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
