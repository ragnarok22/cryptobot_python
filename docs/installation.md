# Installation

## Requirements

- Python 3.9.12+
- pip (or Poetry for development)

## Install from PyPI

```bash
pip install cryptobot-python
```

## Verify Installation

```python
from cryptobot import CryptoBotClient
print(CryptoBotClient)
```

## Install from Source

```bash
git clone https://github.com/ragnarok22/cryptobot_python.git
cd cryptobot_python
poetry install
```

For documentation tooling:

```bash
poetry install --extras docs
```

## Development Setup

```bash
poetry install
make lint
make test
```

## Common Pitfalls

- Use `cryptobot-python` as the package name in `pip install`.
- Keep mainnet and testnet tokens separate.
- Store tokens in environment variables instead of source code.
