"""Top-level package for CryptoBot Python."""

__author__ = """Reinier Hernández"""
__email__ = "sasuke.reinier@gmail.com"
__version__ = "0.5.1"

from ._sync.client import CryptoBotClient  # noqa: F401
from .client import AsyncCryptoBotClient  # noqa: F401
