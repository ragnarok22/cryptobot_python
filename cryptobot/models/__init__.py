from dataclasses import dataclass
from enum import Enum


@dataclass
class App:
    app_id: int
    name: str
    payment_processing_bot_username: str


class Asset(Enum):
    BTC = "BTC"
    TON = "TON"
    ETH = "ETH"
    USDT = "USDT"
    USDC = "USDC"
    BUSD = "BUSD"


@dataclass
class Invoice:
    invoice_id: int
    status: str
    hash: str
    asset: str
    amount: str
    pay_url: str
    created_at: str
    allow_comments: bool
    allow_anonymous: bool
