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
    LTC = "LTC"
    USDT = "USDT"
    USDC = "USDC"
    BNB = "BNB"
    TRX = "TRX"


class Status(Enum):
    active = "active"
    paid = "paid"
    expired = "expired"


class TransferStatus(Enum):
    completed = "completed"


class ButtonName(Enum):
    viewItem = "viewItem"
    openChannel = "openChannel"
    openBot = "openBot"
    callback = "callback"


class CheckStatus(Enum):
    active = "active"
    activated = "activated"


@dataclass
class Invoice:
    """Invoice
    docs: https://help.send.tg/en/articles/10279948-crypto-pay-api
    """

    invoice_id: int
    status: Status
    hash: str
    amount: str
    asset: Optional[Asset] = None

    currency_type: Optional[str] = None
    description: Optional[str] = None
    comment: Optional[str] = None
    hidden_message: Optional[str] = None
    payload: Optional[str] = None

    created_at: Optional[str] = None
    expiration_date: Optional[str] = None
    paid_at: Optional[str] = None

    fiat: Optional[str] = None
    accepted_assets: Optional[List[Asset]] = None

    fee_asset: Optional[Asset] = None
    fee_amount: Optional[str] = None
    fee_in_usd: Optional[str] = None

    paid_anonymously: bool = True
    paid_amount: Optional[str] = None
    paid_fiat_rate: Optional[str] = None
    paid_usd_rate: Optional[str] = None
    paid_asset: Optional[Asset] = None
    paid_btn_name: Optional[ButtonName] = None
    paid_btn_url: Optional[str] = None

    bot_invoice_url: Optional[str] = None
    mini_app_invoice_url: Optional[str] = None
    web_app_invoice_url: Optional[str] = None

    allow_comments: bool = True
    allow_anonymous: bool = True

    swap_to: Optional[str] = None
    is_swapped: Optional[bool] = None
    swapped_uid: Optional[str] = None
    swapped_to: Optional[str] = None
    swapped_rate: Optional[str] = None
    swapped_output: Optional[str] = None
    swapped_usd_amount: Optional[str] = None
    swapped_usd_rate: Optional[str] = None

    # deprecated: use fee_amount, bot_invoice_url, paid_usd_rate instead
    fee: Optional[str] = None
    pay_url: Optional[str] = None
    usd_rate: Optional[str] = None


@dataclass
class Transfer:
    """Transfer
    docs: https://help.send.tg/en/articles/10279948-crypto-pay-api
    """

    transfer_id: int
    user_id: int
    asset: Asset
    amount: str
    status: TransferStatus
    completed_at: str
    spend_id: Optional[str] = None
    comment: Optional[str] = None


@dataclass
class Check:
    """Check
    docs: https://help.send.tg/en/articles/10279948-crypto-pay-api
    """

    check_id: int
    hash: str
    asset: Asset
    amount: str
    bot_check_url: str
    status: CheckStatus
    created_at: str
    activated_at: Optional[str] = None


@dataclass
class AppStats:
    """AppStats
    docs: https://help.send.tg/en/articles/10279948-crypto-pay-api
    """

    volume: float
    conversion: float
    unique_users_count: int
    created_invoice_count: int
    paid_invoice_count: int
    start_at: str
    end_at: str


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
    source: str
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
