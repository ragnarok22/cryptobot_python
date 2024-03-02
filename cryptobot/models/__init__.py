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
    BNB = "BNB"
    TRX = "TRX"


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
    docs: https://help.crypt.bot/crypto-pay-api#Invoice
    """

    invoice_id: int
    status: Status
    hash: str
    amount: str
    asset: Asset

    currency_type: str = None
    description: str = None
    comment: str = None
    hidden_message: str = None
    payload: str = None

    created_at: str = None
    expiration_date: str = None
    paid_at: str = None

    fiat: str = None
    accepted_assets: list = None

    fee_asset: str = None
    fee_amount: str = None

    paid_anonymously: bool = True
    paid_amount: str = None
    paid_fiat_rate: str = None
    paid_usd_rate: str = None
    paid_asset: str = None
    paid_btn_name: ButtonName = None
    paid_btn_url: str = None

    bot_invoice_url: str = None

    allow_comments: bool = True
    allow_anonymous: bool = True

    # deprecated
    fee: str = None
    pay_url: str = None
    usd_rate: str = None


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
    onhold: str


@dataclass
class ExchangeRate:
    """ExchangeRate"""
    is_valid: bool
    is_crypto: bool
    is_fiat: bool
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
