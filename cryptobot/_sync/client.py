from typing import List

import httpx

from ..errors import CryptoBotError
from ..models import App, Asset, Balance, ButtonName, Currency, ExchangeRate, Invoice, Status, Transfer


class CryptoBotClient:
    """Crypto Bot Client"""

    def __init__(self, api_token, is_mainnet: bool = True, timeout: float = 5.0):
        self.api_token = api_token
        self.timeout = timeout
        self.__base_url = "https://pay.crypt.bot/api" if is_mainnet else "https://testnet-pay.crypt.bot/api"
        self.__http_client = httpx.Client(
            base_url=self.__base_url,
            timeout=self.timeout,
            headers={
                "Crypto-Pay-API-Token": self.api_token
            }
        )

    def get_me(self) -> App:
        """Get basic information about an app"""
        response = self.__http_client.get("/getMe")
        if response.status_code == 200:
            info = response.json()['result']
            return App(**info)
        else:
            data = response.json()['error']
            raise CryptoBotError(**data)

    def __create_invoice(self, **kwargs) -> Invoice:
        """Create a new invoice"""
        response = self.__http_client.post("/createInvoice", json=kwargs)
        if response.status_code == 200:
            info = response.json()['result']
            return Invoice(**info)
        else:
            data = response.json()['error']
            raise CryptoBotError.from_json(data)

    def create_invoice(self, asset: Asset, amount: float, description: str = None, hidden_message: str = None,
                       paid_btn_name: ButtonName = None, paid_btn_url: str = None, payload: str = None,
                       allow_comments: bool = None, allow_anonymous: bool = None, expires_in: int = None) -> Invoice:
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
            "expires_in": expires_in
        }
        # TODO: Check the minimum amount

        # remove None values
        for key, value in dict(data).items():
            if value is None:
                del data[key]

        if paid_btn_name:
            data['paid_btn_name'] = paid_btn_name.name
        return self.__create_invoice(**data)

    def transfer(self, user_id: int, asset: Asset, amount: float, spend_id: str, comment: str = None,
                 disable_send_notification: bool = False) -> Transfer:
        """Send coins from your app's balance to a user"""
        data = {
            "user_id": user_id,
            "asset": asset.name,
            "amount": str(amount),
            "spend_id": spend_id,
            "comment": comment,
            "disable_send_notification": disable_send_notification
        }
        response = self.__http_client.post("/transfer", json=data)
        if response.status_code == 200:
            info = response.json()['result']
            return Transfer(**info)
        else:
            data = response.json()['error']
            raise CryptoBotError.from_json(data)

    def get_invoices(self, asset: Asset = None, invoice_ids: str = None, status: Status = None, offset: int = 0,
                     count: int = 100) -> List[Invoice]:
        """Get a list of invoices"""
        data = {
        }
        if asset:
            data['asset'] = asset.name
        if invoice_ids:
            data['invoice_ids'] = invoice_ids
        if status:
            data['status'] = status.name
        if offset:
            data['offset'] = offset
        if count:
            data['count'] = count

        response = self.__http_client.get("/getInvoices", params=data)
        if response.status_code == 200:
            info = response.json()['result']
            return [Invoice(**i) for i in info['items']]
        else:
            data = response.json()['error']
            raise CryptoBotError.from_json(data)

    def get_balances(self) -> List[Balance]:
        """Get the balances of your app"""
        response = self.__http_client.get("/getBalance")
        if response.status_code == 200:
            info = response.json()['result']
            return [Balance(**i) for i in info]
        else:
            data = response.json()['error']
            raise CryptoBotError.from_json(data)

    def get_exchange_rates(self) -> List[ExchangeRate]:
        """Get the exchange rates"""
        response = self.__http_client.get("/getExchangeRates")
        if response.status_code == 200:
            info = response.json()['result']
            return [ExchangeRate(**i) for i in info]
        else:
            data = response.json()['error']
            raise CryptoBotError.from_json(data)

    def get_currencies(self) -> List[Currency]:
        """Get the currencies"""
        response = self.__http_client.get("/getCurrencies")
        if response.status_code == 200:
            info = response.json()['result']
            return [Currency(**i) for i in info]
        else:
            data = response.json()['error']
            raise CryptoBotError.from_json(data)
