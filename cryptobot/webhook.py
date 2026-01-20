import hashlib
import json
import logging
from dataclasses import dataclass

import uvicorn
from colorama import Fore, Style
from fastapi import FastAPI, Request

from cryptobot.errors import CryptoBotError

logger = logging.getLogger(__name__)


def check_signature(token: str, body: str, headers) -> bool:
    """Verify webhook signature using HMAC-SHA256.

    This function validates that webhook requests are genuinely from Crypto Bot
    by comparing the HMAC-SHA256 signature in the request headers with a
    computed signature based on your API token and the request body.

    Args:
        token: Your Crypto Bot API token.
        body: The raw webhook request body as a string (unparsed JSON).
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
    hmac = hashlib.sha256(secret)
    hmac.update(body.encode() if isinstance(body, str) else body)
    computed_signature = hmac.hexdigest()
    received_signature = headers.get("crypto-pay-api-signature", "")

    logger.debug(f"Computed HMAC: {computed_signature}")
    logger.debug(f"Received signature: {received_signature}")

    return computed_signature == received_signature


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
    callback: callable
    api_token: str
    port: int = 2203
    url: str = "/webhook"
    log_level: str = "error"

    def __post_init__(self):
        # Create a new FastAPI app instance for this listener
        self.app = FastAPI()

        @self.app.post(self.url)
        async def listen_webhook(request: Request):
            try:
                # Get raw body for signature verification
                raw_body = await request.body()
                raw_body_str = raw_body.decode("utf-8")

                # Parse JSON for use
                data = json.loads(raw_body_str)
                logger.info(f"Received webhook: update_type={data.get('update_type')}")

                # Verify signature using raw body
                if not check_signature(self.api_token, raw_body_str, request.headers):
                    logger.warning("Invalid webhook signature detected")
                    raise CryptoBotError(code=400, name="Invalid signature")

                # Execute callback with error handling
                try:
                    self.callback(request.headers, data)
                except Exception as e:
                    logger.error(f"Callback function error: {e}", exc_info=True)
                    raise CryptoBotError(code=500, name=f"Callback error: {str(e)}")

                return {"ok": True}
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in webhook request: {e}")
                raise CryptoBotError(code=400, name="Invalid JSON")
            except CryptoBotError:
                raise
            except Exception as e:
                logger.error(f"Unexpected error processing webhook: {e}", exc_info=True)
                raise CryptoBotError(code=500, name=f"Internal error: {str(e)}")

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
            * Listening on https://0.0.0.0:2203/webhook (Press CTRL+C to stop)
        """
        url = f"https://{self.host}:{self.port}{self.url}"
        logger.info(f"Listening on {url}")

        print(Fore.BLUE + r"""
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
""")
        print(Style.RESET_ALL + f"""[Webhook Listener]

* Docs: https://help.crypt.bot/crypto-pay-api#Webhook
* Listening on {url} (Press CTRL+C to stop)
            """)
        uvicorn.run(self.app, host=self.host, port=self.port, log_level=self.log_level)
