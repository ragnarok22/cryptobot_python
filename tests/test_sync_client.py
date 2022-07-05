#!/usr/bin/env python

"""Tests for `cryptobot` package."""
import os
import unittest

from dotenv import load_dotenv

from cryptobot import CryptoBotClient
from cryptobot.errors import CryptoBotError
from cryptobot.models import Asset

load_dotenv()


class TestCryptoBotSyncClient(unittest.TestCase):
    """Tests for `cryptobot` client"""

    def setUp(self):
        """Set up test fixtures, if any."""
        api_token = os.getenv('API_TOKEN')
        self.client = CryptoBotClient(api_token, is_mainnet=False)

    def tearDown(self) -> None:
        """Tear down test fixtures, if any."""

    def test_get_me(self):
        """Retreating app information"""
        api_token = os.getenv('API_TOKEN')
        client = CryptoBotClient(api_token, is_mainnet=False)
        info = client.get_me()
        self.assertEqual(info.app_id, 5496)
        self.assertEqual(info.name, 'Connecton Test')

    def test_get_me_error(self):
        """Retreating app information"""
        client = CryptoBotClient("WRONG_TOKEN", is_mainnet=False)
        with self.assertRaises(CryptoBotError):
            client.get_me()

    def test_create_invoice(self):
        """Create a new invoice"""
        invoice = self.client.create_invoice(Asset.TON, 0.01)
        self.assertEqual(invoice.status, 'active')
        self.assertEqual(invoice.asset, 'TON')
        self.assertEqual(invoice.amount, '0.01')
        self.assertEqual(invoice.allow_comments, True)
        self.assertEqual(invoice.allow_anonymous, True)
        self.assertEqual(f'https://t.me/CryptoTestnetBot?start={invoice.hash}', invoice.pay_url)

    def test_create_invoice_error(self):
        """Create a new invoice"""
        with self.assertRaises(CryptoBotError):
            self.client.create_invoice(Asset.TON, 0.0001)
