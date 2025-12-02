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
    """Crypto Bot Client"""

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
        """Get basic information about an app"""
        response = self._http_client.get("/getMe")
        info = self._handle_response(response)
        return App(**info)

    def __create_invoice(self, **kwargs) -> Invoice:
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
        """Create a new invoice"""
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
        # TODO: Check the minimum amount

        # remove None values
        for key, value in dict(data).items():
            if value is None:
                del data[key]

        if paid_btn_name:
            data["paid_btn_name"] = paid_btn_name.name
        return self.__create_invoice(**data)

    def transfer(
        self,
        user_id: int,
        asset: Asset,
        amount: float,
        spend_id: str,
        comment: Optional[str] = None,
        disable_send_notification: bool = False,
    ) -> Transfer:
        """Send coins from your app's balance to a user"""
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
        """Get a list of invoices"""
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
        """Get the balances of your app"""
        response = self._http_client.get("/getBalance")
        info = self._handle_response(response)
        return [Balance(**i) for i in info]

    def get_exchange_rates(self) -> List[ExchangeRate]:
        """Get the exchange rates"""
        response = self._http_client.get("/getExchangeRates")
        info = self._handle_response(response)
        return [ExchangeRate(**i) for i in info]

    def get_currencies(self) -> List[Currency]:
        """Get the currencies"""
        response = self._http_client.get("/getCurrencies")
        info = self._handle_response(response)
        return [Currency(**i) for i in info]
