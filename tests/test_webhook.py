#!/usr/bin/env python

"""Simplified tests for webhook functionality in `cryptobot` package."""

import hashlib
import hmac
import json
from unittest.mock import Mock, patch

import httpx
import pytest

from cryptobot.webhook import InMemoryReplayKeyStore, Listener, check_signature


def make_signature(token, raw_body):
    """Create a signature matching check_signature for test payloads."""

    secret = hashlib.sha256(token.encode()).digest()
    return hmac.new(secret, raw_body if isinstance(raw_body, bytes) else raw_body.encode(), hashlib.sha256).hexdigest()


class TestCheckSignature:
    """Tests for signature verification function."""

    def test_check_signature_valid(self):
        """Test signature verification with valid signature."""
        token = "test_token"
        body_dict = {"test": "data"}
        raw_body = json.dumps(body_dict)
        headers = {"crypto-pay-api-signature": make_signature(token, raw_body)}

        assert check_signature(token, raw_body, headers) is True

    def test_check_signature_invalid(self):
        """Test signature verification with invalid signature."""
        token = "test_token"
        raw_body = json.dumps({"test": "data"})
        headers = {"crypto-pay-api-signature": "invalid_signature"}

        assert check_signature(token, raw_body, headers) is False

    def test_check_signature_different_body(self):
        """Test signature verification fails with different body."""
        token = "test_token"
        original_body_dict = {"test": "data"}
        modified_body_dict = {"test": "modified_data"}

        # Create raw body strings
        original_raw = json.dumps(original_body_dict)
        modified_raw = json.dumps(modified_body_dict)

        headers = {"crypto-pay-api-signature": make_signature(token, original_raw)}

        # Verify with modified body should fail
        assert check_signature(token, modified_raw, headers) is False

    def test_check_signature_complex_body(self):
        """Test signature verification with complex body structure."""
        token = "test_token"
        body_dict = {
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

        # Create raw body string
        raw_body = json.dumps(body_dict)

        headers = {"crypto-pay-api-signature": make_signature(token, raw_body)}

        assert check_signature(token, raw_body, headers) is True

    def test_check_signature_accepts_bytes_body(self):
        """Ensure bytes payloads are handled correctly."""
        token = "test_token"
        raw_body = b'{"key":"value"}'
        headers = {"crypto-pay-api-signature": make_signature(token, raw_body)}

        assert check_signature(token, raw_body, headers) is True


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

    def test_listener_requires_callable_callback(self):
        with pytest.raises(TypeError, match="callback must be callable"):
            Listener(host="localhost", callback=None, api_token="test_token")

    def test_listener_requires_replay_store_contract(self):
        class InvalidStore:
            pass

        with pytest.raises(TypeError, match="replay_store must implement put_if_absent"):
            Listener(host="localhost", callback=Mock(), api_token="test_token", replay_store=InvalidStore())

    def test_listener_requires_non_negative_replay_ttl(self):
        with pytest.raises(ValueError, match="replay_ttl_seconds must be >= 0"):
            Listener(host="localhost", callback=Mock(), api_token="test_token", replay_ttl_seconds=-1)

    def test_listener_requires_callable_replay_key_resolver(self):
        with pytest.raises(TypeError, match="replay_key_resolver must be callable"):
            Listener(host="localhost", callback=Mock(), api_token="test_token", replay_key_resolver="bad")

    @patch("cryptobot.webhook.uvicorn.run")
    @patch("builtins.print")
    def test_listener_listen(self, mock_print, mock_uvicorn_run):
        """Test listener.listen() method."""
        callback = Mock()
        listener = Listener(host="localhost", callback=callback, api_token="test_token", port=8080)

        listener.listen()

        # Check that uvicorn.run was called with correct parameters
        mock_uvicorn_run.assert_called_once_with(listener.app, host="localhost", port=8080, log_level="error")

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

        listener1 = Listener(host="localhost", callback=callback1, api_token="test_token1", port=8080)
        listener2 = Listener(host="localhost", callback=callback2, api_token="test_token2", port=8081)

        assert listener1.port != listener2.port
        assert listener1.callback != listener2.callback
        # Each listener has its own FastAPI app instance
        assert listener1.app is not listener2.app


class TestListenerWebhookEndpoint:
    """End-to-end tests for the FastAPI webhook route."""

    @pytest.mark.asyncio
    async def test_webhook_valid_signature_runs_callback(self):
        callback = Mock()
        token = "test_token"
        listener = Listener(host="localhost", callback=callback, api_token=token)

        payload = {"update_type": "invoice_paid", "payload": {"invoice_id": 42}}
        raw_body = json.dumps(payload)
        headers = {"crypto-pay-api-signature": make_signature(token, raw_body)}

        transport = httpx.ASGITransport(app=listener.app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post(listener.url, content=raw_body, headers=headers)

        assert response.status_code == 200
        assert response.json() == {"ok": True}
        callback.assert_called_once()
        passed_headers, passed_data = callback.call_args[0]
        assert passed_data == payload
        assert passed_headers.get("crypto-pay-api-signature") == headers["crypto-pay-api-signature"]

    @pytest.mark.asyncio
    async def test_webhook_invalid_signature_raises_error(self):
        callback = Mock()
        token = "test_token"
        listener = Listener(host="localhost", callback=callback, api_token=token)

        payload = {"update_type": "invoice_paid", "payload": {"invoice_id": 1}}
        raw_body = json.dumps(payload)

        transport = httpx.ASGITransport(app=listener.app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post(
                listener.url,
                content=raw_body,
                headers={"crypto-pay-api-signature": "bad"},
            )

        callback.assert_not_called()
        assert response.status_code == 400
        assert response.json() == {"detail": "Invalid signature"}

    @pytest.mark.asyncio
    async def test_webhook_missing_signature_returns_400(self):
        callback = Mock()
        token = "test_token"
        listener = Listener(host="localhost", callback=callback, api_token=token)

        payload = {"update_type": "invoice_paid", "payload": {"invoice_id": 1}}
        raw_body = json.dumps(payload)

        transport = httpx.ASGITransport(app=listener.app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post(
                listener.url,
                content=raw_body,
            )

        callback.assert_not_called()
        assert response.status_code == 400
        assert response.json() == {"detail": "Invalid signature"}

    @pytest.mark.asyncio
    async def test_webhook_invalid_json_raises_error(self):
        callback = Mock()
        token = "test_token"
        listener = Listener(host="localhost", callback=callback, api_token=token)
        raw_body = "not-json"
        headers = {"crypto-pay-api-signature": make_signature(token, raw_body)}

        transport = httpx.ASGITransport(app=listener.app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post(
                listener.url,
                content=raw_body,
                headers=headers,
            )

        callback.assert_not_called()
        assert response.status_code == 400
        assert response.json() == {"detail": "Invalid JSON"}

    @pytest.mark.asyncio
    async def test_webhook_non_object_json_returns_400(self):
        callback = Mock()
        token = "test_token"
        listener = Listener(host="localhost", callback=callback, api_token=token)
        raw_body = json.dumps(["not", "an", "object"])
        headers = {"crypto-pay-api-signature": make_signature(token, raw_body)}

        transport = httpx.ASGITransport(app=listener.app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post(listener.url, content=raw_body, headers=headers)

        callback.assert_not_called()
        assert response.status_code == 400
        assert response.json() == {"detail": "Invalid JSON payload"}

    @pytest.mark.asyncio
    async def test_webhook_invalid_encoding_returns_400(self):
        callback = Mock()
        token = "test_token"
        listener = Listener(host="localhost", callback=callback, api_token=token)

        transport = httpx.ASGITransport(app=listener.app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post(
                listener.url,
                content=b"\xff\xfe\xfa",
                headers={"crypto-pay-api-signature": "bad"},
            )

        callback.assert_not_called()
        assert response.status_code == 400
        assert response.json() == {"detail": "Invalid encoding"}

    @pytest.mark.asyncio
    async def test_webhook_callback_error_propagates(self):
        def bad_callback(headers, data):
            raise ValueError("boom")

        token = "test_token"
        listener = Listener(host="localhost", callback=bad_callback, api_token=token)

        payload = {"update_type": "invoice_paid", "payload": {"invoice_id": 2}}
        raw_body = json.dumps(payload)
        headers = {"crypto-pay-api-signature": make_signature(token, raw_body)}

        transport = httpx.ASGITransport(app=listener.app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post(
                listener.url,
                content=raw_body,
                headers=headers,
            )

        assert response.status_code == 500
        assert response.json() == {"detail": "Callback error"}

    @pytest.mark.asyncio
    async def test_webhook_async_callback_is_awaited(self):
        was_called = {"value": False}

        async def async_callback(headers, data):
            was_called["value"] = True

        token = "test_token"
        listener = Listener(host="localhost", callback=async_callback, api_token=token)

        payload = {"update_type": "invoice_paid", "payload": {"invoice_id": 3}}
        raw_body = json.dumps(payload)
        headers = {"crypto-pay-api-signature": make_signature(token, raw_body)}

        transport = httpx.ASGITransport(app=listener.app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post(listener.url, content=raw_body, headers=headers)

        assert response.status_code == 200
        assert was_called["value"] is True

    @pytest.mark.asyncio
    async def test_webhook_replay_duplicate_rejected(self):
        callback = Mock()
        token = "test_token"
        replay_store = InMemoryReplayKeyStore()
        listener = Listener(host="localhost", callback=callback, api_token=token, replay_store=replay_store)

        payload = {"update_id": 42, "update_type": "invoice_paid", "payload": {"invoice_id": 100}}
        raw_body = json.dumps(payload)
        headers = {"crypto-pay-api-signature": make_signature(token, raw_body)}

        transport = httpx.ASGITransport(app=listener.app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            first = await client.post(listener.url, content=raw_body, headers=headers)
            second = await client.post(listener.url, content=raw_body, headers=headers)

        assert first.status_code == 200
        assert second.status_code == 409
        assert second.json() == {"detail": "Duplicate webhook"}
        callback.assert_called_once()

    @pytest.mark.asyncio
    async def test_webhook_replay_key_released_on_callback_error(self):
        call_count = {"value": 0}

        def flaky_callback(headers, data):
            call_count["value"] += 1
            if call_count["value"] == 1:
                raise ValueError("temporary failure")

        token = "test_token"
        replay_store = InMemoryReplayKeyStore()
        listener = Listener(host="localhost", callback=flaky_callback, api_token=token, replay_store=replay_store)

        payload = {"update_id": 99, "update_type": "invoice_paid", "payload": {"invoice_id": 555}}
        raw_body = json.dumps(payload)
        headers = {"crypto-pay-api-signature": make_signature(token, raw_body)}

        transport = httpx.ASGITransport(app=listener.app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            first = await client.post(listener.url, content=raw_body, headers=headers)
            second = await client.post(listener.url, content=raw_body, headers=headers)

        assert first.status_code == 500
        assert second.status_code == 200
        assert call_count["value"] == 2

    @pytest.mark.asyncio
    async def test_webhook_replay_key_resolver_can_disable_dedupe(self):
        callback = Mock()
        token = "test_token"
        replay_store = InMemoryReplayKeyStore()
        listener = Listener(
            host="localhost",
            callback=callback,
            api_token=token,
            replay_store=replay_store,
            replay_key_resolver=lambda data, raw_body, headers: None,
        )

        payload = {"update_type": "invoice_paid", "payload": {"invoice_id": 11}}
        raw_body = json.dumps(payload)
        headers = {"crypto-pay-api-signature": make_signature(token, raw_body)}

        transport = httpx.ASGITransport(app=listener.app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            first = await client.post(listener.url, content=raw_body, headers=headers)
            second = await client.post(listener.url, content=raw_body, headers=headers)

        assert first.status_code == 200
        assert second.status_code == 200
        assert callback.call_count == 2


class TestReplayProtectionInternals:
    def test_in_memory_replay_store_expires_keys(self):
        store = InMemoryReplayKeyStore()
        with patch("cryptobot.webhook.time.monotonic", side_effect=[100.0, 102.0]):
            assert store.put_if_absent("k1", ttl_seconds=1) is True
            assert store.put_if_absent("k1", ttl_seconds=1) is True

    def test_default_replay_key_uses_payload_identifier(self):
        listener = Listener(host="localhost", callback=Mock(), api_token="token")
        data = {"update_type": "invoice_paid", "payload": {"invoice_id": 555}}
        key = listener._default_replay_key(data, raw_body=json.dumps(data), _headers={})
        assert key == "invoice_paid:invoice_id:555"

    def test_default_replay_key_falls_back_to_body_hash(self):
        listener = Listener(host="localhost", callback=Mock(), api_token="token")
        raw_body = json.dumps({"update_type": "unknown", "payload": {}})
        key = listener._default_replay_key({"update_type": "unknown", "payload": {}}, raw_body=raw_body, _headers={})
        assert key.startswith("body:")

    def test_blank_replay_key_skips_store_write(self):
        replay_store = Mock()
        replay_store.put_if_absent.return_value = True

        listener = Listener(
            host="localhost",
            callback=Mock(),
            api_token="token",
            replay_store=replay_store,
            replay_key_resolver=lambda data, raw_body, headers: "  ",
        )

        key = listener._reserve_replay_key(raw_body="{}", data={}, headers={})
        assert key is None
        replay_store.put_if_absent.assert_not_called()

    def test_release_replay_key_ignores_store_errors(self):
        replay_store = Mock()
        replay_store.remove.side_effect = RuntimeError("boom")
        listener = Listener(host="localhost", callback=Mock(), api_token="token", replay_store=replay_store)
        listener._release_replay_key("k1")
