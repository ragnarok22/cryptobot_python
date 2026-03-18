"""Top-level package for CryptoBot Python."""

__author__ = """Reinier Hernández"""
__email__ = "sasuke.reinier@gmail.com"
__version__ = "1.0.0"

from ._sync.client import CryptoBotClient  # noqa: F401
from .client import AsyncCryptoBotClient  # noqa: F401
