from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


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

    currency_type: Optional[str] = None
    description: Optional[str] = None
    comment: Optional[str] = None
    hidden_message: Optional[str] = None
    payload: Optional[str] = None

    created_at: Optional[str] = None
    expiration_date: Optional[str] = None
    paid_at: Optional[str] = None

    fiat: Optional[str] = None
    accepted_assets: Optional[List[str]] = None

    fee_asset: Optional[str] = None
    fee_amount: Optional[str] = None
    fee_in_usd: Optional[str] = None

    paid_anonymously: bool = True
    paid_amount: Optional[str] = None
    paid_fiat_rate: Optional[str] = None
    paid_usd_rate: Optional[str] = None
    paid_asset: Optional[str] = None
    paid_btn_name: Optional[ButtonName] = None
    paid_btn_url: Optional[str] = None

    bot_invoice_url: Optional[str] = None

    allow_comments: bool = True
    allow_anonymous: bool = True

    swap_to: Optional[str] = None

    # deprecated
    fee: Optional[str] = None
    pay_url: Optional[str] = None
    usd_rate: Optional[str] = None
    mini_app_invoice_url: Optional[str] = None
    web_app_invoice_url: Optional[str] = None


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
    comment: Optional[str] = None


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
    url: Optional[str] = None
