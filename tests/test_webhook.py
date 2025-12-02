#!/usr/bin/env python

"""Simplified tests for webhook functionality in `cryptobot` package."""

import hashlib
import json
from unittest.mock import Mock, patch

from cryptobot.webhook import Listener, check_signature


class TestCheckSignature:
    """Tests for signature verification function."""

    def test_check_signature_valid(self):
        """Test signature verification with valid signature."""
        token = "test_token"
        body = {"test": "data"}

        # Create expected signature
        secret = hashlib.sha256(token.encode()).digest()
        check_string = json.dumps(body)
        hmac = hashlib.sha256(secret)
        hmac.update(check_string.encode())
        expected_signature = hmac.hexdigest()

        headers = {"crypto-pay-api-signature": expected_signature}

        assert check_signature(token, body, headers) is True

    def test_check_signature_invalid(self):
        """Test signature verification with invalid signature."""
        token = "test_token"
        body = {"test": "data"}
        headers = {"crypto-pay-api-signature": "invalid_signature"}

        assert check_signature(token, body, headers) is False

    def test_check_signature_different_body(self):
        """Test signature verification fails with different body."""
        token = "test_token"
        original_body = {"test": "data"}
        modified_body = {"test": "modified_data"}

        # Create signature for original body
        secret = hashlib.sha256(token.encode()).digest()
        check_string = json.dumps(original_body)
        hmac = hashlib.sha256(secret)
        hmac.update(check_string.encode())
        signature = hmac.hexdigest()

        headers = {"crypto-pay-api-signature": signature}

        # Verify with modified body should fail
        assert check_signature(token, modified_body, headers) is False

    def test_check_signature_complex_body(self):
        """Test signature verification with complex body structure."""
        token = "test_token"
        body = {
            "update_id": 12345,
            "update_type": "invoice_paid",
            "request_date": "2023-01-01T00:00:00Z",
            "payload": {
                "invoice_id": 123,
                "status": "paid",
                "asset": "TON",
                "amount": "10.5",
                "fee": "0.1",
            },
        }

        secret = hashlib.sha256(token.encode()).digest()
        check_string = json.dumps(body)
        hmac = hashlib.sha256(secret)
        hmac.update(check_string.encode())
        expected_signature = hmac.hexdigest()

        headers = {"crypto-pay-api-signature": expected_signature}

        assert check_signature(token, body, headers) is True


class TestListener:
    """Tests for Listener class."""

    def test_listener_creation(self):
        """Test creating Listener instance."""
        callback = Mock()
        listener = Listener(
            host="localhost",
            callback=callback,
            api_token="test_token",
            port=8080,
            url="/test-webhook",
            log_level="info",
        )

        assert listener.host == "localhost"
        assert listener.callback == callback
        assert listener.api_token == "test_token"
        assert listener.port == 8080
        assert listener.url == "/test-webhook"
        assert listener.log_level == "info"

    def test_listener_default_values(self):
        """Test Listener default values."""
        callback = Mock()
        listener = Listener(host="localhost", callback=callback, api_token="test_token")

        assert listener.port == 2203
        assert listener.url == "/webhook"
        assert listener.log_level == "error"

    @patch("cryptobot.webhook.uvicorn.run")
    @patch("builtins.print")
    def test_listener_listen(self, mock_print, mock_uvicorn_run):
        """Test listener.listen() method."""
        callback = Mock()
        listener = Listener(
            host="localhost", callback=callback, api_token="test_token", port=8080
        )

        listener.listen()

        # Check that uvicorn.run was called with correct parameters
        mock_uvicorn_run.assert_called_once_with(
            listener.app, host="localhost", port=8080, log_level="error"
        )

        # Check that banner was printed
        assert mock_print.call_count >= 2  # ASCII art + info message

    def test_listener_app_exists(self):
        """Test that Listener has FastAPI app."""
        callback = Mock()
        listener = Listener(host="localhost", callback=callback, api_token="test_token")

        # Check that app exists
        assert hasattr(listener, "app")
        assert listener.app is not None

    def test_multiple_listeners(self):
        """Test creating multiple Listener instances."""
        callback1 = Mock()
        callback2 = Mock()

        listener1 = Listener(
            host="localhost", callback=callback1, api_token="test_token1", port=8080
        )
        listener2 = Listener(
            host="localhost", callback=callback2, api_token="test_token2", port=8081
        )

        assert listener1.port != listener2.port
        assert listener1.callback != listener2.callback
        # Note: Listeners share the same app class variable, which is expected behavior
