import hashlib
import hmac
import inspect
import json
import logging
import threading
import time
from collections.abc import Awaitable, Mapping
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional, Protocol, Union

import uvicorn
from colorama import Fore, Style
from fastapi import FastAPI, HTTPException, Request

logger = logging.getLogger(__name__)


class ReplayKeyStore(Protocol):
    """Storage contract for webhook replay-protection keys."""

    def put_if_absent(self, key: str, ttl_seconds: Optional[int] = None) -> bool:
        """Atomically store key if absent.

        Returns:
            True when key is accepted and stored.
            False when key already exists (replay detected).
        """

    def remove(self, key: str) -> None:
        """Remove a previously stored key.

        Implementations may use this to roll back reservation when callback fails.
        """


class InMemoryReplayKeyStore:
    """Thread-safe in-memory replay key store with optional TTL eviction."""

    def __init__(self):
        self._keys: Dict[str, Optional[float]] = {}
        self._lock = threading.Lock()

    def put_if_absent(self, key: str, ttl_seconds: Optional[int] = None) -> bool:
        with self._lock:
            now = time.monotonic()
            self._purge_expired(now)

            expiry = now + ttl_seconds if ttl_seconds and ttl_seconds > 0 else None
            if key in self._keys:
                return False

            self._keys[key] = expiry
            return True

    def remove(self, key: str) -> None:
        with self._lock:
            self._keys.pop(key, None)

    def _purge_expired(self, now: float) -> None:
        expired_keys = [key for key, expires_at in self._keys.items() if expires_at is not None and now >= expires_at]
        for key in expired_keys:
            del self._keys[key]


WebhookHeaders = Mapping[str, str]
WebhookPayload = Dict[str, Any]
ReplayKeyResolver = Callable[[WebhookPayload, str, WebhookHeaders], Optional[str]]
WebhookCallback = Callable[[WebhookHeaders, WebhookPayload], Union[None, Awaitable[None]]]


def check_signature(token: str, body: Union[str, bytes], headers) -> bool:
    """Verify webhook signature using HMAC-SHA256.

    This function validates that webhook requests are genuinely from Crypto Bot
    by comparing the HMAC-SHA256 signature in the request headers with a
    computed signature based on your API token and the request body.

    Args:
        token: Your Crypto Bot API token.
        body: The raw webhook request body as a string (unparsed JSON) or bytes.
        headers: The request headers containing the signature.

    Returns:
        True if the signature is valid, False otherwise.

    Security Note:
        Always verify webhook signatures to prevent unauthorized access.
        The signature is computed as: HMAC-SHA256(SHA256(api_token), raw_request_body)

        IMPORTANT: The body must be the raw, unparsed JSON string as received from
        the request, not a re-serialized dictionary. JSON serialization order and
        formatting must match exactly for signature verification to succeed.

    Example:
        >>> headers = {"crypto-pay-api-signature": "abc123..."}
        >>> raw_body = '{"update_id":1,"update_type":"invoice_paid",...}'
        >>> if check_signature("YOUR_API_TOKEN", raw_body, headers):
        ...     print("Valid webhook")
        ... else:
        ...     print("Invalid signature - possible attack!")
    """
    secret = hashlib.sha256(token.encode()).digest()
    raw_body = body.encode() if isinstance(body, str) else body
    computed_signature = hmac.new(secret, raw_body, hashlib.sha256).hexdigest()
    received_signature = headers.get("crypto-pay-api-signature", "")

    logger.debug(f"Computed HMAC: {computed_signature}")
    logger.debug(f"Received signature: {received_signature}")

    return hmac.compare_digest(computed_signature, received_signature)


