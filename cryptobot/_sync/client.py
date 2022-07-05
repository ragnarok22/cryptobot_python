import httpx

from cryptobot.errors import CrytoBotError
from cryptobot.models import App


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
            raise CrytoBotError(**data)
