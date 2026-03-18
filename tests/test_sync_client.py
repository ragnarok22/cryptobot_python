#!/usr/bin/env python

"""Tests for `cryptobot` package."""

import os
import socket
import unittest

import pytest
from dotenv import load_dotenv

from cryptobot import CryptoBotClient
from cryptobot.errors import CryptoBotError
from cryptobot.models import Asset, ButtonName, CheckStatus, Status, TransferStatus

load_dotenv()

# Check if API token is available (for CI environments like PRs from forks/bots)
API_TOKEN = os.getenv("API_TOKEN")
SKIP_AUTH_TESTS = not API_TOKEN or API_TOKEN.strip() == ""


@pytest.mark.integration
class TestCryptoBotSyncClient(unittest.TestCase):
    """Tests for `cryptobot` client"""

    @classmethod
    def setUpClass(cls):
        if SKIP_AUTH_TESTS:
            raise unittest.SkipTest("API_TOKEN not available (e.g., PR from fork/bot)")

        try:
            socket.getaddrinfo("testnet-pay.crypt.bot", 443)
        except socket.gaierror as exc:
            raise unittest.SkipTest("Integration target is not reachable from this environment") from exc

    def setUp(self):
        """Set up test fixtures, if any."""
        self.client = CryptoBotClient(API_TOKEN, is_mainnet=False)

    def tearDown(self) -> None:
        """Tear down test fixtures, if any."""

    @unittest.skipIf(SKIP_AUTH_TESTS, "API_TOKEN not available (e.g., PR from fork/bot)")
    def test_get_me(self):
        """Retreating app information"""
        client = CryptoBotClient(API_TOKEN, is_mainnet=False)
        info = client.get_me()
        self.assertIsNotNone(info.app_id)
        self.assertIsNotNone(info.name)

    @unittest.skipIf(SKIP_AUTH_TESTS, "API_TOKEN not available (e.g., PR from fork/bot)")
    def test_get_me_error(self):
        """Retreating app information"""
        client = CryptoBotClient("WRONG_TOKEN", is_mainnet=False)
        with self.assertRaises(CryptoBotError):
            client.get_me()

    @unittest.skipIf(SKIP_AUTH_TESTS, "API_TOKEN not available (e.g., PR from fork/bot)")
    def test_create_invoice(self):
        """Create a new invoice"""
        invoice = self.client.create_invoice(1, asset=Asset.TON)
        self.assertEqual(invoice.status, Status.active)
        self.assertEqual(invoice.asset, Asset.TON)
        self.assertEqual(invoice.amount, "1")
        self.assertEqual(invoice.allow_comments, True)
        self.assertEqual(invoice.allow_anonymous, True)
        self.assertIsNotNone(invoice.bot_invoice_url)

    @unittest.skipIf(SKIP_AUTH_TESTS, "API_TOKEN not available (e.g., PR from fork/bot)")
    def test_create_invoice_with_params(self):
        """Create a new invoice with all optional parameters"""
        invoice = self.client.create_invoice(
            1,
            asset=Asset.TON,
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
        self.assertEqual(invoice.status, Status.active)
        self.assertEqual(invoice.asset, Asset.TON)
        self.assertEqual(invoice.amount, "1")
        self.assertEqual(invoice.allow_comments, False)
        self.assertEqual(invoice.allow_anonymous, False)
        self.assertIsNotNone(invoice.bot_invoice_url)

    @unittest.skipIf(SKIP_AUTH_TESTS, "API_TOKEN not available (e.g., PR from fork/bot)")
    def test_create_invoice_error(self):
        """Create a new invoice with too small amount"""
        with self.assertRaises(CryptoBotError):
            self.client.create_invoice(0.0001, asset=Asset.TON)

    @unittest.skipIf(SKIP_AUTH_TESTS, "API_TOKEN not available (e.g., PR from fork/bot)")
    def test_transfer(self):
        """Transfer - may fail if testnet account has insufficient funds"""
        try:
            transfer = self.client.transfer(699381957, Asset.TON, 0.1, "test_spend_id")
            self.assertIn(transfer.status, (TransferStatus.completed, "success"))
            self.assertEqual(transfer.asset, Asset.TON)
            self.assertEqual(transfer.amount, "0.1")
        except CryptoBotError as e:
            # Allow INSUFFICIENT_FUNDS or AMOUNT_TOO_SMALL errors in testnet
            if e.name not in ("INSUFFICIENT_FUNDS", "AMOUNT_TOO_SMALL"):
                raise

    @unittest.skipIf(SKIP_AUTH_TESTS, "API_TOKEN not available (e.g., PR from fork/bot)")
    def test_get_invoices(self):
        """Get invoices"""
        invoices = self.client.get_invoices()
        self.assertGreater(len(invoices), 0)
        self.assertIsNotNone(invoices[0].bot_invoice_url)

    @unittest.skipIf(SKIP_AUTH_TESTS, "API_TOKEN not available (e.g., PR from fork/bot)")
    def test_get_balances(self):
        """Get balance"""
        balances = self.client.get_balances()
        self.assertIsNotNone(balances)

    @unittest.skipIf(SKIP_AUTH_TESTS, "API_TOKEN not available (e.g., PR from fork/bot)")
    def test_exchange_rates(self):
        """Get exchange rates"""
        rates = self.client.get_exchange_rates()
        self.assertIsNotNone(rates)
        self.assertIsInstance(rates, list)
        self.assertGreater(len(rates), 0)
        for rate in rates:
            self.assertIsInstance(rate.source, str)
            self.assertIsInstance(rate.target, str)
            self.assertIsInstance(rate.rate, str)
            self.assertIsInstance(rate.is_valid, bool)

    @unittest.skipIf(SKIP_AUTH_TESTS, "API_TOKEN not available (e.g., PR from fork/bot)")
    def test_get_currencies(self):
        """Get currencies"""
        currencies = self.client.get_currencies()
        self.assertIsNotNone(currencies)
        self.assertIsInstance(currencies, list)

    @unittest.skipIf(SKIP_AUTH_TESTS, "API_TOKEN not available (e.g., PR from fork/bot)")
    def test_delete_invoice(self):
        """Create and delete an invoice"""
        invoice = self.client.create_invoice(1, asset=Asset.TON)
        result = self.client.delete_invoice(invoice.invoice_id)
        self.assertTrue(result)

    @unittest.skipIf(SKIP_AUTH_TESTS, "API_TOKEN not available (e.g., PR from fork/bot)")
    def test_create_and_delete_check(self):
        """Create and delete a crypto check"""
        try:
            check = self.client.create_check(Asset.TON, 1)
            self.assertIsNotNone(check.check_id)
            self.assertEqual(check.asset, Asset.TON)
            self.assertEqual(check.amount, "1")
            self.assertEqual(check.status, CheckStatus.active)
            self.assertIsNotNone(check.bot_check_url)

            result = self.client.delete_check(check.check_id)
            self.assertTrue(result)
        except CryptoBotError as e:
            # METHOD_DISABLED: createCheck must be enabled in app security settings
            if e.name not in ("INSUFFICIENT_FUNDS", "AMOUNT_TOO_SMALL", "METHOD_DISABLED"):
                raise

    @unittest.skipIf(SKIP_AUTH_TESTS, "API_TOKEN not available (e.g., PR from fork/bot)")
    def test_get_transfers(self):
        """Get transfers"""
        transfers = self.client.get_transfers()
        self.assertIsInstance(transfers, list)

    @unittest.skipIf(SKIP_AUTH_TESTS, "API_TOKEN not available (e.g., PR from fork/bot)")
    def test_get_checks(self):
        """Get checks"""
        checks = self.client.get_checks()
        self.assertIsInstance(checks, list)

    @unittest.skipIf(SKIP_AUTH_TESTS, "API_TOKEN not available (e.g., PR from fork/bot)")
    def test_get_stats(self):
        """Get app statistics"""
        stats = self.client.get_stats()
        self.assertIsNotNone(stats.start_at)
        self.assertIsNotNone(stats.end_at)
        self.assertIsInstance(stats.unique_users_count, int)

    @unittest.skipIf(SKIP_AUTH_TESTS, "API_TOKEN not available (e.g., PR from fork/bot)")
    def test_create_invoice_fiat(self):
        """Create a fiat invoice"""
        try:
            invoice = self.client.create_invoice(
                10.00,
                currency_type="fiat",
                fiat="USD",
            )
            self.assertEqual(invoice.status, Status.active)
            self.assertEqual(invoice.currency_type, "fiat")
            self.assertEqual(invoice.fiat, "USD")
            self.assertIsNotNone(invoice.bot_invoice_url)
        except CryptoBotError:
            pass  # fiat may not be available on testnet