@dataclass
class Listener:
    """FastAPI-based webhook listener for Crypto Bot payment notifications.

    This class creates an HTTP server that receives and validates webhook notifications
    from Crypto Bot when invoices are paid or other events occur. It automatically
    verifies request signatures to ensure authenticity.

    Args:
        host: Hostname or IP address to bind to (e.g., "0.0.0.0", "localhost").
        callback: Function called when a valid webhook is received.
                  Signature: callback(headers: dict, data: dict) -> None
        api_token: Your Crypto Bot API token for signature verification.
        port: Port number to listen on. Default: 2203.
        url: Webhook endpoint path. Default: "/webhook".
        log_level: Uvicorn logging level ("critical", "error", "warning", "info", "debug").
                   Default: "error".

    Security:
        - All incoming webhooks are verified using HMAC-SHA256 signatures
        - Invalid signatures are rejected with a 400 error
        - Never expose your API token in logs or responses

    Examples:
        Basic webhook listener:
            >>> def handle_payment(headers, data):
            ...     if data['update_type'] == 'invoice_paid':
            ...         invoice_id = data['payload']['invoice_id']
            ...         print(f"Payment received for invoice {invoice_id}")
            >>>
            >>> listener = Listener(
            ...     host="0.0.0.0",
            ...     callback=handle_payment,
            ...     api_token="YOUR_API_TOKEN"
            ... )
            >>> listener.listen()  # Starts the server

        Custom port and path:
            >>> listener = Listener(
            ...     host="localhost",
            ...     callback=handle_payment,
            ...     api_token="YOUR_API_TOKEN",
            ...     port=8080,
            ...     url="/crypto-webhook",
            ...     log_level="info"
            ... )
            >>> listener.listen()

        Production deployment with ngrok/reverse proxy:
            >>> # 1. Start your listener
            >>> listener = Listener(
            ...     host="0.0.0.0",
            ...     callback=handle_payment,
            ...     api_token="YOUR_API_TOKEN",
            ...     port=443
            ... )
            >>>
            >>> # 2. Configure webhook URL in Crypto Bot
            >>> # Set webhook to: https://yourdomain.com/webhook
            >>>
            >>> # 3. Start listening
            >>> listener.listen()
    """

    host: str
    callback: WebhookCallback
    api_token: str
    port: int = 2203
    url: str = "/webhook"
    log_level: str = "error"
    replay_store: Optional[ReplayKeyStore] = None
    replay_ttl_seconds: int = 3600
    replay_key_resolver: Optional[ReplayKeyResolver] = None
    app: FastAPI = field(init=False, repr=False)

    async def _read_raw_body(self, request: Request) -> str:
        raw_body = await request.body()
        try:
            return raw_body.decode("utf-8")
        except UnicodeDecodeError as e:
            logger.error(f"Invalid body encoding in webhook request: {e}")
            raise HTTPException(status_code=400, detail="Invalid encoding") from e

    def _verify_signature(self, raw_body: str, headers) -> None:
        if not check_signature(self.api_token, raw_body, headers):
            logger.warning("Invalid webhook signature detected")
            raise HTTPException(status_code=400, detail="Invalid signature")

    @staticmethod
    def _parse_json(raw_body: str) -> dict:
        try:
            return json.loads(raw_body)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in webhook request: {e}")
            raise HTTPException(status_code=400, detail="Invalid JSON") from e

    @staticmethod
    def _default_replay_key(data: WebhookPayload, raw_body: str, _headers: WebhookHeaders) -> str:
        update_id = data.get("update_id")
        if update_id is not None:
            return f"update_id:{update_id}"

        update_type = data.get("update_type", "unknown")
        payload = data.get("payload")
        if isinstance(payload, dict):
            for field_name in ("invoice_id", "transfer_id", "check_id"):
                value = payload.get(field_name)
                if value is not None:
                    return f"{update_type}:{field_name}:{value}"

        body_hash = hashlib.sha256(raw_body.encode("utf-8")).hexdigest()
        return f"body:{body_hash}"

    def _reserve_replay_key(self, raw_body: str, data: WebhookPayload, headers: WebhookHeaders) -> Optional[str]:
        if self.replay_store is None:
            return None

        resolver = self.replay_key_resolver or self._default_replay_key
        replay_key = resolver(data, raw_body, headers)
        if replay_key is None:
            return None

        replay_key = str(replay_key).strip()
        if not replay_key:
            return None

        ttl_seconds = self.replay_ttl_seconds if self.replay_ttl_seconds > 0 else None
        is_accepted = self.replay_store.put_if_absent(replay_key, ttl_seconds=ttl_seconds)
        if not is_accepted:
            logger.warning("Replay webhook rejected. key=%s", replay_key)
            raise HTTPException(status_code=409, detail="Duplicate webhook")

        return replay_key

    def _release_replay_key(self, replay_key: Optional[str]) -> None:
        if not replay_key or self.replay_store is None:
            return

        try:
            self.replay_store.remove(replay_key)
        except Exception as e:
            logger.warning("Failed to release replay key %s after callback failure: %s", replay_key, e)

    async def _execute_callback(self, headers: WebhookHeaders, data: WebhookPayload) -> None:
        callback_result = self.callback(headers, data)
        if inspect.isawaitable(callback_result):
            await callback_result

    def __post_init__(self):
        if not callable(self.callback):
            raise TypeError("callback must be callable")
        if self.replay_store is not None and not hasattr(self.replay_store, "put_if_absent"):
            raise TypeError("replay_store must implement put_if_absent(key, ttl_seconds=None)")
        if self.replay_ttl_seconds < 0:
            raise ValueError("replay_ttl_seconds must be >= 0")
        if self.replay_key_resolver is not None and not callable(self.replay_key_resolver):
            raise TypeError("replay_key_resolver must be callable")

        # Create a new FastAPI app instance for this listener
        self.app = FastAPI()

        @self.app.post(self.url)
        async def listen_webhook(request: Request):
            raw_body = await self._read_raw_body(request)
            self._verify_signature(raw_body, request.headers)
            data = self._parse_json(raw_body)

            logger.info(f"Received webhook: update_type={data.get('update_type')}")
            replay_key = self._reserve_replay_key(raw_body, data, request.headers)

            try:
                await self._execute_callback(request.headers, data)
            except Exception as e:
                self._release_replay_key(replay_key)
                logger.error(f"Callback function error: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail="Callback error") from e

            return {"ok": True}

    def listen(self):
        """Start the webhook server and listen for incoming requests.

        This method starts a uvicorn server that listens for webhook notifications.
        It will block until the server is stopped (Ctrl+C).

        Note:
            This is a blocking call. The server will run until interrupted.

        Example:
            >>> listener = Listener("0.0.0.0", my_callback, "API_TOKEN")
            >>> listener.listen()  # Server starts and blocks here
            [Webhook Listener]
            * Docs: https://help.crypt.bot/crypto-pay-api#Webhook
            * Listening on http://0.0.0.0:2203/webhook (Press CTRL+C to stop)
        """
        url = f"http://{self.host}:{self.port}{self.url}"
        logger.info(f"Listening on {url}")

        print(
            Fore.BLUE
            + r"""
 $$$$$$\                                  $$\                     $$$$$$$\              $$\
$$  __$$\                                 $$ |                    $$  __$$\             $$ |
$$ /  \__| $$$$$$\  $$\   $$\  $$$$$$\  $$$$$$\    $$$$$$\        $$ |  $$ | $$$$$$\  $$$$$$\
$$ |      $$  __$$\ $$ |  $$ |$$  __$$\ \_$$  _|  $$  __$$\       $$$$$$$\ |$$  __$$\ \_$$  _|
$$ |      $$ |  \__|$$ |  $$ |$$ /  $$ |  $$ |    $$ /  $$ |      $$  __$$\ $$ /  $$ |  $$ |
$$ |  $$\ $$ |      $$ |  $$ |$$ |  $$ |  $$ |$$\ $$ |  $$ |      $$ |  $$ |$$ |  $$ |  $$ |$$\
\$$$$$$  |$$ |      \$$$$$$$ |$$$$$$$  |  \$$$$  |\$$$$$$  |      $$$$$$$  |\$$$$$$  |  \$$$$  |
 \______/ \__|       \____$$ |$$  ____/    \____/  \______/       \_______/  \______/    \____/
                    $$\   $$ |$$ |
                    \$$$$$$  |$$ |
                     \______/ \__|
"""
        )
        print(
            Style.RESET_ALL
            + f"""[Webhook Listener]

* Docs: https://help.crypt.bot/crypto-pay-api#Webhook
* Listening on {url} (Press CTRL+C to stop)
            """
        )
        uvicorn.run(self.app, host=self.host, port=self.port, log_level=self.log_level)
