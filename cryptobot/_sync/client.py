from typing import List, Optional

import httpx

from ..errors import CryptoBotError
from ..models import (
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


class CryptoBotClient:
    """Crypto Bot API client for creating invoices and managing cryptocurrency payments.

    This client provides a synchronous interface to the Crypto Bot API, supporting
    invoice creation, transfers, balance checking, and exchange rate queries.

    Args:
        api_token: Your Crypto Bot API token. Get it from @CryptoBot on Telegram.
        is_mainnet: If True, use mainnet. If False, use testnet. Default: True.
        timeout: HTTP request timeout in seconds. Default: 5.0.

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

    def __init__(self, api_token, is_mainnet: bool = True, timeout: float = 5.0):
        self.api_token = api_token
        self.timeout = timeout
        self._base_url = (
            "https://pay.crypt.bot/api"
            if is_mainnet
            else "https://testnet-pay.crypt.bot/api"
        )
        self._http_client = httpx.Client(
            base_url=self._base_url,
            timeout=self.timeout,
            headers={"Crypto-Pay-API-Token": self.api_token},
        )

    def _handle_response(self, response: httpx.Response) -> dict:
        """Handle HTTP response and raise appropriate errors"""
        if response.status_code == 200:
            return response.json()["result"]
        try:
            data = response.json()["error"]
            raise CryptoBotError.from_json(data)
        except (ValueError, KeyError):
            # Response is not JSON or doesn't have error field
            raise CryptoBotError(
                code=response.status_code,
                name=f"HTTPError: {response.text[:100]}",
            )

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
        response = self._http_client.get("/getMe")
        info = self._handle_response(response)
        return App(**info)

    def _create_invoice(self, **kwargs) -> Invoice:
        """Create a new invoice"""
        response = self._http_client.post("/createInvoice", json=kwargs)
        info = self._handle_response(response)
        return Invoice(**info)

    def create_invoice(
        self,
        asset: Asset,
        amount: float,
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
        """Create a new cryptocurrency payment invoice.

        Args:
            asset: Cryptocurrency asset (e.g., Asset.BTC, Asset.TON, Asset.ETH).
            amount: Invoice amount in the specified cryptocurrency.
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

        Note:
            Amount limits roughly correspond to 1-25,000 USD equivalent for each asset.
            Use get_exchange_rates() to convert amounts between currencies.

        Examples:
            Simple invoice:
                >>> invoice = client.create_invoice(Asset.TON, 1.5)
                >>> print(invoice.bot_invoice_url)

            Invoice with description and custom button:
                >>> invoice = client.create_invoice(
                ...     asset=Asset.BTC,
                ...     amount=0.0001,
                ...     description="Premium Membership",
                ...     hidden_message="Thank you for your purchase!",
                ...     paid_btn_name=ButtonName.viewItem,
                ...     paid_btn_url="https://example.com/premium"
                ... )
                >>> print(f"Invoice ID: {invoice.invoice_id}")

            Invoice that expires in 1 hour:
                >>> invoice = client.create_invoice(
                ...     asset=Asset.USDT,
                ...     amount=10,
                ...     description="Limited time offer",
                ...     expires_in=3600  # 1 hour
                ... )
        """
        # Validate amount
        if amount <= 0:
            raise ValueError("Amount must be greater than 0")

        data = {
            "asset": asset.name,
            "amount": str(amount),
            "description": description,
            "hidden_message": hidden_message,
            "paid_btn_url": paid_btn_url,
            "payload": payload,
            "allow_comments": allow_comments,
            "allow_anonymous": allow_anonymous,
            "expires_in": expires_in,
            "swap_to": swap_to,
        }

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
        response = self._http_client.post("/transfer", json=data)
        info = self._handle_response(response)
        return Transfer(**info)

    def get_invoices(
        self,
        asset: Optional[Asset] = None,
        invoice_ids: Optional[str] = None,
        status: Optional[Status] = None,
        offset: int = 0,
        count: int = 100,
    ) -> List[Invoice]:
        """Get a list of invoices created by your app.

        Args:
            asset: Filter by cryptocurrency asset (e.g., Asset.BTC). Default: all assets.
            invoice_ids: Comma-separated list of invoice IDs to retrieve.
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
                >>> for invoice in invoices:
                ...     print(f"{invoice.invoice_id}: {invoice.status}")

            Get only paid TON invoices:
                >>> paid_invoices = client.get_invoices(
                ...     asset=Asset.TON,
                ...     status=Status.paid
                ... )

            Get specific invoices by ID:
                >>> invoices = client.get_invoices(invoice_ids="123,456,789")

            Pagination example:
                >>> page1 = client.get_invoices(count=50, offset=0)
                >>> page2 = client.get_invoices(count=50, offset=50)
        """
        data = {}
        if asset:
            data["asset"] = asset.name
        if invoice_ids:
            data["invoice_ids"] = invoice_ids
        if status:
            data["status"] = status.name
        if offset:
            data["offset"] = offset
        if count:
            data["count"] = count

        response = self._http_client.get("/getInvoices", params=data)
        info = self._handle_response(response)
        return [Invoice(**i) for i in info["items"]]

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
        response = self._http_client.get("/getBalance")
        info = self._handle_response(response)
        return [Balance(**i) for i in info]

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
        response = self._http_client.get("/getExchangeRates")
        info = self._handle_response(response)
        return [ExchangeRate(**i) for i in info]

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
        response = self._http_client.get("/getCurrencies")
        info = self._handle_response(response)
        return [Currency(**i) for i in info]
