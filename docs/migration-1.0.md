# Migrating from 0.5.x to 1.0.0

This guide covers the breaking changes introduced in v1.0.0 and how to update
your code.

## `create_invoice()` signature change

The `asset` parameter is no longer the first positional argument and is now
optional. `amount` is the first positional argument.

**Before (0.5.x):**

```python
invoice = client.create_invoice(Asset.TON, 1.5)

# or with keyword arguments
invoice = client.create_invoice(asset=Asset.TON, amount=1.5)
```

**After (1.0.0):**

```python
invoice = client.create_invoice(1.5, asset=Asset.TON)

# keyword-only style still works, but asset must come after amount
invoice = client.create_invoice(amount=1.5, asset=Asset.TON)
```

If you were already using `asset=` and `amount=` as keyword arguments, the only
change is that `asset` is now optional (required only for crypto invoices).

### Fiat invoices

The signature change enables the new fiat invoice support. To create a fiat
invoice, omit `asset` and pass `currency_type`, `fiat`, and `accepted_assets`
instead:

```python
invoice = client.create_invoice(
    amount=10.00,
    currency_type="fiat",
    fiat="USD",
    accepted_assets="USDT,TON,BTC",
)
```

## `ExchangeRate.source` is now a `str`

`ExchangeRate.source` changed from the `Asset` enum to a plain `str` because
the API can return fiat currency codes that are not members of `Asset`.

**Before (0.5.x):**

```python
rates = client.get_exchange_rates()
btc_usd = next(r for r in rates if r.source == Asset.BTC and r.target == "USD")
```

**After (1.0.0):**

```python
rates = client.get_exchange_rates()
btc_usd = next(r for r in rates if r.source == "BTC" and r.target == "USD")
```

## Validation error messages

Internal validation was generalized to support checks and transfers. If your
code matches on exception messages from `create_invoice` or `get_invoices`,
update accordingly:

| 0.5.x message                                        | 1.0.0 message                                   |
| ---------------------------------------------------- | ------------------------------------------------ |
| `"invoice_ids string cannot be empty"`                | `"ids string cannot be empty"`                   |
| `"invoice_ids list cannot be empty"`                  | `"ids list cannot be empty"`                     |
| `"invoice_ids string must contain positive integer IDs"` | `"ids string must contain positive integer IDs"` |
| `"invoice_ids list must contain positive integers"`   | `"ids list must contain positive integers"`       |
| `"invoice_ids must be a comma-separated string or list of integers"` | `"ids must be a comma-separated string or list of integers"` |

## New endpoints

These are additive and do not break existing code, but are worth noting:

- `delete_invoice(invoice_id)`
- `create_check(asset, amount, ...)` / `delete_check(check_id)`
- `get_checks(...)` with `iter_checks()` and `iter_check_pages()` pagination
- `get_transfers(...)` with `iter_transfers()` and `iter_transfer_pages()` pagination
- `get_stats(start_at, end_at)`
- `fiat` filter parameter on `get_invoices()`

All new endpoints are available on both `CryptoBotClient` and
`AsyncCryptoBotClient`.
