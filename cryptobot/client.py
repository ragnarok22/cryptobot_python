import asyncio
from collections.abc import AsyncIterator, Awaitable
from contextlib import suppress
from types import TracebackType
from typing import Any, Callable, List, Optional, Set, Union

import httpx

from ._utils import parse_json
from .errors import CryptoBotError
from .models import (
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


class AsyncCryptoBotClient:
    """Async Crypto Bot API client for modern service workloads."""

    @staticmethod
    def _short_text(response: httpx.Response, limit: int = 100) -> str:
        return str(getattr(response, "text", ""))[:limit]

    def __init__(
        self,
        api_token: str,
        is_mainnet: bool = True,
        timeout: float = 5.0,
        max_retries: int = 0,
        retry_backoff: float = 0.5,
        retryable_status_codes: Optional[Set[int]] = None,
    ):
        self.api_token = api_token
        self.timeout = timeout
        self.max_retries = max(0, max_retries)
        self.retry_backoff = max(0.0, retry_backoff)
        self.retryable_status_codes = (
            set(retryable_status_codes) if retryable_status_codes is not None else {429, 500, 502, 503, 504}
        )
        self._base_url = "https://pay.crypt.bot/api" if is_mainnet else "https://testnet-pay.crypt.bot/api"
        self._http_client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=self.timeout,
            headers={"Crypto-Pay-API-Token": self.api_token},
        )

    def _retry_delay(self, attempt: int, response: Optional[httpx.Response] = None) -> float:
        delay: float = self.retry_backoff * (2**attempt)

        if response is not None:
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                with suppress(ValueError):
                    delay = max(delay, float(retry_after))

        return delay if delay > 0.0 else 0.0

    async def _execute_with_retry(
        self, request_fn: Callable[..., Awaitable[httpx.Response]], *args: Any, **kwargs: Any
    ) -> httpx.Response:
        retryable_exceptions = (
            httpx.TimeoutException,
            httpx.NetworkError,
            httpx.RemoteProtocolError,
        )

        for attempt in range(self.max_retries + 1):
            try:
                response = await request_fn(*args, **kwargs)
            except retryable_exceptions:
                if attempt >= self.max_retries:
                    raise
                delay = self._retry_delay(attempt)
                if delay > 0:
                    await asyncio.sleep(delay)
                continue

            if response.status_code in self.retryable_status_codes and attempt < self.max_retries:
                delay = self._retry_delay(attempt, response)
                if delay > 0:
                    await asyncio.sleep(delay)
                continue

            return response

        raise RuntimeError("Unexpected retry flow state")  # pragma: no cover

    def _handle_response(self, response: httpx.Response) -> Any:
        try:
            payload = response.json()
        except ValueError as exc:
            raise CryptoBotError(
                code=response.status_code,
                name=f"Invalid JSON response: {self._short_text(response)}",
            ) from exc

        if response.status_code == 200:
            if isinstance(payload, dict) and "result" in payload:
                return payload["result"]
            raise CryptoBotError(
                code=200,
                name="Malformed success response: missing 'result'",
            )

        if isinstance(payload, dict) and isinstance(payload.get("error"), dict):
            raise CryptoBotError.from_json(payload["error"])

        raise CryptoBotError(
            code=response.status_code,
            name=f"HTTPError: {self._short_text(response)}",
        )

    async def close(self) -> None:
        await self._http_client.aclose()

    async def __aenter__(self) -> "AsyncCryptoBotClient":
        return self

    async def __aexit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> None:
        await self.close()

    @staticmethod
    def _validate_count(count: int) -> None:
        if count < 1 or count > 1000:
            raise ValueError("count must be between 1 and 1000")

    @staticmethod
    def _validate_expires_in(expires_in: int) -> None:
        if expires_in < 1 or expires_in > 2678400:
            raise ValueError("expires_in must be between 1 and 2678400 seconds")

    @staticmethod
    def _normalize_ids(ids: Optional[Union[str, List[int]]], name: str = "ids") -> Optional[str]:
        if ids is None:
            return None

        if isinstance(ids, str):
            normalized = ",".join(part.strip() for part in ids.split(",") if part.strip())
            if not normalized:
                raise ValueError(f"{name} string cannot be empty")

            for part in normalized.split(","):
                if not part.isdigit() or int(part) <= 0:
                    raise ValueError(f"{name} string must contain positive integer IDs")
            return normalized

        if isinstance(ids, list):
            if not ids:
                raise ValueError(f"{name} list cannot be empty")

            normalized_parts = []
            for id_val in ids:
                if isinstance(id_val, bool) or not isinstance(id_val, int) or id_val <= 0:
                    raise ValueError(f"{name} list must contain positive integers")
                normalized_parts.append(str(id_val))
            return ",".join(normalized_parts)

        raise TypeError(f"{name} must be a comma-separated string or list of integers")

    async def get_me(self) -> App:
        response = await self._execute_with_retry(self._http_client.get, "/getMe")
        info = self._handle_response(response)
        return parse_json(App, **info)

    async def _create_invoice(self, **kwargs: Any) -> Invoice:
        response = await self._execute_with_retry(self._http_client.post, "/createInvoice", json=kwargs)
        info = self._handle_response(response)
        return parse_json(Invoice, **info)

    async def create_invoice(
        self,
        amount: float,
        asset: Optional[Asset] = None,
        currency_type: Optional[str] = None,
        fiat: Optional[str] = None,
        accepted_assets: Optional[str] = None,
        description: Optional[str] = None,
        hidden_message: Optional[str] = None,
        paid_btn_name: Optional[ButtonName] = None,
        paid_btn_url: Optional[str] = None,
        payload: Optional[str] = None,
        allow_comments: Optional[bool] = None,
        allow_anonymous: Optional[bool] = None,
        expires_in: Optional[int] = None,
        swap_to: Optional[str] = None,
    ) -> Invoice:
        if amount <= 0:
            raise ValueError("Amount must be greater than 0")
        if expires_in is not None:
            self._validate_expires_in(expires_in)

        data: dict[str, Any] = {
            "amount": str(amount),
            "currency_type": currency_type,
            "fiat": fiat,
            "accepted_assets": accepted_assets,
            "description": description,
            "hidden_message": hidden_message,
            "paid_btn_url": paid_btn_url,
            "payload": payload,
            "allow_comments": allow_comments,
            "allow_anonymous": allow_anonymous,
            "expires_in": expires_in,
            "swap_to": swap_to,
        }

        if asset is not None:
            data["asset"] = asset.name

        for key, value in dict(data).items():
            if value is None:
                del data[key]

        if paid_btn_name:
            data["paid_btn_name"] = paid_btn_name.name
        return await self._create_invoice(**data)

    async def transfer(
        self,
        user_id: int,
        asset: Asset,
        amount: float,
        spend_id: str,
        comment: Optional[str] = None,
        disable_send_notification: bool = False,
    ) -> Transfer:
        if amount <= 0:
            raise ValueError("Amount must be greater than 0")

        data = {
            "user_id": user_id,
            "asset": asset.name,
            "amount": str(amount),
            "spend_id": spend_id,
            "comment": comment,
            "disable_send_notification": disable_send_notification,
        }
        response = await self._execute_with_retry(self._http_client.post, "/transfer", json=data)
        info = self._handle_response(response)
        return parse_json(Transfer, **info)

    async def get_invoices(
        self,
        asset: Optional[Asset] = None,
        fiat: Optional[str] = None,
        invoice_ids: Optional[Union[str, List[int]]] = None,
        status: Optional[Status] = None,
        offset: int = 0,
        count: int = 100,
    ) -> List[Invoice]:
        if offset < 0:
            raise ValueError("offset must be greater than or equal to 0")
        self._validate_count(count)
        normalized_invoice_ids = self._normalize_ids(invoice_ids, "invoice_ids")

        data: dict[str, Any] = {}
        if asset:
            data["asset"] = asset.name
        if fiat:
            data["fiat"] = fiat
        if normalized_invoice_ids is not None:
            data["invoice_ids"] = normalized_invoice_ids
        if status:
            data["status"] = status.name
        if offset:
            data["offset"] = offset
        data["count"] = count

        response = await self._execute_with_retry(self._http_client.get, "/getInvoices", params=data)
        info = self._handle_response(response)
        return [parse_json(Invoice, **i) for i in info["items"]]

    async def iter_invoice_pages(
        self,
        asset: Optional[Asset] = None,
        invoice_ids: Optional[Union[str, List[int]]] = None,
        status: Optional[Status] = None,
        page_size: int = 100,
        start_offset: int = 0,
    ) -> AsyncIterator[List[Invoice]]:
        if start_offset < 0:
            raise ValueError("start_offset must be greater than or equal to 0")
        self._validate_count(page_size)

        offset = start_offset
        while True:
            page = await self.get_invoices(
                asset=asset,
                invoice_ids=invoice_ids,
                status=status,
                offset=offset,
                count=page_size,
            )
            if not page:
                break

            yield page

            if len(page) < page_size:
                break

            offset += page_size

    async def iter_invoices(
        self,
        asset: Optional[Asset] = None,
        invoice_ids: Optional[Union[str, List[int]]] = None,
        status: Optional[Status] = None,
        page_size: int = 100,
        start_offset: int = 0,
    ) -> AsyncIterator[Invoice]:
        async for page in self.iter_invoice_pages(
            asset=asset,
            invoice_ids=invoice_ids,
            status=status,
            page_size=page_size,
            start_offset=start_offset,
        ):
            for invoice in page:
                yield invoice

    async def get_balances(self) -> List[Balance]:
        response = await self._execute_with_retry(self._http_client.get, "/getBalance")
        info = self._handle_response(response)
        return [parse_json(Balance, **i) for i in info]

    async def get_exchange_rates(self) -> List[ExchangeRate]:
        response = await self._execute_with_retry(self._http_client.get, "/getExchangeRates")
        info = self._handle_response(response)
        return [parse_json(ExchangeRate, **i) for i in info]

    async def get_currencies(self) -> List[Currency]:
        response = await self._execute_with_retry(self._http_client.get, "/getCurrencies")
        info = self._handle_response(response)
        return [parse_json(Currency, **i) for i in info]

    async def delete_invoice(self, invoice_id: int) -> bool:
        """Delete an invoice by ID."""
        response = await self._execute_with_retry(self._http_client.post, "/deleteInvoice", json={"invoice_id": invoice_id})
        result: bool = self._handle_response(response)
        return result

    async def create_check(
        self,
        asset: Asset,
        amount: float,
        pin_to_user_id: Optional[int] = None,
        pin_to_username: Optional[str] = None,
    ) -> Check:
        """Create a new crypto check."""
        if amount <= 0:
            raise ValueError("Amount must be greater than 0")

        data: dict[str, Any] = {
            "asset": asset.name,
            "amount": str(amount),
        }
        if pin_to_user_id is not None:
            data["pin_to_user_id"] = pin_to_user_id
        if pin_to_username is not None:
            data["pin_to_username"] = pin_to_username

        response = await self._execute_with_retry(self._http_client.post, "/createCheck", json=data)
        info = self._handle_response(response)
        return parse_json(Check, **info)

    async def delete_check(self, check_id: int) -> bool:
        """Delete a check by ID."""
        response = await self._execute_with_retry(self._http_client.post, "/deleteCheck", json={"check_id": check_id})
        result: bool = self._handle_response(response)
        return result

    async def get_transfers(
        self,
        asset: Optional[Asset] = None,
        transfer_ids: Optional[Union[str, List[int]]] = None,
        spend_id: Optional[str] = None,
        offset: int = 0,
        count: int = 100,
    ) -> List[Transfer]:
        """Get a list of transfers."""
        if offset < 0:
            raise ValueError("offset must be greater than or equal to 0")
        self._validate_count(count)
        normalized_ids = self._normalize_ids(transfer_ids, "transfer_ids")

        data: dict[str, Any] = {}
        if asset:
            data["asset"] = asset.name
        if normalized_ids is not None:
            data["transfer_ids"] = normalized_ids
        if spend_id is not None:
            data["spend_id"] = spend_id
        if offset:
            data["offset"] = offset
        data["count"] = count

        response = await self._execute_with_retry(self._http_client.get, "/getTransfers", params=data)
        info = self._handle_response(response)
        return [parse_json(Transfer, **i) for i in info["items"]]

    async def iter_transfer_pages(
        self,
        asset: Optional[Asset] = None,
        transfer_ids: Optional[Union[str, List[int]]] = None,
        spend_id: Optional[str] = None,
        page_size: int = 100,
        start_offset: int = 0,
    ) -> AsyncIterator[List[Transfer]]:
        """Iterate over transfer result pages."""
        if start_offset < 0:
            raise ValueError("start_offset must be greater than or equal to 0")
        self._validate_count(page_size)

        offset = start_offset
        while True:
            page = await self.get_transfers(
                asset=asset,
                transfer_ids=transfer_ids,
                spend_id=spend_id,
                offset=offset,
                count=page_size,
            )
            if not page:
                break
            yield page
            if len(page) < page_size:
                break
            offset += page_size

    async def iter_transfers(
        self,
        asset: Optional[Asset] = None,
        transfer_ids: Optional[Union[str, List[int]]] = None,
        spend_id: Optional[str] = None,
        page_size: int = 100,
        start_offset: int = 0,
    ) -> AsyncIterator[Transfer]:
        """Iterate transfers item-by-item across paginated results."""
        async for page in self.iter_transfer_pages(
            asset=asset,
            transfer_ids=transfer_ids,
            spend_id=spend_id,
            page_size=page_size,
            start_offset=start_offset,
        ):
            for transfer in page:
                yield transfer

    async def get_checks(
        self,
        asset: Optional[Asset] = None,
        check_ids: Optional[Union[str, List[int]]] = None,
        status: Optional[CheckStatus] = None,
        offset: int = 0,
        count: int = 100,
    ) -> List[Check]:
        """Get a list of checks."""
        if offset < 0:
            raise ValueError("offset must be greater than or equal to 0")
        self._validate_count(count)
        normalized_ids = self._normalize_ids(check_ids, "check_ids")

        data: dict[str, Any] = {}
        if asset:
            data["asset"] = asset.name
        if normalized_ids is not None:
            data["check_ids"] = normalized_ids
        if status:
            data["status"] = status.name
        if offset:
            data["offset"] = offset
        data["count"] = count

        response = await self._execute_with_retry(self._http_client.get, "/getChecks", params=data)
        info = self._handle_response(response)
        return [parse_json(Check, **i) for i in info["items"]]

    async def iter_check_pages(
        self,
        asset: Optional[Asset] = None,
        check_ids: Optional[Union[str, List[int]]] = None,
        status: Optional[CheckStatus] = None,
        page_size: int = 100,
        start_offset: int = 0,
    ) -> AsyncIterator[List[Check]]:
        """Iterate over check result pages."""
        if start_offset < 0:
            raise ValueError("start_offset must be greater than or equal to 0")
        self._validate_count(page_size)

        offset = start_offset
        while True:
            page = await self.get_checks(
                asset=asset,
                check_ids=check_ids,
                status=status,
                offset=offset,
                count=page_size,
            )
            if not page:
                break
            yield page
            if len(page) < page_size:
                break
            offset += page_size

    async def iter_checks(
        self,
        asset: Optional[Asset] = None,
        check_ids: Optional[Union[str, List[int]]] = None,
        status: Optional[CheckStatus] = None,
        page_size: int = 100,
        start_offset: int = 0,
    ) -> AsyncIterator[Check]:
        """Iterate checks item-by-item across paginated results."""
        async for page in self.iter_check_pages(
            asset=asset,
            check_ids=check_ids,
            status=status,
            page_size=page_size,
            start_offset=start_offset,
        ):
            for check in page:
                yield check

    async def get_stats(
        self,
        start_at: Optional[str] = None,
        end_at: Optional[str] = None,
    ) -> AppStats:
        """Get app statistics."""
        data: dict[str, Any] = {}
        if start_at is not None:
            data["start_at"] = start_at
        if end_at is not None:
            data["end_at"] = end_at

        response = await self._execute_with_retry(self._http_client.get, "/getStats", params=data)
        info = self._handle_response(response)
        return parse_json(AppStats, **info)
