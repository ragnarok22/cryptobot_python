# Webhook Security Guide

This guide explains how to safely receive Crypto Bot webhook events in production.

## Threat Model

A webhook endpoint is a public HTTP surface. Without verification and controls, attackers can:

- Forge payment notifications
- Replay old updates
- Exhaust worker capacity with burst traffic

## Signature Verification

Crypto Bot signs each request with:

```text
HMAC-SHA256(SHA256(api_token), raw_request_body)
```

The signature arrives in the `crypto-pay-api-signature` header.

## Recommended: Use `Listener`

`Listener` verifies signatures before executing your callback.

```python
import os

from cryptobot.webhook import InMemoryReplayKeyStore, Listener


def handle_webhook(headers, data):
    if data.get("update_type") == "invoice_paid":
        payload = data.get("payload", {})
        print("Verified payment for invoice", payload.get("invoice_id"))


listener = Listener(
    host="127.0.0.1",  # Prefer localhost behind reverse proxy
    callback=handle_webhook,
    api_token=os.environ["CRYPTOBOT_API_TOKEN"],
    replay_store=InMemoryReplayKeyStore(),
    replay_ttl_seconds=3600,
    port=2203,
    url="/webhook",
    log_level="info",
)
listener.listen()
```

`callback` can be synchronous (`def`) or asynchronous (`async def`).

## Manual Verification (Custom FastAPI App)

If you manage your own FastAPI route, verify against the **raw body string**.

```python
import json
import os

from fastapi import FastAPI, HTTPException, Request

from cryptobot.webhook import check_signature

app = FastAPI()
api_token = os.environ["CRYPTOBOT_API_TOKEN"]


@app.post("/webhook")
async def webhook(request: Request):
    raw = await request.body()
    raw_str = raw.decode("utf-8")

    if not check_signature(api_token, raw_str, request.headers):
        raise HTTPException(status_code=400, detail="Invalid signature")

    data = json.loads(raw_str)
    # Handle verified data...
    return {"ok": True}
```

## Replay Protection

`Listener` supports pluggable replay protection via `replay_store`.
For production, prefer a shared store (e.g., Redis) implementing:

- `put_if_absent(key: str, ttl_seconds: int | None) -> bool`
- `remove(key: str) -> None`

Built-in in-memory replay protection:

```python
import os

from cryptobot.webhook import InMemoryReplayKeyStore, Listener

listener = Listener(
    host="127.0.0.1",
    callback=handle_webhook,
    api_token=os.environ["CRYPTOBOT_API_TOKEN"],
    replay_store=InMemoryReplayKeyStore(),
    replay_ttl_seconds=3600,
)
```

In production, store this in Redis or your database instead of process memory.

### Custom Replay Keys

If your integration has a stable business identifier, use `replay_key_resolver`:

```python
import os

from cryptobot.webhook import InMemoryReplayKeyStore, Listener


def replay_key_resolver(data, raw_body, headers):
    payload = data.get("payload", {})
    invoice_id = payload.get("invoice_id")
    if invoice_id is not None:
        return f"invoice_paid:{invoice_id}"
    return None


listener = Listener(
    host="127.0.0.1",
    callback=handle_webhook,
    api_token=os.environ["CRYPTOBOT_API_TOKEN"],
    replay_store=InMemoryReplayKeyStore(),
    replay_ttl_seconds=3600,
    replay_key_resolver=replay_key_resolver,
)
```

## Deployment Hardening

1. Use HTTPS at the public edge.
2. Bind app to `127.0.0.1` behind Nginx/Caddy/ingress when possible.
3. Apply request limits and upstream timeouts.
4. Keep webhook handler fast; queue expensive work.
5. Never log secrets or full raw payloads in production.

## Reverse Proxy Example (Nginx)

```nginx
server {
    listen 443 ssl http2;
    server_name pay.example.com;

    ssl_certificate /etc/letsencrypt/live/pay.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/pay.example.com/privkey.pem;

    location /webhook {
        proxy_pass http://127.0.0.1:2203/webhook;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Queue-Based Processing

Move non-trivial business logic off the request thread.

```python
from queue import Queue
from threading import Thread

work_q: Queue[dict] = Queue(maxsize=1000)


def worker():
    while True:
        update = work_q.get()
        try:
            # Process invoice_paid, transfer_completed, etc.
            pass
        finally:
            work_q.task_done()


def handle_webhook(headers, data):
    work_q.put_nowait(data)


Thread(target=worker, daemon=True).start()
```

## Local Testing

### 1. Run listener locally

```bash
# Start your own listener script (example filename)
uv run python listener.py
```

### 2. Expose local port with ngrok

```bash
ngrok http 2203
```

### 3. Set webhook URL in Crypto Bot

Use the HTTPS URL from ngrok plus `/webhook`.

## Pytest Signature Test

```python
import hashlib
import hmac
import json

from fastapi.testclient import TestClient

from cryptobot.webhook import Listener


def sign(token: str, raw_body: str) -> str:
    secret = hashlib.sha256(token.encode()).digest()
    return hmac.new(secret, raw_body.encode("utf-8"), hashlib.sha256).hexdigest()


def test_valid_signature():
    received = {}

    def callback(headers, data):
        received.update(data)

    listener = Listener(host="127.0.0.1", callback=callback, api_token="test-token")
    client = TestClient(listener.app)

    body = {"update_id": 1, "update_type": "invoice_paid", "payload": {"invoice_id": 123}}
    raw = json.dumps(body)
    signature = sign("test-token", raw)

    resp = client.post("/webhook", content=raw, headers={"crypto-pay-api-signature": signature})

    assert resp.status_code == 200
    assert received["update_id"] == 1
```

## Security Checklist

- [ ] Signature verification enabled (`Listener` or `check_signature`)
- [ ] HTTPS termination configured
- [ ] Token comes from environment/secrets manager
- [ ] Replay protection in place
- [ ] Slow/background operations moved to workers
- [ ] Request logging redacts sensitive fields

## References

- [Crypto Bot API docs](https://help.crypt.bot/crypto-pay-api)
- [OWASP Webhook Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Webhook_Security_Cheat_Sheet.html)
- [FastAPI security docs](https://fastapi.tiangolo.com/tutorial/security/)
