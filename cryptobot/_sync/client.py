import time
from collections.abc import Iterator
from contextlib import suppress
from types import TracebackType
from typing import Any, Callable, List, Optional, Set, Union

import httpx

from .._utils import parse_json
from ..errors import CryptoBotError
from ..models import (
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


class CryptoBotClient:
    """Crypto Bot API client for creating invoices and managing cryptocurrency payments.

    This client provides a synchronous interface to the Crypto Bot API, supporting
    invoice creation, transfers, balance checking, and exchange rate queries.

    Args:
        api_token: Your Crypto Bot API token. Get it from @CryptoBot on Telegram.
        is_mainnet: If True, use mainnet. If False, use testnet. Default: True.
        timeout: HTTP request timeout in seconds. Default: 5.0.
        max_retries: Number of retries for retryable failures. Default: 0 (disabled).
        retry_backoff: Base seconds for exponential backoff between retries. Default: 0.5.
        retryable_status_codes: HTTP status codes that should be retried. Default: {429, 500, 502, 503, 504}.

    Example:
        >>> from cryptobot import CryptoBotClient
        >>> from cryptobot.models import Asset
        >>>
        >>> # Initialize client
        >>> client = CryptoBotClient("YOUR_API_TOKEN")
        >>>
        >>> # Create a simple invoice
        >>> invoice = client.create_invoice(Asset.TON, 1.5)
        >>> print(invoice.bot_invoice_url)
    """

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
        self._http_client = httpx.Client(
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

    def _execute_with_retry(self, request_fn: Callable[..., httpx.Response], *args: Any, **kwargs: Any) -> httpx.Response:
        retryable_exceptions = (
            httpx.TimeoutException,
            httpx.NetworkError,
            httpx.RemoteProtocolError,
        )

        for attempt in range(self.max_retries + 1):
            try:
                response = request_fn(*args, **kwargs)
            except retryable_exceptions:
                if attempt >= self.max_retries:
                    raise
                delay = self._retry_delay(attempt)
                if delay > 0:
                    time.sleep(delay)
                continue

            if response.status_code in self.retryable_status_codes and attempt < self.max_retries:
                delay = self._retry_delay(attempt, response)
                if delay > 0:
                    time.sleep(delay)
                continue

            return response

        # This is unreachable due to the return/raise branches above.
        raise RuntimeError("Unexpected retry flow state")  # pragma: no cover

    def _handle_response(self, response: httpx.Response) -> Any:
        """Handle HTTP responses consistently and raise typed errors for malformed payloads."""
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

    def close(self) -> None:
        """Close the underlying HTTP client and release network resources."""
        self._http_client.close()

    def __enter__(self) -> "CryptoBotClient":
        return self

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> None:
        self.close()

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

    def get_me(self) -> App:
        """Get basic information about your Crypto Bot application.

        Returns:
            App object containing app_id, name, and payment_processing_bot_username.

        Raises:
            CryptoBotError: If the API request fails or authentication is invalid.

        Example:
            >>> client = CryptoBotClient("YOUR_API_TOKEN")
            >>> app = client.get_me()
            >>> print(f"App Name: {app.name}")
            >>> print(f"App ID: {app.app_id}")
            >>> print(f"Bot Username: {app.payment_processing_bot_username}")
        """
        response = self._execute_with_retry(self._http_client.get, "/getMe")
        info = self._handle_response(response)
        return parse_json(App, **info)

    def _create_invoice(self, **kwargs: Any) -> Invoice:
        """Create a new invoice"""
        response = self._execute_with_retry(self._http_client.post, "/createInvoice", json=kwargs)
        info = self._handle_response(response)
        return parse_json(Invoice, **info)

    def create_invoice(
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
        """Create a new payment invoice.

        Args:
            amount: Invoice amount (e.g., 125.50).
            asset: Cryptocurrency asset. Required if currency_type is "crypto" (default).
            currency_type: "crypto" or "fiat". Default: "crypto".
            fiat: Fiat currency code (e.g., "USD"). Required if currency_type is "fiat".
            accepted_assets: Comma-separated crypto codes accepted for fiat invoices.
            description: Optional description shown to the customer (up to 1024 chars).
            hidden_message: Optional message shown after successful payment (up to 2048 chars).
            paid_btn_name: Optional name of the button shown after payment (ButtonName enum).
            paid_btn_url: Optional URL opened when the button is pressed (up to 1024 chars).
            payload: Optional data (up to 4096 bytes) attached to the invoice.
            allow_comments: Allow customers to add comments. Default: True.
            allow_anonymous: Allow anonymous payments. Default: True.
            expires_in: Optional time in seconds until invoice expiration (1-2678400).
            swap_to: Optional asset code to convert the payment to (e.g., "USDT").

        Returns:
            Invoice object with payment URL, status, and other details.

        Raises:
            ValueError: If amount is less than or equal to 0.
            CryptoBotError: If the API request fails.

        Examples:
            Crypto invoice:
                >>> invoice = client.create_invoice(1.5, asset=Asset.TON)
                >>> print(invoice.bot_invoice_url)

            Fiat invoice:
                >>> invoice = client.create_invoice(
                ...     amount=10.00,
                ...     currency_type="fiat",
                ...     fiat="USD",
                ...     accepted_assets="USDT,TON,BTC",
                ... )
        """
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

        # remove None values
        for key, value in dict(data).items():
            if value is None:
                del data[key]

        if paid_btn_name:
            data["paid_btn_name"] = paid_btn_name.name
        return self._create_invoice(**data)

    def transfer(
        self,
        user_id: int,
        asset: Asset,
        amount: float,
        spend_id: str,
        comment: Optional[str] = None,
        disable_send_notification: bool = False,
    ) -> Transfer:
        """Send cryptocurrency from your app's balance to a Telegram user.

        Args:
            user_id: Telegram user ID to receive the transfer.
            asset: Cryptocurrency asset to send (e.g., Asset.TON, Asset.BTC).
            amount: Amount to transfer in the specified cryptocurrency.
            spend_id: Unique string to prevent duplicate transfers (up to 64 chars).
            comment: Optional comment for the transfer (up to 1024 chars).
            disable_send_notification: Don't send notification to the user. Default: False.

        Returns:
            Transfer object with transfer details and status.

        Raises:
            ValueError: If amount is less than or equal to 0.
            CryptoBotError: If transfer fails (e.g., insufficient funds, invalid user).

        Note:
            Amount limits roughly correspond to 1-25,000 USD equivalent for each asset.
            The spend_id must be unique to prevent duplicate transfers.

        Examples:
            Simple transfer:
                >>> transfer = client.transfer(
                ...     user_id=123456789,
                ...     asset=Asset.TON,
                ...     amount=1.5,
                ...     spend_id="order_12345"
                ... )
                >>> print(f"Transfer ID: {transfer.transfer_id}")

            Transfer with comment:
                >>> transfer = client.transfer(
                ...     user_id=123456789,
                ...     asset=Asset.USDT,
                ...     amount=10,
                ...     spend_id="reward_abc123",
                ...     comment="Cashback reward for your purchase!"
                ... )
        """
        # Validate amount
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
        response = self._execute_with_retry(self._http_client.post, "/transfer", json=data)
        info = self._handle_response(response)
        return parse_json(Transfer, **info)

    def get_invoices(
        self,
        asset: Optional[Asset] = None,
        fiat: Optional[str] = None,
        invoice_ids: Optional[Union[str, List[int]]] = None,
        status: Optional[Status] = None,
        offset: int = 0,
        count: int = 100,
    ) -> List[Invoice]:
        """Get a list of invoices created by your app.

        Args:
            asset: Filter by cryptocurrency asset (e.g., Asset.BTC). Default: all assets.
            fiat: Filter by fiat currency code (e.g., "USD"). Default: all.
            invoice_ids: Comma-separated IDs string or list of invoice IDs to retrieve.
            status: Filter by invoice status (Status.active, Status.paid, Status.expired).
            offset: Number of invoices to skip. Default: 0.
            count: Number of invoices to return (1-1000). Default: 100.

        Returns:
            List of Invoice objects matching the filter criteria.

        Raises:
            CryptoBotError: If the API request fails.

        Examples:
            Get all invoices:
                >>> invoices = client.get_invoices()

            Get only paid TON invoices:
                >>> paid_invoices = client.get_invoices(asset=Asset.TON, status=Status.paid)

            Get fiat invoices:
                >>> usd_invoices = client.get_invoices(fiat="USD")
        """
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

        response = self._execute_with_retry(self._http_client.get, "/getInvoices", params=data)
        info = self._handle_response(response)
        return [parse_json(Invoice, **i) for i in info["items"]]

    def iter_invoice_pages(
        self,
        asset: Optional[Asset] = None,
        invoice_ids: Optional[Union[str, List[int]]] = None,
        status: Optional[Status] = None,
        page_size: int = 100,
        start_offset: int = 0,
    ) -> Iterator[List[Invoice]]:
        """Iterate over invoice result pages until no more invoices are available."""
        if start_offset < 0:
            raise ValueError("start_offset must be greater than or equal to 0")
        self._validate_count(page_size)

        offset = start_offset
        while True:
            page = self.get_invoices(
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

    def iter_invoices(
        self,
        asset: Optional[Asset] = None,
        invoice_ids: Optional[Union[str, List[int]]] = None,
        status: Optional[Status] = None,
        page_size: int = 100,
        start_offset: int = 0,
    ) -> Iterator[Invoice]:
        """Iterate invoices item-by-item across paginated get_invoices results."""
        for page in self.iter_invoice_pages(
            asset=asset,
            invoice_ids=invoice_ids,
            status=status,
            page_size=page_size,
            start_offset=start_offset,
        ):
            for invoice in page:
                yield invoice

    def get_balances(self) -> List[Balance]:
        """Get cryptocurrency balances of your app.

        Returns:
            List of Balance objects for all supported cryptocurrencies.

        Raises:
            CryptoBotError: If the API request fails.

        Example:
            >>> balances = client.get_balances()
            >>> for balance in balances:
            ...     print(f"{balance.currency_code}: {balance.available} available, {balance.onhold} on hold")
            BTC: 0.00150000 available, 0.00000000 on hold
            TON: 150.5 available, 10.0 on hold
        """
        response = self._execute_with_retry(self._http_client.get, "/getBalance")
        info = self._handle_response(response)
        return [parse_json(Balance, **i) for i in info]

    def get_exchange_rates(self) -> List[ExchangeRate]:
        """Get current exchange rates for all supported cryptocurrencies.

        Returns:
            List of ExchangeRate objects with conversion rates.

        Raises:
            CryptoBotError: If the API request fails.

        Example:
            >>> rates = client.get_exchange_rates()
            >>> for rate in rates:
            ...     if rate.source == Asset.BTC and rate.target == "USD":
            ...         print(f"1 BTC = ${rate.rate} USD")
            1 BTC = $45000.50 USD

            Calculate invoice amount:
                >>> # Convert $100 USD to TON
                >>> rates = client.get_exchange_rates()
                >>> ton_usd_rate = next(r for r in rates if r.source == Asset.TON and r.target == "USD")
                >>> ton_amount = 100 / float(ton_usd_rate.rate)
                >>> invoice = client.create_invoice(Asset.TON, ton_amount)
        """
        response = self._execute_with_retry(self._http_client.get, "/getExchangeRates")
        info = self._handle_response(response)
        return [parse_json(ExchangeRate, **i) for i in info]

    def get_currencies(self) -> List[Currency]:
        """Get information about supported cryptocurrencies.

        Returns:
            List of Currency objects with details about each supported cryptocurrency.

        Raises:
            CryptoBotError: If the API request fails.

        Example:
            >>> currencies = client.get_currencies()
            >>> for currency in currencies:
            ...     print(f"{currency.code}: {currency.name} (decimals: {currency.decimals})")
            ...     print(f"  Blockchain: {currency.is_blockchain}, Stablecoin: {currency.is_stablecoin}")
            BTC: Bitcoin (decimals: 8)
              Blockchain: True, Stablecoin: False
            USDT: Tether (decimals: 6)
              Blockchain: True, Stablecoin: True
        """
        response = self._execute_with_retry(self._http_client.get, "/getCurrencies")
        info = self._handle_response(response)
        return [parse_json(Currency, **i) for i in info]

    def delete_invoice(self, invoice_id: int) -> bool:
        """Delete an invoice by ID.

        Args:
            invoice_id: The invoice ID to delete.

        Returns:
            True on success.

        Raises:
            CryptoBotError: If the API request fails.
        """
        response = self._execute_with_retry(self._http_client.post, "/deleteInvoice", json={"invoice_id": invoice_id})
        result: bool = self._handle_response(response)
        return result

    def create_check(
        self,
        asset: Asset,
        amount: float,
        pin_to_user_id: Optional[int] = None,
        pin_to_username: Optional[str] = None,
    ) -> Check:
        """Create a new crypto check.

        Args:
            asset: Cryptocurrency asset for the check.
            amount: Check amount in the specified cryptocurrency.
            pin_to_user_id: Optional Telegram user ID who can activate the check.
            pin_to_username: Optional Telegram username who can activate the check.

        Returns:
            Check object with activation URL and details.

        Raises:
            ValueError: If amount is less than or equal to 0.
            CryptoBotError: If the API request fails.
        """
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

        response = self._execute_with_retry(self._http_client.post, "/createCheck", json=data)
        info = self._handle_response(response)
        return parse_json(Check, **info)

    def delete_check(self, check_id: int) -> bool:
        """Delete a check by ID.

        Args:
            check_id: The check ID to delete.

        Returns:
            True on success.

        Raises:
            CryptoBotError: If the API request fails.
        """
        response = self._execute_with_retry(self._http_client.post, "/deleteCheck", json={"check_id": check_id})
        result: bool = self._handle_response(response)
        return result

    def get_transfers(
        self,
        asset: Optional[Asset] = None,
        transfer_ids: Optional[Union[str, List[int]]] = None,
        spend_id: Optional[str] = None,
        offset: int = 0,
        count: int = 100,
    ) -> List[Transfer]:
        """Get a list of transfers.

        Args:
            asset: Filter by cryptocurrency asset. Default: all.
            transfer_ids: Comma-separated IDs or list of transfer IDs.
            spend_id: Filter by unique spend_id string.
            offset: Number of transfers to skip. Default: 0.
            count: Number of transfers to return (1-1000). Default: 100.

        Returns:
            List of Transfer objects.

        Raises:
            CryptoBotError: If the API request fails.
        """
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

        response = self._execute_with_retry(self._http_client.get, "/getTransfers", params=data)
        info = self._handle_response(response)
        return [parse_json(Transfer, **i) for i in info["items"]]

    def iter_transfer_pages(
        self,
        asset: Optional[Asset] = None,
        transfer_ids: Optional[Union[str, List[int]]] = None,
        spend_id: Optional[str] = None,
        page_size: int = 100,
        start_offset: int = 0,
    ) -> Iterator[List[Transfer]]:
        """Iterate over transfer result pages."""
        if start_offset < 0:
            raise ValueError("start_offset must be greater than or equal to 0")
        self._validate_count(page_size)

        offset = start_offset
        while True:
            page = self.get_transfers(
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

    def iter_transfers(
        self,
        asset: Optional[Asset] = None,
        transfer_ids: Optional[Union[str, List[int]]] = None,
        spend_id: Optional[str] = None,
        page_size: int = 100,
        start_offset: int = 0,
    ) -> Iterator[Transfer]:
        """Iterate transfers item-by-item across paginated results."""
        for page in self.iter_transfer_pages(
            asset=asset,
            transfer_ids=transfer_ids,
            spend_id=spend_id,
            page_size=page_size,
            start_offset=start_offset,
        ):
            for transfer in page:
                yield transfer

    def get_checks(
        self,
        asset: Optional[Asset] = None,
        check_ids: Optional[Union[str, List[int]]] = None,
        status: Optional[CheckStatus] = None,
        offset: int = 0,
        count: int = 100,
    ) -> List[Check]:
        """Get a list of checks.

        Args:
            asset: Filter by cryptocurrency asset. Default: all.
            check_ids: Comma-separated IDs or list of check IDs.
            status: Filter by check status. Default: all.
            offset: Number of checks to skip. Default: 0.
            count: Number of checks to return (1-1000). Default: 100.

        Returns:
            List of Check objects.

        Raises:
            CryptoBotError: If the API request fails.
        """
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

        response = self._execute_with_retry(self._http_client.get, "/getChecks", params=data)
        info = self._handle_response(response)
        return [parse_json(Check, **i) for i in info["items"]]

    def iter_check_pages(
        self,
        asset: Optional[Asset] = None,
        check_ids: Optional[Union[str, List[int]]] = None,
        status: Optional[CheckStatus] = None,
        page_size: int = 100,
        start_offset: int = 0,
    ) -> Iterator[List[Check]]:
        """Iterate over check result pages."""
        if start_offset < 0:
            raise ValueError("start_offset must be greater than or equal to 0")
        self._validate_count(page_size)

        offset = start_offset
        while True:
            page = self.get_checks(
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

    def iter_checks(
        self,
        asset: Optional[Asset] = None,
        check_ids: Optional[Union[str, List[int]]] = None,
        status: Optional[CheckStatus] = None,
        page_size: int = 100,
        start_offset: int = 0,
    ) -> Iterator[Check]:
        """Iterate checks item-by-item across paginated results."""
        for page in self.iter_check_pages(
            asset=asset,
            check_ids=check_ids,
            status=status,
            page_size=page_size,
            start_offset=start_offset,
        ):
            for check in page:
                yield check

    def get_stats(
        self,
        start_at: Optional[str] = None,
        end_at: Optional[str] = None,
    ) -> AppStats:
        """Get app statistics.

        Args:
            start_at: Start date in ISO 8601 format. Default: 24 hours ago.
            end_at: End date in ISO 8601 format. Default: now.

        Returns:
            AppStats object with volume, conversion, and invoice counts.

        Raises:
            CryptoBotError: If the API request fails.
        """
        data: dict[str, Any] = {}
        if start_at is not None:
            data["start_at"] = start_at
        if end_at is not None:
            data["end_at"] = end_at

        response = self._execute_with_retry(self._http_client.get, "/getStats", params=data)
        info = self._handle_response(response)
        return parse_json(AppStats, **info)
