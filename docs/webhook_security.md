# Webhook Security Guide

This guide explains how to securely configure and use webhooks with Crypto Bot to receive payment notifications.

## Table of Contents

1. [Overview](#overview)
2. [Signature Verification](#signature-verification)
3. [Secure Token Handling](#secure-token-handling)
4. [Deployment Best Practices](#deployment-best-practices)
5. [Common Security Pitfalls](#common-security-pitfalls)
6. [Testing Webhooks](#testing-webhooks)

## Overview

Webhooks allow Crypto Bot to send real-time notifications to your application when events occur (e.g., invoice paid, transfer completed). **Security is critical** because webhooks expose an HTTP endpoint that accepts external requests.

### Why Signature Verification Matters

Without signature verification, an attacker could:
- Send fake payment notifications
- Trigger unauthorized actions in your application
- Access sensitive business logic
- Cause financial losses

The `cryptobot` library automatically verifies signatures for you using HMAC-SHA256.

## Signature Verification

### How It Works

Crypto Bot signs every webhook request using HMAC-SHA256:

```
signature = HMAC-SHA256(SHA256(api_token), request_body)
```

The signature is sent in the `crypto-pay-api-signature` header.

### Automatic Verification

The `Listener` class automatically verifies all incoming webhooks:

```python
from cryptobot.webhook import Listener

def handle_webhook(headers, data):
    # This function is only called for VERIFIED webhooks
    if data['update_type'] == 'invoice_paid':
        invoice = data['payload']
        print(f"Verified payment: {invoice['invoice_id']}")

listener = Listener(
    host="0.0.0.0",
    callback=handle_webhook,
    api_token="YOUR_API_TOKEN"  # Used for signature verification
)
listener.listen()
```

**Important:** Invalid signatures are rejected with a 400 error before reaching your callback.

### Manual Verification

If you're implementing a custom webhook handler, use the `check_signature` function:

```python
from cryptobot.webhook import check_signature
from fastapi import FastAPI, Request, HTTPException

app = FastAPI()

@app.post("/webhook")
async def webhook(request: Request):
    body = await request.json()

    # Verify signature
    if not check_signature("YOUR_API_TOKEN", body, request.headers):
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Process verified webhook
    print(f"Verified webhook: {body}")
    return {"status": "ok"}
```

## Secure Token Handling

### ❌ Never Do This

```python
# DON'T hardcode tokens in source code
listener = Listener(
    host="0.0.0.0",
    callback=handle_webhook,
    api_token="12345:AABCD..."  # ❌ BAD!
)
```

### ✅ Use Environment Variables

```python
import os
from dotenv import load_dotenv

# Load from .env file
load_dotenv()

listener = Listener(
    host="0.0.0.0",
    callback=handle_webhook,
    api_token=os.getenv("CRYPTOBOT_API_TOKEN")  # ✅ GOOD!
)
```

**`.env` file:**
```bash
CRYPTOBOT_API_TOKEN=12345:AABCD...
```

**Important:** Add `.env` to your `.gitignore`!

### Token Storage Best Practices

1. **Development:** Use `.env` files (never commit them)
2. **Production:** Use environment variables or secrets management:
   - AWS Secrets Manager
   - HashiCorp Vault
   - Kubernetes Secrets
   - Azure Key Vault

3. **CI/CD:** Use encrypted secrets:
   - GitHub Secrets
   - GitLab CI/CD Variables
   - CircleCI Environment Variables

## Deployment Best Practices

### 1. Use HTTPS (TLS/SSL)

**Always use HTTPS** for webhook endpoints. Crypto Bot requires HTTPS for production webhooks.

#### Development with ngrok

```bash
# Install ngrok
brew install ngrok  # macOS
# or download from https://ngrok.com

# Start your webhook server
python app.py  # Runs on localhost:2203

# In another terminal, create HTTPS tunnel
ngrok http 2203
```

You'll get a URL like `https://abc123.ngrok.io` - use this as your webhook URL.

#### Production Deployment

Use a reverse proxy like Nginx or a cloud service:

```nginx
# Nginx configuration
server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location /webhook {
        proxy_pass http://127.0.0.1:2203;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 2. Bind to Localhost in Production

```python
# ✅ GOOD: Only accessible via reverse proxy
listener = Listener(
    host="127.0.0.1",  # localhost only
    callback=handle_webhook,
    api_token=os.getenv("CRYPTOBOT_API_TOKEN"),
    port=2203
)

# ❌ BAD: Exposed to internet without HTTPS
listener = Listener(
    host="0.0.0.0",  # accessible from anywhere
    callback=handle_webhook,
    api_token=os.getenv("CRYPTOBOT_API_TOKEN"),
    port=2203
)
```

### 3. Implement Rate Limiting

Protect against DoS attacks:

```python
from fastapi import FastAPI, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

listener = Listener(
    host="127.0.0.1",
    callback=handle_webhook,
    api_token=os.getenv("CRYPTOBOT_API_TOKEN")
)

# Apply rate limiting
@limiter.limit("100/minute")
@listener.app.post("/webhook")
async def rate_limited_webhook(request: Request):
    # Your webhook logic
    pass
```

### 4. Logging and Monitoring

```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def handle_webhook(headers, data):
    try:
        # Log webhook receipt (don't log sensitive data!)
        logger.info(f"Webhook received: {data.get('update_type')}")

        # Process webhook
        if data['update_type'] == 'invoice_paid':
            invoice_id = data['payload']['invoice_id']
            logger.info(f"Payment received for invoice {invoice_id}")

    except Exception as e:
        logger.error(f"Webhook processing failed: {e}", exc_info=True)
        raise

listener = Listener(
    host="127.0.0.1",
    callback=handle_webhook,
    api_token=os.getenv("CRYPTOBOT_API_TOKEN"),
    log_level="info"  # Set uvicorn log level
)
```

## Common Security Pitfalls

### ❌ Pitfall 1: Not Verifying Signatures

```python
# ❌ DANGEROUS: No signature verification
@app.post("/webhook")
async def webhook(data: dict):
    # Anyone can send fake payments!
    process_payment(data)
```

**Fix:** Always use the `Listener` class or `check_signature` function.

### ❌ Pitfall 2: Exposing API Token in Logs

```python
# ❌ BAD: Token in logs
logger.info(f"Starting webhook with token: {api_token}")

# ❌ BAD: Token in error messages
raise Exception(f"Failed with token {api_token}")
```

**Fix:** Never log sensitive data.

### ❌ Pitfall 3: Trusting User Input

```python
# ❌ DANGEROUS: SQL injection risk
def handle_webhook(headers, data):
    user_id = data['payload']['user_id']
    db.execute(f"SELECT * FROM users WHERE id = {user_id}")  # ❌
```

**Fix:** Use parameterized queries:

```python
# ✅ SAFE: Parameterized query
def handle_webhook(headers, data):
    user_id = data['payload']['user_id']
    db.execute("SELECT * FROM users WHERE id = ?", (user_id,))  # ✅
```

### ❌ Pitfall 4: Synchronous Blocking Operations

```python
# ❌ BAD: Blocks webhook server
def handle_webhook(headers, data):
    time.sleep(30)  # Long operation blocks server!
    send_email(data)
```

**Fix:** Use async operations or background tasks:

```python
# ✅ GOOD: Background processing
import asyncio
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor()

def handle_webhook(headers, data):
    # Queue background task
    executor.submit(process_payment_async, data)

def process_payment_async(data):
    # Long-running operation in background
    send_email(data)
    update_database(data)
```

## Testing Webhooks

### Local Testing with Mock Signature

```python
import hashlib
import json
from cryptobot.webhook import check_signature

# Test signature verification
api_token = "test_token"
body = {
    "update_id": 1,
    "update_type": "invoice_paid",
    "payload": {"invoice_id": 123}
}

# Generate valid signature
secret = hashlib.sha256(api_token.encode()).digest()
check_string = json.dumps(body)
hmac = hashlib.sha256(secret)
hmac.update(check_string.encode())
signature = hmac.hexdigest()

# Test verification
headers = {"crypto-pay-api-signature": signature}
assert check_signature(api_token, body, headers) == True

# Test invalid signature
invalid_headers = {"crypto-pay-api-signature": "wrong_signature"}
assert check_signature(api_token, body, invalid_headers) == False
```

### Testing with pytest

```python
from fastapi.testclient import TestClient
from cryptobot.webhook import Listener

def test_webhook_valid_signature():
    received_data = {}

    def callback(headers, data):
        received_data.update(data)

    listener = Listener(
        host="localhost",
        callback=callback,
        api_token="test_token"
    )

    client = TestClient(listener.app)

    # Generate valid signature
    # ... (same as above)

    response = client.post(
        "/webhook",
        json=body,
        headers={"crypto-pay-api-signature": signature}
    )

    assert response.status_code == 200
    assert received_data["update_id"] == 1

def test_webhook_invalid_signature():
    listener = Listener(
        host="localhost",
        callback=lambda h, d: None,
        api_token="test_token"
    )

    client = TestClient(listener.app)

    response = client.post(
        "/webhook",
        json={"test": "data"},
        headers={"crypto-pay-api-signature": "invalid"}
    )

    assert response.status_code == 400
```

## Security Checklist

Before going to production, verify:

- [ ] HTTPS/TLS enabled for webhook endpoint
- [ ] API token stored in environment variables (not hardcoded)
- [ ] Signature verification enabled (automatic with `Listener`)
- [ ] Webhook server binds to localhost (behind reverse proxy)
- [ ] Rate limiting implemented
- [ ] Logging configured (without sensitive data)
- [ ] Error handling implemented
- [ ] Background task processing for long operations
- [ ] Firewall rules configured
- [ ] Monitoring and alerting set up

## Additional Resources

- [Crypto Bot API Documentation](https://help.crypt.bot/crypto-pay-api)
- [OWASP Webhook Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Webhook_Security_Cheat_Sheet.html)
- [FastAPI Security Documentation](https://fastapi.tiangolo.com/tutorial/security/)
- [PEP 543 - TLS/SSL](https://peps.python.org/pep-0543/)
