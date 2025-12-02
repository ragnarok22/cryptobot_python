#!/usr/bin/env python

"""Tests for `cryptobot` package."""

import os
import unittest

from dotenv import load_dotenv

from cryptobot import CryptoBotClient
from cryptobot.errors import CryptoBotError
from cryptobot.models import Asset, ButtonName

load_dotenv()

# Check if API token is available (for CI environments like PRs from forks/bots)
API_TOKEN = os.getenv("API_TOKEN")
SKIP_AUTH_TESTS = not API_TOKEN or API_TOKEN.strip() == ""


class TestCryptoBotSyncClient(unittest.TestCase):
    """Tests for `cryptobot` client"""

    def setUp(self):
        """Set up test fixtures, if any."""
        if not SKIP_AUTH_TESTS:
            self.client = CryptoBotClient(API_TOKEN, is_mainnet=False)

    def tearDown(self) -> None:
        """Tear down test fixtures, if any."""

    @unittest.skipIf(
        SKIP_AUTH_TESTS, "API_TOKEN not available (e.g., PR from fork/bot)"
    )
    def test_get_me(self):
        """Retreating app information"""
        client = CryptoBotClient(API_TOKEN, is_mainnet=False)
        info = client.get_me()
        self.assertIsNotNone(info.app_id)
        self.assertIsNotNone(info.name)

    def test_get_me_error(self):
        """Retreating app information"""
        client = CryptoBotClient("WRONG_TOKEN", is_mainnet=False)
        with self.assertRaises(CryptoBotError):
            client.get_me()

    @unittest.skipIf(
        SKIP_AUTH_TESTS, "API_TOKEN not available (e.g., PR from fork/bot)"
    )
    def test_create_invoice(self):
        """Create a new invoice"""
        invoice = self.client.create_invoice(Asset.TON, 1)
        self.assertEqual(invoice.status, "active")
        self.assertEqual(invoice.asset, "TON")
        self.assertEqual(invoice.amount, "1")
        self.assertEqual(invoice.allow_comments, True)
        self.assertEqual(invoice.allow_anonymous, True)
        self.assertEqual(
            f"https://t.me/CryptoTestnetBot?start={invoice.hash}", invoice.pay_url
        )

    @unittest.skipIf(
        SKIP_AUTH_TESTS, "API_TOKEN not available (e.g., PR from fork/bot)"
    )
    def test_create_invoice_with_params(self):
        """Create a new invoice"""
        invoice = self.client.create_invoice(
            Asset.TON,
            1,
            description="Test",
            hidden_message="Test",
            paid_btn_name=ButtonName.viewItem,
            paid_btn_url="https://reinierhernandez.com",
            payload="Test",
            allow_comments=False,
            allow_anonymous=False,
            expires_in=1,
            swap_to="USDT",
        )
        self.assertEqual(invoice.status, "active")
        self.assertEqual(invoice.asset, "TON")
        self.assertEqual(invoice.amount, "1")
        self.assertEqual(invoice.allow_comments, False)
        self.assertEqual(invoice.allow_anonymous, False)
        self.assertEqual(
            f"https://t.me/CryptoTestnetBot?start={invoice.hash}", invoice.pay_url
        )

    @unittest.skipIf(
        SKIP_AUTH_TESTS, "API_TOKEN not available (e.g., PR from fork/bot)"
    )
    def test_create_invoice_error(self):
        """Create a new invoice"""
        with self.assertRaises(CryptoBotError):
            self.client.create_invoice(Asset.TON, 0.0001)

    @unittest.skipIf(
        SKIP_AUTH_TESTS, "API_TOKEN not available (e.g., PR from fork/bot)"
    )
    def test_transfer(self):
        """Transfer - may fail if testnet account has insufficient funds"""
        try:
            transfer = self.client.transfer(699381957, Asset.TON, 1.0, "test_spend_id")
            self.assertEqual(transfer.status, "success")
            self.assertEqual(transfer.asset, Asset.TON)
            self.assertEqual(transfer.amount, "1.0")
        except CryptoBotError as e:
            # Allow INSUFFICIENT_FUNDS error in testnet
            if e.name != "INSUFFICIENT_FUNDS":
                raise

    @unittest.skipIf(
        SKIP_AUTH_TESTS, "API_TOKEN not available (e.g., PR from fork/bot)"
    )
    def test_get_invoices(self):
        """Get invoices"""
        invoices = self.client.get_invoices()
        self.assertEqual(invoices[0].asset, "TON")
        self.assertEqual(invoices[0].amount, "1")
        self.assertEqual(
            f"https://t.me/CryptoTestnetBot?start={invoices[0].hash}",
            invoices[0].pay_url,
        )

    @unittest.skipIf(
        SKIP_AUTH_TESTS, "API_TOKEN not available (e.g., PR from fork/bot)"
    )
    def test_get_balances(self):
        """Get balance"""
        balances = self.client.get_balances()
        self.assertIsNotNone(balances)

    def test_exchange_rates(self):
        """Get exchange rates"""
        # rates = self.client.get_exchange_rates()
        # self.assertEqual(len(rates), 84)  # 7 assets and 6 exchange rates

    @unittest.skipIf(
        SKIP_AUTH_TESTS, "API_TOKEN not available (e.g., PR from fork/bot)"
    )
    def test_get_currencies(self):
        """Get currencies"""
        currencies = self.client.get_currencies()
        self.assertIsNotNone(currencies)
        self.assertIsInstance(currencies, list)
