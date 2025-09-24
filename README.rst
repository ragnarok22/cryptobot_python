================
CryptoBot Python
================

.. image:: https://img.shields.io/pypi/v/cryptobot_python.svg
    :target: https://pypi.python.org/pypi/cryptobot-python

.. image:: https://github.com/ragnarok22/cryptobot_python/actions/workflows/python-tests.yml/badge.svg
    :target: https://github.com/ragnarok22/cryptobot_python/actions/workflows/python-tests.yml
    :alt: Python tests

.. image:: https://results.pre-commit.ci/badge/github/ragnarok22/cryptobot_python/main.svg
    :target: https://results.pre-commit.ci/latest/github/ragnarok22/cryptobot_python/main
    :alt: pre-commit.ci status

.. image:: https://readthedocs.org/projects/cryptobot-python/badge/?version=latest
    :target: https://cryptobot-python.readthedocs.io/en/latest/?version=latest
    :alt: Documentation Status

.. image:: https://codecov.io/gh/ragnarok22/cryptobot_python/graph/badge.svg?token=ZsuusfJ2NJ
    :target: https://codecov.io/gh/ragnarok22/cryptobot_python

.. image:: https://deepwiki.com/badge.svg
    :target: https://deepwiki.com/ragnarok22/cryptobot_python
    :alt: Ask DeepWiki


Unofficial, but friendly client for the `Crypto Bot <https://pay.crypt.bot/>`_ API. Provides Pythonic models, sane defaults, and synchronous helpers so you can issue invoices or payouts with minimal boilerplate.

Features
--------

* Lean synchronous client powered by ``httpx``
* Dataclass models for invoices, balances, currencies, and exchange rates
* Enum-based guard rails for assets, statuses, and button names
* Optional testnet support and configurable request timeout
* FastAPI webhook example to bootstrap integrations

Installation
------------

CryptoBot Python targets Python 3.9+. Install it from PyPI:

.. code-block:: bash

   pip install cryptobot-python

Quick Start
-----------

Grab an API token from ``@CryptoBot`` in Telegram, then create a client and start issuing invoices:

.. code-block:: python

   from cryptobot import CryptoBotClient
   from cryptobot.models import Asset

   client = CryptoBotClient("YOUR_API_TOKEN")

   invoice = client.create_invoice(
       asset=Asset.USDT,
       amount=5.25,
       description="Coffee order #42",
   )

   print(invoice.bot_invoice_url)

Invoices, balances, currencies, and transfers are returned as dataclasses, so attributes are available using dot access. For low-level control, check the `API reference <https://cryptobot-python.readthedocs.io/en/latest/>`_.

Handling Errors
---------------

All API failures raise :class:`cryptobot.errors.CryptoBotError`. Inspect the error for the Crypto Bot error ``code`` and ``name``:

.. code-block:: python

   try:
       client.transfer(user_id=12345, asset=Asset.TON, amount=0.5, spend_id="demo")
   except CryptoBotError as exc:
       print(exc.code, exc.name)

Local Development
-----------------

Clone the repo and install development dependencies with Poetry:

.. code-block:: bash

   poetry install

Use the helper ``Makefile`` targets while iterating:

.. code-block:: bash

   make lint      # flake8 checks for cryptobot/ and tests/
   make test      # pytest with coverage report
   make docs      # rebuild the Sphinx documentation

To experiment with the webhook example, run:

.. code-block:: bash

   poetry run uvicorn cryptobot.webhook:app --reload

Contributing
------------

Bug reports, feature ideas, and pull requests are welcome. Please run ``make lint`` and ``make test`` before opening a PR, and update the docs when modifying public APIs. See ``AGENTS.md`` for more contributor guidance.

Credits
-------

This project started with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
