#!/usr/bin/env python

"""Tests for webhook functionality in `cryptobot` package."""
import hashlib
import json
import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi import Request

from cryptobot.webhook import check_signature, Listener
from cryptobot.errors import CryptoBotError


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

    def test_check_signature_missing_header(self):
        """Test signature verification with missing header."""
        token = "test_token"
        body = {"test": "data"}
        headers = {}

        with pytest.raises(KeyError):
            check_signature(token, body, headers)

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

    def test_check_signature_empty_body(self):
        """Test signature verification with empty body."""
        token = "test_token"
        body = {}

        secret = hashlib.sha256(token.encode()).digest()
        check_string = json.dumps(body)
        hmac = hashlib.sha256(secret)
        hmac.update(check_string.encode())
        expected_signature = hmac.hexdigest()

        headers = {"crypto-pay-api-signature": expected_signature}

        assert check_signature(token, body, headers) is True

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
                "fee": "0.1"
            }
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
            port=8080,
            url="/test-webhook",
            log_level="info"
        )

        assert listener.host == "localhost"
        assert listener.callback == callback
        assert listener.port == 8080
        assert listener.url == "/test-webhook"
        assert listener.log_level == "info"

    def test_listener_default_values(self):
        """Test Listener default values."""
        callback = Mock()
        listener = Listener(host="localhost", callback=callback)

        assert listener.port == 2203
        assert listener.url == "/webhook"
        assert listener.log_level == "error"

    @patch('cryptobot.webhook.uvicorn.run')
    @patch('builtins.print')
    def test_listener_listen(self, mock_print, mock_uvicorn_run):
        """Test listener.listen() method."""
        callback = Mock()
        listener = Listener(host="localhost", callback=callback, port=8080)

        listener.listen()

        # Check that uvicorn.run was called with correct parameters
        mock_uvicorn_run.assert_called_once_with(
            listener.app,
            host="localhost",
            port=8080,
            log_level="error"
        )

        # Check that banner was printed
        assert mock_print.call_count >= 2  # ASCII art + info message

    @pytest.mark.asyncio
    async def test_webhook_endpoint_valid_signature(self):
        """Test webhook endpoint with valid signature."""
        callback = Mock()
        listener = Listener(host="localhost", callback=callback)

        client = TestClient(listener.app)

        # Prepare test data
        test_data = {"update_id": 123, "update_type": "invoice_paid"}
        token = "49418:AAAUuM5C7EEiUbLD53oXo7coFbLmZDMHoYv"  # Hardcoded in webhook.py

        # Create valid signature
        secret = hashlib.sha256(token.encode()).digest()
        check_string = json.dumps(test_data)
        hmac = hashlib.sha256(secret)
        hmac.update(check_string.encode())
        signature = hmac.hexdigest()

        headers = {"crypto-pay-api-signature": signature}

        response = client.post("/webhook", json=test_data, headers=headers)

        assert response.status_code == 200
        assert response.json() == {"message": "Thank you CryptoBot"}
        callback.assert_called_once()

    def test_webhook_endpoint_invalid_signature(self):
        """Test webhook endpoint with invalid signature."""
        callback = Mock()
        listener = Listener(host="localhost", callback=callback)

        client = TestClient(listener.app)

        test_data = {"update_id": 123, "update_type": "invoice_paid"}
        headers = {"crypto-pay-api-signature": "invalid_signature"}

        response = client.post("/webhook", json=test_data, headers=headers)

        assert response.status_code == 400  # Should raise CryptoBotError
        callback.assert_not_called()

    def test_webhook_endpoint_missing_signature(self):
        """Test webhook endpoint with missing signature header."""
        callback = Mock()
        listener = Listener(host="localhost", callback=callback)

        client = TestClient(listener.app)

        test_data = {"update_id": 123, "update_type": "invoice_paid"}

        response = client.post("/webhook", json=test_data)

        # Should fail due to missing signature header
        assert response.status_code in [400, 422, 500]
        callback.assert_not_called()

    def test_listener_app_creation(self):
        """Test that Listener creates FastAPI app."""
        callback = Mock()
        listener = Listener(host="localhost", callback=callback)

        # Check that app is created
        assert hasattr(listener, 'app')
        assert listener.app is not None

        # Check that route is registered
        routes = [route.path for route in listener.app.routes]
        assert "/webhook" in routes

    def test_listener_custom_url(self):
        """Test Listener with custom URL."""
        callback = Mock()
        listener = Listener(
            host="localhost",
            callback=callback,
            url="/custom-webhook"
        )

        routes = [route.path for route in listener.app.routes]
        assert "/custom-webhook" in routes

    @patch('cryptobot.webhook.check_signature')
    def test_webhook_signature_check_called(self, mock_check_signature):
        """Test that signature check is called in webhook endpoint."""
        mock_check_signature.return_value = True
        callback = Mock()
        listener = Listener(host="localhost", callback=callback)

        client = TestClient(listener.app)

        test_data = {"update_id": 123}
        headers = {"crypto-pay-api-signature": "test_signature"}

        response = client.post("/webhook", json=test_data, headers=headers)

        assert response.status_code == 200
        mock_check_signature.assert_called_once()

    def test_callback_receives_correct_parameters(self):
        """Test that callback receives correct parameters."""
        callback = Mock()
        listener = Listener(host="localhost", callback=callback)

        client = TestClient(listener.app)

        test_data = {"update_id": 456, "update_type": "transfer_completed"}
        token = "49418:AAAUuM5C7EEiUbLD53oXo7coFbLmZDMHoYv"

        # Create valid signature
        secret = hashlib.sha256(token.encode()).digest()
        check_string = json.dumps(test_data)
        hmac = hashlib.sha256(secret)
        hmac.update(check_string.encode())
        signature = hmac.hexdigest()

        headers = {"crypto-pay-api-signature": signature}

        response = client.post("/webhook", json=test_data, headers=headers)

        assert response.status_code == 200

        # Check callback was called with correct arguments
        callback.assert_called_once()
        call_args = callback.call_args
        assert len(call_args[0]) == 2  # headers and data
        assert call_args[0][1] == test_data  # data parameter

    def test_multiple_listeners(self):
        """Test creating multiple Listener instances."""
        callback1 = Mock()
        callback2 = Mock()

        listener1 = Listener(host="localhost", callback=callback1, port=8080)
        listener2 = Listener(host="localhost", callback=callback2, port=8081)

        assert listener1.port != listener2.port
        assert listener1.callback != listener2.callback
        assert listener1.app != listener2.app  # Different FastAPI instances