#!/usr/bin/env python

"""Tests for `cryptobot` package."""
import os
import unittest

from dotenv import load_dotenv

from cryptobot import CryptoBotClient
from cryptobot.errors import CryptoBotError
from cryptobot.models import Asset, ButtonName

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

    def test_create_invoice_with_params(self):
        """Create a new invoice"""
        invoice = self.client.create_invoice(Asset.TON, 0.01, description='Test', hidden_message='Test',
                                             paid_btn_name=ButtonName.viewItem,
                                             paid_btn_url='https://reinierhernandez.com', payload='Test',
                                             allow_comments=False, allow_anonymous=False, expires_in=1)
        self.assertEqual(invoice.status, 'active')
        self.assertEqual(invoice.asset, 'TON')
        self.assertEqual(invoice.amount, '0.01')
        self.assertEqual(invoice.allow_comments, False)
        self.assertEqual(invoice.allow_anonymous, False)
        self.assertEqual(f'https://t.me/CryptoTestnetBot?start={invoice.hash}', invoice.pay_url)

    def test_create_invoice_error(self):
        """Create a new invoice"""
        with self.assertRaises(CryptoBotError):
            self.client.create_invoice(Asset.TON, 0.0001)

    def test_transfer(self):
        """Transfer"""
        transfer = self.client.transfer(699381957, Asset.TON, 0.01, 'Test')
        self.assertEqual(transfer.status, 'active')
        self.assertEqual(transfer.asset, 'TON')
        self.assertEqual(transfer.amount, '0.01')

    def test_get_invoices(self):
        """Get invoices"""
        invoices = self.client.get_invoices()
        self.assertEqual(invoices[0].status, 'expired')
        self.assertEqual(invoices[0].asset, 'TON')
        self.assertEqual(invoices[0].amount, '0.01')
        self.assertEqual(f'https://t.me/CryptoTestnetBot?start={invoices[0].hash}', invoices[0].pay_url)

    def test_get_balances(self):
        """Get balance"""
        balances = self.client.get_balances()
        self.assertEqual(len(balances), 7)  # 7 assets
        self.assertEqual(balances[0].available, '0')

    def test_exchange_rates(self):
        """Get exchange rates"""
        rates = self.client.get_exchange_rates()
        self.assertEqual(len(rates), 42)  # 7 assets and 6 exchange rates

    def test_get_currencies(self):
        """Get currencies"""
        currencies = self.client.get_currencies()
        self.assertIsNotNone(currencies)
        self.assertIsInstance(currencies, list)
