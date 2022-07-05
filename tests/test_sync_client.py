#!/usr/bin/env python

"""Tests for `cryptobot` package."""
import logging
import os
import unittest

from dotenv import load_dotenv

from cryptobot import CryptoBotClient

load_dotenv()


class TestCryptoBotSyncClient(unittest.TestCase):
    """Tests for `cryptobot` client"""

    def setUp(self):
        """Set up test fixtures, if any."""

    def tearDown(self) -> None:
        """Tear down test fixtures, if any."""

    def test_get_me(self):
        """Retreating app information"""
        api_token = os.getenv('API_TOKEN')
        client = CryptoBotClient(api_token, is_mainnet=False)
        logging.info(client.get_me())
