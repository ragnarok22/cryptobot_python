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


class Status(Enum):
    active = "active"
    paid = "paid"
    expired = "expired"


class ButtonName(Enum):
    viewItem = "viewItem"
    openChannel = "openChannel"
    callback = "callback"


@dataclass
class Invoice:
    """Invoice
    docs: https://telegra.ph/Crypto-Pay-API-11-25#Invoice
    """
    invoice_id: int
    status: Status
    hash: str
    asset: Asset
    amount: str
    pay_url: str
    description: str = None
    created_at: str = None
    allow_comments: bool = True
    allow_anonymous: bool = True
    expiration_date: str = None
    paid_at: str = None
    paid_anonymously: bool = True
    comment: str = None
    hidden_message: str = None
    payload: str = None
    paid_btn_name: ButtonName = None
    paid_btn_url: str = None


@dataclass
class Transfer:
    """Transfer
    docs: https://telegra.ph/Crypto-Pay-API-11-25#Transfer
    """
    transfer_id: int
    user_id: int
    asset: Asset
    amount: str
    status: Status
    completed_at: str
    comment: str = None


@dataclass
class Balance:
    """Balance"""
    currency_code: str
    available: str


@dataclass
class ExchangeRate:
    """ExchangeRate"""
    is_valid: bool
    source: Asset
    target: str
    rate: str


@dataclass
class Currency:
    is_blockchain: bool
    is_stablecoin: bool
    is_fiat: bool
    name: str
    code: str
    decimals: int
    url: str = None
